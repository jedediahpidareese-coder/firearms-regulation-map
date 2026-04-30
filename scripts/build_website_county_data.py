"""Phase 4: emit the JSON files the website needs to render the county-level
choropleth.

Reads `data/processed/county_panel_2009_2024.csv` and writes:

    docs/data/county/{year}.json     one file per year, lazy-loaded by the page
    docs/data/county_meta.json       variable definitions for the county view
    docs/data/county_manifest.json   high-level summary (years, vars, etc.)

Each per-year file is shaped as { county_fips: { var: value, ... } } so the
frontend can look up `byFips[fips][var]` cheaply.

The variable list is intentionally smaller than the underlying panel (30+ cols)
to keep file sizes down. Add or remove items in COUNTY_VARS below.
"""

from __future__ import annotations

import json
from collections import OrderedDict, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
OUT = ROOT / "docs" / "data"
COUNTY_DIR = OUT / "county"
COUNTY_DIR.mkdir(parents=True, exist_ok=True)


# Variables we expose on the county map. Many overlap conceptually with the
# state map but use county-level values; a few (state_*) are intentionally
# state-baseline values joined down to county.
COUNTY_VARS = OrderedDict([
    # Population
    ("population", {
        "label": "Population", "category": "Demographics",
        "unit": "People", "format": "integer",
        "definition": "County resident population from Census PEP.",
        "source": "Census Population Estimates Program",
        "source_url": "https://www.census.gov/programs-surveys/popest.html",
    }),

    # Crime (Kaplan UCR, 2009-2024 except a handful of tiny counties).
    ("county_violent_crime_rate", {
        "label": "Violent crime rate", "category": "Crime",
        "unit": "Per 100,000 people", "format": "rate",
        "definition": "Index violent crimes per 100,000 (Kaplan UCR aggregated to county-year).",
        "source": "Jacob Kaplan UCR Offenses Known V22",
        "source_url": "https://www.openicpsr.org/openicpsr/project/100707",
    }),
    ("county_property_crime_rate", {
        "label": "Property crime rate", "category": "Crime",
        "unit": "Per 100,000 people", "format": "rate",
        "definition": "Index property crimes per 100,000.",
        "source": "Jacob Kaplan UCR Offenses Known V22",
        "source_url": "https://www.openicpsr.org/openicpsr/project/100707",
    }),
    ("county_murder_rate", {
        "label": "Murder rate", "category": "Crime",
        "unit": "Per 100,000 people", "format": "rate",
        "definition": "Murder per 100,000.",
        "source": "Jacob Kaplan UCR Offenses Known V22",
        "source_url": "https://www.openicpsr.org/openicpsr/project/100707",
    }),
    ("county_robbery_rate", {
        "label": "Robbery rate", "category": "Crime",
        "unit": "Per 100,000 people", "format": "rate",
        "definition": "Robbery per 100,000.",
        "source": "Jacob Kaplan UCR Offenses Known V22",
        "source_url": "https://www.openicpsr.org/openicpsr/project/100707",
    }),
    ("county_aggravated_assault_rate", {
        "label": "Aggravated assault rate", "category": "Crime",
        "unit": "Per 100,000 people", "format": "rate",
        "definition": "Aggravated assault per 100,000.",
        "source": "Jacob Kaplan UCR Offenses Known V22",
        "source_url": "https://www.openicpsr.org/openicpsr/project/100707",
    }),
    ("county_burglary_rate", {
        "label": "Burglary rate", "category": "Crime",
        "unit": "Per 100,000 people", "format": "rate",
        "definition": "Burglary per 100,000.",
        "source": "Jacob Kaplan UCR Offenses Known V22",
        "source_url": "https://www.openicpsr.org/openicpsr/project/100707",
    }),
    ("county_larceny_rate", {
        "label": "Larceny rate", "category": "Crime",
        "unit": "Per 100,000 people", "format": "rate",
        "definition": "Larceny per 100,000.",
        "source": "Jacob Kaplan UCR Offenses Known V22",
        "source_url": "https://www.openicpsr.org/openicpsr/project/100707",
    }),

    # State firearm mortality joined down (Phase 2a).
    ("state_firearm_suicide_rate", {
        "label": "State firearm suicide rate (joined down)", "category": "Suicide & firearm deaths",
        "unit": "Per 100,000 people", "format": "rate",
        "definition": "STATE-LEVEL firearm suicide rate, applied to every county in the state. No within-state variation.",
        "source": "Firearm suicide / homicide v2 dataset (joined down by state)",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/37743886/",
        "caveat": "State value applied to every county. Not true county detail.",
    }),
    ("state_firearm_homicide_rate", {
        "label": "State firearm homicide rate (joined down)", "category": "Suicide & firearm deaths",
        "unit": "Per 100,000 people", "format": "rate",
        "definition": "STATE-LEVEL firearm homicide rate, applied to every county in the state.",
        "source": "Firearm suicide / homicide v2 dataset (joined down by state)",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/37743886/",
        "caveat": "State value applied to every county. Not true county detail.",
    }),
    ("state_ownership_fss", {
        "label": "State FS/S ownership proxy (joined down)", "category": "Gun ownership",
        "unit": "Firearm-suicide ratio", "format": "percent",
        "definition": "STATE-LEVEL firearm-suicide-share proxy. Same value for every county in the state. Mechanically tied to suicide outcomes.",
        "source": "Firearm suicide / homicide v2 dataset",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/37743886/",
        "caveat": "State value applied to every county; tied to suicide outcomes.",
    }),

    # Demographics (county-level from ACS).
    ("share_white_nh", {
        "label": "Share non-Hispanic white", "category": "Demographics",
        "unit": "Share of population", "format": "percent",
        "definition": "Share of population non-Hispanic white alone (ACS 5y B03002).",
        "source": "ACS 5-year",
        "source_url": "https://www.census.gov/programs-surveys/acs/",
    }),
    ("share_black_nh", {
        "label": "Share non-Hispanic Black", "category": "Demographics",
        "unit": "Share of population", "format": "percent",
        "definition": "Share of population non-Hispanic Black alone (ACS 5y B03002).",
        "source": "ACS 5-year",
        "source_url": "https://www.census.gov/programs-surveys/acs/",
    }),
    ("share_hispanic", {
        "label": "Share Hispanic", "category": "Demographics",
        "unit": "Share of population", "format": "percent",
        "definition": "Share of population Hispanic or Latino, any race.",
        "source": "ACS 5-year",
        "source_url": "https://www.census.gov/programs-surveys/acs/",
    }),
    ("share_male", {
        "label": "Share male", "category": "Demographics",
        "unit": "Share of population", "format": "percent",
        "definition": "Share of population male.",
        "source": "ACS 5-year",
        "source_url": "https://www.census.gov/programs-surveys/acs/",
    }),
    ("share_age_15_24", {
        "label": "Share age 15-24", "category": "Demographics",
        "unit": "Share of population", "format": "percent",
        "definition": "Share of population aged 15-24.",
        "source": "ACS 5-year",
        "source_url": "https://www.census.gov/programs-surveys/acs/",
    }),
    ("share_age_25_44", {
        "label": "Share age 25-44", "category": "Demographics",
        "unit": "Share of population", "format": "percent",
        "definition": "Share of population aged 25-44.",
        "source": "ACS 5-year",
        "source_url": "https://www.census.gov/programs-surveys/acs/",
    }),
    ("share_bachelors_plus", {
        "label": "Share with bachelor's degree or higher (25+)", "category": "Demographics",
        "unit": "Share of adults 25+", "format": "percent",
        "definition": "Share of adults age 25+ with bachelor's degree or higher (ACS 5y; B15003 from 2012 onward, B15002 for 2009-2011).",
        "source": "ACS 5-year",
        "source_url": "https://www.census.gov/programs-surveys/acs/",
    }),

    # Economy.
    ("median_hh_income_real_2024", {
        "label": "Median household income (2024 USD)", "category": "Economy",
        "unit": "U.S. dollars (2024)", "format": "currency",
        "definition": "Census SAIPE median household income, deflated to 2024 dollars via CPI-U.",
        "source": "Census SAIPE",
        "source_url": "https://www.census.gov/programs-surveys/saipe/",
    }),
    ("poverty_pct_all_ages", {
        "label": "Poverty rate", "category": "Economy",
        "unit": "Percent", "format": "percent_pre",
        "definition": "Census SAIPE all-ages poverty rate.",
        "source": "Census SAIPE",
        "source_url": "https://www.census.gov/programs-surveys/saipe/",
    }),
    ("unemployment_rate", {
        "label": "Unemployment rate", "category": "Economy",
        "unit": "Percent", "format": "percent_pre",
        "definition": "BLS LAUS annual average unemployment rate (via USDA ERS mirror; 2024 not yet released).",
        "source": "BLS LAUS via USDA ERS",
        "source_url": "https://www.ers.usda.gov/data-products/county-level-data-sets/",
    }),
    ("pcpi_real_2024", {
        "label": "Per-capita personal income (2024 USD)", "category": "Economy",
        "unit": "U.S. dollars (2024)", "format": "currency",
        "definition": "BEA per-capita personal income, deflated to 2024 dollars via CPI-U.",
        "source": "BEA CAINC1",
        "source_url": "https://www.bea.gov/data/economic-accounts/regional",
    }),

    # State laws joined down.
    ("lawtotal", {
        "label": "State firearm law count (joined down)", "category": "Regulation",
        "unit": "Laws (count)", "format": "integer",
        "definition": "Tufts state firearm law count, applied to every county in the state.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
    }),
])


