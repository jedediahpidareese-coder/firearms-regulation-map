"""SCM (Abadie-Diamond-Hainmueller 2010) for state laws raising the
minimum age for handgun purchase above the federal floor of 18.

In-window cohorts from outputs/age21_handgun_audit/treatment_adoption_table.csv:
  WV-2010, WY-2010 (13+ post; ample)
  FL-2018, VT-2018 (5 post; good)
  WA-2019 (4 post; marginal but OK)
  CO-2023 (0-1 post; deferred)

Headline outcome is firearm suicide -- the literature (Webster et al.,
Anestis et al., Crifasi 2015) consistently identifies youth-band firearm
suicide as the channel for age-21 effects. We don't have age-stratified
suicide here so we use all-ages firearm_suicide_rate as a proxy; the
caveat is that adult suicides may dilute any youth-specific effect.

Outputs: outputs/age21_handgun_scm/{state}_{g}/{weights, trajectories,
placebo}.csv + figures/{outcome}.svg per case.
"""
from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
import pandas as pd
from cs_lib import load_panel_core_augmented
from lib_scm import run_scm_for_case, eligible_donors_simple

ROOT = Path(__file__).resolve().parent.parent
OUT_BASE = ROOT / "outputs" / "age21_handgun_scm"
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
    {"state": "WV", "label": "West Virginia", "g": 2010},
    {"state": "WY", "label": "Wyoming",       "g": 2010},
    {"state": "FL", "label": "Florida",       "g": 2018},
    {"state": "VT", "label": "Vermont",       "g": 2018},
    {"state": "WA", "label": "Washington",    "g": 2019},
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
            panel, treated_state=state, treated_var="age21handgunsale",
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
