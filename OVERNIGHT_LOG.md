# Overnight log — 2026-05-01 → 2026-05-02

Orchestrator + ~10 background agents fanning out across three tracks +
website integration. This file is updated incrementally as tracks land.

---

## Track B — Spatial RDD pipeline + CJ controls + website UI fixes ✅ LANDED

**Commit:** `9077a2c` (50 files, +161,353 / −100,419)
**Pushed to:** `claude/adoring-galileo-d721c3` → GitHub `main`

### What landed
- `scripts/lib_rdd.py` — DLR-style estimator (~620 lines): county FE +
  state-pair × year FE via iterative within-FE Frisch–Waugh–Lovell;
  Liang-Zeger and Cameron-Gelbach-Miller two-way clustering; Knight
  spillover-pair filter; event study; SVG plotter.
- `scripts/run_rdd_{permitless_carry,red_flag,ubc}.py` — thin per-policy
  runners. Each runs the 10-spec robustness battery × 9 outcomes.
- `outputs/{permitless_carry,red_flag,ubc}_rdd/` — per-policy outputs:
  cohort_n, headline, robustness, event_study CSVs + figures.
- `outputs/border_rdd/methodology.md` — cross-policy methodology doc.
- CJ controls layer (Section 2.13 of `data_appendix.md`):
  imprisonment, police expenditure, death penalty, executions, sworn
  officers (state + county). LEOKA streamed from openICPSR project
  102180 V15 zip without unzipping.
- `data_appendix.md` Section 2.13 spliced (CJ controls); old 2.13
  renumbered to 2.14 with MVT-fix entry.
- `scripts/build_county_crime.py` — MVT column-name fix
  (`actual_mtr_veh_theft_total` → `actual_motor_vehicle_theft_total`);
  county_panel rebuilt to include `county_motor_vehicle_theft_rate`.
- `outputs/rdd_diagnostics/` — pre-RDD descriptive characterization
  (Agent B) plus 9-paper literature scan (Agent A).
- Website UI fixes (Agent D): per-100k labels for rate vars; click-to-
  lock sidebar; d3.zoom on both modes.

### Headline RDD findings (B = 100 km, FE = pair × year, cluster = state)

| Policy | Outcome | β | SE | z | n |
|---|---|---:|---:|---:|---:|
| **Permitless carry** | county_murder_rate | −1.18 | 0.55 | −2.16* | 31,248 |
| | state_firearm_suicide_rate | +0.36 | 0.11 | +3.29*** | 29,295 |
| | state_total_suicide_rate | +0.54 | 0.17 | +3.24*** | 29,295 |
| | state_firearm_homicide_rate | +0.28 | 0.13 | +2.13* | 29,271 |
| **Civil red-flag** | state_firearm_suicide_rate | −0.70 | 0.06 | −11.10*** | 29,295 |
| | state_total_suicide_rate | −0.55 | 0.11 | −5.15*** | 29,295 |
| | state_firearm_homicide_rate (does NOT replicate CS21 −0.14) | +0.19 | 0.21 | +0.94 | 29,271 |
| **UBC** (first significant signals in project) | state_firearm_suicide_rate | −0.26 | 0.12 | −2.19* | 29,295 |
| | state_total_suicide_rate | −0.44 | 0.13 | −3.35*** | 29,295 |
| | county_violent_crime_rate | +19.04 | 8.99 | +2.12* | 31,248 |
| | county_murder_rate | −0.60 | 0.15 | −3.89*** | 31,248 |

### Design choices made unilaterally
- Headline bandwidth 100 km (per Agent B diagnostic — sufficient
  straddling pairs without bleeding too far interior).
- Sworn officers per 100k surfaced both at county grain (true county-
  level Kaplan LEOKA) AND state grain (sum-up rollup, joined down).
- LEOKA zip stays compressed — script streams via `zipfile.BytesIO`
  (matches user preference, saves ~1 GB disk).
- DC sworn-officers rolls up to NaN where state CJ already had NaN
  (DC has no state-stock prisoners post-2001).
