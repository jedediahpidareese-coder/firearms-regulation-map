"""Augment each balanced panel with the variables that exist in raw data on disk
but were not yet integrated:

- Granular FBI/OpenCrime crime components: homicide, robbery, rape, agg assault,
  burglary, larceny, motor vehicle theft (counts and per-100k rates).
  The same NC->ND 2022 reassignment from the existing crime_repairs_log is applied.
- Firearm suicides, total suicides, firearm homicides, nonfirearm homicides
  (counts and per-100k rates), plus the FS/S ownership proxy.
- RAND TL-354 household firearm ownership rate (HFR) and standard error,
  1980-2016, 50 states.

The augmentation preserves the original (state_abbr, year) row layout - balance
of the underlying panel is unchanged. Augmented variables can have missing cells
within the panel window when their source series ends earlier (e.g. RAND ends in
2016; FS/S ends in 2023). A coverage report is written for each.

Outputs:
    data/processed/{panel}_augmented.csv
    data/processed/panel_augmented_balance.csv
    data/processed/panel_augmented_coverage.csv
"""

from __future__ import annotations

import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"

sys.path.insert(0, str(ROOT / "scripts"))
from build_website_data import (  # noqa: E402
    load_crime_detail, load_suicide_homicide, load_rand_ownership,
)

PANELS = OrderedDict([
    ("panel_core",        ("panel_core_1979_2024.csv",        1979, 2024)),
    ("panel_demographic", ("panel_demographic_1990_2024.csv", 1990, 2024)),
    ("panel_market",      ("panel_market_1999_2024.csv",      1999, 2024)),
    ("panel_modern",      ("panel_modern_2008_2024.csv",      2008, 2024)),
])

ADDED_VARS = [
    # crime granular (from OpenCrime detail)
    "homicide", "homicide_rate",
    "robbery", "robbery_rate",
    "rape", "rape_rate",
    "aggravated_assault", "aggravated_assault_rate",
    "burglary", "burglary_rate",
    "larceny", "larceny_rate",
    "motor_vehicle_theft", "motor_vehicle_theft_rate",
    # suicide / firearm-related deaths
    "firearm_suicides", "total_suicides",
    "firearm_suicide_rate", "total_suicide_rate",
    "firearm_homicides", "nonfirearm_homicides",
    "firearm_homicide_rate", "nonfirearm_homicide_rate",
    "homicide_rate_kalesan",
    # ownership
    "ownership_fss",
    "ownership_rand", "ownership_rand_se",
]


def merge_safely(base: pd.DataFrame, addition: pd.DataFrame, label: str) -> pd.DataFrame:
    """Left-merge addition onto base by (state_abbr, year), with a duplicate guard."""
    grouped = addition.groupby(["state_abbr", "year"]).size()
    if (grouped > 1).any():
        dupes = grouped[grouped > 1].head(5)
        raise RuntimeError(f"Duplicate (state, year) rows in {label}:\n{dupes}")
    overlap = [c for c in addition.columns
               if c not in ("state_abbr", "year") and c in base.columns]
    if overlap:
        addition = addition.drop(columns=overlap)
    return base.merge(addition, on=["state_abbr", "year"], how="left")


def augment(panel_name: str, fname: str, ystart: int, yend: int):
    base = pd.read_csv(PROC / fname)
    n_in = len(base)

    crime = load_crime_detail()
    sh = load_suicide_homicide()
    rand = load_rand_ownership()

    augmented = base.copy()
    augmented = merge_safely(augmented, crime, "OpenCrime granular")
    augmented = merge_safely(augmented, sh, "firearm_suicide_homicide_dataset_v2")
    augmented = merge_safely(augmented, rand, "RAND TL-354")

    # Sanity: row count and (state,year) layout unchanged.
    if len(augmented) != n_in:
        raise RuntimeError(f"{panel_name}: augment changed row count {n_in} -> {len(augmented)}")
    grp = augmented.groupby(["state_abbr", "year"]).size()
    if (grp > 1).any():
        raise RuntimeError(f"{panel_name}: duplicate (state, year) after augment")

    out_path = PROC / f"{panel_name}_augmented.csv"
    augmented.to_csv(out_path, index=False)

    # Coverage rows.
    coverage = []
    for var in ADDED_VARS:
        if var not in augmented.columns:
            continue
        s = augmented[["state_abbr", "year", var]].dropna(subset=[var])
        coverage.append(OrderedDict([
            ("panel", panel_name),
            ("variable", var),
            ("non_null", int(len(s))),
            ("expected_in_window", n_in),
            ("coverage_pct", round(100 * len(s) / n_in, 1) if n_in else 0.0),
            ("first_year_observed", int(s["year"].min()) if len(s) else None),
            ("last_year_observed", int(s["year"].max()) if len(s) else None),
            ("states_observed", int(s["state_abbr"].nunique()) if len(s) else 0),
        ]))

    return augmented, coverage


def main():
    balance_rows = []
    coverage_rows = []
    for name, (fname, ystart, yend) in PANELS.items():
        df, coverage = augment(name, fname, ystart, yend)
        coverage_rows.extend(coverage)
        rows = len(df)
        states = df["state_abbr"].nunique()
        years = df["year"].nunique()
        expected = (yend - ystart + 1) * 50
        balance_rows.append(OrderedDict([
            ("panel", name + "_augmented"),
            ("year_range", f"{ystart}-{yend}"),
            ("rows", rows),
            ("rows_expected", expected),
            ("states", states),
            ("years", years),
            ("variables", df.shape[1]),
            ("balanced", rows == expected and states == 50),
        ]))
        print(f"{name + '_augmented':<35} rows={rows:,}/{expected:,} states={states} years={years} vars={df.shape[1]}")

    pd.DataFrame(balance_rows).to_csv(PROC / "panel_augmented_balance.csv", index=False)
    pd.DataFrame(coverage_rows).to_csv(PROC / "panel_augmented_coverage.csv", index=False)
    print()
    print("Wrote:")
    for name in PANELS:
        print(f"  data/processed/{name}_augmented.csv")
    print("  data/processed/panel_augmented_balance.csv")
    print("  data/processed/panel_augmented_coverage.csv")


if __name__ == "__main__":
    main()
