# Minimum age 21 for handgun purchase -- Callaway-Sant'Anna ATT(g, t)

**Date:** 2026-04-30
**Script:** [`scripts/run_cs_age21_handgun.py`](../../scripts/run_cs_age21_handgun.py)
**Output folder:** `outputs/age21_handgun_cs/`

This is the fourth policy analysis in the project, following the
[permitless-carry](../permitless_carry_cs/methodology.md),
[civil red-flag](../red_flag_cs/methodology.md), and
[universal background check](../ubc_cs/methodology.md) analyses. The
estimator, panel, outcome menu, bootstrap procedure, and inference
defaults are identical to those analyses; the only differences are the
treatment definition, cohort wave, and strict-control rule.

## What "minimum age 21 for handgun purchase" means here

Federal law sets the minimum age for handgun purchase from a federally
licensed firearms dealer (FFL) at 21, but the floor for **private**
handgun transfers and for **long gun** purchases is 18. State laws can
raise the floor above 18 for private handgun transfers. The Tufts
codebook decomposes age-21 handgun rules into several variants:

| Variable | What it means |
|---|---|
| `age21handgunsale` | Handgun purchase from BOTH licensed dealers AND private sellers restricted to age 21+, with no parental-consent exemption |
| `age21handgunsalecommercial` | Same restriction but only against licensed dealers |
| `age21handgunsaleprivate` | Same restriction but only against private sellers |
| `age21handgunpossess` | Handgun **possession** (not just purchase) restricted to age 21+ |

We use **`age21handgunsale`** as the treatment variable because it is the
joint indicator that captures the policy of interest -- raising the
minimum age for *any* handgun purchase regardless of channel. States
that close only one channel (commercial-only or private-only) leave a
substitution path that arguably weakens the treatment, so the cleanest
treatment definition is the joint variable.

## Cohorts

Treatment is the first 0->1 switch in `age21handgunsale` for a state
that begins the panel (1999) coded 0. Twelve states already have
`age21handgunsale == 1` in 1999 (CA, CT, DE, HI, IA, MA, MD, MO, NE,
OH, RI, SC); these are excluded as already-treated and are also
excluded from the never-treated control pool because they have no
usable pre-period.

| Cohort | n states | states |
|---|---|---|
| 2010 | 2 | WV, WY |
| 2018 | 2 | FL, VT |
| 2019 | 1 | WA |
| 2023 | 1 | CO |

Six states across four cohorts. **NY (2000) and NJ (2001)** are
dropped from the analysis sample because adoption preceded
`ANALYSIS_YEARS[0] + 5 = 2004` -- there is no five-year pre-period
inside the panel. They are documented in the audit
`treatment_adoption_table.csv` and `dropped_log.csv` for transparency.

The **modern wave (FL/VT 2018, WA 2019, CO 2023) is the post-Parkland
political response** that the policy literature focuses on. The two
2010 movers (WV, WY) are quieter Republican-state changes that arrived
on a different political track. We do not split by adopter profile in
the headline pool because cohort sizes are already small (1-2 states
per cohort).

42 never-treated control states. The strict pool -- states with
`age21handgunsale == 0` for every year of the cohort's `[g-5, g+5]`
window -- contains 30 states for the 2010 cohort and 32 states for the
2018/2019/2023 cohorts. (The strict cohort sizes are larger than for
red-flag because age-21-handgun is a less-common policy; many control
states clearly have no plausible alternative variant.)

There are two minor reversals on already-treated states (MO 2007, SC
2008) that are documented in the adoption table but do not affect
cohort derivation -- they happen on states that started 1999 already
coded 1 and therefore never enter the treated pool.

## Headline numbers (four specifications)

Same 4-spec grid as the prior policy analyses: `{OR, RA} x {broad,
strict}`. **Bold** pre-trend z = does not reject (the spec is "clean"
in that sense).

