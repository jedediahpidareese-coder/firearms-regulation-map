"""County-grain Callaway-Sant'Anna ATT(g, t) for permitless carry.

Treatment: a state's first 1->0 switch in the Tufts `law_permitconcealed`
indicator (the state stops requiring a permit to carry concealed). Treatment
is treated as absorbing. The cohort is the SET OF ALL COUNTIES in adopting
states; SE clustering is at the state level so within-state correlation
induced by the state-level treatment is properly accounted for.

This is the county-grain parallel of `scripts/run_cs_permitless_carry.py`
and shares its policy-specific knobs (treatment variable, strict-rule
filter, exclude-after cutoff) one-for-one. Only the underlying machinery
differs - see `scripts/lib_cs_county.py` for details.

Outcomes (8): five Kaplan UCR county-level rates that we now have at
county granularity (violent crime, murder, property crime, burglary, MVT
placebo) plus three state-joined-down mortality rates that we keep for
side-by-side comparison with the state-grain pipeline. The mortality
ones have NO within-state variation and so are identification-equivalent
to the state-grain analysis.

Specs (4): {OR, RA} x {broad, strict} where:
  - broad  = every never-treated state's counties
  - strict = control state must be shall-issue (mayissue==0) AND
             permit-required (permitconcealed==1) for every year of
             [g-5, g+5]; we then use the COUNTIES of the surviving
             control states as the control pool.

We do NOT exclude 2024 cohorts because the county UCR panel runs through
2024. The state-grain pipeline excluded them (EXCLUDE_COHORTS_AFTER=2023)
because the firearm mortality outcomes ended in 2023; here that only
affects the joined-down state mortality outcomes (their post-2023 (g, t)
cells will simply have missing values and be skipped).

Outputs:
  outputs/permitless_carry_cs_county/{att_gt,event_study,overall_att,
                                      cohort_n,dropped_log}.csv
  outputs/permitless_carry_cs_county/figures/event_study_{control_rule}_{spec}_4panel.svg
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from lib_cs_county import (
    OUTCOMES_COUNTY, ANALYSIS_YEARS,
    load_county_panel_2009_2024,
    derive_state_cohorts_for_county, strict_control_pool_county,
    run_one_outcome_county, event_study_aggregations_county,
    overall_att_county, plot_event_study_county,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "permitless_carry_cs_county"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

# County panel runs 2009-2024; include all cohorts within that window.
EXCLUDE_COHORTS_AFTER = 2024

# Strict control rule mirrors the state-grain version exactly.
STRICT_RULE_VARS = ("law_permitconcealed", "law_mayissue")
STRICT_RULE_VALUES = (1, 0)


def main():
    print("Loading county panel ...")
    panel = load_county_panel_2009_2024()
    print(f"  {len(panel):,} county-year rows in "
          f"{ANALYSIS_YEARS[0]}-{ANALYSIS_YEARS[1]}, "
          f"{panel['county_fips'].nunique():,} counties, "
          f"{panel['state_fips'].nunique()} states")

    print("Deriving permitless-carry cohorts (treatment = first 1->0 switch "
          "in law_permitconcealed) ...")
    cohorts, never_treated, dropped = derive_state_cohorts_for_county(
        panel, treatment_var="law_permitconcealed", direction="1to0",
        min_pre_k=5, exclude_after=EXCLUDE_COHORTS_AFTER,
    )
    print(f"  cohorts: {len(cohorts)} (years {sorted(cohorts)})")
    for g in sorted(cohorts):
        n_states = len(cohorts[g])
        n_counties = panel[panel["state_fips"].isin(cohorts[g])
                           & (panel["year"] == g - 1)]["county_fips"].nunique()
        abbrs = [panel[panel["state_fips"] == sf]["state_abbr"].iloc[0]
                 for sf in cohorts[g]]
        print(f"    {g}: {n_states} states ({', '.join(abbrs)}), "
              f"{n_counties} counties")
    print(f"  never-treated controls: {len(never_treated)} states")
    print(f"  dropped: {len(dropped)}")

    cohort_rows = []
    for g, sfs in sorted(cohorts.items()):
        abbrs = [panel[panel["state_fips"] == sf]["state_abbr"].iloc[0]
                 for sf in sfs]
        n_counties = panel[panel["state_fips"].isin(sfs)
                           & (panel["year"] == g - 1)]["county_fips"].nunique()
        cohort_rows.append({"g_cohort": g,
                             "n_states": len(sfs),
                             "n_counties": n_counties,
                             "state_fips": ",".join(sfs),
                             "states": ",".join(abbrs)})
    pd.DataFrame(cohort_rows).to_csv(OUT / "cohort_n.csv", index=False)
    pd.DataFrame(dropped).to_csv(OUT / "dropped_log.csv", index=False)

    print("\nstrict-rule control pool size by cohort:")
    for g in sorted(cohorts):
        strict = strict_control_pool_county(
            panel, sorted(never_treated), g,
            STRICT_RULE_VARS, STRICT_RULE_VALUES)
        n_counties = panel[panel["state_fips"].isin(strict)
                           & (panel["year"] == g - 1)]["county_fips"].nunique()
        print(f"  {g}: {len(strict)} states / {n_counties} counties")

    print("\nRunning ATT(g, t) for each (outcome, spec, control_rule) ...")
    pieces = []
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            for outcome in OUTCOMES_COUNTY:
                print(f"  control_rule={control_rule}  spec={spec}  {outcome}")
                sub = run_one_outcome_county(
                    panel, outcome, cohorts, never_treated,
                    spec=spec, control_rule=control_rule,
                    strict_rule_vars=STRICT_RULE_VARS,
                    strict_rule_values=STRICT_RULE_VALUES)
                pieces.append(sub)
    att_df = pd.concat(pieces, ignore_index=True)
    att_df.to_csv(OUT / "att_gt.csv", index=False)
    print(f"  Wrote {len(att_df):,} (outcome, spec, control_rule, g, t) rows")

    print("\nAggregating ...")
    es_df = event_study_aggregations_county(att_df)
    es_df.to_csv(OUT / "event_study.csv", index=False)
    overall_df = overall_att_county(att_df)
    overall_df.to_csv(OUT / "overall_att.csv", index=False)

    print("\nOverall post-treatment ATT (per 100,000):")
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            print(f"\n  --- control_rule = {control_rule},  spec = {spec} ---")
            sub = overall_df[(overall_df["spec"] == spec)
                             & (overall_df["control_rule"] == control_rule)]
            for _, r in sub.iterrows():
                sig = "**" if abs(r["z"]) >= 1.96 else "  "
                print(f"  {sig} {r['outcome']:<32}  "
                      f"ATT = {r['att_overall_post']:>+10.3f}  "
                      f"(SE {r['se_overall_post']:.3f}, z {r['z']:>+6.2f})  "
                      f"pre-trends z = {r['z_pretrends']:>+5.2f}")

    print("\nPlotting event-study figures ...")
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            es_filtered = es_df[es_df["control_rule"] == control_rule]
            plot_event_study_county(
                es_filtered,
                FIG / f"event_study_{control_rule}_{spec}_4panel.svg",
                spec, OUTCOMES_COUNTY,
                title_suffix="-- permitless carry (law_permitconcealed)")
            print(f"  Wrote "
                  f"{(FIG / f'event_study_{control_rule}_{spec}_4panel.svg').relative_to(ROOT)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
