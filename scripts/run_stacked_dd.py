"""Phase 5i: Grier-style stacked DiD (Cengiz et al. 2019) with optional
entropy balancing (Hainmueller 2012) -- runs all three policies in one
pass for direct comparison with the CS21 results.

Optional flags:
  --with-covid    append the OxCGRT covid_stringency_mean covariate to
                  the RA spec (and to the EB-balancing target); write
                  outputs to outputs/{policy}_stackdd_with_covid/.
  --with-efna     append the Fraser Institute efna_overall covariate to
                  the RA / EB-balancing covariates. Combined with
                  --with-covid, output dir becomes
                  outputs/{policy}_stackdd_with_covid_efna/; alone, it is
                  outputs/{policy}_stackdd_with_efna/.
  --with-despair  append the deaths-of-despair stack
                  (synthetic_opioid_death_rate, freq_mental_distress_pct,
                  ami_pct). Combinable with --with-covid and --with-efna;
                  maximal output is
                  outputs/{policy}_stackdd_with_covid_efna_despair/.

For each policy (permitless carry, civil red-flag, UBC) and each of the
six outcomes used elsewhere in the project, we report three weighting
specifications:

  - unweighted          plain stacked DiD, no covariate adjustment
  - regression-adjusted (RA)  TWFE with covariates as linear controls
  - entropy-balanced    (EB)  controls reweighted (Hainmueller 2012) so
                              their baseline covariate moments match
                              the treated unit's baseline moments;
                              regression has no further covariates
                              (the weighting absorbs them)

The full doubly-robust spec (EB + RA) is logically possible but with
small per-stack samples it can be unstable; we skip it for clarity.
This is identical to the spec menu Grier, Krieger, and Munger 2024 use
(unweighted, EB-only) plus an RA-only spec for comparison.

Outputs (per policy):
  outputs/{policy}_stackdd/
    att_post.csv            one row per (outcome, weighting) with the
                            post-treatment ATT, SE, z, n, n_clusters
    event_study.csv         one row per (outcome, weighting, event_time)
    methodology.md          short policy-specific writeup linking back to
                            the corresponding _cs methodology
    figures/event_study_{weighting}_4panel.svg
"""

from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

from cs_lib import (
    OUTCOMES, ANALYSIS_YEARS,
    load_panel_core_augmented, derive_cohorts, strict_control_pool,
)
from lib_stacked_dd import (
    build_stacks, stack_eb_weights, twfe_within, twfe_event_study,
)
from cs_lib import plot_event_study  # we re-use the SVG plotter

ROOT = Path(__file__).resolve().parent.parent

# Same covariate menu used in the CS21 RA spec, for comparability.
from cs_lib import covariates_for, classify_outcome  # for outcome-aware tier covariates

# Legacy default; superseded by per-outcome tier lookup at run time.
CONTROLS = ["ln_population", "unemployment_rate", "ln_pcpi_real_2024"]
TIERS = ("minimal", "headline", "expanded")

POLICIES = [
    {
        "name": "permitless_carry",
        "treatment_var": "permitconcealed",
        "direction": "1to0",
        "strict_vars": ("permitconcealed", "mayissue"),
        "strict_vals": (1, 0),
        "exclude_after": 2023,
        "ado_table": ROOT / "outputs" / "permitless_carry_suicide_audit"
                                / "treatment_adoption_table.csv",
    },
    {
        "name": "red_flag",
        "treatment_var": "gvro",
        "direction": "0to1",
        "strict_vars": ("gvro", "gvrolawenforcement"),
        "strict_vals": (0, 0),
        "exclude_after": 2023,
        "ado_table": None,
    },
    {
        "name": "ubc",
        "treatment_var": "universal",
        "direction": "0to1",
        "strict_vars": ("universal", "universalpermit"),
        "strict_vals": (0, 0),
        "exclude_after": 2023,
        "ado_table": None,
    },
    {
        "name": "assault_weapons_ban",
        "treatment_var": "assault",
        "direction": "0to1",
        "strict_vars": ("assault",),
        "strict_vals": (0,),
        "exclude_after": 2023,
        "ado_table": None,
    },
    {
        "name": "age21_handgun",
        "treatment_var": "age21handgunsale",
        "direction": "0to1",
        "strict_vars": ("age21handgunsale",),
        "strict_vals": (0,),
        "exclude_after": 2023,
        "ado_table": None,
    },
    {
        "name": "magazine_ban",
        "treatment_var": "magazine",
        "direction": "0to1",
        "strict_vars": ("magazine",),
        "strict_vals": (0,),
        "exclude_after": 2023,
        "ado_table": None,
    },
    {
        "name": "stand_your_ground",
        "treatment_var": "nosyg",
        "direction": "1to0",
        "strict_vars": ("nosyg",),
        "strict_vals": (1,),
        "exclude_after": 2023,
        "ado_table": None,
    },
]


