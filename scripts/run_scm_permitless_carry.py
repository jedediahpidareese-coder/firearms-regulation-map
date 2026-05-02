"""Phase 5d: Synthetic control for individual large permitless-carry adopters.

Two case studies:
  - Texas, 2021 (largest single state in the 2021 cohort; pre-window 2009-2020,
    post-window 2021-2023 = 3 years)
  - Florida, 2023 (post-window is just 2023 = 1 year, but FL is the second
    biggest single-state adoption and the most recent one with any post-data)

Optional flags:
  --with-covid    adds the OxCGRT covid_stringency_mean for the in-window
                  pandemic year(s) as additional pre-period predictors in
                  the SCM weight optimization; output goes to
                  outputs/permitless_carry_scm_with_covid/.
  --with-efna     adds the Fraser Institute efna_overall index for ALL
                  pre-period years as additional pre-period predictors
                  (EFNA varies across the entire pre-period, not just
                  during the pandemic). Combined with --with-covid the
                  output goes to permitless_carry_scm_with_covid_efna/;
                  alone, permitless_carry_scm_with_efna/.
  --with-despair  adds the deaths-of-despair stack
                  (synthetic_opioid_death_rate, freq_mental_distress_pct,
                  ami_pct) as additional pre-period predictors. The
                  predictors enter only for the post-2014 pre-period
                  years where they are observed; pre-2015 cells are
                  zero-fill in the build script and are skipped.
                  Combinable with --with-covid and --with-efna; maximal
                  output is permitless_carry_scm_with_covid_efna_despair/.

For each state and each of our four outcomes:
  1. Donor pool = never-treated states that are shall-issue (mayissue==0) AND
     permit-required (permitconcealed==1) for EVERY year of the pre+post
     window (so the pool is fixed across time, as SCM requires).
  2. Fit SCM weights w >= 0, sum(w) = 1 to minimize pre-period MSE between
     the treated state and the synthetic Sum_j w_j * y_j.
  3. Compute the synthetic trajectory across pre+post, the per-year
     treatment effect Y_treated - Y_synthetic, and the post-period average.
  4. Run a permutation-style placebo test: refit SCM on every donor state
     (treating each as if it were the 'treated' unit, with the rest of the
     pool as donors). Compare the actual post-period effect's magnitude to
     the placebo distribution to get a one-sided p-value.

Outputs:
  outputs/permitless_carry_scm/{TX_2021,FL_2023}/
    weights.csv            donor weights per outcome
    trajectories.csv       year-by-year actual, synthetic, and effect
    placebo.csv            permutation test results
    figures/{outcome}.svg  pure-Python SVG figure (actual vs synthetic, with
                           placebo distribution as gray lines)
  outputs/permitless_carry_scm/methodology.md
"""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
ADO_TABLE = ROOT / "outputs" / "permitless_carry_suicide_audit" / "treatment_adoption_table.csv"

ANALYSIS_YEARS = (1999, 2023)
PRE_YEARS_TARGET = 12   # how many years pre we'd like for the fit
OUTCOMES = OrderedDict([
    ("firearm_suicide_rate",      "Firearm suicide rate (per 100k)"),
    ("total_suicide_rate",        "Total suicide rate (per 100k) [net effect]"),
    ("firearm_homicide_rate",     "Firearm homicide rate (per 100k)"),
    ("homicide_rate",             "Total homicide rate (per 100k)"),
    ("motor_vehicle_theft_rate",  "Motor vehicle theft rate (per 100k) [placebo]"),
])

CASES = [
    {"state": "TX", "label": "Texas",   "g": 2021},
    {"state": "FL", "label": "Florida", "g": 2023},
]


def load_panel() -> pd.DataFrame:
    df = pd.read_csv(PROC / "panel_core_augmented.csv")
    df = df[(df["year"] >= ANALYSIS_YEARS[0]) & (df["year"] <= ANALYSIS_YEARS[1])]
    df = df[df["state_abbr"] != "DC"]
    return df.reset_index(drop=True)


