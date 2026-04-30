# Permitless carry adoption — Callaway-Sant'Anna ATT(g, t)

**Date:** 2026-04-30
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

## Headline numbers

Average post-treatment ATT (per 100,000 population), state-cluster
multiplier-bootstrap standard errors, **no covariate adjustment**:

| Outcome | ATT | SE | z | Pre-trends test (avg ATT for e ∈ [-5, -2]) |
|---|---|---|---|---|
| Firearm suicide rate           | +0.86 | 0.06 | +13.7 | z = -3.59 (rejects 0) |
| Firearm homicide rate          | +0.29 | 0.12 |  +2.5 | z = -1.36 (does not reject) |
| Total homicide rate            | -0.15 | 0.07 |  -2.0 | z = -0.37 (does not reject) |
| Motor vehicle theft (placebo)  | -39.4 | 4.30 |  -9.2 | z = +4.87 (rejects 0) |

### What you should take away

- **The placebo fails.** Motor vehicle theft has nothing to do with permitless
  carry. A clean design should produce ATT ≈ 0 for it. Instead we get a
  large, highly significant negative ATT and a strongly positive pre-trend.
  That tells us treated and control states are on visibly different secular
  paths even before any treatment, and any "effect" we see for the firearm
  outcomes could reflect that, not the policy.
- **The firearm suicide pre-trend is not flat either** (z = -3.59 on the
  e ∈ [-5, -2] average). This matches the original audit's joint pretrend
  rejection.
- **The firearm suicide signal is the strongest.** Even after acknowledging
  the pre-trend issue, post-treatment coefficients are uniformly positive
  and economically meaningful (about +0.9 firearm suicides per 100,000
  population per year). Whether the magnitude survives covariate
  adjustment is an open question — the original audit's covariate-adjusted
  stacked DiD shrinks the estimate to roughly half of this size.
- **Direction is mixed for homicides.** Firearm homicide ticks up; total
  homicide ticks down slightly. Most plausibly: nonfirearm homicide is
  declining for unrelated reasons in the same states. We do not interpret
  this as a real treatment effect.

This is a starting point, not a publishable finding.

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

### Why no covariates yet?

The standard CS21 spec adds covariates either through outcome regression
or doubly-robust IPW. We deliberately ran the simplest version first so
we could see how far the raw signal travels. The placebo failure shows
clearly that covariates are necessary; the next step is to add the same
core controls the original audit uses (`ln_population`, `unemployment_rate`,
`ln_pcpi_real_2024`, `violent_rate`, `property_rate`) and re-estimate the
DR version.

## Outputs

| File | What it is |
|---|---|
| `att_gt.csv` | One row per (outcome, g, t). The raw ATT(g, t) point estimates and SEs. 864 rows. |
| `event_study.csv` | One row per (outcome, event_time). Aggregated event-study coefficients with SEs. |
| `overall_att.csv` | One row per outcome. Overall post-treatment ATT and pre-trend test. |
| `cohort_n.csv` | Cohort-size table from the build run. |
| `dropped_log.csv` | States dropped from analysis with reasons. |
| `figures/event_study_4panel.svg` | 4-panel event-study figure. |

## Reproducing

```sh
python scripts/run_cs_permitless_carry.py
```

The script imports nothing beyond pandas, numpy, and the standard library.
If matplotlib is installed it produces a PNG; otherwise it emits a
hand-built SVG that has the same content (no pip install required).

## Recommended next steps

1. **Add covariate adjustment.** Re-run with the core controls the
   original audit uses; switch from the basic OR estimator to the
   doubly-robust (DR) IPW + outcome-regression estimator that Sant'Anna &
   Zhao (2020) recommend.
2. **Apply the audit's stricter control rule.** Restrict the comparison
   pool to states that are shall-issue (`mayissue == 0`) and
   permit-required (`permitconcealed == 1`) throughout the relevant event
   window. This costs us some control units but makes the placebo
   condition more meaningful.
3. **Run more placebo outcomes.** Burglary, larceny, and prison
   admissions are good additions because they should not respond to
   carry permitting in any direct mechanism.
4. **Consider state-of-the-art alternatives** alongside CS21:
   Sun-Abraham interaction-weighted, BJS, de Chaisemartin-D'Haultfœuille,
   Borusyak-Jaravel-Spiess. CS21 with never-treated control is one of
   several reasonable choices; checking that several agree would strengthen
   any claim.
5. **Synthetic-control sanity check** for the largest individual treated
   states (e.g., Texas 2021, Florida 2023). With single-state cohorts
   this gives a transparent counterfactual that doesn't average across
   heterogeneous adopters.

The original audit's bottom-line recommendation — *do not write a paper
on this question with the current design* — still applies.

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