def cohorts_from_audit(panel: pd.DataFrame, ado_table_path: Path,
                       exclude_after: int):
    """Build cohorts from the existing permitless-carry audit's hand-curated
    treatment_adoption_table.csv so the stacked-DiD analysis uses the same
    cohort definitions the CS21 wrapper does for that policy."""
    t = pd.read_csv(ado_table_path)
    t = t[t["state_abbr"] != "DC"]
    treated = t[t["adoption_year"].notna()
                & t["included_in_mortality_sample"]
                & (t["adoption_year"] <= exclude_after)].copy()
    treated["adoption_year"] = treated["adoption_year"].astype(int)
    cohorts = {}
    dropped = []
    for _, r in treated.iterrows():
        g = int(r["adoption_year"])
        if g - 5 < ANALYSIS_YEARS[0]:
            dropped.append({"state_abbr": r["state_abbr"], "g": g,
                            "reason": "too early for 5-yr pre-period"})
            continue
        cohorts.setdefault(g, []).append(r["state_abbr"])
    nt = t[(t["adoption_year"].isna()) & (t["starts_permit_required"] == 1)]
    return cohorts, set(nt["state_abbr"].tolist()), dropped


def cohorts_from_panel(panel: pd.DataFrame, treatment_var: str,
                       direction: str, exclude_after: int):
    cohorts, never, dropped = derive_cohorts(
        panel, treatment_var=treatment_var, direction=direction,
        min_pre_k=5, exclude_after=exclude_after,
    )
    if treatment_var == "universal":
        # For UBC, also drop never-UBC states that have universalpermit==1
        # at any point (so the control pool is truly never-UBC of any kind).
        keep = set()
        for s in never:
            sub = panel[panel["state_abbr"] == s]
            if (sub["universalpermit"] == 0).all():
                keep.add(s)
        never = keep
    return cohorts, never, dropped


