"""Quick one-off: regenerate the CS21 event-study SVGs for all 8 policies
using the existing event_study.csv outputs. Use this whenever the plotter
changes (e.g. the 2026-05-01 tier-filter fix) without re-running the full
CS21 pipeline.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from cs_lib import plot_event_study, OUTCOMES

ROOT = Path(__file__).resolve().parent.parent
POLICIES = [
    "permitless_carry", "red_flag", "ubc",
    "stand_your_ground", "magazine_ban", "age21_handgun", "assault_weapons_ban",
]

def main() -> None:
    for policy in POLICIES:
        csv = ROOT / "outputs" / f"{policy}_cs" / "event_study.csv"
        if not csv.exists():
            print(f"  skip (no event_study.csv): {policy}")
            continue
        es_df = pd.read_csv(csv)
        figs = ROOT / "outputs" / f"{policy}_cs" / "figures"
        figs.mkdir(exist_ok=True)
        for control_rule in ("broad", "strict"):
            for spec in ("or", "ra"):
                sub = es_df[es_df["control_rule"] == control_rule]
                out = figs / f"event_study_{control_rule}_{spec}_4panel.svg"
                title = f"-- {policy.replace('_', ' ')}"
                plot_event_study(sub, out, spec, OUTCOMES, title_suffix=title)
                print(f"  wrote {out.name}")

if __name__ == "__main__":
    main()
