# U.S. Firearms Regulation, Crime, and Controls: Data Inventory

Prepared on 2026-04-22 for research design, econometrics, and visualization work.

## Bottom line

There is no single public turnkey panel that cleanly covers firearm laws, violent/property crime, demographics, and economic controls all the way through calendar year 2026.

As of 2026-04-22, the strongest practical build is:

1. Law panel: Tufts State Firearm Laws database for 1976-2024.
2. Current-law extension: Everytown Gun Law Navigator / 2026 rankings and ATF 2025 state-law compendium for 2025-2026 status checks.
3. Crime outcomes: FBI UCR / Crime Data Explorer for long-run violent and property crime; NACJD/ICPSR for older county or agency panels.
4. Controls: Census ACS + SAIPE + Census/SEER population files + BLS LAUS + BEA regional accounts.
5. Optional gun-market and exposure measures: NICS, RAND household firearm ownership estimates, ATF commerce/trafficking data.

The most important timing caveat is that complete official annual violent/property crime totals do not yet extend through 2026. The latest full FBI annual release is 2024, released on 2025-08-05. Some monthly or partial 2025/2026 indicators exist, but not a complete official 2026 annual crime panel.

## What the main law datasets cover

For the policy measures you named, the major modern law panels are generally sufficient:

- `RTC / shall-issue / public carry / concealed carry`: covered in Tufts, Everytown, and RAND.
- `Constitutional carry / permitless carry`: usually a specific subtype of public-carry or concealed-carry regulation; Everytown is strongest for current status, while Tufts and RAND are better for historical panel work.
- `Red flag laws / ERPOs`: covered in Everytown current data and in newer RAND / Tufts era law codings.
- `Magazine bans / large-capacity magazine bans`: covered in Tufts and RAND.
- `Assault weapon bans`: covered in Tufts and RAND.
- `Universal background checks / private-sale checks / permit-to-purchase / waiting periods / child access prevention / dealer licensing / domestic violence prohibitors / stand-your-ground`: covered across the main law panels below.

Important modeling note: the literature often treats `shall-issue RTC`, `may-issue`, and `permitless carry` as distinct policy states. Do not collapse them unless the design is intentionally coarse.

## Recommended panel builds

### 1. State-year panel for causal inference

Best for staggered adoption designs, event studies, synthetic controls, and DiD.

- Laws: Tufts 1976-2024.
- Violent/property crime: FBI UCR/CDE state annual series 1960-2024.
- Demographics: ACS, SAIPE, Census/SEER populations.
- Economics: LAUS unemployment, BEA income/GDP.
- Optional gun exposure controls: RAND household firearm ownership 1980-2016, NICS 1998-2026.

Suggested usable window:

- `1976-2024` for state-year law + crime.
- `1980-2016` if you need modeled household gun ownership from RAND.
- `1998-2024` if you want to add NICS.

### 2. County-year panel

Best for finer spatial heterogeneity, border-county designs, spillovers, and mapping.

- Crime: NACJD/ICPSR UCR county or agency archives plus newer FBI/CDE outputs where available.
- Laws: merge state law panel onto counties.
- Demographics/economics: ACS, SAIPE, LAUS, BEA county income, SEER/NCHS/Census population denominators.
- Geography: Census TIGER/Line county shapefiles.

Suggested usable window:

- `1990s-2024` is usually the safest modern county-year range if you want decent controls and mapping.
- Earlier county crime work is possible through ICPSR/NACJD, but data cleaning cost rises quickly.

### 3. State-month panel

Best for purchase shocks, short-run law effects, and interactive dashboards.

- NICS by state and type: 1998-2026.
- Monthly unemployment: LAUS.
- Monthly or rolling crime: only if you are comfortable with preliminary FBI monthly data and comparability caveats.
- Policy adoption dates: append exact effective dates from law sources.

Suggested usable window:

- `1998-2026` for background-check and law-adoption dashboards.

## Source inventory

### A. Firearm law panels and trackers

