"""SCM (Abadie-Diamond-Hainmueller 2010) for state-level large-capacity
magazine bans.

In-window cohorts from outputs/magazine_ban_audit/treatment_adoption_table.csv:
  CO-2013, CT-2013 (10 post-period years; good for SCM)
  VT-2018 (5 post; OK)
  DE-2022, RI-2022, WA-2022, IL-2023 (1-2 post; deferred)

The literature for LCM bans is thin -- Klarevas-Conner-Hemenway (2019) is
the canonical paper but they used state-FE neg-binomial on mass-shooting
counts (an outcome we don't have). For our standard outcomes, SCM per
state is the most credible alternative to the underpowered CS21.

Outputs: outputs/magazine_ban_scm/{state}_{g}/{weights, trajectories,
placebo}.csv + figures/{outcome}.svg per case.
"""
from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
import pandas as pd
from cs_lib import load_panel_core_augmented
from lib_scm import run_scm_for_case, eligible_donors_simple

ROOT = Path(__file__).resolve().parent.parent
OUT_BASE = ROOT / "outputs" / "magazine_ban_scm"
OUT_BASE.mkdir(parents=True, exist_ok=True)

ANALYSIS_YEARS = (1999, 2023)
PRE_YEARS_TARGET = 12

OUTCOMES = OrderedDict([
    ("firearm_suicide_rate",      "Firearm suicide rate (per 100k)"),
    ("firearm_homicide_rate",     "Firearm homicide rate (per 100k)"),
    ("homicide_rate",             "Total homicide rate (per 100k)"),
    ("motor_vehicle_theft_rate",  "Motor vehicle theft rate (per 100k) [placebo]"),
])

CASES = [
    {"state": "CO", "label": "Colorado",    "g": 2013},
    {"state": "CT", "label": "Connecticut", "g": 2013},
    {"state": "VT", "label": "Vermont",     "g": 2018},
]


def main() -> None:
    panel = load_panel_core_augmented()
    print(f"Loaded panel: {len(panel):,} state-year rows in "
          f"{ANALYSIS_YEARS[0]}-{ANALYSIS_YEARS[1]}")
    for case in CASES:
        state, g, label = case["state"], case["g"], case["label"]
        out_dir = OUT_BASE / f"{state}_{g}"
        print(f"\n=== {state} ({label}), adoption year g = {g} ===")
        donors = eligible_donors_simple(
            panel, treated_state=state, treated_var="magazine",
            treated_var_eligible_value=0,
            pre_window=(max(g - PRE_YEARS_TARGET, ANALYSIS_YEARS[0]), ANALYSIS_YEARS[1]),
        )
        print(f"  donor pool ({len(donors)}): {', '.join(donors)}")
        run_scm_for_case(
            panel, treated_state=state, g=g, donors=donors,
            outcomes=OUTCOMES, out_dir=out_dir,
            pre_years_target=PRE_YEARS_TARGET,
            analysis_years=ANALYSIS_YEARS, label=label,
        )
    print("\nDone.")


if __name__ == "__main__":
    main()
