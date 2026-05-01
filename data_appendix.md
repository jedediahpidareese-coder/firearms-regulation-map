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

### 2.10 Phase 2b — county-detailed firearm mortality (blocked by CDC policy)

**What we wanted.** Real county-3-year-window firearm suicide and
firearm homicide counts/rates for every U.S. county.

**What we found after working through every public path.** True
county-level firearm mortality cannot be obtained from any public CDC
or NCHS source. We confirmed each candidate:

1. **NCHS public-use Multiple Cause of Death files (CDC FTP).** We
   downloaded most of these for 2009–2023 (~1.8 GB) and confirmed by
   inspecting the records: starting with the 2005 release, NCHS removed
   ALL geographic identifiers from public-use files (no county, no
   state, not even region or division). The CDC documentation is
   explicit: *"All public-use micro-data files from 2005-present
   contain individual-level vital event data at the national level
   only, and specifically contain no geographic identifiers at the
   state, county, or city level."* These files are unusable for our
   purpose. We removed the partial downloads from disk to reclaim space.
2. **CDC WONDER API
   (`https://wonder.cdc.gov/controller/datarequest/D77`).** The API is
   alive and responds to authenticated POST requests, but the official
   API documentation (the maintained example notebook for the D76
   Detailed Mortality database, plus the equivalent D77 documentation)
   is unambiguous: *"Queries for mortality and births statistics from
   the National Vital Statistics System cannot limit or group results
   by any location field, such as Region, Division, State or County."*
   That is, the WONDER web interface lets you query by county on the
   browser, but the API does not — only national-level grouping.
3. **NCHS restricted-use files.** These DO contain county FIPS without
   suppression. Access requires an IRB-approved research protocol, a
   Data Use Agreement signed by an institutional officer, and a typical
   review timeline of weeks to months. Out of scope for a website
   build.

**Net result.** The state firearm mortality joined down to every
county (Section 2.9, the `state_*` columns) is the most county detail
we can publish for firearm mortality without restricted-use access.
This is not a code limitation; it is a CDC data-release policy that
applies uniformly to anyone working from public data.

**If you want true county detail later.** The realistic path is to
apply for NCHS restricted-use access through your institution's IRB.
The application form and instructions are at
<https://www.cdc.gov/nchs/data-linkage/research-data-center.htm>. Once
approved, the workflow is the same as what Section 2.9 already
implements, but with the restricted file's county FIPS column
replacing the state-level baseline. Add an `county_firearm_*` column
group; everything else in the county panel stays unchanged.

**A cheaper alternative for spot-checking specific counties.** The CDC
WONDER web UI does serve county-level firearm-cause queries with
their <10-deaths cell-suppression rule. Anyone who wants a single
county's firearm-suicide series can pull it manually from
<https://wonder.cdc.gov/mcd.html> in a few minutes.

### 2.11 County-level crime from Jacob Kaplan's UCR Offenses Known (Phase 3)

**What this is.** For each county, the count and per-100,000 rate of
each major reported crime category (murder, manslaughter, rape, robbery,
aggravated assault, burglary, larceny, motor vehicle theft, arson),
plus the FBI "index violent" and "index property" totals — for each
year 2009 through 2024.

**Why this is hard.** The FBI's old public Crime Data API (the one at
`api.usa.gov/crime/fbi/sapi/`) was decommissioned. Their developer
documentation host doesn't even resolve anymore. The remaining clean
publicly-available source is Jacob Kaplan's "Offenses Known and
Clearances by Arrest" project on openICPSR, which Kaplan maintains by
carefully reading the FBI's raw fixed-width annual files, applying the
agency-to-county crosswalk, and re-publishing in a sane CSV/Stata/RDA
format. Version 22 (the version we used) covers 1960 through 2024 in a
single 908 MB CSV.

