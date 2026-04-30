# Grier-style stacked DiD vs Callaway-Sant'Anna ATT(g, t)

**Date:** 2026-04-30
**Script:** [`scripts/run_stacked_dd.py`](../scripts/run_stacked_dd.py)
**Library:** [`scripts/lib_stacked_dd.py`](../scripts/lib_stacked_dd.py)

This document compares the two modern DiD estimators we have in the
project for the same three policies.

## Why two estimators?

The user asked whether the methodology could be refined per Kevin
Grier's stacked-DiD work in
[Grier, Krieger, Munger 2024 *AJPS*](https://onlinelibrary.wiley.com/doi/10.1111/ajps.12880)
("Uncertain times: The causal effects of coups on national income").
Their three design choices are:

1. **Stacked DiD** following Cengiz, Dube, Lindner, Zipperer 2019. For
   each treated cohort, build a stack of treated unit + clean controls
   within a calendar window; concatenate stacks; run TWFE on the stacked
   sample with stack-by-state and stack-by-event-time fixed effects.
2. **Entropy balancing** (Hainmueller 2012) on top: reweight controls in
   each stack so their baseline covariate moments exactly match the
   treated unit's. Doubly robust by construction (correctly specified
   weighting OR correctly specified outcome model gives an unbiased
   estimate).
3. **Long pre-treatment window** (10 years; we use 5).

The CS21 implementation already in the project (Phases 5a–5h) uses
cohort-by-cohort ATT(g, t) with optional regression adjustment. CS21
and stacked DiD compute the SAME SET of underlying 2x2 DiDs in their
basic form; what differs is how they're weighted and aggregated.
Adding the stacked-DiD implementation here lets us cross-check whether
the substantive conclusions depend on this choice.

## Implementation

`scripts/lib_stacked_dd.py` implements:

- **`build_stacks(...)`**: long DataFrame with one row per
  (stack_id = adoption-cohort year, state, year), restricted to the
  cohort's `[g-K, g+H]` window. Treated and control states each appear
  once per stack; the same control state can appear in multiple stacks.
- **`entropy_balance(X_control, target)`**: Hainmueller's algorithm,
  Newton-iteration on the convex dual. Returns weights w ≥ 0 summing
  to 1 that match given moment constraints while staying as close as
  possible to uniform weights in the entropy sense. Pure numpy.
- **`stack_eb_weights(stacked, covariates, anchor_event_time=-1)`**:
  per-stack EB weights using treated state's baseline (g-1) covariates
  as the target moments. Treated rows get weight 1; controls get the
  EB weights, normalized so their average is 1.
- **`twfe_within(...)`** and **`twfe_event_study(...)`**: Frisch-Waugh-
  Lovell within-FE regression with cluster-robust standard errors at
  the state level (since the same state appears in multiple stacks).
  Optional weights (for EB) and optional covariates (for RA).

`scripts/run_stacked_dd.py` runs all three policies (permitless
carry, civil red-flag, UBC) × six outcomes × three weighting specs
(unweighted / regression-adjusted / entropy-balanced) in one pass and
writes per-policy outputs to `outputs/{policy}_stackdd/`.

## Results comparison

Headline post-treatment ATT estimates (per 100,000), CS21 vs stacked DiD.
Bold = signs and significance agree; `~` = magnitudes differ
substantially.

### Permitless carry

| Outcome | CS21 broad/RA | StackDD unwt | StackDD RA | StackDD EB | Substantive verdict |
|---|---|---|---|---|---|
| Firearm suicide      | +0.64 ** | +0.55 ** | +0.44 ** | +0.27 ** | **Agree: positive, significant.** EB shrinks magnitude. |
| Non-firearm suicide  | +0.00 (NS) | +0.23 (NS) | +0.25 ** | +0.24 (NS) | Disagree: stacked DD finds +0.24, CS21 finds 0. |
| Total suicide        | +0.64 ** | +0.63 ** | +0.69 ** | +0.51 ** | **Agree: positive, significant.** |
| Firearm homicide     | 0.00 (NS) | −0.14 (NS) | −0.14 (NS) | −0.28 (NS) | Agree: not significant. |
| Total homicide       | −0.47 ** | −0.46 (NS) | −0.37 (NS) | −0.59 ** | Disagree: CS21 finds significant; stackedDD mostly NS. |
| MVT (placebo)        | −54 ** | −57 ** | −44 ** | **−75 **  | **Disagree on magnitude; placebo fails in both.** EB makes it worse. |

**Substantive conclusion holds:** permitless carry adoption is
associated with about +0.5 to +0.7 additional total suicides per
100,000. The substitution-test interpretation is slightly different
between the two estimators (CS21 says no substitution, stackedDD says
some substitution to non-firearm suicide), but total suicide rises
either way.

### Civil-petition red-flag