| Spec | Control | Firearm suicide | Firearm homicide | Total homicide | MV theft (placebo) |
|---|---|---|---|---|---|
| OR | broad | +0.69** (pre z = **+1.09**) | -0.62** (pre z = -3.16) | -0.32** (pre z = -2.29) | -8.3 (pre z = -12.6) |
| OR | strict | +0.58** (pre z = **+1.59**) | -0.73** (pre z = **-1.21**) | -0.37** (pre z = **-1.60**) | -10.7** (pre z = -10.1) |
| **RA** | **broad** | +0.43** (pre z = **+1.54**) | -0.52** (pre z = -8.04) | -0.33** (pre z = -3.60) | -28.2** (pre z = -15.7) |
| RA | strict | +0.16 (pre z = **+1.73**) | -0.46** (pre z = -7.16) | -0.36** (pre z = -3.00) | -36.4** (pre z = -9.1) |

### What the four-spec grid tells us

- **Firearm-suicide direction is positive** (+0.16 to +0.69 per
  100,000) and statistically significant in three of four specs. This
  is the OPPOSITE direction from the literature on age-21 laws, which
  finds reductions in youth firearm-suicide (Webster et al., Anestis).
  Importantly, the pre-trend tests do NOT reject in any spec
  (z = +1.1 to +1.7), so the design is not obviously confounded by an
  Ashenfelter-dip story. The plausible explanations for the wrong-sign
  finding are: (a) the headline is at the all-ages level and the youth
  effect (literature target) is a small slice of the overall total;
  (b) the modern adopter wave is dominated by post-Parkland states
  (FL, VT, WA, CO) that may also be on a separate suicide trajectory
  unrelated to the policy; (c) the small cohort count means the
  pooled estimate is heavily weighted by 1-2 states per cohort.
- **Firearm homicide is significantly negative** (-0.46 to -0.73 per
  100,000) in every spec, BUT **the pre-trend rejects in every RA
  spec at |z| > 7**. The OR specs have weaker pre-trends (|z| = 1.2 to
  3.2) but they still reject in the broad/OR spec. The
  strict-control/OR spec is the cleanest pre-trend (z = -1.21,
  borderline), and there the headline is -0.73 per 100,000. We do
  NOT lead with this number because the broad/RA spec, which is the
  primary spec for the other policy analyses in this project, has a
  badly rejecting pre-trend (z = -8.0).
- **Total homicide moves with firearm homicide**, also significantly
  negative across specs but with rejecting pre-trends.
- **Motor vehicle theft (placebo) is large and rejects in every
  spec** with pre-trend |z| > 9. This is a serious concern: the
  placebo says adopting and non-adopting states are on different
  property-crime trajectories during the 2010-2023 window in a way
  the design cannot absorb. The pattern resembles the
  permitless-carry analysis's placebo failure rather than the cleaner
  red-flag placebo.
- **Non-firearm suicide rises substantially** (+1.27 to +1.48 per
  100,000) with badly rejecting pre-trends in every spec
  (|z| = 8 to 13). Total suicide rises in every spec. This pattern
  rules OUT a substitution-only story (a rising firearm suicide
  series accompanied by an even larger rising non-firearm suicide
  series) and is more consistent with both being driven by a common
  state-trend confounder.

**Headline finding for state minimum-age-21 handgun laws (all-ages):**
The policy is associated with a **statistically significant INCREASE
in firearm suicide** of about +0.43 per 100,000 (broad/RA, z = +4.5,
clean pre-trend). The firearm-homicide reduction (-0.52 per 100,000,
broad/RA) has a strongly rejecting pre-trend and the placebo also
fails, so we treat it as not credible.

This headline contradicts published youth-stratified work (Webster,
Anestis). The most likely reasons:

1. **Outcome aggregation.** The published literature looks at the
   18-20 age band specifically; this design uses all-ages firearm
   suicide because the project does not have age-stratified mortality
   data. If the policy reduces 18-20 firearm suicide but coincides
   with broader trends in 21+ firearm suicide that go the other way,
   the all-ages estimate could mask the youth-band effect entirely.
2. **Cohort selection.** The published work draws heavily on
   pre-1999 adopters (CA, CT, MA, MD, etc.) that are excluded here as
   already-treated. The post-1999 wave is a smaller, politically
   different group.
3. **Ashenfelter-dip in reverse.** Adopters might be on rising
   firearm-suicide trajectories before adoption AND continue to rise
   after, with the post-adoption rise misattributed to the law. The
   pre-trend slopes (+0.25 per year for OR/broad) are consistent
   with this.

