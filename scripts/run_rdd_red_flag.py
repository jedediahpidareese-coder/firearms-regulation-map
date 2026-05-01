"""Phase 6 spatial RDD: civil-petition red-flag laws (extreme risk
protection orders).

Treatment: first 0->1 switch in Tufts `law_gvro` -- the indicator that the
state allows civilian petition for an ERPO. The older law-enforcement-only
ERPO category (gvrolawenforcement) is NOT considered treated here, matching
the convention used by the state-level CS21 and stacked-DiD analyses.

Identification: Dube-Lester-Reich (2010, RESTAT) contiguous-county-pair
DiD. County FE + state-pair x year FE; within-strip sample defined by
Census 2020 population centroids. Headline bandwidth 100 km, state-cluster SE.

Caveat (per Agent B diagnostic): straddling-pair counts are smaller for
red-flag than for permitless carry (mean 11/yr vs 25/yr at 100 km), and
descriptive cross-border outcome gaps in the pre-period flag potential
selection. Pair x year FE is the primary defense; results should be read
alongside the donut and spillover-filter robustness rows.

Outputs (under outputs/red_flag_rdd/):
    cohort_n.csv, headline.csv, robustness.csv, event_study.csv,
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
OUT = ROOT / "outputs" / "red_flag_rdd"


def main() -> None:
    print("Loading county panel + border distances ...")
    panel = load_county_panel_with_borders()
    print(f"  {len(panel):,} county-year rows")

    summary = run_full_battery(
        panel,
        treatment_var="law_gvro",
        direction="0to1",
        policy_name="red_flag",
        out_dir=OUT,
        outcomes_primary=OUTCOMES_PRIMARY,
        outcomes_secondary=OUTCOMES_SECONDARY,
    )
    print(f"\nDone. Summary: {summary}")


if __name__ == "__main__":
    main()
