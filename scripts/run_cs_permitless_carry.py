"""Phase 5 (research): Callaway-Sant'Anna ATT(g, t) for permitless carry.

Treatment: a state's first 1->0 switch in Tufts `permitconcealed` (the
state stops requiring a permit to carry concealed). Treatment is
treated as absorbing.

Outcomes (run side-by-side):
  firearm_suicide_rate, firearm_homicide_rate, homicide_rate,
  motor_vehicle_theft_rate (placebo).

Specs (4): {OR, RA} x {broad, strict} where:
  - broad  = every never-treated state
  - strict = control state must be shall-issue (mayissue==0) AND
             permit-required (permitconcealed==1) for every year of
             [g-5, g+5]

All shared CS21 machinery is in scripts/cs_lib.py. This file is
intentionally short -- it just wires up the policy-specific knobs and
calls the shared functions. The companion script
scripts/run_cs_red_flag.py uses the same library with different
treatment / strict-rule arguments, so the two analyses are guaranteed
to share their estimator behaviour.

Outputs:
  outputs/permitless_carry_cs/{att_gt,event_study,overall_att,cohort_n,dropped_log}.csv
  outputs/permitless_carry_cs/figures/event_study_{control_rule}_{spec}_4panel.svg
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
ADO_TABLE = ROOT / "outputs" / "permitless_carry_suicide_audit" / "treatment_adoption_table.csv"
OUT = ROOT / "outputs" / "permitless_carry_cs"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

# v2 firearm suicide / homicide file ends 2023, so the audit excludes
# LA 2024 and SC 2024 from the mortality sample.
EXCLUDE_COHORTS_AFTER = 2023

STRICT_RULE_VARS = ("permitconcealed", "mayissue")
STRICT_RULE_VALUES = (1, 0)


def main():
    print("Loading panel ...")
    panel = load_panel_core_augmented()
    print(f"  {len(panel):,} state-year rows in {ANALYSIS_YEARS[0]}-{ANALYSIS_YEARS[1]}")

    # We have the existing audit's treatment_adoption_table.csv as ground
    # truth for permitless-carry adoption years. derive_cohorts() would
    # also work but the audit table reflects manual review of partial-year
    # effective dates, so we prefer it.
    print("Loading cohorts from existing audit treatment_adoption_table.csv ...")
    t = pd.read_csv(ADO_TABLE)
    t = t[t["state_abbr"] != "DC"]
    treated = t[t["adoption_year"].notna()
                & t["included_in_mortality_sample"]
                & (t["adoption_year"] <= EXCLUDE_COHORTS_AFTER)].copy()
    treated["adoption_year"] = treated["adoption_year"].astype(int)
    cohorts: dict[int, list[str]] = {}
    dropped = []
    for _, r in treated.iterrows():
        g = int(r["adoption_year"])
        if g - 5 < ANALYSIS_YEARS[0]:
            dropped.append({"state_abbr": r["state_abbr"],
                            "adoption_year": g,
                            "dropped_reason": "adoption too early for 5-yr pre-period"})
            continue
        cohorts.setdefault(g, []).append(r["state_abbr"])
    nt = t[(t["adoption_year"].isna()) & (t["starts_permit_required"] == 1)]
    never_treated = set(nt["state_abbr"].tolist())

    print(f"  cohorts: {len(cohorts)} (years {sorted(cohorts)})")
    for g in sorted(cohorts):
        print(f"    {g}: {len(cohorts[g])} states ({', '.join(cohorts[g])})")
    print(f"  never-treated controls: {len(never_treated)}")
    print(f"  dropped from analysis: {len(dropped)}")

    pd.DataFrame([{"g_cohort": g, "n_states": len(s), "states": ",".join(s)}
                  for g, s in sorted(cohorts.items())]
                 ).to_csv(OUT / "cohort_n.csv", index=False)
    pd.DataFrame(dropped).to_csv(OUT / "dropped_log.csv", index=False)

    print("\nstrict-rule control pool size by cohort:")
    for g in sorted(cohorts):
        strict = strict_control_pool(panel, sorted(never_treated), g,
                                     STRICT_RULE_VARS, STRICT_RULE_VALUES)
        print(f"  {g}: {len(strict)} states ({', '.join(strict)})")

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
                             title_suffix="-- permitless carry (permitconcealed)")
            print(f"  Wrote {(FIG / f'event_study_{control_rule}_{spec}_4panel.svg').relative_to(ROOT)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
