### 1.X State minimum-age-21 handgun purchase laws (`age21handgunsale`)

**What this is.** State laws raising the minimum legal age for handgun
purchase above the federal floor. The federal floor is age 21 for
handgun purchases from a licensed dealer (FFL) but age 18 for both
private handgun transfers and all long-gun purchases. State age-21
handgun laws close the private-transfer gap so that a handgun cannot
legally be purchased at all by a buyer under 21 within the state's
borders.

**Source.** The Tufts indicator `age21handgunsale`. The codebook
defines this as: "Purchase of handguns from licensed dealers and
private sellers restricted to age 21 and older." A separate
`age21handgunpossess` variable covers the broader rule that a person
under 21 may not even possess a handgun (much rarer; very few states
have it).

**What we did with it.** Used `age21handgunsale` as-is, treating
adoption as the first 0->1 switch within a state's panel
([`scripts/run_cs_age21_handgun.py`](scripts/run_cs_age21_handgun.py)).

**Adoption history (1999-2023 panel window).** Twelve states already
have `age21handgunsale == 1` in 1999 -- CA, CT, DE, HI, IA, MA, MD,
MO, NE, OH, RI, SC -- and are excluded from both the treated and
never-treated pools because they have no usable pre-period. Eight
states adopt during the panel:

| Year | State |
|---|---|
| 2000 | NY |
| 2001 | NJ |
| 2010 | WV, WY |
| 2018 | FL, VT |
| 2019 | WA |
| 2023 | CO |

NY (2000) and NJ (2001) are dropped from the analysis sample because
their adoption year is too close to the panel start to allow a
five-year pre-period. The analytical cohorts are therefore four
(2010, 2018, 2019, 2023) covering six states. Two reversals on
already-treated states are documented (MO 2007, SC 2008) but do not
affect cohort derivation.

**Important caveats.** (a) The Tufts indicator captures purchase
restrictions only -- it does not capture the related
`age21handgunpossess` rule, which a small number of states (CA, HI,
NJ, IL) layer on top of the purchase restriction. (b) The headline
analysis estimates effects on **all-ages** firearm suicide and
homicide rates, because the project's mortality data
(`firearm_suicide_homicide_dataset_v2.tab`, 1949-2023) is not
age-stratified. The published youth-and-young-adult literature
(Webster, Anestis, etc.) targets the 18-20 age band specifically, so
the all-ages headline is a substantially diluted version of the
literature's preferred outcome and may even point in the opposite
direction if the modern adopter wave is on a different overall
firearm-suicide trend than non-adopters.

### 1.X.1 Causal-style results for the age-21 handgun law

**What this is.** Callaway-Sant'Anna ATT(g, t) estimates for the
effect of `age21handgunsale` adoption on six outcomes (firearm
suicide, non-firearm suicide, total suicide, firearm homicide, total
homicide, motor vehicle theft as placebo), plus a complementary
Cengiz-style stacked DiD with three weighting variants.

**Source.** Outputs in
[`outputs/age21_handgun_cs/`](outputs/age21_handgun_cs/),
[`outputs/age21_handgun_stackdd/`](outputs/age21_handgun_stackdd/),
and the Roth-Sant'Anna pre-trend bounds in
[`outputs/roth_sa_bounds/age21_handgun_firearm_suicide_bounds.csv`](outputs/roth_sa_bounds/age21_handgun_firearm_suicide_bounds.csv).
Methodology document in
[`outputs/age21_handgun_cs/methodology.md`](outputs/age21_handgun_cs/methodology.md).

**What we did.** Same four-spec grid as the other policy analyses
({OR, RA} x {broad, strict}), where the strict-control rule requires
a comparison state to have `age21handgunsale == 0` for every year of
each cohort's `[g-5, g+5]` window. Stacked DiD adds three weighting
schemes (unweighted, regression-adjusted, entropy-balanced) for
robustness.

**Headline numbers (CS21, broad/RA, all-ages).** The estimated
ATT for firearm suicide is **+0.43 per 100,000** (z = +4.5,
pre-trend z = +1.5 -- clean). The estimated ATT for firearm homicide
is **-0.52 per 100,000** (z = -10.1, pre-trend z = -8.0 -- BAD).
The placebo (motor vehicle theft) is large and significant in every
spec with badly rejecting pre-trends, indicating that adopters and
non-adopters are on different property-crime trajectories during the
2010-2023 window in a way the design cannot absorb.

**Reading the firearm-suicide result.** The positive sign contradicts
the published youth-stratified literature, which finds reductions in
the targeted age band. The most plausible explanations are:

1. **Outcome aggregation.** All-ages firearm suicide is dominated by
   adults 21+. Even a meaningful 18-20 effect would be a small slice
   of the total and could be masked by independent trends in 21+
   firearm suicide.
2. **Adopter-wave selection.** The post-1999 wave is small (six
   states, four cohorts) and dominated by post-Parkland adopters
   (FL 2018, VT 2018, WA 2019, CO 2023). These states may share
   trends unrelated to the policy itself.
3. **Pre-trend extrapolation.** The Roth-Sant'Anna bounds at e = +1
   and M = 1 (assuming the post-period continues the observed
   pre-period slope at full strength) flip the firearm-suicide
   point estimate to negative territory but the CI typically
   includes zero, so the headline does not survive even modest
   pre-trend adjustment.

**Reading the firearm-homicide result.** Negative and statistically
significant in every spec, but the pre-trend rejects in every spec
at |z| > 7 except the strict/OR specification (|z| = 1.2, borderline).
The homicide reduction is unlikely to be driven by the policy mechanism
(age-21 handgun rules target buyers, not the broader population that
drives most firearm-homicide variation), so the strong pre-trend is
the more plausible read: states adopting the law are also experiencing
broader homicide reductions for unrelated reasons.

**Important caveats.** This analysis replicates neither the
youth-stratified design of the published age-21 literature nor the
individual-level mechanism studies that the published causal claim
ultimately rests on. The all-ages aggregate is a coarse instrument
for measuring a policy that is mechanically targeted at a narrow age
band. Until age-stratified mortality data is added to the project,
the responsible read of these results is "the all-ages design cannot
recover the published youth-band effect, and the placebo failure
suggests broader identification problems specific to the modern
adopter wave."