def build():
    print("Loading county panel ...")
    df = pd.read_csv(PROC / "county_panel_2009_2024.csv",
                     dtype={"county_fips": str, "state_fips": str})
    print(f"  {len(df):,} rows, {df['county_fips'].nunique()} counties, "
          f"{df['year'].nunique()} years")

    # Emit a single county_names.json the page uses for hover labels.
    # Pick the most recent (county_name, state_name) per county_fips so the
    # AK/SD/VA renames land on canonical modern names.
    last_names = (df.sort_values("year")
                    .groupby("county_fips", as_index=False)
                    .agg({"county_name": "last", "state_name": "last"}))
    name_map = {
        r["county_fips"]: f"{r['county_name']}, {r['state_name']}"
        for _, r in last_names.iterrows()
    }
    (OUT / "county_names.json").write_text(json.dumps(name_map, separators=(",", ":")))
    print(f"  Wrote docs/data/county_names.json: {len(name_map):,} entries, "
          f"{(OUT / 'county_names.json').stat().st_size/1024:,.0f} KB")

    available = [v for v in COUNTY_VARS if v in df.columns]
    missing = [v for v in COUNTY_VARS if v not in df.columns]
    if missing:
        print(f"  WARN: panel missing columns we wanted: {missing}")

    years = sorted(df["year"].dropna().unique().astype(int).tolist())
    bytes_total = 0
    for yr in years:
        sub = df[df["year"] == yr][["county_fips"] + available].copy()
        out: dict[str, dict[str, float]] = {}
        for rec in sub.to_dict(orient="records"):
            fips = rec["county_fips"]
            cell: dict[str, float] = {}
            for k, v in rec.items():
                if k == "county_fips":
                    continue
                if v is None:
                    continue
                if isinstance(v, float) and np.isnan(v):
                    continue
                cell[k] = round(float(v), 4) if isinstance(v, (int, float, np.floating)) else v
            if cell:
                out[fips] = cell
        path = COUNTY_DIR / f"{yr}.json"
        path.write_text(json.dumps(out, separators=(",", ":")))
        size = path.stat().st_size
        bytes_total += size
        print(f"  {yr}: {len(out):,} counties, {size/1024:,.0f} KB")
    print(f"Total per-year files: {bytes_total/1024/1024:.1f} MB")

    # Metadata: include only the variables we actually emitted.
    metadata: dict[str, dict] = {}
    for v in available:
        m = dict(COUNTY_VARS[v])
        s = df[["year", v]].dropna()
        m["observed_year_range"] = ([int(s["year"].min()), int(s["year"].max())]
                                    if len(s) else None)
        m["observed_obs"] = int(len(s))
        metadata[v] = m
    (OUT / "county_meta.json").write_text(json.dumps(metadata, indent=2))

    categories: dict[str, list[str]] = defaultdict(list)
    for v, m in metadata.items():
        categories[m["category"]].append(v)
    manifest = {
        "generated_at": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "year_range": [years[0], years[-1]],
        "years": years,
        "variables": list(metadata.keys()),
        "categories": {k: sorted(v) for k, v in categories.items()},
        "default_variable": "county_violent_crime_rate",
        "default_year": 2024,
        "topo_url": "https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json",
    }
    (OUT / "county_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote docs/data/county_meta.json and docs/data/county_manifest.json")
    print(f"Variables: {len(metadata)} across {len(categories)} categories")


if __name__ == "__main__":
    build()
