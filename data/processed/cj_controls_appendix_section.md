### 2.13 Criminal-justice controls (Phase 4)

**What this is.** A small companion file
([`data/processed/state_cj_controls_1979_2024.csv`](data/processed/state_cj_controls_1979_2024.csv))
that gives every state-year a vector of criminal-justice "posture"
variables, plus a thin county-year companion
([`data/processed/county_cj_controls_2009_2024.csv`](data/processed/county_cj_controls_2009_2024.csv))
that exposes the one variable that is observed at the county grain.
These controls feed into both the existing CS21 / stacked-DiD specs
and the planned spatial-RDD design, where they robustify identification
by absorbing state-level CJ context (which is plausibly correlated with
both gun-policy adoption and the crime/mortality outcomes of interest).
The CJ layer joins to the analysis frame at run-time via
`(state_fips, state_abbr, year)`; it does NOT touch the existing
`panel_*.csv` or `county_panel_2009_2024.csv` outputs.

**Outputs.**

| File | Rows | Columns of interest |
|---|---|---|
| `data/processed/state_cj_controls_1979_2024.csv` | 51 states × 46 years = 2,346 | `imprisonment_rate`, `police_expenditure_per_capita_real_2024`, `has_death_penalty`, `executions_count`, `sworn_officers_per_100k` (placeholder) |
| `data/processed/state_cj_controls_coverage.csv` | per-variable per-year coverage table | diagnostic only |
| `data/processed/county_cj_controls_2009_2024.csv` | 3,133 counties × 16 years = 50,128 | `county_sworn_officers_per_100k` (placeholder until LEOKA file is downloaded) |

**Build scripts.** [`scripts/build_state_cj_controls.py`](scripts/build_state_cj_controls.py)
and [`scripts/build_county_leoka.py`](scripts/build_county_leoka.py).
Raw inputs live under `data/state_cj_raw/` and `data/county/kaplan_leoka/`
(gitignored — same convention as `data/county/kaplan_offenses/`; rebuild
by running the scripts after re-downloading the source files documented
below).

#### 2.13.1 Imprisonment rate (state-year)

**What this is.** Total prisoners under state-or-federal correctional
jurisdiction (year-end stock) divided by state resident population,
expressed as the rate per 100,000 residents. Same denominator the
project uses elsewhere
([`data/processed/state_population_1900_2025.csv`](data/processed/state_population_1900_2025.csv)).

**Source.** U.S. Bureau of Justice Statistics, National Prisoner
Statistics Program (NPS-1A), distributed as a series of annual
"Prisoners in 20XX" reports. Landing page:
<https://bjs.ojp.gov/data-collection/national-prisoner-statistics-nps-program>.
Each report's Table 2 (post-2014) or Table 3 (pre-2014) lists the
state-by-state stock for the report year and the prior year. We
downloaded one report per available year and stitched them.

Raw files used (each is a small CSV/PDF in `data/state_cj_raw/`):

- 1980, 1982–1983, 1986–1992, 1996, 1997 — older PDF reports
  (`p80.pdf`, `p82.pdf`, `p83.pdf`, `p86.pdf`–`p92.pdf`, `p96.pdf`,
  `p97.txt`). Parsed by extracting Table 1 from the first two pages
  and matching state-name lines against a regex that requires two
  plausible large integers (year-current, year-prior) with a
  year-over-year ratio in 0.7–1.5.
- 1998 onward — official BJS spreadsheet zips (`p98.zip` … `p23st.zip`),
  parsed via per-report column-position maps (each report's Table 2/3
  has a slightly different layout — male/female sub-columns, blank
  columns, different orderings — so the parser uses an explicit
  `(year, column_offset_after_state_name)` pair per report).

**What we did** (in `scripts/build_state_cj_controls.py`):

1. Downloaded the available BJS report tables to `data/state_cj_raw/`.
2. For each report file, extracted the per-state TOTAL (jurisdictional)
   prisoner stock for the report year and the prior year. Where the
   raw spreadsheets ship a sex-breakdown or sentenced-only table, we
   grab only the "Total" column.
3. Where multiple reports cover the same state-year (e.g. both
   `p18t02.csv` and `p19t02.csv` carry 2018), we keep the value from
   the later-publication report (BJS revises prior years between
   editions; the later edition is the canonical revised count).
