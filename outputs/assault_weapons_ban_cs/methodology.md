# State assault weapons bans (AWBs) — Callaway-Sant'Anna ATT(g, t)

**Date:** 2026-04-30
**Script:** [`scripts/run_cs_assault_weapons_ban.py`](../../scripts/run_cs_assault_weapons_ban.py)
**Output folder:** `outputs/assault_weapons_ban_cs/`

Fourth policy in the research portion of the project, after
[permitless carry](../permitless_carry_cs/methodology.md),
[red-flag laws](../red_flag_cs/methodology.md), and
[universal background checks](../ubc_cs/methodology.md). Same
estimator, same panel, same six outcomes, same four-spec robustness
grid. The only differences are the treatment definition and the
strict-rule control filter.

## What "assault weapons ban" means here

Tufts publishes the binary `assault` flag, which the codebook defines
as "Ban on sale of assault weapons beyond just assault pistols" —
i.e., the ban must cover **long guns**, not just pistols. (Hawaii's
assault-pistol-only ban is therefore correctly coded `assault == 0`
throughout the panel.) During the 1994–2004 federal ban window Tufts
only awards the point if the state had its own state-level ban on the
books, since federal preemption is the same everywhere.

We use the modern, post-federal-sunset definition. Treatment is the
first 0→1 switch in `assault`. Direction is `0to1`. The strict
control rule requires `assault == 0` for every year in the cohort's
[g−5, g+5] window.

## Cohorts

Five state-level AWBs flip 0→1 inside the analysis window
(1999–2023):

| Year | State | Notes |
|---|---|---|
| 2000 | NY | Pre-SAFE-Act AWB; **excluded** because 2000 − 5 = 1995 < 1999 |
| 2013 | MD | Firearm Safety Act, post-Newtown |
| 2022 | DE | Lethal Weapons Act |
| 2023 | IL | Protect Illinois Communities Act, post-Highland Park |
| 2023 | WA | HB 1240 |

After the pre-period filter, **3 distinct cohorts (2013, 2022, 2023)
covering 4 treated states (MD, DE, IL, WA)** enter the analysis.
NY 2000 is in `dropped_log.csv`.

States already banned at the start of the window (1989–1998 AWBs:
CA, CT, MA, NJ) never appear in the cohort dictionary because their
0→1 transition predates the analysis window. They are also excluded
from the never-treated control pool by `derive_cohorts` since their
`assault` value never starts at 0 inside the window. The remaining
**45 never-treated states** form the broad control pool. The strict
rule (assault == 0 throughout [g−5, g+5]) yields **41 strict-pool
controls** for each cohort (the four 1989–1998 already-banned states
fail the [g−5, g+5] check at every g).

## Cross-check vs RAND State Firearm Laws Database

Tufts and RAND agree on every state and every adoption year:

- **CA**: Roberti-Roos AWB enacted 1989; Tufts records assault==1
  from 1990 onward. RAND agrees. (CA tightened the ban in 1999
  post-Stockton; that's not a 0→1 transition so is invisible here.)
- **CT**: 1993 post-Stockton ban; Tufts assault==1 from 1993. CT
  tightened post-Newtown 2013 (added to banned-list); also
  invisible as a 0→1 flip.
- **MA**: 1998 ban; Tufts assault==1 from 1999.
- **NJ**: 1990 early post-Stockton ban.
- **NY**: 2000 ban; tightened post-Newtown 2013 (NY SAFE Act). The
  2000 0→1 flip is what Tufts records.
- **MD, DE, IL, WA**: post-Newtown / post-Highland Park wave;
  matching adoption years.
- **HI**: assault-PISTOL-only ban (does not cover long guns), so
  Tufts codes assault==0; RAND likewise excludes from a long-gun
  AWB list. No discrepancy.
- **DC** is excluded from the panel as elsewhere in this project.

No RAND/Tufts disagreements documented for this policy. All
adoption years pass cross-check.

## Headline numbers (four specifications)

Same 4-spec grid as the red-flag analysis: `{OR, RA} × {broad,
strict}`. The headline outcome for AWBs is **firearm homicide rate**
— this is the outcome the published AWB literature focuses on
(e.g., Koper & Roth 2001 federal-ban evaluation, Gius 2014
state-level study). Tufts' own codebook concedes the literature
does NOT expect AWBs to produce a measurable decline in firearm
*homicide* (assault weapons are a small share of homicides), but
the literature frames the question that way and so do we.

Per 100,000 population, post-treatment ATT and pre-trend z. Bold
pre-z means the pre-trend does not reject (z within ±1.96).

| Spec | Control | Firearm homicide | Firearm suicide | Total homicide | MV theft (placebo) |
|---|---|---|---|---|---|
| OR | broad  | +0.42 (pre z = **−1.55**) | −0.95 (pre z = −4.71) | +0.34 (pre z = −3.07) | −22 (pre z = −4.79) |
| OR | strict | +0.33 (pre z = **−1.25**) | −1.02 (pre z = −3.85) | +0.27 (pre z = −2.85) | −25 (pre z = −4.81) |
| RA | broad  | +0.97 (pre z = −4.42) | −0.51 (pre z = −8.16) | +0.68 (pre z = −6.03) | −17 (pre z = −6.39) |
| RA | strict | +0.72 (pre z = −3.56) | −0.74 (pre z = −5.46) | +0.38 (pre z = −2.91) | −26 (pre z = −3.08) |

### What the four-spec grid tells us

- **The headline firearm-homicide ATT is positive, not negative.**
  In all four specs, treated states' firearm-homicide rates rise
  relative to controls in the post-period. This is the *opposite*
  direction the published literature implies. The most defensible
  reading is **not** that AWBs cause more firearm homicide; instead
  it reflects **timing and composition**: 4 of 5 treated states
  adopted in 2022–2023, putting their post-period almost entirely
  inside the post-pandemic firearm-homicide spike (which was larger
  in already-urban Democratic-leaning adopter states than in the
  rural never-treated pool). The OR specs (which do not adjust for
  observed covariates) get pre-trend z within the conventional
  bound (−1.55 / −1.25), but the post-period is dominated by a
  national shock the design cannot absorb.
- **Firearm-suicide and total-suicide are negative and large**
  (−0.51 to −1.02 firearm; −0.55 to −1.18 total), but every spec
  has a strongly rejecting pre-trend (z < −2.5). This looks like a
  classic timing artifact: states adopting in 2022–2023 had been
  on declining-relative trends in suicide for years before, and
  the post-period extrapolates that decline.
- **Motor vehicle theft (placebo) fails badly in all four specs**
  with both pre-trend z < −3 and large negative post coefficients.
  This is the same problem in different clothing: the AWB-adopter
  states (mostly densely populated, blue-state) had property-crime
  trends diverging from the never-treated rural pool well before
  the AWB. The placebo failure says we should **not** read the
  headline ATTs as causal.
- **Strict control rule barely changes the headline.** Removing
  the four 1989–1998 already-banned states from the [g−5, g+5]
  filter (broad pool 45 → strict pool 41) shifts the firearm
  homicide ATT by ~0.1–0.25 across specs. The fragility direction
  is consistent with the broad-pool result; both pools include
  essentially the same rural-Republican never-treated states.

**Headline finding for state assault weapons bans:** the design
**cannot identify a causal effect** with this cohort structure.
With 4 treated states and 3 cohorts (one of which contributes 5
post-period years, three of which contribute 0–1 post-period
years inside the panel ending in 2023), the post-period is
mechanically dominated by 2022–2023 calendar-year shocks (the
post-pandemic firearm-homicide and motor-vehicle-theft surges
that hit urban states harder). The estimator returns *some* ATT
in every cell, but the placebo failure and the rejecting pre-trends
in 3 of 4 specs say the ATTs are picking up **trend differences,
not policy effects**. We report them for transparency and for the
Roth-Sant'Anna sensitivity in the bounds folder.

The only spec with a passable pre-trend (OR/strict, OR/broad on
firearm-homicide) returns a *positive* ATT, which is implausible
as a treatment effect of AWBs. We interpret that as evidence the
design is identifying a calendar-year confounder, not the policy.

## Comparison to the other three policies

| | Permitless carry | Red-flag (civil) | UBC | Assault weapons ban |
|---|---|---|---|---|
| Treated cohorts | 9 cohorts, 25 states | 5 cohorts, 13 states | 8 cohorts, 11 states | **3 cohorts, 4 states** |
| Adopter profile | Mostly Republican states, 2010–2024 wave | Mostly Democratic states, 2016–2024 wave | Mixed, 1991–2023 wave | All Democratic, 4-of-5 in 2022–2023 |
| Headline outcome | Firearm suicide (+0.6 / 100k) | Firearm homicide (−0.14 / 100k) | Total suicide (−1.0 / 100k) | Firearm homicide (NOT IDENTIFIED) |
| Placebo (MVT) | Fails | Cleaner (sig ATT, clean pre-trend) | Mostly clean | **Fails badly (pre-trend rejects)** |
| Pre-trends overall | Some specs clean | Firearm-homicide spec clean | UBC specs clean | **Almost all specs reject** |

The AWB analysis is the most poorly identified of the four policy
analyses in the project. The fundamental problem is sample size
plus calendar timing: 4 treated states, 3 of which adopted in the
12 months before the panel ends, leave the design with essentially
no post-period to compare to.

## Sample, estimator, and inference

Same as the red-flag and UBC analyses (see
[red-flag methodology](../red_flag_cs/methodology.md) sections
"Sample" through "Two specs"). The only differences:

- **Treatment variable:** `assault` (instead of `gvro` or `universal`).
- **Treatment direction:** 0→1 first switch.
- **Strict rule:** the comparison state must have `assault == 0`
  for every year in `[g − 5, g + 5]`.

All shared logic lives in [`scripts/cs_lib.py`](../../scripts/cs_lib.py).

## Outputs

| File | What |
|---|---|
| `att_gt.csv` | One row per (outcome, spec, control_rule, g, t). |
| `event_study.csv` | One row per (outcome, spec, control_rule, event_time). |
| `overall_att.csv` | One row per (outcome, spec, control_rule). |
| `cohort_n.csv` | Cohort sizes. |
| `dropped_log.csv` | States dropped from analysis with reasons (NY 2000 dropped: pre-window). |
| `figures/event_study_{control_rule}_{spec}_4panel.svg` | 4 figures. |

## Recommended next steps

1. **Wait for more post-period.** With three of the four treated
   states adopting in 2022–2023, the design is identification-
   starved. Re-running this analysis once 2025–2027 mortality data
   land would more than triple the post-period observations.
2. **Synthetic control for MD 2013.** Maryland 2013 is the only
   AWB cohort with a meaningful post-period (2013–2023). A
   per-state synthetic counterfactual would give cleaner evidence
   than the pooled CS21 here.
3. **Consider AWB-tightening events as treatments.** CA 1999, CT
   2013, NY 2013 all tightened pre-existing bans. These are not
   0→1 transitions in `assault` but they are policy changes; a
   continuous-treatment design might extract more identification.
4. **Stratify by mass-shooting prevalence.** AWB literature is
   typically interested in mass-shooting outcomes specifically,
   not all firearm homicides. Adding a mass-shooting outcome
   would test the policy on its own claimed mechanism.
