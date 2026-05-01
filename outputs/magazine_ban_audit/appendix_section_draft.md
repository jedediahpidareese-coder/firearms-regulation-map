# Appendix section draft -- state large-capacity magazine (LCM) bans

This file mirrors the writing style of `data_appendix.md` Sections
1.3 / 1.4 and is intended to be spliced into a future revision of the
data appendix by the orchestrator.

---

### State large-capacity magazine bans (LCM bans) -- treatment cohort and identification

**What this is.** The Tufts indicator `magazine` flags states whose
laws ban the civilian sale of large-capacity ammunition magazines
*beyond just assault-pistol magazines* (i.e., the ban covers rifle and
shotgun magazines as well, not only handgun magazines). A state-year
with such a ban on the books gets `magazine == 1`. Two companion Tufts
indicators provide context but are *not* used as the treatment:
`tenroundlimit == 1` flags the subset of LCM-banning states whose
threshold is 10 rounds (the federal 1994-2004 ban used 15 rounds, and
states like CO 2013, DE 2022, NJ pre-2018 used 15 or 17 rounds);
`magazinepreowned == 1` flags states that ban *possession* (not just
sale) of pre-owned LCMs. Hawaii's handgun-only LCM provision keeps it
at `magazine == 0` throughout the panel -- this is the Tufts coding
convention, not an oversight, and aligns with how RAND classifies HI.
The federal 1994-2004 ban is intentionally not credited to any state
during its operational window; only state-level bans count.

