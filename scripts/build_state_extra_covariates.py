"""Build three new state-year covariate files needed by the literature-
backed firearm-policy spec set (see outputs/rdd_diagnostics/
covariate_recommendations.md):

  1. data/processed/state_alcohol_per_capita_1977_2023.csv
     -- per-capita ethanol consumption, gallons (NIAAA Surveillance Report
        #122 or openICPSR project 105583).
        Source: user-downloaded into data/state_cj_raw/ as either
                openICPSR zip (preferred; clean CSV inside)
                or NIAAA SR-122 PDF (fallback; rotated tables).

  2. data/processed/state_drug_overdose_2003_2021.csv
     -- model-based drug-poisoning death rate per 100k by state-year.
        Aggregated from CDC NCHS NCHS-Drug-Poisoning-Mortality-by-County
        (data.cdc.gov/NCHS/NCHS-Drug-Poisoning-Mortality-by-County-
        United-Sta/rpvx-m2md), county-year 2003-2021.

  3. data/processed/state_religious_adherence_2020.csv
     -- religious adherents as a percentage of state population, 2020 only.
        Source: US Religion Census 2020 (ARDA / U.S. Religion Census /
        Association of Statisticians of American Religious Bodies).
        Slow-moving; treated as a state-level baseline. State FE absorbs
        most cross-cohort variation in the DiD specs.

The 2010/2000/1990/1980 RCMS data are NOT auto-downloaded here -- those
are paywalled or behind interactive forms on ARDA. If the user puts
historical Excel files into data/state_cj_raw/ matching the pattern
arda_*USRC*.xlsx, the 2020 loader will pick them up too.
"""

from __future__ import annotations

import io
import re
import zipfile
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "state_cj_raw"
PROC = ROOT / "data" / "processed"

# Two-letter postal codes used as the canonical state key elsewhere in
# the project (matches panel_core_augmented.csv `state_abbr`).
STATE_NAME_TO_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME",
    "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE",
    "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


# --------------------------------------------------------------------------
# 1) NIAAA: per-capita ethanol consumption from openICPSR project 105583
#    (preferred) or NIAAA Surveillance Report #122 PDF (fallback).
# --------------------------------------------------------------------------

def find_niaaa_zip() -> Path | None:
    """Locate the openICPSR project 105583 download in data/state_cj_raw/.
    The user drops it as-is (any filename ending in .zip)."""
    if not RAW.exists():
        return None
    for z in sorted(RAW.glob("*.zip")):
        try:
            with zipfile.ZipFile(z) as zf:
                # Must have at least one CSV mentioning alcohol or per-capita
                names = [n.lower() for n in zf.namelist()]
                if any("alcohol" in n or "ethanol" in n or "percapita" in n.replace("_","")
                       or "per_capita" in n or "consumption" in n for n in names):
                    return z
                # openICPSR project 105583 V5 ships as 105583-V5.zip
                if "105583" in z.name:
                    return z
        except zipfile.BadZipFile:
            continue
    return None


def parse_niaaa_zip(zip_path: Path) -> pd.DataFrame:
    """Parse the openICPSR project 105583 zip. Returns a long DataFrame
    with columns [state_abbr, year, alcohol_per_capita_ethanol_gallons].
    """
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        # Find the per-state per-capita CSV. openICPSR names vary; try
        # several patterns.
        cands = [n for n in names if n.lower().endswith(".csv")
                 and ("alcohol" in n.lower() or "consumption" in n.lower()
                      or "ethanol" in n.lower() or "state" in n.lower()
                      or "per_capita" in n.lower() or "percapita" in n.lower())]
        # Prefer ones with "per_capita" or "apparent" in the name (canonical
        # NIAAA naming convention)
        cands_pc = [n for n in cands if "per_capita" in n.lower() or "apparent" in n.lower()]
        chosen = (cands_pc + cands)[0] if cands else None
        if chosen is None:
            raise RuntimeError(
                f"{zip_path.name}: no CSV matching state/per-capita pattern; "
                f"contents: {names[:20]}"
            )
        print(f"  reading {chosen} from {zip_path.name}")
        df = pd.read_csv(io.BytesIO(zf.read(chosen)))
    return _normalize_niaaa_long(df)


