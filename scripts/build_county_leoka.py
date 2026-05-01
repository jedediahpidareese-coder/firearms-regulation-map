"""Phase 4 — county-year LEOKA / sworn-officer layer (2009–2024).

Companion to scripts/build_state_cj_controls.py. Builds the one CJ
posture variable that is observed at county grain rather than imputed
from state averages: full-time sworn (peace-officer-status) law-
enforcement personnel per 100,000 residents.

Source. Jacob Kaplan's openICPSR project 102180 ("Uniform Crime
Reporting Program Data: Police Employee (LEOKA) Data, 1960–202X").
openICPSR requires a free user account and login to download; we do
NOT scrape it.

Usage. Drop the openICPSR project 102180 .zip into
data/county/kaplan_leoka/ as-is — this script streams the inner
year-aggregated CSV directly from the zip via Python's zipfile module
without unzipping. If no zip is present, the script writes a
placeholder output (NaN officer columns) so downstream code can join
without breaking.

The other three Tier 1 controls (imprisonment_rate,
police_expenditure_per_capita_real_2024, has_death_penalty,
executions_count) are STATE-level only and will be joined to the
county panel via state_fips at analysis time.

Outputs:
    data/processed/county_cj_controls_2009_2024.csv
"""

from __future__ import annotations

import io
import zipfile
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
COUNTY = DATA / "county"
PROC = DATA / "processed"
LEOKA_DIR = COUNTY / "kaplan_leoka"

YEAR_START, YEAR_END = 2009, 2024
YEARS = list(range(YEAR_START, YEAR_END + 1))


def make_fips(state, county) -> str:
    return f"{int(state):02d}{int(county):03d}"


def load_county_population() -> pd.DataFrame:
    """Use the county_panel population already produced by
    scripts/build_county_panel.py as the denominator."""
    panel = pd.read_csv(
        PROC / "county_panel_2009_2024.csv",
        usecols=["county_fips", "state_fips", "year", "population"],
        dtype={"county_fips": str, "state_fips": str},
    )
    return panel


# ---------------------------------------------------------------------
# Kaplan LEOKA / Police Employee data (placeholder)
# ---------------------------------------------------------------------

# Expected schema (openICPSR project 102180):
#   ori, ori9, agency_name, state, state_abb, year, fips_state_code,
#   fips_county_code, fips_state_county_code, agency_type,
#   total_employees, total_male_officers, total_female_officers,
#   total_officers, total_male_civilians, total_female_civilians,
#   total_civilians, ...
# (See Kaplan's openICPSR project 102180 codebook for the exact list.)

KAPLAN_LEOKA_OFFICER_COLS = [
    "total_employees_officers",   # actual column in openICPSR project 102180 V15
    # Fallback names in case future Kaplan vintages rename:
    "total_officers",
    "officers_total",
    "sworn_officers",
]


def _open_inner_csv(outer_zip: Path):
    """Yield a (csv_filename, file-handle) pair for the LEOKA yearly CSV,
    handling the openICPSR project 102180 nested-zip layout:

        102180-V15.zip
        +-- LEOKA_csv_1960_2024_year.zip          (CSV-format year-aggregated bundle)
            +-- leoka_yearly_1960_2024.csv        (~1 GB uncompressed)

    The inner-zip bytes (~30 MB compressed) are read into memory; the
    inner CSV is streamed in chunks via pandas. If the user has already
    extracted a loose CSV in LEOKA_DIR, that is used instead.
    """
    # Prefer a loose extracted CSV if the user already unzipped:
    loose = (list(LEOKA_DIR.rglob("*employ*yearly*.csv")) +
             list(LEOKA_DIR.rglob("*leoka*yearly*.csv")) +
             list(LEOKA_DIR.rglob("*police_employ*.csv")))
    if loose:
        path = loose[0]
        print(f"  Reading loose Kaplan LEOKA file: {path.name}")
        return path.name, open(path, "rb"), None  # caller closes

    # Otherwise traverse the openICPSR nested zip.
    with zipfile.ZipFile(outer_zip) as outer:
        names = outer.namelist()
        inner_name = next(
            (n for n in names if n.lower().endswith(".zip")
             and "csv" in n.lower() and "year" in n.lower()),
            None,
        )
        if inner_name is None:
            raise RuntimeError(
                f"{outer_zip.name} contains no *csv*year*.zip member; "
                f"saw {names}"
            )
        print(f"  Found nested year-CSV zip: {inner_name}")
        inner_bytes = outer.read(inner_name)

    inner_buf = io.BytesIO(inner_bytes)
    inner = zipfile.ZipFile(inner_buf)  # caller closes
    csv_name = next(
        (n for n in inner.namelist() if n.lower().endswith(".csv")), None,
    )
    if csv_name is None:
        raise RuntimeError(
            f"{inner_name} contains no .csv member; saw {inner.namelist()}"
        )
    print(f"  Streaming inner CSV: {csv_name}")
    return csv_name, inner.open(csv_name), inner  # return handle + zipfile to keep alive