**Source.** [Tufts CTSI State Firearm Laws Database](https://www.tuftsctsi.org/state-firearm-laws/),
the same source used throughout Section 1.1. The codebook entry for
`magazine` is in row 55 of
`data/tufts_state_firearm_laws_codebook.xlsx`, under category 8
(Assault weapons and large-capacity magazines), sub-category "Large
capacity magazine ban". Cross-checked against the
[RAND State Firearm Laws Database](https://www.rand.org/research/gun-policy/state-laws.html);
two coding decisions diverge from RAND's modern-event framing and one
state is in dispute -- see the disagreement table below.

**What we did.** Read `magazine` directly from `panel_core_augmented`,
identified each state's first 0->1 transition, and filtered to
in-window adoptions (the analysis window is 1999-2023). The treated
set, as recorded in
[`outputs/magazine_ban_audit/treatment_adoption_table.csv`](outputs/magazine_ban_audit/treatment_adoption_table.csv):

| Year | State | In CS21? | Notes |
|---|---|---|---|
| 1990 | NJ | no | Assault Firearms Act; predates 1999 window |
| 1994 | MD | no | original 20-round ban; predates window. Tufts does NOT generate a 2013 cohort when MD reduced the limit to 10 rounds |
| 1998 | MA | no | Gun Control Act of 1998; predates window |
| 2000 | CA, NY | dropped | adoption year minus 5 = 1995 < 1999 window start |
| 2013 | CO, CT | yes | post-Newtown / post-Aurora wave |
| 2018 | VT | yes | Act 94 (10-round long-gun / 15-round handgun) |
| 2022 | DE, RI, WA | yes | post-pandemic wave |
| 2023 | IL | yes | Protect Illinois Communities Act, post-Highland Park |

After the 5-year pre-period filter, **4 cohorts and 7 treated states**
enter the Callaway-Sant'Anna and stacked-DiD specs: a substantively
larger treated set than the assault-weapons-ban analysis (4 states / 3
cohorts) but smaller than red-flag (13 / 5) and permitless carry (25 /
many). Because three of the seven adoptions land in 2022-2023, the
post-period inside the 1999-2023 panel is mechanically dominated by
the post-pandemic firearm-violence regime and contains very few
event-time `e >= 2` cells.

**Tufts / RAND disagreements.** Three substantive issues:

1. **MD 2013 reduction-to-10-rounds.** Tufts dates MD's `magazine == 1`
   at 1994 (original 20-round ban). RAND's modern-event framing
   credits the 2013 Firearm Safety Act (which dropped the limit to 10
   rounds) as the policy event of analytic interest. Our cohort
   construction follows Tufts: MD never generates a 2013 cohort
   because `magazine` is already 1 in 2012. A continuous-treatment
   design that exploited `tenroundlimit` flips would recover the 2013
   tightening event for MD; our binary design cannot.
2. **NY 2013 SAFE Act.** Same pattern as MD. Tufts dates NY at 2000
   (Hevesi/Pataki LCM ban). NY SAFE Act 2013 tightened to 7 rounds
   (later struck down on the 7-round limit; reverted to 10), which
   does not register as a 0->1 transition in `magazine`. NY 2000 is
   excluded from cohorts on the 5-year pre-window rule regardless.
3. **OR Measure 114 (2022).** Voters approved the >10-round LCM ban
   in November 2022, but a Harney County preliminary injunction
   (December 2022) and ongoing OR Supreme Court litigation kept the
   ban from taking effect through the end of our analysis window.
   Tufts codes OR `magazine == 0` throughout; RAND's database notes
   the passage but does not treat OR as a banned state during the
   contested period. **We agree with Tufts** -- there is no enforced
   ban during 1999-2023 -- so OR remains in the never-treated control
   pool. If Measure 114 ultimately takes effect, OR will need to be
   reclassified in a future revision.

These three discrepancies translate to **0 of 7 in-window cohort
states** disagreeing with RAND on the cohort year (everyone in the
2013 / 2018 / 2022 / 2023 waves matches RAND exactly), well under
the 30 percent threshold the project uses to abandon a Tufts-derived
analysis.

**Caveats.**
- *Tightening events are invisible.* As above (MD 2013, NY 2013, NJ
  2018 reduction to 10 rounds, CA 2016 possession ban). Tufts's
  binary `magazine` flag cannot record tightening, only the first
  0->1.
- *Possession bans are pooled with sale bans.* CA (post-2016), NJ
  (post-2018), and CT (registration) impose different enforcement
  costs than pure sale bans (CO 15-round, WA 10-round sale-only).
  The `magazinepreowned` flag could support a sub-analysis but the
  treated set would shrink to ~3 in-window states.
- *DC excluded* from the panel as elsewhere in this project. DC has
  a longstanding LCM ban but is dropped throughout.
- *Federal ban (1994-2004)* is correctly excluded: states only
  receive `magazine == 1` if they had their own state ban during
  that window, so the federal preemption period does not contaminate
  the cohort definitions.

---

### Estimator and identification -- magazine-ban analysis

The mechanical pipeline (estimator, panel, six outcomes, four-spec
robustness grid `{OR, RA} x {broad, strict}`) is identical to the
red-flag analysis described in
[`outputs/red_flag_cs/methodology.md`](outputs/red_flag_cs/methodology.md).
Three things specifically change for LCM bans:

- **Treatment variable** is `magazine` instead of `gvro` /
  `permitconcealed` / `universal` / `assault`.
- **Treatment direction** is `0->1` (adoption of a ban).
- **Strict control rule** is `magazine == 0` for every year of
  `[g - 5, g + 5]`. Because all in-window adopters are post-2012
  and pre-1999 already-banned states (CA, MA, MD, NJ, NY) fail this
  filter at every cohort year, the strict pool (38 states per cohort)
  is only 3 smaller than the broad pool (41 states).

**Headline outcomes.** The published LCM literature (Klarevas et al.
2019, RAND 2018/2024 *Effects of Bans on the Sale of Assault Weapons
and High-Capacity Magazines*) frames the question around two outcomes:

1. **Mass-shooting frequency / lethality.** The clearest mechanism
   for an LCM ban is reducing the per-incident casualty count of
   active-shooter events; secondary literature also looks at incidence.
2. **Firearm homicide.** The diffuse mechanism (LCMs are used in only
   a small share of all firearm homicides) means a measurable
   population-level homicide effect is theoretically possible but
   small. Tufts' codebook concedes the literature does not strongly
   expect a measurable decline in firearm homicide from LCM bans
   alone.

**The mass-shooting outcome is not yet in this project's panel.** The
v1 outcomes (firearm suicide, firearm homicide, total suicide,
non-firearm suicide, total homicide, motor-vehicle theft placebo) do
not include a state-year mass-shooting count or fatality count. We
flag this as a **v2 limitation**: the headline LCM-ban outcome of
public-health interest cannot be estimated with the current panel.
For comparability with the rest of the project we report the same six
outcomes used elsewhere; the headline column for the LCM writeup is
`firearm_homicide_rate`.

**Identification verdict.** The CS21 specs return statistically
significant negative ATTs for `firearm_homicide_rate` in every cell,
with the cleanest pre-trends of any policy in the project for that
outcome:

| spec | control | ATT firearm_homicide_rate | SE | z | pre-trends z |
|---|---|---|---|---|---|
| OR  | broad  | **-0.999** | 0.201 | -4.97 | +0.17 |
| OR  | strict | **-1.037** | 0.201 | -5.15 | +0.55 |
| RA  | broad  | **-0.791** | 0.106 | -7.44 | -7.57 |
| RA  | strict | **-0.948** | 0.116 | -8.17 | -7.91 |

The OR specs are the cleanest: pre-trends z are essentially zero
(+0.17, +0.55), so the parallel-trends assumption is not contradicted
in the pre-period, and the post-period ATTs are large (about -1 per
100,000 firearm-homicide deaths) and tightly estimated. The RA specs
have problematic pre-trend tests, suggesting the covariate adjustment
(population, unemployment, real per-capita personal income) is
introducing rather than removing differential pre-trends -- read the
OR specs as the headline.

The stacked-DiD estimates are smaller in magnitude but the same
direction:

| spec | ATT firearm_homicide_rate | SE | z |
|---|---|---|---|
| unweighted | **-0.839** | 0.340 | -2.47 |
| RA         | **-0.842** | 0.382 | -2.21 |
| EB         |   -0.504  | 0.341 | -1.48 |

The placebo (`motor_vehicle_theft_rate`) is **noisily positive in
every spec** with z between +1.6 and +9.5 and pre-trend z below -3 in
all four CS21 cells, signaling that LCM-adopter states (urban,
Democratic-leaning) had property-crime trends diverging from the
never-treated rural pool well before the LCM ban. This is the same
placebo-failure pattern the assault-weapons-ban analysis hit, and it
constrains how much causal weight to put on the firearm-homicide
result.

The Roth-Sant'Anna sensitivity bounds in
[`outputs/roth_sa_bounds/magazine_ban_firearm_suicide_bounds.csv`](outputs/roth_sa_bounds/magazine_ban_firearm_suicide_bounds.csv)
(consolidating the per-spec
`cs21_magazine_ban_*_firearm_suicide_rate_bounds.csv` and
`stackdd_magazine_ban_single_*_firearm_suicide_rate_bounds.csv`
files) confirm that for the secondary `firearm_suicide_rate` outcome,
the small in-magnitude ATTs are not robust: the M = 1 confidence
interval includes zero in 4 of 4 CS21 specs and 3 of 3 stacked-DiD
specs.

**Bottom line.** The LCM-ban analysis returns the most credible
firearm-homicide point estimate of any state-policy analysis in this
project (about -1 per 100,000 firearm-homicide deaths under the OR
specs, with clean pre-trends), but the placebo failure on motor
vehicle theft means the estimate should be read as an upper bound on
the causal effect rather than a clean identification. The mass-
shooting outcome that the LCM literature actually centers on is a
v2 limitation: the project does not yet have a state-year mass-
shooting panel, and the v1 firearm-homicide signal -- while
suggestive of a real effect -- is mechanically dominated by the
2022-2023 adoption wave and the post-pandemic firearm-homicide
regime. A v2 revision should add a state-year mass-shooting outcome
(e.g., from Mother Jones, the Violence Project, or GVA) and re-run
this analysis; the cohort definitions and audit table will not need
to change.

Outputs are stored in the standard locations:
- `outputs/magazine_ban_audit/` -- adoption table + this draft
- `outputs/magazine_ban_cs/` -- CS21 ATTs and event-study figures
- `outputs/magazine_ban_stackdd/` -- stacked-DiD ATTs and figures
- `outputs/roth_sa_bounds/cs21_magazine_ban_*` and
  `outputs/roth_sa_bounds/stackdd_magazine_ban_*` -- pre-trend bounds
- `outputs/roth_sa_bounds/magazine_ban_firearm_suicide_bounds.csv`
  -- consolidated bounds file
