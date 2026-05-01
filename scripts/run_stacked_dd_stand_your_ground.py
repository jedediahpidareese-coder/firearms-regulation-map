"""Phase 5i (stand-your-ground only): Grier-style stacked DiD for SYG laws.

Forked from `scripts/run_stacked_dd.py` so the SYG analysis can run in
isolation in its own worktree without touching the multi-policy POLICIES
list. The merge into the main multi-policy script is coordinated by the
orchestrator (we also append a SYG entry to the shared POLICIES list, but
this fork is what is actually executed in this worktree).

For Stand-Your-Ground (Tufts variable `nosyg`, treated when state flips
1->0) and each of the six outcomes used elsewhere in the project, we
report three weighting specifications:

  - unweighted          plain stacked DiD, no covariate adjustment
  - regression-adjusted (RA)  TWFE with covariates as linear controls
  - entropy-balanced    (EB)  controls reweighted (Hainmueller 2012) so
                              their baseline covariate moments match
                              the treated unit's baseline moments

Outputs:
  outputs/stand_your_ground_stackdd/
    att_post.csv            one row per (outcome, weighting)
    event_study.csv         one row per (outcome, weighting, event_time)
    dropped_log.csv
    figures/event_study_{weighting}_4panel.svg
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from cs_lib import (
    OUTCOMES, ANALYSIS_YEARS,
    load_panel_core_augmented, derive_cohorts, strict_control_pool,
    plot_event_study,
)
from lib_stacked_dd import (
    build_stacks, stack_eb_weights, twfe_within, twfe_event_study,
)

ROOT = Path(__file__).resolve().parent.parent
CONTROLS = ["ln_population", "unemployment_rate", "ln_pcpi_real_2024"]

POLICY = {
    "name": "stand_your_ground",
    "treatment_var": "nosyg",
    "direction": "1to0",
    "strict_vars": ("nosyg",),
    "strict_vals": (1,),
    "exclude_after": 2023,
}


def run_one_policy(panel: pd.DataFrame, policy: dict):
    name = policy["name"]
    out_dir = ROOT / "outputs" / f"{name}_stackdd"
    fig_dir = out_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {name} ===")

    cohorts, never_treated, dropped = derive_cohorts(
        panel, treatment_var=policy["treatment_var"],
        direction=policy["direction"], min_pre_k=5,
        exclude_after=policy["exclude_after"],
    )
    print(f"  cohorts: {len(cohorts)}, treated states: "
          f"{sum(len(v) for v in cohorts.values())}, "
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

    eb = stack_eb_weights(stacked, CONTROLS, anchor_event_time=-1)
    print(f"  EB weights: mean={eb.mean():.3f}, min={eb.min():.3f}, "
          f"max={eb.max():.3f}")

    att_rows = []
    es_rows = []
    for outcome in OUTCOMES:
        for spec_name, weights, covariates in [
            ("unweighted", None, None),
            ("ra",         None, CONTROLS),
            ("eb",         eb,   None),
        ]:
            try:
                att = twfe_within(stacked, outcome, weights, covariates)
            except Exception as e:
                print(f"  [skip] {outcome}/{spec_name}: {e}")
                continue
            att_rows.append({
                "outcome": outcome, "spec": spec_name,
                "att": att["beta"], "se": att["se"], "z": att["z"],
                "n": att["n"], "n_clusters": att["n_clusters"],
            })
            try:
                es = twfe_event_study(stacked, outcome, weights, covariates,
                                      leads=5, lags=5, omit=-1)
            except Exception as e:
                print(f"  [skip ES] {outcome}/{spec_name}: {e}")
                continue
            es["outcome"] = outcome
            es["spec"] = spec_name
            es_rows.append(es)

    att_df = pd.DataFrame(att_rows)
    es_df = pd.concat(es_rows, ignore_index=True) if es_rows else pd.DataFrame()
    att_df.to_csv(out_dir / "att_post.csv", index=False)
    es_df.to_csv(out_dir / "event_study.csv", index=False)
    pd.DataFrame(dropped).to_csv(out_dir / "dropped_log.csv", index=False)

    print(f"  Wrote outputs/{name}_stackdd/att_post.csv "
          f"({len(att_df)} (outcome, spec) rows)")

    print(f"\n  --- {name} stacked-DiD post ATT ---")
    for _, r in att_df.iterrows():
        sig = "**" if abs(r["z"]) >= 1.96 else "  "
        print(f"  {sig} [{r['spec']:<10}] {r['outcome']:<26}  "
              f"ATT = {r['att']:>+8.3f}  "
              f"(SE {r['se']:.3f}, z {r['z']:>+5.2f})")

    for spec_name in ("unweighted", "ra", "eb"):
        sub = es_df[es_df["spec"] == spec_name]
        if sub.empty:
            continue
        bridged = sub.rename(columns={"beta": "att"}).copy()
        bridged["control_rule"] = spec_name
        plot_event_study(bridged.assign(spec=spec_name),
                         fig_dir / f"event_study_{spec_name}_4panel.png",
                         spec_name, OUTCOMES,
                         title_suffix=f"-- stacked DiD ({name})")
        print(f"  Wrote {(fig_dir / f'event_study_{spec_name}_4panel.svg').relative_to(ROOT)}")


def main():
    panel = load_panel_core_augmented()
    print(f"Panel: {len(panel):,} state-year rows in "
          f"{ANALYSIS_YEARS[0]}-{ANALYSIS_YEARS[1]}")
    run_one_policy(panel, POLICY)
    print("\nAll done.")


if __name__ == "__main__":
    main()
