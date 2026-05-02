"""Build JSON data files used by the static map at /docs.

Reads the existing balanced panels in data/processed plus the firearm
suicide/homicide file and OpenCrime granular crime trends, and emits:

    docs/data/panel.json      compact per-state per-year values
    docs/data/metadata.json   variable definitions, sources, caveats
    docs/data/manifest.json   high-level summary the page uses for the legend

The script is idempotent. Re-run after the underlying CSVs change.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PROC = DATA / "processed"
OUT = ROOT / "docs" / "data"
OUT.mkdir(parents=True, exist_ok=True)

STATE_NAME_TO_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME",
    "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE",
    "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


def load_panel_modern() -> pd.DataFrame:
    """ACS + NICS + laws + crime totals, 2008-2024."""
    return pd.read_csv(PROC / "panel_modern_2008_2024.csv")


def load_panel_demographic() -> pd.DataFrame:
    """Long demographic + laws + crime totals, 1990-2024."""
    return pd.read_csv(PROC / "panel_demographic_1990_2024.csv")


def load_panel_core() -> pd.DataFrame:
    """Long laws + crime totals + economic controls, 1979-2024."""
    return pd.read_csv(PROC / "panel_core_1979_2024.csv")


def load_cj_controls() -> pd.DataFrame:
    """State-year CJ controls (Section 2.13 of data_appendix). Returns
    columns state_abbr, year, plus the four+one CJ posture variables."""
    p = PROC / "state_cj_controls_1979_2024.csv"
    if not p.exists():
        return pd.DataFrame(columns=["state_abbr", "year"])
    df = pd.read_csv(p, dtype={"state_fips": str})
    keep = ["state_abbr", "year",
            "imprisonment_rate",
            "police_expenditure_per_capita_real_2024",
            "has_death_penalty", "executions_count",
            "sworn_officers_per_100k"]
    return df[[c for c in keep if c in df.columns]]


def load_alcohol_per_capita() -> pd.DataFrame:
    """NIAAA per-capita ethanol consumption, 1977-2018 (state-year).
    Documented in data_appendix.md Section 2.13.x."""
    p = PROC / "state_alcohol_per_capita_1977_2023.csv"
    if not p.exists():
        return pd.DataFrame(columns=["state_abbr", "year"])
    return pd.read_csv(p)


def load_drug_overdose() -> pd.DataFrame:
    """CDC NCHS state-year drug-overdose mortality, 2003-2021."""
    p = PROC / "state_drug_overdose_2003_2021.csv"
    if not p.exists():
        return pd.DataFrame(columns=["state_abbr", "year"])
    return pd.read_csv(p)


def load_religion() -> pd.DataFrame:
    """ARDA US Religion Census 2020 state-level adherence rates.
    2020 cross-section broadcast to all years (slow-moving baseline)."""
    p = PROC / "state_religious_adherence_2020.csv"
    if not p.exists():
        return pd.DataFrame(columns=["state_abbr"])
    return pd.read_csv(p)[["state_abbr", "religion_adherents_pct_2020"]]


def load_fentanyl_deaths() -> pd.DataFrame:
    """CDC VSRR T40.4 synthetic-opioid death rate per 100k. Built by
    scripts/build_fentanyl_deaths_state_year.py. Pre-1999 zero-fill;
    post-coverage carry-forward."""
    p = PROC / "fentanyl_deaths_state_year.csv"
    if not p.exists():
        return pd.DataFrame(columns=["state_abbr", "year"])
    return pd.read_csv(p)[["state_abbr", "year", "synthetic_opioid_death_rate"]]


def load_brfss_mental_distress() -> pd.DataFrame:
    """CDC BRFSS frequent-mental-distress prevalence (% adults reporting
    >=14 poor mental-health days in past 30). Built by
    scripts/build_brfss_mental_distress_state_year.py."""
    p = PROC / "brfss_mental_distress_state_year.csv"
    if not p.exists():
        return pd.DataFrame(columns=["state_abbr", "year"])
    return pd.read_csv(p)[["state_abbr", "year", "freq_mental_distress_pct"]]


def load_nsduh() -> pd.DataFrame:
    """SAMHSA NSDUH state-year prevalence of any mental illness, serious
    mental illness, and major depressive episode (past year). Two-year
    rolling averages assigned to the upper year."""
    p = PROC / "nsduh_mental_illness_state_year.csv"
    if not p.exists():
        return pd.DataFrame(columns=["state_abbr", "year"])
    return pd.read_csv(p)[["state_abbr", "year", "ami_pct", "smi_pct", "mde_pct"]]


def load_lcm_thresholds() -> pd.DataFrame:
    """Hand-coded current-statute LCM round-count thresholds for the 12 states +
    DC + Delaware that have an active large-capacity magazine ban.

    Returned as a state-level (no year) lookup keyed by postal abbreviation; the
    panel builder broadcasts the threshold across all years where Tufts
    `magazine == 1`. This means early adopters whose threshold has shifted
    (NJ 15 -> 10 in 2018; NY 10 -> 7 -> 10 from 1994/2013/2014) are shown at
    their CURRENT statutory threshold across the full ban period. That's a
    descriptive simplification, documented in
    data/processed/lcm_thresholds_state.csv (column `notes`).
    """
    p = PROC / "lcm_thresholds_state.csv"
    if not p.exists():
        return pd.DataFrame(columns=["state_abbr",
                                      "magazine_threshold_handgun",
                                      "magazine_threshold_long_gun"])
    df = pd.read_csv(p)
    df = df.rename(columns={
        "postal": "state_abbr",
        "threshold_handgun": "magazine_threshold_handgun",
        "threshold_long_gun": "magazine_threshold_long_gun",
    })
    return df[["state_abbr",
               "magazine_threshold_handgun",
               "magazine_threshold_long_gun"]]


def load_panel_market() -> pd.DataFrame:
    """Adds NICS to core, 1999-2024."""
    return pd.read_csv(PROC / "panel_market_1999_2024.csv")


def load_rand_ownership() -> pd.DataFrame:
    """RAND TL-354 household firearm ownership rate (HFR), 1980-2016, 50 states.

    Schell et al. (2020) structural equation model combining BRFSS, GSS, Pew, hunting
    licenses, Guns & Ammo subscriptions, NICS, and Fem/Male FS/S into a single annual
    state estimate of the share of adults living in a household with any firearm.
    """
    path = DATA / "TL-354-State-Level Estimates of Household Firearm Ownership.xlsx"
    df = pd.read_excel(path, sheet_name="State-Level Data & Factor Score")
    df = df.rename(columns={"STATE": "state", "Year": "year",
                            "HFR": "ownership_rand", "HFR_se": "ownership_rand_se"})
    df["state"] = df["state"].astype(str).str.strip()
    df["state_abbr"] = df["state"].map(STATE_NAME_TO_ABBR)
    df = df[df["state_abbr"].notna()]
    return df[["state_abbr", "year", "ownership_rand", "ownership_rand_se"]]


def load_suicide_homicide() -> pd.DataFrame:
    """Kalesan-style firearm suicide/homicide + FS/S ownership proxy, 1949-2023."""
    df = pd.read_csv(DATA / "firearm_suicide_homicide_dataset_v2.tab", sep="\t")
    df["state"] = df["state"].str.strip().str.strip('"')
    df["state_abbr"] = df["state"].map(STATE_NAME_TO_ABBR)
    rename = {
        "fss": "ownership_fss",
        "homicide_rate": "homicide_rate_kalesan",
        "firearm_homicide_rate": "firearm_homicide_rate",
        "nonfirearm_homicide_rate": "nonfirearm_homicide_rate",
        "firearm_suicides": "firearm_suicides",
        "total_suicides": "total_suicides",
    }
    df = df.rename(columns=rename)
    df["firearm_suicide_rate"] = df["firearm_suicides"] / df["total_population"] * 1e5
    df["total_suicide_rate"] = df["total_suicides"] / df["total_population"] * 1e5
    return df[
        [
            "state_abbr", "year",
            "ownership_fss",
            "firearm_suicide_rate", "total_suicide_rate",
            "firearm_homicide_rate", "nonfirearm_homicide_rate",
            "homicide_rate_kalesan",
            "firearm_suicides", "total_suicides",
        ]
    ]


def load_crime_detail() -> pd.DataFrame:
    """Granular FBI/OpenCrime annual counts and rates, 1979-2024 where available.

    Applies the same NC->ND 2022 reassignment documented in
    data/processed/crime_repairs_log.csv: the raw file double-listed NC for 2022
    and omitted ND. The mislabeled second entry (state-sized ~780k population)
    is moved to ND.
    """
    with (DATA / "opencrime_state_trends.json").open() as f:
        raw = json.load(f)
    rows = []
    for entry in raw:
        abbr = entry.get("abbr")
        if not abbr:
            continue
        for yrec in entry.get("years", []):
            yrec = dict(yrec)
            yrec["state_abbr"] = abbr
            rows.append(yrec)
    df = pd.DataFrame(rows)
    df = df[df["state_abbr"].isin(STATE_NAME_TO_ABBR.values())]

    nc22 = df[(df["state_abbr"] == "NC") & (df["year"] == 2022)]
    if len(nc22) > 1:
        misplaced = nc22[nc22["population"] < 5_000_000]
        if not misplaced.empty:
            df.loc[misplaced.index, "state_abbr"] = "ND"
    pop = df["population"].replace(0, np.nan)
    df["homicide_rate"] = df["homicide"] / pop * 1e5
    df["robbery_rate"] = df["robbery"] / pop * 1e5
    df["rape_rate"] = df["rape"] / pop * 1e5
    df["aggravated_assault_rate"] = df["aggravatedAssault"] / pop * 1e5
    df["burglary_rate"] = df["burglary"] / pop * 1e5
    df["larceny_rate"] = df["larceny"] / pop * 1e5
    df["motor_vehicle_theft_rate"] = df["motorVehicleTheft"] / pop * 1e5
    keep = [
        "state_abbr", "year", "population",
        "violentRate", "propertyRate",
        "homicide", "homicide_rate",
        "robbery", "robbery_rate",
        "rape", "rape_rate",
        "aggravatedAssault", "aggravated_assault_rate",
        "burglary", "burglary_rate",
        "larceny", "larceny_rate",
        "motorVehicleTheft", "motor_vehicle_theft_rate",
    ]
    df = df[keep].rename(columns={
        "violentRate": "violent_rate",
        "propertyRate": "property_rate",
        "aggravatedAssault": "aggravated_assault",
        "motorVehicleTheft": "motor_vehicle_theft",
    })
    return df


# ---- Law category indices (sums of related Tufts indicators) ----

LAW_GROUPS = {
    "law_bg_check_index": [
        "universal", "universalh", "universalpermit", "universalpermith",
        "gunshow", "gunshowh", "statechecks", "statechecksh", "ammbackground",
    ],
    "law_carry_restriction_index": [
        "permitconcealed", "mayissue", "opencarryh", "opencarryl",
        "opencarrypermith", "opencarrypermitl",
    ],
    "law_banned_weapons_index": [
        "assault", "assaultlist", "assaultregister", "assaulttransfer",
        "magazine", "magazinepreowned", "tenroundlimit", "onefeature",
    ],
    "law_buyer_restriction_index": [
        "permit", "permith", "registration", "registrationh",
        "defactoreg", "defactoregh",
        "age21handgunsale", "age21longgunsale", "age18longgunsale",
        "loststolen", "onepermonth", "waiting", "waitingh",
    ],
    "law_dv_index": [
        "mcdv", "mcdvsurrender", "mcdvremovalallowed", "mcdvremovalrequired",
        "incidentremoval", "incidentall",
        "dvro", "exparte", "dvrosurrender", "expartesurrender", "dvroremoval",
        "stalking", "relinquishment",
    ],
    "law_storage_cap_index": ["locked", "liability", "gvro", "gvrolawenforcement"],
}


def add_law_indices(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for name, cols in LAW_GROUPS.items():
        present = [c for c in cols if c in df.columns]
        if not present:
            df[name] = np.nan
        else:
            df[name] = df[present].sum(axis=1, min_count=1)
    return df


# ---- Build merged panel ----

def build_panel() -> pd.DataFrame:
    core = add_law_indices(load_panel_core())
    market = load_panel_market()
    demo = load_panel_demographic()
    modern = load_panel_modern()
    crime = load_crime_detail()
    sh = load_suicide_homicide()

    # Start from core (1979-2024, 50 states) which has laws + headline crime + economy.
    base = core[[
        "state_abbr", "year", "lawtotal",
        "violent_rate", "property_rate",
        "unemployment_rate", "pcpi_real_2024", "population",
        "law_bg_check_index", "law_carry_restriction_index",
        "law_banned_weapons_index", "law_buyer_restriction_index",
        "law_dv_index", "law_storage_cap_index",
    ] + [c for c in [
        "universal", "magazine", "magazinepreowned", "assault",
        "assaultlist", "onefeature", "assaultregister", "assaulttransfer",
        "gvro", "locked",
        "permitconcealed", "mayissue", "waiting", "onepermonth", "mcdvsurrender",
    ] if c in core.columns]].copy()

    # Derived: effective fixed-magazine regime (the closest U.S.\ analogue
    # to a "detachable-magazine ban" for rifles). 1 iff the state has all
    # three of: an AWB (assault), a one-feature AWB definition (onefeature),
    # and a large-capacity-magazine sale ban (magazine). The combination
    # forces semi-automatic rifles into fixed-magazine, bolt-action, lever-
    # action, pump-action, or single-shot configurations.
    fm_components = ["assault", "onefeature", "magazine"]
    if all(c in base.columns for c in fm_components):
        base["fixed_magazine_regime"] = (
            (base["assault"] == 1)
            & (base["onefeature"] == 1)
            & (base["magazine"] == 1)
        ).astype(int)

    # Granular crime (1979-2024 where available) overrides aggregate columns when present.
    base = base.merge(
        crime.drop(columns=["population", "violent_rate", "property_rate"], errors="ignore"),
        on=["state_abbr", "year"], how="left",
    )

    # Suicide / ownership proxy (1949-2023; we keep 1979+).
    base = base.merge(sh, on=["state_abbr", "year"], how="left")

    # RAND household firearm ownership 1980-2016.
    rand = load_rand_ownership()
    base = base.merge(rand, on=["state_abbr", "year"], how="left")

    # NICS from market (1999-2024).
    nics_cols = [c for c in market.columns if c.startswith("nics_")]
    if nics_cols:
        base = base.merge(
            market[["state_abbr", "year"] + nics_cols],
            on=["state_abbr", "year"], how="left",
        )

    # ACS modern controls (2008-2024).
    acs_cols = [
        "median_hh_income_real_2024", "poverty_rate",
        "share_white_nh", "share_black_nh", "share_hispanic",
        "share_bachelors_plus", "share_male",
        "share_age_15_24", "share_age_25_44",
    ]
    base = base.merge(
        modern[["state_abbr", "year"] + [c for c in acs_cols if c in modern.columns]],
        on=["state_abbr", "year"], how="left",
    )

    # Pre-ACS demographic reconstruction (1990-2007) lives in panel_demographic; backfill it.
    pre_acs = demo[demo["year"] < 2008]
    pre_keep = [c for c in acs_cols if c in pre_acs.columns]
    base = base.merge(
        pre_acs[["state_abbr", "year"] + pre_keep],
        on=["state_abbr", "year"], how="left",
        suffixes=("", "_pre"),
    )
    for c in pre_keep:
        pre_col = f"{c}_pre"
        if pre_col in base.columns:
            base[c] = base[c].fillna(base[pre_col])
            base = base.drop(columns=pre_col)

    # CJ controls (Section 2.13): imprisonment, police expenditure, death
    # penalty, executions, sworn officers (state rollup of LEOKA).
    cj = load_cj_controls()
    if not cj.empty:
        base = base.merge(cj, on=["state_abbr", "year"], how="left")

    # Health & substances controls added 2026-05-01 for the literature-
    # backed covariate restructure (Section 2.13.x of the appendix):
    # NIAAA alcohol per capita (1977-2018), CDC drug overdose mortality
    # (2003-2021), ARDA religious adherence (2020 cross-section
    # broadcast across years as a slow-moving baseline).
    alc = load_alcohol_per_capita()
    if not alc.empty:
        base = base.merge(alc, on=["state_abbr", "year"], how="left")
    od = load_drug_overdose()
    if not od.empty:
        base = base.merge(od, on=["state_abbr", "year"], how="left")
    rel = load_religion()
    if not rel.empty:
        base = base.merge(rel, on="state_abbr", how="left")

    # Deaths-of-despair stack (added 2026-05-02): synthetic-opioid death
    # rate (CDC VSRR T40.4 fentanyl-era), BRFSS frequent mental distress,
    # NSDUH any-mental-illness / serious-mental-illness / major-depressive-
    # episode prevalence. Motivated by Case-Deaton (2015, 2017), Czeisler
    # et al. (2020), Pirkis et al. (2021).
    fent = load_fentanyl_deaths()
    if not fent.empty:
        base = base.merge(fent, on=["state_abbr", "year"], how="left")
    brfss = load_brfss_mental_distress()
    if not brfss.empty:
        base = base.merge(brfss, on=["state_abbr", "year"], how="left")
    nsduh = load_nsduh()
    if not nsduh.empty:
        base = base.merge(nsduh, on=["state_abbr", "year"], how="left")

    # LCM round-count thresholds (hand-coded current statute for ~14 states/DC).
    # Broadcast the threshold to every year a state has magazine == 1 in Tufts
    # so users can see "10 rounds in CA, 15 in CO, 17 in DE", etc. State-years
    # without an active LCM ban (magazine == 0 or NaN) get NaN thresholds.
    lcm = load_lcm_thresholds()
    if not lcm.empty:
        base = base.merge(lcm, on="state_abbr", how="left")
        if "magazine" in base.columns:
            mask = base["magazine"].fillna(0) != 1
            base.loc[mask, "magazine_threshold_handgun"] = np.nan
            base.loc[mask, "magazine_threshold_long_gun"] = np.nan

    return base.sort_values(["state_abbr", "year"]).reset_index(drop=True)


# ---- JSON emission ----

def df_to_panel_json(df: pd.DataFrame) -> dict:
    """Shape: { state_abbr: { year: { var: value, ... } } }."""
    panel: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    skip = {"state_abbr", "year"}
    for record in df.to_dict(orient="records"):
        abbr = record["state_abbr"]
        year = int(record["year"])
        cell: dict[str, float] = {}
        for k, v in record.items():
            if k in skip:
                continue
            if v is None:
                continue
            if isinstance(v, float) and np.isnan(v):
                continue
            cell[k] = round(float(v), 4) if isinstance(v, (int, float, np.floating)) else v
        panel[abbr][str(year)] = cell
    return dict(panel)


# ---- Variable metadata (definitions + sources + caveats shown on the page) ----

VARIABLE_METADATA = {
    # Laws
    "lawtotal": {
        "label": "Firearm law count (Tufts)",
        "category": "Regulation",
        "unit": "Laws (count)",
        "format": "integer",
        "definition": "Sum of 72 binary firearm law indicators coded by Siegel et al. for the Tufts State Firearm Laws database. Higher values mean more restrictive policy.",
        "source": "Tufts State Firearm Laws (1976-2024)",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "sequential",
        "higher_is": "more regulation",
    },
    "law_bg_check_index": {
        "label": "Background check index",
        "category": "Regulation",
        "unit": "Provisions (count)",
        "format": "integer",
        "definition": "Number of Tufts background-check-related provisions in force, including universal/handgun-only checks, gun-show checks, state-level checks, and ammunition checks.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    "law_carry_restriction_index": {
        "label": "Carry restriction index",
        "category": "Regulation",
        "unit": "Provisions (count)",
        "format": "integer",
        "definition": "Sum of restrictions on concealed and open carry, including may-issue concealed carry, permit requirements for concealed carry, and open carry restrictions for handguns and long guns.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    "law_banned_weapons_index": {
        "label": "Banned-weapons index",
        "category": "Regulation",
        "unit": "Provisions (count)",
        "format": "integer",
        "definition": "Sum of bans on assault weapons (general, list-based, one-feature), restrictions on grandfathered ownership, large-capacity magazine bans, and 10-round limits.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    "law_buyer_restriction_index": {
        "label": "Buyer restriction index",
        "category": "Regulation",
        "unit": "Provisions (count)",
        "format": "integer",
        "definition": "Sum of permit-to-purchase, registration, age-21 sale restrictions, lost/stolen reporting, one-gun-per-month limits, and waiting periods.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    "law_dv_index": {
        "label": "Domestic-violence prohibitor index",
        "category": "Regulation",
        "unit": "Provisions (count)",
        "format": "integer",
        "definition": "Sum of domestic-violence prohibitor laws covering misdemeanor crimes of domestic violence (MCDV), surrender requirements, ex parte orders, DVRO/stalking provisions, and incident-based removal.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    "law_storage_cap_index": {
        "label": "Storage / GVRO / liability index",
        "category": "Regulation",
        "unit": "Provisions (count)",
        "format": "integer",
        "definition": "Sum of locked-storage / child-access prevention, dealer liability, and gun violence restraining order (GVRO / red-flag) provisions.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    "magazine": {
        "label": "LCM sale ban (binary)",
        "category": "Regulation",
        "unit": "Yes / No",
        "format": "binary",
        "definition": "1 if the state bans the sale of large-capacity magazines (LCMs) beyond just assault-pistol ammunition. The threshold for what counts as \"large capacity\" varies by state; see the magazine_threshold_handgun and magazine_threshold_long_gun variables for the round count.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "binary",
    },
    "magazinepreowned": {
        "label": "LCM possession ban (binary)",
        "category": "Regulation",
        "unit": "Yes / No",
        "format": "binary",
        "definition": "1 if the state additionally prohibits possession of pre-owned large-capacity magazines (i.e. magazines acquired before the state's LCM sale ban took effect). 0 means owners may keep grandfathered LCMs even if new sales are banned. This is a stricter form of LCM regulation: California adopted an LCM possession ban in 2017 (Prop 63), New Jersey lowered its threshold and eliminated grandfathering in 2018, and DC's LCM ban has always covered possession.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "binary",
    },
    "magazine_threshold_handgun": {
        "label": "LCM round-count threshold (handguns)",
        "category": "Regulation",
        "unit": "rounds",
        "format": "integer",
        "definition": "Round-count threshold above which a handgun magazine is classified as a \"large-capacity magazine\" under the state's LCM sale ban. Most banning states use 10 rounds (CA, CT, MA, MD, NY, NJ, OR, WA, HI, DC); Colorado uses 15 (HB13-1224, 2013); Vermont uses 15 for handguns (2018); Illinois uses 15 for handguns (PICA, 2023); Delaware uses 17 (HB 450, 2022). NaN for state-years without an active LCM sale ban. Hand-coded from public state-by-state summaries (Giffords Law Center, RAND Smart Policy) — see data/processed/lcm_thresholds_state.csv. Note: the threshold shown is the CURRENT statute and is broadcast across all ban years; states whose threshold shifted mid-period (e.g. NJ 15->10 in 2018) display the current value.",
        "source": "Hand-coded from Giffords / RAND state-by-state LCM summaries",
        "source_url": "https://giffords.org/lawcenter/gun-laws/policy-areas/hardware-ammunition/large-capacity-magazines/",
        "year_range": [1979, 2024],
        "scale": "sequential",
        "caveat": "Current-statute snapshot broadcast to all ban years; threshold changes within a state are not time-resolved.",
    },
    "magazine_threshold_long_gun": {
        "label": "LCM round-count threshold (long guns)",
        "category": "Regulation",
        "unit": "rounds",
        "format": "integer",
        "definition": "Round-count threshold above which a long-gun magazine is classified as a \"large-capacity magazine\" under the state's LCM sale ban. Most banning states match their handgun threshold; Vermont (10 long-gun vs. 15 handgun) and Illinois (10 long-gun vs. 15 handgun under PICA) use a stricter limit for rifles. Hawaii's LCM ban applies to handgun magazines only — long-gun magazines are unrestricted, so this column is NaN for HI. NaN for state-years without an active LCM sale ban. Same source and current-statute caveat as magazine_threshold_handgun.",
        "source": "Hand-coded from Giffords / RAND state-by-state LCM summaries",
        "source_url": "https://giffords.org/lawcenter/gun-laws/policy-areas/hardware-ammunition/large-capacity-magazines/",
        "year_range": [1979, 2024],
        "scale": "sequential",
        "caveat": "Current-statute snapshot broadcast to all ban years; threshold changes within a state are not time-resolved. Hawaii's LCM ban does not cover long-gun magazines (NaN).",
    },
    "assault": {
        "label": "Assault weapons ban (binary)",
        "category": "Regulation",
        "unit": "Yes / No",
        "format": "binary",
        "definition": "1 if state bans the sale of assault weapons beyond assault pistols.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "binary",
    },
    "assaultlist": {
        "label": "AWB by named-list definition (binary)",
        "category": "Regulation",
        "unit": "Yes / No",
        "format": "binary",
        "definition": "1 if the state's assault-weapons ban includes an explicit list of named/banned models (e.g., AR-15, AK-47 variants). Most states with an AWB use a list approach.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "binary",
    },
    "onefeature": {
        "label": "AWB by one-feature definition (binary)",
        "category": "Regulation",
        "unit": "Yes / No",
        "format": "binary",
        "definition": "1 if the state's assault-weapons ban uses a one-feature test: any semi-automatic rifle with a detachable magazine PLUS one military-style feature (pistol grip, telescoping stock, flash hider, etc.) qualifies as an assault weapon. Combined with a low-round LCM ban, this regime effectively forces semi-automatic rifles into fixed-magazine, bolt-action, or single-shot configurations. CA, CT, IL, NY, WA, MA, NJ, DE use this test.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "binary",
    },
    "assaultregister": {
        "label": "Grandfathered AWs must be registered (binary)",
        "category": "Regulation",
        "unit": "Yes / No",
        "format": "binary",
        "definition": "1 if owners of pre-existing (grandfathered) assault weapons must register them with the state. A more restrictive AWB feature.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "binary",
    },
    "assaulttransfer": {
        "label": "Transfer of grandfathered AWs prohibited (binary)",
        "category": "Regulation",
        "unit": "Yes / No",
        "format": "binary",
        "definition": "1 if grandfathered assault weapons cannot be sold or transferred (only kept by the original registered owner). Among the most restrictive AWB features.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "binary",
    },
    "fixed_magazine_regime": {
        "label": "Effective fixed-magazine regime (binary, derived)",
        "category": "Regulation",
        "unit": "Yes / No",
        "format": "binary",
        "definition": "1 if the state has all three: an assault-weapons ban (assault), a one-feature definition (onefeature), and a large-capacity-magazine sale ban (magazine). The combination effectively forces semi-automatic rifles to be configured with fixed magazines, switched to bolt-action / lever-action / pump / single-shot, or sold elsewhere. This is the closest analogue in U.S.\\ law to a 'detachable-magazine ban' for rifles. Derived from Tufts variables; not an independent statute.",
        "source": "Derived from Tufts State Firearm Laws (assault, onefeature, magazine)",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "binary",
    },
    "gvro": {
        "label": "Red-flag / GVRO law (binary)",
        "category": "Regulation",
        "unit": "Yes / No",
        "format": "binary",
        "definition": "1 if state has a gun violence restraining order / extreme risk protection order law allowing temporary firearm removal.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "binary",
    },
    "universal": {
        "label": "Universal background checks (binary)",
        "category": "Regulation",
        "unit": "Yes / No",
        "format": "binary",
        "definition": "1 if the state requires a background check on every firearm transfer, INCLUDING private sales between individuals (gun shows, online, person-to-person). 0 means only federally-licensed dealers (FFLs) must run NICS checks; private sales between residents are exempt under federal law unless a state statute closes that gap.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "binary",
    },
    "permitconcealed": {
        "label": "Permit required to carry concealed (binary)",
        "category": "Regulation",
        "unit": "Yes / No",
        "format": "binary",
        "definition": "1 if the state requires a state-issued permit to carry a concealed firearm in public. 0 means \"permitless carry\" (sometimes called \"constitutional carry\") — any adult who can legally possess a firearm may carry it concealed without first obtaining a permit. The opposite of this variable, when it switches from 1 to 0, is the operational definition of \"adopted permitless carry\" used in the project's causal analyses.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "binary",
    },
    "mayissue": {
        "label": "May-issue concealed carry (binary)",
        "category": "Regulation",
        "unit": "Yes / No",
        "format": "binary",
        "definition": "1 if the state's concealed-carry permitting authority has DISCRETION over whether to issue a permit (\"may-issue\" / \"good cause required\"), or if the state outright bans concealed carry. 0 means \"shall-issue\" — the authority MUST issue a permit to any applicant who meets objective statutory criteria. The 2022 NYSRPA v. Bruen Supreme Court decision made many remaining may-issue regimes unconstitutional, so this variable is mostly historical post-2022.",
        "source": "Tufts State Firearm Laws",
        "source_url": "https://www.tuftsctsi.org/state-firearm-laws/",
        "year_range": [1979, 2024],
        "scale": "binary",
    },

    # Crime - rates per 100k
    "violent_rate": {
        "label": "Violent crime rate",
        "category": "Crime",
        "unit": "Per 100,000 people",
        "format": "rate",
        "definition": "FBI UCR violent crime offenses per 100,000 population. Includes murder/nonnegligent manslaughter, rape, robbery, and aggravated assault.",
        "source": "FBI Uniform Crime Reports / OpenCrime extraction",
        "source_url": "https://cde.ucr.cjis.gov/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    "property_rate": {
        "label": "Property crime rate",
        "category": "Crime",
        "unit": "Per 100,000 people",
        "format": "rate",
        "definition": "FBI UCR property crime offenses per 100,000 population. Includes burglary, larceny-theft, and motor vehicle theft.",
        "source": "FBI Uniform Crime Reports / OpenCrime extraction",
        "source_url": "https://cde.ucr.cjis.gov/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    "homicide_rate": {
        "label": "Homicide rate",
        "category": "Crime",
        "unit": "Per 100,000 people",
        "format": "rate",
        "definition": "Murder and nonnegligent manslaughter per 100,000 population (FBI UCR / OpenCrime).",
        "source": "FBI Uniform Crime Reports / OpenCrime extraction",
        "source_url": "https://cde.ucr.cjis.gov/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    "robbery_rate": {
        "label": "Robbery rate",
        "category": "Crime",
        "unit": "Per 100,000 people",
        "format": "rate",
        "definition": "Reported robbery offenses per 100,000 population (FBI UCR / OpenCrime).",
        "source": "FBI Uniform Crime Reports / OpenCrime extraction",
        "source_url": "https://cde.ucr.cjis.gov/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    "rape_rate": {
        "label": "Rape rate",
        "category": "Crime",
        "unit": "Per 100,000 people",
        "format": "rate",
        "definition": "Reported rape offenses per 100,000 population (FBI UCR / OpenCrime). Definition broadened in 2013; pre/post-2013 levels are not directly comparable.",
        "source": "FBI Uniform Crime Reports / OpenCrime extraction",
        "source_url": "https://cde.ucr.cjis.gov/",
        "year_range": [1979, 2024],
        "scale": "sequential",
        "caveat": "FBI revised the rape definition in 2013; the pre-2013 series uses the legacy definition.",
    },
    "aggravated_assault_rate": {
        "label": "Aggravated assault rate",
        "category": "Crime",
        "unit": "Per 100,000 people",
        "format": "rate",
        "definition": "Reported aggravated assault per 100,000 population (FBI UCR / OpenCrime).",
        "source": "FBI Uniform Crime Reports / OpenCrime extraction",
        "source_url": "https://cde.ucr.cjis.gov/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    "burglary_rate": {
        "label": "Burglary rate",
        "category": "Crime",
        "unit": "Per 100,000 people",
        "format": "rate",
        "definition": "Reported burglary offenses per 100,000 population (FBI UCR / OpenCrime).",
        "source": "FBI Uniform Crime Reports / OpenCrime extraction",
        "source_url": "https://cde.ucr.cjis.gov/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    "larceny_rate": {
        "label": "Larceny rate",
        "category": "Crime",
        "unit": "Per 100,000 people",
        "format": "rate",
        "definition": "Reported larceny-theft per 100,000 population (FBI UCR / OpenCrime).",
        "source": "FBI Uniform Crime Reports / OpenCrime extraction",
        "source_url": "https://cde.ucr.cjis.gov/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    "motor_vehicle_theft_rate": {
        "label": "Motor vehicle theft rate",
        "category": "Crime",
        "unit": "Per 100,000 people",
        "format": "rate",
        "definition": "Reported motor vehicle theft per 100,000 population (FBI UCR / OpenCrime).",
        "source": "FBI Uniform Crime Reports / OpenCrime extraction",
        "source_url": "https://cde.ucr.cjis.gov/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },

    # Suicide / firearm-related deaths
    "firearm_suicide_rate": {
        "label": "Firearm suicide rate",
        "category": "Suicide & firearm deaths",
        "unit": "Per 100,000 people",
        "format": "rate",
        "definition": "Firearm suicides per 100,000 population, derived from the firearm-suicide-share dataset (Kalesan-style v2 file) for 1949-2023.",
        "source": "Firearm suicide / homicide v2 dataset (Kalesan supplement style)",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/37743886/",
        "year_range": [1979, 2023],
        "scale": "sequential",
    },
    "total_suicide_rate": {
        "label": "Total suicide rate",
        "category": "Suicide & firearm deaths",
        "unit": "Per 100,000 people",
        "format": "rate",
        "definition": "All-method suicides per 100,000 population, derived from the firearm-suicide-share dataset for 1949-2023.",
        "source": "Firearm suicide / homicide v2 dataset",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/37743886/",
        "year_range": [1979, 2023],
        "scale": "sequential",
    },
    "firearm_homicide_rate": {
        "label": "Firearm homicide rate",
        "category": "Suicide & firearm deaths",
        "unit": "Per 100,000 people",
        "format": "rate",
        "definition": "Firearm homicides per 100,000 population from the firearm-suicide-share v2 file.",
        "source": "Firearm suicide / homicide v2 dataset",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/37743886/",
        "year_range": [1979, 2023],
        "scale": "sequential",
    },

    # Ownership proxies
    "ownership_rand": {
        "label": "Gun ownership rate (RAND HFR)",
        "category": "Gun ownership",
        "unit": "Share of households",
        "format": "percent",
        "definition": "RAND State-Level Household Firearm Ownership Rate (HFR), 1980-2016. Schell et al. structural equation model combining BRFSS, GSS, Pew, hunting licenses, Guns & Ammo subscriptions, NICS, and the Fem/Male firearm-suicide-share into a single estimate of the share of adults living in a household with any firearm. Most-cited modern state ownership measure; ends in 2016.",
        "source": "RAND TL-354 (Schell et al., 2020)",
        "source_url": "https://www.rand.org/pubs/tools/TL354.html",
        "year_range": [1980, 2016],
        "scale": "sequential",
        "caveat": "Series ends in 2016. Standard errors are non-trivial in early years.",
    },
    "ownership_fss": {
        "label": "Gun ownership proxy (FS/S)",
        "category": "Gun ownership",
        "unit": "Firearm-suicide ratio",
        "format": "percent",
        "definition": "Firearm-suicide-share proxy for state household gun ownership: firearm suicides / all suicides. Most-used long-run proxy in the literature, but mechanically correlated with suicide outcomes; do NOT use as a regressor when the outcome is suicide.",
        "source": "Firearm suicide / homicide v2 dataset",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/37743886/",
        "year_range": [1979, 2023],
        "scale": "sequential",
        "caveat": "Mechanically correlated with suicide outcomes. Treat as descriptive ownership proxy only.",
    },
    "nics_total_per_100k": {
        "label": "NICS background checks per 100k (market activity)",
        "category": "Gun ownership",
        "unit": "Checks per 100,000 people",
        "format": "rate",
        "definition": "Annual FBI NICS background checks per 100,000 population. A flow proxy for legal market activity, NOT a stock measure of gun owners. Background checks do not equal gun sales (multiple firearms per check; some states use NICS for permit re-checks). Do not interpret as ownership rate.",
        "source": "FBI NICS via Data Liberation Project",
        "source_url": "https://www.data-liberation-project.org/datasets/nics-firearm-background-checks/",
        "year_range": [1999, 2024],
        "scale": "sequential",
        "caveat": "Checks are not sales; some states submit large permit re-check volumes that distort year-over-year comparison.",
    },

    # Demographics
    "share_white_nh": {
        "label": "Share non-Hispanic white",
        "category": "Demographics",
        "unit": "Share of population",
        "format": "percent",
        "definition": "Population share identifying as non-Hispanic white. Reconstructed from Census ASRH (1990-1999), intercensal (2000-2009), and Census/PEP (2010-2024) files; ACS 1-year 2008-2024 in the modern panel.",
        "source": "Census Bureau historical population estimates and ACS",
        "source_url": "https://www.census.gov/programs-surveys/popest.html",
        "year_range": [1990, 2024],
        "scale": "sequential",
    },
    "share_black_nh": {
        "label": "Share non-Hispanic Black",
        "category": "Demographics",
        "unit": "Share of population",
        "format": "percent",
        "definition": "Population share identifying as non-Hispanic Black. Same reconstruction approach as share_white_nh.",
        "source": "Census Bureau historical population estimates and ACS",
        "source_url": "https://www.census.gov/programs-surveys/popest.html",
        "year_range": [1990, 2024],
        "scale": "sequential",
    },
    "share_hispanic": {
        "label": "Share Hispanic",
        "category": "Demographics",
        "unit": "Share of population",
        "format": "percent",
        "definition": "Population share identifying as Hispanic or Latino, any race.",
        "source": "Census Bureau historical population estimates and ACS",
        "source_url": "https://www.census.gov/programs-surveys/popest.html",
        "year_range": [1990, 2024],
        "scale": "sequential",
    },
    "share_male": {
        "label": "Share male",
        "category": "Demographics",
        "unit": "Share of population",
        "format": "percent",
        "definition": "Population share male. Reconstructed from Census ASRH/intercensal/PEP files.",
        "source": "Census Bureau historical population estimates and ACS",
        "source_url": "https://www.census.gov/programs-surveys/popest.html",
        "year_range": [1990, 2024],
        "scale": "sequential",
    },
    "share_age_15_24": {
        "label": "Share age 15-24",
        "category": "Demographics",
        "unit": "Share of population",
        "format": "percent",
        "definition": "Population share aged 15-24, the high-violence-risk demographic window typically used in the gun-policy literature.",
        "source": "Census Bureau historical population estimates and ACS",
        "source_url": "https://www.census.gov/programs-surveys/popest.html",
        "year_range": [1990, 2024],
        "scale": "sequential",
    },
    "share_age_25_44": {
        "label": "Share age 25-44",
        "category": "Demographics",
        "unit": "Share of population",
        "format": "percent",
        "definition": "Population share aged 25-44.",
        "source": "Census Bureau historical population estimates and ACS",
        "source_url": "https://www.census.gov/programs-surveys/popest.html",
        "year_range": [1990, 2024],
        "scale": "sequential",
    },
    "share_bachelors_plus": {
        "label": "Share with bachelor's degree or higher (25+)",
        "category": "Demographics",
        "unit": "Share of adults 25+",
        "format": "percent",
        "definition": "Share of adults 25+ with a bachelor's degree or higher. Anchored on Census Statistical Abstract Table 229 (1990, 2000, 2008) and ACS 1-year 2008-2024; pre-ACS years are linearly interpolated within state.",
        "source": "Census Statistical Abstract + ACS",
        "source_url": "https://www.census.gov/library/publications/2010/compendia/statab/130ed.html",
        "year_range": [1990, 2024],
        "scale": "sequential",
        "caveat": "Pre-2008 values are interpolated within state from anchor years.",
    },

    # Economy
    "median_hh_income_real_2024": {
        "label": "Median household income (real 2024 USD)",
        "category": "Economy",
        "unit": "U.S. dollars (2024)",
        "format": "currency",
        "definition": "Median household income from Census SAIPE, deflated to 2024 dollars with CPI-U. SAIPE 1990-1992 and 1994 missing values are interpolated within state.",
        "source": "Census SAIPE deflated to real 2024 USD",
        "source_url": "https://www.census.gov/programs-surveys/saipe/",
        "year_range": [1990, 2024],
        "scale": "sequential",
        "caveat": "1990-1992 and 1994 values were interpolated within state.",
    },
    "poverty_rate": {
        "label": "Poverty rate",
        "category": "Economy",
        "unit": "Share in poverty",
        "format": "percent",
        "definition": "Census SAIPE all-ages poverty rate. Same interpolation caveat as income.",
        "source": "Census SAIPE",
        "source_url": "https://www.census.gov/programs-surveys/saipe/",
        "year_range": [1990, 2024],
        "scale": "sequential",
    },
    "unemployment_rate": {
        "label": "Unemployment rate",
        "category": "Economy",
        "unit": "Percent",
        "format": "percent_pre",
        "definition": "BLS state unemployment rate (annual average of monthly LAUS).",
        "source": "BLS LAUS via FRED",
        "source_url": "https://fred.stlouisfed.org/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    "pcpi_real_2024": {
        "label": "Per-capita personal income (real 2024 USD)",
        "category": "Economy",
        "unit": "U.S. dollars (2024)",
        "format": "currency",
        "definition": "BEA per-capita personal income, deflated to 2024 dollars with CPI-U.",
        "source": "BEA via FRED",
        "source_url": "https://fred.stlouisfed.org/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    "population": {
        "label": "Population",
        "category": "Demographics",
        "unit": "People",
        "format": "integer",
        "definition": "Annual state resident population from FRED / Census.",
        "source": "Census / FRED",
        "source_url": "https://fred.stlouisfed.org/",
        "year_range": [1979, 2024],
        "scale": "sequential",
    },
    # ---- Criminal justice (Phase 4 — Section 2.13 of data appendix) ----
    "imprisonment_rate": {
        "label": "Imprisonment rate",
        "category": "Criminal justice",
        "unit": "Prisoners per 100,000 residents",
        "format": "rate",
        "definition": "Total prisoners under state jurisdiction (year-end stock) per 100,000 residents. Source: BJS National Prisoner Statistics. DC is NaN post-2001 (Lorton closed; DC prisoners transferred to BOP). Pre-1996 has gaps for years where the BJS PDF reports were not in the legacy archive (1981, 1984, 1993-1995).",
        "source": "BJS National Prisoner Statistics (NPS-1A)",
        "source_url": "https://bjs.ojp.gov/data-collection/national-prisoner-statistics-nps-program",
        "year_range": [1979, 2024],
        "scale": "sequential",
        "higher_is": "more incarceration",
    },
    "police_expenditure_per_capita_real_2024": {
        "label": "Police protection expenditure per capita (real 2024 USD)",
        "category": "Criminal justice",
        "unit": "U.S. dollars (2024)",
        "format": "currency",
        "definition": "State + local government combined expenditure on Police protection, per capita, deflated to 2024 dollars using BLS CPI-U. Source: Census Annual Survey of State and Local Government Finances. Linearly interpolated within state across 2003-2008 and 2012-2016 gap years; pre-2002 and 2023+ remain blank.",
        "source": "Census Annual Survey of State & Local Government Finances",
        "source_url": "https://www.census.gov/programs-surveys/gov-finances.html",
        "year_range": [2002, 2022],
        "scale": "sequential",
        "higher_is": "more police spending",
    },
    "has_death_penalty": {
        "label": "Death penalty (active statute)",
        "category": "Criminal justice",
        "unit": "Yes / No",
        "format": "binary",
        "definition": "1 if the state had an active death-penalty statute on December 31 of the year; 0 otherwise. Source: hand-coded from the published timeline of state abolitions and reinstatements (DPIC). Coded as statute-on-the-books, NOT moratoria-adjusted (so CA and PA remain coded 1 despite Newsom and Wolf moratoria).",
        "source": "Death Penalty Information Center (timeline of abolitions)",
        "source_url": "https://deathpenaltyinfo.org/",
        "year_range": [1979, 2024],
        "scale": "binary",
    },
    "executions_count": {
        "label": "Executions in year",
        "category": "Criminal justice",
        "unit": "Executions",
        "format": "integer",
        "definition": "Count of state-jurisdiction executions in this state-year (federal executions excluded). Source: DPIC executions database. 0 for state-years with no execution recorded.",
        "source": "Death Penalty Information Center (executions database)",
        "source_url": "http://deathpenaltyinfo.org/query/executions.csv",
        "year_range": [1979, 2024],
        "scale": "sequential",
        "higher_is": "more executions",
    },
    "sworn_officers_per_100k": {
        "label": "Sworn officers per 100,000 (state rollup)",
        "category": "Criminal justice",
        "unit": "Sworn officers per 100,000 residents",
        "format": "rate",
        "definition": "Full-time sworn (peace-officer-status) law-enforcement personnel summed across all reporting agencies in the state, divided by state population. Source: Kaplan LEOKA (openICPSR project 102180 V15) aggregated agency-level rows. Federal LE (FBI, DEA, ATF, US Marshals) and special-jurisdiction agencies (Amtrak, transit) excluded because they have no county FIPS.",
        "source": "Jacob Kaplan LEOKA (openICPSR 102180)",
        "source_url": "https://www.openicpsr.org/openicpsr/project/102180",
        "year_range": [1979, 2024],
        "scale": "sequential",
        "higher_is": "more police staffing",
    },
    # ---- Health & substances (added 2026-05-01 for the literature-backed
    # covariate restructure; documented in data_appendix Section 2.13.x) ----
    "alcohol_per_capita_ethanol_gallons": {
        "label": "Alcohol per capita (ethanol, gallons / year)",
        "category": "Health & substances",
        "unit": "Gallons of ethanol per resident age 14+ per year",
        "format": "rate",
        "definition": "NIAAA apparent per-capita ethanol consumption — sum of beer + wine + spirits ethanol equivalents in gallons, divided by state resident population age 14+. The canonical alcohol-availability proxy in gun-policy research (used by McClellan-Tekin 2017, Luca-Malhotra-Poliquin 2017, Koper-Roth 2001, Crifasi 2015). Source: NIAAA Alcohol Epidemiologic Data System / openICPSR project 105583 V5. Coverage 1977-2018; later years require the next openICPSR vintage.",
        "source": "NIAAA Surveillance Report (openICPSR 105583 V5)",
        "source_url": "https://www.openicpsr.org/openicpsr/project/105583",
        "year_range": [1977, 2018],
        "scale": "sequential",
        "higher_is": "more alcohol consumption",
    },
    "drug_overdose_per_100k": {
        "label": "Drug overdose mortality (per 100,000)",
        "category": "Health & substances",
        "unit": "Deaths per 100,000 residents",
        "format": "rate",
        "definition": "CDC NCHS Drug Poisoning Mortality, model-based death rate, aggregated from county-year (population-weighted) to state-year. Captures the opioid-era confounder that any post-2010 firearm-policy spec needs to control for (per McCourt 2020 suicide stack). Source: CDC NCHS NCHS-Drug-Poisoning-Mortality-by-County (data.cdc.gov/rpvx-m2md). Coverage 2003-2021.",
        "source": "CDC NCHS Drug Poisoning Mortality by County",
        "source_url": "https://data.cdc.gov/NCHS/NCHS-Drug-Poisoning-Mortality-by-County-United-Sta/rpvx-m2md",
        "year_range": [2003, 2021],
        "scale": "sequential",
        "higher_is": "more overdose deaths",
    },
    "religion_adherents_pct_2020": {
        "label": "Religious adherents as % of population (2020)",
        "category": "Health & substances",
        "unit": "Percent (0-100)",
        "format": "percent_pre",
        "definition": "Share of state population reported as adherents of any religious group in the 2020 US Religion Census (Religious Congregations and Membership Study). 2020 cross-section broadcast across all years (slow-moving baseline; the 1980/1990/2000/2010 censuses are paywalled at ARDA). Used as a suicide-spec covariate per Crifasi 2015, Kivisto-Phalen 2018, McCourt 2020.",
        "source": "ARDA US Religion Census 2020 (ASARB / RCMS)",
        "source_url": "https://www.usreligioncensus.org/",
        "year_range": [1979, 2024],
        "scale": "sequential",
        "higher_is": "more religious adherents",
    },
    # ---- Deaths-of-despair stack (added 2026-05-02 to absorb the post-2019
    # mental-health crisis and the fentanyl-driven overdose epidemic that
    # overlap with the permitless-carry adoption window). Motivated by
    # Case-Deaton (2015, 2017), Czeisler et al. (2020), Pirkis et al. (2021).
    "synthetic_opioid_death_rate": {
        "label": "Synthetic opioid (fentanyl) death rate",
        "category": "Health & substances",
        "unit": "Deaths per 100,000 residents",
        "format": "rate",
        "definition": "State-year synthetic-opioid (fentanyl-included) overdose death rate per 100,000, drawn from CDC Vital Statistics Rapid Release / Multiple Cause of Death using ICD-10 underlying cause T40.4. The post-2014 fentanyl-era surge nearly fully accounts for the rise in total drug-overdose deaths through 2022. Pre-1999 zero-fill; post-coverage carry-forward from the latest observed year. Used as a deaths-of-despair control alongside BRFSS frequent mental distress and NSDUH any-mental-illness prevalence.",
        "source": "CDC VSRR / NCHS Multiple Cause of Death (T40.4)",
        "source_url": "https://wonder.cdc.gov/mcd-icd10.html",
        "year_range": [1999, 2024],
        "scale": "sequential",
        "higher_is": "more fentanyl deaths",
    },
    "freq_mental_distress_pct": {
        "label": "Frequent mental distress (BRFSS)",
        "category": "Health & substances",
        "unit": "% of adults reporting >=14 poor mental-health days in past 30",
        "format": "percent_pre",
        "definition": "State-year prevalence of frequent mental distress, defined as adults reporting >=14 of the past 30 days when their mental health was not good. From the CDC Behavioral Risk Factor Surveillance System (BRFSS) Healthy Days module. Coverage 1993 onward; pre-1993 zero-fill. Used as a deaths-of-despair control alongside synthetic-opioid death rate and NSDUH any-mental-illness prevalence.",
        "source": "CDC BRFSS Healthy Days",
        "source_url": "https://www.cdc.gov/brfss/brfssprevalence/index.html",
        "year_range": [1993, 2024],
        "scale": "sequential",
        "higher_is": "more frequent mental distress",
    },
    "ami_pct": {
        "label": "Any mental illness prevalence (NSDUH)",
        "category": "Health & substances",
        "unit": "% of adults, past year",
        "format": "percent_pre",
        "definition": "State-year prevalence of any mental illness (AMI) in the past year among adults, from SAMHSA's National Survey on Drug Use and Health. NSDUH publishes state estimates as two-year rolling averages; we assign each estimate to the upper year. Coverage roughly 2008 onward (state-level NSDUH start); pre-2008 zero-fill. Used as a deaths-of-despair control alongside synthetic-opioid death rate and BRFSS frequent mental distress.",
        "source": "SAMHSA NSDUH state-level prevalence",
        "source_url": "https://www.samhsa.gov/data/nsduh/state-reports",
        "year_range": [2008, 2024],
        "scale": "sequential",
        "higher_is": "more mental illness",
    },
}


def main() -> None:
    print("Building merged panel ...")
    panel_df = build_panel()
    print(f"Panel rows: {len(panel_df):,}; columns: {len(panel_df.columns)}")
    print(f"Year range: {panel_df['year'].min()} - {panel_df['year'].max()}")
    print(f"States: {panel_df['state_abbr'].nunique()}")

    # Filter to variables we actually want exposed on the website (drop intermediates).
    keep_vars = [
        "state_abbr", "year",
    ] + list(VARIABLE_METADATA.keys())
    keep_vars = [c for c in keep_vars if c in panel_df.columns]
    panel_df = panel_df[keep_vars]

    panel_json = df_to_panel_json(panel_df)
    (OUT / "panel.json").write_text(json.dumps(panel_json, separators=(",", ":")))
    size_kb = (OUT / "panel.json").stat().st_size / 1024
    print(f"Wrote docs/data/panel.json ({size_kb:,.0f} KB)")

    # Compute observed year ranges per variable from actual data.
    metadata = {}
    for var, meta in VARIABLE_METADATA.items():
        if var not in panel_df.columns:
            continue
        s = panel_df[["year", var]].dropna()
        observed_range = [int(s["year"].min()), int(s["year"].max())] if len(s) else None
        meta_out = dict(meta)
        meta_out["observed_year_range"] = observed_range
        meta_out["observed_obs"] = int(len(s))
        metadata[var] = meta_out

    # Group variables by category for the UI.
    categories: dict[str, list[str]] = defaultdict(list)
    for var, meta in metadata.items():
        categories[meta["category"]].append(var)

    manifest = {
        "generated_at": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "year_range": [int(panel_df["year"].min()), int(panel_df["year"].max())],
        "states": sorted(panel_df["state_abbr"].dropna().unique().tolist()),
        "variables": list(metadata.keys()),
        "categories": {k: sorted(v) for k, v in categories.items()},
        "default_variable": "lawtotal",
        "default_year": 2024,
    }

    (OUT / "metadata.json").write_text(json.dumps(metadata, indent=2))
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote docs/data/metadata.json and docs/data/manifest.json")
    print(f"Variables: {len(metadata)} across {len(categories)} categories")


if __name__ == "__main__":
    main()