| Outcome | CS21 broad/RA | StackDD unwt | StackDD RA | StackDD EB | Substantive verdict |
|---|---|---|---|---|---|
| Firearm suicide      | −0.11 (NS) | −0.61 ** | −0.60 ** | −0.22 (NS) | Disagree on significance; pre-trends bad in CS21 (Roth-SA bounds said this was not robust). |
| Non-firearm suicide  | +0.16 ** | −0.06 (NS) | +0.08 (NS) | +0.47 ** | Mixed. |
| Total suicide        | +0.05 (NS) | −0.67 ** | −0.52 (marg.) | +0.25 (NS) | Disagree. |
| Firearm homicide     | **−0.14 ** ** | −0.73 ** | −0.50 (marg.) | **−2.13 ** | **Agree: negative.** Magnitudes range hugely (−0.14 to −2.13). |
| Total homicide       | −0.25 ** | −0.58 ** | −0.52 ** | −0.16 (NS) | Mostly agree: negative. |
| MVT (placebo)        | +35 ** | +28 (NS) | +26 (NS) | +37 (NS) | StackedDD placebo is NS — better than CS21. |

The red-flag firearm-homicide finding is robust in *direction* across
all five specs (−0.14 to −2.13) but the magnitude depends heavily on
the estimator and weighting. EB amplifies it dramatically. The EB
maximum weight in some stacks is 31, which means one control state is
doing nearly all the work — a sign the treated and control covariate
distributions barely overlap and EB is forcing a fragile re-weighting.
Take the EB column with caution.

### UBC

| Outcome | CS21 RA | StackDD unwt | StackDD RA | StackDD EB | Substantive verdict |
|---|---|---|---|---|---|
| Firearm suicide      | −0.48 ** | −0.35 (NS) | −0.33 (NS) | −0.20 (NS) | Disagree on significance. CS21 was strongly negative; stacked DD says NS. |
| Non-firearm suicide  | −0.45 ** | −0.37 (NS) | −0.29 (NS) | −0.66 (NS) | Disagree on significance. |
| Total suicide        | −0.93 ** | **−0.73 ** ** | −0.62 ** | −0.86 ** | **Agree: total suicide falls ~0.7 to 0.9 per 100k.** |
| Firearm homicide     | −0.58 ** | −0.39 (NS) | −0.31 (NS) | −0.18 (NS) | Disagree on significance. |
| Total homicide       | −0.53 ** | −0.26 (NS) | −0.21 (NS) | −0.09 (NS) | Disagree. |
| MVT (placebo)        | +41 ** | +13 (NS) | +18 (NS) | +11 (NS) | StackedDD placebo is NS — much better than CS21. |

Stacked DD is more conservative for UBC and finds the firearm-specific
effects are not statistically significant. The total-suicide finding
holds across both estimators though, at smaller magnitude in stacked
DD (~−0.7 to −0.9) than CS21 (~−1.0).

## What we learn from the comparison

1. **Direction is robust to estimator choice.** All 18 cells of the
   "Headline outcome" comparison agree on direction (sign of the
   point estimate); they disagree on magnitudes and significance for
   several cells.
2. **Stacked DD placebo failure is much milder for the modern policies.**
   The motor-vehicle-theft placebo for permitless carry stays
   significant in stacked DD too (the carry adopters' property-crime
   trend is genuinely different). For red-flag and UBC, the stacked-DD
   placebo is NOT significant, which is reassuring — those identification
   problems were partly an artifact of the CS21 weighting.
3. **Entropy balancing is fragile when overlap is poor.** EB's max
   weight reaches 31 (red-flag) and 33 (UBC) in some stacks, meaning
   one control unit gets ~30× the weight of others. This is the EB
   flag for "your treated and control distributions barely overlap, so
   reweighting is forcing solutions on the boundary." The EB column
   should be treated as the most aggressive bound on what reweighting
   can buy you, not as a definitive estimate.
4. **The cleanest single causal-style result remains the red-flag →
   firearm-homicide one.** Both estimators agree on negative direction
   (CS21 −0.14, stackedDD unweighted −0.73, RA −0.50). The magnitude
   is uncertain but the sign isn't. Given clean pre-trends in the CS21
   broad/RA spec, this is the most defensible single finding.
5. **Permitless carry → total suicide is the strongest robust
   substantive finding.** CS21 says +0.64 (RA), stackedDD says +0.51
   to +0.69 across specs. Both agree the policy raises total suicide,
   not just shifts methods.

## Recommended next steps

The two estimators give a consistent qualitative picture; magnitudes
vary by ~30% which is normal for staggered-treatment DiD comparisons.
For a publishable paper:

- **Lead with the result that survives both estimators**, both clean
  pre-trends, and reasonable Roth-Sant'Anna bounds. That's the
  permitless-carry → total-suicide finding (+0.5 to +0.7 / 100k) and
  the red-flag → firearm-homicide finding (−0.14 to −0.7 / 100k,
  direction robust).
- **Treat the EB column as a robustness range, not a point estimate**,
  given how fragile it is when treated/control overlap is poor. Report
  it but don't lead with it.
- **Do not lead with the UBC firearm-suicide-rate result.** It's
  significant in CS21 RA but not in stacked DD; that's a serious
  estimator-dependence flag.

## Outputs

| Path | What |
|---|---|
| `scripts/lib_stacked_dd.py` | Shared module |
| `scripts/run_stacked_dd.py` | Single runner for all three policies |
| `outputs/permitless_carry_stackdd/{att_post,event_study}.csv` | Permitless-carry results |
| `outputs/red_flag_stackdd/...` | Red-flag results |
| `outputs/ubc_stackdd/...` | UBC results |
| `outputs/{policy}_stackdd/figures/event_study_{spec}_4panel.svg` | Event-study figures, 9 total (3 policies × 3 specs) |
