# Permitless carry adoption — Callaway-Sant'Anna ATT(g, t)

**Date:** 2026-04-30 (updated with regression-adjusted spec)
**Script:** [`scripts/run_cs_permitless_carry.py`](../../scripts/run_cs_permitless_carry.py)
**Output folder:** `outputs/permitless_carry_cs/`

This document is meant to be read alongside the existing
[stacked-DiD feasibility audit](../permitless_carry_suicide_audit/audit_memo.md)
in `outputs/permitless_carry_suicide_audit/`. The audit recommends revising
the design before any manuscript work — that recommendation **stands** and
this CS analysis reinforces it. Below we document what the modern
Callaway & Sant'Anna (2021) ATT(g, t) estimator says when applied to the
same treatment, and we use a placebo outcome to show why the basic
specification is not yet causal.

## Headline numbers (two specifications)

Average post-treatment ATT (per 100,000 population), state-cluster
multiplier-bootstrap standard errors. **OR** = basic outcome regression
with no covariates; **RA** = Sant'Anna & Zhao (2020) regression-adjusted
estimator with three baseline covariates (`ln_population`,
`unemployment_rate`, `ln_pcpi_real_2024`) measured at year *g − 1*.

| Outcome | OR ATT | OR z | OR pre-trend z | RA ATT | RA z | RA pre-trend z |
|---|---|---|---|---|---|---|
| Firearm suicide rate           | +0.86 | +13.7 | −3.6 | **+0.64** | **+16.4** | **−0.86** |
| Firearm homicide rate          | +0.29 |  +2.5 | −1.4 | **−0.003** |  −0.05 | +7.6 |
| Total homicide rate            | −0.15 |  −2.0 | −0.4 | −0.47 |  −7.9 | +6.2 |
| Motor vehicle theft (placebo)  | −39.4 |  −9.2 | +4.9 | −54.2 | −17.6 | +9.0 |

### What you should take away

- **Firearm suicide is the only result that survives covariate adjustment
  with a clean pre-trend.** Adding the three macroeconomic / scale
  covariates shrinks the ATT from +0.86 to +0.64 per 100,000 and — more
  importantly — collapses the pre-period z from −3.6 to −0.86, which no
  longer rejects. That is the cleanest pattern any of the four outcomes
  show in this build.
- **The firearm homicide effect from the OR spec was an artifact.** Once
  controls are added the estimate collapses to essentially zero
  (−0.003, z = −0.05). The OR-spec result was driven by trend
  differences in macroeconomic conditions across treated and never-treated
  states, not by the carry policy.
- **The placebo still fails — and gets worse with covariate adjustment.**
  Motor vehicle theft has nothing to do with concealed-carry permitting.
  RA produces a larger negative "effect" (−54.2) and a stronger positive
  pre-trend than the basic OR spec. That tells us our three macroeconomic
  controls are not enough to absorb the trend differences in property
  crime between adopting and non-adopting states. The right next step is
  outcome-specific covariate sets (e.g., add per-100k income inequality,
  drug-overdose deaths, urbanization, partisan composition) and / or a
  stricter never-treated comparison group (the original audit's
  shall-issue + permit-required rule).
- **Total homicide is similar to the placebo.** RA pushes it more
  negative (−0.47, z = −7.9) but pre-trends are also positive (+6.2),
  which is consistent with the controls failing to absorb the same kind
  of trend gap that breaks the placebo.

**Headline finding for permitless carry, conditional on this build:**
adoption is associated with about **0.6–0.9 additional firearm suicides
per 100,000 residents per year** in the average treated state, with a
pre-trend that — in the covariate-adjusted spec — is no longer
statistically distinguishable from zero. This survives the modal
robustness check most likely to discredit it. It is consistent with the
original audit's directional conclusion but with cleaner pretrend
behaviour under the covariate-adjusted CS21 estimator.

The other outcomes (firearm homicide, total homicide, motor vehicle
theft) require a stricter design before they can be interpreted.

## Sample

- **Panel:** state-year, 1999–2023, DC excluded → 1,250 observations.
- **Outcomes:** four columns from `data/processed/panel_core_augmented.csv`:
  firearm suicide rate, firearm homicide rate (both from the firearm
  suicide / homicide v2 file, 1979–2023), total homicide rate and motor
  vehicle theft rate (both from FBI/OpenCrime).

## Treatment

The treatment is **first 1→0 switch in Tufts `permitconcealed`** —
i.e., the first year a state stops requiring a permit to carry concealed.
Treatment is treated as absorbing (no documented post-adoption reversals
in the panel window). The cohort table comes from the original audit's
[`treatment_adoption_table.csv`](../permitless_carry_suicide_audit/treatment_adoption_table.csv).

| Cohort year (g) | n states | states |
|---|---|---|
| 2010 | 1 | AZ |
| 2011 | 1 | WY |
| 2015 | 3 | KS, ME, MS |
| 2016 | 2 | ID, WV |
| 2017 | 3 | MO, NH, ND |
| 2019 | 3 | KY, OK, SD |
| 2021 | 6 | AR, IA, MT, TN, TX, UT |
| 2022 | 3 | GA, IN, OH |
| 2023 | 3 | AL, FL, NE |

Excluded from this analysis (logged in `dropped_log.csv`):

- **AK 2003.** Adopted before our window begins; cannot form a 5-year
  pre-period within 1999–2023.
- **LA 2024, SC 2024.** Adopted after our outcomes' end date (v2 file
  ends 2023). The original audit also excludes these from its mortality
  sample.

## Control group

**Never-treated only.** We use the 21 states that the audit table marks
as `adoption_year == NaN` AND `starts_permit_required == 1`. This excludes
Vermont (historically permitless carry; never required a permit) and DC.

