from __future__ import annotations

import json
import math
import re
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CRIME_REPAIRS_PATH = DATA_DIR / "manual_crime_repairs.csv"
HISTORICAL_DEMOGRAPHIC_DIR = DATA_DIR / "historical_demographics"


FRED_CPI_SERIES = "CPIAUCSL"
USER_AGENT = "Mozilla/5.0"
HISTORICAL_SASRH_URL_TEMPLATE = (
    "https://www2.census.gov/programs-surveys/popest/tables/1990-2000/state/asrh/sasrh{year_suffix}.txt"
)
STATE_POP_2000_2010_URL = (
    "https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/state/st-est00int-alldata.csv"
)
HISTORICAL_EDUCATION_URLS = {
    1999: "https://www2.census.gov/programs-surveys/demo/tables/educational-attainment/1999/p20-528/tab13.pdf",
    2000: "https://www2.census.gov/programs-surveys/demo/tables/educational-attainment/2000/p20-536/tab13.pdf",
    2001: "https://www2.census.gov/programs-surveys/demo/tables/educational-attainment/2001/cps-detailed-tables/tab13.xls",
    2002: "https://www2.census.gov/programs-surveys/demo/tables/educational-attainment/2002/cps-detailed-tables/tab13.xls",
    2003: "https://www2.census.gov/programs-surveys/demo/tables/educational-attainment/2003/p20-550/tab13.xls",
    2004: "https://www2.census.gov/programs-surveys/demo/tables/educational-attainment/2004/cps-detailed-tables/tab13.xls",
}
DEMOGRAPHIC_CONTROL_COLS = [
    "state",
    "state_abbr",
    "year",
    "controls_source",
    "median_hh_income_nominal",
    "median_hh_income_real_2024",
    "poverty_rate",
    "share_white_nh",
    "share_black_nh",
    "share_hispanic",
    "share_bachelors_plus",
    "share_male",
    "share_age_15_24",
    "share_age_25_44",
]


STATE_FIPS_TO_ABBR = {
    1: "AL",
    2: "AK",
    4: "AZ",
    5: "AR",
    6: "CA",
    8: "CO",
    9: "CT",
    10: "DE",
    11: "DC",
    12: "FL",
    13: "GA",
    15: "HI",
    16: "ID",
    17: "IL",
    18: "IN",
    19: "IA",
    20: "KS",
    21: "KY",
    22: "LA",
    23: "ME",
    24: "MD",
    25: "MA",
    26: "MI",
    27: "MN",
    28: "MS",
    29: "MO",
    30: "MT",
    31: "NE",
    32: "NV",
    33: "NH",
    34: "NJ",
    35: "NM",
    36: "NY",
    37: "NC",
    38: "ND",
    39: "OH",
    40: "OK",
    41: "OR",
    42: "PA",
    44: "RI",
    45: "SC",
    46: "SD",
    47: "TN",
    48: "TX",
    49: "UT",
    50: "VT",
    51: "VA",
    53: "WA",
    54: "WV",
    55: "WI",
    56: "WY",
}


LAW_CUSTOM_VARS = {
    "permitconcealed": "State requires a permit for concealed carry",
    "mayissue": "Concealed-carry permit issuance is discretionary (may-issue)",
    "gvro": "State has an extreme risk protection order / gun violence restraining order law",
    "magazine": "State bans large-capacity magazines",
    "assault": "State bans assault weapons",
    "universal": "Universal background checks required for all firearms",
    "universalh": "Universal background checks required for handguns",
    "waiting": "Waiting period required for firearm purchases",
    "onepermonth": "One-gun-per-month purchase limit",
    "mcdvsurrender": "Mandatory relinquishment for misdemeanor crime of domestic violence",
    "locked": "State has child access prevention / locked storage requirement",
}


