"""Phase 5e: Callaway-Sant'Anna ATT(g, t) for Stand-Your-Ground (SYG) laws
(also called "no duty to retreat" castle-doctrine extensions).

Treatment: first 1->0 switch in Tufts `nosyg`, the indicator that the state
has NO stand-your-ground law. So a state-year with `nosyg == 1` retains a
duty to retreat in public; `nosyg == 0` means SYG is in force. Adoption is
the first year `nosyg` flips from 1 to 0. This matches the Tufts codebook
("A state with a stand your ground law is coded as a 0").

Outcomes (same six as the other policy analyses):
  firearm_suicide_rate, nonfirearm_suicide_rate, total_suicide_rate,
  firearm_homicide_rate, homicide_rate, motor_vehicle_theft_rate (placebo).

Specs (4): {OR, RA} x {broad, strict} where:
  - broad  = every never-treated state (states whose `nosyg == 1` for the
             entire panel)
  - strict = control state must have `nosyg == 1` for every year of
             [g-5, g+5] (i.e., truly duty-to-retreat throughout the
             relevant comparison window)

Outputs:
  outputs/stand_your_ground_cs/{att_gt,event_study,overall_att,cohort_n,dropped_log}.csv
  outputs/stand_your_ground_cs/figures/event_study_{control_rule}_{spec}_4panel.svg
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
OUT = ROOT / "outputs" / "stand_your_ground_cs"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

# v2 firearm suicide / homicide file ends 2023, so we exclude 2024 cohorts.
EXCLUDE_COHORTS_AFTER = 2023

# Strict control rule for SYG-naive states: require nosyg==1 throughout
# the [g-5, g+5] window (i.e., duty-to-retreat in force on both sides of
# the focal cohort's adoption). Single-variable rule, but the cs_lib API
# wants tuples.
STRICT_RULE_VARS = ("nosyg",)
STRICT_RULE_VALUES = (1,)


def main():
    print("Loading panel ...")
    panel = load_panel_core_augmented()
    print(f"  {len(panel):,} state-year rows in {ANALYSIS_YEARS[0]}-{ANALYSIS_YEARS[1]}")

    print("Deriving SYG cohorts (treatment = first 1->0 switch in nosyg) ...")
    cohorts, never_treated, dropped = derive_cohorts(
        panel, treatment_var="nosyg", direction="1to0",
        min_pre_k=5, exclude_after=EXCLUDE_COHORTS_AFTER,
    )
    print(f"  cohorts: {len(cohorts)} (years {sorted(cohorts)})")
    for g in sorted(cohorts):
        print(f"    {g}: {len(cohorts[g])} states ({', '.join(cohorts[g])})")
    print(f"  never-treated controls (nosyg never flips to 0): {len(never_treated)}")
    print(f"  dropped: {len(dropped)}")

    pd.DataFrame([{"g_cohort": g, "n_states": len(s), "states": ",".join(s)}
                  for g, s in sorted(cohorts.items())]
                 ).to_csv(OUT / "cohort_n.csv", index=False)
    pd.DataFrame(dropped).to_csv(OUT / "dropped_log.csv", index=False)

    # Show how strict pool shrinks each cohort.
    print("\nstrict-rule control pool size by cohort (nosyg==1 throughout [g-5, g+5]):")
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
                sub = run_one_outcome_all_tiers(panel, outcome, cohorts, never_treated,
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
                             title_suffix="-- stand-your-ground (nosyg)")
            print(f"  Wrote {(FIG / f'event_study_{control_rule}_{spec}_4panel.svg').relative_to(ROOT)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