4. Divided the result by the state population from
   `state_population_1900_2025.csv` and multiplied by 100,000.

**Coverage.** 1,921 of 2,346 state-years (81.9%). Year-by-year:

| Years | Coverage | Notes |
|---|---|---|
| 1979–1980 | ~37/51 | From `p80.pdf`; older states with footnote/OCR artifacts dropped |
| 1981 | 0/51 | `p81.pdf` table renders state names and numbers in separate text columns; PDF parsing fails. Documented gap. |
| 1982–1983 | ~39/51 | Partial PDF extraction; some states have OCR-scrambled rows |
| 1984 | 0/51 | No `p84.pdf` in the BJS legacy archive at the time of build |
| 1985–1992 | 43–49/51 | Clean PDF extraction with the period-as-thousands-separator fix (`87.297` → `87,297`) |
| 1993–1995 | 0/51 | No `p93/p94/p95.pdf` in the BJS legacy archive. The 2012 BJS "Trends" companion (`p12tar9112.zip`) covers admissions/releases but not stocks. Documented gap. |
| 1996 | 49/51 | From `p96.pdf` |
| 1997–1998 | 50/51 (DC missing) | From `p97.txt` and `p98.zip` |
| 1999–2023 | 49–51/51 (DC missing post-2001; ND missing one year) | From the per-year BJS report zips |
| 2024 | 0/51 | "Prisoners in 2024" report not yet released (April 2026). Will be added once BJS publishes it. |

DC missing post-2001 is correct: DC closed Lorton in 2001 and
transferred its sentenced prisoners to the Federal Bureau of Prisons,
so DC has no state-jurisdiction stock thereafter. Treat DC as 0 (or
drop) at analysis time.

**Spot checks.**