def eligible_donors(panel: pd.DataFrame, treated_state: str, g: int) -> list[str]:
    """Donor pool for SCM around adoption year g.

    Rules (audit-style, fixed across time):
      - Not the treated state itself.
      - Never adopted permitless carry within the analysis window.
      - Shall-issue (mayissue == 0) AND permit-required (permitconcealed == 1)
        for EVERY year in [pre_start, ANALYSIS_YEARS[1]] where pre_start =
        max(g - PRE_YEARS_TARGET, ANALYSIS_YEARS[0]).
    """
    t = pd.read_csv(ADO_TABLE)
    never = set(t.loc[(t["adoption_year"].isna())
                       & (t["starts_permit_required"] == 1), "state_abbr"])
    pre_start = max(g - PRE_YEARS_TARGET, ANALYSIS_YEARS[0])
    out = []
    for s in sorted(never):
        if s == treated_state:
            continue
        sub = panel[(panel["state_abbr"] == s)
                    & (panel["year"] >= pre_start)
                    & (panel["year"] <= ANALYSIS_YEARS[1])]
        if sub.empty:
            continue
        if (sub["mayissue"] == 0).all() and (sub["permitconcealed"] == 1).all():
            out.append(s)
    return out


def fit_scm_weights(y_pre: np.ndarray, Y_pre: np.ndarray) -> np.ndarray:
    """Solve min ||y_pre - Y_pre @ w||^2 s.t. w >= 0, sum(w) = 1.

    y_pre: shape (T_pre,)
    Y_pre: shape (T_pre, J)  donor outcomes in the pre-period.
    Returns w: shape (J,)
    """
    J = Y_pre.shape[1]
    if J == 0:
        return np.zeros(0)
    def loss(w):
        r = y_pre - Y_pre @ w
        return float(r @ r)
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]
    bounds = [(0.0, 1.0)] * J
    # Multi-start to escape local optima of the simplex-constrained problem.
    best_w, best_loss = None, np.inf
    starts = [np.ones(J) / J]
    rng = np.random.default_rng(11)
    for _ in range(5):
        x = rng.dirichlet(np.ones(J))
        starts.append(x)
    for x0 in starts:
        res = minimize(loss, x0, method="SLSQP", bounds=bounds, constraints=cons,
                       options={"maxiter": 200, "ftol": 1e-9})
        if res.fun < best_loss:
            best_loss = res.fun
            best_w = res.x
    # Clip tiny negatives and renormalize.
    best_w = np.clip(best_w, 0, None)
    if best_w.sum() > 0:
        best_w = best_w / best_w.sum()
    return best_w