def run_one_policy(panel: pd.DataFrame, policy: dict, with_covid: bool = False,
                   with_efna: bool = False, with_despair: bool = False):
    name = policy["name"]
    flag_tokens = []
    if with_covid:   flag_tokens.append("covid")
    if with_efna:    flag_tokens.append("efna")
    if with_despair: flag_tokens.append("despair")
    suffix = ("_with_" + "_".join(flag_tokens)) if flag_tokens else ""
    out_dir = ROOT / "outputs" / f"{name}_stackdd{suffix}"
    fig_dir = out_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    flags = []
    if with_covid:   flags.append("with covid")
    if with_efna:    flags.append("with efna")
    if with_despair: flags.append("with despair")
    print(f"\n=== {name}{(' (' + ', '.join(flags) + ')') if flags else ''} ===")

    if policy["ado_table"]:
        cohorts, never_treated, dropped = cohorts_from_audit(
            panel, policy["ado_table"], policy["exclude_after"]
        )
    else:
        cohorts, never_treated, dropped = cohorts_from_panel(
            panel, policy["treatment_var"], policy["direction"],
            policy["exclude_after"]
        )
    print(f"  cohorts: {len(cohorts)}, treated states: {sum(len(v) for v in cohorts.values())}, "
          f"never-treated controls: {len(never_treated)}")

    def strict_pool_fn(p, candidates, g):
        return strict_control_pool(p, candidates, g,
                                   policy["strict_vars"], policy["strict_vals"])

    stacked = build_stacks(panel, cohorts, never_treated, K=5, H=5,
                           strict_pool_fn=strict_pool_fn)
    print(f"  stacked rows: {len(stacked):,}")
    if stacked.empty:
        print(f"  no stacks built; skipping {name}")
        return

    # EB-weight cache: key = (tier, family). Computed lazily once per
    # (tier, family) since EB weights depend only on the baseline-year
    # covariate distribution which is family-tier-specific.
    eb_cache: dict[tuple[str, str], object] = {}

    att_rows = []
    es_rows = []
    for outcome in OUTCOMES:
        family = classify_outcome(outcome)
        for tier in TIERS:
            cov = covariates_for(outcome, tier, with_covid=with_covid,
                                 with_efna=with_efna,
                                 with_despair=with_despair)
            cache_key = (tier, family, with_covid, with_efna, with_despair)
            if cache_key not in eb_cache:
                eb_cache[cache_key] = stack_eb_weights(stacked, cov, anchor_event_time=-1)
            eb = eb_cache[cache_key]
            for spec_name, weights, covariates in [
                ("unweighted", None, None),
                ("ra",         None, cov),
                ("eb",         eb,   None),
            ]:
                # OR / unweighted spec ignores covariates -- only run once,
                # not per tier; stamp tier="all" to deduplicate downstream.
                effective_tier = "all" if spec_name == "unweighted" else tier
                if spec_name == "unweighted" and tier != TIERS[0]:
                    continue  # only run unweighted once
                try:
                    att = twfe_within(stacked, outcome, weights, covariates)
                except Exception as e:
                    print(f"  [skip] {outcome}/{spec_name}/{tier}: {e}")
                    continue
                att_rows.append({
                    "outcome": outcome, "spec": spec_name, "tier": effective_tier,
                    "att": att["beta"], "se": att["se"], "z": att["z"],
                    "n": att["n"], "n_clusters": att["n_clusters"],
                })
                try:
                    es = twfe_event_study(stacked, outcome, weights, covariates,
                                          leads=5, lags=5, omit=-1)
                except Exception as e:
                    print(f"  [skip ES] {outcome}/{spec_name}/{tier}: {e}")
                    continue
                es["outcome"] = outcome
                es["spec"] = spec_name
                es["tier"] = effective_tier
                es_rows.append(es)
    att_df = pd.DataFrame(att_rows)
    es_df = pd.concat(es_rows, ignore_index=True) if es_rows else pd.DataFrame()
    att_df.to_csv(out_dir / "att_post.csv", index=False)
    es_df.to_csv(out_dir / "event_study.csv", index=False)
    pd.DataFrame(dropped).to_csv(out_dir / "dropped_log.csv", index=False)

    print(f"  Wrote outputs/{name}_stackdd/att_post.csv "
          f"({len(att_df)} (outcome, spec) rows)")

    # Print headline.
    print(f"\n  --- {name} stacked-DiD post ATT ---")
    for _, r in att_df.iterrows():
        sig = "**" if abs(r["z"]) >= 1.96 else "  "
        print(f"  {sig} [{r['spec']:<10}] {r['outcome']:<26}  ATT = {r['att']:>+8.3f}  "
              f"(SE {r['se']:.3f}, z {r['z']:>+5.2f})")

    # Plots: one figure per spec, headline tier only (the others are in
    # the CSV for downstream multiverse display in the report).
    for spec_name in ("unweighted", "ra", "eb"):
        if "tier" in es_df.columns:
            tier_filter = "all" if spec_name == "unweighted" else "headline"
            sub = es_df[(es_df["spec"] == spec_name) & (es_df["tier"] == tier_filter)]
        else:
            sub = es_df[es_df["spec"] == spec_name]
        if sub.empty:
            continue
        # cs_lib plot_event_study expects columns "att", "se", "outcome",
        # "spec", "control_rule". Bridge by aliasing.
        bridged = sub.rename(columns={"beta": "att"}).copy()
        bridged["control_rule"] = spec_name
        plot_event_study(bridged.assign(spec=spec_name),
                         fig_dir / f"event_study_{spec_name}_4panel.png",
                         spec_name, OUTCOMES,
                         title_suffix=f"-- stacked DiD ({name})")
        print(f"  Wrote {(fig_dir / f'event_study_{spec_name}_4panel.svg').relative_to(ROOT)}")


def main(with_covid: bool = False, with_efna: bool = False,
         with_despair: bool = False,
         only_policy: str | None = None):
    panel = load_panel_core_augmented()
    print(f"Panel: {len(panel):,} state-year rows in "
          f"{ANALYSIS_YEARS[0]}-{ANALYSIS_YEARS[1]}")
    for policy in POLICIES:
        if only_policy is not None and policy["name"] != only_policy:
            continue
        run_one_policy(panel, policy, with_covid=with_covid,
                       with_efna=with_efna, with_despair=with_despair)
    print("\nAll done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-covid", action="store_true",
                        help="Append OxCGRT covid_stringency_mean to RA "
                             "and EB covariates; write outputs to "
                             "outputs/{policy}_stackdd_with_covid/.")
    parser.add_argument("--with-efna", action="store_true",
                        help="Append Fraser Institute efna_overall to RA "
                             "and EB covariates. Combined with --with-covid, "
                             "outputs/{policy}_stackdd_with_covid_efna/; "
                             "alone, outputs/{policy}_stackdd_with_efna/.")
    parser.add_argument("--with-despair", action="store_true",
                        help="Append the deaths-of-despair stack "
                             "(synthetic_opioid_death_rate, "
                             "freq_mental_distress_pct, ami_pct) to RA and "
                             "EB covariates. Combinable with --with-covid "
                             "and --with-efna; maximal output is "
                             "outputs/{policy}_stackdd_with_covid_efna_"
                             "despair/.")
    parser.add_argument("--only-policy", default=None,
                        help="If set, only run this single policy by name.")
    args = parser.parse_args()
    main(with_covid=args.with_covid, with_efna=args.with_efna,
         with_despair=args.with_despair,
         only_policy=args.only_policy)
