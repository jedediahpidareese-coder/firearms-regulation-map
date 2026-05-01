"""Phase 6 spatial RDD: permitless concealed carry.

Treatment: first 1->0 switch in Tufts `law_permitconcealed` (the indicator
that a permit is required for concealed carry; flipping to 0 means the
state went permitless). Joined down to the county panel from the state
panel as `law_permitconcealed`.

Identification: Dube-Lester-Reich (2010, RESTAT) contiguous-county-pair
DiD adapted to firearm policy. County FE + state-pair x year FE; within-
strip sample defined by Census 2020 population centroids (see Section 2.12
of data_appendix.md). Headline bandwidth 100 km (selected per Agent B's
diagnostic on straddling-pair counts), state-cluster SE.

Outcomes: PRIMARY = true county-level Kaplan UCR rates; SECONDARY = state-
joined-down mortality (no within-state county variation, included as
robustness only -- see methodology).

Outputs (under outputs/permitless_carry_rdd/):
    cohort_n.csv         which states adopted in which year
    headline.csv         one row per outcome at the headline spec
    robustness.csv       all 10 BATTERY_SPECS x all outcomes
    event_study.csv      per-outcome event-time coefficients
    figures/event_study_{primary,secondary}.svg
"""

from __future__ import annotations

from pathlib import Path

from lib_rdd import (
    load_county_panel_with_borders,
    run_full_battery,
    OUTCOMES_PRIMARY, OUTCOMES_SECONDARY,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "permitless_carry_rdd"


def main() -> None:
    print("Loading county panel + border distances ...")
    panel = load_county_panel_with_borders()
    print(f"  {len(panel):,} county-year rows")

    summary = run_full_battery(
        panel,
        treatment_var="law_permitconcealed",
        direction="1to0",
        policy_name="permitless_carry",
        out_dir=OUT,
        outcomes_primary=OUTCOMES_PRIMARY,
        outcomes_secondary=OUTCOMES_SECONDARY,
    )
    print(f"\nDone. Summary: {summary}")


if __name__ == "__main__":
    main()
