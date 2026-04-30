# Data Appendix: Where every number on this site comes from, and what we did to it

This appendix is meant to be readable by anyone — researchers, journalists,
policy people, or curious neighbors — without needing a statistics or data
background. Every variable that appears in the panels or on the website is
listed here together with:

1. The original public source that published it.
2. The exact file or web page we pulled it from.
3. Any change we made to the raw data, in plain English, and why.

If a number on the website looks wrong, this is the first place to check.
If you want to reproduce everything from scratch, see "How to rebuild" at the
end. The companion machine-readable inventory is
[`firearms_us_data_inventory.md`](firearms_us_data_inventory.md), and the
per-source manipulation log lives at
[`data/processed/sources_integrated.csv`](data/processed/sources_integrated.csv).

> **Reading guide.** Each section has a short "What this is" paragraph for
> the general reader, followed by a "Technical detail" block for anyone
> who needs to reproduce the work.

---

## Section 0 — Vocabulary

A few terms we use throughout, in plain language:

- **Panel.** A spreadsheet where every row is one place in one year (e.g.,
  "Iowa in 2015" or "Cook County in 2020"). Every panel here is **balanced**:
  every place appears in every year of the panel's window, so there are no
  unexplained gaps when you compare across places or across time.
- **State-year panel.** One row per state per year. The four state-year
  panels in this project cover 50 states and various year windows.
- **County-year panel.** One row per county per year. The county panel
  covers 3,133 counties from 2009 through 2024.
- **FIPS.** A short numeric code for a place. States have 2-digit codes
  (California = 06). Counties have 5-digit codes that combine the state
  and county codes (Los Angeles County = 06037).
- **Real-USD / 2024 dollars.** Dollar amounts adjusted for inflation so
  that a 2015 dollar and a 2024 dollar represent the same real buying power.
  We use the Consumer Price Index (CPI-U) annual averages from the U.S.
  Bureau of Labor Statistics for this.
- **Per 100,000.** A standard rate that lets you compare different-sized
  places fairly: "if this place had exactly 100,000 people, this is how
  many of those people would have experienced this event in this year."

---

## Section 1 — The state-year panels (1979 through 2024)

**What this is.** Four spreadsheets in
[`data/processed/`](data/processed/) that line up firearm laws, crime,
firearm-related deaths, demographics, the economy, and gun-market activity
for each U.S. state in each year. They're called "core", "demographic",
"market", and "modern" because each one trades a longer history for fewer
variables, or vice versa, depending on what your analysis needs.

**Bottom-line summary.**

| Panel | Years | Rows | Description |
|---|---|---|---|
| `panel_core_1979_2024` | 1979–2024 | 2,300 | The longest-running state-year file. Has firearm laws, crime, basic economic controls. |
| `panel_demographic_1990_2024` | 1990–2024 | 1,750 | Adds reconstructed race/sex/age population shares. |
| `panel_market_1999_2024` | 1999–2024 | 1,300 | Adds FBI background-check counts (NICS). |
| `panel_modern_2008_2024` | 2008–2024 | 850 | Adds modern detailed demographics from the American Community Survey. |

Each panel was built by an upstream pipeline ([`scripts/build_firearms_panel.py`](scripts/build_firearms_panel.py))
that existed before this current pass. We then *augmented* every panel
with three additional data layers (see Section 1.4).

### 1.1 Firearm laws (Tufts)

**What this is.** Each year, every state had a particular set of firearm
laws in force — for example, "California requires universal background
checks" or "Wyoming does not require a permit to carry concealed". This
data turns that into 72 yes/no flags per state per year, and a single
total count, so we can ask things like "how many of these laws were in
force in this state this year?"

