# Appendix section draft — state assault weapons bans (AWBs)

This file mirrors the writing style of `data_appendix.md` Sections
1.3 / 1.4 and is intended to be spliced into a future revision of
the data appendix by the orchestrator.

---

### State assault weapons bans (AWBs) — treatment cohort and identification

**What this is.** The Tufts indicator `assault` flags states whose
laws ban the civilian sale of certain semi-automatic rifles, with
the requirement that the ban must cover **long guns** (not only
pistols). Each state-year that has such a ban on the books gets
`assault == 1`. Hawaii's pistols-only ban therefore stays at
`assault == 0` throughout the panel — this is the Tufts coding
convention, not an oversight. The federal 1994–2004 ban is
intentionally not credited to any state during its operational
window; only state-level bans count.

**Source.** [Tufts CTSI State Firearm Laws Database](https://www.tuftsctsi.org/state-firearm-laws/),
the same source as Section 1.1. The codebook entry for `assault`
is in row 50 of `data/tufts_state_firearm_laws_codebook.xlsx`,
under category 8 (Assault weapons and large-capacity magazines),
sub-category "Assault weapons ban". Cross-checked against the
RAND State Firearm Laws Database; no discrepancies on adoption
year for any state in our panel.

**What we did.** Read `assault` directly from `panel_core_augmented`,
identified each state's first 0→1 transition, and filtered to
in-window adoptions (the analysis window is 1999–2023). The
treated set, as recorded in
[`outputs/assault_weapons_ban_audit/treatment_adoption_table.csv`](outputs/assault_weapons_ban_audit/treatment_adoption_table.csv):

| Year | State | In CS21? | Notes |
|---|---|---|---|
| 1989/90 | CA, NJ | no | post-Stockton wave; predates 1999 window |
| 1993 | CT | no | post-Stockton; predates window |
| 1998/99 | MA | no | predates window |
| 2000 | NY | dropped | adoption year minus 5 = 1995 < 1999 window start |
| 2013 | MD | yes | post-Newtown wave (Firearm Safety Act) |
| 2022 | DE | yes | Lethal Weapons Act |
| 2023 | IL, WA | yes | post-Highland Park wave |

After the 5-year pre-period filter, **3 cohorts and 4 treated
states** enter the Callaway-Sant'Anna and stacked-DiD specs.
That's the smallest treated set of any policy in the project
(red-flag: 13, UBC: 11, permitless carry: 25). With three of
the four treated states adopting in 2022–2023, the post-period
inside the 1999–2023 panel is mechanically dominated by 2022–
2023 calendar-year shocks.

**Caveats.**
- *Tightening events are invisible.* CA 1999 (post-Stockton),
  CT 2013 (post-Newtown), and NY 2013 (NY SAFE Act) all
  tightened pre-existing bans. Tufts' binary `assault` flag
  cannot record tightening, only the first 0→1. A
  continuous-treatment design would extract more identification
  from these events.
- *DC excluded* from the panel as elsewhere in this project
  (DC has its own AWB but the rest of the project drops DC).
- *Federal ban (1994–2004)* is correctly excluded: states only
  receive `assault == 1` if they had their own state ban during
  that window, so the federal preemption period does not
  contaminate the cohort definitions.

---

### Estimator and identification — assault-weapons-ban analysis

The mechanical pipeline (estimator, panel, six outcomes, four-spec
robustness grid `{OR, RA} × {broad, strict}`) is identical to the
red-flag analysis described in
[`outputs/red_flag_cs/methodology.md`](outputs/red_flag_cs/methodology.md).
Three things specifically change for AWBs:

- **Treatment variable** is `assault` instead of `gvro` /
  `permitconcealed` / `universal`.
- **Treatment direction** is `0→1` (adoption of a ban).
- **Strict control rule** is `assault == 0` for every year of
  `[g − 5, g + 5]`. Because already-banned states (CA, CT, MA,
  NJ) fail this filter at every cohort year, the strict pool
  (41 states per cohort) is only 4 smaller than the broad pool
  (45 states).

**Headline outcome.** AWB literature (e.g., Koper & Roth 2001
on the federal ban, Gius 2014 on state-level bans) focuses on
*firearm homicide* rather than firearm suicide as the primary
outcome. Tufts' own codebook concedes the literature does **not**
expect AWBs to produce a measurable decline in firearm homicide
(assault weapons are a small share of all firearm homicides),
but the literature frames the question that way and so do we.
For comparability with the rest of the project we report the same
six outcomes used elsewhere; the headline column for the AWB
writeup is `firearm_homicide_rate`.

**Identification verdict.** The CS21 specs return statistically
significant ATTs in every cell, but the design **does not credibly
identify a causal effect of AWBs**:

- The placebo (motor vehicle theft) fails in all four specs with
  pre-trend z < −3 and large negative post coefficients,
  suggesting AWB-adopter states (mostly densely populated,
  Democratic-leaning) had property-crime trends diverging from
  the never-treated rural pool well before the AWB.
- Pre-trend tests reject in 3 of 4 firearm-homicide specs and
  in all 4 firearm-suicide specs.
- The headline firearm-homicide ATT is *positive* in all four
  specs (+0.33 to +0.97 per 100,000), which is biologically
  implausible as a treatment effect of removing certain rifles
  from the legal market. The most parsimonious reading is that
  the design is identifying the post-pandemic firearm-homicide
  spike — which hit urban states harder — rather than the
  policy effect.

The Roth-Sant'Anna sensitivity bounds in
[`outputs/roth_sa_bounds/cs21_assault_weapons_ban_*_firearm_suicide_rate_bounds.csv`](outputs/roth_sa_bounds/)
confirm that even modest pre-trend extrapolation (M = 1) flips
the firearm-suicide ATT to a confidence interval that includes
zero in 3 of 4 CS21 specs and 3 of 3 stacked-DiD specs.

**Bottom line.** Mechanically the pipeline runs and produces
numbers, and the numbers are stored in the standard locations
(`outputs/assault_weapons_ban_cs/`,
`outputs/assault_weapons_ban_stackdd/`,
`outputs/roth_sa_bounds/cs21_assault_weapons_ban_*` and
`outputs/roth_sa_bounds/stackdd_assault_weapons_ban_*`). But
the AWB analysis is the most identification-starved of the four
state-level policy analyses in the project — a 4-treated-state,
3-cohort design with most of the post-period inside the
post-2020 firearm-homicide spike — and the placebo failure says
the headline ATTs should not be read as causal until a
substantially longer post-period is available (likely
2026 or later).
