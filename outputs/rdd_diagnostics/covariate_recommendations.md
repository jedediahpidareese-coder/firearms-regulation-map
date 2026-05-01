# Covariate Recommendations for State-Level Firearm-Policy Causal Inference

**Project:** Firearms Regulation, state-level DiD/SCM/RDD estimation
**Date:** 2026-05-01
**Author:** Literature scan (read-only review of project panel; no code or data modified)
**Current covariates in production specs:** `ln_population`, `unemployment_rate`, `ln_pcpi_real_2024` (only)
**Bottom line:** the inherited specification is materially thinner than the modal published spec in this literature. Modern peer-reviewed work in JELS, AJPH, JOLE, JHR, PNAS, and Preventive Medicine routinely conditions on 8–17 controls. The largest single omission is **per-capita ethanol consumption** (NIAAA Surveillance Reports), which is in essentially every published specification that touches violence or suicide. Demographic shares, an incarceration measure, and a police staffing measure are also load-bearing in the modal spec; we already have all three in-project but they are not being passed to the estimator. This document recommends a tiered, outcome-specific set of replacements and maps each recommended variable to its data source.

This scan covers ~20 papers spanning the methodological spectrum (Lott-Mustard pro-RTC through Donohue-Aneja-Weber, Webster/Crifasi/Vernick, Cheng-Hoekstra, McClellan-Tekin, Anestis, Klarevas-Conner-Hemenway, Luca-Malhotra-Poliquin, Kivisto, Knight, Kalesan-Galea, Miller-Hemenway), and synthesizes covariate philosophies from RAND's *Science of Gun Policy* (4th ed., 2024) which is the canonical methodology review. Where exact lists were not extractable from PDFs (Stanford Law Review, NBER WPs that returned binary), I cross-validated against published abstracts, RAND syntheses, comment exchanges (Econ Journal Watch), and replication metadata. Citations include URLs.

---

## Section 1 — Covariate specifications by paper

The table below enumerates each paper's covariate set, with notable inclusions, notable omissions, and the overall "covariate philosophy" one-liner. Entries are intentionally compact; full URLs at end of section.

### 1.1 Right-to-Carry / Concealed Carry

| Cite | Outcome | Treatment | Estimator | Covariates used | Notable inclusions | Notable exclusions | Philosophy |
|---|---|---|---|---|---|---|---|
| Lott & Mustard (1997, *J. Legal Studies* 26:1) | County violent crime, murder, rape, assault, property crime | RTC / shall-issue | County FE panel + state-year, dummy treatment, also arrest-rate covariate | Arrest rate (lagged), county population density, real per-capita personal income, real per-capita unemployment insurance payments, real per-capita income-maintenance payments, real per-capita retirement payments, 36 age × race × gender population shares (6 age bands × 2 races × 3 genders) | Massive demographic detail; arrest rate as deterrence proxy | **No incarceration; no police force size; no alcohol; no urbanicity beyond density** | "Throw the kitchen sink of demographics + an arrest deterrent; let county FE absorb everything else." Critiqued for parameter:obs ratio of 1:8–1:14 → overfit risk. |
| Ayres & Donohue (2003, *Stanford LR* 55:1193) | Same UCR-7 categories | RTC | County and state FE + state-specific time trends, expanded covariates | Lott-Mustard demographics + arrest rate + lagged incarceration + lagged police staffing + state-specific linear trends; some specs add MSA % and county per-capita income measures | First wave to add **incarceration and police rates explicitly** | No alcohol, no drug overdose | "Lott controls aren't enough — add CJ-system and let state-specific trends absorb the parallel-trends violation." |
| Aneja, Donohue & Zhang (2014, NBER WP w18294) | Violent crime | RTC | Panel with multiple covariate sets; LASSO | "DAW set" (preferred): real per-capita personal income, unemployment rate, poverty rate, percentage of population in MSAs, six demographic age-sex-race shares, lagged incarceration rate, lagged police staffing rate; "LM set": Lott-Mustard original; "BC set" (Brennan Center): a smaller subset; "MM set" (Moody-Marvell) | Formalized comparison of competing covariate sets | Even DAW excludes alcohol | "Show robustness across LM/BC/MM/DAW covariate sets; preferred adds CJ controls Lott omitted." |
| Donohue, Aneja & Weber (2019, *J. Empirical Legal Studies* 16:198) | UCR violent crime, murder | RTC | Panel-FE + Synthetic Control (SCM) | DAW panel set (above) for panel-FE specs. SCM predictors: same DAW set + pre-treatment outcome lags | Demonstrates **DAW > LM** under modern data; SCM matches on outcome levels | No alcohol; no drug overdose; no religiosity | "Specification multiverse: report all four covariate sets; SCM predicts pre-period outcomes well using DAW." |
| Donohue, Cai, Bondy & Cook (2023, NBER WP 30190 / *AEJ:Applied* forthcoming) | City-level violent crime, gun theft, clearance rates | RTC, mechanism analysis | Panel-FE on 217 US cities, FE for city + year | City-level covariates: real per-capita income, unemployment rate, poverty rate, share black, share Hispanic, share male, age-band shares, lagged incarceration rate, lagged police staffing per capita, lagged clearance rate | First to bring city panel; mechanism focus | Same gaps as DAW | "Same DAW philosophy ported to cities; mechanism evidence (gun theft, clearance) does the heavy lifting." |
| Plassmann & Whitley (2003, *Stanford LR* 55:1313) | Violent crime | RTC (rebuttal to Ayres-Donohue) | County panel | Lott-Mustard original set plus minor adjustments | Pro-RTC reply | Same omissions as LM | "Defend the LM set; modifications to coding overturn AD result (later corrected by AD critics)." |

