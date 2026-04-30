"""Audit the balanced panels in data/processed.

Reports per panel:
- expected vs actual rows, states, years
- balance status (no missing state-year cells)
- per-variable coverage (non-null counts and observed year range)
- categorical groups (laws, crime, demo, economy, market, suicide, ownership)
- gaps vs the ideal econometric stack (suicide rates, RAND HFR, FS/S, granular crime)

Writes:
    data/processed/panel_audit_summary.csv      one row per panel
    data/processed/panel_audit_variables.csv    one row per (panel, variable)
    data/processed/panel_audit_gaps.csv         one row per identified gap
    data/processed/panel_audit_report.md        human-readable summary
"""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
DATA = ROOT / "data"
OUT = PROC

PANELS = OrderedDict([
    ("panel_core",        ("panel_core_1979_2024.csv",        1979, 2024)),
    ("panel_demographic", ("panel_demographic_1990_2024.csv", 1990, 2024)),
    ("panel_market",      ("panel_market_1999_2024.csv",      1999, 2024)),
    ("panel_modern",      ("panel_modern_2008_2024.csv",      2008, 2024)),
])

# Variable groups for human-readable categorization.
LAW_PREFIXES = (
    "amm", "assault", "magazine", "tenroundlimit", "onefeature",
    "universal", "gunshow", "statechecks", "ammbackground",
    "permit", "registration", "defactoreg", "loststolen", "onepermonth",
    "waiting", "age18", "age21",
    "gvro", "locked", "liability",
    "mcdv", "incident", "dvro", "exparte", "stalking", "relinquishment",
    "permitconcealed", "mayissue", "nosyg",
    "opencarry",
    "dealer", "residential", "theft",
    "violent", "violenth", "violentpartial",
    "college", "elementary",
)

CRIME_VARS = (
    "violent_crime", "violent_rate",
    "property_crime", "property_rate",
    "homicide", "homicide_rate",
    "robbery", "robbery_rate",
    "rape", "rape_rate",
    "aggravated_assault", "aggravated_assault_rate",
    "burglary", "burglary_rate",
    "larceny", "larceny_rate",
    "motor_vehicle_theft", "motor_vehicle_theft_rate",
)

ECON_VARS = (
    "unemployment_rate",
    "pcpi_nominal", "pcpi_real_2024",
    "median_hh_income_nominal", "median_hh_income_real_2024",
    "poverty_rate",
    "ln_pcpi_real_2024", "ln_population",
)

MARKET_VARS = (
    "nics_total", "nics_handgun", "nics_long_gun", "nics_multiple",
    "nics_permit", "nics_permit_recheck", "nics_other",
    "nics_total_per_100k",
)

DEMO_VARS = (
    "population",
    "share_white_nh", "share_black_nh", "share_hispanic",
    "share_male", "share_age_15_24", "share_age_25_44",
    "share_bachelors_plus",
)

# These are the variables an "ideal" gun-policy panel adds beyond what the four
# balanced panels currently include.
IDEAL_ADDITIONS = OrderedDict([
    ("firearm_suicides",         "Firearm suicides (count) - integrate from firearm_suicide_homicide_dataset_v2.tab (1979-2023)"),
    ("total_suicides",           "Total suicides (count) - same source, 1979-2023"),
    ("firearm_suicide_rate",     "Firearm suicides per 100k - derive from counts and population"),
    ("total_suicide_rate",       "Total suicides per 100k - derive from counts and population"),
    ("firearm_homicides",        "Firearm homicides (count) - same source"),
    ("nonfirearm_homicides",     "Nonfirearm homicides (count) - same source"),
    ("firearm_homicide_rate",    "Firearm homicide per 100k - derive"),
    ("nonfirearm_homicide_rate", "Nonfirearm homicide per 100k - derive"),
    ("ownership_fss",            "FS/S ownership proxy - same source (use only as descriptive)"),
    ("ownership_rand",           "RAND household firearm ownership rate (1980-2016) - integrate from TL-354"),
    ("ownership_rand_se",        "RAND HFR standard error - same source"),
    ("homicide", "Homicide count - integrate from OpenCrime granular file (1979-2024)"),
    ("homicide_rate", "Homicide rate per 100k - derive"),
    ("robbery",  "Robbery count - OpenCrime"),
    ("robbery_rate",  "Robbery rate per 100k - derive"),
    ("rape",     "Rape count - OpenCrime (note: 2013 definition change)"),
    ("rape_rate",     "Rape rate per 100k - derive"),
    ("aggravated_assault",       "Agg assault count - OpenCrime"),
    ("aggravated_assault_rate",  "Agg assault rate per 100k - derive"),
    ("burglary", "Burglary count - OpenCrime"),
    ("burglary_rate", "Burglary rate per 100k - derive"),
    ("larceny",  "Larceny count - OpenCrime"),
    ("larceny_rate",  "Larceny rate per 100k - derive"),
    ("motor_vehicle_theft",      "MV theft count - OpenCrime"),
    ("motor_vehicle_theft_rate", "MV theft rate per 100k - derive"),
])


