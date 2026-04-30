"""Phase 5h: Callaway-Sant'Anna ATT(g, t) for universal background checks.

Treatment: first 0->1 switch in Tufts `universal` (universal background
check at point of purchase for ALL firearms by both licensed dealers
and private sellers). Treatment is treated as absorbing.

Older state UBC laws (CA 1991, CT 1999, HI 1981, RI 1990) adopted before
our 1999+ panel begins or have no usable pre-period; they are excluded
as already-treated and they are also excluded from the never-treated
control pool. The modern adoption wave we estimate effects for runs
2013-2021 (DE, CO, NY 2013; WA 2014; OR 2015; NV 2017; VT 2018; NM 2019;
VA 2020; MD 2021).

Strict control rule: control state must have `universal == 0` AND
`universalpermit == 0` for every year of [g-5, g+5] -- i.e., no UBC
mechanism of any kind during the relevant window.

All shared CS21 machinery is in scripts/cs_lib.py.

Outputs:
  outputs/ubc_cs/{att_gt,event_study,overall_att,cohort_n,dropped_log}.csv
  outputs/ubc_cs/figures/event_study_{control_rule}_{spec}_4panel.svg
  outputs/ubc_cs/methodology.md (written separately)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from cs_lib import (
    OUTCOMES, ANALYSIS_YEARS,
    load_panel_core_augmented, derive_cohorts, strict_control_pool,
    run_one_outcome, event_study_aggregations, overall_att,
    plot_event_study,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "ubc_cs"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

EXCLUDE_COHORTS_AFTER = 2023

# Strict control rule: a never-UBC state must have universal==0 AND
# universalpermit==0 for every year of [g-5, g+5]. This excludes states
# that have any UBC mechanism (point-of-purchase or via permit) during
# the relevant window.
STRICT_RULE_VARS = ("universal", "universalpermit")
STRICT_RULE_VALUES = (0, 0)


def main():
    print("Loading panel ...")
    panel = load_panel_core_augmented()
    print(f"  {len(panel):,} state-year rows in {ANALYSIS_YEARS[0]}-{ANALYSIS_YEARS[1]}")

    print("Deriving UBC cohorts (treatment = first 0->1 switch in `universal`) ...")
    cohorts, raw_never, dropped = derive_cohorts(
        panel, treatment_var="universal", direction="0to1",
        min_pre_k=5, exclude_after=EXCLUDE_COHORTS_AFTER,
    )
    print(f"  cohorts: {len(cohorts)} (years {sorted(cohorts)})")
    for g in sorted(cohorts):
        print(f"    {g}: {len(cohorts[g])} states ({', '.join(cohorts[g])})")

    # Refine never-treated: must also have universalpermit == 0 throughout
    # the panel window so they're truly never-UBC, not "UBC via permit"
    # masquerading as never-treated. (Otherwise our control group would
    # include states like HI/MA that have permit-based UBC.)
    never_treated = set()
    excluded_due_to_permit_ubc = []
    for s in raw_never:
        sub = panel[panel["state_abbr"] == s]
        if (sub["universalpermit"] == 0).all():
            never_treated.add(s)
        else:
            excluded_due_to_permit_ubc.append(s)
    print(f"  never-treated controls (universal==0 AND universalpermit==0 throughout): {len(never_treated)}")
    if excluded_due_to_permit_ubc:
        print(f"  excluded due to having universalpermit==1 at some point: "
              f"{', '.join(sorted(excluded_due_to_permit_ubc))}")
    print(f"  cohorts dropped (too-early or post-EXCLUDE_COHORTS_AFTER): {len(dropped)}")

    pd.DataFrame([{"g_cohort": g, "n_states": len(s), "states": ",".join(s)}
                  for g, s in sorted(cohorts.items())]
                 ).to_csv(OUT / "cohort_n.csv", index=False)
    pd.DataFrame(dropped + [{"state_abbr": s, "adoption_year": None,
                              "dropped_reason": "had universalpermit==1 at some point"}
                             for s in excluded_due_to_permit_ubc]
                 ).to_csv(OUT / "dropped_log.csv", index=False)

    print("\nstrict-rule control pool size by cohort:")
    for g in sorted(cohorts):
        strict = strict_control_pool(panel, sorted(never_treated), g,
                                     STRICT_RULE_VARS, STRICT_RULE_VALUES)
        print(f"  {g}: {len(strict)} states ({', '.join(strict[:8])}{'...' if len(strict) > 8 else ''})")

    print("\nRunning ATT(g, t) for each (outcome, spec, control_rule) ...")
    pieces = []
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            for outcome in OUTCOMES:
                print(f"  control_rule={control_rule}  spec={spec}  {outcome}")
                sub = run_one_outcome(panel, outcome, cohorts, never_treated,
                                      spec=spec, control_rule=control_rule,
                                      strict_rule_vars=STRICT_RULE_VARS,
                                      strict_rule_values=STRICT_RULE_VALUES)
                pieces.append(sub)
    att_df = pd.concat(pieces, ignore_index=True)
    att_df.to_csv(OUT / "att_gt.csv", index=False)
    print(f"  Wrote {len(att_df):,} (outcome, spec, control_rule, g, t) rows")

    print("\nAggregating ...")
    es_df = event_study_aggregations(att_df)
    es_df.to_csv(OUT / "event_study.csv", index=False)
    overall_df = overall_att(att_df)
    overall_df.to_csv(OUT / "overall_att.csv", index=False)

    print("\nOverall post-treatment ATT (per 100,000):")
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            print(f"\n  --- control_rule = {control_rule},  spec = {spec} ---")
            sub = overall_df[(overall_df["spec"] == spec)
                             & (overall_df["control_rule"] == control_rule)]
            for _, r in sub.iterrows():
                sig = "**" if abs(r["z"]) >= 1.96 else "  "
                print(f"  {sig} {r['outcome']:<26}  ATT = {r['att_overall_post']:>+8.3f}  "
                      f"(SE {r['se_overall_post']:.3f}, z {r['z']:>+5.2f})  "
                      f"pre-trends z = {r['z_pretrends']:>+5.2f}")

    print("\nPlotting event-study figures ...")
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            es_filtered = es_df[es_df["control_rule"] == control_rule]
            plot_event_study(es_filtered,
                             FIG / f"event_study_{control_rule}_{spec}_4panel.png",
                             spec, OUTCOMES,
                             title_suffix="-- universal background checks (universal)")
            print(f"  Wrote {(FIG / f'event_study_{control_rule}_{spec}_4panel.svg').relative_to(ROOT)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
