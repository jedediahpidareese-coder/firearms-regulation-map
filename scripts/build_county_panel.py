"""Phase 1 of the county-year panel build.

Produces a balanced county-year panel for 2009-2024 with:

- Total resident population from Census PEP
  (intercensal 2000-2010 totals for 2009; PEP 2010-2019 vintage for 2010-2019;
   PEP 2020-2024 vintage for 2020-2024).
- Small Area Income and Poverty Estimates (SAIPE) from the per-year XLS files
  for median household income and the all-ages poverty rate.
- State firearm laws joined down from the existing balanced state panel.

FIPS bridge (renames preserved as the post-2014 canonical FIPS):

- AK Wade Hampton (02270) -> Kusilvak (02158), effective 2015.
- SD Shannon (46113) -> Oglala Lakota (46102), effective 2015.
- VA Bedford City (51515) is dissolved into Bedford County (51019) starting 2013;
  pre-2013 city values are added to the county before merging.

Dropped from this v1 panel (documented below):

- Connecticut (state FIPS 09): the 2022 reorganization replaced 8 historical
  counties with 9 planning regions whose geometries are not coterminous, so
  there is no clean 2009-2024 county time series. CT will return in a later
  pass with an explicit pre/post-2022 bridge or a population-weighted
  apportionment to the 8 historical counties.

Outputs:

    data/processed/county_panel_2009_2024.csv
    data/processed/county_panel_balance.csv
    data/processed/county_panel_coverage.csv
    data/processed/county_panel_dropped.csv
    data/processed/county_variable_dictionary.csv
    data/processed/county_fips_bridge.csv
"""

from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
COUNTY = DATA / "county"
PROC = DATA / "processed"

YEAR_START, YEAR_END = 2009, 2024
YEARS = list(range(YEAR_START, YEAR_END + 1))

# CPI-U all-urban annual average, used to deflate SAIPE income to 2024 dollars.
# Values are BLS CPIAUCNS annual averages (rounded to 2 decimals); 2024 = base.
CPI_2024 = 313.689
CPI_BY_YEAR = {
    2009: 214.537, 2010: 218.056, 2011: 224.939, 2012: 229.594,
    2013: 232.957, 2014: 236.736, 2015: 237.017, 2016: 240.007,
    2017: 245.120, 2018: 251.107, 2019: 255.657, 2020: 258.811,
    2021: 270.970, 2022: 292.655, 2023: 304.702, 2024: 313.689,
}

# FIPS rename bridge: source FIPS -> canonical FIPS (modern).
FIPS_RENAMES = {
    "02270": "02158",  # AK Wade Hampton -> Kusilvak (2015)
    "46113": "46102",  # SD Shannon -> Oglala Lakota (2015)
}

# VA Bedford City absorbed into Bedford County in 2013; sum city into county.
BEDFORD_CITY = "51515"
BEDFORD_COUNTY = "51019"

# CT 2022 reorganization. Old county FIPS:
CT_OLD = {"09001", "09003", "09005", "09007", "09009", "09011", "09013", "09015"}
# New planning region FIPS (2022+):
CT_NEW = {"09110", "09120", "09130", "09140", "09150", "09160", "09170", "09190", "09180"}
DROP_FIPS = CT_OLD | CT_NEW


def make_fips(state, county) -> str:
    return f"{int(state):02d}{int(county):03d}"


# --------------------- PEP population loading ---------------------