def run_one_case(panel: pd.DataFrame, case: dict, out_base: Path,
                 with_covid: bool = False, with_efna: bool = False,
                 with_despair: bool = False):
    state = case["state"]
    g = case["g"]
    case_dir = out_base / f"{state}_{g}"
    fig_dir = case_dir / "figures"
    case_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {state} ({case['label']}), adoption year g = {g} ===")

    donors = eligible_donors(panel, state, g)
    print(f"  donor pool ({len(donors)}): {', '.join(donors)}")
    pre_years = list(range(max(g - PRE_YEARS_TARGET, ANALYSIS_YEARS[0]), g))
    post_years = list(range(g, ANALYSIS_YEARS[1] + 1))
    all_years = pre_years + post_years

    weights_rows = []
    traj_rows = []
    placebo_rows = []

    for outcome in OUTCOMES:
        # Build full-window matrix for the donor pool + treated.
        wide = (panel[panel["state_abbr"].isin([state] + donors)
                      & panel["year"].isin(all_years)]
                .pivot(index="year", columns="state_abbr", values=outcome))
        if state not in wide.columns:
            print(f"  [{outcome}] treated state missing data; skipping")
            continue
        # Drop donors with any missing values in the window.
        full_donors = [d for d in donors if wide[d].notna().all() and wide[d].count() == len(all_years)]
        if not full_donors:
            print(f"  [{outcome}] no donors with complete window; skipping")
            continue
        wide = wide.loc[all_years, [state] + full_donors]
        if wide[state].isna().any():
            print(f"  [{outcome}] treated has missing in window; skipping")
            continue

        # Fit on pre-period only.
        y_pre = wide.loc[pre_years, state].to_numpy(dtype=float)
        Y_pre = wide.loc[pre_years, full_donors].to_numpy(dtype=float)

        # COVID-robustness extension: append covid_stringency_mean for
        # the in-pre-period pandemic year(s) (2020 for TX_2021; 2020-2022
        # for FL_2023) as additional pre-period predictors.
        if with_covid:
            covid_pre_years = [y for y in pre_years if y >= 2020]
            if covid_pre_years and "covid_stringency_mean" in panel.columns:
                tr_covid = (panel[(panel["state_abbr"] == state)
                                  & panel["year"].isin(covid_pre_years)]
                            .set_index("year")["covid_stringency_mean"]
                            .reindex(covid_pre_years).fillna(0.0)
                            .to_numpy(dtype=float))
                donor_covid = []
                for d in full_donors:
                    dv = (panel[(panel["state_abbr"] == d)
                                & panel["year"].isin(covid_pre_years)]
                          .set_index("year")["covid_stringency_mean"]
                          .reindex(covid_pre_years).fillna(0.0)
                          .to_numpy(dtype=float))
                    donor_covid.append(dv)
                donor_covid = np.column_stack(donor_covid) if donor_covid else \
                              np.empty((len(covid_pre_years), 0))
                # Standardize covid scale to be comparable to outcome scale
                # (suicide rates ~10-25 per 100k; stringency ~0-100). Scale
                # by ratio of standard deviations of pre-period outcome
                # vs covid for this state.
                outcome_sd = float(np.std(y_pre, ddof=1)) if len(y_pre) > 1 else 1.0
                covid_sd = float(np.std(np.r_[tr_covid, donor_covid.flatten()], ddof=1)) \
                           if (len(tr_covid) + donor_covid.size) > 1 else 1.0
                if covid_sd > 1e-9:
                    scale = outcome_sd / covid_sd
                else:
                    scale = 1.0
                tr_covid_s = tr_covid * scale
                donor_covid_s = donor_covid * scale
                y_pre = np.concatenate([y_pre, tr_covid_s])
                Y_pre = np.vstack([Y_pre, donor_covid_s])

        # EFNA-robustness extension: unlike OxCGRT, EFNA varies across
        # all pre-period years, so we append efna_overall for the FULL
        # pre-period (1985-onward, observed annually). This forces the
        # synthetic counterfactual to track Texas's economic-freedom
        # trajectory across the entire pre-window.
        if with_efna and "efna_overall" in panel.columns:
            tr_efna = (panel[(panel["state_abbr"] == state)
                             & panel["year"].isin(pre_years)]
                       .set_index("year")["efna_overall"]
                       .reindex(pre_years).to_numpy(dtype=float))
            donor_efna = []
            for d in full_donors:
                dv = (panel[(panel["state_abbr"] == d)
                            & panel["year"].isin(pre_years)]
                      .set_index("year")["efna_overall"]
                      .reindex(pre_years).to_numpy(dtype=float))
                donor_efna.append(dv)
            donor_efna = np.column_stack(donor_efna) if donor_efna else \
                         np.empty((len(pre_years), 0))
            # Scale efna (range ~5-9) to be comparable to outcome scale.
            # Use the same ratio-of-SDs approach as COVID above.
            # Recompute outcome_sd from the OUTCOME-only portion of y_pre
            # in case --with-covid already appended COVID rows.
            outcome_only = y_pre[:len(pre_years)]
            outcome_sd_for_efna = float(np.std(outcome_only, ddof=1)) \
                                  if len(outcome_only) > 1 else 1.0
            efna_sd = float(np.std(np.r_[tr_efna,
                                         donor_efna.flatten()], ddof=1)) \
                      if (len(tr_efna) + donor_efna.size) > 1 else 1.0
            if efna_sd > 1e-9:
                escale = outcome_sd_for_efna / efna_sd
            else:
                escale = 1.0
            # NaN-safe: replace NaN in EFNA with column mean for the
            # state to avoid breaking the SCM optimizer; since EFNA is
            # forward-filled in build_efna, this should rarely fire.
            tr_efna = np.nan_to_num(tr_efna, nan=float(np.nanmean(tr_efna))
                                    if not np.all(np.isnan(tr_efna)) else 0.0)
            donor_efna = np.nan_to_num(donor_efna, nan=0.0)
            tr_efna_s = tr_efna * escale
            donor_efna_s = donor_efna * escale
            y_pre = np.concatenate([y_pre, tr_efna_s])
            Y_pre = np.vstack([Y_pre, donor_efna_s])

        w = fit_scm_weights(y_pre, Y_pre)

        # For trajectory plotting/effect computation, restrict back to
        # the outcome rows only (drop the appended covid rows).
        if with_covid and "covid_stringency_mean" in panel.columns:
            T_outcome = len(pre_years)
        else:
            T_outcome = len(pre_years)

        # Synthetic trajectory across full window.
        Y_full = wide.loc[all_years, full_donors].to_numpy(dtype=float)
        y_synth = Y_full @ w
        y_treated = wide.loc[all_years, state].to_numpy(dtype=float)

        for i, yr in enumerate(all_years):
            traj_rows.append(OrderedDict([
                ("outcome", outcome),
                ("year", yr),
                ("event_time", yr - g),
                ("y_treated", float(y_treated[i])),
                ("y_synthetic", float(y_synth[i])),
                ("effect", float(y_treated[i] - y_synth[i])),
            ]))

        # Save weights.
        for d, wt in zip(full_donors, w):
            if wt > 1e-4:
                weights_rows.append(OrderedDict([
                    ("outcome", outcome),
                    ("donor", d),
                    ("weight", float(wt)),
                ]))

        # Pre-period RMSE for context (compute on outcome-only rows).
        y_pre_outcome = y_pre[:T_outcome]
        Y_pre_outcome = Y_pre[:T_outcome, :]
        pre_rmse = float(np.sqrt(np.mean((y_pre_outcome - Y_pre_outcome @ w) ** 2)))
        print(f"  [{outcome}] pre-period RMSE = {pre_rmse:.4g}; "
              f"non-zero donors = {sum(w > 1e-4)}/{len(full_donors)}")

        # Permutation test: refit SCM on every donor as if treated.
        actual_post = float(np.mean(y_treated[len(pre_years):]
                                    - y_synth[len(pre_years):]))
        placebo_post = []
        for j, d in enumerate(full_donors):
            other = [k for k in range(len(full_donors)) if k != j]
            y_d_pre = Y_pre[:, j]
            Y_other_pre = Y_pre[:, other]
            if Y_other_pre.shape[1] == 0:
                continue
            w_p = fit_scm_weights(y_d_pre, Y_other_pre)
            y_d_full = Y_full[:, j]
            Y_other_full = Y_full[:, other]
            y_d_synth = Y_other_full @ w_p
            placebo_post.append(float(np.mean(y_d_full[len(pre_years):]
                                              - y_d_synth[len(pre_years):])))
        if placebo_post:
            placebo_arr = np.asarray(placebo_post)
            n = len(placebo_arr)
            # Two-sided rank: how many placebo |effects| are >= |actual|?
            p_two = float((np.abs(placebo_arr) >= np.abs(actual_post)).sum() / n)
            placebo_rows.append(OrderedDict([
                ("outcome", outcome),
                ("actual_post_effect", actual_post),
                ("n_placebo", n),
                ("placebo_mean", float(placebo_arr.mean())),
                ("placebo_sd", float(placebo_arr.std(ddof=1) if n > 1 else float("nan"))),
                ("p_value_two_sided", p_two),
            ]))

        # SVG figure for this outcome.
        plot_scm_svg(fig_dir / f"{outcome}.svg", outcome, OUTCOMES[outcome],
                     all_years, pre_years, g, y_treated, y_synth,
                     full_donors, Y_full, w_per_placebo=None,
                     case_label=case["label"])

    pd.DataFrame(weights_rows).to_csv(case_dir / "weights.csv", index=False)
    pd.DataFrame(traj_rows).to_csv(case_dir / "trajectories.csv", index=False)
    pd.DataFrame(placebo_rows).to_csv(case_dir / "placebo.csv", index=False)
    print(f"  Wrote {(case_dir / 'weights.csv').relative_to(ROOT)}")
    print(f"        {(case_dir / 'trajectories.csv').relative_to(ROOT)}")
    print(f"        {(case_dir / 'placebo.csv').relative_to(ROOT)}")

    # Print summary table.
    print(f"\n  --- {state} {g} per-outcome summary ---")
    pl = pd.DataFrame(placebo_rows)
    if not pl.empty:
        for _, r in pl.iterrows():
            sig = "**" if r["p_value_two_sided"] <= 0.10 else "  "
            print(f"  {sig} {r['outcome']:<26}  effect = {r['actual_post_effect']:>+8.3f}  "
                  f"placebo p = {r['p_value_two_sided']:.3f}  "
                  f"(placebo mean {r['placebo_mean']:>+7.3f}, sd {r['placebo_sd']:.3f})")