def categorize(col: str) -> str:
    if col in CRIME_VARS:
        return "crime"
    if col in ECON_VARS:
        return "economy"
    if col in MARKET_VARS:
        return "market"
    if col in DEMO_VARS:
        return "demographics"
    if col in {"firearm_suicides", "total_suicides", "firearm_suicide_rate", "total_suicide_rate",
               "firearm_homicides", "nonfirearm_homicides",
               "firearm_homicide_rate", "nonfirearm_homicide_rate"}:
        return "suicide_homicide"
    if col in {"ownership_fss", "ownership_rand", "ownership_rand_se"}:
        return "ownership"
    if col == "lawtotal":
        return "law_total"
    if col.startswith(LAW_PREFIXES):
        return "law"
    if col in {"state", "state_abbr", "year", "acs_dataset"}:
        return "key"
    return "other"


def audit_panel(name: str, fname: str, ystart: int, yend: int):
    df = pd.read_csv(PROC / fname)
    n = len(df)
    states = df["state_abbr"].nunique() if "state_abbr" in df.columns else df["state"].nunique()
    years = df["year"].nunique()
    expected = (yend - ystart + 1) * 50
    expected_years = yend - ystart + 1
    is_balanced = (n == expected) and (states == 50) and (years == expected_years)

    grouped = df.groupby(["state_abbr", "year"]).size().reset_index(name="n")
    duplicate_rows = (grouped["n"] > 1).sum()

    summary_row = OrderedDict([
        ("panel", name),
        ("file", fname),
        ("expected_year_range", f"{ystart}-{yend}"),
        ("rows_actual", n),
        ("rows_expected", expected),
        ("states_actual", states),
        ("years_actual", years),
        ("years_expected", expected_years),
        ("variables_total", df.shape[1]),
        ("duplicate_state_year_rows", int(duplicate_rows)),
        ("is_balanced", bool(is_balanced)),
    ])

    var_rows = []
    for col in df.columns:
        non_null = df[col].notna().sum()
        if df[col].dtype.kind in "fiub":
            ymin = df.loc[df[col].notna(), "year"].min() if non_null else None
            ymax = df.loc[df[col].notna(), "year"].max() if non_null else None
        else:
            ymin = ymax = None
        var_rows.append(OrderedDict([
            ("panel", name),
            ("variable", col),
            ("category", categorize(col)),
            ("dtype", str(df[col].dtype)),
            ("non_null", int(non_null)),
            ("missing", int(n - non_null)),
            ("observed_first_year", int(ymin) if pd.notna(ymin) else None),
            ("observed_last_year", int(ymax) if pd.notna(ymax) else None),
        ]))
    return summary_row, var_rows, set(df.columns)


def detect_gaps(present_by_panel: dict[str, set[str]]):
    rows = []
    for var, note in IDEAL_ADDITIONS.items():
        for panel in PANELS:
            if var not in present_by_panel[panel]:
                rows.append(OrderedDict([
                    ("panel", panel),
                    ("variable", var),
                    ("status", "missing"),
                    ("recommendation", note),
                ]))
    return rows


