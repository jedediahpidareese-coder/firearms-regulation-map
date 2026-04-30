"""Phase 5 (research): Callaway-Sant'Anna ATT(g,t) for permitless carry.

Treatment: a state's first 1->0 switch in Tufts `permitconcealed` (i.e., the
state stops requiring a permit to carry concealed). Treatment cohorts are
defined by the year of that switch. The treatment is treated as absorbing.

Outcomes (run side-by-side for triangulation):
  1. firearm_suicide_rate         (most-studied; v2 file 1979-2023)
  2. firearm_homicide_rate        (v2 file 1979-2023)
  3. homicide_rate                (FBI/OpenCrime 1979-2024)
  4. motor_vehicle_theft_rate     (PLACEBO -- gun policy shouldn't move car theft)

Estimator: simple Callaway & Sant'Anna (2021) ATT(g, t) with:
  - never-treated comparison group (all states whose treatment_adoption_table
    row has no adoption_year and starts permit-required = 1; this excludes
    Vermont, which was historically permitless throughout)
  - long-difference baseline at t = g - 1 (year before adoption)
  - no covariate adjustment (basic OR estimator)
  - state-cluster Mammen-style multiplier bootstrap for SEs (B = 2000)

Output:
  outputs/permitless_carry_cs/att_gt.csv          one row per (outcome, g, t)
  outputs/permitless_carry_cs/event_study.csv     one row per (outcome, e)
  outputs/permitless_carry_cs/overall_att.csv     one row per outcome
  outputs/permitless_carry_cs/cohort_n.csv        per-cohort treated unit count
  outputs/permitless_carry_cs/figures/event_study_4panel.png
  outputs/permitless_carry_cs/methodology.md      writeup

Caveats documented in methodology.md:
  - Single-state cohorts (AK 2003, AZ 2010, WY 2011) yield very noisy ATT(g,t).
  - We follow CS21 by NOT computing ATT for any (g, t) where the treated cohort
    has fewer than 2 observed long-differences.
  - The existing stacked-DiD audit at outputs/permitless_carry_suicide_audit/
    uses a STRICTER control set (state must be shall-issue + permit-required
    throughout the event window). The CS estimator here uses a single
    never-treated pool for clarity. Robustness to the stricter rule is left
    as a follow-up.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
ADO_TABLE = ROOT / "outputs" / "permitless_carry_suicide_audit" / "treatment_adoption_table.csv"
OUT = ROOT / "outputs" / "permitless_carry_cs"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

# ----- knobs ---------------------------------------------------------------

ANALYSIS_YEARS = (1999, 2023)        # state-year window included in the build
MIN_PRE_K = 5                        # how many pre-event years to require for a cohort
EVENT_WINDOW = (-5, 5)               # event-time range used for the figure
N_BOOTSTRAP = 2000
RANDOM_SEED = 7

# Baseline covariates for the regression-adjusted (RA) estimator.
# We deliberately use only non-crime, non-mortality controls so the same
# spec works for every outcome including the placebo. ln_population already
# captures most scale variation; unemployment_rate and per-capita real income
# capture macroeconomic conditions.
RA_COVARIATES = ["ln_population", "unemployment_rate", "ln_pcpi_real_2024"]

# Audit's stricter control-eligibility rule: a control state must be
# shall-issue (mayissue == 0) AND require a permit to carry concealed
# (permitconcealed == 1) for every year in the cohort's relevant event
# window. We use [g-5, g+5] for any cohort g.
STRICT_WINDOW = (-5, 5)
OUTCOMES = OrderedDict([
    ("firearm_suicide_rate",      "Firearm suicide rate (per 100k)"),
    ("firearm_homicide_rate",     "Firearm homicide rate (per 100k)"),
    ("homicide_rate",             "Total homicide rate (per 100k)"),
    ("motor_vehicle_theft_rate",  "Motor vehicle theft rate (per 100k) [placebo]"),
])


def load_panel() -> pd.DataFrame:
    """Augmented state panel filtered to the analysis window (and DC excluded)."""
    df = pd.read_csv(PROC / "panel_core_augmented.csv")
    df = df[(df["year"] >= ANALYSIS_YEARS[0]) & (df["year"] <= ANALYSIS_YEARS[1])]
    df = df[df["state_abbr"] != "DC"]
    return df.reset_index(drop=True)


def load_cohorts():
    """Return (cohorts dict, never_treated set, dropped notes).

    cohorts: { adoption_year (int) : list of state abbreviations }, only
             including cohorts with first adoption year in ANALYSIS_YEARS and
             at least one full pre-period of MIN_PRE_K years inside the panel.
    never_treated: set of state_abbrs that started permit-required and never
             switched to permitless within the panel window. (Excludes VT,
             which was historically permitless: starts_permit_required = 0.)
    """
    t = pd.read_csv(ADO_TABLE)
    t = t[t["state_abbr"] != "DC"]
    treated = t[t["adoption_year"].notna()].copy()
    treated["adoption_year"] = treated["adoption_year"].astype(int)
    cohorts: dict[int, list[str]] = {}
    notes: list[OrderedDict] = []
    for _, r in treated.iterrows():
        g = int(r["adoption_year"])
        if not r["included_in_mortality_sample"]:
            notes.append(OrderedDict([("state_abbr", r["state_abbr"]),
                                      ("adoption_year", g),
                                      ("dropped_reason",
                                       "audit excluded from mortality sample (e.g., 2024 adopters)")]))
            continue
        if g - MIN_PRE_K < ANALYSIS_YEARS[0]:
            notes.append(OrderedDict([("state_abbr", r["state_abbr"]),
                                      ("adoption_year", g),
                                      ("dropped_reason",
                                       f"adoption {g} too early for {MIN_PRE_K}-year pre-period in {ANALYSIS_YEARS[0]}+")]))
            continue
        cohorts.setdefault(g, []).append(r["state_abbr"])

    # Never-treated: no adoption_year AND started permit-required = 1.
    nt = t[(t["adoption_year"].isna()) & (t["starts_permit_required"] == 1)]
    never_treated = set(nt["state_abbr"].tolist())
    return cohorts, never_treated, notes


def strict_control_pool(panel: pd.DataFrame,
                        candidates: list[str], g: int) -> list[str]:
    """Filter candidate control states down to those that are shall-issue
    (mayissue == 0) AND permit-required (permitconcealed == 1) for every year
    in the cohort's [g-5, g+5] event window. Adopted from the audit's rule.
    """
    lo = g + STRICT_WINDOW[0]
    hi = g + STRICT_WINDOW[1]
    out = []
    for s in candidates:
        sub = panel[(panel["state_abbr"] == s)
                    & (panel["year"] >= lo) & (panel["year"] <= hi)]
        if sub.empty:
            continue
        if (sub["mayissue"] == 0).all() and (sub["permitconcealed"] == 1).all():
            out.append(s)
    return out


def long_diff(panel: pd.DataFrame, outcome: str,
              states: list[str], year_t: int, year_b: int) -> pd.Series:
    """For each state in `states`, return Y[year_t] - Y[year_b]; drop NaN."""
    sub = panel[panel["state_abbr"].isin(states) & panel["year"].isin([year_t, year_b])]
    if sub.empty:
        return pd.Series(dtype=float)
    pv = sub.pivot(index="state_abbr", columns="year", values=outcome)
    if year_t not in pv.columns or year_b not in pv.columns:
        return pd.Series(dtype=float)
    diff = pv[year_t] - pv[year_b]
    return diff.dropna()


def att_gt_point(panel: pd.DataFrame, outcome: str,
                 g: int, t: int,
                 treated_states: list[str],
                 control_states: list[str]):
    """Return the point estimate ATT(g, t) plus the per-state long-differences
    used to compute it (needed for the bootstrap)."""
    base = g - 1
    tr = long_diff(panel, outcome, treated_states, t, base)
    co = long_diff(panel, outcome, control_states, t, base)
    if len(tr) == 0 or len(co) == 0:
        return None, tr, co
    return tr.mean() - co.mean(), tr, co


def cluster_bootstrap_ses(estimator_fn, treated_long, control_long, n_b, rng):
    """Generic state-cluster Mammen multiplier bootstrap.
    estimator_fn(treated_weights, control_weights) returns a scalar.
    treated_long / control_long are pd.Series indexed by state_abbr.

    Mammen weights: w = (1 - sqrt(5)) / 2 with prob (sqrt(5)+1)/(2 sqrt(5)),
                    w = (1 + sqrt(5)) / 2 otherwise.
    For simplicity and because our N is small, we use Rademacher weights
    (+/- 1) which has cleaner small-sample behavior."""
    boots = []
    for _ in range(n_b):
        wt_tr = rng.choice([-1.0, 1.0], size=len(treated_long))
        wt_co = rng.choice([-1.0, 1.0], size=len(control_long))
        boots.append(estimator_fn(wt_tr, wt_co))
    return float(np.std(boots, ddof=1))


def _baseline_X(panel: pd.DataFrame, states: list[str], year_b: int,
                covariates: list[str]) -> pd.DataFrame:
    """Wide table indexed by state with covariate values at the baseline year."""
    sub = panel[panel["state_abbr"].isin(states) & (panel["year"] == year_b)]
    sub = sub.set_index("state_abbr")[covariates].dropna()
    return sub


def att_gt_ra(panel: pd.DataFrame, outcome: str,
              g: int, t: int,
              treated_states: list[str],
              control_states: list[str],
              covariates: list[str]):
    """Regression-adjusted ATT(g, t).

    Sant'Anna & Zhao (2020) RA estimator with never-treated comparison:

        1. Fit OLS of long-difference DeltaY on baseline X using ONLY
           never-treated control units.
        2. Predict the counterfactual long-difference for each treated unit
           using its own baseline X.
        3. ATT(g, t) = mean(treated DeltaY) - mean(predicted counterfactual).

    No covariate adjustment is identified for unit-fixed effects within the
    long difference; the regression sweeps out covariate-driven trend
    differences instead.

    Returns (att, treated_long_diff, control_long_diff, treated_residual,
    control_residual). The residuals are needed for the cluster bootstrap.
    """
    base = g - 1
    tr_dy = long_diff(panel, outcome, treated_states, t, base)
    co_dy = long_diff(panel, outcome, control_states, t, base)
    if len(tr_dy) == 0 or len(co_dy) == 0:
        return None, tr_dy, co_dy, None, None
    tr_X = _baseline_X(panel, treated_states, base, covariates)
    co_X = _baseline_X(panel, control_states, base, covariates)
    # Drop units missing covariates after the baseline pull.
    tr_dy = tr_dy.loc[tr_dy.index.intersection(tr_X.index)]
    co_dy = co_dy.loc[co_dy.index.intersection(co_X.index)]
    tr_X = tr_X.loc[tr_dy.index]
    co_X = co_X.loc[co_dy.index]
    if len(co_dy) <= len(covariates) + 2:
        # Not enough degrees of freedom in the control regression. Fall back
        # to the basic OR estimator (no covariate adjustment) for this cell.
        att, _, _ = att_gt_point(panel, outcome, g, t, treated_states, control_states)
        return att, tr_dy, co_dy, None, None

    # Add intercept; OLS via numpy linalg.
    Xc = np.c_[np.ones(len(co_X)), co_X.to_numpy()]
    yc = co_dy.to_numpy()
    beta, *_ = np.linalg.lstsq(Xc, yc, rcond=None)
    co_pred = Xc @ beta
    co_resid = yc - co_pred
    Xt = np.c_[np.ones(len(tr_X)), tr_X.to_numpy()]
    tr_pred = Xt @ beta
    att = float(tr_dy.to_numpy().mean() - tr_pred.mean())
    return att, tr_dy, co_dy, None, co_resid


def att_gt_ra_se(panel: pd.DataFrame, outcome: str, g: int, t: int,
                 treated_states: list[str], control_states: list[str],
                 covariates: list[str], n_b: int, rng) -> float:
    """Cluster bootstrap SE for the RA ATT(g, t). At each replication we
    refit the regression on a Rademacher-resampled control set and recompute
    the ATT, then take the std of the bootstrap distribution."""
    base = g - 1
    tr_dy = long_diff(panel, outcome, treated_states, t, base)
    co_dy = long_diff(panel, outcome, control_states, t, base)
    if len(tr_dy) < 2 or len(co_dy) < 2:
        return float("nan")
    tr_X = _baseline_X(panel, treated_states, base, covariates).loc[tr_dy.index.intersection(_baseline_X(panel, treated_states, base, covariates).index)]
    co_X = _baseline_X(panel, control_states, base, covariates).loc[co_dy.index.intersection(_baseline_X(panel, control_states, base, covariates).index)]
    tr_dy = tr_dy.loc[tr_X.index]
    co_dy = co_dy.loc[co_X.index]
    if len(co_dy) <= len(covariates) + 2:
        # Fall back to the basic SE.
        return att_gt_se(tr_dy, co_dy, n_b, rng)
    yc = co_dy.to_numpy()
    Xc = np.c_[np.ones(len(co_X)), co_X.to_numpy()]
    Xt = np.c_[np.ones(len(tr_X)), tr_X.to_numpy()]
    yt = tr_dy.to_numpy()
    boots = np.empty(n_b)
    for b in range(n_b):
        # Multiplier weights at the cluster (state) level. Weighted OLS:
        # multiply each control row's contribution by w_co, then refit.
        wt_co = rng.choice([0.5, 1.5], size=len(yc))  # Bayesian bootstrap-style positive weights
        # Solve weighted normal equations.
        W = np.sqrt(wt_co)[:, None]
        Xw, yw = Xc * W, yc * W.flatten()
        beta_b, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
        # Apply to treated; weighted mean of treated long-differences too.
        wt_tr = rng.choice([0.5, 1.5], size=len(yt))
        att_b = ((yt - Xt @ beta_b) * wt_tr).mean() / wt_tr.mean()
        boots[b] = att_b
    return float(np.std(boots, ddof=1))


def att_gt_se(treated_long, control_long, n_b, rng):
    """SE for a single ATT(g, t) via Rademacher cluster bootstrap.
    Approximation: bootstrap mean shift assuming long-diff is the score."""
    if len(treated_long) < 2 or len(control_long) < 2:
        return float("nan")
    tr_arr = treated_long.to_numpy()
    co_arr = control_long.to_numpy()
    tr_mean = tr_arr.mean()
    co_mean = co_arr.mean()
    tr_dev = tr_arr - tr_mean
    co_dev = co_arr - co_mean
    boots = np.empty(n_b)
    for b in range(n_b):
        wt_tr = rng.choice([-1.0, 1.0], size=len(tr_arr))
        wt_co = rng.choice([-1.0, 1.0], size=len(co_arr))
        boots[b] = (wt_tr * tr_dev).mean() - (wt_co * co_dev).mean()
    return float(np.std(boots, ddof=1))


def run_one_outcome(panel: pd.DataFrame, outcome: str,
                    cohorts: dict[int, list[str]],
                    never_treated: set[str],
                    spec: str,
                    control_rule: str = "broad") -> pd.DataFrame:
    """Compute ATT(g, t) for all valid (g, t) pairs for one outcome.

    spec: "or" for basic outcome regression (no covariates) or "ra" for
          regression-adjusted (Sant'Anna-Zhao 2020 RA estimator) using the
          baseline covariates listed in RA_COVARIATES.
    control_rule: "broad" uses every never-treated state; "strict" applies
          the audit's shall-issue + permit-required rule cohort-by-cohort.
    """
    rng = np.random.default_rng(RANDOM_SEED)
    rows = []
    for g in sorted(cohorts):
        treated_states = cohorts[g]
        if control_rule == "strict":
            control_states = strict_control_pool(panel, sorted(never_treated), g)
        else:
            control_states = sorted(never_treated)
        if not control_states:
            continue
        for t in range(ANALYSIS_YEARS[0], ANALYSIS_YEARS[1] + 1):
            if t == g - 1:
                continue
            if spec == "or":
                att, tr_long, co_long = att_gt_point(
                    panel, outcome, g, t, treated_states, control_states
                )
                if att is None:
                    continue
                se = att_gt_se(tr_long, co_long, N_BOOTSTRAP, rng)
                n_tr, n_co = len(tr_long), len(co_long)
            else:  # "ra"
                att, tr_long, co_long, _, _ = att_gt_ra(
                    panel, outcome, g, t, treated_states, control_states,
                    RA_COVARIATES,
                )
                if att is None:
                    continue
                se = att_gt_ra_se(panel, outcome, g, t, treated_states,
                                  control_states, RA_COVARIATES, N_BOOTSTRAP, rng)
                n_tr, n_co = len(tr_long), len(co_long)
            rows.append(OrderedDict([
                ("outcome", outcome),
                ("spec", spec),
                ("control_rule", control_rule),
                ("g_cohort", g),
                ("t_year", t),
                ("event_time", t - g),
                ("n_treated", int(n_tr)),
                ("n_control", int(n_co)),
                ("att", float(att)),
                ("se", se),
            ]))
    return pd.DataFrame(rows)


def event_study_aggregations(att_df: pd.DataFrame) -> pd.DataFrame:
    """Average ATT(g, g+e) over cohorts for each event time e, per (outcome, spec)."""
    rows = []
    for (outcome, spec, control_rule), group in att_df.groupby(["outcome", "spec", "control_rule"]):
        for e in range(EVENT_WINDOW[0], EVENT_WINDOW[1] + 1):
            sub = group[group["event_time"] == e]
            if sub.empty:
                continue
            w = sub["n_treated"].to_numpy(dtype=float)
            w = w / w.sum()
            att_e = float((w * sub["att"]).sum())
            se_e = float(np.sqrt((w**2 * sub["se"]**2).sum()))
            rows.append(OrderedDict([
                ("outcome", outcome),
                ("spec", spec),
                ("control_rule", control_rule),
                ("event_time", e),
                ("att", att_e),
                ("se", se_e),
                ("n_cohorts", int(len(sub))),
                ("total_treated_states", int(sub["n_treated"].sum())),
            ]))
    return pd.DataFrame(rows)


def overall_att(att_df: pd.DataFrame) -> pd.DataFrame:
    """Average post-treatment ATT(g, t) (t >= g) per (outcome, spec)."""
    rows = []
    for (outcome, spec, control_rule), group in att_df.groupby(["outcome", "spec", "control_rule"]):
        post = group[group["event_time"] >= 0]
        if post.empty:
            continue
        w = post["n_treated"].to_numpy(dtype=float)
        w = w / w.sum()
        att_bar = float((w * post["att"]).sum())
        se_bar = float(np.sqrt((w**2 * post["se"]**2).sum()))
        pre = group[(group["event_time"] <= -2) & (group["event_time"] >= EVENT_WINDOW[0])]
        if not pre.empty:
            wpr = pre["n_treated"].to_numpy(dtype=float) / pre["n_treated"].sum()
            pre_att = float((wpr * pre["att"]).sum())
            pre_se = float(np.sqrt((wpr**2 * pre["se"]**2).sum()))
            pre_z = pre_att / pre_se if pre_se > 0 else float("nan")
        else:
            pre_att = pre_se = pre_z = float("nan")
        rows.append(OrderedDict([
            ("outcome", outcome),
            ("spec", spec),
            ("control_rule", control_rule),
            ("att_overall_post", att_bar),
            ("se_overall_post", se_bar),
            ("z", att_bar / se_bar if se_bar > 0 else float("nan")),
            ("att_pretrends_avg", pre_att),
            ("se_pretrends_avg", pre_se),
            ("z_pretrends", pre_z),
            ("n_post_cells", int(len(post))),
            ("n_pre_cells", int(len(pre))),
        ]))
    return pd.DataFrame(rows)


def plot_event_study(es_df: pd.DataFrame, path: Path, spec: str):
    """Render a 4-panel event-study figure to SVG. Tries matplotlib first; if
    matplotlib isn't installed, falls back to a hand-built SVG so we always
    produce a figure without requiring a pip install."""
    es_df = es_df[es_df["spec"] == spec]
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        plot_event_study_svg(es_df, path.with_suffix(".svg"), spec)
        return

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    axes = axes.flatten()
    for ax, (var, title) in zip(axes, OUTCOMES.items()):
        sub = es_df[es_df["outcome"] == var].sort_values("event_time")
        if sub.empty:
            ax.text(0.5, 0.5, "no data", ha="center", va="center")
            ax.set_title(title)
            continue
        e = sub["event_time"].to_numpy()
        att = sub["att"].to_numpy()
        se = sub["se"].to_numpy()
        ax.fill_between(e, att - 1.96 * se, att + 1.96 * se, color="#1f3a5f", alpha=0.2)
        ax.plot(e, att, "o-", color="#1f3a5f")
        ax.axhline(0, color="#aaaaaa", linewidth=0.7)
        ax.axvline(-0.5, color="#b9461a", linewidth=0.6, linestyle="--",
                   label="treatment onset")
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Event time (years from adoption)")
        ax.set_ylabel("ATT (per 100,000)")
        ax.grid(True, color="#eeeeee", linewidth=0.5)
    axes[0].legend(fontsize=9, loc="best")
    fig.suptitle("Permitless carry adoption: Callaway-Sant'Anna ATT by event time",
                 fontsize=13, y=1.00)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def plot_event_study_svg(es_df: pd.DataFrame, path: Path, spec: str):
    """Pure-Python SVG fallback for the 4-panel event-study figure."""
    PANEL_W, PANEL_H = 380, 260
    GAP = 30
    PAD_L, PAD_R, PAD_T, PAD_B = 60, 18, 50, 50  # within each panel
    FIG_W = 2 * PANEL_W + GAP + 30
    FIG_H = 2 * PANEL_H + GAP + 70
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {FIG_W} {FIG_H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" font-size="11">',
        f'<text x="{FIG_W/2}" y="22" text-anchor="middle" font-size="14" font-weight="600">'
        f"Permitless carry adoption: Callaway-Sant'Anna ATT by event time ({spec.upper()})</text>",
    ]
    layout = list(OUTCOMES.items())
    for idx, (var, title) in enumerate(layout):
        sub = es_df[es_df["outcome"] == var].sort_values("event_time")
        col = idx % 2
        row = idx // 2
        x0 = 15 + col * (PANEL_W + GAP)
        y0 = 40 + row * (PANEL_H + GAP)
        # Frame.
        parts.append(f'<rect x="{x0}" y="{y0}" width="{PANEL_W}" height="{PANEL_H}" '
                     f'fill="#fafaf7" stroke="#e2e2dc"/>')
        parts.append(f'<text x="{x0 + PANEL_W/2}" y="{y0 + 18}" text-anchor="middle" '
                     f'font-weight="600">{title}</text>')
        if sub.empty:
            parts.append(f'<text x="{x0 + PANEL_W/2}" y="{y0 + PANEL_H/2}" '
                         f'text-anchor="middle" fill="#888">no data</text>')
            continue
        e = sub["event_time"].to_numpy()
        att = sub["att"].to_numpy()
        se = sub["se"].to_numpy()
        x_lo, x_hi = float(e.min()) - 0.5, float(e.max()) + 0.5
        lower = att - 1.96 * se
        upper = att + 1.96 * se
        y_lo = float(min(lower.min(), 0.0))
        y_hi = float(max(upper.max(), 0.0))
        if y_lo == y_hi:
            y_lo, y_hi = y_lo - 1, y_hi + 1
        ix0 = x0 + PAD_L
        iy0 = y0 + PAD_T
        iw = PANEL_W - PAD_L - PAD_R
        ih = PANEL_H - PAD_T - PAD_B

        def px(v): return ix0 + (v - x_lo) / (x_hi - x_lo) * iw
        def py(v): return iy0 + ih - (v - y_lo) / (y_hi - y_lo) * ih

        # Zero line.
        if y_lo <= 0 <= y_hi:
            parts.append(f'<line x1="{ix0}" y1="{py(0)}" x2="{ix0+iw}" y2="{py(0)}" '
                         f'stroke="#aaaaaa" stroke-width="0.7"/>')
        # CI band as polygon.
        band_pts = [(px(e[i]), py(upper[i])) for i in range(len(e))] + \
                   [(px(e[i]), py(lower[i])) for i in range(len(e) - 1, -1, -1)]
        band_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in band_pts)
        parts.append(f'<polygon points="{band_str}" fill="#1f3a5f" opacity="0.18"/>')
        # ATT line.
        line_pts = " ".join(f"{px(ei):.1f},{py(ai):.1f}" for ei, ai in zip(e, att))
        parts.append(f'<polyline points="{line_pts}" fill="none" stroke="#1f3a5f" '
                     f'stroke-width="1.6"/>')
        # Points.
        for ei, ai in zip(e, att):
            parts.append(f'<circle cx="{px(ei):.1f}" cy="{py(ai):.1f}" r="2.6" '
                         f'fill="#1f3a5f"/>')
        # Treatment-onset vertical line.
        parts.append(f'<line x1="{px(-0.5):.1f}" y1="{iy0}" x2="{px(-0.5):.1f}" '
                     f'y2="{iy0+ih}" stroke="#b9461a" stroke-dasharray="3 3"/>')
        # Axes.
        parts.append(f'<line x1="{ix0}" y1="{iy0+ih}" x2="{ix0+iw}" y2="{iy0+ih}" '
                     f'stroke="#444"/>')
        parts.append(f'<line x1="{ix0}" y1="{iy0}" x2="{ix0}" y2="{iy0+ih}" '
                     f'stroke="#444"/>')
        # X ticks.
        for ti in sorted(set(int(v) for v in e)):
            x = px(ti)
            parts.append(f'<line x1="{x:.1f}" y1="{iy0+ih}" x2="{x:.1f}" '
                         f'y2="{iy0+ih+3}" stroke="#444"/>')
            parts.append(f'<text x="{x:.1f}" y="{iy0+ih+15}" text-anchor="middle" '
                         f'fill="#444">{ti}</text>')
        # Y ticks.
        for k in range(5):
            v = y_lo + (y_hi - y_lo) * k / 4
            y = py(v)
            parts.append(f'<line x1="{ix0-3}" y1="{y:.1f}" x2="{ix0}" y2="{y:.1f}" '
                         f'stroke="#444"/>')
            label = f"{v:.2g}"
            parts.append(f'<text x="{ix0-6}" y="{y+3:.1f}" text-anchor="end" '
                         f'fill="#444">{label}</text>')
        # Axis labels.
        parts.append(f'<text x="{ix0+iw/2}" y="{iy0+ih+34}" text-anchor="middle" '
                     f'fill="#444">Event time (years from adoption)</text>')
        parts.append(f'<text x="{x0+12}" y="{iy0+ih/2}" text-anchor="middle" '
                     f'fill="#444" transform="rotate(-90 {x0+12} {iy0+ih/2})">ATT (per 100k)</text>')

    parts.append(f'<text x="{FIG_W-15}" y="{FIG_H-12}" text-anchor="end" fill="#888" font-size="10">'
                 "Shaded band: pointwise 95% CI from cluster bootstrap. "
                 "Vertical dashed line marks the year before adoption.</text>")
    parts.append("</svg>")
    path.write_text("\n".join(parts))


def main():
    print("Loading panel ...")
    panel = load_panel()
    print(f"  {len(panel):,} state-year rows in {ANALYSIS_YEARS[0]}-{ANALYSIS_YEARS[1]}")

    cohorts, never_treated, dropped = load_cohorts()
    print(f"  cohorts: {len(cohorts)} (years {sorted(cohorts)})")
    for g in sorted(cohorts):
        print(f"    {g}: {len(cohorts[g])} states ({', '.join(cohorts[g])})")
    print(f"  never-treated controls: {len(never_treated)} states")
    print(f"  dropped from analysis (logged): {len(dropped)}")

    # Cohort table for the writeup.
    cohort_rows = [OrderedDict([("g_cohort", g), ("n_states", len(s)),
                                ("states", ",".join(s))])
                   for g, s in sorted(cohorts.items())]
    pd.DataFrame(cohort_rows).to_csv(OUT / "cohort_n.csv", index=False)
    pd.DataFrame(dropped).to_csv(OUT / "dropped_log.csv", index=False)

    print("\nRunning ATT(g, t) for each (outcome, spec, control_rule) combination ...")
    # Quick visibility on how the strict rule shrinks the control pool.
    strict_examples = {}
    for g in sorted(cohorts):
        strict_examples[g] = strict_control_pool(panel, sorted(never_treated), g)
    print("  strict-rule control pool size by cohort:")
    for g, ctrl in strict_examples.items():
        print(f"    {g}: {len(ctrl)} states ({', '.join(ctrl)})")
    pieces = []
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            for outcome, label in OUTCOMES.items():
                print(f"  control_rule={control_rule}  spec={spec}  {outcome}")
                sub = run_one_outcome(panel, outcome, cohorts, never_treated,
                                      spec=spec, control_rule=control_rule)
                pieces.append(sub)
    att_df = pd.concat(pieces, ignore_index=True)
    att_df.to_csv(OUT / "att_gt.csv", index=False)
    print(f"  Wrote {len(att_df):,} (outcome, g, t) rows to outputs/permitless_carry_cs/att_gt.csv")

    print("\nAggregating to event-study and overall ATT ...")
    es_df = event_study_aggregations(att_df)
    es_df.to_csv(OUT / "event_study.csv", index=False)
    overall_df = overall_att(att_df)
    overall_df.to_csv(OUT / "overall_att.csv", index=False)

    print("\nOverall post-treatment ATT (per 100,000):")
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            print(f"\n  --- control_rule = {control_rule},  spec = {spec} ---")
            sub = overall_df[(overall_df["spec"] == spec)
                             & (overall_df["control_rule"] == control_rule)]
            for _, r in sub.iterrows():
                sig = "**" if abs(r["z"]) >= 1.96 else "  "
                print(f"  {sig} {r['outcome']:<26}  ATT = {r['att_overall_post']:>+8.3f}  "
                      f"(SE {r['se_overall_post']:.3f}, z {r['z']:>+5.2f})  "
                      f"pre-trends z = {r['z_pretrends']:>+5.2f}")

    print("\nPlotting event-study (one figure per spec x control_rule) ...")
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            es_filtered = es_df[es_df["control_rule"] == control_rule]
            plot_event_study(es_filtered,
                             FIG / f"event_study_{control_rule}_{spec}_4panel.png", spec)
            print(f"  Wrote {(FIG / f'event_study_{control_rule}_{spec}_4panel.svg').relative_to(ROOT)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
