"""Phase 1 -- large-capacity magazine ban (LCM) cohort construction.

Treatment variable: Tufts `magazine` (an indicator that the state bans the
sale of large-capacity ammunition magazines beyond just assault-pistol
magazines, covering rifle/shotgun magazines as well). Direction: 0->1.

The federal Public Safety and Recreational Firearms Use Protection Act
(Title XI of the 1994 Crime Control Act) banned magazines >10 rounds for
1994-2004; per the codebook, Tufts only credits a state ban during that
window if the state passed its OWN ban. Threshold: the federal ban used
>15 rounds; state-level bans almost universally use >10 rounds (Tufts
flags those with `tenroundlimit==1`).

Builds outputs/magazine_ban_audit/treatment_adoption_table.csv, mirroring
the layout of the assault_weapons_ban / permitless_carry audit tables.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs" / "magazine_ban_audit"
OUT.mkdir(parents=True, exist_ok=True)

ANALYSIS_LO, ANALYSIS_HI = 1999, 2023
MIN_PRE_K = 5  # CS21 requires this many pre-period years


def first_transition(values, direction="0to1"):
    """Return the year of the first 0->1 (or 1->0) transition in a list of
    (year, value) tuples, or None if none observed."""
    prev = None
    for y, v in values:
        if pd.isna(v):
            continue
        if prev is not None:
            if direction == "0to1" and prev == 0 and v == 1:
                return int(y)
            if direction == "1to0" and prev == 1 and v == 0:
                return int(y)
        prev = v
    return None


def all_reversals(values):
    """All 1->0 transition years (post-adoption reversals)."""
    out = []
    prev = None
    for y, v in values:
        if pd.isna(v):
            continue
        if prev == 1 and v == 0:
            out.append(int(y))
        prev = v
    return out


def main():
    panel = pd.read_csv(PROC / "panel_core_augmented.csv")
    panel = panel.sort_values(["state_abbr", "year"]).reset_index(drop=True)

    rows = []
    for st, grp in panel.groupby("state_abbr"):
        if st == "DC":
            continue
        state_name = grp["state"].iloc[0]
        full_years = list(zip(grp["year"].tolist(), grp["magazine"].tolist()))
        first = first_transition(full_years, direction="0to1")
        # whether they start the analysis window already with a ban
        start_val = None
        for y, v in full_years:
            if y == ANALYSIS_LO:
                start_val = v
                break
        starts_banned = int(start_val == 1) if start_val is not None else 0
        end_val = None
        for y, v in full_years:
            if y == ANALYSIS_HI:
                end_val = v
                break
        ends_banned = int(end_val == 1) if end_val is not None else 0
        reversals = all_reversals(full_years)
        adoption_year = None
        if first is not None and ANALYSIS_LO + 1 <= first <= ANALYSIS_HI:
            adoption_year = first
        included = bool(adoption_year is not None
                        and adoption_year - MIN_PRE_K >= ANALYSIS_LO)
        absorbing = (adoption_year is not None
                     and not any(r > adoption_year for r in reversals))
        post_reversal_yrs = ",".join(str(r) for r in reversals
                                     if (adoption_year is None or r > adoption_year))
        # capture the ten-round-limit flag at end of window for context
        end_tenround = None
        for _, r in grp.iterrows():
            if r["year"] == ANALYSIS_HI:
                end_tenround = int(r["tenroundlimit"]) if not pd.isna(r["tenroundlimit"]) else None
                break
        rows.append(OrderedDict([
            ("state", state_name),
            ("state_abbr", st),
            ("treatment_variable", "magazine"),
            ("adoption_rule", "first 0-to-1 switch in magazine (Tufts)"),
            ("adoption_year", adoption_year if adoption_year is not None else ""),
            ("included_in_mortality_sample", included),
            ("absorbing_after_adoption_through_2024", absorbing),
            ("post_adoption_reversal_years", post_reversal_yrs),
            ("starts_banned_1999", starts_banned),
            ("ends_banned_2023", ends_banned),
            ("ten_round_limit_2023", end_tenround if end_tenround is not None else ""),
            ("first_observed_adoption_year_any_panel", first if first else ""),
            ("notes_rand_crosscheck", ""),
        ]))

    # Annotate with RAND/Siegel cross-check notes (manual). Tufts captures
    # the ORIGINAL state-level magazine ban year; later strengthening events
    # (e.g., MD/NY 2013 reduction to 10 rounds; CA 2016 possession ban) are
    # NOT 0->1 transitions in `magazine` and do not generate cohorts.
    NOTES = {
        # Pre-1999 already-banned states (excluded from in-window cohorts):
        "NJ": "NJ Public Law 1990 ch. 32 (Assault Firearms Act). Tufts magazine==1 "
              "from 1990 onward; NJ used a 15-round limit (later 10 rounds in 2018). "
              "Already-banned at 1999, excluded from in-window cohorts. Matches RAND.",
        "MD": "MD originally banned magazines >20 rounds in 1994. Tufts magazine==1 "
              "from 1994 onward (matches the original ban year). MD reduced limit "
              "to 10 rounds in 2013 (Firearm Safety Act); RAND State Firearm Laws "
              "Database flags 2013 as the modern LCM ban event. Tufts coding does "
              "NOT generate a 2013 cohort (already 1) -- DOCUMENTED DISAGREEMENT. "
              "Already-banned at 1999, excluded from in-window cohorts.",
        "MA": "MA passed its LCM ban in 1998 (Gun Control Act of 1998), 10-round "
              "limit. Tufts magazine==1 from 1998 onward. Already-banned at 1999, "
              "excluded from in-window cohorts. Matches RAND.",
        # Pre-window adopters with adoption_year in [2000, ANALYSIS_LO+5):
        "CA": "CA Roberti-Roos AWB (1989) banned LCMs for assault weapons; the "
              "broad LCM sale ban (Penal Code 32310) took effect 2000 (10-round). "
              "CA tightened to a possession ban in 2016 (Prop 63). Tufts: 0->1 in "
              "2000; excluded from cohorts because 2000 - 5 = 1995 < ANALYSIS_LO. "
              "Matches RAND.",
        "NY": "NY first restricted LCMs in 2000 (Hevesi/Pataki LCM ban, 10-round); "
              "tightened to 7 rounds in NY SAFE Act 2013 (later struck down on the "
              "7-round limit; reverted to 10). Tufts: 0->1 in 2000; excluded from "
              "cohorts (2000 - 5 = 1995 < ANALYSIS_LO). The 2013 SAFE-Act expansion "
              "is NOT a 0->1 transition in magazine. Matches RAND on the 2000 event.",
        # In-window adopters that DO contribute to cohorts:
        "CO": "CO HB 13-1224, effective July 1 2013 (post-Aurora/Sandy Hook). "
              "15-round limit. Tufts: 0->1 in 2013. Matches RAND.",
        "CT": "CT Public Act 13-3, April 2013 (post-Newtown). 10-round limit, "
              "with grandfathering of pre-existing magazines requiring registration. "
              "Tufts: 0->1 in 2013. Matches RAND.",
        "VT": "VT Act 94, effective October 2018. 10-round limit for long guns, "
              "15-round limit for handguns. Tufts: 0->1 in 2018. Matches RAND.",
        "DE": "DE HB 450 / Lethal Firearms Safety Act of 2022. 17-round limit. "
              "Tufts: 0->1 in 2022. Matches RAND.",
        "RI": "RI House Bill 7457 / 2022 LCM ban, 10-round limit. Tufts: 0->1 in "
              "2022. Matches RAND.",
        "WA": "WA SB 5078, signed March 2022, effective July 2022. 10-round limit "
              "on sale/manufacture/import (possession remains legal). Tufts: 0->1 "
              "in 2022. Matches RAND.",
        "IL": "IL Protect Illinois Communities Act, January 2023 (post-Highland "
              "Park). 10-round rifle / 15-round handgun limit, paired with AWB. "
              "Tufts: 0->1 in 2023. Matches RAND.",
        # Documented Tufts/RAND disagreements:
        "OR": "OR Measure 114 (Nov 2022) banned magazines >10 rounds; effective "
              "date stayed by ongoing state and federal litigation through 2024 "
              "(Harney County preliminary injunction Dec 2022; OR Supreme Court "
              "appeal pending). Tufts magazine==0 throughout; RAND notes the "
              "passage but the ban is NOT in force. DOCUMENTED DISAGREEMENT but "
              "we agree with Tufts that no enforced ban exists in our analysis "
              "window.",
        "HI": "HI bans LCMs for HANDGUNS only (no long-gun coverage), so Tufts "
              "coding rule (must cover long guns) yields magazine==0 throughout. "
              "RAND lists HI's handgun-only LCM provision but excludes from a "
              "broad state-LCM list for the same reason. No discrepancy.",
    }
    for r in rows:
        st = r["state_abbr"]
        if st in NOTES:
            r["notes_rand_crosscheck"] = NOTES[st]

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "treatment_adoption_table.csv", index=False)

    # Console summary
    treated = df[df["adoption_year"] != ""].copy()
    included_n = int(df["included_in_mortality_sample"].sum())
    print(f"Wrote {OUT / 'treatment_adoption_table.csv'}")
    print(f"  observed 0->1 adoptions in 1999-2023: {len(treated)}")
    for _, r in treated.iterrows():
        flag = "INCLUDED" if r["included_in_mortality_sample"] else "EXCLUDED (pre-window)"
        print(f"    {r['state_abbr']} {r['adoption_year']}  {flag}")
    print(f"  cohorts contributing to CS21 sample (>= MIN_PRE_K pre years): {included_n}")
    cohort_yrs = sorted(set(int(r["adoption_year"]) for r in rows
                            if r["included_in_mortality_sample"]))
    print(f"  distinct cohort years: {len(cohort_yrs)} ({cohort_yrs})")


if __name__ == "__main__":
    main()