### 1.2 Permit-to-Purchase / Background Checks

| Cite | Outcome | Treatment | Estimator | Covariates used | Notable inclusions | Notable exclusions | Philosophy |
|---|---|---|---|---|---|---|---|
| Webster, Crifasi & Vernick (2014, *J. Urban Health* 91:293) | State firearm/non-firearm homicide | MO PTP repeal (2007) | State-year panel-FE GLS, cluster-robust SE | Unemployment rate, poverty rate, burglary rate (per 100k), incarceration rate (per 100k), law enforcement officers per capita, indicator for SYG, indicator for RTC, indicator for "Saturday night special" handgun ban, juvenile violent-felony bar | Burglary as a "demand for guns" proxy; PTP-relevant policy controls | **No alcohol; no drug overdose; no demographics beyond poverty** | "Add CJ + concurrent-policy controls; demographic shifts assumed slow and absorbed by state FE." |
| Crifasi, Meyers, Vernick & Webster (2015, *Preventive Medicine* 79:43) | Firearm/non-firearm suicide | CT PTP (1995) and MO repeal | Synthetic Control | SCM predictors include: poverty, unemployment, percent male, percent Black, percent metropolitan, age shares, ethanol consumption per capita, religious adherence, education, and overdose rate | First explicit use of **NIAAA ethanol** and **religious adherence** in this literature for suicide outcomes | — | "Suicide-specific covariate stack: alcohol, religiosity, overdose are first-class predictors." |
| Rudolph, Stuart, Vernick & Webster (2015, *AJPH* 105:e49) | Firearm/non-firearm homicide | CT PTP (1995) | Synthetic Control | Population size, log population density, log share Black, log share Hispanic, share age 0–18, share age 15–24, poverty rate (16+), Gini coefficient, per-capita income, jobs per adult, law-enforcement officers per 100k, log law-enforcement expenditures, robbery rate per 100k, percent in MSAs | Inequality (Gini), jobs per adult, robbery (proxy for "crime regime") | **No alcohol; no incarceration; no drug overdose** in homicide specs | "Homicide SCM: rich economic-inequality + policing predictors; suicide-specific factors moved to suicide spec." |
| McCourt, Crifasi, Stuart, et al. (2020, *AJPH* 110:1546) | Firearm/non-firearm homicide; firearm/non-firearm suicide | PTP/UBC adoption or repeal in CT, MD, MO, PA | Synthetic Control, separate models per outcome × state | **Homicide model:** population size, law-enforcement expenditures per capita, LE officers per capita, % Black, % Latino, Gini, % age 15–24, % age 0–18, % metropolitan, robbery rate, population density, poverty rate, jobs per capita, average individual income per capita, unemployment rate, **incarceration rate**. **Suicide model:** unemployment, poverty, % male, % married, % Black, % veteran, % metropolitan, **ethanol consumption per capita**, **religious adherence**, education, **overdose rate** | Cleanest published statement of "homicide stack" vs. "suicide stack" | Even this paper splits cleanly: alcohol/religion/overdose are suicide predictors; CJ vars are homicide predictors | "Outcome-tailored stacks: homicide ↔ CJ + economic-inequality; suicide ↔ alcohol + religion + overdose + demographics." |

### 1.3 Stand-Your-Ground / Castle Doctrine

| Cite | Outcome | Treatment | Estimator | Covariates used | Notable inclusions | Notable exclusions | Philosophy |
|---|---|---|---|---|---|---|---|
| Cheng & Hoekstra (2013, *J. Human Resources* 48:821) | Homicide; UCR-violent crime | Castle doctrine / SYG | Panel-FE + state-specific linear trends + region-by-year FE | Time-varying state controls: police rate, incarceration rate, real per-capita welfare/public-assistance spending, median income, poverty rate, unemployment rate, demographic shares (race, age, gender) | First to add **welfare/public-assistance spending** | No alcohol per se; no drug overdose | "FE + state trends + economic + CJ; rule out parallel-trend violations from changes in state-level transfers." |
| McClellan & Tekin (2017, *J. Human Resources* 52:621) | Monthly homicide; firearm injuries | SYG laws | DiD with state + year FE; region × year FE; state-specific trends | Time-varying: police staffing rate, incarceration rate, demographic shares, unemployment, poverty, real income, alcohol consumption per capita | Includes **alcohol** explicitly | No drug overdose; no urbanicity | "Cheng-Hoekstra controls + alcohol; show SYG coefficient is robust across many specs." |