def plot_scm_svg(path: Path, outcome: str, label: str,
                 all_years, pre_years, g,
                 y_treated, y_synth,
                 donors, Y_full, w_per_placebo, case_label: str):
    W, H = 720, 380
    PAD_L, PAD_R, PAD_T, PAD_B = 60, 40, 50, 50
    iw = W - PAD_L - PAD_R
    ih = H - PAD_T - PAD_B
    x_lo, x_hi = float(min(all_years)), float(max(all_years))
    # y range: include treated, synthetic, and donor lines for context.
    y_lo = float(min(np.min(y_treated), np.min(y_synth), np.min(Y_full)))
    y_hi = float(max(np.max(y_treated), np.max(y_synth), np.max(Y_full)))
    if y_lo == y_hi:
        y_lo, y_hi = y_lo - 1, y_hi + 1
    pad = (y_hi - y_lo) * 0.05
    y_lo -= pad
    y_hi += pad

    def px(v): return PAD_L + (v - x_lo) / (x_hi - x_lo) * iw
    def py(v): return PAD_T + ih - (v - y_lo) / (y_hi - y_lo) * ih

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" font-size="12">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fafaf7"/>',
        f'<text x="{W/2}" y="22" text-anchor="middle" font-size="14" font-weight="600">'
        f'{case_label} ({g}): {label}</text>',
    ]
    # Faint donor lines for context (so reviewers can see the placebo distribution).
    for j in range(Y_full.shape[1]):
        pts = " ".join(f"{px(yr):.1f},{py(Y_full[i, j]):.1f}" for i, yr in enumerate(all_years))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="#bbb" '
                     f'stroke-width="0.6" opacity="0.6"/>')
    # Synthetic line (dashed).
    pts_synth = " ".join(f"{px(yr):.1f},{py(y_synth[i]):.1f}" for i, yr in enumerate(all_years))
    parts.append(f'<polyline points="{pts_synth}" fill="none" stroke="#1f3a5f" '
                 f'stroke-width="2" stroke-dasharray="6 4"/>')
    # Treated line (solid).
    pts_tr = " ".join(f"{px(yr):.1f},{py(y_treated[i]):.1f}" for i, yr in enumerate(all_years))
    parts.append(f'<polyline points="{pts_tr}" fill="none" stroke="#b9461a" '
                 f'stroke-width="2.4"/>')
    # Treatment line.
    parts.append(f'<line x1="{px(g - 0.5):.1f}" y1="{PAD_T}" '
                 f'x2="{px(g - 0.5):.1f}" y2="{PAD_T + ih}" '
                 f'stroke="#1f2024" stroke-width="0.8" stroke-dasharray="4 3"/>')
    parts.append(f'<text x="{px(g - 0.5):.1f}" y="{PAD_T - 5}" text-anchor="middle" '
                 f'fill="#1f2024" font-size="10">adoption ({g})</text>')
    # Axes.
    parts.append(f'<line x1="{PAD_L}" y1="{PAD_T+ih}" x2="{PAD_L+iw}" y2="{PAD_T+ih}" stroke="#444"/>')
    parts.append(f'<line x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{PAD_T+ih}" stroke="#444"/>')
    # X ticks.
    for yr in all_years:
        if (yr - all_years[0]) % 2 == 0:
            parts.append(f'<line x1="{px(yr):.1f}" y1="{PAD_T+ih}" x2="{px(yr):.1f}" y2="{PAD_T+ih+4}" stroke="#444"/>')
            parts.append(f'<text x="{px(yr):.1f}" y="{PAD_T+ih+18}" text-anchor="middle" fill="#444">{yr}</text>')
    # Y ticks.
    for k in range(5):
        v = y_lo + (y_hi - y_lo) * k / 4
        y = py(v)
        parts.append(f'<line x1="{PAD_L-4}" y1="{y:.1f}" x2="{PAD_L}" y2="{y:.1f}" stroke="#444"/>')
        parts.append(f'<text x="{PAD_L-7}" y="{y+3:.1f}" text-anchor="end" fill="#444">{v:.2g}</text>')
    # Legend.
    parts.append(f'<rect x="{W-200}" y="{PAD_T+10}" width="190" height="60" fill="white" stroke="#e2e2dc"/>')
    parts.append(f'<line x1="{W-190}" y1="{PAD_T+25}" x2="{W-160}" y2="{PAD_T+25}" stroke="#b9461a" stroke-width="2.4"/>')
    parts.append(f'<text x="{W-155}" y="{PAD_T+29}" font-size="11">{case_label} (treated)</text>')
    parts.append(f'<line x1="{W-190}" y1="{PAD_T+45}" x2="{W-160}" y2="{PAD_T+45}" stroke="#1f3a5f" stroke-width="2" stroke-dasharray="6 4"/>')
    parts.append(f'<text x="{W-155}" y="{PAD_T+49}" font-size="11">Synthetic counterfactual</text>')
    parts.append(f'<line x1="{W-190}" y1="{PAD_T+62}" x2="{W-160}" y2="{PAD_T+62}" stroke="#bbb" stroke-width="0.6"/>')
    parts.append(f'<text x="{W-155}" y="{PAD_T+66}" font-size="10">Donor states (gray)</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts))


def main(with_covid: bool = False, with_efna: bool = False,
         with_despair: bool = False):
    panel = load_panel()
    parts = []
    if with_covid: parts.append("covid")
    if with_efna: parts.append("efna")
    if with_despair: parts.append("despair")
    suffix = ("_with_" + "_".join(parts)) if parts else ""
    out_base = ROOT / "outputs" / f"permitless_carry_scm{suffix}"
    out_base.mkdir(parents=True, exist_ok=True)
    print(f"Loaded panel: {len(panel):,} state-year rows in "
          f"{ANALYSIS_YEARS[0]}-{ANALYSIS_YEARS[1]}")
    if parts:
        print(f"[{'+'.join(parts)}] writing outputs to {out_base.relative_to(ROOT)}")
    for case in CASES:
        run_one_case(panel, case, out_base, with_covid=with_covid,
                     with_efna=with_efna, with_despair=with_despair)
    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-covid", action="store_true",
                        help="Add OxCGRT covid_stringency_mean for the "
                             "pre-period pandemic year(s) as a "
                             "predictor in the SCM weight optimization.")
    parser.add_argument("--with-efna", action="store_true",
                        help="Add Fraser Institute efna_overall as a "
                             "predictor for ALL pre-period years.")
    parser.add_argument("--with-despair", action="store_true",
                        help="Add the deaths-of-despair stack "
                             "(synthetic_opioid_death_rate, "
                             "freq_mental_distress_pct, ami_pct) as "
                             "additional pre-period predictors.")
    args = parser.parse_args()
    main(with_covid=args.with_covid, with_efna=args.with_efna,
         with_despair=args.with_despair)
