### 1.X Stand-your-ground laws (Tufts `nosyg`)

**What this is.** A state-level indicator of whether a state has extended
its "castle doctrine" beyond the home and vehicle to public places, so
that a person who reasonably perceives a deadly threat has *no duty to
retreat* before using deadly force. These are commonly called
"stand-your-ground" (SYG) or "shoot first" laws. Florida's 2005 statute
is the well-known prototype, and a wave of about two dozen states adopted
similar provisions between 2006 and 2018. The SYG empirical literature
is centered on **homicide** (Cheng & Hoekstra 2013; Humphreys et al.
2017; McClellan & Tekin 2017; RAND 2020 evidence review), so this is the
outcome we use for headline reporting.

**Source.** Tufts/Siegel state firearm laws database, variable `nosyg`,
stored in [`data/tufts_state_firearm_laws.xlsx`](data/tufts_state_firearm_laws.xlsx)
with definitions in
[`data/tufts_state_firearm_laws_codebook.xlsx`](data/tufts_state_firearm_laws_codebook.xlsx).
The codebook entry says "A state with a stand your ground law is coded
as a 0. All other states are coded as a 1," so a state-year with
`nosyg == 1` retains a duty to retreat in public, and `nosyg == 0`
means SYG is in force. Treatment is the first 1->0 switch in `nosyg`.

**What we did.** Derived adoption cohorts directly from the Tufts panel,
then cross-checked five well-known cases (Florida 2005, Georgia 2006,
Texas 2007, Arizona 2010, Pennsylvania 2011) against the
[RAND State Firearm Laws Database](https://www.rand.org/research/gun-policy/state-laws.html);
all five matched exactly. The full Tufts adoption table is written to
[`outputs/stand_your_ground_audit/treatment_adoption_table.csv`](outputs/stand_your_ground_audit/treatment_adoption_table.csv).
Thirty states have switched to SYG between 1994 (Utah, the earliest
codification) and 2021 (Arkansas and North Dakota), spread across 13
adoption cohorts; 20 states (largely the Northeast, Mid-Atlantic, and
Pacific Coast) still have a duty to retreat through 2024 and serve as
the never-treated control pool.

**Methodology.** The same Callaway-Sant'Anna ATT(g, t) and stacked-DiD
machinery used for the other Tufts-coded policies (Sections on
permitless carry and red-flag) was applied with treatment direction
`1to0` on `nosyg`. The strict control rule requires `nosyg == 1` for
every year in the [g-5, g+5] window — i.e., the comparison state never
adopts SYG within the comparison window of the focal cohort. We report
the same four CS21 specifications ({OR, RA} x {broad, strict}) and
three stacked-DiD weighting choices (unweighted, regression-adjusted,
entropy-balanced). Outputs are in
[`outputs/stand_your_ground_cs/`](outputs/stand_your_ground_cs/) and
[`outputs/stand_your_ground_stackdd/`](outputs/stand_your_ground_stackdd/).

**Headline ATT.** For the SYG-focal outcome, **firearm homicide rate**,
the broad/RA Callaway-Sant'Anna estimator returns ATT = +0.54 deaths
per 100,000 (SE 0.04, z = +12.8); the strict-control RA version is
+0.47 (z = +10.9). Both are positive and large, consistent with the
mainstream finding in the SYG literature that these laws raise firearm
homicide. The placebo (motor-vehicle theft) is small and statistically
indistinguishable from zero in the RA spec (-3.50, z = -0.97 strict;
+0.41, z = +0.12 broad), which is reassuring.

**Caveats.** (i) The 2005-2007 wave is highly clustered, so identification
leans heavily on a few cohort-years, and stacked-DiD with EB weights
gives a meaningfully different firearm-homicide point estimate (-0.14,
z = -0.50) than CS21 — readers should treat the magnitude as more
uncertain than the z-statistics suggest. (ii) Pre-trend tests on the
suicide outcomes are noisy (Roth-Sant'Anna sensitivity bounds in
[`outputs/roth_sa_bounds/stand_your_ground_firearm_suicide_bounds.csv`](outputs/roth_sa_bounds/stand_your_ground_firearm_suicide_bounds.csv)
include zero at M = 1 across all CS21 specifications), and SYG laws are
not theoretically expected to move suicide outcomes, so we report
firearm-suicide ATTs only for completeness. (iii) Tufts codes Utah's
1994 statute as the earliest SYG provision; this aligns with RAND but is
older than what most reviews emphasize, and the result is largely
identified off the post-2005 cohorts in any case.