The Roth-Sant'Anna pre-trend bounds at e=+1
(`outputs/roth_sa_bounds/age21_handgun_firearm_suicide_bounds.csv`)
show that even modest pre-trend extrapolation (M=1, projecting the
pre-period slope forward unchanged) flips the sign of the
firearm-suicide ATT to negative, but the CI typically includes zero.
This is the opposite-direction analog of the red-flag
firearm-suicide caveat: the pre-trend is small enough that it is
unlikely to be the WHOLE story, but it is large enough relative to
the post-period coefficients that you cannot trust the headline at
face value.

## Comparison to the other policy analyses

| | Permitless carry | Red-flag | UBC | Min age 21 handgun |
|---|---|---|---|---|
| Adopter profile | Mostly Republican, 2010-2023 | Mostly Democratic, 2016-2023 | Mostly Democratic, 2013-2021 | Mixed (WV/WY 2010, FL/VT 2018, WA 2019, CO 2023) |
| Treated cohorts (n states) | 9 cohorts (25 states) | 5 (13) | 9 (10) | 4 (6) |
| Headline outcome | Firearm suicide (+0.6 / 100k, robust) | Firearm homicide (-0.14, broad/RA) | Firearm suicide (NS, large CI) | Firearm suicide (+0.4, opposite direction from literature) |
| Placebo (MVT) | **Fails badly** | Cleaner | Mixed | **Fails badly** |
| Pre-trends | Some specs clean | Firearm-homicide spec clean | Mostly clean | Firearm-suicide clean; everything else rejects |

The age-21 handgun analysis sits between permitless-carry and
red-flag in identification quality. The placebo failure resembles the
permitless-carry analysis (large and significant in every spec). But
unlike permitless-carry, the headline outcome (firearm suicide) has a
clean pre-trend in every spec. The wrong-sign result is the most
plausible read here: either the all-ages aggregation is masking a
youth-targeted effect, or the modern adopter wave's confounders
overpower the policy mechanism in the pooled estimate.

## Sample, estimator, and inference

Same as the other policy analyses (see
[the permitless-carry methodology document](../permitless_carry_cs/methodology.md)
sections "Sample" through "Two specs"). The only differences:

- **Treatment variable:** `age21handgunsale` (instead of
  `permitconcealed` / `gvro` / `universal`).
- **Treatment direction:** 0->1 first switch.
- **Strict rule:** the comparison state must have
  `age21handgunsale == 0` for every year in `[g-5, g+5]`. Single rule;
  there is no plausible "alternative channel" age-21 variant
  analogous to UBC's universalpermit.

All shared logic lives in [`scripts/cs_lib.py`](../../scripts/cs_lib.py).

## Outputs

| File | What |
|---|---|
| `att_gt.csv` | One row per (outcome, spec, control_rule, g, t). |
| `event_study.csv` | One row per (outcome, spec, control_rule, event_time). |
| `overall_att.csv` | One row per (outcome, spec, control_rule). |
| `cohort_n.csv` | Cohort sizes. |
| `dropped_log.csv` | States dropped from analysis with reasons. |
| `figures/event_study_{control_rule}_{spec}_4panel.svg` | 4 figures. |

## Recommended next steps

1. **Get age-stratified mortality data** (e.g., CDC WONDER 5-year age
   bands). The published literature consensus is that age-21 laws
   reduce 18-20 firearm suicide. The all-ages aggregation here may
   wash out the youth-targeted effect entirely.
2. **Roth-Sant'Anna honest pre-trend bounds for firearm homicide.** The
   homicide effect has a strong pre-trend; honest bounds would say
   how much pre-trend extrapolation is required to "explain away" the
   post-period coefficients.
3. **Synthetic control for the largest single-state cohorts** (FL
   2018, WA 2019, CO 2023). Single-state cohorts get arithmetic
   weight equal to multi-state cohorts in the CS21 aggregation, but
   their inference is one-cluster and probably understated.
4. **Stratify by adopter wave.** Splitting the 2010 cohort (WV, WY) from
   the post-Parkland wave (FL, VT, WA, CO) might reveal that the
   wrong-sign finding is driven by one but not the other.