### 1.4 Suicide-focused / Age-21 / Lethal-Means Restriction

| Cite | Outcome | Treatment | Estimator | Covariates used | Notable inclusions | Notable exclusions | Philosophy |
|---|---|---|---|---|---|---|---|
| Anestis & Anestis (2015, *AJPH* 105:2059) | State firearm/total suicide rates | 4 handgun laws (waiting period, UBC, gun lock, open carry) | Cross-sectional ANCOVA | Poverty rate, population density (only) | — | **Almost everything** (acknowledged) | "Limited cross-section; admits religiosity, depression, gun ownership unmeasurable in 2010 wave." |
| Anestis et al. (2017, *AJPH* 107:579) | State suicide-rate change | Same 4 laws | Within-state change ANCOVA | Demographic data + suicidal ideation/depression rates from NSDUH; gun-ownership proxy from Kalesan | Adds **NSDUH ideation/depression** rates and a household gun-ownership proxy | Cross-sectional only on changes | "Change scores → control demographics + mental-health prevalence + ownership." |
| Crifasi et al. (2015, see above) | Firearm suicide | PTP | SCM | (See suicide stack: ethanol, religious adherence, overdose, demographics, % male, % married, % veteran) | Canonical "suicide" predictor stack | — | Outcome-tailored. |
| Kivisto & Phalen (2018, *Psychiatric Services* 69:855) | Firearm/non-firearm suicide | CT (1999, 2007) and IN (2006) ERPO/red-flag laws | SCM with annual state panel 1981–2015 | State suicide-risk covariates (mostly aligned with Crifasi-style suicide stack: demographics, alcohol consumption, poverty, unemployment, religious adherence) | Pioneers SCM for ERPO; uses suicide-stack predictors | — | "Suicide stack ported to ERPO setting; placebo on non-firearm suicide and on never-treated states." |
| Luca, Malhotra & Poliquin (2017, *PNAS* 114:12162) | State firearm homicide and suicide | Waiting periods | Panel-FE with state + year FE | Time-varying covariates: alcohol consumption per capita, poverty, income, urbanization, share Black, **seven age groups** | Granular age bands; explicit alcohol | No incarceration in headline spec; no police rate; no drug overdose | "Light CJ controls but rich demographic + alcohol; identify off the natural experiment." |

### 1.5 Mass Shootings / Magazine & Assault-Weapon Bans

| Cite | Outcome | Treatment | Estimator | Covariates used | Notable inclusions | Notable exclusions | Philosophy |
|---|---|---|---|---|---|---|---|
| Klarevas, Conner & Hemenway (2019, *AJPH* 109:1754) | High-fatality mass shootings (occurrence; deaths) | LCM bans | State-FE logit + negative binomial; clustered SE | 10 controls: total state population, population density, share age 19–24, share age 25–34, share Black, share with college degree, real per-capita median income, unemployment rate, per-capita prison population, household firearm prevalence (proxy from CDC/NVSS) | Includes **household firearm prevalence proxy** | No alcohol; no drug overdose; no police staffing | "Tight set; HH-firearm proxy is the load-bearing addition because LCMs proxy gun-market intensity." |
| Koper & Roth (2001, *J. Quantitative Criminology* 17:33) | Gun homicide; AW-traced incidents | 1994 Federal AWB | Pre/post panel | State-level demographics, unemployment, % MSA, alcohol consumption per capita, age shares | First gun-policy paper to use **NIAAA ethanol** explicitly | Limited CJ controls | "Federal-policy time series — alcohol enters as a national time-varying confounder." |

### 1.6 Trafficking and Cross-State Spillovers

| Cite | Outcome | Treatment | Estimator | Covariates used | Notable inclusions | Notable exclusions | Philosophy |
|---|---|---|---|---|---|---|---|
| Knight (2013, *AEJ:Economic Policy* 5:200) | Crime-gun trace counts (state-pair-year) | State gun-policy strictness | Gravity model with origin- and destination-state FE | Source- and destination-state controls: population, real income, distance, common border, demographic shares | Cross-state distance + origin/dest FE | Outcome is gun flows, not crime; controls minimal | "Spatial gravity model; state FE absorbs most confounders." |

### 1.7 Reviews / Meta-analytic Perspectives

| Cite | Scope | Methodological recommendation on covariates |
|---|---|---|
| Cook & Donohue (2017, *Science* 358:1259, "Saving lives by regulating guns") | Synthesis editorial | Endorses richer-control specifications over Lott-style sparse models; flags overfitting risk |
| Cook & Ludwig (2006 onward) and Cook & Goss (2014, *The Gun Debate*) | Book/policy synthesis | Argue economic + CJ + market controls are essential |
| RAND, *The Science of Gun Policy* (4th ed., Smart, Morral et al., 2024, RR-A243-9) | Systematic review of 207 studies | Explicitly flags "covariate selection" as one of seven methodological standards; recommends pre-registered, theory-driven covariate sets and robustness across specifications. |
| Miller, Azrael & Hemenway (2002, *Epidemiology* 13:517) | Suicide–firearm-prevalence association | Used HH firearm ownership + poverty + urbanization controls; canonical "minimum suicide spec" |
| Kalesan, Mobily, Keiser, Fagan & Galea (2016, *Lancet* 387:1847) | Cross-sectional firearm-mortality–laws association | Controls: gun ownership rate, non-firearm homicide rate, unemployment rate (sparse, criticized for cross-sectional design) |

