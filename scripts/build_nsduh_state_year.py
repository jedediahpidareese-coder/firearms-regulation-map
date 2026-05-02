"""Build state-year mental-illness prevalence covariates from the SAMHSA
National Survey on Drug Use and Health (NSDUH) Small Area Estimation
(SAE) state-prevalence tables.

Source: SAMHSA NSDUH state releases
   https://www.samhsa.gov/data/data-we-collect/nsduh-national-survey-drug-use-and-health/state-releases
For each release year (the SAE tables are 2-year averages), we download
the percent-prevalence CSV zip and extract the AMI / SMI / MDE tables.
The 2-year midpoint convention codes the second year (e.g., 2018-2019 ->
year 2019) to align with the publication year. The 2019-2020 release was
not produced by SAMHSA due to COVID-19 methodology changes; year 2020 is
NaN. The 2020-2021 release was also affected by methodology breaks (NSDUH
moved to web-based interviewing in 2021); SAMHSA cautions that 2020/2021
estimates "should not be pooled or compared with prior years," so the
year-2021 cell is NaN here -- including it would mix apples and oranges.

Coverage:
  - 1999-2015: zero-fill (we did not download pre-2015-2016 NSDUH state
    SAE releases; AMI/SMI columns existed in older NSDUH state tables but
    methodology and table organization differ markedly across editions
    and pre-2008 the state-level NSDUH was a different survey).
  - 2016-2024: observed via the 7 SAE releases:
        2015-2016 -> coded year 2016 (AMI tab 27 in NSDUHsaeExcelTab27-2016)
        2016-2017 -> coded year 2017
        2017-2018 -> coded year 2018
        2018-2019 -> coded year 2019
        2019-2020 -> not produced (COVID); year 2020 NaN
        2020-2021 -> methodology break; year 2021 NaN
        2021-2022 -> coded year 2022
        2022-2023 -> coded year 2023
        2023-2024 -> coded year 2024
    Year-2020/2021 NaN propagates through the augment merge and shows up
    as a hole in the panel. The estimator covariate stack handles NaN by
    falling back to OR (no covariates) for that cell.

Output: data/processed/nsduh_mental_illness_state_year.csv
  state_fips, state_abbr, state, year, ami_pct, smi_pct, mde_pct
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROC = DATA_DIR / "processed"

ZIP_DIR = DATA_DIR / "nsduh_zips"
OUT_PATH = PROC / "nsduh_mental_illness_state_year.csv"

YEAR_RANGE = (1999, 2024)

# release zip filename -> coded year (2-year midpoint = the LATER year).
# (Earlier releases code year as the LATER of the two NSDUH years per the
# SAMHSA convention: 2018-2019 estimate -> "year 2019".)
RELEASES = {
    "nsduh_2016.zip": 2016,
    "nsduh_2017.zip": 2017,
    "nsduh_2018.zip": 2018,
    "nsduh_2019.zip": 2019,
    "nsduh_2022.zip": 2022,
    "nsduh_2023.zip": 2023,
    "nsduh_2024.zip": 2024,
}

NAME_TO_FIPS_ABBR = {
    "Alabama":              ("01", "AL"),
    "Alaska":               ("02", "AK"),
    "Arizona":              ("04", "AZ"),
    "Arkansas":             ("05", "AR"),
    "California":           ("06", "CA"),
    "Colorado":             ("08", "CO"),
    "Connecticut":          ("09", "CT"),
    "Delaware":             ("10", "DE"),
    "District of Columbia": ("11", "DC"),
    "Florida":              ("12", "FL"),
    "Georgia":              ("13", "GA"),
    "Hawaii":               ("15", "HI"),
    "Idaho":                ("16", "ID"),
    "Illinois":             ("17", "IL"),
    "Indiana":              ("18", "IN"),
    "Iowa":                 ("19", "IA"),
    "Kansas":               ("20", "KS"),
    "Kentucky":             ("21", "KY"),
    "Louisiana":            ("22", "LA"),
    "Maine":                ("23", "ME"),
    "Maryland":             ("24", "MD"),
    "Massachusetts":        ("25", "MA"),
    "Michigan":             ("26", "MI"),
    "Minnesota":            ("27", "MN"),
    "Mississippi":          ("28", "MS"),
    "Missouri":             ("29", "MO"),
    "Montana":              ("30", "MT"),
    "Nebraska":             ("31", "NE"),
    "Nevada":               ("32", "NV"),
    "New Hampshire":        ("33", "NH"),
    "New Jersey":           ("34", "NJ"),
    "New Mexico":           ("35", "NM"),
    "New York":             ("36", "NY"),
    "North Carolina":       ("37", "NC"),
    "North Dakota":         ("38", "ND"),
    "Ohio":                 ("39", "OH"),
    "Oklahoma":             ("40", "OK"),
    "Oregon":               ("41", "OR"),
    "Pennsylvania":         ("42", "PA"),
    "Rhode Island":         ("44", "RI"),
    "South Carolina":       ("45", "SC"),
    "South Dakota":         ("46", "SD"),
    "Tennessee":            ("47", "TN"),
    "Texas":                ("48", "TX"),
    "Utah":                 ("49", "UT"),
    "Vermont":              ("50", "VT"),
    "Virginia":             ("51", "VA"),
    "Washington":           ("53", "WA"),
    "West Virginia":        ("54", "WV"),
    "Wisconsin":            ("55", "WI"),
    "Wyoming":              ("56", "WY"),
}

KEYWORDS = {
    "ami_pct": [r"\bany mental illness\b"],
    "smi_pct": [r"\bserious mental illness\b"],
    "mde_pct": [r"\bmajor depressive episode\b"],
}


def _classify(title: str) -> str | None:
    """Map a table-1 title to one of our three measure keys."""
    t = title.lower()
    # Exclude co-occurring SUD tables (same title contains "any mental illness")
    if "co-occurring" in t or "co occurring" in t:
        return None
    for key, pats in KEYWORDS.items():
        for p in pats:
            if re.search(p, t):
                return key
    return None


def _parse_pct(s) -> float:
    if pd.isna(s):
        return float("nan")
    s = str(s).strip()
    if s == "" or s.lower() == "nan":
        return float("nan")
    s = s.rstrip("%").strip()
    # Strip stray BOM and quotes.
    s = s.lstrip("﻿").strip('"').strip()
    try:
        return float(s)
    except ValueError:
        return float("nan")


def parse_zip(zip_path: Path, year: int) -> dict[str, dict[str, float]]:
    """Return {state_name: {ami_pct: x, smi_pct: y, mde_pct: z}}.

    Each NSDUH release zip has many CSV tables; we look at the first row
    (table title) to identify which measure each table reports, then read
    the data block (after the row that starts with "Order").
    """
    out: dict[str, dict[str, float]] = {}
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            if not name.endswith(".csv"):
                continue
            with z.open(name) as f:
                raw = f.read().decode("utf-8", errors="replace")
            # First non-empty line is title.
            lines = raw.splitlines()
            if not lines:
                continue
            title = lines[0].split(",")[0].strip().strip('"').lstrip("﻿")
            measure = _classify(title)
            if measure is None:
                continue
            # Find the row that starts the table; the column header row
            # begins with a quoted "Order" cell across all years 2016-2024.
            start = None
            for i, line in enumerate(lines):
                first = line.split(",")[0].strip().strip('"').lstrip("﻿")
                if first == "Order":
                    start = i
                    break
            if start is None:
                continue
            block = "\n".join(lines[start:])
            from io import StringIO
            df = pd.read_csv(StringIO(block))
            # Find the "State" column.
            state_col = None
            for c in df.columns:
                if c.strip().lower() == "state":
                    state_col = c
                    break
            if state_col is None:
                continue
            # The 18+ Estimate column varies in name across releases:
            #   "18+ Estimate" (most),  "Total" (some older), or after
            #   the "State" column, the first data column is the 18+ point
            #   estimate. We pick by header-name first, fall back to the
            #   first column AFTER 'state' as 18+.
            est_col = None
            for c in df.columns:
                cl = c.strip().lower()
                if cl in ("18+ estimate", "18+ point estimate",
                          "12+ estimate", "12+ point estimate",
                          "estimate", "point estimate"):
                    # MDE is reported among 12+ in newer releases, AMI/SMI
                    # are 18+; we accept either as the "all-adults"
                    # population for the coding task.
                    est_col = c
                    break
            if est_col is None:
                # First non-Order/State column.
                cols = list(df.columns)
                for c in cols:
                    if c.strip().lower() not in ("order", "state"):
                        est_col = c
                        break
            if est_col is None:
                continue
            df = df[[state_col, est_col]].copy()
            df.columns = ["state_name", "value"]
            df["state_name"] = df["state_name"].astype(str).str.strip()
            df["value"] = df["value"].apply(_parse_pct)
            for _, r in df.iterrows():
                sn = r["state_name"]
                if sn not in NAME_TO_FIPS_ABBR:
                    continue
                if pd.isna(r["value"]):
                    continue
                if sn not in out:
                    out[sn] = {}
                # If the same measure appears twice (rare), prefer the
                # FIRST 18+ Estimate column rather than overwriting.
                if measure not in out[sn]:
                    out[sn][measure] = float(r["value"])
    return out


def expand_to_full_panel(per_year: dict[int, dict[str, dict[str, float]]]) -> pd.DataFrame:
    abbrs = [(name, fips, abbr)
             for name, (fips, abbr) in NAME_TO_FIPS_ABBR.items()]
    years = list(range(YEAR_RANGE[0], YEAR_RANGE[1] + 1))
    rows = []
    for state_name, fips, abbr in abbrs:
        for y in years:
            row = {
                "state_fips": fips,
                "state_abbr": abbr,
                "state": state_name,
                "year": y,
                "ami_pct": np.nan,
                "smi_pct": np.nan,
                "mde_pct": np.nan,
            }
            if y <= 2015:
                # Pre-2016 zero-fill (we did not pull older releases).
                row["ami_pct"] = 0.0
                row["smi_pct"] = 0.0
                row["mde_pct"] = 0.0
            elif y in per_year:
                d = per_year[y].get(state_name, {})
                for k in ("ami_pct", "smi_pct", "mde_pct"):
                    if k in d:
                        row[k] = float(d[k])
            # else: NaN (e.g., year 2020, 2021 -- not produced / break)
            rows.append(row)
    return (pd.DataFrame(rows)
            .sort_values(["state_fips", "year"])
            .reset_index(drop=True))


def main() -> None:
    if not ZIP_DIR.exists():
        raise FileNotFoundError(
            f"NSDUH zip directory not found: {ZIP_DIR}. "
            "Download the 2016-2024 SAE percent zips from samhsa.gov "
            "(see docstring for URL pattern) into data/nsduh_zips/."
        )
    per_year: dict[int, dict[str, dict[str, float]]] = {}
    for fname, year in RELEASES.items():
        zp = ZIP_DIR / fname
        if not zp.exists():
            print(f"  [skip] {fname}: not present (year {year} -> NaN)")
            continue
        print(f"Parsing {fname} (coded year {year}) ...")
        d = parse_zip(zp, year)
        n_states = sum(1 for s in d.values() if s)
        print(f"  parsed {n_states} states with at least one measure")
        per_year[year] = d

    full = expand_to_full_panel(per_year)
    print(f"\nExpanded panel ({YEAR_RANGE[0]}-{YEAR_RANGE[1]}): {len(full):,} rows")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    full.to_csv(OUT_PATH, index=False)
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")

    cov = (full[full["year"] >= 2016]
           .groupby("year")[["ami_pct", "smi_pct", "mde_pct"]]
           .agg(lambda s: s.notna().sum())
           .reset_index())
    print("\nCoverage of ami_pct / smi_pct / mde_pct by year (2016+):")
    print(cov.to_string(index=False))

    chk = full[(full["state_abbr"].isin(["TX", "FL", "OH"]))
               & (full["year"].isin([2018, 2019, 2022, 2024]))]
    print("\nSpot-check (TX, FL, OH; 2018, 2019, 2022, 2024):")
    print(chk[["state_abbr", "year", "ami_pct", "smi_pct", "mde_pct"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
