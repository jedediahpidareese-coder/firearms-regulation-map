"""Augment each balanced panel with the variables that exist in raw data on disk
but were not yet integrated:

- Granular FBI/OpenCrime crime components: homicide, robbery, rape, agg assault,
  burglary, larceny, motor vehicle theft (counts and per-100k rates).
  The same NC->ND 2022 reassignment from the existing crime_repairs_log is applied.
- Firearm suicides, total suicides, firearm homicides, nonfirearm homicides
  (counts and per-100k rates), plus the FS/S ownership proxy.
- RAND TL-354 household firearm ownership rate (HFR) and standard error,
  1980-2016, 50 states.

The augmentation preserves the original (state_abbr, year) row layout - balance
of the underlying panel is unchanged. Augmented variables can have missing cells
within the panel window when their source series ends earlier (e.g. RAND ends in
2016; FS/S ends in 2023). A coverage report is written for each.

Outputs:
    data/processed/{panel}_augmented.csv
    data/processed/panel_augmented_balance.csv
    data/processed/panel_augmented_coverage.csv
"""

from __future__ import annotations

import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"

sys.path.insert(0, str(ROOT / "scripts"))
from build_website_data import (  # noqa: E402
    load_crime_detail, load_suicide_homicide, load_rand_ownership,
)

PANELS = OrderedDict([
    ("panel_core",        ("panel_core_1979_2024.csv",        1979, 2024)),
    ("panel_demographic", ("panel_demographic_1990_2024.csv", 1990, 2024)),
    ("panel_market",      ("panel_market_1999_2024.csv",      1999, 2024)),
    ("panel_modern",      ("panel_modern_2008_2024.csv",      2008, 2024)),
])

ADDED_VARS = [
    # crime granular (from OpenCrime detail)
    "homicide", "homicide_rate",
    "robbery", "robbery_rate",
    "rape", "rape_rate",
    "aggravated_assault", "aggravated_assault_rate",
    "burglary", "burglary_rate",
    "larceny", "larceny_rate",
    "motor_vehicle_theft", "motor_vehicle_theft_rate",
    # suicide / firearm-related deaths
    "firearm_suicides", "total_suicides",
    "firearm_suicide_rate", "total_suicide_rate",
    "firearm_homicides", "nonfirearm_homicides",
    "firearm_homicide_rate", "nonfirearm_homicide_rate",
    "homicide_rate_kalesan",
    # ownership
    "ownership_fss",
    "ownership_rand", "ownership_rand_se",
    # COVID-19 lockdown stringency (OxCGRT, Hale et al. 2021).
    # Pre-2020: zero. 2020-2022: observed. 2023+: carry forward.
    "covid_stringency_mean", "covid_stringency_max", "covid_days_lockdown",
    "covid_containment_mean", "covid_containment_max",
    "covid_econsupport_mean", "covid_econsupport_max",
    # Economic Freedom of North America (Stansel, Torra, McMahon 2023,
    # Fraser Institute). All-government index, 0-10 scale, higher = freer.
    # 1985-2021 observed; pre-1985 zero-fill, 2022-2024 carry-forward.
    "efna_overall", "efna_government_spending", "efna_taxes",
    "efna_regulation",
    # Deaths-of-despair covariate stack (added 2026-05-01 to absorb the
    # post-2019 mental-health crisis and the fentanyl-driven overdose
    # epidemic that overlap with the permitless-carry adoption window;
    # motivated by Case-Deaton 2015/2017 framework, Crifasi 2015 suicide-
    # spec covariate stack, Hollingsworth-Ruhm-Simon 2017 / Ruhm 2018
    # opioid-mortality-as-control precedent).
    "synthetic_opioid_death_rate",   # CDC VSRR T40.4 fentanyl-era
    "freq_mental_distress_pct",      # CDC BRFSS Healthy Days >=14 days
    "ami_pct", "smi_pct", "mde_pct", # SAMHSA NSDUH mental illness
]


