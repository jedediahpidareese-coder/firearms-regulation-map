"""Build state-year synthetic opioid (fentanyl-included, ICD-10 T40.4)
overdose mortality rate from the CDC NCHS Vital Statistics Rapid Release
(VSRR) provisional drug-overdose dataset (data.cdc.gov/xkb8-kh2a).

Source: data.cdc.gov SODA endpoint
   https://data.cdc.gov/resource/xkb8-kh2a.csv?$limit=200000
Mirror page: https://www.cdc.gov/nchs/nvss/vsrr/drug-overdose-data.htm

The VSRR table publishes 12-month-ending counts of overdose deaths by
indicator (drug class) for each state and each month. The
``Synthetic opioids, excl. methadone (T40.4)`` indicator isolates
synthetic-opioid-involved poisoning deaths, which post-2014 are almost
entirely fentanyl. We take the December 12-month-ending value as the
annual count, then divide by the state's mid-year resident population
(from data/processed/state_population_1900_2025.csv) and multiply by
100,000 to get a death rate per 100k.

Year handling:
  - VSRR begins 2015. Pre-2015 rows are zero-filled because (a) the
    synthetic-opioid epidemic was negligible pre-2014 (CDC NCHS Data
    Brief 491, Spencer 2024 documents the post-2014 fentanyl ramp), and
    (b) for the deaths-of-despair robustness exercise the relevant
    variation is post-2018 in any case (since the permitless-carry
    cohorts identifying off the 2019+ adoption window).
  - 2015-2024 are observed where the state reports.
  - States with no observed VSRR value in a given year (the table has
    quality footnotes; some states are flagged "low data quality") get
    NaN, which the augment merge then leaves as NaN downstream. The
    panel-aware estimator covariate stack handles NaN by RA fallback to
    OR (no covariates) for that cell -- the same robustness we already
    have for the 2018+ cohorts when the alcohol per-capita ends in 2018.

Output: data/processed/fentanyl_deaths_state_year.csv
  state_fips, state_abbr, state, year, synthetic_opioid_death_rate
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROC = DATA_DIR / "processed"

RAW_PATH = DATA_DIR / "vsrr_drug_overdose_state.csv"
POP_PATH = PROC / "state_population_1900_2025.csv"
OUT_PATH = PROC / "fentanyl_deaths_state_year.csv"

YEAR_RANGE = (1999, 2024)
INDICATOR = "Synthetic opioids, excl. methadone (T40.4)"

# 50 states + DC. NY and NYC are reported separately in VSRR; we combine
# them into a single NY total (their counts are reported as separate
# jurisdictions: state == "NY" excludes NYC, "YC" is just NYC).
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
            f"VSRR raw file not found: {RAW_PATH}. Download with:\n"
            "  curl -sSL 'https://data.cdc.gov/resource/xkb8-kh2a.csv?$limit=200000' "
            f"-o {RAW_PATH.relative_to(ROOT)}"
        )
    df = pd.read_csv(RAW_PATH, low_memory=False)
    return df


def aggregate_state_year(df: pd.DataFrame) -> pd.DataFrame:
    """Pull the December 12-month-ending count per state-year for the
    Synthetic opioids (T40.4) indicator. Combine NY (state=="NY", excludes
    NYC) with YC (NYC only) into a single NY total because the rest of the
    panels are state-grain."""
    syn = df[df["indicator"] == INDICATOR].copy()
    # December gives the calendar-year-end 12-month-ending count.
    dec = syn[syn["month"] == "December"].copy()
    # predicted_value is the model-completed value (used when a state's
    # raw data has data-quality issues); reported "data_value" agrees with
    # predicted_value when both are present, so prefer predicted_value for
    # consistent coverage.
    dec["count"] = pd.to_numeric(dec["predicted_value"], errors="coerce")
    # Fall back to data_value if predicted_value is missing.
    dec["count"] = dec["count"].fillna(
        pd.to_numeric(dec["data_value"], errors="coerce")
    )
    dec = dec[["state", "year", "count"]].copy()
    # Combine NY + YC (NYC) into total NY.
    ny = dec[dec["state"].isin(["NY", "YC"])].groupby("year")["count"].sum(
        min_count=1).reset_index()
    ny["state"] = "NY"
    others = dec[~dec["state"].isin(["NY", "YC"])]
    out = pd.concat([others, ny[["state", "year", "count"]]], ignore_index=True)
    out["year"] = out["year"].astype(int)
    return out


def load_state_population() -> pd.DataFrame:
    pop = pd.read_csv(POP_PATH)
    pop["year"] = pop["year"].astype(int)
    return pop[["state_abbr", "year", "population"]]


def expand_to_full_panel(agg: pd.DataFrame, pop: pd.DataFrame) -> pd.DataFrame:
    """Build the state-year panel with synthetic_opioid_death_rate per 100k.

    Years: YEAR_RANGE.
      Pre-2015: zero-fill (the fentanyl epidemic was negligible pre-2014).
      2015-2024: count / population * 1e5 if both observed; else NaN.
    """
    abbrs = sorted(ABBR_TO_FIPS_NAME)
    years = list(range(YEAR_RANGE[0], YEAR_RANGE[1] + 1))
    rows = []
    agg_idx = agg.set_index(["state", "year"])["count"]
    pop_idx = pop.set_index(["state_abbr", "year"])["population"]
    for abbr in abbrs:
        fips, name = ABBR_TO_FIPS_NAME[abbr]
        for y in years:
            if y < 2015:
                rate = 0.0
            else:
                count = agg_idx.get((abbr, y), np.nan)
                p = pop_idx.get((abbr, y), np.nan)
                if pd.notna(count) and pd.notna(p) and p > 0:
                    rate = float(count) / float(p) * 1e5
                else:
                    rate = np.nan
            rows.append({
                "state_fips": fips,
                "state_abbr": abbr,
                "state": name,
                "year": y,
                "synthetic_opioid_death_rate": rate,
            })
    return (pd.DataFrame(rows)
            .sort_values(["state_fips", "year"])
            .reset_index(drop=True))


def main() -> None:
    print(f"Reading {RAW_PATH.relative_to(ROOT)} ...")
    raw = load_raw()
    print(f"  raw rows: {len(raw):,}")

    agg = aggregate_state_year(raw)
    print(f"  state-year cells with December counts (NYC merged into NY): "
          f"{len(agg):,}")

    pop = load_state_population()
    print(f"  state population rows: {len(pop):,}")

    full = expand_to_full_panel(agg, pop)
    print(f"  expanded panel ({YEAR_RANGE[0]}-{YEAR_RANGE[1]}): {len(full):,}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    full.to_csv(OUT_PATH, index=False)
    print(f"  Wrote {OUT_PATH.relative_to(ROOT)}")

    # Coverage by year.
    cov = (full.assign(has=full["synthetic_opioid_death_rate"].notna())
                .groupby("year")["has"].sum()
                .reset_index().rename(columns={"has": "n_states_with_rate"}))
    print("\nCoverage of synthetic_opioid_death_rate by year:")
    print(cov.to_string(index=False))

    # Spot-check: TX, FL, OH around the fentanyl peak.
    chk = full[(full["state_abbr"].isin(["TX", "FL", "OH"]))
               & (full["year"].isin([2015, 2018, 2020, 2022]))]
    print("\nSpot-check (TX, FL, OH; 2015, 2018, 2020, 2022):")
    print(chk[["state_abbr", "year", "synthetic_opioid_death_rate"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
