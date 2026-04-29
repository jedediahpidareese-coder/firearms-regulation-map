# U.S. Firearms Regulation, Crime, and Outcomes

Research project building balanced state-year panels for econometric and causal-inference work on U.S. firearm regulation, ownership, crime, suicide, and demographics, plus a public interactive map.

## Layout

- [`firearms_us_data_inventory.md`](firearms_us_data_inventory.md) &middot; inventory of every data source under consideration with coverage, geography, and links.
- [`scripts/`](scripts/) &middot; build pipelines for the balanced panels and for the website data.
- [`data/`](data/) &middot; raw and intermediate inputs.
- [`data/processed/`](data/processed/) &middot; the four balanced panels:
  - `panel_core_1979_2024.csv` &middot; 50 states &times; 46 years, laws + crime + economics
  - `panel_demographic_1990_2024.csv` &middot; adds reconstructed demographic shares
  - `panel_market_1999_2024.csv` &middot; adds NICS background checks
  - `panel_modern_2008_2024.csv` &middot; adds ACS demographic detail
  - Plus `variable_dictionary.csv`, `panel_balance_checks.csv`, `coverage_diagnostics.csv`, `sources_integrated.csv`, `crime_repairs_log.csv`.
- [`outputs/`](outputs/) &middot; the consolidated balanced panel workbook and an example causal-inference audit (permitless-carry &rarr; suicide).
- [`docs/`](docs/) &middot; the public website (deployed via GitHub Pages from this folder).

## Rebuild

```sh
# 1. Rebuild balanced panels (slow; needs raw inputs in data/)
python scripts/build_firearms_panel.py

# 2. Rebuild website data
python scripts/build_website_data.py

# 3. Preview website
python -m http.server 8765 -d docs
# then open http://localhost:8765/
```

## Citations &amp; sources

See the [about page](docs/about.html) and [`firearms_us_data_inventory.md`](firearms_us_data_inventory.md) for full source citations.