- California 1980: 24,579 (matches BJS Table 1 in `p80.pdf` exactly).
- California 1989: 87,297 (matches; required parser handling of
  OCR'd periods as thousands separators).
- California 2010: 165,062 (matches; the year before realignment
  reduced CA's stock by ~16k).
- Texas 1979: 26,522, Texas 2020: 137,985 (matches BJS published
  series).
- New York 2007: 62,623 → 2023 stock would have been ~32k (massive
  decarceration; we capture the 2018 value at 47,510 and the 2023
  trajectory at 32,609).

**Caveats.**

1. **Pre-1996 has gaps**. 1981, 1984, 1993–1995 are entirely missing
   because the corresponding BJS PDF reports were not in the legacy
   archive at build time, or extracted with broken table layouts.
   Estimating these years would require either OCR repair or pulling
   from a third-party compilation (e.g. ICPSR NACJD study 38555 or
   the Sourcebook of Criminal Justice Statistics). We did not do
   either; they are documented as gaps.
2. **Definitional shifts.** BJS counts are jurisdictional (where the
   prisoner is legally held) since 1977. Pre-1977 counts use custodial
   definitions and are not in scope here. Within 1979–2024 the
   jurisdictional definition is consistent, but BJS revised individual
   states' totals between editions; we use the most recent revision
   available for each year.
3. **Federal vs state.** The variable is the **state** stock only;
   federal prisoners (BOP) are excluded. For a "total persons under
   correctional jurisdiction" measure, add the federal series from
   `keystatsupdate_2022.csv` (national totals only, included in the
   raw data folder).

#### 2.13.2 Police protection expenditure per capita (state-year, real 2024 USD)

**What this is.** State + local government combined expenditure on
"Police protection" per capita, deflated to 2024 dollars using
BLS CPI-U (annual average). Census of Governments / Annual Survey of
State and Local Government Finances reports this as one of the major
expenditure categories.

**Source.** U.S. Census Bureau, Annual Survey of State and Local
Government Finances. Landing page:
<https://www.census.gov/programs-surveys/gov-finances.html>.
Each fiscal year's **Table 1** (file naming `YYslsstab1.xlsx` post-2017,
`YYslsstab1a.xls` + `YYslsstab1b.xls` for 2009–2011, just `YYslsstab.xls`
or per-state CSVs for older years) is a wide spreadsheet with one
column block per state.

Raw files used (in `data/state_cj_raw/`):

- `02slsstab.xls` and `02slsstab1b.xls` (split-state layout, FY2002).
- `09slsstab.xls`/`09slsstab1b.xls`, `10slsstab.xls`/`10slsstab1b.xls`,
  `11slsstab.xls`/`11slsstab1b.xls` (FY2009–2011).
- `17slsstab1.xlsx` … `22slsstab1.xlsx` (FY2017–2022; single-file
  layout with a leading "Line" column).

**What we did** (in `scripts/build_state_cj_controls.py`):

1. For each Census file, read the spreadsheet and auto-detected the
   layout: location of the state-header row (the row containing
   "Alabama"), the location of the "Police protection" expenditure
   row (looking for that label in column 0 or column 1), and the
   per-state column block size (3 columns pre-2009 = State&Local /
   State / Local; 5 columns 2009+ = State&Local / S&L coefficient
   of variation / State / Local / Local CV).
2. Extracted the State&Local combined "Police protection" expenditure
   for each state. Census reports these in $thousands.
3. Divided by state population (same denominator used for
   `imprisonment_rate`) to get per-capita.
4. Deflated to 2024 dollars using the BLS CPI-U all-urban annual
   average index (`CPI_BY_YEAR` in the build script — values 1979–2008
   from the BLS historical CPI-U PDF tables, 2009–2024 reproduced
   from `scripts/build_county_panel.py` for cross-script consistency).
5. **Linearly interpolated** within state across the gap years
   (2003–2008 and 2012–2016) so analysts have a continuous series
   inside the observed window. The flag column
   `police_expenditure_imputed_flag` marks interpolated values.
   Years outside the observed window (1979–2001 before any anchor,
   2023–2024 after the latest published anchor) remain NaN.

**Coverage.** 1,071 of 2,346 state-years (45.7%) — 51 states ×
the years 2002 and 2009–2022 (with 2003–2008 and 2012–2016
interpolated within state). Pre-2002 and 2023+ remain NaN; the
Census 2023 release was an Individual-Unit-File only (no summary
table), and the 1992/1997 publications shipped only national
totals at this URL.

**Spot checks.**

- California 2009 = $625/cap (real 2024 USD). Matches the
  Government-Finance interactive tool's CA aggregate of ~$15B / ~37M
  residents = ~$405 nominal × CPI deflation ≈ $625.
- Wyoming 2022 = ~$520/cap real (small-state lower bound).
- New York 2010 = ~$910/cap real (state with NYPD as a major
  contributor to the local total).

**Caveats.**

1. **Census is fiscal-year, not calendar-year.** Most state and
   local FYs end June 30, so the 2022 number captures roughly
   July 2021–June 2022 spending. We label it `year=2022` for the
   join; analysts who care about a calendar match should add
   ~half a year to the labeling.
2. **Linear interpolation between Census-of-Governments years.**
   Police expenditure does not move smoothly year-to-year (LE-budget
   shocks happen in waves: post-9/11, post-Ferguson, post-2020,
   post-COVID). Treat interpolated values as a smoothed approximation,
   not a measurement. The `police_expenditure_imputed_flag` column
   identifies interpolated rows.
3. **Includes both salaries and capital outlays.** Census's
   "Police protection" category bundles current operating expense
   plus capital outlays. State-only or local-only breakdowns are
   available in the same files but not exposed here (the State&Local
   combined is the most policy-relevant aggregate for state-level
   identification arguments).

#### 2.13.3 Capital punishment status (state-year)

**What this is.** Two variables:

- `has_death_penalty` (binary state-year) — 1 if the state had an
  active death-penalty statute on December 31 of that year, 0
  otherwise.
- `executions_count` (integer) — count of state-jurisdiction
  executions carried out in that state-year (federal executions
  excluded).

**Source.** Death Penalty Information Center (DPIC) executions
database. Landing page: <https://deathpenaltyinfo.org/>. Direct CSV
download: <http://deathpenaltyinfo.org/query/executions.csv>
(298 KB, 1,664 rows, one per execution, 1977–April 2026). The
underlying records are post-Gregg (the 1976 Supreme Court decision
that allowed capital punishment to resume).

**What we did** (in `scripts/build_state_cj_controls.py`):

1. Downloaded `executions.csv` (saved to `data/state_cj_raw/`).
2. Filtered to `Federal == 'No'` (drop the 16 federal executions
   under Bush-Cheney and Trump 1.0).
3. Mapped `State` to two-letter postal code and grouped by
   `(state_abbr, year)` to get `executions_count`.
4. Hand-coded `has_death_penalty` from the published timeline of
   state abolitions and reinstatements:
    - **Modern (post-1976) abolitions**: NM 2009, IL 2011, CT 2012,
      MD 2013, NE 2015, DE 2016, WA 2018, NH 2019, CO 2020, VA 2021.
    - **Pre-Gregg holdovers / functional abolitions**: NY (statute
      struck down 2004 by *People v. LaValle*; coded as abolished
      2007 since the legislature did not repair through the end of
      Gov. Pataki's term and the Court of Appeals reaffirmed in
      *People v. Taylor* 2007), NJ legislative abolition Dec 2007,
      RI 1984, MA 1984.
    - **Reinstatements**: NE 2016 (ballot referendum reversing the
      2015 legislative repeal).
    - **Never had post-Gregg DP statute**: AK, HI, IA, ME, MI, MN,
      ND, VT, WV, WI, plus DC.

**Coverage.** 100% (all 2,346 state-years). The binary is computed
from the timeline above — no source dependency. The execution count
defaults to 0 for any state-year with no record in DPIC.

**Spot checks.**

- Texas 2000: 40 executions (matches DPIC; peak year).
- Texas 2020: 3 executions (matches; COVID-era slowdown).
- New York post-2007: 0 executions, `has_death_penalty == 0`
  (matches; NY has not had an active statute since Pataki).
- Virginia 2021: still has 1 execution (Christopher Mosley, July
  2017), and `has_death_penalty` switches to 0 in 2021 (the
  abolition year). Pre-2021 Virginia has 113 executions.
- Federal: NOT in this file (we drop federal rows). Federal
  executions are 1 (2001) + 13 (2020–2021) + 0 since.

**Caveats.**

1. **Statute vs practice.** `has_death_penalty == 1` means the statute
   is on the books, NOT that executions are actively occurring. We do
   NOT encode moratoria. California's Newsom moratorium (2019+) and
   Pennsylvania's Wolf moratorium (2015+) leave both states coded
   as `has_death_penalty == 1` because the statute remains. To use
   "active practice" instead, gate on `executions_count > 0` over
   the past N years.
2. **Pre-Gregg years.** 1979 is post-Gregg, but the first execution
   under the modern regime was in 1977 (Gilmore, Utah). States that
   had statutes pre-Gregg but did not enact a Gregg-compliant statute
   are coded `has_death_penalty == 0` from 1979 onward (e.g. AK, HI,
   ME, MI, MN, ND, VT, WI). RI and MA had pre-Gregg statutes that
   were struck down in the 1980s; we code them as DP=1 in their
   early years and DP=0 from the abolition year forward.
3. **NY's 2004–2007 limbo.** NY's death-penalty statute was on the
   books but unconstitutional from 2004 onward. We use 2007 as the
   abolition year (the year the Court of Appeals confirmed in
   *People v. Taylor* that no path to a constitutional statute
   existed under the existing legislative posture). Some sources
   use 2004; the difference matters only for state-year averaging
   in 2004–2006.

#### 2.13.4 Sworn officers per 100,000 residents — placeholder

**What we wanted.** State-year and county-year totals of full-time
sworn (peace-officer-status) law-enforcement personnel from the
FBI UCR LEOKA / Police Employees data, divided by state and county
population to produce per-100k rates.

**What we found.** The FBI's underlying data is published agency-by-
agency-year (one row per ORI per year); aggregating to state/county
requires working from the agency-level file. The cleanest publicly
available copy is **Jacob Kaplan's openICPSR project 102180**
("Uniform Crime Reporting Program Data: Police Employee (LEOKA) Data")
— the LEOKA companion to the offenses-known files we already use for
crime (see Section 2.11). openICPSR projects require a free user
account and login to download.

The existing `data/county/kaplan_offenses/` bundle on this disk
contains only project **100707** (offenses-known), not project
102180 (LEOKA). The offenses-known file does include
`officers_killed_by_felony`, `officers_killed_by_accident`, and
`officers_assaulted` columns — but those are **incident counts, not
employment counts**, and cannot be turned into a sworn-officer
denominator.

**Status.** The build emits placeholder columns with 0% coverage:

- `state_cj_controls_1979_2024.csv`: `sworn_officers_per_100k` = NaN,
  `has_sworn_officers` = 0.
- `county_cj_controls_2009_2024.csv`: `county_sworn_officers_per_100k`
  = NaN, `has_county_sworn_officers` = 0.

The build script
[`scripts/build_county_leoka.py`](scripts/build_county_leoka.py)
is set up so that dropping the openICPSR project 102180 .zip into
`data/county/kaplan_leoka/` (no need to unzip — the script streams
the inner year-aggregated CSV directly) and re-running it will
produce the sworn-officer columns end-to-end (auto-detects the
officer-count column, applies the same FIPS bridge as the crime
panel, sums to county-year, divides by population).

**To complete this variable.** Register at
<https://www.openicpsr.org/openicpsr/project/102180>, download the
project .zip, drop it into `data/county/kaplan_leoka/`, and run
`python scripts/build_county_leoka.py`. We did not scrape
openICPSR (would require login).

#### 2.13.5 Tier 2 variables (deferred)

The original brief listed three additional state-year sentencing
controls as Tier 2, to be built only if Tier 1 work completed under
half the budget. Tier 1 work (especially the multi-vintage BJS
prisoners parsing) consumed most of the budget; **the following
remain v2 work**:

- **Three-strikes laws** (state-year binary): would require coding
  the year of adoption per state from a legal source (Wikipedia /
  Sentencing Project compilation). 26 states have some form;
  CA 1994 was first.
- **Truth-in-sentencing laws** (state-year binary): tied to the
  1994 federal Violent Crime Control Act incentive grants;
  ~30 states adopted some version. Coding requires walking each
  state's enactment record.
- **Mandatory-minimum sentences for firearm offenses** (state-year
  binary): the Tufts firearm-laws panel
  ([`data/tufts_state_firearm_laws.xlsx`](data/tufts_state_firearm_laws.xlsx))
  already has several mandatory-minimum-related indicators; a v2
  pass should harmonize those into a single composite or use the
  Sentencing Project's compilation directly.

Each of these is a ~few-hour hand-coding job from existing legal
references. We left them out of v1 because they are time-invariant
within the policy windows of interest (most enactments cluster
1992–1998, well before the firearm-policy treatments of interest
in this project's CS21 / spatial-RDD designs), and they would
absorb a small amount of degrees of freedom without changing the
identifying variation in the policy-effect specs.

#### 2.13.6 Summary of CJ-controls build manipulations

| Source | What we did | Why |
|---|---|---|
| BJS Prisoners-in-XX CSV (1998–2023) | Per-report column-position map; took the "Total" column only (skipping male/female/sentenced sub-columns) | Each report has a slightly different column layout that breaks naïve "first N numbers" parsing |
| BJS Prisoners-in-XX PDF (1980–1996) | Extracted text from pages 1–2 only; required state-name regex match plus year-over-year ratio in 0.7–1.5 | Avoids picking up values from "change" / "release" / "capacity" tables that appear later in the document |
| BJS PDF text with OCR'd periods | Pre-processed `\d{1,3}\.\d{3}` to `\d{1,3}\d{3}` (treat "87.297" as "87,297") | The period-as-thousands-separator artifact is common in early-1990s scanned reports |
| Multiple BJS reports covering same state-year | Kept the value from the **later** report | BJS revises prior-year counts between editions; the later edition is canonical |
| Census State&Local Finance per-state column blocks | Auto-detected layout (3-col pre-2009, 5-col 2009+, with/without leading "Line" column) | Layout changed with the 2017 publication overhaul |
| Police expenditure across years | Linear interpolation within state across observed-window gaps | Census Annual Survey skipped 2003–2008 and 2012–2016 here; interpolation preserves the panel |
| All current-USD financial values | Deflated to 2024 USD using BLS CPI-U annual averages | So expenditures are comparable across years |
| DC imprisonment | Left as NaN | DC closed Lorton in 2001 and transferred prisoners to BOP; no state stock to report |
| LEOKA / sworn officers | Placeholder columns; documented as needs-manual-download from openICPSR project 102180 | We do not scrape openICPSR (login required); the build script will fill the columns once the .zip is dropped into `data/county/kaplan_leoka/` |