def find_kaplan_leoka_zip() -> Path | None:
    """Locate the openICPSR project 102180 outer .zip in LEOKA_DIR."""
    if not LEOKA_DIR.exists():
        return None
    zips = sorted(LEOKA_DIR.glob("*.zip"))
    return zips[0] if zips else None


def load_kaplan_leoka(year_start: int = 1960,
                      year_end: int = 2024) -> pd.DataFrame | None:
    """Return AGENCY-level sworn-officer counts (one row per ORI x year),
    filtered to [year_start, year_end]. The county and state rollups are
    done by the callers (main() filters/aggregates at county grain;
    state-level callers do their own grouping).
    """
    outer = find_kaplan_leoka_zip()
    if outer is None:
        return None
    csv_name, fh, owner_zip = _open_inner_csv(outer)
    try:
        # Read only the columns we need; the LEOKA CSV has 257 columns.
        usecols = (
            ["year", "fips_state_code", "fips_county_code", "state_abb"]
            + KAPLAN_LEOKA_OFFICER_COLS
        )
        # Pandas will skip usecols not present in the file.
        df_iter = pd.read_csv(
            io.TextIOWrapper(fh, encoding="latin1"),
            usecols=lambda c: c in usecols,
            dtype={"fips_state_code": "Int64", "fips_county_code": "Int64",
                   "year": "Int64"},
            low_memory=False,
            chunksize=200_000,
        )
        chunks = []
        for chunk in df_iter:
            chunk = chunk.loc[chunk["year"].between(year_start, year_end)]
            chunks.append(chunk)
        df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    finally:
        fh.close()
        if owner_zip is not None:
            owner_zip.close()

    if df.empty:
        return None

    officer_col = next(
        (c for c in KAPLAN_LEOKA_OFFICER_COLS if c in df.columns), None,
    )
    if officer_col is None:
        raise RuntimeError(
            f"LEOKA CSV has none of {KAPLAN_LEOKA_OFFICER_COLS}; "
            f"saw {list(df.columns)}"
        )

    # Build county_fips (drop rows missing either FIPS code).
    df = df.dropna(subset=["fips_state_code", "fips_county_code"]).copy()
    df["state_fips"] = df["fips_state_code"].astype(int).astype(str).str.zfill(2)
    df["county_fips_raw"] = (
        df["state_fips"]
        + df["fips_county_code"].astype(int).astype(str).str.zfill(3)
    )
    # Apply same FIPS bridge as build_county_crime.py
    fips_bridge = {"02270": "02158", "46113": "46102", "51515": "51019"}
    df["county_fips"] = df["county_fips_raw"].map(lambda f: fips_bridge.get(f, f))

    # Aggregate to county-year (sum across agencies within a county).
    out = (df.groupby(["county_fips", "state_fips", "year"], as_index=False)[officer_col]
             .sum()
             .rename(columns={officer_col: "county_sworn_officers"}))
    return out


# ---------------------------------------------------------------------
# Assemble
# ---------------------------------------------------------------------

