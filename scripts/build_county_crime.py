"""Phase 3: aggregate Jacob Kaplan's agency-level UCR Offenses Known files
into a county-year crime panel and merge into the existing county panel.

This script expects the user to have manually downloaded Kaplan's openICPSR
project 100707 ("Offenses Known and Clearances by Arrest, 1960-2020")
and placed the unpacked files under:

    data/county/kaplan_offenses/

Kaplan distributes one file per year (CSV / DTA / RDA). This script:
1. Discovers the per-year offense files in that directory.
2. Reads each year's agency-level rows (one per ORI per year).
3. Filters to the panel window (2009-2024 currently; gaps documented).
4. Sums agency offense counts to (county_fips, year).
5. Computes per-100,000 rates using PEP county population from the existing
   panel.
6. Writes the county-year crime layer to
   data/processed/county_crime_2009_2024.csv (separate file so it does not
   interact with the existing balanced county panel until we explicitly
   merge it).

Outputs:
    data/processed/county_crime_2009_2024.csv
    data/processed/county_crime_coverage.csv
    data/processed/county_crime_dropped_agencies.csv

Open questions to verify with the actual files in hand:
- Exact column names (FIPS_STATE_CODE / FIPS_COUNTY_CODE vs fips_state / fips_county).
- Whether the actual_* columns already aggregate the 12 months of the year,
  or whether each row is a single month.
- Whether ORI counts include rows from agencies covering the same county
  (yes - sheriff's office plus city PDs - we sum them).
- How Kaplan handles months-missing imputation (we'll preserve his
  reported `actual_*` values without re-adjusting).
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
COUNTY = DATA / "county"
KAPLAN = COUNTY / "kaplan_offenses"
PROC = DATA / "processed"

YEAR_START, YEAR_END = 2009, 2024
YEARS = list(range(YEAR_START, YEAR_END + 1))

# Apply the same FIPS bridge the county panel uses (see scripts/build_county_panel.py).
# Kaplan publishes pre-rename FIPS for AK Wade Hampton and SD Shannon throughout
# all years; remap them to the canonical post-2015 codes so they merge cleanly.
KAPLAN_FIPS_RENAMES = {
    "02270": "02158",  # AK Wade Hampton -> Kusilvak (2015)
    "46113": "46102",  # SD Shannon -> Oglala Lakota (2015)
    "51515": "51019",  # VA Bedford City -> Bedford County (2013)
}


# Kaplan publishes counts for many offense categories. We extract a useful
# subset that aligns with the state-panel granular crime variables.
KAPLAN_OFFENSE_COLUMNS = [
    "actual_murder",
    "actual_manslaughter",
    "actual_rape_total",                 # may be split (legacy + revised) post-2013
    "actual_robbery_total",
    "actual_assault_aggravated",
    "actual_burglary_total",
    "actual_theft_total",
    "actual_mtr_veh_theft_total",
    "actual_arson_total",
    # Index-crime aggregates Kaplan computes:
    "actual_index_violent",
    "actual_index_property",
    "actual_all_crimes",
]

# Map Kaplan column names -> our canonical names.
RENAME_OUT = {
    "actual_murder":               "county_murder",
    "actual_manslaughter":         "county_manslaughter",
    "actual_rape_total":           "county_rape",
    "actual_robbery_total":        "county_robbery",
    "actual_assault_aggravated":   "county_aggravated_assault",
    "actual_burglary_total":       "county_burglary",
    "actual_theft_total":          "county_larceny",
    "actual_mtr_veh_theft_total":  "county_motor_vehicle_theft",
    "actual_arson_total":          "county_arson",
    "actual_index_violent":        "county_violent_crime",
    "actual_index_property":       "county_property_crime",
    "actual_all_crimes":           "county_all_index_crimes",
}


def discover_data() -> tuple[Path | None, dict[int, Path]]:
    """Locate Kaplan offense data.

    Two layouts are supported:
    - One concatenated file like `offenses_known_yearly_1960_2024.csv`
      (the usual openICPSR V22 distribution).
    - Per-year files like `offenses_known_yearly_2009.csv` (older form).

    Returns (combined_file_path_or_None, by_year_dict).
    """
    if not KAPLAN.exists():
        raise SystemExit(
            f"Kaplan files not found at {KAPLAN}.\n"
            "Please download openICPSR project 100707 and unzip there."
        )
    combined: Path | None = None
    by_year: dict[int, Path] = {}
    for path in sorted(KAPLAN.rglob("*")):
        if not path.is_file():
            continue
        name = path.name.lower()
        ext_ok = (name.endswith(".csv") or name.endswith(".csv.gz")
                  or name.endswith(".dta") or name.endswith(".dta.gz")
                  or name.endswith(".parquet"))
        if not ext_ok:
            continue
        if "yearly" in name and ("1960_2024" in name or "1960-2024" in name):
            combined = path
            continue
        # Otherwise look for a 4-digit panel-window year in the filename.
        for token in name.replace("_", " ").replace("-", " ").replace(".", " ").split():
            if token.isdigit() and len(token) == 4:
                year = int(token)
                if YEAR_START <= year <= YEAR_END:
                    by_year[year] = path
                    break
    return combined, by_year


def _load_one(path: Path) -> pd.DataFrame:
    """Load one Kaplan year file, picking the column subset we need."""
    if path.name.lower().endswith(".dta") or path.name.lower().endswith(".dta.gz"):
        df = pd.read_stata(path, convert_categoricals=False)
    else:
        # Read whole file - Kaplan files are typically <500 MB uncompressed.
        df = pd.read_csv(path, low_memory=False)
    # Normalize column names to lowercase.
    df.columns = [c.lower() for c in df.columns]
    return df


def _county_fips_from(df: pd.DataFrame) -> pd.Series:
    """Build a 5-digit county FIPS string from whichever Kaplan column pair exists."""
    candidates_state  = ["fips_state_code", "fips_state", "state_fips_code", "state_fips"]
    candidates_county = ["fips_county_code", "fips_county", "county_fips_code", "county_fips"]
    sc = next((c for c in candidates_state if c in df.columns), None)
    cc = next((c for c in candidates_county if c in df.columns), None)
    if not sc or not cc:
        raise KeyError(
            f"Kaplan file is missing FIPS columns; tried {candidates_state} and {candidates_county}; "
            f"saw {list(df.columns)[:30]}..."
        )
    s = pd.to_numeric(df[sc], errors="coerce")
    c = pd.to_numeric(df[cc], errors="coerce")
    out = (s.astype("Int64").astype(str).str.zfill(2)
           + c.astype("Int64").astype(str).str.zfill(3))
    out[s.isna() | c.isna()] = pd.NA
    return out


def _year_from(df: pd.DataFrame, fallback: int) -> pd.Series:
    if "year" in df.columns:
        return pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    return pd.Series([fallback] * len(df), index=df.index, dtype="Int64")


def aggregate_year(path: Path, year: int, dropped_log: list) -> pd.DataFrame:
    df = _load_one(path)
    if df.empty:
        return pd.DataFrame()
    df["county_fips"] = _county_fips_from(df)
    df["year_col"] = _year_from(df, year)
    df = df[df["year_col"] == year]
    # Track and drop rows missing county FIPS (these are non-geocoded agencies,
    # e.g., FBI/DEA/college PDs whose ORI doesn't live in any county).
    no_fips = df["county_fips"].isna()
    if no_fips.any():
        dropped_log.append(OrderedDict([
            ("year", year),
            ("source_file", path.name),
            ("rows_no_county_fips", int(no_fips.sum())),
            ("note", "agencies with missing county FIPS (federal, tribal, or unmatched)"),
        ]))
    df = df[~no_fips]

    keep = [c for c in KAPLAN_OFFENSE_COLUMNS if c in df.columns]
    if not keep:
        raise KeyError(
            f"None of {KAPLAN_OFFENSE_COLUMNS} found in Kaplan file {path.name}; "
            f"saw {[c for c in df.columns if c.startswith('actual_')][:10]}..."
        )
    g = df.groupby("county_fips")[keep].sum(min_count=1)
    g["year"] = year
    g = g.reset_index().rename(columns=RENAME_OUT)
    return g


def aggregate_combined(path: Path, dropped_log: list) -> pd.DataFrame:
    """Read one big concatenated yearly file (the usual V22 distribution),
    keeping only the panel window and the columns we need."""
    needed = (["ori", "year", "fips_state_code", "fips_county_code"]
              + KAPLAN_OFFENSE_COLUMNS)
    print(f"  Reading {path.name} (large file - reading in chunks) ...", flush=True)
    chunks = pd.read_csv(
        path,
        usecols=lambda c: c in needed,
        dtype={"fips_state_code": "Int64", "fips_county_code": "Int64",
               "year": "Int64"},
        chunksize=200_000,
        low_memory=False,
    )
    pieces = []
    for chunk in chunks:
        chunk = chunk[(chunk["year"] >= YEAR_START) & (chunk["year"] <= YEAR_END)]
        if chunk.empty:
            continue
        pieces.append(chunk)
    df = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
    print(f"  Loaded {len(df):,} agency-year rows in window")

    df["county_fips"] = (df["fips_state_code"].astype("Int64").astype(str).str.zfill(2)
                         + df["fips_county_code"].astype("Int64").astype(str).str.zfill(3))
    no_fips = df["fips_state_code"].isna() | df["fips_county_code"].isna()
    if no_fips.any():
        for yr in df.loc[no_fips, "year"].unique():
            n = int(((df["year"] == yr) & no_fips).sum())
            dropped_log.append(OrderedDict([
                ("year", int(yr)),
                ("source_file", path.name),
                ("rows_no_county_fips", n),
                ("note", "agencies with missing county FIPS (federal, tribal, college, transit, etc.)"),
            ]))
        df = df[~no_fips]

    keep = [c for c in KAPLAN_OFFENSE_COLUMNS if c in df.columns]
    if not keep:
        raise KeyError(
            f"None of {KAPLAN_OFFENSE_COLUMNS} found in {path.name}; "
            f"actual_* columns present: "
            f"{[c for c in df.columns if c.startswith('actual_')][:10]}"
        )

    # Apply FIPS bridge so the canonical (modern) codes match the rest of the
    # county panel. Has to happen BEFORE groupby so renamed rows aggregate with
    # any existing modern-FIPS rows for the same place.
    for src, dst in KAPLAN_FIPS_RENAMES.items():
        df.loc[df["county_fips"] == src, "county_fips"] = dst

    g = (df.groupby(["county_fips", "year"], as_index=False)[keep]
            .sum(min_count=1))
    return g.rename(columns=RENAME_OUT)


def main() -> None:
    combined, files = discover_data()
    dropped_log: list = []
    if combined is not None:
        print(f"Using combined file: {combined.relative_to(KAPLAN.parent)}")
        long = aggregate_combined(combined, dropped_log)
    elif files:
        print(f"Found {len(files)} Kaplan year files: {sorted(files)}")
        pieces: list = []
        for year, path in sorted(files.items()):
            print(f"  {year}: {path.name} ...", end=" ", flush=True)
            sub = aggregate_year(path, year, dropped_log)
            print(f"{len(sub):,} county rows")
            pieces.append(sub)
        long = pd.concat(pieces, ignore_index=True)
    else:
        raise SystemExit(
            f"No Kaplan files matched in {KAPLAN}. Expected either a single "
            "yearly_1960_2024 file or per-year CSV/DTA files."
        )

    # Attach county population from the existing county panel for rate denominators.
    panel = pd.read_csv(PROC / "county_panel_2009_2024.csv",
                        dtype={"county_fips": str, "state_fips": str})
    pop = panel[["county_fips", "year", "population"]]
    long = long.merge(pop, on=["county_fips", "year"], how="left")

    # Compute per-100k rates for the count columns (skip arson and any that
    # are themselves count totals over multiple categories).
    rate_cols_in = [
        "county_murder", "county_robbery", "county_rape", "county_aggravated_assault",
        "county_burglary", "county_larceny", "county_motor_vehicle_theft",
        "county_violent_crime", "county_property_crime",
    ]
    for c in rate_cols_in:
        if c in long.columns:
            long[c + "_rate"] = long[c] / long["population"].replace(0, np.nan) * 1e5

    # Coverage report.
    long_path = PROC / "county_crime_2009_2024.csv"
    long.sort_values(["county_fips", "year"]).to_csv(long_path, index=False)

    coverage = []
    cols_for_cov = [c for c in long.columns if c not in ("county_fips", "year", "population")]
    for c in cols_for_cov:
        nn = int(long[c].notna().sum())
        coverage.append(OrderedDict([
            ("variable", c),
            ("non_null", nn),
            ("rows_total", len(long)),
            ("coverage_pct", round(100 * nn / len(long), 2) if len(long) else 0.0),
        ]))
    pd.DataFrame(coverage).to_csv(PROC / "county_crime_coverage.csv", index=False)
    pd.DataFrame(dropped_log).to_csv(PROC / "county_crime_dropped_agencies.csv", index=False)

    print(f"\nWrote {long_path.relative_to(ROOT)}: {len(long):,} county-year rows")
    print(f"      {(PROC / 'county_crime_coverage.csv').relative_to(ROOT)}")
    print(f"      {(PROC / 'county_crime_dropped_agencies.csv').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
