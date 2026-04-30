"""Shared Callaway-Sant'Anna ATT(g, t) machinery used by per-policy runners
(scripts/run_cs_permitless_carry.py, scripts/run_cs_red_flag.py, ...).

Pure Python, only depends on numpy + pandas. No econometrics packages.

Public API:

    OUTCOMES                 ordered dict of outcome variable -> display label
    ANALYSIS_YEARS           panel window
    EVENT_WINDOW             event-time bounds for aggregation/figures
    N_BOOTSTRAP              cluster-bootstrap reps
    RANDOM_SEED              shared RNG seed
    RA_COVARIATES            covariates for RA spec
    STRICT_WINDOW            event window used by the strict control rule

    load_panel_core_augmented()                        DataFrame
    long_diff(panel, outcome, states, year_t, year_b)  Series

    derive_cohorts(panel, treatment_var, direction,    -> (cohorts, never_treated, dropped)
                   min_pre_k=5, exclude_after=None)

    strict_control_pool(panel, candidates, g,
                        rule_vars=("permitconcealed", "mayissue"),
                        rule_values=(1, 0))            -> list[str]

    run_one_outcome(panel, outcome, cohorts, never_treated,
                    spec, control_rule,
                    strict_rule_vars=..., strict_rule_values=...)  -> DataFrame

    event_study_aggregations(att_df)                   DataFrame
    overall_att(att_df)                                DataFrame

    plot_event_study(es_df, path, spec, outcomes_dict, title_suffix="")

    Plus the SVG fallback used inside plot_event_study when matplotlib is missing.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"

ANALYSIS_YEARS = (1999, 2023)
EVENT_WINDOW = (-5, 5)
N_BOOTSTRAP = 2000
RANDOM_SEED = 7
RA_COVARIATES = ["ln_population", "unemployment_rate", "ln_pcpi_real_2024"]
STRICT_WINDOW = (-5, 5)

OUTCOMES = OrderedDict([
    ("firearm_suicide_rate",      "Firearm suicide rate (per 100k)"),
    ("firearm_homicide_rate",     "Firearm homicide rate (per 100k)"),
    ("homicide_rate",             "Total homicide rate (per 100k)"),
    ("motor_vehicle_theft_rate",  "Motor vehicle theft rate (per 100k) [placebo]"),
])


# ----------- panel loading + cohort derivation --------------------------

def load_panel_core_augmented() -> pd.DataFrame:
    df = pd.read_csv(PROC / "panel_core_augmented.csv")
    df = df[(df["year"] >= ANALYSIS_YEARS[0]) & (df["year"] <= ANALYSIS_YEARS[1])]
    df = df[df["state_abbr"] != "DC"]
    return df.reset_index(drop=True)


def derive_cohorts(panel: pd.DataFrame,
                   treatment_var: str,
                   direction: str,
                   min_pre_k: int = 5,
                   exclude_after: int | None = None):
    """Build cohorts from a Tufts policy variable.

    direction: "0to1" if treatment is the first year the variable goes from
               0 to 1 (e.g., adopting a new restriction); "1to0" if the
               first year it goes from 1 to 0 (e.g., dropping a permit
               requirement).

    exclude_after: if set, drop cohorts whose adoption year is greater than
                   this (use to align with outcomes whose latest year is
                   earlier than ANALYSIS_YEARS[1]).

    Returns:
        cohorts: { adoption_year (int) : list of state abbreviations }
        never_treated: set of state abbreviations that never switch
        dropped: list of OrderedDict explaining drops
    """
    cohorts: dict[int, list[str]] = {}
    notes: list[OrderedDict] = []
    never_treated: set[str] = set()

    for state, group in panel.sort_values(["state_abbr", "year"]).groupby("state_abbr"):
        prev = None
        adoption_year = None
        for _, r in group.iterrows():
            v = r[treatment_var]
            if pd.isna(v):
                continue
            if prev is not None:
                if direction == "0to1" and prev == 0 and v == 1:
                    adoption_year = int(r["year"])
                    break
                if direction == "1to0" and prev == 1 and v == 0:
                    adoption_year = int(r["year"])
                    break
            prev = v
        if adoption_year is None:
            never_treated.add(state)
            continue
        if exclude_after is not None and adoption_year > exclude_after:
            notes.append(OrderedDict([("state_abbr", state),
                                      ("adoption_year", adoption_year),
                                      ("dropped_reason",
                                       f"adoption year > exclude_after={exclude_after}")]))
            continue
        if adoption_year - min_pre_k < ANALYSIS_YEARS[0]:
            notes.append(OrderedDict([("state_abbr", state),
                                      ("adoption_year", adoption_year),
                                      ("dropped_reason",
                                       f"adoption {adoption_year} too early for {min_pre_k}-yr pre-period in {ANALYSIS_YEARS[0]}+")]))
            continue
        cohorts.setdefault(adoption_year, []).append(state)
    return cohorts, never_treated, notes


def strict_control_pool(panel: pd.DataFrame,
                        candidates: list[str], g: int,
                        rule_vars=("permitconcealed", "mayissue"),
                        rule_values=(1, 0)) -> list[str]:
    """Filter candidates to those satisfying every rule_var == rule_value
    for every year in [g + STRICT_WINDOW[0], g + STRICT_WINDOW[1]]."""
    lo = g + STRICT_WINDOW[0]
    hi = g + STRICT_WINDOW[1]
    out = []
    for s in candidates:
        sub = panel[(panel["state_abbr"] == s)
                    & (panel["year"] >= lo) & (panel["year"] <= hi)]
        if sub.empty:
            continue
        ok = True
        for var, val in zip(rule_vars, rule_values):
            if not (sub[var] == val).all():
                ok = False
                break
        if ok:
            out.append(s)
    return out


# ----------- ATT(g, t) machinery ----------------------------------------

def long_diff(panel: pd.DataFrame, outcome: str,
              states: list[str], year_t: int, year_b: int) -> pd.Series:
    sub = panel[panel["state_abbr"].isin(states) & panel["year"].isin([year_t, year_b])]
    if sub.empty:
        return pd.Series(dtype=float)
    pv = sub.pivot(index="state_abbr", columns="year", values=outcome)
    if year_t not in pv.columns or year_b not in pv.columns:
        return pd.Series(dtype=float)
    return (pv[year_t] - pv[year_b]).dropna()


def att_gt_point(panel, outcome, g, t, treated_states, control_states):
    base = g - 1
    tr = long_diff(panel, outcome, treated_states, t, base)
    co = long_diff(panel, outcome, control_states, t, base)
    if len(tr) == 0 or len(co) == 0:
        return None, tr, co
    return tr.mean() - co.mean(), tr, co


def att_gt_se(treated_long, control_long, n_b, rng):
    if len(treated_long) < 2 or len(control_long) < 2:
        return float("nan")
    tr_arr = treated_long.to_numpy()
    co_arr = control_long.to_numpy()
    tr_dev = tr_arr - tr_arr.mean()
    co_dev = co_arr - co_arr.mean()
    boots = np.empty(n_b)
    for b in range(n_b):
        wt_tr = rng.choice([-1.0, 1.0], size=len(tr_arr))
        wt_co = rng.choice([-1.0, 1.0], size=len(co_arr))
        boots[b] = (wt_tr * tr_dev).mean() - (wt_co * co_dev).mean()
    return float(np.std(boots, ddof=1))


def _baseline_X(panel, states, year_b, covariates):
    sub = panel[panel["state_abbr"].isin(states) & (panel["year"] == year_b)]
    return sub.set_index("state_abbr")[covariates].dropna()


def att_gt_ra(panel, outcome, g, t, treated_states, control_states, covariates):
    base = g - 1
    tr_dy = long_diff(panel, outcome, treated_states, t, base)
    co_dy = long_diff(panel, outcome, control_states, t, base)
    if len(tr_dy) == 0 or len(co_dy) == 0:
        return None, tr_dy, co_dy
    tr_X = _baseline_X(panel, treated_states, base, covariates)
    co_X = _baseline_X(panel, control_states, base, covariates)
    tr_dy = tr_dy.loc[tr_dy.index.intersection(tr_X.index)]
    co_dy = co_dy.loc[co_dy.index.intersection(co_X.index)]
    tr_X = tr_X.loc[tr_dy.index]
    co_X = co_X.loc[co_dy.index]
    if len(co_dy) <= len(covariates) + 2:
        att, _, _ = att_gt_point(panel, outcome, g, t, treated_states, control_states)
        return att, tr_dy, co_dy
    Xc = np.c_[np.ones(len(co_X)), co_X.to_numpy()]
    yc = co_dy.to_numpy()
    beta, *_ = np.linalg.lstsq(Xc, yc, rcond=None)
    Xt = np.c_[np.ones(len(tr_X)), tr_X.to_numpy()]
    tr_pred = Xt @ beta
    return float(tr_dy.to_numpy().mean() - tr_pred.mean()), tr_dy, co_dy


def att_gt_ra_se(panel, outcome, g, t, treated_states, control_states,
                 covariates, n_b, rng):
    base = g - 1
    tr_dy = long_diff(panel, outcome, treated_states, t, base)
    co_dy = long_diff(panel, outcome, control_states, t, base)
    if len(tr_dy) < 2 or len(co_dy) < 2:
        return float("nan")
    tr_X = _baseline_X(panel, treated_states, base, covariates)
    co_X = _baseline_X(panel, control_states, base, covariates)
    tr_dy = tr_dy.loc[tr_dy.index.intersection(tr_X.index)]
    co_dy = co_dy.loc[co_dy.index.intersection(co_X.index)]
    tr_X = tr_X.loc[tr_dy.index]
    co_X = co_X.loc[co_dy.index]
    if len(co_dy) <= len(covariates) + 2:
        return att_gt_se(tr_dy, co_dy, n_b, rng)
    yc = co_dy.to_numpy()
    Xc = np.c_[np.ones(len(co_X)), co_X.to_numpy()]
    Xt = np.c_[np.ones(len(tr_X)), tr_X.to_numpy()]
    yt = tr_dy.to_numpy()
    boots = np.empty(n_b)
    for b in range(n_b):
        wt_co = rng.choice([0.5, 1.5], size=len(yc))
        W = np.sqrt(wt_co)[:, None]
        beta_b, *_ = np.linalg.lstsq(Xc * W, yc * W.flatten(), rcond=None)
        wt_tr = rng.choice([0.5, 1.5], size=len(yt))
        boots[b] = ((yt - Xt @ beta_b) * wt_tr).mean() / wt_tr.mean()
    return float(np.std(boots, ddof=1))


def run_one_outcome(panel, outcome, cohorts, never_treated,
                    spec, control_rule,
                    strict_rule_vars=("permitconcealed", "mayissue"),
                    strict_rule_values=(1, 0)):
    rng = np.random.default_rng(RANDOM_SEED)
    rows = []
    for g in sorted(cohorts):
        treated_states = cohorts[g]
        if control_rule == "strict":
            control_states = strict_control_pool(panel, sorted(never_treated), g,
                                                 strict_rule_vars, strict_rule_values)
        else:
            control_states = sorted(never_treated)
        if not control_states:
            continue
        for t in range(ANALYSIS_YEARS[0], ANALYSIS_YEARS[1] + 1):
            if t == g - 1:
                continue
            if spec == "or":
                att, tr, co = att_gt_point(panel, outcome, g, t,
                                           treated_states, control_states)
                if att is None:
                    continue
                se = att_gt_se(tr, co, N_BOOTSTRAP, rng)
            else:
                att, tr, co = att_gt_ra(panel, outcome, g, t,
                                        treated_states, control_states,
                                        RA_COVARIATES)
                if att is None:
                    continue
                se = att_gt_ra_se(panel, outcome, g, t, treated_states,
                                  control_states, RA_COVARIATES, N_BOOTSTRAP, rng)
            rows.append(OrderedDict([
                ("outcome", outcome),
                ("spec", spec),
                ("control_rule", control_rule),
                ("g_cohort", g),
                ("t_year", t),
                ("event_time", t - g),
                ("n_treated", int(len(tr))),
                ("n_control", int(len(co))),
                ("att", float(att)),
                ("se", se),
            ]))
    return pd.DataFrame(rows)


# ----------- Aggregations -----------------------------------------------

def event_study_aggregations(att_df):
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
                ("outcome", outcome), ("spec", spec), ("control_rule", control_rule),
                ("event_time", e), ("att", att_e), ("se", se_e),
                ("n_cohorts", int(len(sub))),
                ("total_treated_states", int(sub["n_treated"].sum())),
            ]))
    return pd.DataFrame(rows)


def overall_att(att_df):
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
            ("outcome", outcome), ("spec", spec), ("control_rule", control_rule),
            ("att_overall_post", att_bar), ("se_overall_post", se_bar),
            ("z", att_bar / se_bar if se_bar > 0 else float("nan")),
            ("att_pretrends_avg", pre_att),
            ("se_pretrends_avg", pre_se),
            ("z_pretrends", pre_z),
            ("n_post_cells", int(len(post))),
            ("n_pre_cells", int(len(pre))),
        ]))
    return pd.DataFrame(rows)


# ----------- SVG figure (matplotlib-free fallback) ----------------------

def plot_event_study(es_df, path, spec, outcomes_dict, title_suffix=""):
    es_df = es_df[es_df["spec"] == spec]
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        plot_event_study_svg(es_df, path.with_suffix(".svg"), spec,
                             outcomes_dict, title_suffix)
        return
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    axes = axes.flatten()
    for ax, (var, title) in zip(axes, outcomes_dict.items()):
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
        ax.set_xlabel("Event time")
        ax.set_ylabel("ATT (per 100,000)")
        ax.grid(True, color="#eeeeee", linewidth=0.5)
    axes[0].legend(fontsize=9, loc="best")
    fig.suptitle(f"Callaway-Sant'Anna ATT by event time ({spec.upper()}) {title_suffix}".strip(),
                 fontsize=13, y=1.00)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def plot_event_study_svg(es_df, path, spec, outcomes_dict, title_suffix=""):
    PANEL_W, PANEL_H = 380, 260
    GAP = 30
    PAD_L, PAD_R, PAD_T, PAD_B = 60, 18, 50, 50
    FIG_W = 2 * PANEL_W + GAP + 30
    FIG_H = 2 * PANEL_H + GAP + 70
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {FIG_W} {FIG_H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" font-size="11">',
        f'<text x="{FIG_W/2}" y="22" text-anchor="middle" font-size="14" font-weight="600">'
        f"Callaway-Sant'Anna ATT by event time ({spec.upper()}) {title_suffix}</text>",
    ]
    layout = list(outcomes_dict.items())
    for idx, (var, title) in enumerate(layout):
        sub = es_df[es_df["outcome"] == var].sort_values("event_time")
        col = idx % 2
        row = idx // 2
        x0 = 15 + col * (PANEL_W + GAP)
        y0 = 40 + row * (PANEL_H + GAP)
        parts.append(f'<rect x="{x0}" y="{y0}" width="{PANEL_W}" height="{PANEL_H}" fill="#fafaf7" stroke="#e2e2dc"/>')
        parts.append(f'<text x="{x0 + PANEL_W/2}" y="{y0 + 18}" text-anchor="middle" font-weight="600">{title}</text>')
        if sub.empty:
            parts.append(f'<text x="{x0 + PANEL_W/2}" y="{y0 + PANEL_H/2}" text-anchor="middle" fill="#888">no data</text>')
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
        if y_lo <= 0 <= y_hi:
            parts.append(f'<line x1="{ix0}" y1="{py(0)}" x2="{ix0+iw}" y2="{py(0)}" stroke="#aaaaaa" stroke-width="0.7"/>')
        band_pts = [(px(e[i]), py(upper[i])) for i in range(len(e))] + \
                   [(px(e[i]), py(lower[i])) for i in range(len(e) - 1, -1, -1)]
        band_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in band_pts)
        parts.append(f'<polygon points="{band_str}" fill="#1f3a5f" opacity="0.18"/>')
        line_pts = " ".join(f"{px(ei):.1f},{py(ai):.1f}" for ei, ai in zip(e, att))
        parts.append(f'<polyline points="{line_pts}" fill="none" stroke="#1f3a5f" stroke-width="1.6"/>')
        for ei, ai in zip(e, att):
            parts.append(f'<circle cx="{px(ei):.1f}" cy="{py(ai):.1f}" r="2.6" fill="#1f3a5f"/>')
        parts.append(f'<line x1="{px(-0.5):.1f}" y1="{iy0}" x2="{px(-0.5):.1f}" y2="{iy0+ih}" stroke="#b9461a" stroke-dasharray="3 3"/>')
        parts.append(f'<line x1="{ix0}" y1="{iy0+ih}" x2="{ix0+iw}" y2="{iy0+ih}" stroke="#444"/>')
        parts.append(f'<line x1="{ix0}" y1="{iy0}" x2="{ix0}" y2="{iy0+ih}" stroke="#444"/>')
        for ti in sorted(set(int(v) for v in e)):
            x = px(ti)
            parts.append(f'<line x1="{x:.1f}" y1="{iy0+ih}" x2="{x:.1f}" y2="{iy0+ih+3}" stroke="#444"/>')
            parts.append(f'<text x="{x:.1f}" y="{iy0+ih+15}" text-anchor="middle" fill="#444">{ti}</text>')
        for k in range(5):
            v = y_lo + (y_hi - y_lo) * k / 4
            y = py(v)
            parts.append(f'<line x1="{ix0-3}" y1="{y:.1f}" x2="{ix0}" y2="{y:.1f}" stroke="#444"/>')
            parts.append(f'<text x="{ix0-6}" y="{y+3:.1f}" text-anchor="end" fill="#444">{v:.2g}</text>')
        parts.append(f'<text x="{ix0+iw/2}" y="{iy0+ih+34}" text-anchor="middle" fill="#444">Event time (years from adoption)</text>')
        parts.append(f'<text x="{x0+12}" y="{iy0+ih/2}" text-anchor="middle" fill="#444" transform="rotate(-90 {x0+12} {iy0+ih/2})">ATT (per 100k)</text>')
    parts.append(f'<text x="{FIG_W-15}" y="{FIG_H-12}" text-anchor="end" fill="#888" font-size="10">Shaded band: pointwise 95% CI from cluster bootstrap. Vertical dashed line marks the year before adoption.</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts))