def main() -> None:
    print("=== Building county CJ controls 2009–2024 ===")

    pop = load_county_population()
    print(f"  Loaded population for {pop['county_fips'].nunique()} counties "
          f"× {pop['year'].nunique()} years")

    leoka = load_kaplan_leoka()
    if leoka is None:
        print("  Kaplan LEOKA file not on disk. Writing placeholder output.")
        print("  -> needs manual download from openICPSR project 102180")
        # Build a placeholder: one row per (county_fips, year) with NaN officer count
        out = pop.copy()
        out["county_sworn_officers"] = np.nan
        out["county_sworn_officers_per_100k"] = np.nan
        out["has_county_sworn_officers"] = 0
    else:
        merged = pop.merge(leoka, on=["county_fips", "state_fips", "year"], how="left")
        merged["county_sworn_officers_per_100k"] = np.where(
            merged["population"].notna() & merged["county_sworn_officers"].notna(),
            merged["county_sworn_officers"] / merged["population"] * 100_000.0,
            np.nan,
        )
        merged["has_county_sworn_officers"] = merged[
            "county_sworn_officers_per_100k"].notna().astype(int)
        out = merged

    out_cols = [
        "county_fips", "state_fips", "year",
        "county_sworn_officers_per_100k",
        "county_sworn_officers",
        "population",
        "has_county_sworn_officers",
    ]
    out_path = PROC / "county_cj_controls_2009_2024.csv"
    out[out_cols].to_csv(out_path, index=False)

    print(f"\nWrote {out_path}")
    n_total = len(out)
    n_with = int(out["has_county_sworn_officers"].sum())
    print(f"  rows: {n_total}, with sworn-officer count: {n_with} "
          f"({100.0 * n_with / n_total:.1f}%)")

    # Also update state_cj_controls_*.csv with state-level sworn officers
    # (sum across counties within state, divide by state population). The
    # state file already exists from build_state_cj_controls.py with
    # placeholder NaN; we fill the sworn_officers_per_100k column in-place.
    if leoka is not None:
        update_state_cj_with_leoka(leoka)


def update_state_cj_with_leoka(leoka_county: pd.DataFrame) -> None:
    """Aggregate the LEOKA county-year sworn-officer data to state-year and
    fill the sworn_officers_per_100k column in
    data/processed/state_cj_controls_1979_2024.csv. Side effect: rewrites
    that file in place. Documented in data_appendix.md Section 2.13.4.
    """
    state_cj_path = PROC / "state_cj_controls_1979_2024.csv"
    if not state_cj_path.exists():
        print(f"\n  (skipping state-level update; {state_cj_path.name} not found)")
        return

    print("\nAggregating LEOKA to state-year and updating state_cj_controls ...")
    # Sum officers within state-year. Note: LEOKA county-year was filtered
    # to whatever year range load_kaplan_leoka was called with; default is
    # 1960-2024, which covers the state CJ panel's 1979-2024 fully.
    state_off = (leoka_county.groupby(["state_fips", "year"], as_index=False)
                 ["county_sworn_officers"].sum()
                 .rename(columns={"county_sworn_officers": "sworn_officers_state_total"}))

    state_cj = pd.read_csv(state_cj_path, dtype={"state_fips": str})
    # Drop the existing sworn-officers columns (they are placeholders).
    for c in ("sworn_officers_per_100k", "has_sworn_officers"):
        if c in state_cj.columns:
            state_cj = state_cj.drop(columns=c)

    merged = state_cj.merge(state_off, on=["state_fips", "year"], how="left")
    merged["sworn_officers_per_100k"] = np.where(
        merged["population"].notna() & merged["sworn_officers_state_total"].notna(),
        merged["sworn_officers_state_total"] / merged["population"] * 100_000.0,
        np.nan,
    )
    merged["has_sworn_officers"] = merged["sworn_officers_per_100k"].notna().astype(int)
    merged = merged.drop(columns=["sworn_officers_state_total"])

    merged.to_csv(state_cj_path, index=False)
    n_with = int(merged["has_sworn_officers"].sum())
    print(f"  Updated {state_cj_path.name}: {n_with}/{len(merged)} state-years "
          f"({100.0 * n_with / len(merged):.1f}%) now have sworn_officers_per_100k")


if __name__ == "__main__":
    main()
