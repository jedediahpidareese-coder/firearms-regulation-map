# Spatial regression-discontinuity on state borders — methodology

**Date:** 2026-05-01
**Estimator module:** [`scripts/lib_rdd.py`](../../scripts/lib_rdd.py)
**Per-policy runners:** [`scripts/run_rdd_permitless_carry.py`](../../scripts/run_rdd_permitless_carry.py),
[`run_rdd_red_flag.py`](../../scripts/run_rdd_red_flag.py),
[`run_rdd_ubc.py`](../../scripts/run_rdd_ubc.py)
**Per-policy output folders:** `outputs/{permitless_carry,red_flag,ubc}_rdd/`
**Diagnostics + literature scan:** `outputs/rdd_diagnostics/`

This document describes the spatial regression-discontinuity (RDD) design
applied to firearm policy at the U.S. county grain. It complements — does
not replace — the state-level Callaway–Sant'Anna (`outputs/{policy}_cs/`)
and Cengiz-style stacked DiD (`outputs/{policy}_stackdd/`) analyses.

---

## Design

We adapt the Dube–Lester–Reich (2010, *Restat*) contiguous-county-pair
identification strategy to firearm policy. The estimating equation for a
single policy and outcome is

```
Y_{i,t} = β · treat_{i,t}
        + α_i  (county fixed effect)
        + γ_{pair, t}  (state-pair × year fixed effect)
        + ε_{i,t}
```

estimated by iterative within-FE Frisch–Waugh–Lovell demeaning
(`scripts/lib_rdd._demean_iterative`).

The identifying variation is the *within-pair, within-year* deviation
between counties on opposite sides of a state border that experience
different policy regimes. State-pair × year FE absorb everything common
to both sides of a border-segment in a given year (regional shocks,
shared media markets, weather, etc.). County FE absorb time-invariant
county characteristics (population, baseline crime levels, geography).

Sample restriction: counties with `distance_to_nearest_other_state_km ≤
bandwidth` from the geometry layer
([`data/processed/county_border_distances.csv`](../../data/processed/county_border_distances.csv),
documented in Section 2.12 of the data appendix).

State-pair labels: unordered `{state_i, nearest_other_state_i}`, e.g. the
`{IL, IN}` pair contains all border-strip counties in either Illinois or
Indiana whose nearest other-state centroid is in the partner state.

Hawaii (state FIPS 15) and Puerto Rico (72) are excluded entirely — for
both, the nearest other-state centroid is across an ocean and not a
meaningful comparison.

---

## Outcomes and stratification

We split outcomes into two strata that have very different identification
properties under this design:

**Primary outcomes** (true county-level, real within-state variation):

| Variable | Source |
|---|---|
| `county_violent_crime_rate` | Kaplan UCR aggregated to county-year |
| `county_murder_rate` | Kaplan UCR |
| `county_property_crime_rate` | Kaplan UCR |
| `county_burglary_rate` | Kaplan UCR (placebo) |
| `county_motor_vehicle_theft_rate` | Kaplan UCR (placebo) |

**Secondary outcomes** (state-joined-down mortality — *no* within-state
variation by construction; reported for completeness only):

| Variable | Source |
|---|---|
| `state_firearm_suicide_rate` | Kalesan-style v2, joined down |
| `state_total_suicide_rate` | v2 |
| `state_nonfirearm_suicide_rate` | v2 (derived = total − firearm) |
| `state_firearm_homicide_rate` | v2 |

**Critical caveat for the secondary outcomes.** Every county in California
in 2020 carries California's value of `state_firearm_suicide_rate`. The
RDD on these outcomes therefore reduces to a population-weighted state-
level comparison restricted to border counties — not a county-grain
identification gain. We report them so the methodology is honest and
comparable to the existing state-level CS21 and stacked-DiD results, but
the interpretive weight should sit on the primary (true county-level)
outcomes.

---

## Spec grid (10 specifications per policy × outcome)

The per-policy runner runs the following 10-cell robustness battery:

| Spec name | bw_km | donut_km | FE | Cluster | Covariates | Spillover filter |
|---|---|---|---|---|---|---|
| `headline` | 100 | 0 | pair × year | state | none | off |
| `bw_50km` | 50 | 0 | pair × year | state | none | off |
| `bw_200km` | 200 | 0 | pair × year | state | none | off |
| `donut_10km` | 100 | 10 | pair × year | state | none | off |
| `donut_25km` | 100 | 25 | pair × year | state | none | off |
| `fe_twoway` | 100 | 0 | county + year | state | none | off |
| `cluster_pair` | 100 | 0 | pair × year | state-pair | none | off |
| `cluster_twoway` | 100 | 0 | pair × year | state + year | none | off |
| `with_covariates` | 100 | 0 | pair × year | state | RA_COVARIATES | off |
| `drop_spillover` | 100 | 0 | pair × year | state | none | **on** |