**URLs (papers cited):**

- Lott & Mustard 1997 — https://chicagounbound.uchicago.edu/cgi/viewcontent.cgi?article=1150&context=law_and_economics
- Ayres & Donohue 2003 — https://law.stanford.edu/publications/shooting-down-the-more-guns-less-crime-hypothesis-3/ ; https://ianayres.yale.edu/sites/default/files/files/Ayres_Donohue_article.pdf
- Aneja, Donohue, Zhang 2014 — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2443681
- Donohue, Aneja, Weber 2019 — https://onlinelibrary.wiley.com/doi/abs/10.1111/jels.12219 ; https://www.nber.org/papers/w23510
- Donohue, Cai, Bondy, Cook 2023 — https://www.nber.org/papers/w30190
- Plassmann & Whitley 2003 — Wikipedia summary at https://en.wikipedia.org/wiki/More_Guns,_Less_Crime
- Webster, Crifasi, Vernick 2014 — https://pmc.ncbi.nlm.nih.gov/articles/PMC3978146/
- Crifasi, Meyers, Vernick, Webster 2015 — https://pubmed.ncbi.nlm.nih.gov/26212633/
- Rudolph, Stuart, Vernick, Webster 2015 — https://pmc.ncbi.nlm.nih.gov/articles/PMC4504296/
- McCourt, Crifasi, Stuart et al. 2020 — https://pmc.ncbi.nlm.nih.gov/articles/PMC7483089/
- Cheng & Hoekstra 2013 — https://jhr.uwpress.org/content/48/3/821
- McClellan & Tekin 2017 — https://jhr.uwpress.org/content/52/3/621
- Anestis & Anestis 2015 — https://pmc.ncbi.nlm.nih.gov/articles/PMC4566551/
- Anestis et al. 2017 — https://ajph.aphapublications.org/doi/full/10.2105/AJPH.2016.303650
- Kivisto & Phalen 2018 — https://psychiatryonline.org/doi/10.1176/appi.ps.201700250
- Luca, Malhotra & Poliquin 2017 — https://www.pnas.org/doi/10.1073/pnas.1619896114
- Klarevas, Conner & Hemenway 2019 — https://pmc.ncbi.nlm.nih.gov/articles/PMC6836798/
- Koper & Roth 2001 — https://link.springer.com/article/10.1023/A:1007522431219
- Knight 2013 — https://www.aeaweb.org/articles?id=10.1257/pol.5.4.200
- Miller, Azrael & Hemenway 2002 — https://pubmed.ncbi.nlm.nih.gov/12192220/
- Kalesan et al. 2016 — https://pubmed.ncbi.nlm.nih.gov/26972843/
- Cook & Donohue 2017 (Science) — https://www.science.org/doi/10.1126/science.aar3067
- RAND 4th ed. — https://www.rand.org/pubs/research_reports/RRA243-9.html ; https://pmc.ncbi.nlm.nih.gov/articles/PMC11630101/

---

## Section 2 — Three-tier covariate recommendation by outcome category

For each outcome family, three specifications are recommended: **Minimal** (the smallest defensible set a Lott-school reviewer would not reject), **Headline** (modal modern set, what a Donohue/Webster reviewer would expect), and **Expanded** (kitchen-sink for robustness). All variable names below use the panel column conventions already in use (`panel_core_augmented.csv`, `panel_demographic_augmented.csv`, `state_cj_controls_1979_2024.csv`).

### 2.1 Lethal violence (homicide; firearm homicide; UCR violent crime; county violent/murder rates)

#### Minimal (Lott-Mustard-acceptable defensible floor)
| Variable | Rationale | Source / paper |
|---|---|---|
| `ln_population` | Standard scale control; in every spec | Lott-Mustard, DAW |
| `ln_pcpi_real_2024` | Real income; in every modern spec | Lott-Mustard, DAW |
| `unemployment_rate` | Business-cycle control; required by Donohue 2019 | DAW |
| `poverty_rate` | Standard economic-distress control | DAW, Webster 2014 |
| `share_age_15_24` + `share_age_25_44` | Crime-prone age structure (the bare minimum demographic detail) | Lott-Mustard's 36-cell version simplified |
| `share_male` | Sex composition | Lott-Mustard |
| `share_black_nh` + `share_hispanic` | Race composition (matters for crime rates and sometimes for treatment selection) | DAW, Rudolph 2015, Klarevas 2019 |

This is roughly the BC ("Brennan Center") set as described by Donohue. It would survive a Lott-school referee because (a) it controls for crime-prone demographics, and (b) it does not introduce post-treatment "bad controls" like arrest rates that the Donohue critique argues are endogenous.