def _normalize_niaaa_long(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize a NIAAA per-capita table to (state_abbr, year, val).
    Handles both wide (state x year columns) and long (state, year, val)
    formats.
    """
    cols_lower = {c.lower(): c for c in df.columns}
    # Detect wide vs long
    state_col = next((cols_lower[k] for k in ("state", "state_abbr", "geographic area")
                      if k in cols_lower), None)
    year_col = next((cols_lower[k] for k in ("year",) if k in cols_lower), None)
    eth_col = next((cols_lower[k] for k in (
        "ethanol_all_drinks_gallons_per_capita",  # openICPSR 105583 V5
        "ethanol", "per_capita_ethanol",
        "all_beverages_per_capita_ethanol",
        "per_capita_consumption",
        "all_beverages")
                    if k in cols_lower), None)
    if state_col is None:
        raise RuntimeError(f"NIAAA: no state column among {list(df.columns)[:10]}...")
    if year_col is not None and eth_col is not None:
        # Long format
        out = df[[state_col, year_col, eth_col]].copy()
        out.columns = ["state_name_or_abbr", "year", "alcohol_per_capita_ethanol_gallons"]
    else:
        # Wide: pivot to long. Year columns are 4-digit ints.
        year_cols = [c for c in df.columns if re.fullmatch(r"\d{4}", str(c))]
        if not year_cols:
            raise RuntimeError(f"NIAAA: no year columns recognized; saw {list(df.columns)[:10]}")
        out = df.melt(id_vars=[state_col], value_vars=year_cols,
                      var_name="year", value_name="alcohol_per_capita_ethanol_gallons")
        out = out.rename(columns={state_col: "state_name_or_abbr"})
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    # Map state name -> abbr; pass-through if already abbr; case-insensitive
    # name matching (openICPSR ships lowercase state names).
    NAME_LOWER = {k.lower(): v for k, v in STATE_NAME_TO_ABBR.items()}
    def _to_abbr(s):
        if not isinstance(s, str):
            return None
        s = s.strip()
        if len(s) == 2 and s.upper() == s:
            return s
        return STATE_NAME_TO_ABBR.get(s) or NAME_LOWER.get(s.lower())
    out["state_abbr"] = out["state_name_or_abbr"].map(_to_abbr)
    out = out.dropna(subset=["state_abbr", "year"])
    out["year"] = out["year"].astype(int)
    return out[["state_abbr", "year", "alcohol_per_capita_ethanol_gallons"]]


def build_alcohol_csv() -> bool:
    z = find_niaaa_zip()
    out_path = PROC / "state_alcohol_per_capita_1977_2023.csv"
    if z is None:
        # Could fall back to PDF parsing here; for now flag as missing.
        print("  ! NIAAA zip not found in data/state_cj_raw/. "
              "Drop openICPSR project 105583 zip to enable.")
        return False
    print(f"  parsing NIAAA zip {z.name}")
    df = parse_niaaa_zip(z)
    df = df.sort_values(["state_abbr", "year"]).reset_index(drop=True)
    df.to_csv(out_path, index=False)
    print(f"  wrote {out_path}: {df.shape[0]} rows; "
          f"{df.year.min()}-{df.year.max()}; {df.state_abbr.nunique()} states")
    return True


# --------------------------------------------------------------------------
# 2) CDC drug overdose: aggregate county-year to state-year
# --------------------------------------------------------------------------

def build_overdose_csv() -> bool:
    src = RAW / "cdc_drug_poisoning_county.csv"
    out_path = PROC / "state_drug_overdose_2003_2021.csv"
    if not src.exists():
        print(f"  ! {src.name} not found.")
        return False
    print(f"  reading {src.name}")
    df = pd.read_csv(src, dtype={"FIPS": str, "FIPS State": str})
    # Aggregate: deaths per county = rate × pop / 100k; sum to state; divide.
    df["deaths"] = df["Model-based Death Rate"] * df["Population"] / 100_000.0
    state = (df.groupby(["State", "Year"], as_index=False)
             .agg(deaths=("deaths", "sum"), population=("Population", "sum")))
    state["drug_overdose_per_100k"] = state["deaths"] / state["population"] * 100_000.0
    # CDC NCHS Drug-Poisoning-by-County uses full state names in the
    # "State" column; map to 2-letter postal abbreviation to match the
    # rest of the project.
    state["state_abbr"] = state["State"].map(STATE_NAME_TO_ABBR)
    state = state.dropna(subset=["state_abbr"])
    out = state[["state_abbr", "Year", "drug_overdose_per_100k"]].rename(
        columns={"Year": "year"})
    out = out.sort_values(["state_abbr", "year"]).reset_index(drop=True)
    out.to_csv(out_path, index=False)
    print(f"  wrote {out_path}: {len(out)} rows; "
          f"{out.year.min()}-{out.year.max()}; {out.state_abbr.nunique()} states")
    return True


# --------------------------------------------------------------------------
# 3) ARDA religion 2020 (state cross-section)
# --------------------------------------------------------------------------

def build_religion_csv() -> bool:
    src = RAW / "arda_2020_USRC_Summaries.xlsx"
    out_path = PROC / "state_religious_adherence_2020.csv"
    if not src.exists():
        print(f"  ! {src.name} not found.")
        return False
    print(f"  reading {src.name}")
    df = pd.read_excel(src, sheet_name="2020 State Summary")
    keep = [c for c in df.columns if c in (
        "State Code", "State Name", "2020 Population",
        "Adherents", "Adherents as % of Population")]
    df = df[keep].rename(columns={
        "State Name": "state_name",
        "2020 Population": "population_2020",
        "Adherents": "religion_adherents_2020",
        "Adherents as % of Population": "religion_adherents_pct_2020",
    })
    df["state_abbr"] = df["state_name"].map(STATE_NAME_TO_ABBR)
    df = df.dropna(subset=["state_abbr"])
    out = df[["state_abbr", "state_name", "population_2020",
              "religion_adherents_2020", "religion_adherents_pct_2020"]]
    out.to_csv(out_path, index=False)
    print(f"  wrote {out_path}: {len(out)} rows (state cross-section)")
    return True


# --------------------------------------------------------------------------

def main() -> None:
    PROC.mkdir(parents=True, exist_ok=True)
    print("=== Building state-year extra covariates ===")
    print("\n[1/3] NIAAA per-capita ethanol consumption ...")
    ok_alc = build_alcohol_csv()
    print("\n[2/3] CDC drug-overdose mortality (state aggregation) ...")
    ok_od = build_overdose_csv()
    print("\n[3/3] ARDA US Religion Census 2020 ...")
    ok_rel = build_religion_csv()
    print("\nSummary:")
    print(f"  alcohol:  {'OK' if ok_alc else 'PENDING (need NIAAA zip)'}")
    print(f"  overdose: {'OK' if ok_od else 'FAIL'}")
    print(f"  religion: {'OK' if ok_rel else 'FAIL'}")


if __name__ == "__main__":
    main()