`RA_COVARIATES` = `["unemployment_rate", "share_white_nh",
"share_age_15_24", "share_age_25_44", "share_bachelors_plus"]`. We omit
log(population) because pair × year FE already absorbs cross-sectional
level differences.

`drop_spillover`: per Knight (2013, *AEJ:EP*), border counties may be
partly treated by their *neighbor's* policy via gun flows. This filter
drops state-pair-years where the *control-side* state itself borders a
third state with the same policy already in force, removing the most
contaminated comparisons.

Per outcome × policy: 10 robustness rows. Per policy: 9 outcomes × 10
specs = 90 robustness rows + 9 headline rows + 99 event-study rows
(11 event-times × 9 outcomes).

---

## Headline results (B = 100 km, FE = pair × year, cluster = state)

| Policy | n cohorts | n treated states |
|---|---|---|
| Permitless carry (`law_permitconcealed`, 1→0) | 10 | 27 |
| Civil red-flag (`law_gvro`, 0→1) | 6 | 15 |
| UBC (`law_universal`, 0→1) | 8 | 11 |

### Permitless carry

| Outcome | β | SE | z | n |
|---|---:|---:|---:|---:|
| county_violent_crime_rate | −1.31 | 6.48 | −0.20 | 31,248 |
| **county_murder_rate** | **−1.18** | **0.55** | **−2.16*** | 31,248 |
| county_property_crime_rate | +46.63 | 23.92 | +1.95 | 31,248 |
| county_burglary_rate | +11.91 | 6.25 | +1.91 | 31,248 |
| county_motor_vehicle_theft_rate | +1.64 | 3.52 | +0.47 | 31,248 |
| **state_firearm_suicide_rate** | **+0.36** | **0.11** | **+3.29*** | 29,295 |
| **state_total_suicide_rate** | **+0.54** | **0.17** | **+3.24*** | 29,295 |
| state_nonfirearm_suicide_rate | +0.18 | 0.10 | +1.79 | 29,295 |
| **state_firearm_homicide_rate** | **+0.28** | **0.13** | **+2.13*** | 29,271 |

The state-joined suicide and firearm-homicide signals replicate the
existing CS21 results (the project's headline state-level finding was
+0.6/100k total suicide; the RDD restricted to the border subsample
recovers a similar +0.54/100k). The county-grain murder result (−1.18/100k)
is new — and goes the opposite direction from the state-joined firearm
homicide. The two outcomes measure different things (county-level all-
method murder vs. state-level firearm-only homicide), so opposite signs
are not internally inconsistent, but the divergence is worth flagging
in the report.

### Civil red-flag

| Outcome | β | SE | z | n |
|---|---:|---:|---:|---:|
| county_violent_crime_rate | −23.81 | 13.52 | −1.76 | 31,248 |
| county_murder_rate | −2.18 | 1.14 | −1.91 | 31,248 |
| county_property_crime_rate | −16.14 | 33.81 | −0.48 | 31,248 |
| county_burglary_rate | +12.83 | 9.66 | +1.33 | 31,248 |
| county_motor_vehicle_theft_rate | −3.14 | 5.79 | −0.54 | 31,248 |
| **state_firearm_suicide_rate** | **−0.70** | **0.06** | **−11.10*** | 29,295 |
| **state_total_suicide_rate** | **−0.55** | **0.11** | **−5.15*** | 29,295 |
| state_nonfirearm_suicide_rate | +0.16 | 0.09 | +1.84 | 29,295 |
| state_firearm_homicide_rate | +0.19 | 0.21 | +0.94 | 29,271 |

**Notable divergence from existing CS21:** the state-level CS21 found
firearm-homicide ATT = −0.14 (broad/RA, the project's only previously-
robust effect). The RDD restricted to the border subsample finds
+0.19 (NS). One interpretation: the state-level CS21 effect comes from
within-state heterogeneity — adopting states' interior counties drive
the average — and the border-county comparisons (which are what the RDD
identifies on) don't show the effect. This narrows the policy's
implied mechanism: red-flag effects are not concentrated at borders.