def load_pep_population() -> pd.DataFrame:
    """Return one row per (county_fips, year) with `population`, 2009-2024.

    Reads three vintages and concatenates; vintage overlaps are resolved by
    preferring the newer vintage for shared years (none in our setup since
    each vintage owns its window).
    """
    pep_2009 = pd.read_csv(COUNTY / "co-est00int-tot.csv", encoding="latin1")
    pep_2019 = pd.read_csv(COUNTY / "co-est2019-alldata.csv", encoding="latin1")
    pep_2024 = pd.read_csv(COUNTY / "co-est2024-alldata.csv", encoding="latin1")

    rows = []

    # 2009 from intercensal 2000-2010 (county level, SUMLEV == 50)
    p09 = pep_2009.loc[pep_2009["SUMLEV"] == 50].copy()
    p09["county_fips"] = p09.apply(lambda r: make_fips(r["STATE"], r["COUNTY"]), axis=1)
    p09["state_fips"] = p09["STATE"].astype(str).str.zfill(2)
    p09["county_name"] = p09["CTYNAME"]
    p09["state_name"] = p09["STNAME"]
    p09 = p09[["county_fips", "state_fips", "county_name", "state_name", "POPESTIMATE2009"]]
    p09 = p09.rename(columns={"POPESTIMATE2009": "population"}).assign(year=2009)
    rows.append(p09)

    # 2010-2019 from PEP 2010-2019
    p19 = pep_2019.loc[pep_2019["SUMLEV"] == 50].copy()
    p19["county_fips"] = p19.apply(lambda r: make_fips(r["STATE"], r["COUNTY"]), axis=1)
    p19["state_fips"] = p19["STATE"].astype(str).str.zfill(2)
    for yr in range(2010, 2020):
        col = f"POPESTIMATE{yr}"
        sub = p19[["county_fips", "state_fips", "CTYNAME", "STNAME", col]].rename(
            columns={col: "population", "CTYNAME": "county_name", "STNAME": "state_name"}
        )
        sub["year"] = yr
        rows.append(sub)

    # 2020-2024 from PEP 2020-2024
    p24 = pep_2024.loc[pep_2024["SUMLEV"] == 50].copy()
    p24["county_fips"] = p24.apply(lambda r: make_fips(r["STATE"], r["COUNTY"]), axis=1)
    p24["state_fips"] = p24["STATE"].astype(str).str.zfill(2)
    for yr in range(2020, 2025):
        col = f"POPESTIMATE{yr}"
        sub = p24[["county_fips", "state_fips", "CTYNAME", "STNAME", col]].rename(
            columns={col: "population", "CTYNAME": "county_name", "STNAME": "state_name"}
        )
        sub["year"] = yr
        rows.append(sub)

    pop = pd.concat(rows, ignore_index=True)
    return pop[["county_fips", "state_fips", "year", "county_name", "state_name", "population"]]


# --------------------- SAIPE loading -----------------------------

# Column-name harmonization across SAIPE vintages.
SAIPE_COLUMN_ALIASES = {
    "state_fips":  ["State FIPS Code", "State FIPS", "STATE", "stateFIPS"],
    "county_fips": ["County FIPS Code", "County FIPS", "COUNTY", "countyFIPS"],
    "name":        ["Name", "County Name"],
    "median_hh_income": [
        "Median Household Income",
        "Median Household Income in Dollars",
        "Estimate of Median Household Income",
    ],
    "poverty_pct_all_ages": [
        "Poverty Percent, All Ages",
        "Poverty Percent All Ages",
        "Estimate Percent of People of All Ages in Poverty",
    ],
}