CUSTOM_DICTIONARY_ROWS = [
    {
        "variable_name": "population",
        "group": "Crime / denominator",
        "label": "Population",
        "description": "Annual resident population used to construct crime rates.",
        "source": "FRED / Census state population",
    },
    {
        "variable_name": "violent_crime",
        "group": "Crime",
        "label": "Violent crime count",
        "description": "Total violent crime count.",
        "source": "OpenCrime / FBI Crime Data Explorer",
    },
    {
        "variable_name": "violent_rate",
        "group": "Crime",
        "label": "Violent crime rate",
        "description": "Violent crimes per 100,000 population, derived from violent crime counts and annual population.",
        "source": "Derived from crime counts and FRED / Census population",
    },
    {
        "variable_name": "homicide",
        "group": "Crime",
        "label": "Homicide count",
        "description": "Murder and nonnegligent manslaughter count.",
        "source": "OpenCrime / FBI Crime Data Explorer",
    },
    {
        "variable_name": "homicide_rate",
        "group": "Crime",
        "label": "Homicide rate",
        "description": "Homicides per 100,000 population.",
        "source": "OpenCrime / FBI Crime Data Explorer",
    },
    {
        "variable_name": "rape",
        "group": "Crime",
        "label": "Rape count",
        "description": "Reported rape count in the state crime series.",
        "source": "OpenCrime / FBI Crime Data Explorer",
    },
    {
        "variable_name": "robbery",
        "group": "Crime",
        "label": "Robbery count",
        "description": "Reported robbery count.",
        "source": "OpenCrime / FBI Crime Data Explorer",
    },
    {
        "variable_name": "aggravated_assault",
        "group": "Crime",
        "label": "Aggravated assault count",
        "description": "Reported aggravated assault count.",
        "source": "OpenCrime / FBI Crime Data Explorer",
    },
    {
        "variable_name": "property_crime",
        "group": "Crime",
        "label": "Property crime count",
        "description": "Total property crime count.",
        "source": "OpenCrime / FBI Crime Data Explorer",
    },
    {
        "variable_name": "property_rate",
        "group": "Crime",
        "label": "Property crime rate",
        "description": "Property crimes per 100,000 population, derived from property crime counts and annual population.",
        "source": "Derived from crime counts and FRED / Census population",
    },
    {
        "variable_name": "burglary",
        "group": "Crime",
        "label": "Burglary count",
        "description": "Reported burglary count.",
        "source": "OpenCrime / FBI Crime Data Explorer",
    },
    {
        "variable_name": "larceny",
        "group": "Crime",
        "label": "Larceny count",
        "description": "Reported larceny count.",
        "source": "OpenCrime / FBI Crime Data Explorer",
    },
    {
        "variable_name": "motor_vehicle_theft",
        "group": "Crime",
        "label": "Motor vehicle theft count",
        "description": "Reported motor vehicle theft count.",
        "source": "OpenCrime / FBI Crime Data Explorer",
    },
    {
        "variable_name": "unemployment_rate",
        "group": "Economic control",
        "label": "Annual average unemployment rate",
        "description": "Annual average of the monthly state unemployment rate.",
        "source": "FRED / BLS",
    },
    {
        "variable_name": "pcpi_nominal",
        "group": "Economic control",
        "label": "Per capita personal income (nominal)",
        "description": "Annual per capita personal income in current dollars.",
        "source": "FRED / BEA",
    },
    {
        "variable_name": "pcpi_real_2024",
        "group": "Economic control",
        "label": "Per capita personal income (2024 dollars)",
        "description": "Per capita personal income deflated to 2024 dollars using annual average CPI-U.",
        "source": "FRED / BEA / BLS CPI",
    },
    {
        "variable_name": "ln_population",
        "group": "Derived control",
        "label": "Log population",
        "description": "Natural log of population.",
        "source": "Derived from population",
    },
    {
        "variable_name": "ln_pcpi_real_2024",
        "group": "Derived control",
        "label": "Log real PCPI",
        "description": "Natural log of real per capita personal income in 2024 dollars.",
        "source": "Derived from pcpi_real_2024",
    },
    {
        "variable_name": "nics_total",
        "group": "Firearm market proxy",
        "label": "NICS total checks",
        "description": "Total annual NICS firearm background checks.",
        "source": "Data Liberation Project / FBI NICS",
    },
    {
        "variable_name": "nics_handgun",
        "group": "Firearm market proxy",
        "label": "NICS handgun checks",
        "description": "Annual NICS handgun checks.",
        "source": "Data Liberation Project / FBI NICS",
    },
    {
        "variable_name": "nics_long_gun",
        "group": "Firearm market proxy",
        "label": "NICS long-gun checks",
        "description": "Annual NICS long-gun checks.",
        "source": "Data Liberation Project / FBI NICS",
    },
    {
        "variable_name": "nics_multiple",
        "group": "Firearm market proxy",
        "label": "NICS multiple checks",
        "description": "Annual NICS multiple-firearm transaction checks.",
        "source": "Data Liberation Project / FBI NICS",
    },
    {
        "variable_name": "nics_permit",
        "group": "Firearm market proxy",
        "label": "NICS permit checks",
        "description": "Annual NICS permit checks.",
        "source": "Data Liberation Project / FBI NICS",
    },
    {
        "variable_name": "nics_permit_recheck",
        "group": "Firearm market proxy",
        "label": "NICS permit rechecks",
        "description": "Annual NICS permit rechecks.",
        "source": "Data Liberation Project / FBI NICS",
    },
    {
        "variable_name": "nics_other",
        "group": "Firearm market proxy",
        "label": "NICS other checks",
        "description": "Annual NICS 'other' checks.",
        "source": "Data Liberation Project / FBI NICS",
    },
    {
        "variable_name": "nics_total_per_100k",
        "group": "Firearm market proxy",
        "label": "NICS total checks per 100,000",
        "description": "Annual NICS total checks per 100,000 population.",
        "source": "Derived from NICS total checks and population",
    },
    {
        "variable_name": "median_hh_income_nominal",
        "group": "Demographic / economic control",
        "label": "Median household income (nominal)",
        "description": "Annual state median household income in current dollars.",
        "source": "SAIPE (1999-2004) / ACS (2005-2024)",
    },
    {
        "variable_name": "median_hh_income_real_2024",
        "group": "Demographic / economic control",
        "label": "Median household income (2024 dollars)",
        "description": "Median household income deflated to 2024 dollars using annual average CPI-U.",
        "source": "SAIPE / ACS / BLS CPI",
    },
    {
        "variable_name": "poverty_rate",
        "group": "Demographic / economic control",
        "label": "Poverty rate",
        "description": "Annual state poverty rate.",
        "source": "SAIPE (1999-2004) / ACS (2005-2024)",
    },
    {
        "variable_name": "share_white_nh",
        "group": "Demographic control",
        "label": "Share non-Hispanic White",
        "description": "Share of population that is non-Hispanic White alone.",
        "source": "Census population estimates (1999-2004) / ACS (2005-2024)",
    },
    {
        "variable_name": "share_black_nh",
        "group": "Demographic control",
        "label": "Share non-Hispanic Black",
        "description": "Share of population that is non-Hispanic Black alone.",
        "source": "Census population estimates (1999-2004) / ACS (2005-2024)",
    },
    {
        "variable_name": "share_hispanic",
        "group": "Demographic control",
        "label": "Share Hispanic",
        "description": "Share of population that is Hispanic or Latino of any race.",
        "source": "Census population estimates (1999-2004) / ACS (2005-2024)",
    },
    {
        "variable_name": "share_bachelors_plus",
        "group": "Demographic control",
        "label": "Share bachelor's degree or higher",
        "description": "Share of the education universe with a bachelor's degree or more.",
        "source": "CPS/Census state education tables (1999-2004) / ACS (2005-2024)",
    },
    {
        "variable_name": "share_male",
        "group": "Demographic control",
        "label": "Share male",
        "description": "Share of population that is male.",
        "source": "Census population estimates (1999-2004) / ACS (2005-2024)",
    },
    {
        "variable_name": "share_age_15_24",
        "group": "Demographic control",
        "label": "Share age 15-24",
        "description": "Share of population age 15 to 24.",
        "source": "Census population estimates (1999-2004) / ACS (2005-2024)",
    },
    {
        "variable_name": "share_age_25_44",
        "group": "Demographic control",
        "label": "Share age 25-44",
        "description": "Share of population age 25 to 44.",
        "source": "Census population estimates (1999-2004) / ACS (2005-2024)",
    },
    {
        "variable_name": "controls_source",
        "group": "Metadata",
        "label": "Demographic controls source",
        "description": "Source family used for the demographic control bundle: historical mix for 1999-2004, ACS 1-year for most later years, and ACS 5-year for 2020.",
        "source": "Census API / Census population estimates / CPS state tables",
    },
]


def fetch_json(url: str) -> list | dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def ensure_download(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=240) as response:
        destination.write_bytes(response.read())
    return destination


def read_fred_series(series_id: str) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    df = pd.read_csv(url)
    value_col = [c for c in df.columns if c != "DATE" and c != "observation_date"]
    if not value_col:
        raise ValueError(f"No value column returned for {series_id}")
    date_col = "DATE" if "DATE" in df.columns else "observation_date"
    df = df.rename(columns={date_col: "date", value_col[0]: "value"})
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def flatten_opencrime_state_trends(path: Path) -> pd.DataFrame:
    records = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for item in records:
        for year_row in item["years"]:
            rows.append(
                {
                    "state_abbr": item["abbr"],
                    "state": item["name"],
                    "year": int(year_row["year"]),
                    "population": year_row.get("population"),
                    "violent_crime": year_row.get("violentCrime"),
                    "violent_rate": year_row.get("violentRate"),
                    "homicide": year_row.get("homicide"),
                    "homicide_rate": year_row.get("homicideRate"),
                    "rape": year_row.get("rape"),
                    "robbery": year_row.get("robbery"),
                    "aggravated_assault": year_row.get("aggravatedAssault"),
                    "property_crime": year_row.get("propertyCrime"),
                    "property_rate": year_row.get("propertyRate"),
                    "burglary": year_row.get("burglary"),
                    "larceny": year_row.get("larceny"),
                    "motor_vehicle_theft": year_row.get("motorVehicleTheft"),
                }
            )
    return pd.DataFrame(rows)


