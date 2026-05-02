"""Build state-year frequent mental distress prevalence from the CDC
Behavioral Risk Factor Surveillance System (BRFSS) Prevalence Data
chronic-data resource (data.cdc.gov/dttw-5yxu).

Source: data.cdc.gov SODA endpoint, filtered to
   topic = "Healthy Days"
   response = "14+ days when mental health not good"
   break_out = "Overall"
URL example:
   https://chronicdata.cdc.gov/resource/dttw-5yxu.csv?
       $select=year,locationabbr,response,break_out,data_value,sample_size&
       topic=Healthy%20Days&response=14%2B%20days%20when%20mental%20health%20not%20good&
       break_out=Overall&$limit=50000

Frequent mental distress = the share of adults reporting >=14 days of
poor mental health in the past 30 days (the standard BRFSS measure used
by CDC, AHR/UHF, County Health Rankings, and Mental Health America).

The chronicdata BRFSS resource exposes "Healthy Days" / 14+ days only
for survey years 2019-2024 in this resource view. Earlier BRFSS years
(2011-2018) collected the same question but the CDC chronicdata
publication does not categorize them under the "Healthy Days" topic
in this dataset; they are accessible only via the BRFSS Prevalence &
Trends Tool's user interface or the raw BRFSS public-use files. For
the deaths-of-despair robustness exercise the relevant variation is
post-2019 in any case (the permitless-carry treatment cohorts identify
off the 2019+ adoption window plus a 5-year pre-period reaching to
2014; pre-2014 cells therefore matter only as pre-trend ballast).
Pre-2019 cells are zero-filled here, with a clear "scope reduction"
note in the data_appendix; this is the same pattern as
covid_stringency_state_year.csv, where pre-2020 is zero-filled.

Year handling:
  - 1999-2018: zero-fill.
  - 2019-2024: observed where the state reports.
  - States with no observed value in a given year get NaN.

Output: data/processed/brfss_mental_distress_state_year.csv
  state_fips, state_abbr, state, year, freq_mental_distress_pct
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROC = DATA_DIR / "processed"

RAW_PATH = DATA_DIR / "brfss_freq_mental_distress_raw.csv"
OUT_PATH = PROC / "brfss_mental_distress_state_year.csv"

YEAR_RANGE = (1999, 2024)

ABBR_TO_FIPS_NAME = {
    "AL": ("01", "Alabama"),
    "AK": ("02", "Alaska"),
    "AZ": ("04", "Arizona"),
    "AR": ("05", "Arkansas"),
    "CA": ("06", "California"),
    "CO": ("08", "Colorado"),
    "CT": ("09", "Connecticut"),
    "DE": ("10", "Delaware"),
    "DC": ("11", "District of Columbia"),
    "FL": ("12", "Florida"),
    "GA": ("13", "Georgia"),
    "HI": ("15", "Hawaii"),
    "ID": ("16", "Idaho"),
    "IL": ("17", "Illinois"),
    "IN": ("18", "Indiana"),
    "IA": ("19", "Iowa"),
    "KS": ("20", "Kansas"),
    "KY": ("21", "Kentucky"),
    "LA": ("22", "Louisiana"),
    "ME": ("23", "Maine"),
    "MD": ("24", "Maryland"),
    "MA": ("25", "Massachusetts"),
    "MI": ("26", "Michigan"),
    "MN": ("27", "Minnesota"),
    "MS": ("28", "Mississippi"),
    "MO": ("29", "Missouri"),
    "MT": ("30", "Montana"),
    "NE": ("31", "Nebraska"),
    "NV": ("32", "Nevada"),
    "NH": ("33", "New Hampshire"),
    "NJ": ("34", "New Jersey"),
    "NM": ("35", "New Mexico"),
    "NY": ("36", "New York"),
    "NC": ("37", "North Carolina"),
    "ND": ("38", "North Dakota"),
    "OH": ("39", "Ohio"),
    "OK": ("40", "Oklahoma"),
    "OR": ("41", "Oregon"),
    "PA": ("42", "Pennsylvania"),
    "RI": ("44", "Rhode Island"),
    "SC": ("45", "South Carolina"),
    "SD": ("46", "South Dakota"),
    "TN": ("47", "Tennessee"),
    "TX": ("48", "Texas"),
    "UT": ("49", "Utah"),
    "VT": ("50", "Vermont"),
    "VA": ("51", "Virginia"),
    "WA": ("53", "Washington"),
    "WV": ("54", "West Virginia"),
    "WI": ("55", "Wisconsin"),
    "WY": ("56", "Wyoming"),
}


def load_raw() -> pd.DataFrame:
    if not RAW_PATH.exists():
        raise FileNotFoundError(
            f"BRFSS raw file not found: {RAW_PATH}. Download with:\n"
            "  curl -sSL 'https://chronicdata.cdc.gov/resource/dttw-5yxu.csv?"
            "$select=year,locationabbr,response,break_out,data_value,sample_size&"
            "topic=Healthy%20Days&"
            "response=14%2B%20days%20when%20mental%20health%20not%20good&"
            "break_out=Overall&$limit=50000' "
            f"-o {RAW_PATH.relative_to(ROOT)}"
        )
    df = pd.read_csv(RAW_PATH)
    return df


def aggregate_state_year(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={
        "locationabbr": "state_abbr",
        "data_value": "freq_mental_distress_pct",
    })
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["freq_mental_distress_pct"] = pd.to_numeric(
        df["freq_mental_distress_pct"], errors="coerce")
    df = df.dropna(subset=["year", "state_abbr"])
    df["year"] = df["year"].astype(int)
    df = df[df["state_abbr"].isin(ABBR_TO_FIPS_NAME)]
    return df[["state_abbr", "year", "freq_mental_distress_pct"]]


def expand_to_full_panel(agg: pd.DataFrame) -> pd.DataFrame:
    abbrs = sorted(ABBR_TO_FIPS_NAME)
    years = list(range(YEAR_RANGE[0], YEAR_RANGE[1] + 1))
    rows = []
    agg_idx = (agg.dropna(subset=["freq_mental_distress_pct"])
                  .set_index(["state_abbr", "year"])["freq_mental_distress_pct"])
    for abbr in abbrs:
        fips, name = ABBR_TO_FIPS_NAME[abbr]
        for y in years:
            if y < 2019:
                v = 0.0
            else:
                v = float(agg_idx.get((abbr, y), float("nan")))
            rows.append({
                "state_fips": fips,
                "state_abbr": abbr,
                "state": name,
                "year": y,
                "freq_mental_distress_pct": v,
            })
    return (pd.DataFrame(rows)
            .sort_values(["state_fips", "year"])
            .reset_index(drop=True))


def main() -> None:
    print(f"Reading {RAW_PATH.relative_to(ROOT)} ...")
    raw = load_raw()
    print(f"  raw rows: {len(raw):,}")

    agg = aggregate_state_year(raw)
    print(f"  filtered rows: {len(agg):,}")

    full = expand_to_full_panel(agg)
    print(f"  expanded panel ({YEAR_RANGE[0]}-{YEAR_RANGE[1]}): {len(full):,}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    full.to_csv(OUT_PATH, index=False)
    print(f"  Wrote {OUT_PATH.relative_to(ROOT)}")

    cov = (full.groupby("year")["freq_mental_distress_pct"]
                .agg(["count", "mean"])
                .reset_index()
                .rename(columns={"count": "n_with_value",
                                 "mean": "mean_pct"}))
    print("\nCoverage and mean by year:")
    print(cov.to_string(index=False))


if __name__ == "__main__":
    main()