def write_markdown_report(summary, variables, gaps):
    lines = ["# Balanced panel audit", ""]
    lines.append(f"_Generated: {pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M UTC')}_")
    lines.append("")
    lines.append("## Panel-level summary")
    lines.append("")
    lines.append("| Panel | Years | Rows | States | Years (n) | Vars | Dupes | Balanced |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in summary:
        lines.append(f"| `{r['panel']}` | {r['expected_year_range']} | "
                     f"{r['rows_actual']:,}/{r['rows_expected']:,} | "
                     f"{r['states_actual']} | {r['years_actual']}/{r['years_expected']} | "
                     f"{r['variables_total']} | {r['duplicate_state_year_rows']} | "
                     f"{'✅' if r['is_balanced'] else '❌'} |")

    lines.append("")
    lines.append("## Variables by category, per panel")
    lines.append("")
    var_df = pd.DataFrame(variables)
    cats_in_order = ["key", "law", "law_total", "crime", "economy", "market", "demographics",
                     "suicide_homicide", "ownership", "other"]
    for panel_name in PANELS:
        sub = var_df[var_df["panel"] == panel_name]
        cat_counts = sub.groupby("category").size().reindex(cats_in_order, fill_value=0)
        lines.append(f"### `{panel_name}`")
        lines.append("")
        lines.append("| Category | n vars | Vars (alpha) |")
        lines.append("|---|---|---|")
        for cat in cats_in_order:
            n = int(cat_counts.get(cat, 0))
            if n == 0:
                continue
            vars_in_cat = sub.loc[sub["category"] == cat, "variable"].sort_values().tolist()
            preview = ", ".join(f"`{v}`" for v in vars_in_cat[:8])
            if len(vars_in_cat) > 8:
                preview += f", ... (+{len(vars_in_cat) - 8} more)"
            lines.append(f"| {cat} | {n} | {preview} |")
        lines.append("")

    lines.append("## Gaps vs the ideal econometric stack")
    lines.append("")
    lines.append("These variables exist in raw data on disk and on the public website JSON, but are not yet integrated into the saved balanced panel CSVs in `data/processed/`. The `scripts/build_website_data.py` pipeline already loads and merges them, so the same merge code can be lifted into the panel build.")
    lines.append("")
    if not gaps:
        lines.append("_No gaps detected._")
    else:
        gaps_df = pd.DataFrame(gaps)
        for var in gaps_df["variable"].unique():
            note = gaps_df[gaps_df["variable"] == var]["recommendation"].iloc[0]
            missing_panels = sorted(gaps_df[gaps_df["variable"] == var]["panel"].tolist())
            lines.append(f"- `{var}` &mdash; missing in: {', '.join(missing_panels)}")
            lines.append(f"  - {note}")

    lines.append("")
    lines.append("## How to apply the fixes")
    lines.append("")
    lines.append("Run `python scripts/augment_panels.py` (added in the same change) which:")
    lines.append("")
    lines.append("1. Reads each existing balanced panel.")
    lines.append("2. Merges in the granular crime variables from `data/opencrime_state_trends.json` (with the documented NC&rarr;ND 2022 reassignment).")
    lines.append("3. Merges in suicide/homicide counts and the FS/S ownership proxy from `data/firearm_suicide_homicide_dataset_v2.tab`.")
    lines.append("4. Merges in the RAND household firearm ownership rate (1980-2016) from the TL-354 spreadsheet.")
    lines.append("5. Computes derived rates (per 100k) for any count-only variables.")
    lines.append("6. Writes augmented panels alongside the originals as `data/processed/{panel_name}_augmented.csv` and re-runs balance checks.")

    (PROC / "panel_audit_report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    summary_rows = []
    var_rows = []
    present = {}
    for name, (fname, ystart, yend) in PANELS.items():
        s, v, cols = audit_panel(name, fname, ystart, yend)
        summary_rows.append(s)
        var_rows.extend(v)
        present[name] = cols

    gap_rows = detect_gaps(present)

    pd.DataFrame(summary_rows).to_csv(PROC / "panel_audit_summary.csv", index=False)
    pd.DataFrame(var_rows).to_csv(PROC / "panel_audit_variables.csv", index=False)
    pd.DataFrame(gap_rows).to_csv(PROC / "panel_audit_gaps.csv", index=False)
    write_markdown_report(summary_rows, var_rows, gap_rows)

    print("Wrote:")
    for fn in ("panel_audit_summary.csv", "panel_audit_variables.csv",
               "panel_audit_gaps.csv", "panel_audit_report.md"):
        print(f"  data/processed/{fn}")
    print()
    print("Panel summary:")
    for s in summary_rows:
        bal = "OK" if s["is_balanced"] else "UNBALANCED"
        print(f"  {s['panel']:<20} {s['expected_year_range']:<10} "
              f"rows={s['rows_actual']:,} vars={s['variables_total']} {bal}")
    print()
    print(f"Identified {len(gap_rows)} missing-variable cells across {len(IDEAL_ADDITIONS)} target additions.")


if __name__ == "__main__":
    main()