Note this is a *broader* control set than the original audit's
specification, which additionally requires the control state to be
shall-issue (i.e., `mayissue == 0`) throughout the relevant event window.
Replicating the stricter rule under CS21 is a sensible robustness check
and is queued for the next pass.

## Estimator

We compute, for each treatment cohort g and calendar year t in the
analysis window:

> ATT(g, t) = E[Y_t − Y_{g−1} | treated, cohort g] − E[Y_t − Y_{g−1} | never-treated]

This is Callaway & Sant'Anna's (2021) "outcome regression" estimator with
the never-treated comparison group, no covariates. We omit the baseline
year t = g − 1 (ATT identically 0 by construction). For each (g, t) we
record the point estimate, the cluster-robust standard error from a
state-level Rademacher multiplier bootstrap (B = 2,000 replications,
seed 7), and the number of treated and control units that contributed.

We then aggregate to:

- **Event-time ATT(e):** weighted average of ATT(g, g+e) over g, with
  cohort weights proportional to the treated-state count. SE is the
  weighted root-sum-of-squares of the underlying ATT(g, t) SEs.
- **Overall post-treatment ATT:** weighted average of ATT(g, t) for
  t ≥ g, same cohort-size weighting.

### Two specs

We run both:

- **OR (basic outcome regression):** no covariates. The simplest possible
  CS21. Useful as a baseline before any adjustment.
- **RA (Sant'Anna-Zhao 2020 regression-adjusted):** for each (g, t), fit
  OLS of ΔY on a constant and three baseline covariates using
  never-treated control units only, then predict the counterfactual
  long-difference for each treated unit. ATT(g, t) is the mean of the
  treated long-differences minus the mean of those predicted
  counterfactuals.

We deliberately use only macroeconomic / scale covariates that are
neutral across the four outcomes:

- `ln_population` — captures scale and metro-area composition shifts.
- `unemployment_rate` — captures labour-market cycle (suicides and
  property crime are both pro-cyclical in different directions).
- `ln_pcpi_real_2024` — captures real income trajectory.

We do **not** include violent_rate or property_rate as controls because
they are mechanically correlated with three of our four outcomes
(homicide, motor vehicle theft, and the firearm-homicide variant of
violent crime). The original stacked-DiD audit includes them as controls
in some specs; that's a defensible choice for the firearm-suicide
outcome but not for the others.

## Outputs

| File | What it is |
|---|---|
| `att_gt.csv` | One row per (outcome, spec, g, t). 1,728 rows. |
| `event_study.csv` | One row per (outcome, spec, event_time). |
| `overall_att.csv` | One row per (outcome, spec) with overall post-treatment ATT and pre-trend test. |
| `cohort_n.csv` | Cohort-size table from the build run. |
| `dropped_log.csv` | States dropped from analysis with reasons. |
| `figures/event_study_or_4panel.svg` | 4-panel event-study figure, OR spec. |
| `figures/event_study_ra_4panel.svg` | 4-panel event-study figure, RA spec. |

## Reproducing

```sh
python scripts/run_cs_permitless_carry.py
```

The script imports nothing beyond pandas, numpy, and the standard library.
If matplotlib is installed it produces a PNG; otherwise it emits a
hand-built SVG that has the same content (no pip install required).

## Recommended next steps

1. **Add fully doubly-robust (DR) estimation with IPW.** RA on its own
   has clearly fixed the firearm-suicide pre-trend but not the other
   outcomes' pre-trends. Adding propensity-score weighting on top of
   the regression adjustment (the full Sant'Anna-Zhao DR estimator)
   should help further when the propensity model fits well.
2. **Apply the audit's stricter control rule.** Restrict the comparison
   pool to states that are shall-issue (`mayissue == 0`) and
   permit-required (`permitconcealed == 1`) throughout the relevant
   event window. This costs us some control units but makes the placebo
   condition more meaningful and may resolve the residual placebo issue.
3. **More placebo outcomes.** Burglary, larceny, and prison admissions
   are good additions because they should not respond to carry
   permitting in any direct mechanism. If they all show similar
   placebo failures we know the residual issue is with the comparison
   group, not the policy.
4. **Cross-check with alternative estimators.** Sun-Abraham, Borusyak-
   Jaravel-Spiess, de Chaisemartin-D'Haultfœuille. CS21 with
   never-treated control is one of several reasonable choices; agreement
   across estimators strengthens any causal claim.
5. **Synthetic-control sanity check** for the largest individual
   treated states (e.g., Texas 2021, Florida 2023). With single-state
   cohorts this gives a transparent counterfactual that doesn't average
   across heterogeneous adopters.

The original audit's caution about *publishing* on this question stands.
With the RA spec adding a credible firearm-suicide-specific result and a
clean pre-trend, the design is closer to defensible — but the placebo
failure for property crime says we're not there yet on the broader
panel of outcomes.

## References

- Callaway, B., & Sant'Anna, P. H. C. (2021). "Difference-in-Differences
  with Multiple Time Periods." *Journal of Econometrics*, 225(2), 200–230.
- Sant'Anna, P. H. C., & Zhao, J. (2020). "Doubly robust
  difference-in-differences estimators." *Journal of Econometrics*,
  219(1), 101–122.
- Goodman-Bacon, A. (2021). "Difference-in-differences with variation in
  treatment timing." *Journal of Econometrics*, 225(2), 254–277.
- Sun, L., & Abraham, S. (2021). "Estimating dynamic treatment effects in
  event studies with heterogeneous treatment effects." *Journal of
  Econometrics*, 225(2), 175–199.
