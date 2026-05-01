"""Shared synthetic-control machinery (Abadie-Diamond-Hainmueller 2010 JASA)
used by per-policy runners (run_scm_assault_weapons_ban.py, etc.).

The literature unanimously prefers SCM over staggered-DiD for policies with
small treated cohorts (1-4 states). Examples our spec-grid hits:
  Assault weapons ban (4 states), magazine ban (~4 in-window cohorts),
  age-21 handgun (4-6 states), permitless carry (single big-state cases
  like TX, FL, CA).

The CS21 / stacked-DiD pipelines run for ALL 8 policies in this project,
but for the small-cohort policies the per-event-time CS21 estimates are
underpowered: at +5 event-time, only the earliest cohort contributes, so
the cluster-bootstrap SE is degenerate. SCM gives an explicit per-state
counterfactual + permutation-style placebo inference instead.

Public API:

    fit_scm_weights(y_pre, Y_pre)            -> (J,) weights, sums to 1
    run_scm_for_case(panel, treated_state, g, donors, outcomes, out_dir,
                     pre_years_target=12, label=None)
    plot_scm_svg(path, outcome, label, all_years, pre_years, g,
                 y_treated, y_synth, donors, Y_full, case_label)

Both single-policy runners and the report builder import from here.

References:
  Abadie, A., Diamond, A., & Hainmueller, J. (2010). "Synthetic control
    methods for comparative case studies: Estimating the effect of
    California's tobacco control program." JASA 105(490): 493-505.
  Abadie, A. (2021). "Using synthetic controls: Feasibility, data
    requirements, and methodological aspects." JEL 59(2): 391-425.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def fit_scm_weights(y_pre: np.ndarray, Y_pre: np.ndarray) -> np.ndarray:
    """Solve min ||y_pre - Y_pre @ w||^2 s.t. w >= 0, sum(w) = 1.

    The Abadie-Diamond-Hainmueller weight problem: simplex-constrained QP.
    Solved via SLSQP with multi-start initialization to escape local
    optima of the simplex feasible set.

    y_pre: shape (T_pre,) -- treated state's pre-period outcome.
    Y_pre: shape (T_pre, J) -- donor states' pre-period outcomes.
    Returns (J,) nonneg weights summing to 1.
    """
    J = Y_pre.shape[1]
    if J == 0:
        return np.zeros(0)

    def loss(w):
        r = y_pre - Y_pre @ w
        return float(r @ r)

    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]
    bounds = [(0.0, 1.0)] * J
    starts = [np.ones(J) / J]
    rng = np.random.default_rng(11)
    for _ in range(5):
        starts.append(rng.dirichlet(np.ones(J)))
    best_w, best_loss = None, np.inf
    for x0 in starts:
        res = minimize(loss, x0, method="SLSQP", bounds=bounds, constraints=cons,
                       options={"maxiter": 200, "ftol": 1e-9})
        if res.fun < best_loss:
            best_loss = res.fun
            best_w = res.x
    best_w = np.clip(best_w, 0.0, None)
    if best_w.sum() > 0:
        best_w = best_w / best_w.sum()
    return best_w


def run_scm_for_case(panel: pd.DataFrame,
                     treated_state: str,
                     g: int,
                     donors: list[str],
                     outcomes: OrderedDict,
                     out_dir: Path,
                     pre_years_target: int = 12,
                     analysis_years: tuple = (1999, 2023),
                     label: str | None = None) -> dict:
    """Run SCM end-to-end for one (treated_state, adoption_year_g) case
    across all `outcomes`. Writes per-case CSVs (weights, trajectories,
    placebo) and a per-outcome SVG to out_dir.

    Returns a summary dict with per-outcome ATT and placebo p-value.
    """
    label = label or treated_state
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    pre_years = list(range(max(g - pre_years_target, analysis_years[0]), g))
    post_years = list(range(g, analysis_years[1] + 1))
    all_years = pre_years + post_years

    weights_rows: list[OrderedDict] = []
    traj_rows: list[OrderedDict] = []
    placebo_rows: list[OrderedDict] = []
    summary: dict[str, dict] = {}

    for outcome in outcomes:
        wide = (panel[panel["state_abbr"].isin([treated_state] + donors)
                      & panel["year"].isin(all_years)]
                .pivot(index="year", columns="state_abbr", values=outcome))
        if treated_state not in wide.columns:
            print(f"  [{outcome}] treated state missing data; skipping")
            continue
        full_donors = [d for d in donors
                       if d in wide.columns
                       and wide[d].notna().all()
                       and wide[d].count() == len(all_years)]
        if not full_donors:
            print(f"  [{outcome}] no donors with complete window; skipping")
            continue
        wide = wide.loc[all_years, [treated_state] + full_donors]
        if wide[treated_state].isna().any():
            print(f"  [{outcome}] treated has missing in window; skipping")
            continue

        y_pre = wide.loc[pre_years, treated_state].to_numpy(dtype=float)
        Y_pre = wide.loc[pre_years, full_donors].to_numpy(dtype=float)
        w = fit_scm_weights(y_pre, Y_pre)

        Y_full = wide.loc[all_years, full_donors].to_numpy(dtype=float)
        y_synth = Y_full @ w
        y_treated = wide.loc[all_years, treated_state].to_numpy(dtype=float)

        for i, yr in enumerate(all_years):
            traj_rows.append(OrderedDict([
                ("outcome", outcome),
                ("year", yr),
                ("event_time", yr - g),
                ("y_treated", float(y_treated[i])),
                ("y_synthetic", float(y_synth[i])),
                ("effect", float(y_treated[i] - y_synth[i])),
            ]))
        for d, wt in zip(full_donors, w):
            if wt > 1e-4:
                weights_rows.append(OrderedDict([
                    ("outcome", outcome),
                    ("donor", d),
                    ("weight", float(wt)),
                ]))

        pre_rmse = float(np.sqrt(np.mean((y_pre - Y_pre @ w) ** 2)))
        actual_post = float(np.mean(y_treated[len(pre_years):]
                                    - y_synth[len(pre_years):]))
        print(f"  [{outcome}] pre-period RMSE = {pre_rmse:.4g}; "
              f"non-zero donors = {sum(w > 1e-4)}/{len(full_donors)}; "
              f"post ATT = {actual_post:+.3f}")

        # Permutation placebo: refit SCM on every donor as if it were
        # treated, with the rest of the donor pool serving as donors.
        placebo_post = []
        for j, d in enumerate(full_donors):
            other = [k for k in range(len(full_donors)) if k != j]
            if not other:
                continue
            y_d_pre = Y_pre[:, j]
            Y_other_pre = Y_pre[:, other]
            w_p = fit_scm_weights(y_d_pre, Y_other_pre)
            y_d_full = Y_full[:, j]
            Y_other_full = Y_full[:, other]
            y_d_synth = Y_other_full @ w_p
            placebo_post.append(float(np.mean(y_d_full[len(pre_years):]
                                              - y_d_synth[len(pre_years):])))
        if placebo_post:
            placebo_arr = np.asarray(placebo_post)
            n = len(placebo_arr)
            p_two = float((np.abs(placebo_arr) >= np.abs(actual_post)).sum() / n)
            placebo_rows.append(OrderedDict([
                ("outcome", outcome),
                ("actual_post_effect", actual_post),
                ("n_placebo", n),
                ("placebo_mean", float(placebo_arr.mean())),
                ("placebo_sd", float(placebo_arr.std(ddof=1) if n > 1 else float("nan"))),
                ("p_value_two_sided", p_two),
                ("pre_rmse", pre_rmse),
            ]))
            summary[outcome] = {
                "att": actual_post,
                "p_two_sided": p_two,
                "pre_rmse": pre_rmse,
                "n_donors_nonzero": int(sum(w > 1e-4)),
                "n_donors_total": int(len(full_donors)),
            }

        plot_scm_svg(fig_dir / f"{outcome}.svg", outcome, outcomes[outcome],
                     all_years, pre_years, g, y_treated, y_synth,
                     full_donors, Y_full, case_label=label)

    pd.DataFrame(weights_rows).to_csv(out_dir / "weights.csv", index=False)
    pd.DataFrame(traj_rows).to_csv(out_dir / "trajectories.csv", index=False)
    pd.DataFrame(placebo_rows).to_csv(out_dir / "placebo.csv", index=False)
    return {"label": label, "g": g, "outcomes": summary,
            "n_donors": len(full_donors) if 'full_donors' in dir() else 0}


def plot_scm_svg(path: Path, outcome: str, label: str,
                 all_years, pre_years, g,
                 y_treated, y_synth,
                 donors, Y_full, case_label: str) -> None:
    """One-panel SVG: treated trajectory (solid red), synthetic
    counterfactual (dashed blue), faint donor lines (gray) for context.
    Vertical dashed line at adoption year g."""
    W, H = 720, 380
    PAD_L, PAD_R, PAD_T, PAD_B = 60, 40, 50, 50
    iw = W - PAD_L - PAD_R
    ih = H - PAD_T - PAD_B
    x_lo, x_hi = float(min(all_years)), float(max(all_years))
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
    for j in range(Y_full.shape[1]):
        pts = " ".join(f"{px(yr):.1f},{py(Y_full[i, j]):.1f}"
                       for i, yr in enumerate(all_years))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="#bbb" '
                     f'stroke-width="0.6" opacity="0.6"/>')
    pts_synth = " ".join(f"{px(yr):.1f},{py(y_synth[i]):.1f}"
                          for i, yr in enumerate(all_years))
    parts.append(f'<polyline points="{pts_synth}" fill="none" stroke="#1f3a5f" '
                 f'stroke-width="2" stroke-dasharray="6 4"/>')
    pts_tr = " ".join(f"{px(yr):.1f},{py(y_treated[i]):.1f}"
                       for i, yr in enumerate(all_years))
    parts.append(f'<polyline points="{pts_tr}" fill="none" stroke="#b9461a" '
                 f'stroke-width="2.4"/>')
    parts.append(f'<line x1="{px(g - 0.5):.1f}" y1="{PAD_T}" '
                 f'x2="{px(g - 0.5):.1f}" y2="{PAD_T + ih}" '
                 f'stroke="#1f2024" stroke-width="0.8" stroke-dasharray="4 3"/>')
    parts.append(f'<text x="{px(g - 0.5):.1f}" y="{PAD_T - 5}" text-anchor="middle" '
                 f'fill="#1f2024" font-size="10">adoption ({g})</text>')
    parts.append(f'<line x1="{PAD_L}" y1="{PAD_T+ih}" x2="{PAD_L+iw}" y2="{PAD_T+ih}" stroke="#444"/>')
    parts.append(f'<line x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{PAD_T+ih}" stroke="#444"/>')
    for yr in all_years:
        if (yr - all_years[0]) % 2 == 0:
            parts.append(f'<line x1="{px(yr):.1f}" y1="{PAD_T+ih}" x2="{px(yr):.1f}" y2="{PAD_T+ih+4}" stroke="#444"/>')
            parts.append(f'<text x="{px(yr):.1f}" y="{PAD_T+ih+18}" text-anchor="middle" fill="#444">{yr}</text>')
    for k in range(5):
        v = y_lo + (y_hi - y_lo) * k / 4
        y = py(v)
        parts.append(f'<line x1="{PAD_L-4}" y1="{y:.1f}" x2="{PAD_L}" y2="{y:.1f}" stroke="#444"/>')
        parts.append(f'<text x="{PAD_L-7}" y="{y+3:.1f}" text-anchor="end" fill="#444">{v:.2g}</text>')
    parts.append(f'<rect x="{W-200}" y="{PAD_T+10}" width="190" height="60" fill="white" stroke="#e2e2dc"/>')
    parts.append(f'<line x1="{W-190}" y1="{PAD_T+25}" x2="{W-160}" y2="{PAD_T+25}" stroke="#b9461a" stroke-width="2.4"/>')
    parts.append(f'<text x="{W-155}" y="{PAD_T+29}" font-size="11">{case_label} (treated)</text>')
    parts.append(f'<line x1="{W-190}" y1="{PAD_T+45}" x2="{W-160}" y2="{PAD_T+45}" stroke="#1f3a5f" stroke-width="2" stroke-dasharray="6 4"/>')
    parts.append(f'<text x="{W-155}" y="{PAD_T+49}" font-size="11">Synthetic counterfactual</text>')
    parts.append(f'<line x1="{W-190}" y1="{PAD_T+62}" x2="{W-160}" y2="{PAD_T+62}" stroke="#bbb" stroke-width="0.6"/>')
    parts.append(f'<text x="{W-155}" y="{PAD_T+66}" font-size="10">Donor states (gray)</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts))


def eligible_donors_simple(panel: pd.DataFrame,
                           treated_state: str,
                           treated_var: str,
                           treated_var_eligible_value: int,
                           pre_window: tuple) -> list[str]:
    """Generic donor-pool builder. A donor is eligible if it had
    `treated_var == treated_var_eligible_value` for EVERY year in
    pre_window. Excludes the treated state itself and DC.

    For e.g. assault weapons ban with `assault==0` throughout: pass
    treated_var="assault", treated_var_eligible_value=0.
    """
    pre_lo, pre_hi = pre_window
    out = []
    for s in sorted(panel["state_abbr"].unique()):
        if s == treated_state or s == "DC":
            continue
        sub = panel[(panel["state_abbr"] == s)
                    & (panel["year"] >= pre_lo)
                    & (panel["year"] <= pre_hi)]
        if sub.empty:
            continue
        if (sub[treated_var] == treated_var_eligible_value).all():
            out.append(s)
    return out