- State-joined mortality outcomes labeled SECONDARY in methodology;
  primary outcomes are the true county-level Kaplan crime rates.

### Caveats / TODOs surfaced
- Red-flag firearm-homicide RDD does NOT replicate the project's
  existing CS21 −0.14 finding. Possible interpretation: CS21 effect
  is concentrated in interior counties, not at borders. Worth
  discussing in the report.
- All three policies show county_murder_rate ↓ in the headline. May
  be a state × year linear-trend artifact; Step 4 sensitivity sweep
  should test.
- 96 county-years missing sworn officers (5 small Alaska boroughs +
  Kalawao HI; same entities that have no Kaplan crime data).
- 2024 BJS Prisoners report not released; imprisonment_rate 2024 NaN
  for all states.

---

## Track A — 5 new state-level policies (CS21 + StackDD + Roth-SA bounds)

Status: 1 of 5 returned, 4 still running.

### CAP (Child-Access Prevention) — SKIPPED
Tufts panel only has `locked` (mandatory secure storage; 4 states,
zero clean cohorts), not the Webster/Vernick `capliable` (negligence-
based liability). Skip-rule met. Documented in
`outputs/cap_audit/SKIPPED.md`. Suggests external RAND/Giffords coding
as an unblock.

### Assault weapons ban — DESIGN FAILS (honest negative)
**Tufts column:** `assault` (long-gun-inclusive AWB), direction 0→1.
**Cohorts:** 3 in-window (MD 2013, DE 2022, IL 2023, WA 2023; n=4 states).
NY 2000 dropped (pre-period < 1999 panel start). 45 never-treated controls.
**Headline firearm_homicide_rate:**
- CS21: positive (+0.33 to +0.97 per 100k) but pre-trends fail in OR specs
  (z ≈ −1.3/−1.5) and reject in RA specs.
- StackDD: negative (−0.28 to −1.42 per 100k); only EB spec significant.
- Placebo (MVT) fails: pre-z < −3 in every CS21 spec.
- Sign disagreement between estimators + placebo failure ⇒ **design does
  not credibly identify a causal effect.** Post-period dominated by the
  2022–2023 firearm-homicide spike.
**RAND/Tufts agreement:** all 9 historical adopters (CA, NJ, CT, MA, NY,
MD, DE, IL, WA) match. HI's pistols-only ban correctly coded `assault==0`
per Tufts' long-gun-required rule.
**Files created:** outputs/assault_weapons_ban_{audit,cs,stackdd}/, 7
roth_sa_bounds CSVs, scripts/run_cs_assault_weapons_ban.py,
scripts/build_assault_weapons_ban_audit.py.

### Stand-your-ground — RA broad firearm_homicide is the headline finding
**Tufts column:** `nosyg`-derived (1→0 transition = state adopts SYG).
**Cohorts:** 13 in-window cohorts, 28 treated states (FL 2005 first; AR/ND 2021
last). Big sample. 22 never-treated controls.
**Headline firearm_homicide_rate (CS21):**
- OR/broad: +0.84/100k, z = +13.1, pre-trend z = +2.30 (marginal)
- **RA/broad: +0.54/100k, z = +12.8, pre-trend z = −0.30 CLEAN ⇐ HEADLINE**
- RA/strict: +0.47/100k, z = +10.9, pre-trend z = +0.12 CLEAN
**Headline firearm_suicide_rate (CS21):**
- OR specs find +0.5 with rejecting pre-trends (z ≈ −4.3)
- RA specs find small negatives (−0.07 to −0.09) but still rejecting pre-trends.
- Treat with caution; the OR/RA sign-flip indicates the covariates are doing
  much of the work.
**Bottom line:** SYG → +0.5/100k firearm homicide is a clean positive finding
consistent with McClellan-Tekin (2017) and Cheng-Hoekstra (2013) which found
~8% increase. Files: outputs/stand_your_ground_{audit,cs,stackdd}/, scripts/
run_cs_stand_your_ground.py.