**Source.** [Tufts CTSI State Firearm Laws Database](https://www.tuftsctsi.org/state-firearm-laws/),
1976–2024. Coded by Michael Siegel and colleagues, originally with Robert
Wood Johnson Foundation funding.

**What we did.** Loaded the published Excel workbook at face value. We
*derived* six summary indices by adding up Tufts' indicators in obvious
groups: "background check index" sums all the background-check provisions,
"carry restriction index" sums the carry-permit provisions, and so on. The
exact group memberships are in [`scripts/build_website_data.py`](scripts/build_website_data.py)
under `LAW_GROUPS`.

**Caveats.** Tufts notes that recent court decisions (the 2022 *Bruen* case
in particular) put some state laws in legal limbo. Tufts does not generally
re-code temporary court injunctions. If a particular state had a major
court fight in the last few years, treat its 2023–2024 entries as
"law on the books" rather than "law in operational effect".

### 1.2 Crime (FBI Uniform Crime Reports, OpenCrime extraction)

**What this is.** How many violent crimes and property crimes were reported
to the FBI in each state each year, broken into specific offense types
(homicide, robbery, rape, aggravated assault, burglary, larceny, motor
vehicle theft) — and the same numbers expressed as a rate per 100,000
people.

**Source.** Originally [FBI Uniform Crime Reports / Crime Data Explorer](https://cde.ucr.cjis.gov/).
We use the OpenCrime project's extraction (`data/opencrime_state_trends.json`)
because it provides ready-to-parse JSON for the same FBI numbers. The
upstream FBI series goes back to 1960; we use 1979 onward to align with
the rest of the state panel.

**What we did.**
- Loaded the OpenCrime JSON, kept the per-state per-year counts and
  computed per-100,000 rates from population denominators (see Section 1.5
  for the population source).
- **Repaired one known data error in the source.** The OpenCrime feed
  double-listed North Carolina for 2022 and missed North Dakota for the
  same year. The second NC 2022 entry was actually ND data with the wrong
  state label (its population matches ND, not NC). We re-labelled it back
  to ND. This single fix is logged in
  [`data/processed/crime_repairs_log.csv`](data/processed/crime_repairs_log.csv)
  and applied identically anywhere these crime numbers are used.

**Caveats.**
- The FBI changed the legal definition of "rape" in 2013. Pre-2013 and
  post-2013 rape rates are not directly comparable.
- The FBI began transitioning from UCR (Uniform Crime Reports) to NIBRS
  (National Incident-Based Reporting System) in 2021. This affected agency
  participation and reporting consistency for some years; coverage is
  improving but not back to UCR-era completeness.

### 1.3 Firearm-related deaths (Kalesan-style v2 dataset)

**What this is.** How many people in each state died by firearm suicide,
firearm homicide, all suicides, and all homicides each year. Also includes
a measure called "FS/S" (firearm-suicide share), which the public-health
literature often uses as a proxy for how many households in that state own
a firearm.

**Source.** A long-run state file (1949–2023) compiled in the
firearm-suicide-share / Kalesan tradition. Stored as
[`data/firearm_suicide_homicide_dataset_v2.tab`](data/firearm_suicide_homicide_dataset_v2.tab).
The same idea is described in the related literature, e.g. the
[2023 *Data in Brief* paper](https://pubmed.ncbi.nlm.nih.gov/37743886/).

**What we did.**
- Loaded the file as-is.
- *Computed* per-100,000 rates from the count columns and the same year's
  population.
- Mapped the long-form state names to the same two-letter abbreviations
  used elsewhere in the project so it joins cleanly.

**Important caveat (please read).** FS/S is the share of all suicides
that involved a firearm. This number is mechanically tied to the suicide
data itself, so **never use FS/S as an explanatory variable when your
outcome is suicide** — you'd just be regressing a thing on a piece of
itself. Use FS/S as a descriptive ownership stand-in only, and prefer
the RAND household firearm ownership rate (see Section 1.4) for analyses
of suicide outcomes.

### 1.4 Three augmentation layers added in this pass

These three sources were already inventoried but not yet *merged* into
the per-state spreadsheets when this pass started. We added them with
[`scripts/augment_panels.py`](scripts/augment_panels.py).

**Granular crime components from FBI/OpenCrime.** Pulled the per-offense
counts and per-100k rates (homicide, robbery, rape, aggravated assault,
burglary, larceny, motor vehicle theft). 100% coverage in every panel.

**Firearm and total suicides, firearm and total homicides from the v2
file.** Counts and per-100k rates for 1979–2023 (the source ends in 2023,
so 2024 cells are intentionally blank for these variables).

**Household firearm ownership rate (RAND TL-354).** Estimated share of
adults in each state who live in a household with a firearm, 1980–2016.

**Source for RAND.** [RAND State-Level Estimates of Household Firearm
Ownership](https://www.rand.org/pubs/tools/TL354.html) by Schell, Peterson,
Vegetabile, Scherling, Smart, and Morral (2020). Downloaded as
`RAND_TL354.database.zip`, kept on disk as
[`data/TL-354-State-Level Estimates of Household Firearm Ownership.xlsx`](data/TL-354-State-Level Estimates of Household Firearm Ownership.xlsx).

**What we did with RAND.** Loaded the "State-Level Data & Factor Score"
sheet, mapped state names to abbreviations, kept the HFR estimate and
its standard error, and joined by (state, year). Years outside 1980–2016
remain blank — we don't fill them in.

**Why RAND is the better ownership measure.** RAND's HFR is a structural
estimate that combines several underlying surveys and administrative
sources (BRFSS, Pew, Gallup, GSS, hunting licenses, *Guns & Ammo*
subscriptions, NICS, and the FS/S proxy itself) into one number per state
per year. It's the most careful state-level ownership estimate publicly
available. The trade-off is that it ends in 2016.

### 1.5 Demographics, economy, and gun-market controls

**Demographics.** State race/sex/age shares come from a mix of sources
depending on the year. The pipeline (in [`scripts/build_firearms_panel.py`](scripts/build_firearms_panel.py))
uses Census ASRH text files for 1990–1999, the 2000s intercensal CSVs for
2000–2009, and Census/PEP for 2010–2024. The American Community Survey
(ACS 1-year) is used directly from 2008 onward when available. Bachelor's
degree share before 2008 is interpolated within state from the
Statistical Abstract Table 229 anchor years (1990, 2000, 2008).

**Economy.** Per-capita personal income (BEA via FRED), state population
(Census via FRED), unemployment rate (BLS LAUS via FRED, monthly series
averaged to annual). Income is published in nominal dollars and we
deflate to 2024 dollars using CPI-U annual averages. Median household
income at the state level is from the Census SAIPE program.

**Gun-market activity (NICS).** FBI National Instant Criminal Background
Check System counts by month, state, and check type. Data are from the
[Data Liberation Project's NICS extraction](https://www.data-liberation-project.org/datasets/nics-firearm-background-checks/).
We use 1999 onward (1998 is partial) and per-100k normalization. **NICS
is not gun sales** — some states use NICS for permit re-checks (which
inflate counts) and a single check can cover multiple firearms. Read NICS
as "legal-market activity flow", not "guns sold".

### 1.6 Summary of state-panel manipulations (the "what changed" list)

Every change made to source data in the state panels:

| Source | What we changed | Why |
|---|---|---|
| OpenCrime granular crime | Reassigned a stray 2022 NC row (population ~780k) to ND | The raw feed double-listed NC and missed ND for that year; population fingerprint matched ND |
| RAND HFR | Joined as-is; no transformation | The published file is already clean |
| Firearm suicide/homicide v2 | Computed per-100k rates ourselves from counts | The source ships counts but not rates |
| Tufts laws | Derived 6 summary indices by summing related indicators | Easier to read on a map than 72 individual flags |
| All economy variables in nominal USD | Deflated to 2024 USD using CPI-U annual averages | So values are comparable across years |
| SAIPE 1990–1992 and 1994 | Linearly interpolated within state | SAIPE skipped these years; interpolation preserves the balanced panel |
| Pre-2008 bachelor's-or-higher share | Linearly interpolated within state from Census Statistical Abstract Table 229 anchors (1990, 2000, 2008) | Single-year college-attainment estimates aren't consistently available before ACS |

---

## Section 2 — The county-year panel (2009 through 2024)

**What this is.** A new spreadsheet
([`data/processed/county_panel_2009_2024.csv`](data/processed/county_panel_2009_2024.csv))
that does the same thing as the state panels but at the county level: one
row per U.S. county per year. We chose 2009–2024 because that's the window
where every layer is high-quality and comparable across counties.

**Numbers.** 3,133 counties × 16 years = 50,128 rows. The panel is fully
balanced: every county appears in every year.

### 2.1 Population (Census Population Estimates Program / PEP)

**What this is.** Each county's resident population for each year.

**Source.** Three flat files from the U.S. Census Bureau's Population
Estimates Program:

- 2009 from [the 2000–2010 intercensal totals file](https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/county/co-est00int-tot.csv).
- 2010–2019 from the [Vintage 2019 PEP all-data file](https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/counties/totals/co-est2019-alldata.csv).
- 2020–2024 from the [Vintage 2024 PEP all-data file](https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/totals/co-est2024-alldata.csv).

We saved the raw files under [`data/county/`](data/county/).

**What we did.** Picked the `POPESTIMATE{year}` columns for each year in
the panel window and stacked them into one long table. Each county-year
appears once.

### 2.2 Income and poverty (Census SAIPE)

**What this is.** The Census Small Area Income and Poverty Estimates
program publishes one estimate per county per year for median household
income and the all-ages poverty rate.

**Source.** One Excel workbook per year from the Census website, e.g.
[`est24all.xls`](https://www2.census.gov/programs-surveys/saipe/datasets/2024/2024-state-and-county/est24all.xls).
We have the 2009–2024 files in [`data/county/`](data/county/) (16 files
total, named `saipe-est{YY}all.xls`).

**What we did.**
- Read each year's file, dropped the national and state-only summary rows,
  kept the county-level rows.
- Harmonized the column names (Census changed a few label spellings between
  2009 and 2010; the script handles both).
- Combined all 16 years into one long table.
- Computed a real-USD version of median household income using CPI-U
  annual averages, with 2024 as the base year.

**Caveats.** SAIPE does not publish a county-level estimate for the
District of Columbia (it appears at the state level only), so DC is blank
for these variables.

### 2.3 Unemployment (BLS LAUS via the USDA ERS mirror)

**What this is.** The annual average unemployment rate in each county.

**Source.** The Bureau of Labor Statistics publishes LAUS (Local Area
Unemployment Statistics) for every county. The U.S. Department of
Agriculture's Economic Research Service maintains a convenient single-file
mirror of the same data:
[unemployment-and-median-household-income-for-the-united-states-states-and-counties-2000-23.xlsx](https://www.ers.usda.gov/media/5494/unemployment-and-median-household-income-for-the-united-states-states-and-counties-2000-23.xlsx).

**Why the ERS mirror, not BLS directly?** The BLS website blocks our
network's automated requests. ERS publishes the same numbers BLS does.

**What we did.** Read the workbook, kept county rows, melted the per-year
"Unemployment_rate_2009", "Unemployment_rate_2010", ... columns into a
long table. The file currently runs 2000–2023, so **the panel's 2024 cells
are blank for unemployment** — that data isn't released yet, and will be
filled when ERS publishes the 2024 update (typically late in the following
year).

### 2.4 Per-capita personal income (BEA CAINC1)

**What this is.** Each county's average personal income per resident, per
year.

**Source.** The Bureau of Economic Analysis publishes CAINC1, "Personal
Income Summary", as a downloadable ZIP of one CSV per state. We downloaded
[CAINC1.zip](https://apps.bea.gov/regional/zip/CAINC1.zip) and unpacked it
to [`data/county/bea_cainc1/`](data/county/bea_cainc1/) (one file per state,
plus a U.S. total file).

**What we did.**
- Read each state's CSV.
- Kept only "LineCode 3" rows, which BEA defines as "Per capita personal
  income (dollars)".
- Stripped quotes and whitespace from the GeoFIPS column to get clean
  5-digit county FIPS codes.
- Stacked years 2009–2024 into a long table.
- Computed a real-USD version using CPI-U annual averages (2024 base).

**Caveats.** 53 counties don't appear in the BEA CAINC1 file with their
own per-capita figure. These are mostly Virginia counties paired with
adjacent independent cities — BEA reports them as a combined area rather
than separately — plus a small Hawaii anomaly (Kalawao County). We chose
to leave those cells blank rather than guess.

### 2.5 Demographics from the American Community Survey 5-year (Census API)

**What this is.** The share of each county's population that is male,
that is non-Hispanic White, non-Hispanic Black, Hispanic, in different
age groups, and the share of adults age 25 and over with a bachelor's
degree or higher.

**Source.** The U.S. Census Bureau's American Community Survey 5-year
estimates, accessed through the [Census Data API](https://www.census.gov/data/developers/data-sets/acs-5year.html).
We pull one year at a time and cache each year's response under
[`data/county/acs5_cache/`](data/county/acs5_cache/) so re-runs are fast.

**Tables we use.** B01001 (sex by age), B03002 (Hispanic or Latino origin
by race), and either B15003 (educational attainment 25+, used for 2012
and later) or the older B15002 (used for 2009–2011, before B15003 existed).

**What we did.**
- Built one URL per year that asks for ~24–28 specific cells across all
  counties in the country.
- For each year, computed: share male = B01001_002 / B01001_001;
  share white non-Hispanic = B03002_003 / B03002_001;
  share Black non-Hispanic = B03002_004 / B03002_001;
  share Hispanic = B03002_012 / B03002_001;
  share age 15–24 = sum of male and female 15–24 cells / total;
  share age 25–44 = sum of male and female 25–44 cells / total;
  share bachelor's-or-higher = sum of bachelor/master/professional/doctorate
  cells / population 25+.
- Coverage is 100% across all 16 years.

**Note about the 2012 table change.** Census replaced its educational
attainment table B15002 with B15003 starting with the 2012 release. The
script automatically picks the right table for each year, so the
bachelor's-or-higher series is continuous across the change.

**Note about ACS 5-year naming.** "ACS 5y 2024" really means "the rolling
average of ACS surveys collected over calendar years 2020–2024". We attach
that estimate to year 2024 in the panel. This is the standard convention
for using ACS in a county-year panel.

### 2.6 State firearm laws joined down to counties

**What this is.** Firearms law is set at the state level (with a few
local-ordinance exceptions in non-preempting states). For each county, we
attach its state's law indicators in that year, so analyses can use county
demographics together with the law environment.

**Source.** Same as Section 1.1 (Tufts state firearm laws). We use the
state-year `panel_core_1979_2024.csv` and join it to the county panel by
state FIPS and year.

**What we did.** Renamed the law columns with a `law_` prefix and merged.
Counties in DC have blank law columns because Tufts does not include DC.

### 2.7 The county FIPS bridge (handling renames and reorganizations)

**The problem.** A few counties were renamed, dissolved, or reorganized
between 2009 and 2024. If we just stacked years naively, the panel would
look unbalanced or contain a mix of "old name" and "new name" rows for
the same place.

**What we did.** Applied the bridge documented in
[`data/processed/county_fips_bridge.csv`](data/processed/county_fips_bridge.csv).
In plain English:

- **Alaska:** Wade Hampton Census Area was renamed to Kusilvak Census Area
  in 2015 (FIPS 02270 → 02158). We re-label the old code to the new code so
  it appears as one continuous county.
- **South Dakota:** Shannon County was renamed to Oglala Lakota County in
  2015 (FIPS 46113 → 46102). Same treatment.
- **Virginia:** Bedford City (FIPS 51515) reverted to town status and
  rejoined Bedford County (FIPS 51019) in 2013. We add the city's
  pre-2013 numbers into the county before merging.
- **Connecticut:** The state replaced its 8 historical counties (FIPS
  09001, 09003, 09005, 09007, 09009, 09011, 09013, 09015) with 9 new
  Planning Regions (FIPS 09110, 09120, 09130, 09140, 09150, 09160, 09170,
  09180, 09190) starting in 2022. The new regions are **not the same
  geographic shapes** as the old counties, so there is no clean way to
  splice them into one continuous time series without making a separate
  population-weighted apportionment. **We dropped Connecticut from the v1
  county panel entirely** and noted this as a known gap to fill in a
  follow-up pass.

**Three Alaska entities also dropped** because the 2019 split of
Valdez-Cordova Census Area into Chugach (FIPS 02063) and Copper River
(FIPS 02066) leaves none of those three (the original 02261 plus the two
new ones) with a continuous 16-year coverage. They are listed in
[`data/processed/county_panel_dropped.csv`](data/processed/county_panel_dropped.csv).

### 2.8 Sanity checks we ran on the county panel

After building the panel we verified:

- **State totals.** Sum every county's 2024 population by state and
  compare to the published Census state totals. Differences were within
  0.1–0.4% across CA, TX, FL, NY, WY (the differences come from rounding
  in PEP intercensal estimates and the dropped CT/AK entities).
- **Spot checks against published values.** Manhattan (NY) 2022 per-capita
  income $199,790 matches BEA's published figure. Arlington VA 2022
  bachelor's-plus share 76.8% matches ACS published estimates (and
  matches Arlington's well-known position as the highest-educated U.S.
  county). Oglala Lakota SD 2022 per-capita income $36,599 and 8.1%
  bachelor's-plus is consistent with its position as the poorest U.S.
  county. LA County 2022 unemployment 5.0% matches BLS published rate.
- **Year-over-year changes.** Six county-years show a population change
  greater than 30%. All six are well-known data quirks: PEP rebenchmarks
  to the 2020 census for two small counties (Trinity CA, Madison ID),
  small-base noise for two tiny Texas counties (Hudspeth, Concho), and
  Loving County TX (population 67–119 across the panel — percentage
  changes are inherently noisy when the base is double digits).

### 2.9 State firearm mortality joined down (Phase 2a)

**What this is.** Four columns on every county row that report the
**state-level** firearm-related death rates and the FS/S ownership
proxy for that county's state in that year. Every county in California in
2020 has the same `state_firearm_suicide_rate` (California's value);
every county in Wyoming in 2020 has Wyoming's value; and so on. There is
no within-state variation.

**Source.** The same firearm-suicide / homicide v2 dataset described in
Section 1.3 — but joined by `(state_fips, year)` to every county row.

**Columns added.**
- `state_firearm_suicide_rate` — firearm suicides per 100,000 (state value).
- `state_total_suicide_rate` — all-method suicides per 100,000 (state value).
- `state_firearm_homicide_rate` — firearm homicides per 100,000 (state value).
- `state_ownership_fss` — firearm-suicide-share ownership proxy
  (state value, 0–1 scale).

**Coverage.** 93.75% of county-years. The 6.25% gap is **all of 2024**:
the v2 file ends in 2023, so 2024 cells are blank for these four
columns. They will fill in once the v2 file releases 2024 numbers.

**Why we chose this approach for v1 of Phase 2.** The user-preferred
approach (3-year-window aggregation from CDC WONDER) requires either:

1. Constructing a CDC WONDER XML API query — which we attempted but
   received generic "error processing your request" 400s. This needs
   careful query construction and may need multiple iterations to get
   right. We've documented this as Phase 2b.
2. Downloading the NCHS Multiple Cause of Death public-use microdata
   files from CDC FTP — total ~1.8 GB across 1999–2023, ~3 million
   death records per year, fixed-width text format. Parsing is
   straightforward but the public-use files **suppress county FIPS for
   counties under 250,000 population**, so even with these files we
   only get true county detail for the ~245 largest U.S. counties (they
   contain ~50% of the U.S. population, but it's not all counties).

**Honest framing.** The state-baseline approach is the simplest honest
thing we can do today. It gives every county a usable mortality
variable while making it impossible to mistake the value for true
county-level detail (the `state_` prefix is a tell). Phase 2b will
overlay real county detail where the underlying sources support it,
not replace this baseline.

**Caveats (please read).** These columns do **not** vary across
counties within a state. Do not interpret `state_firearm_suicide_rate`
in Los Angeles County as the suicide rate of LA County — it is the
California state suicide rate, applied to LA County. To analyze
within-state county variation in mortality, wait for Phase 2b or use
CDC WONDER directly.

### 2.10 Phase 2b — county-detailed firearm mortality (deferred plan)

**What this would add.** Real county-3-year-window firearm suicide and
firearm homicide counts/rates for the ~245 U.S. counties with
population ≥250,000. Smaller counties remain on the state baseline
from Phase 2a.

**Best-available data path.** Download the NCHS public-use Multiple
Cause of Death files from
<https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/DVS/mortality/>
for the 2009–2023 panel window (15 files × ~120 MB each, ~1.8 GB
total). Parse each year's fixed-width text file extracting only:
year, state of residence, county of residence (suppressed for <250k
pop counties), and ICD-10 underlying cause of death. Filter to
firearm-related causes:

- `X72`, `X73`, `X74` — intentional self-harm by firearm (suicide).
- `X93`, `X94`, `X95` — assault by firearm (homicide).
- `W32`, `W33`, `W34` — accidental firearm discharge.
- `Y22`, `Y23`, `Y24` — firearm discharge of undetermined intent.
- `*U01.4` — terrorism involving firearms (rare, included for completeness).

Aggregate to (county_fips, 3-year-window, cause_category) → counts;
divide by 3-year average population (already in the panel) for rates.

Output columns to add when this lands:

- `county_firearm_suicide_count_3y`
- `county_firearm_homicide_count_3y`
- `county_firearm_suicide_rate_3y`
- `county_firearm_homicide_rate_3y`
- `county_mortality_county_detail_available` — boolean flag

**Alternative path: CDC WONDER API.** The official Centers for Disease
Control "Wide-ranging Online Data for Epidemiologic Research" tool has
a documented HTTP POST API that returns the same county-year-cause
aggregations and applies CDC's standard <10-deaths cell-suppression
rule. The API is at
`https://wonder.cdc.gov/controller/datarequest/D77` and accepts an
XML query parameter set. We tested the endpoint and it responds (200
on landing, 400 on malformed POSTs, with HTML error responses), but
constructing a valid query specification is tedious and was deferred
to a follow-up pass.

**Why neither path landed in this checkpoint.** Time and bandwidth.
Both paths are well-understood; either can be implemented when the
user wants county-detailed mortality.

### 2.11 Summary of county-panel manipulations

| Source | What we changed | Why |
|---|---|---|
| Census PEP | Stitched three vintages (intercensal, 2010–2019, 2020–2024) into one continuous series | No single PEP file covers 2009–2024 |
| SAIPE | Harmonized column-name spellings between the 2009 file and 2010+ files | Census changed labels in 2010 |
| BEA CAINC1 | Stripped quotes and whitespace from GeoFIPS to get clean 5-digit codes | Raw file ships with `"06037 "` style identifiers |
| ACS 5-year | Used B15002 for 2009–2011 and B15003 from 2012 onward for bachelor's-or-higher | Census introduced B15003 in 2012 |
| FIPS codes (AK, SD) | Renamed Wade Hampton → Kusilvak and Shannon → Oglala Lakota | Both are renames of the same geographic area |
| FIPS codes (VA Bedford) | Re-labelled Bedford City rows to Bedford County and summed | Bedford City rejoined the county in 2013 |
| FIPS codes (CT) | Dropped all CT counties from v1 | The 2022 reorganization replaced 8 counties with 9 non-coterminous planning regions |
| FIPS codes (AK Valdez-Cordova) | Dropped 02063, 02066, 02261 | The 2019 split leaves none of the three with continuous 16-year coverage |
| All nominal-USD income variables | Deflated to 2024 USD using CPI-U annual averages | So values are comparable across years |

---

## Section 3 — The public website

The map at <https://jedediahpidareese-coder.github.io/firearms-regulation-map/>
is built from the same balanced state panels described above. The build
script is [`scripts/build_website_data.py`](scripts/build_website_data.py),
which produces three JSON files inside [`docs/data/`](docs/data/):

- `panel.json` — every state, every year, every variable that appears on
  the map. ~2 MB.
- `metadata.json` — for every variable: its display label, units, the
  format the website should use to display it (percent, currency, integer,
  etc.), source link, definition, observed year range, and any caveat.
- `manifest.json` — a small index used to populate the dropdowns and
  set defaults.

The page itself ([`docs/index.html`](docs/index.html), [`docs/js/app.js`](docs/js/app.js))
loads these JSON files at view time and renders the choropleth with D3 and
TopoJSON. There is no server-side processing — it is a fully static site.
A definitions page ([`docs/about.html`](docs/about.html)) is auto-generated
from `metadata.json` so the website's variable list and this appendix can
never drift apart.

The U.S. state outlines come from the standard
[us-atlas](https://github.com/topojson/us-atlas) topology
(`states-10m.json`), loaded from the jsdelivr CDN.

---

## How to rebuild everything

```sh
# 1. Rebuild the original state panels from raw inputs (slow).
python scripts/build_firearms_panel.py

# 2. Audit them (writes data/processed/panel_audit_*.csv and panel_audit_report.md).
python scripts/audit_panels.py

# 3. Add the suicide / RAND ownership / granular crime layers.
python scripts/augment_panels.py

# 4. Build the website data files.
python scripts/build_website_data.py

# 5. Build the county panel.
python scripts/build_county_panel.py

# 6. (Coming) Phase 2: county firearm mortality at 3-year windows.
# python scripts/build_county_mortality.py

# Preview the website locally.
python -m http.server 8765 -d docs
# then open http://localhost:8765/
```

---

## Open log of changes

| Date | Phase | What changed |
|---|---|---|
| 2026-04-22 | Initial | Inventory and the four state-year balanced panels prepared by the upstream pipeline. |
| 2026-04-29 | Website v1 | Built the public choropleth map and definitions page; deployed to GitHub Pages. Added RAND household firearm ownership (TL-354) to the website data. |
| 2026-04-29 | Audit + augment | Wrote `audit_panels.py` and `augment_panels.py`; added granular crime, firearm/total suicides, firearm/total homicides, FS/S, and RAND HFR to all four state panels as `*_augmented.csv`. |
| 2026-04-29 | Website polish | Fixed legend overlap; rewrote unit labels to be capitalized and contextual; added explicit `format` field to metadata. |
| 2026-04-29 | County Phase 1a | Built `county_panel_2009_2024.csv` with PEP population, SAIPE income/poverty, state laws joined down. 3,133 counties × 16 years balanced. |
| 2026-04-29 | County Phase 1b | Added BLS LAUS unemployment (via USDA ERS mirror), BEA per-capita personal income, and ACS 5-year demographic shares (sex, race/Hispanic, age groups, bachelor's+) to the county panel. |
| 2026-04-29 | Phase 2a | State-level firearm suicide / total-suicide / firearm-homicide rates plus the FS/S ownership proxy joined down to every county-year. State value, no within-state variation, 2009-2023 (2024 not yet released by the v2 source). |
| 2026-04-29 | Phase 2b | _Deferred._ Plan documented in Section 2.10. NCHS public-use file approach (~1.8 GB download, ~245 large counties only) or CDC WONDER API (XML construction work). Will be picked up after Phase 3. |

This file is updated at the end of every meaningful change. The most
recent commits in <https://github.com/jedediahpidareese-coder/firearms-regulation-map/commits/main>
will always reflect the current state.
