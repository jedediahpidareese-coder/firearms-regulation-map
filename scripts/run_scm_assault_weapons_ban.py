"""SCM (Abadie-Diamond-Hainmueller 2010) for assault weapons bans.

The CS21 results for AWB are too noisy to interpret credibly: only 4
treated states across 3 cohorts, and at event-time +5 only the 2013-MD
cohort contributes (n=1). The literature (Klarevas-Conner-Hemenway 2019,
Koper-Roth 2001 for the federal AWB sunset) handles small-cohort policies
with SCM. This runner does that.

In-window cohorts from outputs/assault_weapons_ban_audit/treatment_adoption_table.csv:
  MD-2013 (10 post-period years; ample for SCM)
  DE-2022, IL-2023, WA-2023 (only 1-2 post-period years observed -- too
    short for SCM convergence per the Crifasi 2015 / McCourt 2020
    convention of >= 3 post-period years; SKIPPED here, will rejoin
    when v2 mortality data covers 2024+)

Outputs: outputs/assault_weapons_ban_scm/{state}_{g}/{weights, trajectories,
placebo}.csv + figures/{outcome}.svg per case.
"""
from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
import pandas as pd
from cs_lib import load_panel_core_augmented
from lib_scm import run_scm_for_case, eligible_donors_simple

ROOT = Path(__file__).resolve().parent.parent
OUT_BASE = ROOT / "outputs" / "assault_weapons_ban_scm"
OUT_BASE.mkdir(parents=True, exist_ok=True)

ANALYSIS_YEARS = (1999, 2023)
PRE_YEARS_TARGET = 12

OUTCOMES = OrderedDict([
    ("firearm_homicide_rate",     "Firearm homicide rate (per 100k)"),
    ("homicide_rate",             "Total homicide rate (per 100k)"),
    ("motor_vehicle_theft_rate",  "Motor vehicle theft rate (per 100k) [placebo]"),
])

CASES = [
    {"state": "MD", "label": "Maryland", "g": 2013},
    # DE-2022, IL-2023, WA-2023 deferred until v2 mortality covers 2024+.
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
            panel, treated_state=state, treated_var="assault",
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
