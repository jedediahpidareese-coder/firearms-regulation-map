"""Phase 5f: Roth & Sant'Anna 'honest' pre-trend bounds for the event-study
estimates from the CS21 builds.

The classical pre-trend test asks: "Are the pre-period ATT(e) estimates
jointly zero?" If they are, you assume parallel trends and use the
post-period ATTs at face value. If they reject, you have to either
discard the design or argue around it.

Roth-Sant'Anna (2019) and the more general Rambachan-Roth (2023)
"honest" pre-trends framework offers a middle path: instead of pretesting
and binarizing, you ASSUME the post-treatment trend deviation from
parallel trends is bounded by some multiple M of the observed
pre-period trend. Then you report ATT bounds across a range of M and
let the reader / reviewer decide what M they think is plausible.

We implement the simplest useful version:

  1. Fit a linear pre-trend to the event-study coefficients ATT(e) for
     e in [E_MIN, -2] (skipping e = -1, the omitted year).
  2. Get the slope b_hat and its SE.
  3. For each post-period e >= 0, the "trend-adjusted" ATT is
       ATT_adj(e) = ATT(e) - (e + 1) * b_hat
     because the pre-trend extrapolated forward from e = -1 to event
     time e is (e + 1) * b_hat.
  4. CIs are built two ways:
     a. Strict (M = 0): original CI, no adjustment.
     b. Bounded (M > 0): subtract M * (e + 1) * b_hat from the point
        estimate; CI half-width is the original SE plus
        M * (e + 1) * SE(b_hat). This is the conservative
        Rambachan-Roth-style bound.
  5. Sensitivity grid: M in (0, 0.5, 1.0, 2.0).

Inputs:
  outputs/permitless_carry_cs/event_study.csv
  outputs/red_flag_cs/event_study.csv

Outputs:
  outputs/roth_sa_bounds/{policy}_{spec}_{control_rule}_{outcome}_bounds.csv
  outputs/roth_sa_bounds/methodology.md (brief)

We focus on the firearm_suicide_rate outcome because both the permitless
carry and red-flag analyses produce post-treatment coefficients with
problematic pre-trends for that outcome. Other outcomes can be added
by editing the OUTCOMES_TO_BOUND list.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "roth_sa_bounds"
OUT.mkdir(parents=True, exist_ok=True)

INPUTS = [
    # CS21 event-study tables. Have columns:
    #   outcome, spec, control_rule, event_time, att, se, ...
    {
        "policy": "permitless_carry",
        "estimator": "cs21",
        "es_path": ROOT / "outputs" / "permitless_carry_cs" / "event_study.csv",
        "att_col": "att",
        "specs": [("broad", "ra"), ("strict", "ra"),
                  ("broad", "or"), ("strict", "or")],
    },
    {
        "policy": "red_flag",
        "estimator": "cs21",
        "es_path": ROOT / "outputs" / "red_flag_cs" / "event_study.csv",
        "att_col": "att",
        "specs": [("broad", "ra"), ("strict", "ra"),
                  ("broad", "or"), ("strict", "or")],
    },
    {
        "policy": "ubc",
        "estimator": "cs21",
        "es_path": ROOT / "outputs" / "ubc_cs" / "event_study.csv",
        "att_col": "att",
        "specs": [("broad", "ra"), ("broad", "or")],
    },
    {
        "policy": "assault_weapons_ban",
        "estimator": "cs21",
        "es_path": ROOT / "outputs" / "assault_weapons_ban_cs" / "event_study.csv",
        "att_col": "att",
        "specs": [("broad", "ra"), ("strict", "ra"),
                  ("broad", "or"), ("strict", "or")],
    },
    # Stacked-DiD event-study tables. Have columns:
    #   outcome, spec, event_time, beta, se, ...   (no control_rule)
    {
        "policy": "permitless_carry",
        "estimator": "stackdd",
        "es_path": ROOT / "outputs" / "permitless_carry_stackdd" / "event_study.csv",
        "att_col": "beta",
        "specs": [(None, "unweighted"), (None, "ra"), (None, "eb")],
    },
    {
        "policy": "red_flag",
        "estimator": "stackdd",
        "es_path": ROOT / "outputs" / "red_flag_stackdd" / "event_study.csv",
        "att_col": "beta",
        "specs": [(None, "unweighted"), (None, "ra"), (None, "eb")],
    },
    {
        "policy": "ubc",
        "estimator": "stackdd",
        "es_path": ROOT / "outputs" / "ubc_stackdd" / "event_study.csv",
        "att_col": "beta",
        "specs": [(None, "unweighted"), (None, "ra"), (None, "eb")],
    },
    {
        "policy": "assault_weapons_ban",
        "estimator": "stackdd",
        "es_path": ROOT / "outputs" / "assault_weapons_ban_stackdd" / "event_study.csv",
        "att_col": "beta",
        "specs": [(None, "unweighted"), (None, "ra"), (None, "eb")],
    },
    {
        "policy": "age21_handgun",
        "estimator": "cs21",
        "es_path": ROOT / "outputs" / "age21_handgun_cs" / "event_study.csv",
        "att_col": "att",
        "specs": [("broad", "ra"), ("strict", "ra"),
                  ("broad", "or"), ("strict", "or")],
    },
    {
        "policy": "age21_handgun",
        "estimator": "stackdd",
        "es_path": ROOT / "outputs" / "age21_handgun_stackdd" / "event_study.csv",
        "att_col": "beta",
        "specs": [(None, "unweighted"), (None, "ra"), (None, "eb")],
    },
    {
        "policy": "magazine_ban",
        "estimator": "cs21",
        "es_path": ROOT / "outputs" / "magazine_ban_cs" / "event_study.csv",
        "att_col": "att",
        "specs": [("broad", "ra"), ("strict", "ra"),
                  ("broad", "or"), ("strict", "or")],
    },
    {
        "policy": "magazine_ban",
        "estimator": "stackdd",
        "es_path": ROOT / "outputs" / "magazine_ban_stackdd" / "event_study.csv",
        "att_col": "beta",
        "specs": [(None, "unweighted"), (None, "ra"), (None, "eb")],
    },
    {
        "policy": "stand_your_ground",
        "estimator": "cs21",
        "es_path": ROOT / "outputs" / "stand_your_ground_cs" / "event_study.csv",
        "att_col": "att",
        "specs": [("broad", "ra"), ("strict", "ra"),
                  ("broad", "or"), ("strict", "or")],
    },
    {
        "policy": "stand_your_ground",
        "estimator": "stackdd",
        "es_path": ROOT / "outputs" / "stand_your_ground_stackdd" / "event_study.csv",
        "att_col": "beta",
        "specs": [(None, "unweighted"), (None, "ra"), (None, "eb")],
    },
]
OUTCOMES_TO_BOUND = ["firearm_suicide_rate"]
PRE_E_MIN = -5
PRE_E_MAX = -2  # skip -1 (baseline)
SENSITIVITY_M = [0.0, 0.5, 1.0, 2.0]


def fit_pre_trend(df_es: pd.DataFrame, att_col: str = "att"):
    """Linear regression of ATT(e) on e for e in [PRE_E_MIN, PRE_E_MAX].

    Returns (b_hat, se_b) for the slope, plus the intercept (which we ignore
    because we anchor predictions at e = -1).
    """
    sub = df_es[(df_es["event_time"] >= PRE_E_MIN)
                & (df_es["event_time"] <= PRE_E_MAX)].copy()
    if len(sub) < 2:
        return float("nan"), float("nan")
    e = sub["event_time"].to_numpy(dtype=float)
    y = sub[att_col].to_numpy(dtype=float)
    sigma2 = sub["se"].to_numpy(dtype=float) ** 2
    # Weighted OLS: weights = 1 / sigma2_e (so larger-SE pre-coefs matter less).
    # Prevent div by zero.
    sigma2 = np.maximum(sigma2, 1e-9)
    w = 1.0 / sigma2
    X = np.c_[np.ones(len(e)), e]
    Wsqrt = np.sqrt(w)[:, None]
    beta, *_ = np.linalg.lstsq(X * Wsqrt, y * Wsqrt.flatten(), rcond=None)
    # SE for slope from weighted OLS.
    resid = y - X @ beta
    n, k = len(y), 2
    if n <= k:
        return float(beta[1]), float("nan")
    XtWX = X.T @ (w[:, None] * X)
    XtWXinv = np.linalg.pinv(XtWX)
    sigma_hat2 = float((resid * w * resid).sum() / (n - k))
    cov = sigma_hat2 * XtWXinv
    se_b = float(np.sqrt(cov[1, 1]))
    return float(beta[1]), se_b


def bounds_for_outcome(df_es: pd.DataFrame, att_col: str = "att") -> pd.DataFrame:
    """Compute Roth-Sant'Anna-style bounds for one (outcome, spec, ...)
    event-study series. Returns one row per (event_time, M)."""
    b_hat, se_b = fit_pre_trend(df_es, att_col=att_col)
    rows = []
    for _, r in df_es.iterrows():
        e = int(r["event_time"])
        if e < 0:
            continue
        att = float(r[att_col])
        se = float(r["se"])
        for M in SENSITIVITY_M:
            offset = (e + 1) * b_hat       # extrapolated pre-trend at event-time e
            adj = att - M * offset
            ci_half = 1.96 * np.sqrt(se ** 2 + (M * (e + 1)) ** 2 * (se_b ** 2))
            rows.append(OrderedDict([
                ("event_time", e),
                ("M_sensitivity", M),
                ("att_original", att),
                ("se_original", se),
                ("pre_trend_slope_b_hat", b_hat),
                ("pre_trend_slope_se", se_b),
                ("att_trend_adjusted", adj),
                ("ci_half_width", float(ci_half)),
                ("ci_low", float(adj - ci_half)),
                ("ci_high", float(adj + ci_half)),
                ("ci_includes_zero", bool((adj - ci_half) <= 0 <= (adj + ci_half))),
            ]))
    return pd.DataFrame(rows)


def main():
    print("Roth-Sant'Anna honest pre-trend bounds")
    print("=" * 72)
    summary_rows = []
    for inp in INPUTS:
        try:
            es_full = pd.read_csv(inp["es_path"])
        except FileNotFoundError:
            print(f"  skip (file missing): {inp['es_path']}")
            continue
        for outcome in OUTCOMES_TO_BOUND:
            for control_rule, spec in inp["specs"]:
                if control_rule is None:
                    sub = es_full[(es_full["outcome"] == outcome)
                                  & (es_full["spec"] == spec)]
                    rule_label = "single"
                else:
                    sub = es_full[(es_full["outcome"] == outcome)
                                  & (es_full["spec"] == spec)
                                  & (es_full["control_rule"] == control_rule)]
                    rule_label = control_rule
                # Tier-aware (added 2026-05-01): att_gt now has multiple
                # tiers per (control_rule, spec). Filter to OR's "all"
                # marker or RA/EB's "headline" tier so the pre-trend fit
                # uses one consistent series.
                if "tier" in sub.columns:
                    if spec in ("or", "unweighted"):
                        sub = sub[sub["tier"] == "all"]
                    else:
                        sub = sub[sub["tier"] == "headline"]
                if sub.empty:
                    print(f"  no data for {inp['estimator']}/{inp['policy']}/"
                          f"{rule_label}/{spec}/{outcome}; skipping")
                    continue
                bdf = bounds_for_outcome(sub, att_col=inp["att_col"])
                if bdf.empty:
                    continue
                fname = (f"{inp['estimator']}_{inp['policy']}_{rule_label}_"
                         f"{spec}_{outcome}_bounds.csv")
                bdf.to_csv(OUT / fname, index=False)
                key_e = 1
                pick = bdf[(bdf["event_time"] == key_e)].sort_values("M_sensitivity")
                if pick.empty:
                    continue
                base = pick[pick["M_sensitivity"] == 0.0].iloc[0]
                m1 = pick[pick["M_sensitivity"] == 1.0].iloc[0]
                m2 = pick[pick["M_sensitivity"] == 2.0].iloc[0]
                summary_rows.append(OrderedDict([
                    ("estimator", inp["estimator"]),
                    ("policy", inp["policy"]),
                    ("outcome", outcome),
                    ("control_rule", rule_label),
                    ("spec", spec),
                    ("pre_trend_slope_b_hat", float(base["pre_trend_slope_b_hat"])),
                    ("pre_trend_slope_se", float(base["pre_trend_slope_se"])),
                    ("att_e1_original", float(base["att_original"])),
                    ("ci_e1_M0", f"({base['ci_low']:+.3f}, {base['ci_high']:+.3f})"),
                    ("att_e1_M1", float(m1["att_trend_adjusted"])),
                    ("ci_e1_M1", f"({m1['ci_low']:+.3f}, {m1['ci_high']:+.3f})"),
                    ("ci_M1_includes_zero", bool(m1["ci_includes_zero"])),
                    ("att_e1_M2", float(m2["att_trend_adjusted"])),
                    ("ci_e1_M2", f"({m2['ci_low']:+.3f}, {m2['ci_high']:+.3f})"),
                    ("ci_M2_includes_zero", bool(m2["ci_includes_zero"])),
                ]))
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT / "summary_e1.csv", index=False)
    print("\nSummary at event-time e = +1 (first full post-treatment year):")
    cols_to_show = ["estimator", "policy", "control_rule", "spec",
                    "att_e1_original", "ci_e1_M0",
                    "att_e1_M1", "ci_e1_M1", "ci_M1_includes_zero"]
    print(summary[cols_to_show].to_string(index=False))


if __name__ == "__main__":
    main()