| Source | Coverage | Geography | What it gives you | Why it matters | Link |
|---|---|---|---|---|---|
| Tufts State Firearm Laws | 1976-2024 | 50 states | Downloadable panel of 72 firearm law provisions in 11 categories | Best broad historical state-law panel I found; explicitly includes concealed carry, assault weapon / large-capacity magazine laws, child access prevention, domestic violence, and stand-your-ground | [Tufts CTSI](https://www.tuftsctsi.org/state-firearm-laws/) |
| Tufts historical report | 1976-2024 | 50 states | Narrative summary, methodology, and state pages | Useful for law definitions and scope notes, including Bruen-era coding caveats | [The Changing Landscape of U.S. Gun Policy](https://www.tuftsctsi.org/wp-content/uploads/2025/05/The-Changing-Landscape-of-U.S.-Gun-Policy-STATE-FIREARM-LAWS-1976%E2%80%932024.pdf) |
| Everytown Gun Law Navigator | 1991-present | 50 states | State-by-year law comparisons | Best current public-facing tracker for seeing how specific law measures changed over time; strong for current law status | [Gun Law Navigator](https://maps.everytownresearch.org/navigator/) |
| Everytown 2026 Gun Law Rankings | 2026 cross-section | 50 states | 2026 ranking plus 50 tracked gun-safety laws | Best verified current 2026 cross-section in this inventory | [Everytown 2026 rankings](https://everytownsupportfund.org/press/everytown-releases-2026-state-gun-law-rankings-providing-roadmap-for-saving-262000-lives-from-gun-violence-over-the-next-decade/) |
| RAND State Firearm Law Database | 1979-2024 (methods doc up to 2024-01-01) | 50 states | Longitudinal law database with detailed law classes and citations | Strong for transparent legal citations and harmonized law categories; useful cross-check against Tufts/Everytown | [RAND methods and documentation](https://www.rand.org/content/dam/rand/pubs/tools/TLA200/TLA243-2-v3/RAND_TLA243-2-v3.pdf) |
| ICPSR / DOJ State Firearm Law Database | 1991-2019 | 50 states | Downloadable panel of 134 firearm law provisions | Best older high-dimensional law panel for 1991-2019 if you want many narrow policy indicators | [Data.gov / ICPSR 37363](https://catalog.data.gov/dataset/state-firearm-law-database-state-firearm-laws-1991-2019-e2e9d) |
| ATF State Laws and Published Ordinances | annual editions; archive reaches back to the 1970s | states and some local ordinances | Annual statutory compendium | Best official legal backfill and current compliance cross-check; 36th edition was published/revised 2026-01-15 | [ATF 36th edition landing page](https://www.atf.gov/node/65211) |
| Alcohol-related firearm law data | 2010-2023 | 50 states | Specialized panel on alcohol-related firearm statutes | Niche but useful if you want mechanism-specific heterogeneity or interaction terms | [OpenICPSR project](https://www.openicpsr.org/openicpsr/project/239498/view) |

### B. Crime outcomes and criminal justice measures

| Source | Coverage | Geography | What it gives you | Why it matters | Link |
|---|---|---|---|---|---|
| FBI UCR / Crime Data Explorer | annual state/national estimates back to 1960; latest full annual release 2024 | national, state, county, city, agency | Violent crime, property crime, and component offenses | Core official source for long-run violent/property crime outcomes | [FBI UCR program](https://www.fbi.gov/services/cjis/ucr/) |
| FBI 2024 release FAQ | 2024 annual release | national / state | Release timing and download guidance | Confirms the latest full annual FBI release date and where to get tables | [2024 FAQ PDF](https://cde.ucr.cjis.gov/LATEST/resources/reports/Reported%20Crimes%20in%20the%20Nation%202024%20FAQs.pdf) |
| FBI legacy UCR tool archive note | 1960-2009 | national / state | Confirmation of back-to-1960 state and national estimates | Useful when documenting historical coverage in methods sections | [FBI archive note](https://archives.fbi.gov/archives/news/stories/2010/november/ucrtool_112910/ucrtool_112910) |
| FBI monthly crime release | preliminary monthly / rolling | national and state-facing public release | Preliminary monthly crime and law-enforcement indicators | Best source for more recent but not final trends; use carefully | [Monthly release note](https://www.fbi.gov/news/press-releases/fbi-releases-monthly-crime-and-law-enforcement-data) |
| NACJD / ICPSR criminal justice archive | series vary by file; historical UCR files reach back to the 1960s | county, agency, state, national | Archived UCR, arrest, corrections, and other justice datasets | Best route for deep historical county/agency panels and reproducible archival work | [National Archive of Criminal Justice Data](https://bjs.ojp.gov/data/national-archive-criminal-justice-data) |
| NCVS API | survey series is long-run; API supports downloadable victimization tables | national, region, some state outputs | Violent and property victimization, including nonreported crime | Best complement to police-reported crime when you care about underreporting | [NCVS API](https://bjs.ojp.gov/national-crime-victimization-survey-ncvs-api) |
| BJS data analysis tools | modern interactive tools | national and state | LEARCAT, corrections, and other justice tools | Good supplement for incarceration and recent incident-based justice data | [BJS data tools](https://bjs.ojp.gov/data/data-analysis-tools) |
| BJS National Prisoner Statistics / CSAT | annual; tool spans 1978-forward | state and national | Prison population, admissions, releases, imprisonment rates | Typical criminal-justice control in guns/crime work | [NPS collection page](https://bjs.ojp.gov/data-collection/national-prisoner-statistics-nps) |

### C. Firearm prevalence, commerce, and market proxies

| Source | Coverage | Geography | What it gives you | Why it matters | Link |
|---|---|---|---|---|---|
| RAND household firearm ownership estimates | 1980-2016 | 50 states | Annual state-level estimated household firearm ownership | Most widely used modeled ownership series in modern policy research | [RAND TL-354](https://www.rand.org/pubs/tools/TL354.html) |
| Firearm-suicide-share ownership proxy dataset | 1949-2020 | 50 states | Long historical proxy for household gun ownership | Best very long-run ownership proxy when you need pre-1980 coverage | [PubMed entry](https://pubmed.ncbi.nlm.nih.gov/37743886/) |
| FBI NICS Year by State/Type | 1998-11 to 2026-03 | states / territories | Annualized background checks by type | Essential high-frequency proxy for legal retail market activity; not equal to gun sales | [NICS year-by-state/type](https://www.fbi.gov/file-repository/cjis/nics_firearm_checks_-_year_by_state_type.pdf/view) |
| FBI NICS main page | 1998-present | states / territories | Current and archived NICS downloads | Main official hub for monthly and yearly files | [FBI NICS](https://www.fbi.gov/services/cjis/nics/) |
| Data Liberation Project NICS extraction | 1998-present | states / territories | CSV-friendly extraction of official NICS PDFs | Best convenience dataset for websites and dashboards | [Data Liberation Project](https://www.data-liberation-project.org/datasets/nics-firearm-background-checks/) |
| ATF Firearms Commerce report | comparative data as far back as 1975; current report page offers 2024 | national and state | Manufacturing, imports, FFLs, commerce context | Useful for market-side controls and industry context | [ATF data and statistics](https://www.atf.gov/resource-center/data-statistics) |
| ATF AFMER | annual; one-year publication lag; latest confirmed page here is 2023 final report | manufacturer / national totals | Firearms manufacturing and export counts | Best direct manufacturing source | [2023 AFMER](https://www.atf.gov/explosives/2023-annual-firearms-manufacturers-and-export-report-afmer) |
| ATF NFCTA volumes | select series 2000-2024 | national, state, trafficking / crime-gun contexts | Crime-gun, trafficking, commerce, and industry datasets | Strong supplement if your project touches diversion or trafficking channels | [NFCTA crime guns volume](https://www.atf.gov/firearms/national-firearms-commerce-and-trafficking-assessment-nfcta-crime-guns-volume-one) |

### D. Firearm injury and mortality outcomes

| Source | Coverage | Geography | What it gives you | Why it matters | Link |
|---|---|---|---|---|---|
| CDC WONDER Multiple Cause of Death | county-level mortality files; commonly used for modern post-1999 firearm analyses | county, state, national | Firearm homicide, suicide, accident, legal intervention, and broader mortality categories | Standard mortality source in gun-policy papers | [CDC WONDER MCD](https://wonder.cdc.gov/mcd.html) |
| CDC WISQARS Injury Reports | 2001-present | national and state for fatal injuries | Fatal and nonfatal injury reporting interface | Easy way to pull firearm injury outcome tables quickly | [WISQARS](https://wisqars.cdc.gov/) |
| WISQARS Injury Reports help | 2001-present | national and state | Documentation on coverage and filters | Useful citation for methods sections | [Injury Reports help](https://wisqars.cdc.gov/help/injury-reports) |
| NVDRS in WISQARS | 2003-present | participating areas; now all states funded | Violent death circumstances and mechanism details | Best circumstances data for firearm homicides/suicides | [About NVDRS data](https://wisqars.cdc.gov/about/nvdrs-data) |

### E. Demographic, economic, policing, and structural controls

| Source | Coverage | Geography | What it gives you | Why it matters | Link |
|---|---|---|---|---|---|
| ACS API | annual modern ACS era | national, state, county, tract, many other geographies | Population, race/ethnicity, age structure, education, income, poverty, housing, insurance, migration, family structure, etc. | Main all-purpose control source for modern work and dashboards | [ACS data via API](https://www.census.gov/programs-surveys/acs/data/data-via-api.html) |
| SAIPE | annual; latest verified release is 2024 | state and county | Single-year model-based income and poverty estimates | Often better than raw ACS for county poverty / income controls | [SAIPE program](https://www.census.gov/programs-surveys/saipe.html) |
| Census annual population estimates | current vintage releases through 2025 as of 2026-03 | state and county | Annual resident population estimates and components of change | Best denominator for rates when you need the newest population counts | [2025 county population file layout](https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2025/CO-EST2025-ALLDATA.pdf) |
| SEER population data | 1969-2024 | state and county; age/sex/race detail | Long-run annual population denominators | Best for long panels that need age/race population detail | [SEER population download](https://seer.cancer.gov/popdata/download.html) |
| BLS Local Area Unemployment Statistics | monthly and annual | state, county, metro | Labor force, employment, unemployment, unemployment rate | Standard labor-market control | [LAUS quick facts](https://www.bls.gov/opub/hom/lau/pdf/lau.pdf) |
| BEA regional accounts | state data through 2025; county personal income/GDP through 2024 | state and county | Personal income, GDP, earnings, employment context | Standard macroeconomic control stack for panel work | [BEA regional accounts](https://www.bea.gov/data/economic-accounts/regional) |
| BJS LEMAS | periodic since 1987 | agency-level | Sworn officers, civilians, policies, equipment, administration | Best police-capacity and policing-style supplement | [LEMAS](https://bjs.ojp.gov/data-collection/law-enforcement-management-and-administrative-statistics-lemas) |
| Census ASPEP | annual | state and local government | Public employment and payroll, including police protection | Good broad public-safety staffing control | [ASPEP](https://www.census.gov/aspep) |

## Best starting bundle by use case

### If you want the single best state-year econometrics stack

Use:

- Tufts law panel.
- FBI UCR/CDE violent and property crime.
- ACS + SAIPE + SEER/Census population denominators.
- BLS LAUS unemployment.
- BEA income and GDP.
- Optional: RAND household firearm ownership and FBI NICS.

This gives you a very usable `1976-2024` state-year framework, with some supplementary market measures continuing past 2024.

### If you want a county map / website stack

Use:

- County crime from NACJD historical UCR files plus newer FBI/CDE outputs where available.
- State law panel joined to counties.
- ACS 5-year estimates for stable county/tract traits.
- SAIPE for county poverty/income.
- LAUS county unemployment.
- BEA county personal income.
- Census / SEER population denominators.
- Census TIGER/Line shapefiles for mapping.

### If you want a current-policy dashboard through 2026

Use:

- Everytown 2026 rankings and Gun Law Navigator for current law status.
- FBI NICS through 2026-03.
- Latest available Census population estimates through 2025.
- Latest available BEA state data through 2025.
- Treat 2025/2026 crime as preliminary or incomplete unless you are explicitly using FBI monthly releases.

## Caveats that matter for causal work

1. `2026 is not a full annual data year yet.`
   Most official annual crime and demographic sources do not yet have complete 2026 observations.

2. `The 2021 UCR-to-NIBRS transition creates comparability problems.`
   National/state estimates are still usable, but local coverage and agency participation need checking.

3. `NICS is not gun sales.`
   The FBI explicitly warns that background checks do not map one-to-one to firearm purchases.

4. `Law coding differs across datasets.`
   Some sources code enactment, some effective date, and some differ on temporary injunctions or narrow exemptions.

5. `RTC / shall-issue / permitless carry should usually be separated.`
   Many papers get into trouble by combining permissive carry regimes that are substantively different.

6. `Bruen-era litigation complicates current-law coding.`
   Tufts explicitly notes this and does not generally recode temporary injunctions, with specific exceptions.

## What I would build first

If you want the fastest path to a clean research dataset, I would start with:

1. Tufts `1976-2024` laws.
2. FBI `1960-2024` state crime series.
3. ACS + SAIPE + LAUS + BEA + SEER population denominators.
4. RAND household firearm ownership for `1980-2016`.
5. NICS for `1998-2026`.

That stack is strong enough for:

- event studies
- DiD and staggered adoption work
- border-state or border-county designs
- state dashboards
- county choropleths
- long-run trend graphics

## Source notes used for this memo

- Tufts says its downloadable state firearm law database covers `72` provisions across `1976-2024`.
- Everytown says it surveyed state laws for every year back to `1991`, and its verified 2026 rankings were updated on `2026-01-15`.
- RAND says its household firearm ownership database covers `1980-2016`, and its state firearm law documentation is current through `2024-01-01`.
- FBI says the latest full annual "Reported Crimes in the Nation" release is `2024`, released on `2025-08-05`.
- FBI NICS year-by-state/type file currently runs through `2026-03-31`.
- SAIPE's latest verified county/state release in this search was `2024`, published in `2026-01`.
- Census published Vintage `2025` county population estimates on `2026-03-26`.