**Source.** [Kaplan, Jacob (2025). Jacob Kaplan's Concatenated Files:
Uniform Crime Reporting Program Data: Offenses Known and Clearances by
Arrest, 1960-2024. openICPSR project 100707, Version 22.](https://www.openicpsr.org/openicpsr/project/100707)

The raw download is ~2 GB compressed and ~5 GB unpacked, so it is
**not committed to this repository**. It lives at
`data/county/kaplan_offenses/` (gitignored). To reproduce: register a
free openICPSR account, download project 100707 V22 as CSV, unzip into
that directory, then run `python scripts/build_county_crime.py`. The
processed output (`data/processed/county_crime_2009_2024.csv`,
~9 MB) is committed.

**What we did.**

1. Read the combined `offenses_known_yearly_1960_2024.csv` file in
   chunks, kept only year ≥ 2009 and year ≤ 2024, and only the columns
   we use (FIPS state code, FIPS county code, year, the `actual_*`
   offense counts).
2. Dropped agency rows with no county FIPS — these are federal law
   enforcement (FBI, DEA, ATF, US Marshals), Amtrak police, college
   campus police, transit authorities, and similar non-geocoded
   agencies. ~3,088 such rows in 2024, fewer in earlier years (logged
   in `data/processed/county_crime_dropped_agencies.csv`).
3. Applied the same FIPS bridge the rest of the county panel uses
   (Kaplan publishes pre-rename FIPS for AK Wade Hampton, SD Shannon,
   and VA Bedford City throughout the file, even for years after the
   renames). Mapped 02270 → 02158, 46113 → 46102, 51515 → 51019.
4. Summed agency-level offense counts to (county_fips, year). One
   county can have many reporting agencies (e.g., a sheriff's office
   plus several city PDs); we add them.
5. Computed per-100,000 rates using the panel's PEP population for the
   denominator.
6. Merged the county-year crime layer into the main county panel by
   (county_fips, year).

**Coverage.** 99.81% — every county-year except 6 tiny entities × 16
years = 96 rows missing. The 6 entities with zero LE reporting in
Kaplan are:

- Alaska: Denali Borough (02068), Lake & Peninsula Borough (02164),
  Petersburg Census Area (02195), Southeast Fairbanks Census Area
  (02240), Yakutat City and Borough (02282).
- Hawaii: Kalawao County (15005) — population 80, no police force.

**Spot checks.**

- Los Angeles County 2024: 581 murders, 580/100k violent crime —
  consistent with LA County's typical 500-700 annual murders.
- Cook County (Chicago) 2024: 358/100k violent crime, down from
  622/100k in 2018. The drop probably reflects Chicago PD's NIBRS
  transition reporting issues; treat 2021-2024 Cook County violent
  crime cautiously.
- New York County 2024 (Manhattan only, FIPS 36061): 3,356/100k violent
  crime. This is high because the denominator is residents (1.66 M),
  not the daily workforce/tourist population (~3-4 M); a well-known
  artifact for tourist-heavy or commuter-destination counties.
- Loving County, TX 2024: population 48, 0 murders, 34 reported
  property crimes — small-base noise on a county that has truck stops
  on US-285 and a non-trivial transient population.

**Caveats users should know.**

1. **NIBRS transition.** Many large agencies were still adapting to
   the NIBRS reporting standard during 2021-2024. Some published
   counts for those years may be lower than the underlying truth
   because not every agency in the county reported all 12 months.
   Kaplan flags this in the underlying data; we do not adjust further.
2. **Rape definition change.** The FBI revised its rape definition in
   2013. Pre-2013 and post-2013 `county_rape_*` series are not
   directly comparable.
3. **Federal and special-jurisdiction agencies are excluded.** They
   have no county FIPS; their incidents do not appear in our county
   totals. For most analyses that's the right behavior, but for
   border counties and big-city federal-building areas this can
   modestly understate counts.
4. **County rates use resident population.** Tourist or workforce
   denominators would change rates dramatically in places like
   Manhattan, the National Mall, or Disneyland-area Orange County
   (CA). We disclose this rather than try to adjust.

### 2.12 County population centroids and distance to nearest other-state county (geometry layer for spatial RDD)

**What this is.** A small companion file
([`data/processed/county_border_distances.csv`](data/processed/county_border_distances.csv))
that gives every county its 2020 population centroid (latitude/longitude) and
the great-circle distance, in kilometers, from that centroid to the centroid
of the closest county in a different state. This is the foundation for a
planned spatial regression-discontinuity analysis on state borders: the idea
is that two counties on opposite sides of a state line are demographically and
economically similar, so any sharp jump in outcomes (homicide, suicide,
mortality) across the border can plausibly be attributed to the difference in
the firearm-policy environment.

**Source.** The U.S. Census Bureau publishes "Centers of Population", which
are the population-weighted mean centroids of every county at each decennial
census. We use the 2020 file:
[CenPop2020_Mean_CO.txt](https://www2.census.gov/geo/docs/reference/cenpop2020/county/CenPop2020_Mean_CO.txt)
(~171 KB, 3,221 rows, columns STATEFP, COUNTYFP, COUNAME, STNAME, POPULATION,
LATITUDE, LONGITUDE). Cached locally at
[`data/county/CenPop2020_Mean_CO.txt`](data/county/CenPop2020_Mean_CO.txt).

**Why population centroids and not geometric centroids.** A county like San
Bernardino, CA has its geometric centroid in the Mojave Desert, but virtually
all its residents live in the southwestern corner near LA. A geometric
centroid would put the county "far" from the LA-area state-border environment
its residents actually experience; the population centroid puts it where
people live. Census uses the same definition the Bureau publishes for the
historical migration of the U.S. national mean population center.

**What we did** ([`scripts/build_county_border_distances.py`](scripts/build_county_border_distances.py)):

1. Concatenated 2-digit STATEFP and 3-digit COUNTYFP into the same 5-digit
   `county_fips` used elsewhere in the project.
2. Computed the full pairwise great-circle distance matrix with the Haversine
   formula (Earth radius 6,371 km), vectorized in numpy. ~10 million pairs;
   runs in under a second.
3. For each county, masked all same-state counties and took the argmin of the
   remaining row to find the nearest other-state county and its distance.

**Output columns.**

| Column | Meaning |
|---|---|
| `county_fips` | 5-digit FIPS, matches the rest of the county panel |
| `state_fips` | 2-digit state FIPS |
| `lat`, `lon` | 2020 population centroid in decimal degrees |
| `nearest_other_state_county_fips` | 5-digit FIPS of the nearest county whose state differs |
| `nearest_other_state_fips` | 2-digit state FIPS of that county |
| `distance_to_nearest_other_state_km` | great-circle distance in km |

**Diagnostics on output.** 3,221 county records (50 states + DC + 78 Puerto
Rico municipios). 907 counties (28%) sit within 50 km of an other-state
centroid; 1,962 (61%) within 100 km; 2,822 (88%) within 200 km. Median
distance to nearest other-state centroid is 81.2 km. The five most isolated
records are all Hawaii counties (~3,600–3,770 km to the nearest mainland or
Aleutian centroid), as expected.

**Spot checks.**

- Manhattan, NY (36061) → Hudson County, NJ (34017): 8.8 km. Across the river.
- District of Columbia (11001) → Arlington County, VA (51013): 8.4 km. Across the Potomac.
- Cook County, IL (17031) → Lake County, IN (18089): 48.6 km.
- Honolulu, HI (15003) → Aleutians West, AK (02016): 3,732 km. Closest US "state".
- Adjuntas, PR (72001) → Miami-Dade, FL (12086): 1,632 km.

**Caveats.**

- Centroids are 2020-vintage and held fixed across the panel years; population
  movement during 2009–2024 is not reflected. For RDD purposes the centroid is
  a stable geographic anchor, not a dynamic measure.
- "Nearest other-state county" is the closest centroid in any U.S. state, not
  necessarily a contiguous neighbor. For Hawaii or Puerto Rico the nearest
  other-state record is across an ocean and not a meaningful RDD comparison;
  RDD specifications should restrict to small distance bands (e.g., < 50 km
  or < 100 km), which automatically excludes those entries.
- Connecticut counties were not in the 2009–2024 main panel (Section 2.7), but
  they are present here, anchored to their 2020 (post-reorganization)
  centroids. Use this file for them only if you have a separate CT bridge.
- This file does **not** itself implement an RDD specification. It is the
  geometry layer the per-policy border samples and sharp-RDD models will be
  built on top of in a follow-up pass.

### 2.13 Summary of county-panel manipulations

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
serves both the state and county panels described above. The user picks
one of two **modes** with the radio toggle in the header:

- **State mode (1979–2024):** loads the state-year panel once and renders 50
  states. Topology: us-atlas `states-10m.json` from jsdelivr CDN.
- **County mode (2009–2024):** loads the county manifest + metadata once,
  then lazy-loads one year at a time as the visitor drags the year slider.
  Renders 3,133 counties via us-atlas `counties-10m.json` (842 KB),
  with state borders overlaid in dark gray for visual orientation.

### Build scripts

- [`scripts/build_website_data.py`](scripts/build_website_data.py) — emits the
  state files: `docs/data/panel.json` (~2 MB), `docs/data/metadata.json`,
  `docs/data/manifest.json`.
- [`scripts/build_website_county_data.py`](scripts/build_website_county_data.py)
  — emits the county files: 16 per-year files at
  `docs/data/county/{year}.json` (~2 MB each, 32 MB total) plus
  `docs/data/county_meta.json` and `docs/data/county_manifest.json`.

### Why per-year files for counties

A single combined county JSON would be 25–30 MB, painful for the first page
load. Per-year files are smaller and cache well in the browser; the visitor
only pays for the years they actually scrub through.

### Frontend architecture

The page itself ([`docs/index.html`](docs/index.html), [`docs/js/app.js`](docs/js/app.js))
is plain D3 + TopoJSON, no build step. A `mode` object encapsulates each
geography's specifics: how to map a TopoJSON feature to a key, how to look up
values, what the cross-year color-scale domain is, what context variables to
show in the hover sidebar. The render and legend code is identical for both.
The definitions/methodology page ([`docs/about.html`](docs/about.html))
auto-generates separate variable lists for the state view (40 variables) and
the county view (23 variables) by reading `metadata.json` and
`county_meta.json`, so the website and this appendix cannot drift apart.

### What the county view exposes

- **Crime (Kaplan UCR aggregated to county-year):** violent crime rate,
  property crime rate, murder rate, robbery rate, rape rate, aggravated
  assault rate, burglary rate, larceny rate.
- **Demographics (ACS 5-year):** share non-Hispanic white / Black /
  Hispanic, share male, share age 15–24 and 25–44, share with bachelor's
  degree or higher (25+).
- **Economy:** SAIPE median household income (real 2024 USD), SAIPE all-ages
  poverty rate, BLS LAUS unemployment rate (via USDA ERS, 2009–2023; 2024
  null until release), BEA per-capita personal income (real 2024 USD).
- **State firearm mortality joined down (Phase 2a):** state firearm suicide
  rate, state firearm homicide rate, state FS/S ownership proxy. Same value
  for every county in a given state-year. Documented as such in the legend
  caption and the variable's definition.
- **Regulation:** state firearm law count joined down to county.
- **Population:** county resident population (Census PEP).

---

## How to rebuild everything

```sh
# ===== State panels =====

# 1. Rebuild the four original balanced state-year panels from raw inputs (slow).
python scripts/build_firearms_panel.py

# 2. Audit them (writes data/processed/panel_audit_*.csv and panel_audit_report.md).
python scripts/audit_panels.py

# 3. Add the suicide / RAND ownership / granular crime layers
#    -> data/processed/{panel}_augmented.csv.
python scripts/augment_panels.py

# 4. Build the state-mode website data files
#    -> docs/data/{panel,metadata,manifest}.json.
python scripts/build_website_data.py

# ===== County panel =====

# 5. Phase 1+2a: build the county-year panel from PEP, SAIPE, ACS 5y, BLS LAUS
#    (via USDA ERS), BEA, plus state laws and state firearm mortality joined
#    down. ACS results are cached under data/county/acs5_cache/.
python scripts/build_county_panel.py

# 6. Phase 3: county-level UCR crime from Kaplan's openICPSR project 100707.
#    Manually download project 100707 V22 from openicpsr.org (free account)
#    and unzip into data/county/kaplan_offenses/. Then:
python scripts/build_county_crime.py
python scripts/build_county_panel.py    # re-run to merge crime into the panel

# 7. Phase 4: build the county-mode website data files
#    -> docs/data/county/{year}.json (16 files), docs/data/county_meta.json,
#       docs/data/county_manifest.json.
python scripts/build_website_county_data.py

# ===== Preview =====
python -m http.server 8765 -d docs
# then open http://localhost:8765/
```

### Phase 2b — county-detailed firearm mortality (blocked, see Section 2.10)

We tried both promising public paths and found that **CDC has explicitly
removed county/state grouping from public mortality data**:

- Public-use NCHS Multiple Cause of Death files (CDC FTP) have NO
  geographic identifiers since 2005, by design.
- The CDC WONDER API (`/controller/datarequest/D77`) accepts POSTs but the
  documented service "cannot limit or group results by any location field".

The only public path with county detail is the WONDER **web interface**,
which is suitable for occasional manual queries on specific counties of
interest but not for a full programmatic build. The only programmatic
path with county detail is the **NCHS restricted-use files**, which
require an IRB-approved Data Use Agreement (weeks to months to obtain).

Until restricted-use access is in hand, the county panel uses the
state-level firearm mortality joined down to every county
(`state_firearm_suicide_rate`, `state_firearm_homicide_rate`,
`state_ownership_fss`) as documented in Section 2.9.

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
| 2026-04-30 | Phase 3 attempt 1 | Tried the FBI Crime Data API at api.usa.gov/crime/fbi/sapi/. The api.data.gov gateway accepts our key, but every documented FBI endpoint returns 404 from the FBI side. Documentation host (`crime-data-explorer.fr.cloud.gov`) does not resolve. The API has been decommissioned. |
| 2026-04-30 | Phase 3 final | Switched to Jacob Kaplan's openICPSR project 100707 V22 ("Offenses Known and Clearances by Arrest, 1960-2024"). User registered for a free openICPSR account and downloaded the 2 GB compressed bundle. We extracted the combined yearly CSV (908 MB), aggregated agency-level offenses to county-year, applied the same FIPS bridge as the rest of the county panel, and merged in. 21 new `county_*` crime columns at 99.81% coverage. |
| 2026-04-30 | Phase 4 | Added county-mode to the public website. New scripts/build_website_county_data.py emits 16 per-year JSON files (~2 MB each) plus county_meta and county_manifest. Frontend (docs/js/app.js) refactored around a `mode` abstraction so state and county share one render pipeline. Year and selected variable carry across mode switches when compatible. About page now lists 40 state vars + 23 county vars in separate sections. |
| 2026-04-30 | County names | Emit docs/data/county_names.json (107 KB, 3,133 entries) so the website hover sidebar and tooltip show "Los Angeles County, California" instead of the bare FIPS "06037". Renamed counties land on canonical modern names (Kusilvak, not Wade Hampton; Oglala Lakota, not Shannon). |
| 2026-04-30 | Phase 2b investigation | Worked through every public path for county-level firearm mortality. NCHS public-use files have had ALL geographic identifiers stripped since 2005 (CDC policy). The CDC WONDER API does not allow location grouping for mortality (per CDC's own API docs). Only NCHS restricted-use files (IRB-approved DUA, weeks/months to obtain) have county detail without suppression. Section 2.10 now records this with citations; the state firearm mortality joined down to every county (Phase 2a) is the operational solution. |
| 2026-04-30 | Spatial RDD geometry | Built the geometry layer for the planned spatial regression-discontinuity work on state borders: `data/processed/county_border_distances.csv` (3,221 rows). For every county we attach its 2020 population centroid (Census CenPop2020) and the great-circle distance to the closest county in a different state. Section 2.12 documents source, method, and per-county spot checks. 907 counties sit within 50 km of an other-state centroid; 1,962 within 100 km; 2,822 within 200 km. This file is the foundation for per-policy border samples and sharp-RDD specifications, which are a separate follow-up pass. |

This file is updated at the end of every meaningful change. The most
recent commits in <https://github.com/jedediahpidareese-coder/firearms-regulation-map/commits/main>
will always reflect the current state.