#### Headline (modal modern set — what Donohue/Webster reviewer would expect)
Add to Minimal:
| Variable | Rationale | Source / paper |
|---|---|---|
| `imprisonment_rate` (state CJ controls file) | DAW, Webster 2014, Cheng-Hoekstra 2013, McClellan-Tekin 2017 — universally present in modern specs; critique that omitting it inflates RTC effect | DAW |
| `sworn_officers_per_100k` (state CJ controls file) | Same papers | DAW |
| `ln(median_hh_income_real_2024)` or `pcpi_real_2024` | Most papers use one income measure; both are defensible | DAW, Rudolph 2015 |
| `share_bachelors_plus` | Education proxy; in McCourt 2020 and Klarevas 2019 | McCourt 2020 |
| `alcohol_per_capita_ethanol` (NEEDS DOWNLOAD) | Standard in McClellan-Tekin, Luca-Malhotra-Poliquin, Koper-Roth | McClellan & Tekin 2017 |

This corresponds to the **DAW set** with one extension (alcohol).

#### Expanded (kitchen-sink for robustness)
Add to Headline:
| Variable | Rationale | Source / paper |
|---|---|---|
| `police_expenditure_per_capita_real_2024` (state CJ controls file) | Rudolph 2015, McCourt 2020 use LE expenditures rather than headcount; includes both | Rudolph 2015 |
| `share_metropolitan` / `share_urban` (NEEDS DOWNLOAD or addable from county_panel rollup) | Rudolph 2015, McCourt 2020 use % MSA explicitly | Rudolph 2015 |
| `gini_coefficient` (NEEDS DOWNLOAD — ACS B19083 by state) | Rudolph 2015, McCourt 2020 | Rudolph 2015 |
| `drug_overdose_mortality_per_100k` (NEEDS DOWNLOAD — CDC WONDER) | Captures opioid-era confounding for 2010+ panel; critical post-2014 | McCourt 2020 (suicide spec) |
| `ownership_fss` and/or `ownership_rand` | Already in panel; controls for baseline gun-stock differences when treatment ≠ ownership-affecting | Klarevas 2019 (HH firearm prevalence) |
| `burglary_rate` | Webster 2014 uses burglary as a "demand for crime guns" proxy | Webster 2014 |
| State-specific linear trends OR region-by-year FE | Cheng-Hoekstra, McClellan-Tekin, Ayres-Donohue all use one or the other | Multiple |

### 2.2 Suicide (firearm suicide, total suicide, non-firearm suicide as placebo)

The literature splits cleanly: suicide specs use **alcohol, religiosity, overdose, % male, % veteran, % married** that homicide specs do not.

#### Minimal
| Variable | Rationale | Source / paper |
|---|---|---|
| `ln_population` | Standard | All |
| `ln_pcpi_real_2024` | Economic-distress control | Crifasi 2015 |
| `unemployment_rate` | Suicide-economy link | Crifasi 2015, McCourt 2020 |
| `poverty_rate` | Suicide-economy link | Anestis 2015, Crifasi 2015 |
| `share_male` | Suicide is overwhelmingly male | Crifasi 2015, McCourt 2020 |
| `share_age_25_44` and `share_age_15_24` | Age structure of suicide risk | Implied by all |

This corresponds roughly to Anestis & Anestis 2015 (population density + poverty), but extended with male-share and age structure that even Anestis acknowledged would have improved his model.

#### Headline (modal modern suicide set — what Crifasi/McCourt reviewer would expect)
Add to Minimal:
| Variable | Rationale | Source / paper |
|---|---|---|
| `alcohol_per_capita_ethanol` (NEEDS DOWNLOAD — NIAAA Surveillance Reports) | THE canonical suicide covariate; Crifasi 2015, McCourt 2020, Kivisto 2018 all use it | Crifasi 2015 |
| `drug_overdose_mortality_per_100k` (NEEDS DOWNLOAD — CDC WONDER) | McCourt 2020 explicitly | McCourt 2020 |
| `share_bachelors_plus` | Education proxy for suicide risk | McCourt 2020 |
| `share_black_nh` and `share_hispanic` | Suicide rates differ markedly by race | Crifasi 2015 |
| `religious_adherence_rate` (NEEDS DOWNLOAD — Pew RLS or ARDA US Religion Census 1990, 2000, 2010, 2020) | Crifasi 2015, McCourt 2020, Kivisto 2018 use it; protective factor | McCourt 2020 |
| `ownership_fss` or `ownership_rand` | Means-substitution mechanism; firearm-stock proxy is THE confounder for firearm-suicide | Miller-Hemenway 2002 |

This is the canonical "Crifasi/McCourt suicide stack" minus % married and % veteran (next tier).

#### Expanded
Add to Headline:
| Variable | Rationale | Source / paper |
|---|---|---|
| `share_married` (NEEDS DOWNLOAD — ACS S1201) | McCourt 2020 explicit | McCourt 2020 |
| `share_veteran` (NEEDS DOWNLOAD — ACS B21001) | McCourt 2020 explicit; veteran suicide elevated | McCourt 2020 |
| `share_metropolitan` / `share_urban` | McCourt 2020 | McCourt 2020 |
| `nsduh_serious_mental_illness_rate` and/or `nsduh_past_year_depression` (NEEDS DOWNLOAD — NSDUH state estimates) | Anestis 2017 uses NSDUH ideation/depression | Anestis 2017 |
| `imprisonment_rate` | Justification: collateral evidence on the CJ-system's role; arguably a placebo control | — |
| `median_hh_income_real_2024` | Robustness alternative to PCPI | McCourt 2020 |