The firearm-suicide RDD finds a much larger negative effect than the
state-level CS21 (−0.70 vs. CS21 's pre-trend-confounded estimates).
Pre-trend bounds are still required (Phase 5j Roth-SA bounds applied to
state-level only; an RDD analog is v2).

### UBC

| Outcome | β | SE | z | n |
|---|---:|---:|---:|---:|
| **county_violent_crime_rate** | **+19.04** | **8.99** | **+2.12*** | 31,248 |
| **county_murder_rate** | **−0.60** | **0.15** | **−3.89*** | 31,248 |
| **county_property_crime_rate** | **+95.91** | **47.95** | **+2.00*** | 31,248 |
| county_burglary_rate | +42.44 | 22.58 | +1.88 | 31,248 |
| county_motor_vehicle_theft_rate | −2.73 | 9.47 | −0.29 | 31,248 |
| **state_firearm_suicide_rate** | **−0.26** | **0.12** | **−2.19*** | 29,295 |
| **state_total_suicide_rate** | **−0.44** | **0.13** | **−3.35*** | 29,295 |
| state_nonfirearm_suicide_rate | −0.18 | 0.10 | −1.87 | 29,295 |
| state_firearm_homicide_rate | +0.06 | 0.25 | +0.23 | 29,271 |

**First UBC-significant suicide signal in the project.** The state-level
CS21 on UBC was largely null. The RDD on the same outcome finds
−0.26**/−0.44*** for firearm/total suicide. The county-grain crime
signals are mixed (violent up, murder down, property up) and warrant
careful sensitivity-sweep treatment before any interpretation. Pre-
trend diagnostics from Agent B flagged UBC as having noisy pre-trends;
the headline numbers should be read with that caveat.

---

## Cross-policy patterns worth flagging

1. **County-level murder rate decreases under all three policies**
   (β = −1.18, −2.18, −0.60). This consistent pattern likely reflects
   secular county-murder trend differentially absorbing the FE structure;
   it does not necessarily mean all three policies reduce murder. Flag
   for the discussion section: this is a possible specification artifact
   that the sensitivity sweep should test (e.g., does it survive a state
   × year linear trend?).

2. **State-joined mortality outcomes are more "significant" than county-
   level outcomes** in many cells. This is an artifact of design: state-
   joined outcomes have less within-state noise, so SE shrinks. The
   apparent precision is largely about the constructed denominator, not
   identification.

3. **The red-flag headline split** — CS21 found firearm homicide −0.14;
   RDD finds +0.19 NS. Two different identifying variations. The
   discussion should explain that the RDD identifies on border-county
   contrasts only, while CS21 identifies on state-time variation across
   the whole panel. If the policy effect is *uniform across counties
   within an adopting state*, both estimators recover it; if it is
   *concentrated in interior counties* (e.g., where local prosecutors
   actually invoke ERPO petitions), the RDD will miss it.

---

## Lineage and reviewer-friction (from `outputs/rdd_diagnostics/literature_scan.md`)

- **Methodological lodestar:** Dube, Lester, Reich (2010, *RESTAT*) +
  the 2024 NBER w32901 reassessment. Inherits the Neumark-Wascher
  critique that pair × year FE absorbs too much identifying variation;
  we report `fe_twoway` (county + year only) as a robustness.
- **Direct firearm analog:** Knight (2013, *AEJ:EP*) — gun flow
  spillovers across state borders. Our `drop_spillover` spec partially
  addresses this; a Conley-style spatial SE is v2.
- **Effect-size benchmarks:** Webster/Crifasi PTP papers found ~16–47%
  homicide responses; Donohue–Aneja–Weber (2019) RTC +13–15% violent
  crime; Luca-Malhotra-Poliquin (2017) waiting periods −17% gun homicide;
  Kivisto-Phalen (2018) red-flag −7-14% firearm suicide. Our findings
  are mostly in the lower-magnitude end of these ranges.
- **The closest existing border-distance firearm design** is Ashworth &
  Kozinetz (2021), a cross-sectional negative-binomial that finds
  border distance negatively associated with firearm homicide. Our
  panel-DiD adaptation closes the cross-sectional confounding gap they
  identified.

---

## Outputs

| File | What |
|---|---|
| `headline.csv` | One row per outcome at the headline spec |
| `robustness.csv` | All 10 specs × 9 outcomes per policy = 90 rows |
| `event_study.csv` | One row per (outcome, event_time) at the headline spec |
| `cohort_n.csv` | Cohort sizes |
| `figures/event_study_primary.svg` | 4-panel event study, primary outcomes |
| `figures/event_study_secondary.svg` | 4-panel event study, state-joined outcomes |

---

## What is NOT in this v1

- **Sensitivity sweep** (bandwidth = 25/50/100/200/400 km × donut =
  0/10/25/50 km × polynomial-in-distance order × covariates). Planned as
  a separate background task following the runs above.
- **True distance-to-border** (currently the proxy is distance to the
  nearest other-state population centroid, not the actual state line).
  Adding shapely + Census state polygons is a v2 if the polynomial-in-
  distance specs prove sensitive to the proxy.
- **Roth–Sant'Anna pre-trend bounds for the RDD specifications.**
  Already applied to state-level CS21 in `outputs/roth_sa_bounds/`;
  an RDD analog is v2.
- **Conley spatial-correlation SE.** The current SE options are state,
  state-pair, and two-way state × year. Conley spatial SEs would be
  more appropriate for the spillover concern but require more setup.
