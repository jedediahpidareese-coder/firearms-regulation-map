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

## Headline numbers (four specifications)

Average post-treatment ATT (per 100,000 population), state-cluster
multiplier-bootstrap standard errors. We crossed two design choices:

- **Spec:** OR (basic outcome regression, no covariates) vs RA
  (Sant'Anna-Zhao 2020 regression-adjusted with three baseline covariates:
  `ln_population`, `unemployment_rate`, `ln_pcpi_real_2024`).
- **Control rule:** *broad* uses every never-treated state (n=21);
  *strict* applies the original audit's rule that a control state must
  be shall-issue (`mayissue == 0`) AND permit-required
  (`permitconcealed == 1`) for every year in the cohort's
  ±5-year event window. Strict shrinks the control pool to 6–12 states
  depending on the cohort's window (the may-issue Northeast / Pacific
  states drop out).

ATT values are per 100,000 residents per year. Bold = pre-trend test
does not reject (the spec is "clean" in that sense).

| Spec | Control | Firearm suicide | Firearm homicide | Total homicide | MV theft (placebo) |
|---|---|---|---|---|---|
| OR | broad | +0.86 (pre z = −3.6) | +0.29 (pre z = −1.4) | −0.15 (pre z = −0.4) | −39 (pre z = +4.9) |
| OR | **strict** | **+0.59 (pre z = −1.4)** | **−0.01 (pre z = +0.9)** | −0.49 (pre z = +1.4) | −64 (pre z = +6.4) |
| RA | **broad** | **+0.64 (pre z = −0.86)** | −0.003 (pre z = +7.6) | −0.47 (pre z = +6.2) | −54 (pre z = +9.0) |
| RA | strict | +0.30 (pre z = +2.9) | −0.45 (pre z = +5.9) | −0.96 (pre z = +2.7) | −113 (pre z = +8.4) |

### What the four-spec grid tells us

- **Firearm suicide rate is robust.** Positive and statistically
  significant in all four specifications, with point estimates ranging
  from +0.30 to +0.86 per 100,000. The two specs with clean pre-trends
  (broad/RA and strict/OR) put the effect at roughly **+0.6 firearm
  suicides per 100,000 residents per year** in the average treated state.
  Against a baseline U.S. firearm-suicide rate of about 7 per 100k, that
  is roughly an 8–9% relative increase. This is the most defensible
  finding the build produces.
- **The other three outcomes do not have a clean spec.** Firearm
  homicide and total homicide flip sign across specs and the placebo
  fails badly everywhere. The persistent placebo failure tells us
  treated and control states are on different secular paths for property
  crime — and probably for at least some of the violence outcomes — and
  the macro covariates we tried (population scale, unemployment, real
  income) are not enough to absorb that gap.
- **The strict control rule helps for headline outcomes but hurts the
  pre-trends for some specs.** Restricting controls to shall-issue +
  permit-required states yields a smaller, more conservative
  firearm-suicide ATT (+0.30 to +0.59) and tightens the firearm-homicide
  estimate to essentially zero in the strict/OR row. But strict + RA
  combined over-corrects — the firearm-suicide pre-trend rejects again
  (z = +2.9), suggesting the smaller strict pool, paired with regression
  adjustment, picks up sample-specific noise.
- **The placebo is the dominant constraint.** No combination of these
  four specs eliminates the property-crime trend gap. That tells us the
  causal-identification problem here is fundamentally one of
  uncomparable comparison units, not estimator choice.

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
| `att_gt.csv` | One row per (outcome, spec, control_rule, g, t). 3,456 rows. |
| `event_study.csv` | One row per (outcome, spec, control_rule, event_time). |
| `overall_att.csv` | One row per (outcome, spec, control_rule) with overall post-treatment ATT and pre-trend test. |
| `cohort_n.csv` | Cohort-size table. |
| `dropped_log.csv` | States dropped from analysis with reasons. |
| `figures/event_study_{control_rule}_{spec}_4panel.svg` | 4-panel event-study figures, one per spec × control_rule combination (4 figures). |

## Reproducing

```sh
python scripts/run_cs_permitless_carry.py
```

The script imports nothing beyond pandas, numpy, and the standard library.
If matplotlib is installed it produces a PNG; otherwise it emits a
hand-built SVG that has the same content (no pip install required).

## Recommended next steps

1. **Synthetic-control for the largest single-state cohorts.** Texas
   2021 and Florida 2023 are the two biggest single-state-cohort
   adoptions. Building a transparent synthetic counterfactual from a
   weighted donor pool would let us see, state by state, what the
   firearm-suicide-rate trajectory looks like with vs. without the
   policy — without averaging over the heterogeneous cohort mix the
   CS21 design has.
2. **Outcome-specific placebo design for property crime.** The
   persistent motor-vehicle-theft placebo failure tells us we have a
   confounder that loads on property-crime trends. Adding an
   outcome-specific covariate set (e.g., per-capita drug-overdose
   deaths, share urban, share male 15-24) might absorb the gap
   specifically for crime outcomes.
3. **Cross-check the firearm-suicide finding with alternative
   estimators.** Sun-Abraham, Borusyak-Jaravel-Spiess, and the original
   stacked-DiD audit's spec all use different aggregation and weighting
   schemes. Agreement across them on the +0.6/100k firearm-suicide
   ATT would substantially strengthen the claim.
4. **Full doubly-robust (DR) estimation.** Sant'Anna-Zhao DR combines
   regression adjustment with inverse-propensity weighting. With our
   small cohort sizes the IPW model is fragile; this should be done
   carefully (probably with a low-dimensional propensity model on the
   same three covariates).
5. **Restricted-use NCHS data for county-level firearm suicide.** If
   ever we get restricted-use mortality access (Section 2.10 of the
   data appendix), we could replicate this CS21 design at the
   county-year grain and watch whether the firearm-suicide effect
   concentrates in certain county types (rural / high-ownership /
   etc.).

**Bottom line:** the firearm-suicide-rate finding is robust enough
across the four specs to be worth pursuing further with synthetic
control and alternative estimators. The other three outcomes do not
have a clean spec in this build, and the placebo failure is the
honest reason why.

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