def merge_safely(base: pd.DataFrame, addition: pd.DataFrame, label: str) -> pd.DataFrame:
    """Left-merge addition onto base by (state_abbr, year), with a duplicate guard."""
    grouped = addition.groupby(["state_abbr", "year"]).size()
    if (grouped > 1).any():
        dupes = grouped[grouped > 1].head(5)
        raise RuntimeError(f"Duplicate (state, year) rows in {label}:\n{dupes}")
    overlap = [c for c in addition.columns
               if c not in ("state_abbr", "year") and c in base.columns]
    if overlap:
        addition = addition.drop(columns=overlap)
    return base.merge(addition, on=["state_abbr", "year"], how="left")


def load_covid_stringency() -> pd.DataFrame:
    """Load the OxCGRT-derived COVID-19 stringency state-year covariates.

    Built by scripts/build_covid_stringency.py from data/OxCGRT_USA_latest.csv.
    Pre-2020 rows are zero-filled. The merge uses (state_abbr, year) keys
    consistent with the rest of augment_panels.
    """
    p = PROC / "covid_stringency_state_year.csv"
    if not p.exists():
        # Soft-fail: return an empty frame so a missing file does not break
        # the augment pipeline. The downstream analysis scripts will then
        # see no covid_* columns, equivalent to dropping the COVID
        # robustness covariate.
        return pd.DataFrame(columns=["state_abbr", "year"])
    cols = ["state_abbr", "year",
            "covid_stringency_mean", "covid_stringency_max", "covid_days_lockdown",
            "covid_containment_mean", "covid_containment_max",
            "covid_econsupport_mean", "covid_econsupport_max"]
    cv = pd.read_csv(p)
    # Drop DC since the augmented panels exclude DC.
    cv = cv[cv["state_abbr"] != "DC"]
    return cv[cols]


def load_fentanyl_deaths() -> pd.DataFrame:
    """Load the CDC VSRR-derived synthetic opioid (T40.4) state-year death
    rate per 100k. Built by scripts/build_fentanyl_deaths_state_year.py
    from data/vsrr_drug_overdose_state.csv.

    Pre-2015 rows are zero-filled in the build script (the synthetic-
    opioid epidemic was negligible before 2014 / 2015). 2015+ rows are
    observed where the state reports; states with low data quality may be
    NaN in early years. The merge uses (state_abbr, year) keys consistent
    with the rest of augment_panels.
    """
    p = PROC / "fentanyl_deaths_state_year.csv"
    if not p.exists():
        return pd.DataFrame(columns=["state_abbr", "year"])
    cols = ["state_abbr", "year", "synthetic_opioid_death_rate"]
    fd = pd.read_csv(p)
    fd = fd[fd["state_abbr"] != "DC"]
    return fd[cols]


def load_brfss_mental_distress() -> pd.DataFrame:
    """Load the BRFSS state-year frequent-mental-distress prevalence.
    Built by scripts/build_brfss_mental_distress_state_year.py from
    data/brfss_freq_mental_distress_raw.csv. Pre-2019 zero-filled
    (chronicdata BRFSS resource only exposes the Healthy Days topic
    2019-2024). 2019-2024 observed. Documented scope reduction.
    """
    p = PROC / "brfss_mental_distress_state_year.csv"
    if not p.exists():
        return pd.DataFrame(columns=["state_abbr", "year"])
    cols = ["state_abbr", "year", "freq_mental_distress_pct"]
    bf = pd.read_csv(p)
    bf = bf[bf["state_abbr"] != "DC"]
    return bf[cols]


def load_nsduh() -> pd.DataFrame:
    """Load the SAMHSA NSDUH state-year mental-illness prevalence.
    Built by scripts/build_nsduh_state_year.py from
    data/nsduh_zips/. 2016-2019 + 2022-2024 observed; 2020 and 2021
    NaN (2019-2020 release not produced due to COVID; 2020-2021 release
    SAMHSA cautions are not comparable due to the web-mode methodology
    break). Pre-2016 zero-filled.
    """
    p = PROC / "nsduh_mental_illness_state_year.csv"
    if not p.exists():
        return pd.DataFrame(columns=["state_abbr", "year"])
    cols = ["state_abbr", "year", "ami_pct", "smi_pct", "mde_pct"]
    ns = pd.read_csv(p)
    ns = ns[ns["state_abbr"] != "DC"]
    return ns[cols]