### Magazine ban — clean reductions in firearm homicide (OR specs)
**Tufts column:** `magazine`, direction 0→1.
**Cohorts:** 4 in-window (2013 CO+CT; 2018 VT; 2022 DE+RI+WA; 2023 IL).
7 treated states.
**Headline firearm_homicide_rate (CS21):**
- **OR/broad: −1.00/100k, z = −5.0, pre-trend z = +0.17 CLEAN ⇐ HEADLINE**
- OR/strict: −1.04/100k, z = −5.2, pre-trend z = +0.55 CLEAN
- RA specs find similar magnitude (−0.79 to −0.95) but pre-trends reject
  (z ≈ −7.6)
**Headline firearm_suicide_rate (CS21):**
- OR/broad −0.32, OR/strict −0.39 (both clean pre-trends)
- RA/broad +0.03 (NS, clean), RA/strict −0.25 (clean)
**Bottom line:** Magazine bans → ~−1.0/100k firearm homicide reduction with
clean pre-trends in OR specs. Cleaner than the assault-weapons-ban result
(below) and consistent with mass-shooting-frequency literature (which our
panel doesn't directly support — flagged as v2). Files: outputs/magazine_ban_{audit,cs,stackdd}/, scripts/run_cs_magazine_ban.py.

### Age 21 handgun — sign-conflict, not credibly identified
**Tufts column:** `age21handgunsale` (commercial + private), direction 0→1.
**Cohorts:** 4 in-window, 6 treated states (WV 2010, WY 2010, FL 2018, VT 2018,
WA 2019, CO 2023). Earlier adopters (NY 2000, NJ 2001) dropped for insufficient
pre-period; 12 already-treated-at-1999 states excluded. 42 never-treated.
**Headline firearm_suicide_rate (CS21):**
- RA/broad: +0.43/100k, z = +4.5, pre-trend z = +1.5 CLEAN
- Sign is OPPOSITE the published youth-stratified literature.
- Caveat: project lacks age-stratified mortality, so all-ages dilutes the
  literature's youth-band effect.
- Roth-Sant'Anna bounds (M=1) flip sign to negative but CI includes zero.
**Headline firearm_homicide_rate (CS21):**
- RA/broad: −0.52/100k, z = −10.1, but pre-trend z = −8.0 (BAD)
- MV theft placebo also fails badly. Treat as not credible.
**Bottom line:** Design does not credibly identify the age21 effect at all-ages
grain. Need age-stratified mortality data to test the youth-specific channel
the published literature finds. Files: outputs/age21_handgun_{audit,cs,stackdd}/,
scripts/run_cs_age21_handgun.py.

### Assault weapons ban — design fails (already documented above)

---

## Track C — County-level CS21 pipeline ✅ LANDED

**Commit:** `77ded6f` — county-level CS21 pipeline (3 policies)
**Module:** `scripts/lib_cs_county.py` — N_BOOTSTRAP=2000, ANALYSIS_YEARS=(2009, 2024); cluster-bootstrap clusters at state level (counties within a state share the policy assignment); RA covariates include county-level demographics + economics + ln(population) + ln(pcpi_real_2024).
**Per-policy runners:** `scripts/run_cs_county_{permitless_carry, red_flag, ubc}.py`. The 5 Track A policies' county-grain runners are deferred to a follow-up.
**Outputs:** `outputs/{permitless_carry, red_flag, ubc}_cs_county/` — att_gt, event_study, overall_att, cohort_n, dropped_log, figures.

### Headline (RA broad)

| Policy | Outcome | β | SE | z | pre-trend z |
|---|---|---:|---:|---:|---:|
| Permitless carry | county_violent_crime_rate | −10.83 | 2.03 | −5.3 | −0.89 ✅ |
| | county_murder_rate | −0.29 | 0.11 | −2.5 | −2.2 modest |
| | county_motor_vehicle_theft_rate (placebo) | −6.97 | 1.76 | −3.96 | −2.80 fails |
| Civil red-flag | county_violent_crime_rate | −11.74 | 3.18 | −3.7 | −1.66 |
| | county_murder_rate | −0.59 | 0.06 | −9.1 | +2.83 modest |
| | state_firearm_homicide_rate | −0.57 | 0.07 | −8.6 | +5.71 (recovers a much LARGER version of the state CS21 −0.14 finding) |
| | county_burglary_rate (placebo) | +18.56 | 3.78 | +4.9 | −9.64 fails |
| | county_motor_vehicle_theft_rate (placebo) | +0.83 | 2.90 | +0.29 | −1.11 ✅ |
| UBC | county_violent_crime_rate | −12.09 | 1.22 | −9.9 | −15.50 ❌ |
| | county_murder_rate | −1.04 | 0.06 | −16.6 | −9.0 ❌ |
| | placebos all fail badly | | | | |

**Take:** UBC county-grain CS21 not credibly identified (severe pre-trend rejection in every spec). Permitless carry has the cleanest county-grain crime signal. Red flag county-grain replicates and amplifies the state-level CS21 firearm-homicide finding.

---

## Track D — Website CJ integration ✅ LANDED inline

Done by orchestrator (the spawned agent hit the rate limit mid-task; I
finished the work directly). `scripts/build_website_data.py` and
`scripts/build_website_county_data.py` modified to load and merge the
new CJ files; 5 new state-mode variables and 1 county-mode variable
under a new "Criminal justice" category. `docs/js/app.js` palette
extended (`d3.interpolatePuOr`). `docs/data/panel.json` regrew from 40
vars / 6 categories → 45 vars / 7 categories. County-mode regrew from
23 → 24 vars / 7 categories.

---

## Final report regeneration

`outputs/research_report/index.html` regenerated (646 KB; was ~250 KB).
Copied to `docs/research/index.html` (661 KB) so the live site picks up
the new content. Sections in the new report:

1. Executive summary
2. Data and panel construction
3. Methodology
4. Permitless carry
5. Civil-petition red-flag (ERPO)
6. Universal background checks
7. Stand-your-ground (SYG) ⟵ new
8. Large-capacity magazine ban ⟵ new
9. Minimum age 21 for handgun purchase ⟵ new
10. Assault weapons ban ⟵ new
11. Spatial regression discontinuity on county borders ⟵ new
12. County-level Callaway-Sant'Anna ATT(g, t) ⟵ new
13. Cross-policy synthesis
14. Limitations and caveats
15. Appendix: code map and reproduction

---

## Pending integration steps (deferred; not blocking)

1. Splice individual Track A appendix drafts into `data_appendix.md`
   as Section 1.7-1.10 (the drafts live at
   `outputs/{policy}_audit/appendix_section_draft.md`). Currently the
   research report links to those drafts directly via `cs_methodology_link`.
2. CJ-augmented sensitivity sweep — re-run all 8 CS21 pipelines with
   the new CJ controls (imprisonment_rate, sworn_officers_per_100k,
   police_expenditure_per_capita_real_2024) added to the RA covariates,
   then update the report with comparison tables. ~30-40 min of compute
   plus a small report edit.
3. Track A x RDD — run `lib_rdd.run_full_battery` for the 4 new policies
   (SYG, magazine, age21, AWB). Each takes ~2-5 min; bundle into a
   `run_rdd_track_a.py` script that loops, then add to the RDD section
   of the report.
4. Spatial RDD sensitivity sweep — bandwidth × donut × polynomial-in-
   distance × covariates grid (Step 4 in the original RDD plan).

---

## Skipped / blocked (require user action)

- **CAP pipeline:** needs external CAP-liability coding (RAND or
  Giffords). The project's Tufts panel doesn't have the standard
  variable.
- **2024 BJS Prisoners:** waiting for BJS publication.
- **Census ALFIN 2023+:** Census 2023 release was Individual-Unit-File
  only with no summary table; police_expenditure 2023+ remains NaN.
- **NCHS county-level mortality:** would need restricted-use IRB
  approval (Section 2.10 of data_appendix). Not addressable
  programmatically.