def clean_state_crime(
    opencrime_path: Path,
    repairs_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    crime = flatten_opencrime_state_trends(opencrime_path)
    numeric_cols = [c for c in crime.columns if c not in {"state", "state_abbr", "year"}]
    for col in numeric_cols:
        crime[col] = pd.to_numeric(crime[col], errors="coerce")

    repair_log_rows: list[dict] = []
    duplicate_keys = ["state_abbr", "year"]

    nc_2022_mask = (crime["state_abbr"] == "NC") & (crime["year"] == 2022)
    nd_2022_mask = (crime["state_abbr"] == "ND") & (crime["year"] == 2022)
    if int(nc_2022_mask.sum()) == 2 and int(nd_2022_mask.sum()) == 0:
        reassigned_idx = crime.loc[nc_2022_mask].sort_values("population").index[0]
        crime.loc[reassigned_idx, "state_abbr"] = "ND"
        crime.loc[reassigned_idx, "state"] = "North Dakota"
        repair_log_rows.append(
            {
                "state_abbr": "ND",
                "year": 2022,
                "repair_type": "state_reassignment",
                "source_name": "OpenCrime state trends",
                "url": "https://www.opencrime.us/downloads",
                "note": "Reassigned a mislabeled duplicate North Carolina 2022 row to North Dakota 2022 because the raw source duplicated NC and omitted ND.",
            }
        )

    duplicates = crime.loc[crime.duplicated(duplicate_keys, keep=False)].copy()
    if not duplicates.empty:
        compare_cols = [c for c in crime.columns if c not in duplicate_keys]
        for (state_abbr, year), group in duplicates.groupby(duplicate_keys, dropna=False):
            first = group.iloc[0][compare_cols]
            if not group[compare_cols].eq(first).all().all():
                raise ValueError(f"Non-identical duplicate crime rows found for {state_abbr} {year}")
            repair_log_rows.append(
                {
                    "state_abbr": state_abbr,
                    "year": int(year),
                    "repair_type": "duplicate_drop",
                    "source_name": "OpenCrime state trends",
                    "url": "https://www.opencrime.us/downloads",
                    "note": "Dropped an identical duplicate state-year crime row from the source JSON.",
                }
            )
        crime = crime.drop_duplicates(duplicate_keys, keep="first").copy()

    repairs = pd.read_csv(repairs_path)
    repairs["year"] = pd.to_numeric(repairs["year"], errors="raise").astype(int)
    if repairs.duplicated(duplicate_keys).any():
        raise ValueError("manual_crime_repairs.csv contains duplicate state-year keys")

    repair_value_cols = ["state", "violent_crime", "property_crime"]
    repaired = crime.merge(
        repairs[duplicate_keys + repair_value_cols + ["repair_source_name", "repair_url", "repair_note"]],
        on=duplicate_keys,
        how="outer",
        suffixes=("", "_repair"),
    )
    for _, row in repairs.iterrows():
        mask = (repaired["state_abbr"] == row["state_abbr"]) & (repaired["year"] == row["year"])
        used_cols = [
            col
            for col in repair_value_cols
            if pd.notna(row[col]) and repaired.loc[mask, col].isna().any()
        ]
        if used_cols:
            repair_log_rows.append(
                {
                    "state_abbr": row["state_abbr"],
                    "year": int(row["year"]),
                    "repair_type": "manual_fill",
                    "source_name": row["repair_source_name"],
                    "url": row["repair_url"],
                    "note": f"{row['repair_note']} Filled columns: {', '.join(used_cols)}.",
                }
            )
    for col in repair_value_cols:
        repair_col = f"{col}_repair"
        repaired[col] = repaired[col].combine_first(repaired[repair_col])
        repaired = repaired.drop(columns=[repair_col])

    repaired = repaired.drop(columns=["repair_source_name", "repair_url", "repair_note"])
    if repaired.duplicated(duplicate_keys).any():
        raise ValueError("State crime data still contains duplicate state-year keys after repairs")

    expected_years = set(range(1979, 2025))
    coverage_issues = []
    for state_abbr, group in repaired.groupby("state_abbr"):
        years = set(group["year"].astype(int).tolist())
        missing_years = sorted(expected_years - years)
        extra_years = sorted(years - expected_years)
        if missing_years or extra_years:
            coverage_issues.append((state_abbr, missing_years, extra_years))
    if coverage_issues:
        issue_text = "; ".join(
            f"{state_abbr}: missing={missing_years}, extra={extra_years}"
            for state_abbr, missing_years, extra_years in coverage_issues
        )
        raise ValueError(f"State crime coverage is not a full 1979-2024 panel after repairs: {issue_text}")

    cleaned = repaired[
        [
            "state",
            "state_abbr",
            "year",
            "violent_crime",
            "property_crime",
        ]
    ].copy()
    repair_log = pd.DataFrame(
        repair_log_rows,
        columns=["state_abbr", "year", "repair_type", "source_name", "url", "note"],
    )
    return cleaned.sort_values(["state_abbr", "year"]).reset_index(drop=True), repair_log


def build_state_population(state_abbrs: list[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for abbr in state_abbrs:
        pop = read_fred_series(f"{abbr}POP")
        pop["year"] = pop["date"].dt.year
        pop = pop.rename(columns={"value": "population"})[["year", "population"]]
        pop["population"] = (pop["population"] * 1000).round()
        pop["state_abbr"] = abbr
        frames.append(pop)

    population = pd.concat(frames, ignore_index=True)
    population["population"] = pd.to_numeric(population["population"], errors="coerce")
    return population


def build_cpi_annual() -> tuple[pd.DataFrame, float]:
    cpi = read_fred_series(FRED_CPI_SERIES)
    cpi["year"] = cpi["date"].dt.year
    cpi_annual = cpi.groupby("year", as_index=False)["value"].mean().rename(columns={"value": "cpi_avg"})
    cpi_2024 = float(cpi_annual.loc[cpi_annual["year"] == 2024, "cpi_avg"].iloc[0])
    return cpi_annual, cpi_2024


def build_core_controls(state_abbrs: list[str]) -> pd.DataFrame:
    cpi_annual, cpi_2024 = build_cpi_annual()

    unemployment_frames: list[pd.DataFrame] = []
    income_frames: list[pd.DataFrame] = []
    for abbr in state_abbrs:
        ur = read_fred_series(f"{abbr}UR")
        ur["year"] = ur["date"].dt.year
        ur = (
            ur.groupby("year", as_index=False)["value"]
            .mean()
            .rename(columns={"value": "unemployment_rate"})
        )
        ur["state_abbr"] = abbr
        unemployment_frames.append(ur)

        pcpi = read_fred_series(f"{abbr}PCPI")
        pcpi["year"] = pcpi["date"].dt.year
        pcpi = pcpi.rename(columns={"value": "pcpi_nominal"})[["year", "pcpi_nominal"]]
        pcpi["state_abbr"] = abbr
        income_frames.append(pcpi)

    unemployment = pd.concat(unemployment_frames, ignore_index=True)
    income = pd.concat(income_frames, ignore_index=True)
    controls = unemployment.merge(income, on=["state_abbr", "year"], how="outer")
    controls = controls.merge(cpi_annual, on="year", how="left")
    controls["pcpi_real_2024"] = controls["pcpi_nominal"] * (cpi_2024 / controls["cpi_avg"])
    controls = controls.drop(columns=["cpi_avg"])
    return controls


def parse_sasrh_file(path: Path) -> pd.DataFrame:
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()
        if len(parts) == 19 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
            rows.append(parts)

    columns = [
        "year",
        "state_fips",
        "age",
        "nh_white_male",
        "nh_white_female",
        "nh_black_male",
        "nh_black_female",
        "nh_aian_male",
        "nh_aian_female",
        "nh_api_male",
        "nh_api_female",
        "hisp_white_male",
        "hisp_white_female",
        "hisp_black_male",
        "hisp_black_female",
        "hisp_aian_male",
        "hisp_aian_female",
        "hisp_api_male",
        "hisp_api_female",
    ]
    parsed = pd.DataFrame(rows, columns=columns)
    for column in columns:
        parsed[column] = pd.to_numeric(parsed[column], errors="raise")
    parsed["state_abbr"] = parsed["state_fips"].map(STATE_FIPS_TO_ABBR)
    parsed = parsed.dropna(subset=["state_abbr"]).copy()
    return parsed


def build_historical_population_shares(state_lookup: pd.DataFrame) -> pd.DataFrame:
    state_names = state_lookup[["state", "state_abbr"]].drop_duplicates().copy()

    sasrh_1999_path = ensure_download(
        HISTORICAL_SASRH_URL_TEMPLATE.format(year_suffix="99"),
        HISTORICAL_DEMOGRAPHIC_DIR / "sasrh99.txt",
    )
    sasrh = parse_sasrh_file(sasrh_1999_path)
    sasrh = sasrh.loc[sasrh["year"] == 1999].copy()
    value_columns = [
        "nh_white_male",
        "nh_white_female",
        "nh_black_male",
        "nh_black_female",
        "nh_aian_male",
        "nh_aian_female",
        "nh_api_male",
        "nh_api_female",
        "hisp_white_male",
        "hisp_white_female",
        "hisp_black_male",
        "hisp_black_female",
        "hisp_aian_male",
        "hisp_aian_female",
        "hisp_api_male",
        "hisp_api_female",
    ]
    male_columns = [column for column in value_columns if column.endswith("_male")]
    hispanic_columns = [column for column in value_columns if column.startswith("hisp_")]
    sasrh["total_population"] = sasrh[value_columns].sum(axis=1)
    sasrh["male_population"] = sasrh[male_columns].sum(axis=1)
    sasrh["nh_white_population"] = sasrh["nh_white_male"] + sasrh["nh_white_female"]
    sasrh["nh_black_population"] = sasrh["nh_black_male"] + sasrh["nh_black_female"]
    sasrh["hispanic_population"] = sasrh[hispanic_columns].sum(axis=1)
    historical_1999 = (
        sasrh.groupby("state_abbr", as_index=False)
        .agg(
            total_population=("total_population", "sum"),
            male_population=("male_population", "sum"),
            nh_white_population=("nh_white_population", "sum"),
            nh_black_population=("nh_black_population", "sum"),
            hispanic_population=("hispanic_population", "sum"),
        )
        .assign(year=1999)
    )
    age_15_24_1999 = (
        sasrh.loc[sasrh["age"].between(15, 24)]
        .groupby("state_abbr", as_index=False)["total_population"]
        .sum()
        .rename(columns={"total_population": "age_15_24_population"})
    )
    age_25_44_1999 = (
        sasrh.loc[sasrh["age"].between(25, 44)]
        .groupby("state_abbr", as_index=False)["total_population"]
        .sum()
        .rename(columns={"total_population": "age_25_44_population"})
    )
    historical_1999 = historical_1999.merge(age_15_24_1999, on="state_abbr", how="left")
    historical_1999 = historical_1999.merge(age_25_44_1999, on="state_abbr", how="left")

    state_pop_2000_2010_path = ensure_download(
        STATE_POP_2000_2010_URL,
        HISTORICAL_DEMOGRAPHIC_DIR / "st-est00int-alldata.csv",
    )
    popest = pd.read_csv(state_pop_2000_2010_path)
    popest = popest.loc[popest["STATE"].isin(STATE_FIPS_TO_ABBR)].copy()
    popest["state_abbr"] = popest["STATE"].map(STATE_FIPS_TO_ABBR)
    year_columns = [f"POPESTIMATE{year}" for year in range(2000, 2005)]
    popest_long = popest.melt(
        id_vars=["NAME", "STATE", "state_abbr", "SEX", "ORIGIN", "RACE", "AGEGRP"],
        value_vars=year_columns,
        var_name="year_col",
        value_name="population",
    )
    popest_long["year"] = popest_long["year_col"].str[-4:].astype(int)
    popest_long["population"] = pd.to_numeric(popest_long["population"], errors="coerce")

    totals = (
        popest_long.loc[
            (popest_long["SEX"] == 0)
            & (popest_long["ORIGIN"] == 0)
            & (popest_long["RACE"] == 0)
            & (popest_long["AGEGRP"] == 0),
            ["state_abbr", "year", "population"],
        ]
        .rename(columns={"population": "total_population"})
    )
    male = (
        popest_long.loc[
            (popest_long["SEX"] == 1)
            & (popest_long["ORIGIN"] == 0)
            & (popest_long["RACE"] == 0)
            & (popest_long["AGEGRP"] == 0),
            ["state_abbr", "year", "population"],
        ]
        .rename(columns={"population": "male_population"})
    )
    white_nh = (
        popest_long.loc[
            (popest_long["SEX"] == 0)
            & (popest_long["ORIGIN"] == 1)
            & (popest_long["RACE"] == 1)
            & (popest_long["AGEGRP"] == 0),
            ["state_abbr", "year", "population"],
        ]
        .rename(columns={"population": "nh_white_population"})
    )
    black_nh = (
        popest_long.loc[
            (popest_long["SEX"] == 0)
            & (popest_long["ORIGIN"] == 1)
            & (popest_long["RACE"] == 2)
            & (popest_long["AGEGRP"] == 0),
            ["state_abbr", "year", "population"],
        ]
        .rename(columns={"population": "nh_black_population"})
    )
    hispanic = (
        popest_long.loc[
            (popest_long["SEX"] == 0)
            & (popest_long["ORIGIN"] == 2)
            & (popest_long["RACE"] == 0)
            & (popest_long["AGEGRP"] == 0),
            ["state_abbr", "year", "population"],
        ]
        .rename(columns={"population": "hispanic_population"})
    )
    age_15_24 = (
        popest_long.loc[
            (popest_long["SEX"] == 0)
            & (popest_long["ORIGIN"] == 0)
            & (popest_long["RACE"] == 0)
            & (popest_long["AGEGRP"].isin([4, 5]))
        ]
        .groupby(["state_abbr", "year"], as_index=False)["population"]
        .sum()
        .rename(columns={"population": "age_15_24_population"})
    )
    age_25_44 = (
        popest_long.loc[
            (popest_long["SEX"] == 0)
            & (popest_long["ORIGIN"] == 0)
            & (popest_long["RACE"] == 0)
            & (popest_long["AGEGRP"].isin([6, 7, 8, 9]))
        ]
        .groupby(["state_abbr", "year"], as_index=False)["population"]
        .sum()
        .rename(columns={"population": "age_25_44_population"})
    )
    historical_2000_2004 = totals.merge(male, on=["state_abbr", "year"], how="inner")
    historical_2000_2004 = historical_2000_2004.merge(white_nh, on=["state_abbr", "year"], how="inner")
    historical_2000_2004 = historical_2000_2004.merge(black_nh, on=["state_abbr", "year"], how="inner")
    historical_2000_2004 = historical_2000_2004.merge(hispanic, on=["state_abbr", "year"], how="inner")
    historical_2000_2004 = historical_2000_2004.merge(age_15_24, on=["state_abbr", "year"], how="inner")
    historical_2000_2004 = historical_2000_2004.merge(age_25_44, on=["state_abbr", "year"], how="inner")

    historical = pd.concat([historical_1999, historical_2000_2004], ignore_index=True)
    historical = historical.merge(state_names, on="state_abbr", how="left")
    historical = historical.dropna(subset=["state"]).copy()
    historical["share_white_nh"] = historical["nh_white_population"] / historical["total_population"]
    historical["share_black_nh"] = historical["nh_black_population"] / historical["total_population"]
    historical["share_hispanic"] = historical["hispanic_population"] / historical["total_population"]
    historical["share_male"] = historical["male_population"] / historical["total_population"]
    historical["share_age_15_24"] = historical["age_15_24_population"] / historical["total_population"]
    historical["share_age_25_44"] = historical["age_25_44_population"] / historical["total_population"]

    keep_cols = [
        "state",
        "state_abbr",
        "year",
        "share_white_nh",
        "share_black_nh",
        "share_hispanic",
        "share_male",
        "share_age_15_24",
        "share_age_25_44",
    ]
    historical = historical[keep_cols].sort_values(["state", "year"]).reset_index(drop=True)
    return historical


def build_historical_income_poverty(state_lookup: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    cpi_annual, cpi_2024 = build_cpi_annual()
    state_names = state_lookup[["state", "state_abbr"]].drop_duplicates().copy()
    for year in range(1999, 2005):
        url = (
            "https://api.census.gov/data/timeseries/poverty/saipe"
            f"?get=NAME,SAEMHI_PT,SAEPOVRTALL_PT,YEAR&for=state:*&YEAR={year}"
        )
        data = fetch_json(url)
        df = pd.DataFrame(
            data[1:],
            columns=[
                "state",
                "median_hh_income_nominal",
                "poverty_rate_pct",
                "year_label",
                "year",
                "state_fips",
            ],
        )
        df["year"] = pd.to_numeric(df["year"], errors="raise").astype(int)
        df["median_hh_income_nominal"] = pd.to_numeric(df["median_hh_income_nominal"], errors="coerce")
        df["poverty_rate"] = pd.to_numeric(df["poverty_rate_pct"], errors="coerce") / 100
        df["state_fips"] = pd.to_numeric(df["state_fips"], errors="coerce").astype("Int64")
        df["state_abbr"] = df["state_fips"].map(STATE_FIPS_TO_ABBR)
        df = df.merge(state_names, on="state_abbr", how="left", suffixes=("_api", ""))
        df["state"] = df["state"].fillna(df["state_api"])
        frames.append(df[["state", "state_abbr", "year", "median_hh_income_nominal", "poverty_rate"]])

    historical = pd.concat(frames, ignore_index=True)
    historical = historical.dropna(subset=["state_abbr"]).copy()
    historical = historical.merge(cpi_annual, on="year", how="left")
    historical["median_hh_income_real_2024"] = historical["median_hh_income_nominal"] * (cpi_2024 / historical["cpi_avg"])
    historical = historical.drop(columns=["cpi_avg"]).sort_values(["state", "year"]).reset_index(drop=True)
    return historical


def parse_historical_education_pdf(path: Path, allowed_states: set[str]) -> pd.DataFrame:
    rows: list[dict] = []
    pattern = re.compile(
        r"^(?P<state>[A-Za-z .'-]+?)\s+(?P<total>[\d,]+)\s+(?P<hs>[\d.]+)\s+(?P<hs_se>[\d.]+)\s+(?P<ba>[\d.]+)\s+(?P<ba_se>[\d.]+)$"
    )
    reader = PdfReader(path)
    for page in reader.pages:
        text = page.extract_text() or ""
        for raw_line in text.splitlines():
            line = re.sub(r"\s+", " ", raw_line).strip()
            match = pattern.match(line)
            if not match:
                continue
            state = match.group("state").strip()
            if state not in allowed_states:
                continue
            rows.append(
                {
                    "state": state,
                    "education_population_25_plus_thousands": pd.to_numeric(match.group("total").replace(",", ""), errors="coerce"),
                    "share_bachelors_plus": pd.to_numeric(match.group("ba"), errors="coerce") / 100,
                }
            )
    return pd.DataFrame(rows)


def parse_historical_education_xls(path: Path, allowed_states: set[str]) -> pd.DataFrame:
    try:
        raw = pd.read_excel(path, header=None, engine="xlrd")
    except ImportError as exc:
        raise ImportError(
            "Reading historical Census education .xls files requires xlrd. Install xlrd>=2.0.1."
        ) from exc

    data = raw.iloc[:, :5].copy()
    data = data.rename(
        columns={
            0: "state",
            1: "education_population_25_plus_thousands",
            2: "high_school_percent",
            3: "high_school_ci",
            4: "bachelors_percent",
        }
    )
    data["state"] = data["state"].astype(str).str.strip()
    data = data.loc[data["state"].isin(allowed_states)].copy()
    data["education_population_25_plus_thousands"] = pd.to_numeric(
        data["education_population_25_plus_thousands"], errors="coerce"
    )
    data["share_bachelors_plus"] = pd.to_numeric(data["bachelors_percent"], errors="coerce") / 100
    return data[["state", "education_population_25_plus_thousands", "share_bachelors_plus"]].reset_index(drop=True)


def build_historical_education_controls(state_lookup: pd.DataFrame) -> pd.DataFrame:
    allowed_states = set(state_lookup["state"]).union({"District of Columbia"})
    frames: list[pd.DataFrame] = []
    for year, url in sorted(HISTORICAL_EDUCATION_URLS.items()):
        suffix = Path(url).suffix
        path = ensure_download(url, HISTORICAL_DEMOGRAPHIC_DIR / "education" / f"tab13_{year}{suffix}")
        if suffix.lower() == ".pdf":
            frame = parse_historical_education_pdf(path, allowed_states)
        else:
            frame = parse_historical_education_xls(path, allowed_states)
        frame["year"] = year
        frames.append(frame)

    education = pd.concat(frames, ignore_index=True)
    education = education.merge(state_lookup[["state", "state_abbr"]], on="state", how="left")
    education = education.dropna(subset=["state_abbr"]).copy()
    education = education[["state", "state_abbr", "year", "share_bachelors_plus"]]
    education = education.sort_values(["state", "year"]).reset_index(drop=True)
    return education


def build_historical_demographic_controls(state_lookup: pd.DataFrame) -> pd.DataFrame:
    income_poverty = build_historical_income_poverty(state_lookup)
    population_shares = build_historical_population_shares(state_lookup)
    education = build_historical_education_controls(state_lookup)

    historical = income_poverty.merge(population_shares, on=["state", "state_abbr", "year"], how="inner")
    historical = historical.merge(education, on=["state", "state_abbr", "year"], how="inner")
    historical["controls_source"] = "historical_mix"
    historical = historical[DEMOGRAPHIC_CONTROL_COLS].sort_values(["state", "year"]).reset_index(drop=True)
    return historical


def build_acs_controls(state_lookup: pd.DataFrame) -> pd.DataFrame:
    common_vars = [
        "NAME",
        "B01003_001E",
        "B19013_001E",
        "B17001_001E",
        "B17001_002E",
        "B03002_001E",
        "B03002_003E",
        "B03002_004E",
        "B03002_012E",
        "B01001_001E",
        "B01001_002E",
        "B01001_006E",
        "B01001_007E",
        "B01001_008E",
        "B01001_009E",
        "B01001_010E",
        "B01001_011E",
        "B01001_012E",
        "B01001_013E",
        "B01001_014E",
        "B01001_015E",
        "B01001_016E",
        "B01001_017E",
        "B01001_030E",
        "B01001_031E",
        "B01001_032E",
        "B01001_033E",
        "B01001_034E",
        "B01001_035E",
        "B01001_036E",
        "B01001_037E",
        "B01001_038E",
        "B01001_039E",
        "B01001_040E",
        "B01001_041E",
        "B01001_042E",
    ]
    early_education_vars = [
        "B15002_001E",
        "B15002_015E",
        "B15002_016E",
        "B15002_017E",
        "B15002_018E",
        "B15002_032E",
        "B15002_033E",
        "B15002_034E",
        "B15002_035E",
    ]
    late_education_vars = [
        "B15003_001E",
        "B15003_022E",
        "B15003_023E",
        "B15003_024E",
        "B15003_025E",
    ]
    years = list(range(2005, 2025))
    frames: list[pd.DataFrame] = []
    for year in years:
        dataset = "acs5" if year == 2020 else "acs1"
        education_vars = early_education_vars if year <= 2007 else late_education_vars
        acs_vars = common_vars + education_vars
        url = (
            f"https://api.census.gov/data/{year}/acs/{dataset}?get="
            f"{urllib.parse.quote(','.join(acs_vars), safe=',')}&for=state:*"
        )
        data = fetch_json(url)
        df = pd.DataFrame(data[1:], columns=data[0])
        df["year"] = year
        df["controls_source"] = dataset
        frames.append(df)

    acs = pd.concat(frames, ignore_index=True)
    numeric_cols = [c for c in acs.columns if c not in {"NAME", "state", "controls_source"}]
    for col in numeric_cols:
        acs[col] = pd.to_numeric(acs[col], errors="coerce")

    cpi_annual, cpi_2024 = build_cpi_annual()

    acs["state"] = acs["NAME"]
    acs = acs.merge(state_lookup[["state", "state_abbr"]], on="state", how="left")

    acs["poverty_rate"] = acs["B17001_002E"] / acs["B17001_001E"]
    acs["share_white_nh"] = acs["B03002_003E"] / acs["B03002_001E"]
    acs["share_black_nh"] = acs["B03002_004E"] / acs["B03002_001E"]
    acs["share_hispanic"] = acs["B03002_012E"] / acs["B03002_001E"]
    acs["share_bachelors_plus"] = pd.NA
    early_mask = acs["year"] <= 2007
    late_mask = acs["year"] >= 2008
    acs.loc[early_mask, "share_bachelors_plus"] = (
        acs.loc[early_mask, "B15002_015E"]
        + acs.loc[early_mask, "B15002_016E"]
        + acs.loc[early_mask, "B15002_017E"]
        + acs.loc[early_mask, "B15002_018E"]
        + acs.loc[early_mask, "B15002_032E"]
        + acs.loc[early_mask, "B15002_033E"]
        + acs.loc[early_mask, "B15002_034E"]
        + acs.loc[early_mask, "B15002_035E"]
    ) / acs.loc[early_mask, "B15002_001E"]
    acs.loc[late_mask, "share_bachelors_plus"] = (
        acs.loc[late_mask, "B15003_022E"]
        + acs.loc[late_mask, "B15003_023E"]
        + acs.loc[late_mask, "B15003_024E"]
        + acs.loc[late_mask, "B15003_025E"]
    ) / acs.loc[late_mask, "B15003_001E"]
    acs["share_male"] = acs["B01001_002E"] / acs["B01001_001E"]

    age_15_24_cols = [
        "B01001_006E",
        "B01001_007E",
        "B01001_008E",
        "B01001_009E",
        "B01001_010E",
        "B01001_030E",
        "B01001_031E",
        "B01001_032E",
        "B01001_033E",
        "B01001_034E",
    ]
    age_25_44_cols = [
        "B01001_011E",
        "B01001_012E",
        "B01001_013E",
        "B01001_014E",
        "B01001_035E",
        "B01001_036E",
        "B01001_037E",
        "B01001_038E",
    ]
    acs["share_age_15_24"] = acs[age_15_24_cols].sum(axis=1) / acs["B01001_001E"]
    acs["share_age_25_44"] = acs[age_25_44_cols].sum(axis=1) / acs["B01001_001E"]
    acs["median_hh_income_nominal"] = acs["B19013_001E"]
    acs = acs.merge(cpi_annual, on="year", how="left")
    acs["median_hh_income_real_2024"] = acs["median_hh_income_nominal"] * (cpi_2024 / acs["cpi_avg"])
    acs = acs[DEMOGRAPHIC_CONTROL_COLS]
    return acs.dropna(subset=["state_abbr"])


def build_demographic_controls(state_lookup: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    historical = build_historical_demographic_controls(state_lookup)
    acs = build_acs_controls(state_lookup)
    combined = pd.concat([historical, acs], ignore_index=True).sort_values(["state", "year"]).reset_index(drop=True)

    duplicate_rows = int(combined.duplicated(["state_abbr", "year"]).sum())
    if duplicate_rows:
        raise ValueError(f"Demographic controls contain {duplicate_rows} duplicate state-year rows")

    expected_rows = int(state_lookup["state_abbr"].nunique()) * len(range(1999, 2025))
    if int(combined.shape[0]) != expected_rows:
        raise ValueError(
            f"Demographic controls should contain {expected_rows} rows for 1999-2024, found {combined.shape[0]}"
        )

    missing_required_cells = int(combined[DEMOGRAPHIC_CONTROL_COLS].isna().sum().sum())
    if missing_required_cells:
        raise ValueError(f"Demographic controls contain {missing_required_cells} missing required cells")

    return combined, historical, acs


def build_nics_annual(path: Path, state_lookup: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    nics = pd.read_csv(path)
    nics["month"] = pd.to_datetime(nics["month"] + "-01")
    nics["year"] = nics["month"].dt.year

    keep_states = set(state_lookup["state"])
    nics = nics[nics["state"].isin(keep_states)].copy()
    nics = nics.merge(state_lookup[["state", "state_abbr"]], on="state", how="left")

    numeric_cols = [c for c in nics.columns if c not in {"month", "state", "state_abbr"}]
    for col in numeric_cols:
        nics[col] = pd.to_numeric(nics[col], errors="coerce")

    annual = (
        nics.groupby(["state", "state_abbr", "year"], as_index=False)[
            [
                "totals",
                "handgun",
                "long_gun",
                "multiple",
                "permit",
                "permit_recheck",
                "other",
            ]
        ]
        .sum()
        .rename(
            columns={
                "totals": "nics_total",
                "handgun": "nics_handgun",
                "long_gun": "nics_long_gun",
                "multiple": "nics_multiple",
                "permit": "nics_permit",
                "permit_recheck": "nics_permit_recheck",
                "other": "nics_other",
            }
        )
    )
    annual = annual[annual["year"] >= 1999].copy()

    latest_month = nics["month"].max()
    latest_ur_month = pd.Timestamp("2026-01-01")
    current = (
        nics.loc[nics["month"] == latest_month, ["state", "state_abbr", "totals"]]
        .rename(columns={"totals": "nics_latest_month_total"})
        .copy()
    )
    current["nics_latest_month"] = latest_month.strftime("%Y-%m")

    totals_2025 = (
        annual.loc[annual["year"] == 2025, ["state_abbr", "nics_total"]]
        .rename(columns={"nics_total": "nics_2025_total"})
    )
    totals_2026_ytd = (
        nics.loc[nics["year"] == 2026].groupby("state_abbr", as_index=False)["totals"].sum()
        .rename(columns={"totals": "nics_2026_ytd_total"})
    )

    current = current.merge(totals_2025, on="state_abbr", how="left")
    current = current.merge(totals_2026_ytd, on="state_abbr", how="left")
    current["latest_unemployment_month"] = latest_ur_month.strftime("%Y-%m")
    return annual, current


def build_law_dictionary(codebook_path: Path) -> pd.DataFrame:
    codebook = pd.read_excel(codebook_path, sheet_name="Sheet1")
    out = codebook.rename(
        columns={
            "Variable Name": "variable_name",
            "Category": "group",
            "Brief Description of Provision": "label",
            "Detailed Description of Provision": "description",
            "Data Source and Attribution": "source",
        }
    )
    return out[["variable_name", "group", "label", "description", "source"]].copy()


def longest_contiguous_year_span(years: list[int]) -> tuple[int, int]:
    if not years:
        raise ValueError("No complete years available")
    years = sorted(years)
    best_start = years[0]
    best_end = years[0]
    cur_start = years[0]
    cur_end = years[0]
    for year in years[1:]:
        if year == cur_end + 1:
            cur_end = year
        else:
            if (cur_end - cur_start) > (best_end - best_start):
                best_start, best_end = cur_start, cur_end
            cur_start = cur_end = year
    if (cur_end - cur_start) > (best_end - best_start):
        best_start, best_end = cur_start, cur_end
    return best_start, best_end


def build_balanced_panel(
    df: pd.DataFrame,
    required_vars: list[str],
    panel_name: str,
    expected_states: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    working = df.copy()
    duplicate_rows = int(working.duplicated(["state_abbr", "year"]).sum())
    if duplicate_rows:
        raise ValueError(f"{panel_name} contains {duplicate_rows} duplicate state-year rows before balancing")
    working["_complete"] = working[required_vars].notna().all(axis=1)
    year_counts = (
        working.groupby("year", as_index=False)["_complete"].sum().rename(columns={"_complete": "complete_states"})
    )
    full_years = year_counts.loc[year_counts["complete_states"] == expected_states, "year"].astype(int).tolist()
    start_year, end_year = longest_contiguous_year_span(full_years)
    panel = working.loc[(working["year"] >= start_year) & (working["year"] <= end_year)].copy()
    panel = panel.drop(columns=["_complete"])
    if panel.shape[0] != expected_states * (end_year - start_year + 1):
        raise ValueError(f"{panel_name} is not balanced after year restriction")
    if not panel[required_vars].notna().all().all():
        raise ValueError(f"{panel_name} still contains missing values in required variables")

    diag = year_counts.copy()
    diag["panel_name"] = panel_name
    diag["required_var_count"] = len(required_vars)
    diag["expected_states"] = expected_states
    diag["chosen_start_year"] = start_year
    diag["chosen_end_year"] = end_year
    diag["is_in_balanced_span"] = diag["year"].between(start_year, end_year)
    return panel, diag


def save_csv(df: pd.DataFrame, name: str) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_DIR / name, index=False)


def build_balance_check(
    panel: pd.DataFrame,
    required_vars: list[str],
    panel_name: str,
    expected_states: int,
) -> dict:
    year_count = int(panel["year"].nunique())
    rows_expected = expected_states * year_count
    rows_actual = int(panel.shape[0])
    missing_required_cells = int(panel[required_vars].isna().sum().sum())
    duplicate_state_year_rows = int(panel.duplicated(["state_abbr", "year"]).sum())
    states_actual = int(panel["state_abbr"].nunique())
    years_actual = year_count
    is_balanced = (
        rows_actual == rows_expected
        and states_actual == expected_states
        and duplicate_state_year_rows == 0
        and missing_required_cells == 0
    )
    return {
        "panel_name": panel_name,
        "start_year": int(panel["year"].min()),
        "end_year": int(panel["year"].max()),
        "rows_expected": rows_expected,
        "rows_actual": rows_actual,
        "states_expected": expected_states,
        "states_actual": states_actual,
        "years_actual": years_actual,
        "required_var_count": len(required_vars),
        "missing_required_cells": missing_required_cells,
        "duplicate_state_year_rows": duplicate_state_year_rows,
        "is_balanced": is_balanced,
    }


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    laws = pd.read_excel(DATA_DIR / "tufts_state_firearm_laws.xlsx", sheet_name="results")
    law_dictionary = build_law_dictionary(DATA_DIR / "tufts_state_firearm_laws_codebook.xlsx")

    crime, crime_repairs_log = clean_state_crime(DATA_DIR / "opencrime_state_trends.json", CRIME_REPAIRS_PATH)

    state_lookup = (
        crime[["state", "state_abbr"]]
        .drop_duplicates()
        .sort_values(["state"])
        .reset_index(drop=True)
    )
    state_lookup = state_lookup[state_lookup["state"] != "District of Columbia"].copy()
    keep_states = set(state_lookup["state"])
    keep_abbrs = state_lookup["state_abbr"].sort_values().tolist()

    laws = laws[laws["state"].isin(keep_states)].copy()
    laws = laws.merge(state_lookup, on="state", how="left")
    crime = crime[crime["state"].isin(keep_states)].copy()

    law_vars = [c for c in laws.columns if c not in {"state", "state_abbr", "year"}]

    state_population = build_state_population(keep_abbrs)
    core_controls = build_core_controls(keep_abbrs)
    demographic_controls, historical_demographic_controls, acs_controls = build_demographic_controls(state_lookup)
    nics_annual, current_partial = build_nics_annual(DATA_DIR / "nics_firearm_background_checks.csv", state_lookup)

    base = laws.merge(crime, on=["state", "state_abbr", "year"], how="inner")
    base = base.merge(state_population, on=["state_abbr", "year"], how="left")
    base["violent_rate"] = base["violent_crime"] / base["population"] * 100000
    base["property_rate"] = base["property_crime"] / base["population"] * 100000
    base = base.merge(core_controls, on=["state_abbr", "year"], how="left")
    base["ln_population"] = base["population"].apply(lambda x: math.log(x) if pd.notna(x) and x > 0 else pd.NA)
    base["ln_pcpi_real_2024"] = base["pcpi_real_2024"].apply(
        lambda x: math.log(x) if pd.notna(x) and x > 0 else pd.NA
    )

    base = base.merge(nics_annual, on=["state", "state_abbr", "year"], how="left")
    base["nics_total_per_100k"] = base["nics_total"] / base["population"] * 100000
    base = base.merge(demographic_controls, on=["state", "state_abbr", "year"], how="left")

    core_required = law_vars + [
        "population",
        "violent_crime",
        "violent_rate",
        "property_crime",
        "property_rate",
        "unemployment_rate",
        "pcpi_nominal",
        "pcpi_real_2024",
        "ln_population",
        "ln_pcpi_real_2024",
    ]

    market_required = core_required + [
        "nics_total",
        "nics_handgun",
        "nics_long_gun",
        "nics_multiple",
        "nics_permit",
        "nics_permit_recheck",
        "nics_other",
        "nics_total_per_100k",
    ]

    modern_required = market_required + [
        "controls_source",
        "median_hh_income_nominal",
        "median_hh_income_real_2024",
        "poverty_rate",
        "share_white_nh",
        "share_black_nh",
        "share_hispanic",
        "share_bachelors_plus",
        "share_male",
        "share_age_15_24",
        "share_age_25_44",
    ]

    core_panel, core_diag = build_balanced_panel(base, core_required, "panel_core", expected_states=50)
    market_panel, market_diag = build_balanced_panel(base, market_required, "panel_market", expected_states=50)
    modern_panel, modern_diag = build_balanced_panel(base, modern_required, "panel_modern", expected_states=50)

    id_cols = ["state", "state_abbr", "year"]
    core_export_cols = id_cols + [c for c in core_required if c not in id_cols]
    market_export_cols = id_cols + [c for c in market_required if c not in id_cols]
    modern_export_cols = id_cols + [c for c in modern_required if c not in id_cols]

    core_panel = core_panel[core_export_cols].copy()
    market_panel = market_panel[market_export_cols].copy()
    modern_panel = modern_panel[modern_export_cols].copy()
    crime_clean = (
        base[["state", "state_abbr", "year", "population", "violent_crime", "violent_rate", "property_crime", "property_rate"]]
        .sort_values(["state", "year"])
        .reset_index(drop=True)
    )

    current_unemployment = []
    for abbr in keep_abbrs:
        ur = read_fred_series(f"{abbr}UR")
        latest = ur.loc[ur["date"] == ur["date"].max(), ["date", "value"]].iloc[0]
        current_unemployment.append(
            {
                "state_abbr": abbr,
                "latest_unemployment_month": latest["date"].strftime("%Y-%m"),
                "latest_unemployment_rate": latest["value"],
            }
        )
    current_unemployment = pd.DataFrame(current_unemployment)
    current_partial = current_partial.merge(current_unemployment, on=["state_abbr", "latest_unemployment_month"], how="left")
    current_partial = current_partial.merge(state_lookup, on="state_abbr", how="left", suffixes=("", "_lookup"))
    current_partial = current_partial[["state_lookup", "state_abbr", "nics_latest_month", "nics_latest_month_total", "nics_2025_total", "nics_2026_ytd_total", "latest_unemployment_month", "latest_unemployment_rate"]]
    current_partial = current_partial.rename(columns={"state_lookup": "state"})

    panel_summary = pd.DataFrame(
        [
            {
                "panel_name": "panel_core",
                "description": "Long-run balanced panel with Tufts laws, crime outcomes, and core economic controls.",
                "start_year": int(core_panel["year"].min()),
                "end_year": int(core_panel["year"].max()),
                "states": int(core_panel["state_abbr"].nunique()),
                "observations": int(core_panel.shape[0]),
                "variables": int(core_panel.shape[1]),
            },
            {
                "panel_name": "panel_market",
                "description": "Balanced panel adding annual NICS firearm background check measures.",
                "start_year": int(market_panel["year"].min()),
                "end_year": int(market_panel["year"].max()),
                "states": int(market_panel["state_abbr"].nunique()),
                "observations": int(market_panel.shape[0]),
                "variables": int(market_panel.shape[1]),
            },
            {
                "panel_name": "panel_modern",
                "description": "Balanced panel adding annual demographic and socioeconomic controls plus NICS.",
                "start_year": int(modern_panel["year"].min()),
                "end_year": int(modern_panel["year"].max()),
                "states": int(modern_panel["state_abbr"].nunique()),
                "observations": int(modern_panel.shape[0]),
                "variables": int(modern_panel.shape[1]),
            },
        ]
    )
    balance_checks = pd.DataFrame(
        [
            build_balance_check(core_panel, core_required, "panel_core", expected_states=50),
            build_balance_check(market_panel, market_required, "panel_market", expected_states=50),
            build_balance_check(modern_panel, modern_required, "panel_modern", expected_states=50),
        ]
    )

    dashboard_trends = (
        core_panel.groupby("year", as_index=False)
        .agg(
            mean_violent_rate=("violent_rate", "mean"),
            mean_property_rate=("property_rate", "mean"),
            mean_lawtotal=("lawtotal", "mean"),
            states_with_magazine_ban=("magazine", "sum"),
            states_with_gvro=("gvro", "sum"),
        )
        .sort_values("year")
    )

    diagnostics = pd.concat([core_diag, market_diag, modern_diag], ignore_index=True)

    custom_dictionary = pd.DataFrame(CUSTOM_DICTIONARY_ROWS)
    variable_dictionary = pd.concat([law_dictionary, custom_dictionary], ignore_index=True)

    sources = pd.DataFrame(
        [
            {
                "source_name": "Tufts State Firearm Laws",
                "url": "https://www.tuftsctsi.org/state-firearm-laws/",
                "coverage": "1976-2024",
                "geography": "50 states",
                "integrated_into": "panel_core, panel_market, panel_modern",
                "notes": "72 firearm law indicators plus lawtotal.",
            },
            {
                "source_name": "OpenCrime state trends",
                "url": "https://www.opencrime.us/downloads",
                "coverage": "1979-2024",
                "geography": "50 states + DC",
                "integrated_into": "panel_core, panel_market, panel_modern",
                "notes": "Processed FBI-derived counts feed; the raw file duplicated North Carolina 2022 and omitted North Dakota 2022, so the mislabeled duplicate row was reassigned to North Dakota before panel construction.",
            },
            {
                "source_name": "FRED state population",
                "url": "https://fred.stlouisfed.org/",
                "coverage": "1900-2025",
                "geography": "50 states + DC",
                "integrated_into": "panel_core, panel_market, panel_modern",
                "notes": "Annual state resident population series from Census, used as the common population denominator for crime rates.",
            },
            {
                "source_name": "FRED state unemployment rate",
                "url": "https://fred.stlouisfed.org/",
                "coverage": "1976-2026-01",
                "geography": "50 states",
                "integrated_into": "panel_core, panel_market, panel_modern, current_partial",
                "notes": "Monthly UR series annualized to annual average for balanced panels.",
            },
            {
                "source_name": "FRED state PCPI",
                "url": "https://fred.stlouisfed.org/",
                "coverage": "varies by state to 2024",
                "geography": "50 states",
                "integrated_into": "panel_core, panel_market, panel_modern",
                "notes": "BEA per capita personal income series, kept nominal and deflated to 2024 dollars with CPI-U.",
            },
            {
                "source_name": "ACS detailed tables",
                "url": "https://www.census.gov/programs-surveys/acs/data/data-via-api.html",
                "coverage": "2005-2024",
                "geography": "50 states + DC",
                "integrated_into": "panel_modern",
                "notes": "State-level demographic and socioeconomic controls for 2005-2024; 2020 uses ACS 5-year because the 2020 ACS 1-year release was not produced.",
            },
            {
                "source_name": "SAIPE state income and poverty estimates",
                "url": "https://www.census.gov/programs-surveys/saipe/data/api.html",
                "coverage": "1999-2024",
                "geography": "50 states + DC",
                "integrated_into": "panel_modern",
                "notes": "Median household income and poverty rate for the pre-ACS extension years 1999-2004.",
            },
            {
                "source_name": "Census state population estimates by age, sex, race, and Hispanic origin",
                "url": "https://www.census.gov/data/tables/time-series/demo/popest/1990s-state.html",
                "coverage": "1999-2004",
                "geography": "50 states + DC",
                "integrated_into": "panel_modern",
                "notes": "Used to construct non-Hispanic White, non-Hispanic Black, Hispanic, male, age 15-24, and age 25-44 shares for 1999-2004.",
            },
            {
                "source_name": "Census/CPS educational attainment state tables",
                "url": "https://www.census.gov/data/tables/time-series/demo/educational-attainment/cps-historical-time-series.html",
                "coverage": "1999-2004",
                "geography": "50 states + DC",
                "integrated_into": "panel_modern",
                "notes": "Annual Table 13 state education tables provide the bachelor's-or-higher share for the pre-ACS extension years 1999-2004.",
            },
            {
                "source_name": "Data Liberation Project NICS",
                "url": "https://github.com/data-liberation-project/nics-firearm-background-checks",
                "coverage": "1998-11 to 2026-03",
                "geography": "states + territories",
                "integrated_into": "panel_market, panel_modern, current_partial",
                "notes": "Annual state totals start in 1999 because 1998 is partial.",
            },
        ]
    )

    highlight_laws = pd.DataFrame(
        [{"variable_name": k, "description": v} for k, v in LAW_CUSTOM_VARS.items()]
    )

    save_csv(core_panel.sort_values(["state", "year"]), "panel_core_1979_2024.csv")
    save_csv(market_panel.sort_values(["state", "year"]), "panel_market_1999_2024.csv")
    save_csv(modern_panel.sort_values(["state", "year"]), "panel_modern_1999_2024.csv")
    save_csv(current_partial.sort_values("state"), "current_partial_2025_2026.csv")
    save_csv(variable_dictionary.sort_values(["group", "variable_name"]), "variable_dictionary.csv")
    save_csv(sources, "sources_integrated.csv")
    save_csv(diagnostics.sort_values(["panel_name", "year"]), "coverage_diagnostics.csv")
    save_csv(balance_checks, "panel_balance_checks.csv")
    save_csv(panel_summary, "panel_summary.csv")
    save_csv(dashboard_trends, "dashboard_trends.csv")
    save_csv(highlight_laws, "highlight_law_variables.csv")
    save_csv(demographic_controls.sort_values(["state", "year"]), "demographic_controls_1999_2024.csv")
    save_csv(historical_demographic_controls.sort_values(["state", "year"]), "historical_demographic_controls_1999_2004.csv")
    save_csv(acs_controls.sort_values(["state", "year"]), "acs_controls_2005_2024.csv")
    save_csv(core_controls.sort_values(["state_abbr", "year"]), "core_controls_1976_2026.csv")
    save_csv(state_population.sort_values(["state_abbr", "year"]), "state_population_1900_2025.csv")
    save_csv(crime_clean, "crime_state_clean_1979_2024.csv")
    save_csv(crime_repairs_log.sort_values(["state_abbr", "year", "repair_type"]), "crime_repairs_log.csv")
    save_csv(nics_annual.sort_values(["state", "year"]), "nics_annual_1999_2026.csv")

    print(panel_summary.to_string(index=False))


if __name__ == "__main__":
    main()
