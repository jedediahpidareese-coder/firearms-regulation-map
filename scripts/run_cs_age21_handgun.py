"""Phase 5j: Callaway-Sant'Anna ATT(g, t) for state-level minimum-age-21
laws on handgun purchase.

Treatment: first 0->1 switch in Tufts `age21handgunsale`, the indicator
that the state restricts handgun purchases (from BOTH licensed dealers
AND private sellers) to buyers age 21 or older. This raises the minimum
age above the federal floor of 18 for private handgun sales (the federal
floor is 21 only for FFL handgun sales; long guns and private handgun
transfers default to 18 under federal law).

There are two related Tufts variables (`age21handgunsalecommercial`,
`age21handgunsaleprivate`) that decompose this into the two channels;
we pick the joint indicator `age21handgunsale` because it most cleanly
maps to "raised the minimum age for any handgun purchase," which is
the policy treatment we want to estimate.

Outcomes (same six as the other policy analyses):
  firearm_suicide_rate, nonfirearm_suicide_rate, total_suicide_rate,
  firearm_homicide_rate, homicide_rate, motor_vehicle_theft_rate (placebo).

Specs (4): {OR, RA} x {broad, strict} where:
  - broad  = every never-treated state
  - strict = control state must have age21handgunsale==0 for every year
             of [g-5, g+5] (i.e., truly age-21-naive throughout the
             relevant window)

The headline outcome is firearm suicide. The literature focuses on the
youth/young-adult age band (Webster et al., Anestis), but this project
does not have age-stratified mortality data, so the headline estimate
is for ALL ages -- which understates any policy-attributable change in
the targeted 18-20 group by a factor on the order of (population age
18-20) / (total adult population). See appendix for caveats.

Outputs:
  outputs/age21_handgun_cs/{att_gt,event_study,overall_att,cohort_n,dropped_log}.csv
  outputs/age21_handgun_cs/figures/event_study_{control_rule}_{spec}_4panel.svg
  outputs/age21_handgun_cs/methodology.md (written separately)
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
OUT = ROOT / "outputs" / "age21_handgun_cs"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

# v2 firearm suicide / homicide file ends 2023, so we exclude 2024 cohorts.
EXCLUDE_COHORTS_AFTER = 2023

# Strict control rule: a never-age21-handgun state must have
# age21handgunsale == 0 for every year of [g-5, g+5]. Single rule, since
# unlike UBC there is no "permit-based age-21 enforcement" alternate
# channel that would masquerade as never-treated.
STRICT_RULE_VARS = ("age21handgunsale",)
STRICT_RULE_VALUES = (0,)


def main():
    print("Loading panel ...")
    panel = load_panel_core_augmented()
    print(f"  {len(panel):,} state-year rows in {ANALYSIS_YEARS[0]}-{ANALYSIS_YEARS[1]}")

    print("Deriving age21-handgun cohorts (treatment = first 0->1 switch in age21handgunsale) ...")
    cohorts, never_treated, dropped = derive_cohorts(
        panel, treatment_var="age21handgunsale", direction="0to1",
        min_pre_k=5, exclude_after=EXCLUDE_COHORTS_AFTER,
    )
    print(f"  cohorts: {len(cohorts)} (years {sorted(cohorts)})")
    for g in sorted(cohorts):
        print(f"    {g}: {len(cohorts[g])} states ({', '.join(cohorts[g])})")
    print(f"  never-treated controls (age21handgunsale never flips to 1 from 0): {len(never_treated)}")
    print(f"  dropped: {len(dropped)}")

    pd.DataFrame([{"g_cohort": g, "n_states": len(s), "states": ",".join(s)}
                  for g, s in sorted(cohorts.items())]
                 ).to_csv(OUT / "cohort_n.csv", index=False)
    pd.DataFrame(dropped).to_csv(OUT / "dropped_log.csv", index=False)

    print("\nstrict-rule control pool size by cohort (age21handgunsale==0 throughout [g-5, g+5]):")
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
                             title_suffix="-- min age 21 for handgun purchase (age21handgunsale)")
            print(f"  Wrote {(FIG / f'event_study_{control_rule}_{spec}_4panel.svg').relative_to(ROOT)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