def load_efna() -> pd.DataFrame:
    """Load the Fraser Institute Economic Freedom of North America (EFNA)
    state-year covariates.

    Built by scripts/build_efna_state_year.py from
    data/EFNA_states_raw.xlsx. EFNA is observed annually for the 50 U.S.
    states 1985-2021 (with 1990 / 1995 spacing pre-2000); the build
    script linearly interpolates intra-window gaps and forward-fills
    2022-2024 from 2021. Pre-1985 is zero-filled defensively.

    DC is not in EFNA, but the augmented panels exclude DC anyway.
    Returns the (state_abbr, year, efna_*) columns expected by the
    augment merge.
    """
    p = PROC / "efna_state_year.csv"
    if not p.exists():
        return pd.DataFrame(columns=["state_abbr", "year"])
    cols = ["state_abbr", "year",
            "efna_overall", "efna_government_spending",
            "efna_taxes", "efna_regulation"]
    ef = pd.read_csv(p)
    return ef[cols]


def augment(panel_name: str, fname: str, ystart: int, yend: int):
    base = pd.read_csv(PROC / fname)
    n_in = len(base)

    crime = load_crime_detail()
    sh = load_suicide_homicide()
    rand = load_rand_ownership()
    covid = load_covid_stringency()
    efna = load_efna()
    fent = load_fentanyl_deaths()
    brfss = load_brfss_mental_distress()
    nsduh = load_nsduh()

    augmented = base.copy()
    augmented = merge_safely(augmented, crime, "OpenCrime granular")
    augmented = merge_safely(augmented, sh, "firearm_suicide_homicide_dataset_v2")
    augmented = merge_safely(augmented, rand, "RAND TL-354")
    if not covid.empty:
        augmented = merge_safely(augmented, covid, "OxCGRT COVID stringency")
        # Ensure pre-2020 rows are 0 (not NaN) for the COVID covariates.
        # The CSV already zero-fills 1999-2019, but if base has years
        # outside [1999, 2024] (e.g., panel_core 1979-1998) we explicitly
        # zero-fill those too -- per task spec.
        covid_cols = [c for c in covid.columns if c.startswith("covid_")]
        for c in covid_cols:
            augmented[c] = augmented[c].fillna(0.0)
    if not efna.empty:
        augmented = merge_safely(augmented, efna, "EFNA Fraser Institute")
        # For pre-1999 rows in panel_core (1979-1998), back-fill the
        # earliest observed EFNA year (1985) downward to avoid NaN cells
        # that would silently drop in regressions; this matches the same
        # approach used by RAND ownership pre-1980 cells. The build
        # script's earliest observed year for each state is 1985.
        efna_cols = [c for c in efna.columns if c.startswith("efna_")]
        for c in efna_cols:
            # Back-fill: for any state, use the earliest non-null year's
            # value to fill earlier years. This preserves the headline
            # robustness exercise (which is identified off the 1999+
            # window) while keeping the pre-1999 rows non-null.
            augmented[c] = (augmented.groupby("state_abbr")[c]
                            .transform(lambda s: s.bfill().ffill()))
    # Deaths-of-despair stack (2026-05-01 robustness layer).
    if not fent.empty:
        augmented = merge_safely(augmented, fent, "CDC VSRR fentanyl T40.4")
        # Pre-1999 panel_core (1979-1998) rows are outside the build's
        # YEAR_RANGE; defensively zero-fill them (the synthetic-opioid
        # epidemic is essentially a post-2014 phenomenon, so any year
        # outside 2015+ is well-approximated by zero). In-window NaN
        # rows (a state with low VSRR data quality) stay NaN so the
        # estimator's RA-fallback handles them correctly.
        mask_pre = augmented["year"] < 1999
        augmented.loc[mask_pre, "synthetic_opioid_death_rate"] = (
            augmented.loc[mask_pre, "synthetic_opioid_death_rate"].fillna(0.0)
        )
    if not brfss.empty:
        augmented = merge_safely(augmented, brfss, "CDC BRFSS Healthy Days")
        # Same pattern: pre-1999 panel_core rows defensively zero-fill;
        # in-window cells stay as observed (the build script zero-fills
        # 1999-2018 already, so this only matters for panel_core 1979+).
        mask_pre = augmented["year"] < 1999
        augmented.loc[mask_pre, "freq_mental_distress_pct"] = (
            augmented.loc[mask_pre, "freq_mental_distress_pct"].fillna(0.0)
        )
    if not nsduh.empty:
        augmented = merge_safely(augmented, nsduh, "SAMHSA NSDUH")
        # NSDUH year-2020 and year-2021 are NaN at source (the 2019-2020
        # release was not produced because COVID disrupted the survey
        # methodology, and SAMHSA cautions the 2020-2021 estimates are
        # not comparable across the web-mode break). For the deaths-of-
        # despair robustness exercise we want the variable to enter the
        # 2021/2022 cohort cells (whose base years are 2020/2021), so
        # we linearly interpolate the in-window 2020/2021 NaN cells
        # from the 2019 and 2022 NSDUH releases. This is a documented
        # imputation; the alternative (RA-fallback to OR for those cells)
        # would defeat the purpose of the robustness exercise. Pre-1999
        # panel_core rows are defensively zero-filled; the build script
        # zero-fills 1999-2015 already.
        for c in ("ami_pct", "smi_pct", "mde_pct"):
            mask_pre = augmented["year"] < 1999
            augmented.loc[mask_pre, c] = augmented.loc[mask_pre, c].fillna(0.0)
            # Linear-interpolate 2020 and 2021 within state.
            augmented[c] = (
                augmented.sort_values(["state_abbr", "year"])
                         .groupby("state_abbr")[c]
                         .transform(lambda s: s.interpolate(method="linear",
                                                            limit_direction="both"))
            )

    # Sanity: row count and (state,year) layout unchanged.
    if len(augmented) != n_in:
        raise RuntimeError(f"{panel_name}: augment changed row count {n_in} -> {len(augmented)}")
    grp = augmented.groupby(["state_abbr", "year"]).size()
    if (grp > 1).any():
        raise RuntimeError(f"{panel_name}: duplicate (state, year) after augment")

    out_path = PROC / f"{panel_name}_augmented.csv"
    augmented.to_csv(out_path, index=False)

    # Coverage rows.
    coverage = []
    for var in ADDED_VARS:
        if var not in augmented.columns:
            continue
        s = augmented[["state_abbr", "year", var]].dropna(subset=[var])
        coverage.append(OrderedDict([
            ("panel", panel_name),
            ("variable", var),
            ("non_null", int(len(s))),
            ("expected_in_window", n_in),
            ("coverage_pct", round(100 * len(s) / n_in, 1) if n_in else 0.0),
            ("first_year_observed", int(s["year"].min()) if len(s) else None),
            ("last_year_observed", int(s["year"].max()) if len(s) else None),
            ("states_observed", int(s["state_abbr"].nunique()) if len(s) else 0),
        ]))

    return augmented, coverage