def _harmonize_saipe(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    cols = list(df.columns)
    for canon, aliases in SAIPE_COLUMN_ALIASES.items():
        match = next((c for c in cols if c in aliases), None)
        if match is None:
            raise KeyError(f"SAIPE: missing column for {canon}; saw {cols[:8]}...")
        out[canon] = df[match]
    return out


def _try_read_saipe(path: Path) -> pd.DataFrame:
    """SAIPE files for 2009 use header in row 3 (skiprows=2); 2010+ use rows 3+4
    (skiprows=3). Try both and return the one whose column names harmonize."""
    for skip in (3, 2):
        try:
            df = pd.read_excel(path, skiprows=skip)
            return _harmonize_saipe(df)
        except KeyError:
            continue
    raise RuntimeError(f"Could not parse {path.name} with either header layout")


def load_saipe() -> pd.DataFrame:
    rows = []
    for yr in YEARS:
        yy = f"{yr % 100:02d}"
        path = COUNTY / f"saipe-est{yy}all.xls"
        if not path.exists():
            print(f"  WARN: missing {path.name}; skipping {yr}")
            continue
        df = _try_read_saipe(path)
        # Drop national (state_fips==0, county_fips==0) and state (county_fips==0) rows.
        df = df.copy()
        df["state_fips"] = pd.to_numeric(df["state_fips"], errors="coerce").astype("Int64")
        df["county_fips"] = pd.to_numeric(df["county_fips"], errors="coerce").astype("Int64")
        df = df.dropna(subset=["state_fips", "county_fips"])
        df = df[(df["state_fips"] > 0) & (df["county_fips"] > 0)]
        df["county_fips"] = df.apply(
            lambda r: make_fips(r["state_fips"], r["county_fips"]), axis=1
        )
        df["state_fips"] = df["state_fips"].apply(lambda v: f"{int(v):02d}")
        df["year"] = yr
        df["median_hh_income"] = pd.to_numeric(df["median_hh_income"], errors="coerce")
        df["poverty_pct_all_ages"] = pd.to_numeric(df["poverty_pct_all_ages"], errors="coerce")
        rows.append(df[["county_fips", "year",
                        "median_hh_income", "poverty_pct_all_ages"]])
    out = pd.concat(rows, ignore_index=True)
    return out


# --------------------- State laws -------------------------------

def load_state_laws() -> pd.DataFrame:
    """Pull the state-year law panel and prep for joining onto counties."""
    df = pd.read_csv(PROC / "panel_core_1979_2024.csv")
    state_to_fips = {
        "AL":"01","AK":"02","AZ":"04","AR":"05","CA":"06","CO":"08","CT":"09","DE":"10",
        "DC":"11","FL":"12","GA":"13","HI":"15","ID":"16","IL":"17","IN":"18","IA":"19",
        "KS":"20","KY":"21","LA":"22","ME":"23","MD":"24","MA":"25","MI":"26","MN":"27",
        "MS":"28","MO":"29","MT":"30","NE":"31","NV":"32","NH":"33","NJ":"34","NM":"35",
        "NY":"36","NC":"37","ND":"38","OH":"39","OK":"40","OR":"41","PA":"42","RI":"44",
        "SC":"45","SD":"46","TN":"47","TX":"48","UT":"49","VT":"50","VA":"51","WA":"53",
        "WV":"54","WI":"55","WY":"56",
    }
    df["state_fips"] = df["state_abbr"].map(state_to_fips)
    df = df[df["state_fips"].notna()]
    keep = ["state_fips", "year", "lawtotal"] + [c for c in [
        "universal", "magazine", "assault", "gvro", "locked", "permitconcealed",
        "mayissue", "waiting", "onepermonth", "mcdvsurrender", "permit",
    ] if c in df.columns]
    df = df[keep].copy()
    df = df.rename(columns={c: f"law_{c}" if c != "lawtotal" else "lawtotal"
                            for c in keep if c not in ("state_fips", "year", "lawtotal")})
    return df[df["year"].isin(YEARS)]


# --------------------- FIPS bridge -------------------------------

def apply_fips_bridge(pop: pd.DataFrame, saipe: pd.DataFrame):
    """Apply documented renames; return bridged copies plus the bridge log."""
    log_rows = []

    def remap(df: pd.DataFrame, name: str):
        df = df.copy()
        for src, dst in FIPS_RENAMES.items():
            mask = df["county_fips"] == src
            n = int(mask.sum())
            if n:
                df.loc[mask, "county_fips"] = dst
                log_rows.append(OrderedDict([
                    ("source_fips", src), ("canonical_fips", dst),
                    ("rule", "rename"), ("rows_remapped", n), ("dataset", name),
                ]))
        # VA Bedford City: aggregate into Bedford County for pre-2013 rows.
        bedford_mask = df["county_fips"] == BEDFORD_CITY
        if bedford_mask.any():
            df.loc[bedford_mask, "county_fips"] = BEDFORD_COUNTY
            log_rows.append(OrderedDict([
                ("source_fips", BEDFORD_CITY), ("canonical_fips", BEDFORD_COUNTY),
                ("rule", "absorb"), ("rows_remapped", int(bedford_mask.sum())),
                ("dataset", name),
            ]))
        # Drop CT entirely (will return with bridge in a later pass).
        ct_mask = df["county_fips"].isin(DROP_FIPS)
        if ct_mask.any():
            log_rows.append(OrderedDict([
                ("source_fips", "CT (all)"), ("canonical_fips", "DROPPED"),
                ("rule", "drop_ct_2022_reorg"), ("rows_remapped", int(ct_mask.sum())),
                ("dataset", name),
            ]))
            df = df[~ct_mask]
        return df

    pop2 = remap(pop, "PEP")
    saipe2 = remap(saipe, "SAIPE")
    # Aggregate any rows that now share a (county_fips, year) after remap (Bedford).
    pop2 = (pop2.groupby(["county_fips", "year"], as_index=False)
                  .agg({"state_fips": "first", "county_name": "first",
                        "state_name": "first", "population": "sum"}))
    saipe2 = saipe2.groupby(["county_fips", "year"], as_index=False).agg({
        "median_hh_income": "mean", "poverty_pct_all_ages": "mean",
    })
    bridge_log = pd.DataFrame(log_rows)
    return pop2, saipe2, bridge_log


# --------------------- Panel build -------------------------------

def build_panel():
    print("Loading PEP population ...")
    pop = load_pep_population()
    print(f"  PEP rows: {len(pop):,} across {pop['county_fips'].nunique()} counties")

    print("Loading SAIPE income / poverty ...")
    saipe = load_saipe()
    print(f"  SAIPE rows: {len(saipe):,} across {saipe['county_fips'].nunique()} counties")

    print("Applying FIPS bridge (AK, SD, VA Bedford; dropping CT) ...")
    pop, saipe, bridge_log = apply_fips_bridge(pop, saipe)
    bridge_log.to_csv(PROC / "county_fips_bridge.csv", index=False)
    print(f"  bridge log rows: {len(bridge_log)}")

    print("Loading state laws ...")
    laws = load_state_laws()
    print(f"  laws rows (state-year, in window): {len(laws):,}")

    # Build the canonical (county_fips, year) cross product on the intersection
    # of counties that are PRESENT in PEP for ALL years in the window.
    counties_per_year = pop.groupby("county_fips")["year"].nunique()
    full_counties = counties_per_year[counties_per_year == len(YEARS)].index.tolist()
    print(f"  counties with full {YEAR_START}-{YEAR_END} coverage: {len(full_counties):,}")

    base = pd.MultiIndex.from_product(
        [sorted(full_counties), YEARS], names=["county_fips", "year"]
    ).to_frame(index=False)

    # Attach population (and county/state names from PEP).
    base = base.merge(pop, on=["county_fips", "year"], how="left")

    # Attach SAIPE.
    base = base.merge(saipe, on=["county_fips", "year"], how="left")

    # Compute real income (2024 dollars) using CPI-U.
    base["median_hh_income_real_2024"] = base.apply(
        lambda r: r["median_hh_income"] * (CPI_2024 / CPI_BY_YEAR[r["year"]])
                  if pd.notna(r["median_hh_income"]) else np.nan,
        axis=1,
    )

    # Attach state laws via state_fips + year.
    base = base.merge(laws, on=["state_fips", "year"], how="left")

    # Sanity checks.
    rows_actual = len(base)
    rows_expected = len(full_counties) * len(YEARS)
    states = base["state_fips"].nunique()
    counties = base["county_fips"].nunique()
    is_balanced = (rows_actual == rows_expected)

    print(f"\nPanel: {rows_actual:,} rows ({rows_expected:,} expected); "
          f"{counties:,} counties; {states} states+DC; "
          f"balanced={is_balanced}")

    # Coverage of each non-key column.
    coverage = []
    for col in base.columns:
        if col in {"county_fips", "year", "state_fips",
                   "county_name", "state_name"}:
            continue
        nn = int(base[col].notna().sum())
        coverage.append(OrderedDict([
            ("variable", col),
            ("non_null", nn),
            ("rows_total", rows_actual),
            ("coverage_pct", round(100 * nn / rows_actual, 2)),
        ]))
    pd.DataFrame(coverage).to_csv(PROC / "county_panel_coverage.csv", index=False)

    pd.DataFrame([OrderedDict([
        ("panel", "county_panel_2009_2024"),
        ("year_range", f"{YEAR_START}-{YEAR_END}"),
        ("rows", rows_actual),
        ("rows_expected", rows_expected),
        ("counties", counties),
        ("states_plus_dc", states),
        ("variables", base.shape[1]),
        ("balanced", is_balanced),
    ])]).to_csv(PROC / "county_panel_balance.csv", index=False)

    # Document any counties that exist in SOME years but not all (dropped).
    excluded = counties_per_year[counties_per_year != len(YEARS)].reset_index()
    excluded.columns = ["county_fips", "years_observed"]
    excluded.to_csv(PROC / "county_panel_dropped.csv", index=False)

    # Variable dictionary.
    var_dict = pd.DataFrame([
        ("county_fips", "5-digit county FIPS (state FIPS + county FIPS); modern canonical."),
        ("state_fips", "2-digit state FIPS."),
        ("year", "Calendar year."),
        ("county_name", "County name from PEP."),
        ("state_name", "State name from PEP."),
        ("population", "Annual resident population from Census PEP (intercensal 2009; vintage 2010-2019 PEP for 2010-2019; vintage 2020-2024 PEP for 2020-2024)."),
        ("median_hh_income", "Median household income (nominal USD) from Census SAIPE."),
        ("poverty_pct_all_ages", "All-ages poverty rate (percent) from Census SAIPE."),
        ("median_hh_income_real_2024", "Median household income deflated to 2024 USD using CPI-U annual averages."),
        ("lawtotal", "Tufts state firearm law count, joined down by state."),
        ("law_universal", "1 if state requires universal background checks (joined from state)."),
        ("law_magazine", "1 if state bans large-capacity magazines (joined from state)."),
        ("law_assault", "1 if state bans assault weapons (joined from state)."),
        ("law_gvro", "1 if state has a gun violence restraining order / red-flag law (joined from state)."),
        ("law_locked", "1 if state requires firearms be stored locked (joined from state)."),
        ("law_permitconcealed", "1 if state requires permit to carry concealed (joined from state)."),
        ("law_mayissue", "1 if state has may-issue concealed-carry permitting (joined from state)."),
        ("law_waiting", "1 if state requires waiting period for firearm purchases (joined from state)."),
        ("law_onepermonth", "1 if state has one-gun-per-month purchase limit (joined from state)."),
        ("law_mcdvsurrender", "1 if state mandates relinquishment for MCDV (joined from state)."),
        ("law_permit", "1 if state requires permit-to-purchase any firearm (joined from state)."),
    ], columns=["variable", "definition"])
    var_dict.to_csv(PROC / "county_variable_dictionary.csv", index=False)

    # Write panel.
    out_path = PROC / "county_panel_2009_2024.csv"
    base.to_csv(out_path, index=False)
    print(f"\nWrote: {out_path.relative_to(ROOT)}")
    print(f"        {(PROC / 'county_panel_balance.csv').relative_to(ROOT)}")
    print(f"        {(PROC / 'county_panel_coverage.csv').relative_to(ROOT)}")
    print(f"        {(PROC / 'county_panel_dropped.csv').relative_to(ROOT)}")
    print(f"        {(PROC / 'county_fips_bridge.csv').relative_to(ROOT)}")
    print(f"        {(PROC / 'county_variable_dictionary.csv').relative_to(ROOT)}")


if __name__ == "__main__":
    build_panel()