### 2.3 Property / placebo crime (county property, burglary, motor-vehicle theft)

Property crime is typically used as a **placebo** in firearm-policy work — gun policy should not affect non-violent property crime. The covariate set should mirror the violence spec so the placebo is a like-for-like comparison.

#### Minimal
Same as Lethal-Violence Minimal. The minimal placebo set must mirror the minimal treatment set.

#### Headline
Same as Lethal-Violence Headline (DAW set + alcohol). Critical: alcohol DOES predict property crime (especially burglary, motor-vehicle theft) so its inclusion strengthens the placebo.

#### Expanded
Same as Lethal-Violence Expanded but DROP `ownership_fss/rand` if doing a strict placebo (gun ownership shouldn't affect property crime independent of burglary). KEEP `burglary_rate` only when motor-vehicle theft is the outcome (otherwise dropping it as outcome).

### 2.4 (Optional) Youth-specific outcomes

The literature does not cleanly distinguish a youth-band covariate set (most "youth suicide" papers — e.g., the 2024 AJPH age-21 paper, Anestis et al., Houtsma — use the suicide stack scaled to youth). If running a youth-suicide spec separately, the recommendation is:

#### Headline
- Suicide Headline set, but with `share_age_15_24` interacted as the relevant share, and consider replacing total `ownership` with a youth-access proxy (e.g., `share_households_with_children_with_firearms` if available — typically not).
- For youth firearm homicide, use Lethal-Violence Headline.

This is the area with the weakest covariate consensus; no strong philosophy emerges.

---

## Section 3 — Data source inventory and gaps

### 3.1 Already in panel (verified by reading column headers)

| Recommended variable | Panel column name | File | Coverage |
|---|---|---|---|
| Population | `population`, `ln_population` | `panel_core_augmented.csv` | Full |
| Real per-capita personal income | `pcpi_real_2024`, `ln_pcpi_real_2024` | `panel_core_augmented.csv` | Full |
| Unemployment rate | `unemployment_rate` | `panel_core_augmented.csv` | Full |
| Poverty rate | `poverty_rate` | `panel_demographic_augmented.csv` | 1990–2024 |
| Median HH income (nominal & real) | `median_hh_income_nominal`, `median_hh_income_real_2024` | `panel_demographic_augmented.csv` | 1990–2024 |
| Share white NH | `share_white_nh` | `panel_demographic_augmented.csv` | 1990–2024 |
| Share Black NH | `share_black_nh` | `panel_demographic_augmented.csv` | 1990–2024 |
| Share Hispanic | `share_hispanic` | `panel_demographic_augmented.csv` | 1990–2024 |
| Share male | `share_male` | `panel_demographic_augmented.csv` | 1990–2024 |
| Share age 15–24 | `share_age_15_24` | `panel_demographic_augmented.csv` | 1990–2024 |
| Share age 25–44 | `share_age_25_44` | `panel_demographic_augmented.csv` | 1990–2024 |
| Share bachelor's+ | `share_bachelors_plus` | `panel_demographic_augmented.csv` | 1990–2024 (ACS); pre-2005 from Decennial Census via historical_demographic_controls_1999_2004.csv |
| Imprisonment rate | `imprisonment_rate` | `state_cj_controls_1979_2024.csv` | 1979–2024 |
| Sworn officers per 100k | `sworn_officers_per_100k` | `state_cj_controls_1979_2024.csv` | Coverage subject to FBI LEMAS gaps |
| Police expenditure per capita (real) | `police_expenditure_per_capita_real_2024` | `state_cj_controls_1979_2024.csv` | Census of Governments 1979–2020 plus imputation flag |
| Death-penalty indicator, executions count | `has_death_penalty`, `executions_count` | `state_cj_controls_1979_2024.csv` | Full |
| UCR violent / property crime + sub-categories | `violent_crime`, `violent_rate`, `property_crime`, `property_rate`, `homicide_rate`, `robbery_rate`, `rape_rate`, `aggravated_assault_rate`, `burglary_rate`, `larceny_rate`, `motor_vehicle_theft_rate` | `panel_core_augmented.csv` | 1979–2024 |
| Firearm homicide rate, firearm suicide rate, total suicide rate, non-firearm homicide rate | `firearm_homicide_rate`, `firearm_suicide_rate`, `total_suicide_rate`, `nonfirearm_homicide_rate` | `panel_core_augmented.csv` | NCHS-derived, multi-year |
| HH firearm ownership proxy (FSS) | `ownership_fss` | `panel_core_augmented.csv` | Full |
| HH firearm ownership (RAND TL-354 SE & estimate) | `ownership_rand`, `ownership_rand_se` | `panel_core_augmented.csv` | 1980–2016 |
| NICS background-check counts | `nics_total`, `nics_handgun`, `nics_long_gun`, `nics_total_per_100k`, etc. | `panel_market_augmented.csv` | 1999–2026 |
| County-level violent / murder / property / burglary / MVT rates | `county_violent_crime_rate`, `county_murder_rate`, `county_burglary_rate`, `county_motor_vehicle_theft_rate`, etc. | `county_panel_2009_2024.csv` | 2009–2024 |

**Quick wins:** the imprisonment, sworn-officer, police-expenditure variables are all already built but the production specs apparently aren't using them. The single most leveraged improvement is to swap the current 3-variable spec for the **DAW set** drawn entirely from existing files.

### 3.2 Addable from existing in-project sources (no new download)

| Recommended variable | How to compute | Source already in project |
|---|---|---|
| `share_metropolitan` (state-level rollup) | Aggregate county-level metropolitan-status flag from `county_fips_bridge.csv` and county population from `county_panel_2009_2024.csv` | County panel files (2009–2024 only); for earlier years, use NCHS Urban-Rural classification scheme — could be derived from already-downloaded Census intercensal files in `data/raw/` |
| `share_urban` (state-level, slow-moving) | Decennial Census urban-rural counts — already partially captured in `data/raw/historical_demographics/`; add only census decade points and interpolate | Existing downloads |
| State-specific linear time trends | Constructed in regression code from `year` | — |
| Region-by-year FE | Constructed in regression code from `state` → Census region map | — |

### 3.3 Needs new download

| Recommended variable | Canonical source | URL | Effort estimate |
|---|---|---|---|
| **Per-capita ethanol consumption (gallons per capita 14+)** | NIAAA Alcohol Epidemiologic Data System, Surveillance Reports | https://www.niaaa.nih.gov/publications/surveillance-reports ; also openICPSR https://www.openicpsr.org/openicpsr/project/105583/version/V5/view (1977–2018) ; SR #122 covers 1977–2023 | **Low (1–2 hours).** State-year panel CSV directly downloadable from openICPSR or NIAAA. Coverage 1977–2023 → matches our `panel_core` window. **HIGHEST PRIORITY.** |
| **Drug overdose mortality (rate per 100k)** | CDC WONDER multiple cause-of-death files (X40–X44, X60–X64, X85, Y10–Y14 per ICD-10) | https://wonder.cdc.gov/ucd-icd10.html | **Medium (3–4 hours).** Need to query WONDER state-year by ICD-10 cause; suppression for cells <10 deaths in some early-2000s state-years (rare for overdose). Coverage 1999–2023; pre-1999 needs ICD-9 (X-codes don't exist) and is generally not used in this literature. |
| **Religious adherence rate** (per 1,000 population) | US Religion Census (formerly Glenmary Research Center / RCMS) — quinquennial: 1980, 1990, 2000, 2010, 2020 | https://www.usreligioncensus.org/ ; via ARDA at https://www.thearda.com/us-religion/ | **Medium (2–3 hours).** Decennial only; interpolate for inter-census years (the standard approach in Crifasi/McCourt). |
| **Share married** | ACS S1201 (2005+); Decennial Census pre-2005 | https://data.census.gov/table/ACSST1Y2023.S1201 | **Low (1 hour).** Already have ACS infrastructure in panel. |
| **Share veteran** | ACS B21001 (2005+) | https://data.census.gov/table/ACSDT1Y2023.B21001 | **Low (1 hour).** |
| **Gini coefficient** | ACS B19083 (2005+); Frank, Mark W. state Gini series for 1917–present | https://data.census.gov/table/ACSDT1Y2023.B19083 ; http://www.shsu.edu/eco_mwf/inequality.html | **Low (1 hour).** Frank's series is canonical for long-panel work. |
| **NSDUH state estimates of serious mental illness (SMI), past-year depression** | SAMHSA NSDUH state-level estimates | https://www.samhsa.gov/data/data-we-collect/nsduh-national-survey-drug-use-and-health | **Medium (2–3 hours).** Annual state estimates 2008+; sparse pre-2008. Anestis 2017 uses these. |
| **Share metropolitan / urban** for full state-year history | NCHS Urban-Rural Classification Scheme + Census Bureau urban share series | https://www.cdc.gov/nchs/data-analysis-tools/urban-rural.html ; https://www.census.gov/programs-surveys/geography/guidance/geo-areas/urban-rural.html | **Medium (3–4 hours).** Decennial-anchored; requires interpolation. |

### 3.4 Variables flagged in literature but NOT recommended for inclusion

- **Lott-Mustard 36-cell age × race × sex demographic shares.** Overfits dramatically (parameter:obs ≈ 1:8). The 6 share-variables in our panel (`share_age_15_24`, `share_age_25_44`, `share_male`, `share_black_nh`, `share_hispanic`, `share_bachelors_plus`) are sufficient and avoid the overfitting critique.
- **Arrest rate.** Lott-Mustard's preferred deterrence proxy. Donohue 2019 and RAND 2024 both treat it as a "bad control" — endogenous to crime — and the modern consensus omits it.
- **Welfare spending per capita.** Used by Cheng-Hoekstra, but later work (DAW, McCourt) considered it dominated by income + poverty. Optional addition.

### 3.5 Methodological gotchas (read before re-estimating)

1. **DAW vs. LM specification matters more than weighting.** The Donohue-Aneja-Weber 2019 paper (and the 2014 Aneja-Donohue-Zhang precursor) demonstrate that the **same data + same estimator** can yield opposite-signed RTC effects depending on whether you use the LM covariate set (no incarceration, no police) or the DAW set (with both). Our current 3-variable spec is closer to LM than DAW. **Run all three tiers and report the multiverse.**
2. **Entropy balancing vs. RA (regression adjustment).** Across the modern public-health gun-policy SCM literature (Crifasi, Rudolph, McCourt, Kivisto), the **standard weighting is the SCM weight itself** (Abadie-Diamond-Hainmueller), with predictors averaged over pre-treatment years. Outside SCM, the modal weighting in the econometric literature (DAW, Cheng-Hoekstra, McClellan-Tekin, Luca-Malhotra-Poliquin) is **none — straight regression adjustment with state + year FE.** **Entropy balancing is rare** in this literature; the closest analog is Donohue's LASSO-based covariate selection in the 2014 NBER paper. If your re-estimation uses entropy balancing on Callaway-Sant'Anna ATT(g,t) groups, you are doing something more modern than the modal published spec — flag it as a sensitivity vs. RA, not the headline.
3. **Sworn officers and police expenditure are partially imputed in our CJ file.** The `police_expenditure_imputed_flag` column should be controlled for or be the basis of a sensitivity-drop. RAND 2024 specifically flags imputation strategies as a methodological standard.
4. **Alcohol-per-capita is a "policy-era confounder."** The 1990s decline in violence and the 2010s opioid era both correlate with alcohol consumption shifts. Omitting alcohol biases coefficients on any policy adopted in waves (e.g., RTC, SYG, ERPO) where the wave is collinear with alcohol trends. This is the single largest specification gap.
5. **Drug overdose mortality is critical for the 2010+ panel.** The opioid crisis is a major confounder for any policy adopted post-2010 (most ERPO laws, permitless carry expansion, several PTP changes). Without an overdose control, coefficients on these laws may absorb opioid-era mortality changes. CDC WONDER is the standard source.
6. **Religiosity is slow-moving and sparse.** Religious adherence data only exists in 1980, 1990, 2000, 2010, 2020 (US Religion Census). Crifasi/McCourt interpolate. State FE will absorb most of this — its inclusion is more important for SCM (which uses pre-period averages of predictors) than for two-way FE DiD.
7. **Outcome should match covariate stack.** Do not mix: e.g., do not run a homicide regression with the suicide stack (alcohol + religiosity + male share but no incarceration). Most modern gun-policy referees (especially from public health) will reject this. Use the outcome-tailored stacks in Section 2.
8. **Bad controls to avoid.** The literature flags as "bad controls" (post-treatment / mediator-on-the-pathway) the following: arrest rate (endogenous to crime), gun-ownership proxies in policies that explicitly target ownership, NICS background checks (mechanism for many policies), and clearance rates (Donohue-Cai-Bondy-Cook 2023 use these as **outcomes**, not controls).
9. **County-level vs. state-level covariates.** When estimating at the county level (`county_panel_2009_2024.csv`), the demographic and economic controls in the file are county-level, but the CJ controls (`imprisonment_rate`, sworn officers, police expenditure) are state-level. The standard approach is to merge the state-level CJ controls onto each county and treat them as state×year fixed effects (or include them alongside state FE, knowing they are absorbed in part). Verify the merge strategy in `lib_stacked_dd.py` matches expectation.
10. **Pre-treatment matching window for SCM.** Crifasi/McCourt match on prelaw averages of predictors AND every prelaw year of the outcome. If using pre-2010 data with sparse alcohol/overdose coverage, consider matching windows that don't require those variables across the full pre-period.

---

## Recommended priority for orchestrator

1. **Immediately:** swap `ln_population, unemployment_rate, ln_pcpi_real_2024` → DAW Headline set (already in-project). Re-run all stacked-DD and CS specifications. This will be the largest single specification improvement and requires no downloads.
2. **First download:** NIAAA Apparent Per Capita Alcohol Consumption from openICPSR project 105583. ~1 hour. Include in Headline.
3. **Second download:** CDC WONDER drug-overdose mortality 1999–2023 by state-year. ~3 hours. Include in Expanded for any post-2010 policy.
4. **Third download:** US Religion Census state-level adherence rates from ARDA. ~3 hours. Required for any suicide-spec robustness.
5. **Future:** Frank Gini series, ACS marriage/veteran shares, NSDUH SMI/depression. Optional for Expanded tier only.

The **three-tier spec table for each outcome** (Section 2) is the deliverable the orchestrator should implement as alternative spec arguments to the existing estimator entry points. The literature precedent for reporting all three tiers (rather than just one) is established explicitly by Donohue-Aneja-Weber 2019 (DAW vs. BC vs. LM vs. MM) and is a methodological recommendation in RAND (2024).
