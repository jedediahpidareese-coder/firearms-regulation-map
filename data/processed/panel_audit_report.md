# Balanced panel audit

_Generated: 2026-04-30 00:02 UTC_

## Panel-level summary

| Panel | Years | Rows | States | Years (n) | Vars | Dupes | Balanced |
|---|---|---|---|---|---|---|---|
| `panel_core` | 1979-2024 | 2,300/2,300 | 50 | 46/46 | 86 | 0 | ✅ |
| `panel_demographic` | 1990-2024 | 1,750/1,750 | 50 | 35/35 | 96 | 0 | ✅ |
| `panel_market` | 1999-2024 | 1,300/1,300 | 50 | 26/26 | 94 | 0 | ✅ |
| `panel_modern` | 2008-2024 | 850/850 | 50 | 17/17 | 105 | 0 | ✅ |

## Variables by category, per panel

### `panel_core`

| Category | n vars | Vars (alpha) |
|---|---|---|
| key | 3 | `state`, `state_abbr`, `year` |
| law | 72 | `age18longgunpossess`, `age18longgunsale`, `age21handgunpossess`, `age21handgunsale`, `age21longgunpossess`, `age21longgunsale`, `amm18`, `amm21h`, ... (+64 more) |
| law_total | 1 | `lawtotal` |
| crime | 4 | `property_crime`, `property_rate`, `violent_crime`, `violent_rate` |
| economy | 5 | `ln_pcpi_real_2024`, `ln_population`, `pcpi_nominal`, `pcpi_real_2024`, `unemployment_rate` |
| demographics | 1 | `population` |

### `panel_demographic`

| Category | n vars | Vars (alpha) |
|---|---|---|
| key | 3 | `state`, `state_abbr`, `year` |
| law | 72 | `age18longgunpossess`, `age18longgunsale`, `age21handgunpossess`, `age21handgunsale`, `age21longgunpossess`, `age21longgunsale`, `amm18`, `amm21h`, ... (+64 more) |
| law_total | 1 | `lawtotal` |
| crime | 4 | `property_crime`, `property_rate`, `violent_crime`, `violent_rate` |
| economy | 8 | `ln_pcpi_real_2024`, `ln_population`, `median_hh_income_nominal`, `median_hh_income_real_2024`, `pcpi_nominal`, `pcpi_real_2024`, `poverty_rate`, `unemployment_rate` |
| demographics | 8 | `population`, `share_age_15_24`, `share_age_25_44`, `share_bachelors_plus`, `share_black_nh`, `share_hispanic`, `share_male`, `share_white_nh` |

### `panel_market`

| Category | n vars | Vars (alpha) |
|---|---|---|
| key | 3 | `state`, `state_abbr`, `year` |
| law | 72 | `age18longgunpossess`, `age18longgunsale`, `age21handgunpossess`, `age21handgunsale`, `age21longgunpossess`, `age21longgunsale`, `amm18`, `amm21h`, ... (+64 more) |
| law_total | 1 | `lawtotal` |
| crime | 4 | `property_crime`, `property_rate`, `violent_crime`, `violent_rate` |
| economy | 5 | `ln_pcpi_real_2024`, `ln_population`, `pcpi_nominal`, `pcpi_real_2024`, `unemployment_rate` |
| market | 8 | `nics_handgun`, `nics_long_gun`, `nics_multiple`, `nics_other`, `nics_permit`, `nics_permit_recheck`, `nics_total`, `nics_total_per_100k` |
| demographics | 1 | `population` |

### `panel_modern`

| Category | n vars | Vars (alpha) |
|---|---|---|
| key | 4 | `acs_dataset`, `state`, `state_abbr`, `year` |
| law | 72 | `age18longgunpossess`, `age18longgunsale`, `age21handgunpossess`, `age21handgunsale`, `age21longgunpossess`, `age21longgunsale`, `amm18`, `amm21h`, ... (+64 more) |
| law_total | 1 | `lawtotal` |
| crime | 4 | `property_crime`, `property_rate`, `violent_crime`, `violent_rate` |
| economy | 8 | `ln_pcpi_real_2024`, `ln_population`, `median_hh_income_nominal`, `median_hh_income_real_2024`, `pcpi_nominal`, `pcpi_real_2024`, `poverty_rate`, `unemployment_rate` |
| market | 8 | `nics_handgun`, `nics_long_gun`, `nics_multiple`, `nics_other`, `nics_permit`, `nics_permit_recheck`, `nics_total`, `nics_total_per_100k` |
| demographics | 8 | `population`, `share_age_15_24`, `share_age_25_44`, `share_bachelors_plus`, `share_black_nh`, `share_hispanic`, `share_male`, `share_white_nh` |

## Gaps vs the ideal econometric stack

These variables exist in raw data on disk and on the public website JSON, but are not yet integrated into the saved balanced panel CSVs in `data/processed/`. The `scripts/build_website_data.py` pipeline already loads and merges them, so the same merge code can be lifted into the panel build.

- `firearm_suicides` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Firearm suicides (count) - integrate from firearm_suicide_homicide_dataset_v2.tab (1979-2023)
- `total_suicides` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Total suicides (count) - same source, 1979-2023
- `firearm_suicide_rate` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Firearm suicides per 100k - derive from counts and population
- `total_suicide_rate` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Total suicides per 100k - derive from counts and population
- `firearm_homicides` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Firearm homicides (count) - same source
- `nonfirearm_homicides` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Nonfirearm homicides (count) - same source
- `firearm_homicide_rate` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Firearm homicide per 100k - derive
- `nonfirearm_homicide_rate` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Nonfirearm homicide per 100k - derive
- `ownership_fss` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - FS/S ownership proxy - same source (use only as descriptive)
- `ownership_rand` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - RAND household firearm ownership rate (1980-2016) - integrate from TL-354
- `ownership_rand_se` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - RAND HFR standard error - same source
- `homicide` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Homicide count - integrate from OpenCrime granular file (1979-2024)
- `homicide_rate` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Homicide rate per 100k - derive
- `robbery` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Robbery count - OpenCrime
- `robbery_rate` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Robbery rate per 100k - derive
- `rape` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Rape count - OpenCrime (note: 2013 definition change)
- `rape_rate` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Rape rate per 100k - derive
- `aggravated_assault` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Agg assault count - OpenCrime
- `aggravated_assault_rate` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Agg assault rate per 100k - derive
- `burglary` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Burglary count - OpenCrime
- `burglary_rate` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Burglary rate per 100k - derive
- `larceny` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Larceny count - OpenCrime
- `larceny_rate` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - Larceny rate per 100k - derive
- `motor_vehicle_theft` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - MV theft count - OpenCrime
- `motor_vehicle_theft_rate` &mdash; missing in: panel_core, panel_demographic, panel_market, panel_modern
  - MV theft rate per 100k - derive

## How to apply the fixes

Run `python scripts/augment_panels.py` (added in the same change) which:

1. Reads each existing balanced panel.
2. Merges in the granular crime variables from `data/opencrime_state_trends.json` (with the documented NC&rarr;ND 2022 reassignment).
3. Merges in suicide/homicide counts and the FS/S ownership proxy from `data/firearm_suicide_homicide_dataset_v2.tab`.
4. Merges in the RAND household firearm ownership rate (1980-2016) from the TL-354 spreadsheet.
5. Computes derived rates (per 100k) for any count-only variables.
6. Writes augmented panels alongside the originals as `data/processed/{panel_name}_augmented.csv` and re-runs balance checks.