def main():
    balance_rows = []
    coverage_rows = []
    for name, (fname, ystart, yend) in PANELS.items():
        df, coverage = augment(name, fname, ystart, yend)
        coverage_rows.extend(coverage)
        rows = len(df)
        states = df["state_abbr"].nunique()
        years = df["year"].nunique()
        expected = (yend - ystart + 1) * 50
        balance_rows.append(OrderedDict([
            ("panel", name + "_augmented"),
            ("year_range", f"{ystart}-{yend}"),
            ("rows", rows),
            ("rows_expected", expected),
            ("states", states),
            ("years", years),
            ("variables", df.shape[1]),
            ("balanced", rows == expected and states == 50),
        ]))
        print(f"{name + '_augmented':<35} rows={rows:,}/{expected:,} states={states} years={years} vars={df.shape[1]}")

    pd.DataFrame(balance_rows).to_csv(PROC / "panel_augmented_balance.csv", index=False)
    pd.DataFrame(coverage_rows).to_csv(PROC / "panel_augmented_coverage.csv", index=False)
    print()
    print("Wrote:")
    for name in PANELS:
        print(f"  data/processed/{name}_augmented.csv")
    print("  data/processed/panel_augmented_balance.csv")
    print("  data/processed/panel_augmented_coverage.csv")


if __name__ == "__main__":
    main()
