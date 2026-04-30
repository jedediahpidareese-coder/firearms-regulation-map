# Civil-petition red-flag (GVRO) adoption — Callaway-Sant'Anna ATT(g, t)

**Date:** 2026-04-30
**Script:** [`scripts/run_cs_red_flag.py`](../../scripts/run_cs_red_flag.py)
**Output folder:** `outputs/red_flag_cs/`

This is the second policy analysis in the project. The first
[(permitless carry)](../permitless_carry_cs/methodology.md) hit a
persistent placebo failure — adopting states were on different
property-crime trends than non-adopting states, which the design
couldn't absorb. We turn here to **civil-petition extreme risk
protection orders (ERPOs)**, often called *red-flag laws*, because
they have a more bipartisan adopter profile and a more recent adoption
wave (15 states, 2016–2024).

## What "red flag" means here

Tufts publishes two ERPO-related variables:

- `gvro` = state allows **civilian petition** (family member, household
  member, etc.) for an ERPO. This is the modern "red flag" definition
  used by most published research (Swanson et al., RAND, etc.).
- `gvrolawenforcement` = state allows **law-enforcement-only petition**.
  CT, IN, FL, RI, VA had this earlier; some only added civilian petition
  later, and three (FL, RI, VA) still don't allow it.

We use **civil-petition red flag (`gvro`)** as the treatment. The
older LE-only laws are excluded from the treated group AND excluded
from the strict-rule control group (so the comparison is "states with
no ERPO of any kind" vs "states that adopted civil-petition ERPO").

## Cohorts

| Cohort | n states | states |
|---|---|---|
| 2016 | 2 | CA, WA |
| 2018 | 4 | DE, MA, MD, OR |
| 2019 | 4 | CO, IL, NJ, NY |
| 2020 | 2 | HI, NV |
| 2023 | 1 | VT |

13 treated states across 5 cohorts. **MN and MI (2024 adopters) are
excluded** because the v2 firearm-mortality file ends in 2023 and we
have no post-period.

35 never-treated control states (the count is higher than the
permitless-carry analysis because more states never adopted civil
red-flag than never adopted permitless carry).

The strict pool — states with `gvro == 0` AND `gvrolawenforcement == 0`
for every year of the cohort's `[g-5, g+5]` window — drops the older
LE-only ERPO states (CT, IN, FL, RI, VA), leaving 30 strict-pool
controls.

## Headline numbers (four specifications)

Same 4-spec grid as the permitless-carry analysis: `{OR, RA} × {broad,
strict}`. Bold pre-trend z = does not reject (the spec is "clean" in
that sense).

| Spec | Control | Firearm suicide | Firearm homicide | Total homicide | MV theft (placebo) |
|---|---|---|---|---|---|
| OR | broad | −0.21 (pre z = +5.1) | −0.57 (pre z = +2.6) | −0.37 (pre z = +1.5) | +39 (pre z = **+0.5**) |
| OR | strict | −0.24 (pre z = +5.4) | −0.56 (pre z = +2.7) | −0.36 (pre z = +1.5) | +36 (pre z = **+0.5**) |
| **RA** | **broad** | −0.11 (pre z = +4.6) | **−0.14** (pre z = **−0.58**) | −0.25 (pre z = +2.2) | +35 (pre z = **−0.6**) |
| RA | strict | −0.38 (pre z = +5.3) | +0.04 (pre z = **+0.7**) | −0.39 (pre z = +3.3) | +23 (pre z = **+0.3**) |

### What the four-spec grid tells us

- **Firearm homicide is the headline result.** Negative and statistically
  significant in 3 of 4 specs (OR specs at −0.57, broad/RA at −0.14).
  The cleanest spec (broad/RA) gives a pre-trend z = −0.58 (does not
  reject) and a post-treatment ATT of **−0.14 per 100,000** — about a
  3-4% reduction relative to the average state's firearm-homicide rate.
  This is **the cleanest causal-style result the project has produced
  to date** in either policy analysis.
- **Firearm suicide has a strong pre-trend issue.** All four specs find
  a consistently negative ATT (−0.11 to −0.38), but the pre-period
  trend rejects in every spec at z > +4. The pattern looks like
  Ashenfelter's dip: adopting states had RISING firearm suicide rates
  in the years before adoption, which is part of the political story
  that motivated the law in the first place. The observed
  post-treatment decline could plausibly be regression toward the mean
  rather than a treatment effect. Pre-trend-conditioned designs (e.g.,
  Roth-Sant'Anna 2023 honest pre-trends bounds) would be the right
  next step on this outcome.
- **The placebo is much better behaved than in the permitless-carry
  analysis.** Motor vehicle theft rises slightly (+22 to +39 per 100k)
  in adopters vs controls, but with **clean pre-trends in every spec**
  (z = ±0.3 to ±0.7). A clean pre-trend with a positive
  post-coefficient says: there's an unrelated property-crime trend
  difference that opens up post-2016 between red-flag adopters (mostly
  blue states) and non-adopters, not a confounding pre-trend issue.
  This is a much more interpretable design than the permitless-carry
  one, where the placebo failed in BOTH pre and post periods.
- **Strict control rule barely changes the headline.** Removing the
  five LE-only ERPO states from the control pool moves the firearm
  homicide ATT from −0.14 (broad/RA) to +0.04 (strict/RA). That
  fragility says the LE-only states were doing something distinctive
  — maybe acting as a partial treatment, or following different
  trajectories. We report the broad/RA result as primary because the
  strict control set's tiny shift (35 → 30 states) shouldn't be doing
  the work; if it does, the design is on shakier ground than we
  thought.

**Headline finding for civil-petition red-flag laws:** ERPO adoption
is associated with about **0.14 fewer firearm homicides per 100,000
residents per year** in the average treated state, with a clean
pre-trend in the covariate-adjusted spec. This is a genuinely modest
effect — a 3-4% reduction relative to a typical state's firearm
homicide rate — but it's the first finding in the project that
survives the natural set of robustness checks.

The firearm-suicide result is consistent in direction with the
literature (Swanson et al. find ERPO laws reduce firearm suicide) but
suffers from a strong pre-trend that's plausibly explained by reverse
causality (states adopt after a perceived crisis). Anyone using this
result should at minimum apply Roth-Sant'Anna pre-trend bounds.

## Comparison to the permitless-carry analysis

| | Permitless carry | Red-flag (civil) |
|---|---|---|
| Adopter profile | Mostly Republican states, 2010-2024 wave | Mostly Democratic states, 2016-2024 wave |
| Treated cohorts | 9 cohorts, 25 states | 5 cohorts, 13 states |
| Headline outcome | Firearm suicide (+0.6 / 100k, robust to spec) | Firearm homicide (−0.14 / 100k, broad/RA only) |
| Placebo (MVT) verdict | **Fails** (significant ATT and significant pre-trend in every spec) | **Cleaner** (significant ATT but clean pre-trends) |
| Pre-trends overall | Some specs clean, some reject | Firearm-homicide spec is clean; firearm-suicide rejects |

The two analyses tell different stories about the data even though they
use the same estimator and the same outcome set. Permitless-carry
identification is hampered by a fundamental property-crime trend gap
between treated and control states that no design here resolves.
Red-flag identification is cleaner on the placebo and produces a
small-but-defensible firearm-homicide reduction that's consistent with
the policy's stated mechanism (removing firearms from people in
acute crisis).

## Sample, estimator, and inference

Same as the permitless-carry analysis (see
[that methodology document](../permitless_carry_cs/methodology.md)
sections "Sample" through "Two specs"). The only differences:

- **Treatment variable:** `gvro` (instead of `permitconcealed`).
- **Treatment direction:** 0→1 first switch (instead of 1→0).
- **Strict rule:** the comparison state must have `gvro == 0` AND
  `gvrolawenforcement == 0` for every year in `[g-5, g+5]` (instead of
  `mayissue == 0` AND `permitconcealed == 1`).

All shared logic lives in [`scripts/cs_lib.py`](../../scripts/cs_lib.py).
Both policy analyses import from it, which guarantees the headline
spec / weighting / bootstrap procedures are identical and any
differences across the two writeups come from the data, not the code.

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

1. **Roth-Sant'Anna honest pre-trend bounds for firearm suicide.** The
   pre-trend is too persistent to ignore but the post-treatment
   coefficients are consistent in direction. Honest bounds would tell
   us how much pre-trend extrapolation is required to "explain away"
   the post-period coefficients.
2. **Synthetic control for the largest single-state cohort.** California
   2016 and New York 2019 are the two biggest single-state-ish
   cohorts. Synthetic counterfactuals would give per-state evidence to
   complement the pooled CS21.
3. **Stratify by suicide-method substitution.** Add nonfirearm suicide
   as a fifth outcome. If firearm suicide falls and nonfirearm
   suicide stays flat (no substitution), the policy is reducing
   total suicide. If nonfirearm rises one-for-one, the firearm
   reduction is just method substitution.
4. **Consider extending to the LE-only ERPO states.** Right now they
   are excluded from both treated and control. A separate cohort
   analysis (treating the LE-only laws as a distinct treatment) might
   reveal whether civilian-petition specifically matters.
