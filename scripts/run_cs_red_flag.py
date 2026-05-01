"""Phase 5e: Callaway-Sant'Anna ATT(g, t) for civil-petition red-flag laws
(extreme risk protection orders).

Treatment: first 0->1 switch in Tufts `gvro`, the indicator that the state
allows civilian petition for an extreme risk protection order. (The older
law-enforcement-only ERPOs in CT/IN/FL/RI/VA live in `gvrolawenforcement`,
which we do NOT include here -- the modern wave studies the civil-petition
variant.)

Outcomes (same four as the permitless-carry analysis):
  firearm_suicide_rate, firearm_homicide_rate, homicide_rate,
  motor_vehicle_theft_rate (placebo).

Specs (4): {OR, RA} x {broad, strict} where:
  - broad  = every never-treated state
  - strict = control state must have gvro==0 AND gvrolawenforcement==0 for
             every year of [g-5, g+5] (i.e., truly red-flag-naive throughout
             the relevant window)

Outputs:
  outputs/red_flag_cs/{att_gt,event_study,overall_att,cohort_n,dropped_log}.csv
  outputs/red_flag_cs/figures/event_study_{control_rule}_{spec}_4panel.svg
  outputs/red_flag_cs/methodology.md (written separately)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from cs_lib import (
    OUTCOMES, ANALYSIS_YEARS,
    load_panel_core_augmented, derive_cohorts, strict_control_pool,
    run_one_outcome_all_tiers, event_study_aggregations, overall_att,
    plot_event_study,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "red_flag_cs"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

# v2 firearm suicide / homicide file ends 2023, so we exclude 2024 cohorts.
EXCLUDE_COHORTS_AFTER = 2023

# Strict control rule for red-flag-naive states.
STRICT_RULE_VARS = ("gvro", "gvrolawenforcement")
STRICT_RULE_VALUES = (0, 0)


def main():
    print("Loading panel ...")
    panel = load_panel_core_augmented()
    print(f"  {len(panel):,} state-year rows in {ANALYSIS_YEARS[0]}-{ANALYSIS_YEARS[1]}")

    print("Deriving GVRO cohorts (treatment = first 0->1 switch in gvro) ...")
    cohorts, never_treated, dropped = derive_cohorts(
        panel, treatment_var="gvro", direction="0to1",
        min_pre_k=5, exclude_after=EXCLUDE_COHORTS_AFTER,
    )
    print(f"  cohorts: {len(cohorts)} (years {sorted(cohorts)})")
    for g in sorted(cohorts):
        print(f"    {g}: {len(cohorts[g])} states ({', '.join(cohorts[g])})")
    print(f"  never-treated controls (gvro never flips to 1): {len(never_treated)}")
    print(f"  dropped: {len(dropped)}")

    pd.DataFrame([{"g_cohort": g, "n_states": len(s), "states": ",".join(s)}
                  for g, s in sorted(cohorts.items())]
                 ).to_csv(OUT / "cohort_n.csv", index=False)
    pd.DataFrame(dropped).to_csv(OUT / "dropped_log.csv", index=False)

    # Show how strict pool shrinks each cohort.
    print("\nstrict-rule control pool size by cohort (gvro==0 AND gvrolawenforcement==0 throughout [g-5, g+5]):")
    for g in sorted(cohorts):
        strict = strict_control_pool(panel, sorted(never_treated), g,
                                     STRICT_RULE_VARS, STRICT_RULE_VALUES)
        print(f"  {g}: {len(strict)} states ({', '.join(strict[:8])}{'...' if len(strict) > 8 else ''})")

    print("\nRunning ATT(g, t) for each (outcome, spec, control_rule, tier) ...")
    pieces = []
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            for outcome in OUTCOMES:
                print(f"  control_rule={control_rule}  spec={spec}  {outcome}")
                sub = run_one_outcome_all_tiers(
                    panel, outcome, cohorts, never_treated,
                    spec=spec, control_rule=control_rule,
                    strict_rule_vars=STRICT_RULE_VARS,
                    strict_rule_values=STRICT_RULE_VALUES,
                )
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
                             title_suffix="-- red-flag (gvro)")
            print(f"  Wrote {(FIG / f'event_study_{control_rule}_{spec}_4panel.svg').relative_to(ROOT)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
