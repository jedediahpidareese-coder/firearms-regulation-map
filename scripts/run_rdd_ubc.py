"""Phase 6 spatial RDD: universal background checks.

Treatment: first 0->1 switch in Tufts `law_universal` -- the indicator that
the state requires a background check on all firearm purchases (including
private sales), as distinct from the federal NICS check that applies only
to FFL transactions.

Identification: Dube-Lester-Reich (2010, RESTAT) contiguous-county-pair
DiD. County FE + state-pair x year FE; within-strip sample defined by
Census 2020 population centroids. Headline bandwidth 100 km, state-cluster SE.

Caveat (per Agent B diagnostic + RAND evidence reviews): UBC effects in
the literature are classified as inconclusive and the sample is dominated
by the 2013 cohort, leaving few post-period straddling pairs. We run the
RDD anyway as a parallel design to PTP-style point-of-sale background
check work (e.g., McCourt et al. 2020 AJPH four-state SCM).

Outputs (under outputs/ubc_rdd/):
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
OUT = ROOT / "outputs" / "ubc_rdd"


def main() -> None:
    print("Loading county panel + border distances ...")
    panel = load_county_panel_with_borders()
    print(f"  {len(panel):,} county-year rows")

    summary = run_full_battery(
        panel,
        treatment_var="law_universal",
        direction="0to1",
        policy_name="ubc",
        out_dir=OUT,
        outcomes_primary=OUTCOMES_PRIMARY,
        outcomes_secondary=OUTCOMES_SECONDARY,
    )
    print(f"\nDone. Summary: {summary}")


if __name__ == "__main__":
    main()
