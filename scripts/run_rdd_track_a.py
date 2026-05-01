"""Run lib_rdd.run_full_battery for the 4 Track A policies (SYG, magazine,
age21 handgun, AWB). The 3 original policies (permitless carry, red flag,
UBC) already have RDD outputs from the Track B work; this fills the gap
so the report's RDD section covers all 7 policies (CAP excluded — Tufts
panel has no usable CAP variable).

Two of the four policies (SYG, age21 handgun) have treatment variables
that are NOT in the county panel's law_* columns. We pull them from the
state panel and join down by (state_fips, year). Magazine and AWB are
already in the county panel as law_magazine and law_assault.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from lib_rdd import (
    PROC,
    OUTCOMES_PRIMARY, OUTCOMES_SECONDARY,
    load_county_panel_with_borders,
    run_full_battery,
)

ROOT = Path(__file__).resolve().parent.parent

# 2-digit FIPS state codes.
ABBR_TO_FIPS = {
    "AL":"01","AK":"02","AZ":"04","AR":"05","CA":"06","CO":"08","CT":"09","DE":"10",
    "DC":"11","FL":"12","GA":"13","HI":"15","ID":"16","IL":"17","IN":"18","IA":"19",
    "KS":"20","KY":"21","LA":"22","ME":"23","MD":"24","MA":"25","MI":"26","MN":"27",
    "MS":"28","MO":"29","MT":"30","NE":"31","NV":"32","NH":"33","NJ":"34","NM":"35",
    "NY":"36","NC":"37","ND":"38","OH":"39","OK":"40","OR":"41","PA":"42","RI":"44",
    "SC":"45","SD":"46","TN":"47","TX":"48","UT":"49","VT":"50","VA":"51","WA":"53",
    "WV":"54","WI":"55","WY":"56",
}

# (slug, treatment_var, direction, source)
#   source = "county" if the column is already in county_panel as law_<var>
#   source = "state" if we need to join from panel_core_augmented
POLICIES = [
    ("stand_your_ground",   "nosyg",            "1to0", "state"),
    ("magazine_ban",        "law_magazine",     "0to1", "county"),
    ("age21_handgun",       "age21handgunsale", "0to1", "state"),
    ("assault_weapons_ban", "law_assault",      "0to1", "county"),
]


def join_state_law(panel: pd.DataFrame, tufts_var: str) -> tuple[pd.DataFrame, str]:
    """Join a state-level Tufts indicator down to county-year via
    (state_fips, year). Returns (joined_panel, treatment_var_name) where
    the treatment var is renamed `law_<tufts_var>` to follow the project
    convention.
    """
    state = pd.read_csv(PROC / "panel_core_augmented.csv",
                        usecols=["state_abbr", "year", tufts_var])
    state["state_fips"] = state["state_abbr"].map(ABBR_TO_FIPS)
    state = state[state["state_fips"].notna()].copy()
    new_col = f"law_{tufts_var}"
    state = state.rename(columns={tufts_var: new_col})[["state_fips", "year", new_col]]
    panel = panel.merge(state, on=["state_fips", "year"], how="left")
    return panel, new_col


def main() -> None:
    print("Loading county panel + border distances ...")
    base = load_county_panel_with_borders()
    print(f"  {len(base):,} county-year rows")

    for slug, raw_var, direction, source in POLICIES:
        print(f"\n{'='*70}\n  Running RDD for {slug}\n{'='*70}")
        if source == "state":
            panel, treatment_var = join_state_law(base.copy(), raw_var)
            print(f"  Joined state-level {raw_var} as {treatment_var}; "
                  f"{panel[treatment_var].notna().mean():.1%} non-null coverage")
        else:
            panel = base
            treatment_var = raw_var
        out_dir = ROOT / "outputs" / f"{slug}_rdd"
        summary = run_full_battery(
            panel,
            treatment_var=treatment_var,
            direction=direction,
            policy_name=slug,
            out_dir=out_dir,
            outcomes_primary=OUTCOMES_PRIMARY,
            outcomes_secondary=OUTCOMES_SECONDARY,
        )
        print(f"  Done: {summary}")


if __name__ == "__main__":
    main()
