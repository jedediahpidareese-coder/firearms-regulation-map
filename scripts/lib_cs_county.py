"""Shared Callaway-Sant'Anna ATT(g, t) machinery used by per-policy
county-grain runners (scripts/run_cs_county_*.py).

This is the COUNTY-GRAIN parallel of `scripts/cs_lib.py`. Read that
file first; this file mirrors its public API but switches the unit of
observation from `state_abbr` to `county_fips`. Treatment is still
assigned at the state level (state-level law adoption), so cohorts are
defined by state, but each cohort maps to ALL counties in the
adopting states. That gives much more statistical power than the
state-grain version: instead of 5-15 treated states per cohort the
machinery sees hundreds of treated counties per cohort.

Pure Python, only depends on numpy + pandas. No econometrics packages.
No matplotlib (SVG fallback only).

Public API (mirrors cs_lib):

    OUTCOMES_COUNTY          ordered dict of outcome variable -> display label
    ANALYSIS_YEARS           panel window (2009, 2024)
    EVENT_WINDOW             event-time bounds for aggregation/figures
    N_BOOTSTRAP              cluster-bootstrap reps
    RANDOM_SEED              shared RNG seed
    RA_COVARIATES_COUNTY     covariates for RA spec
    STRICT_WINDOW            event window used by the strict control rule

    load_county_panel_2009_2024()                              DataFrame
    long_diff_county(panel, outcome, fips_list, year_t, year_b)  Series

    derive_state_cohorts_for_county(panel, treatment_var, direction,
                   min_pre_k=5, exclude_after=None)
                   -> (cohorts, never_treated_states, dropped)

    strict_control_pool_county(panel, candidates, g,
                        rule_vars, rule_values)            -> list[str]

    run_one_outcome_county(panel, outcome, cohorts, never_treated,
                    spec, control_rule,
                    strict_rule_vars=..., strict_rule_values=...)  -> DataFrame

    event_study_aggregations_county(att_df)                DataFrame
    overall_att_county(att_df)                             DataFrame

    plot_event_study_county(es_df, path, spec, outcomes_dict,
                            title_suffix="")

    Plus the SVG fallback used inside plot_event_study_county.

KEY DIFFERENCES from cs_lib.py:
    1. Unit of observation: county_fips (5-digit string), not state_abbr.
    2. Cohort construction is BY STATE (treatment is state-level law
       adoption). Each cohort year g maps to ALL counties in the
       adopting states.
    3. Long-difference computed per county; treated cell = mean over
       treated counties; control cell = mean over control counties.
    4. Bootstrap SE clusters at the STATE level (counties within a
       state are correlated; treatment is assigned at state level).
       The Rademacher resampling weight is shared by all counties in a
       given state.
    5. RA covariates use county-level demographics + economy controls.

NOTE on state-joined-down mortality outcomes:
    `state_firearm_suicide_rate`, `state_total_suicide_rate`, and
    `state_firearm_homicide_rate` are STATE values broadcast to every
    county in the same state. They have NO within-state variation, so
    a county-grain analysis of these outcomes is identification-
    equivalent to the state-grain analysis once you cluster bootstrap
    at the state level. They are included in OUTCOMES_COUNTY for
    completeness / cross-checking against `cs_lib.py`, NOT because
    county granularity buys identification power on those outcomes.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"

ANALYSIS_YEARS = (2009, 2024)
EVENT_WINDOW = (-5, 5)
N_BOOTSTRAP = 2000
RANDOM_SEED = 7
RA_COVARIATES_COUNTY = [
    "unemployment_rate",
    "ln_pcpi_real_2024",
    "share_white_nh",
    "share_age_15_24",
    "share_age_25_44",
    "share_bachelors_plus",
    "ln_population",
]
STRICT_WINDOW = (-5, 5)

OUTCOMES_COUNTY = OrderedDict([
    ("county_violent_crime_rate",        "Violent crime rate (per 100k, county UCR)"),
    ("county_murder_rate",               "Murder rate (per 100k, county UCR)"),
    ("county_property_crime_rate",       "Property crime rate (per 100k, county UCR)"),
    ("county_burglary_rate",             "Burglary rate (per 100k, county UCR)"),
    ("county_motor_vehicle_theft_rate",  "Motor vehicle theft rate (per 100k, county UCR) [placebo]"),
    ("state_firearm_suicide_rate",       "State firearm suicide rate (joined down) [no county variation]"),
    ("state_total_suicide_rate",         "State total suicide rate (joined down) [no county variation]"),
    ("state_firearm_homicide_rate",      "State firearm homicide rate (joined down) [no county variation]"),
])

# State FIPS -> two-letter abbreviation (50 states + DC). The county
# panel only carries `state_fips`; the state-grain library and
# audit tables are keyed by `state_abbr`, so we attach the abbr in
# load_county_panel_2009_2024().
_STATE_FIPS_TO_ABBR = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY",
}
_STATE_ABBR_TO_FIPS = {v: k for k, v in _STATE_FIPS_TO_ABBR.items()}


# ----------- panel loading + cohort derivation --------------------------

def load_county_panel_2009_2024() -> pd.DataFrame:
    """Read the county-year panel (one row per county_fips x year).

    Reads CSV with explicit string dtype for FIPS columns (so leading
    zeros are preserved). Restricts to ANALYSIS_YEARS, drops DC
    (state_fips == "11") to mirror the state-grain library, and
    derives the two log columns the RA spec needs:
        ln_pcpi_real_2024 = log(pcpi_real_2024)
        ln_population     = log(population)

    Adds `state_abbr` from `state_fips` so downstream code (and the
    optional cross-check against cs_lib outputs) shares the same key.

    The CSV is read once with a single open call - reads are atomic
    on Windows so this is safe even if the orchestrator is rebuilding
    the file in parallel (we either see the old or the new version,
    never a partial write).
    """
    df = pd.read_csv(
        PROC / "county_panel_2009_2024.csv",
        dtype={"county_fips": str, "state_fips": str},
    )
    df = df[(df["year"] >= ANALYSIS_YEARS[0]) & (df["year"] <= ANALYSIS_YEARS[1])]
    df = df[df["state_fips"] != "11"]  # drop DC
    df["state_abbr"] = df["state_fips"].map(_STATE_FIPS_TO_ABBR)
    # Derived covariates for the RA spec.
    with np.errstate(divide="ignore", invalid="ignore"):
        df["ln_pcpi_real_2024"] = np.log(df["pcpi_real_2024"].astype(float))
        df["ln_population"] = np.log(df["population"].astype(float))
    df.loc[~np.isfinite(df["ln_pcpi_real_2024"]), "ln_pcpi_real_2024"] = np.nan
    df.loc[~np.isfinite(df["ln_population"]), "ln_population"] = np.nan
    return df.reset_index(drop=True)


def derive_state_cohorts_for_county(panel: pd.DataFrame,
                                    treatment_var: str,
                                    direction: str,
                                    min_pre_k: int = 5,
                                    exclude_after: int | None = None):
    """Build cohorts from a Tufts policy variable joined down to counties.

    Treatment is state-level. We collapse the county panel to one row
    per (state_fips, year) on the treatment variable (it's identical
    across counties in a state by construction), then find each
    state's first switch in the requested direction.

    direction:
        "0to1" — first year the variable goes from 0 to 1
                 (e.g., adopting a new restriction)
        "1to0" — first year the variable goes from 1 to 0
                 (e.g., dropping a permit requirement)

    exclude_after: if set, drop cohorts whose adoption year is greater
                   than this.

    Returns:
        cohorts: { adoption_year (int) : list of state_fips strings }
        never_treated: set of state_fips strings that never switch
        dropped: list of OrderedDict explaining drops
    """
    cohorts: dict[int, list[str]] = {}
    notes: list[OrderedDict] = []
    never_treated: set[str] = set()

    state_year = (panel[["state_fips", "year", treatment_var]]
                  .drop_duplicates(subset=["state_fips", "year"])
                  .sort_values(["state_fips", "year"]))

    for sf, group in state_year.groupby("state_fips"):
        prev = None
        adoption_year = None
        for _, r in group.iterrows():
            v = r[treatment_var]
            if pd.isna(v):
                continue
            if prev is not None:
                if direction == "0to1" and prev == 0 and v == 1:
                    adoption_year = int(r["year"])
                    break
                if direction == "1to0" and prev == 1 and v == 0:
                    adoption_year = int(r["year"])
                    break
            prev = v
        if adoption_year is None:
            never_treated.add(sf)
            continue
        if exclude_after is not None and adoption_year > exclude_after:
            notes.append(OrderedDict([
                ("state_fips", sf),
                ("state_abbr", _STATE_FIPS_TO_ABBR.get(sf, "")),
                ("adoption_year", adoption_year),
                ("dropped_reason",
                 f"adoption year > exclude_after={exclude_after}"),
            ]))
            continue
        if adoption_year - min_pre_k < ANALYSIS_YEARS[0]:
            notes.append(OrderedDict([
                ("state_fips", sf),
                ("state_abbr", _STATE_FIPS_TO_ABBR.get(sf, "")),
                ("adoption_year", adoption_year),
                ("dropped_reason",
                 f"adoption {adoption_year} too early for "
                 f"{min_pre_k}-yr pre-period in {ANALYSIS_YEARS[0]}+"),
            ]))
            continue
        cohorts.setdefault(adoption_year, []).append(sf)
    return cohorts, never_treated, notes


def strict_control_pool_county(panel: pd.DataFrame,
                               candidates: list[str], g: int,
                               rule_vars,
                               rule_values) -> list[str]:
    """Filter candidate states (state_fips strings) to those satisfying
    every rule_var == rule_value for every year in
    [g + STRICT_WINDOW[0], g + STRICT_WINDOW[1]].

    Like the state-grain version, but we deduplicate to (state_fips,
    year) since the rule variables are state-level.
    """
    lo = g + STRICT_WINDOW[0]
    hi = g + STRICT_WINDOW[1]
    keep_cols = ["state_fips", "year"] + list(rule_vars)
    state_year = (panel[keep_cols]
                  .drop_duplicates(subset=["state_fips", "year"]))
    out = []
    for sf in candidates:
        sub = state_year[(state_year["state_fips"] == sf)
                         & (state_year["year"] >= lo)
                         & (state_year["year"] <= hi)]
        if sub.empty:
            continue
        ok = True
        for var, val in zip(rule_vars, rule_values):
            if not (sub[var] == val).all():
                ok = False
                break
        if ok:
            out.append(sf)
    return out


# ----------- ATT(g, t) machinery (county grain) -------------------------

def long_diff_county(panel: pd.DataFrame, outcome: str,
                     fips_list: list[str], year_t: int, year_b: int) -> pd.Series:
    """Per-county long-difference y_{t} - y_{base} for the county_fips
    in `fips_list` (a list of 5-digit strings). Counties missing
    either year are dropped. Returns a Series indexed by county_fips."""
    sub = panel[panel["county_fips"].isin(fips_list)
                & panel["year"].isin([year_t, year_b])]
    if sub.empty:
        return pd.Series(dtype=float)
    pv = sub.pivot_table(index="county_fips", columns="year",
                         values=outcome, aggfunc="first")
    if year_t not in pv.columns or year_b not in pv.columns:
        return pd.Series(dtype=float)
    return (pv[year_t] - pv[year_b]).dropna()


def _counties_in_states(panel: pd.DataFrame, state_fips_list: list[str],
                        year: int) -> list[str]:
    """All county_fips that are in `state_fips_list` and exist in `year`."""
    sub = panel[panel["state_fips"].isin(state_fips_list)
                & (panel["year"] == year)]
    return sorted(sub["county_fips"].unique().tolist())


def _state_for_counties(panel: pd.DataFrame,
                        county_fips: list[str]) -> pd.Series:
    """Return a Series county_fips -> state_fips for the requested counties.
    Used to build cluster ids for the bootstrap."""
    sub = (panel[panel["county_fips"].isin(county_fips)]
           [["county_fips", "state_fips"]]
           .drop_duplicates(subset=["county_fips"]))
    return sub.set_index("county_fips")["state_fips"]


def att_gt_point_county(panel, outcome, g, t, treated_states, control_states):
    """Point ATT(g, t) at county grain.

    treated_states / control_states are lists of state_fips strings.
    All counties in those states (that have non-missing y at both g-1
    and t) are pooled. ATT = mean(treated long-diff) - mean(control
    long-diff)."""
    base = g - 1
    tr_counties = _counties_in_states(panel, treated_states, base)
    co_counties = _counties_in_states(panel, control_states, base)
    tr = long_diff_county(panel, outcome, tr_counties, t, base)
    co = long_diff_county(panel, outcome, co_counties, t, base)
    if len(tr) == 0 or len(co) == 0:
        return None, tr, co
    return float(tr.mean() - co.mean()), tr, co


def att_gt_se_county(panel, treated_long, control_long, n_b, rng):
    """Cluster bootstrap SE clustered at the STATE level.

    treated_long / control_long are Series indexed by county_fips.
    For each bootstrap rep we draw one Rademacher (+/-1) weight per
    state and apply the same weight to every county in that state -
    this is the standard cluster-bootstrap analog of the state-grain
    cs_lib.att_gt_se.
    """
    if len(treated_long) < 2 or len(control_long) < 2:
        return float("nan")
    tr_state = _state_for_counties(panel, treated_long.index.tolist())
    co_state = _state_for_counties(panel, control_long.index.tolist())
    tr_state = tr_state.reindex(treated_long.index)
    co_state = co_state.reindex(control_long.index)
    tr_states = sorted(tr_state.dropna().unique().tolist())
    co_states = sorted(co_state.dropna().unique().tolist())
    if len(tr_states) < 1 or len(co_states) < 1:
        return float("nan")
    tr_arr = treated_long.to_numpy()
    co_arr = control_long.to_numpy()
    tr_dev = tr_arr - tr_arr.mean()
    co_dev = co_arr - co_arr.mean()
    tr_state_idx = np.array([tr_states.index(s) for s in tr_state.to_numpy()])
    co_state_idx = np.array([co_states.index(s) for s in co_state.to_numpy()])
    boots = np.empty(n_b)
    n_tr_states = len(tr_states)
    n_co_states = len(co_states)
    for b in range(n_b):
        wt_tr_states = rng.choice([-1.0, 1.0], size=n_tr_states)
        wt_co_states = rng.choice([-1.0, 1.0], size=n_co_states)
        wt_tr = wt_tr_states[tr_state_idx]
        wt_co = wt_co_states[co_state_idx]
        boots[b] = (wt_tr * tr_dev).mean() - (wt_co * co_dev).mean()
    return float(np.std(boots, ddof=1))


def _baseline_X_county(panel, county_fips, year_b, covariates):
    """Per-county baseline covariates for RA spec."""
    sub = panel[panel["county_fips"].isin(county_fips)
                & (panel["year"] == year_b)]
    return sub.set_index("county_fips")[covariates].dropna()


def att_gt_ra_county(panel, outcome, g, t, treated_states, control_states,
                     covariates):
    """RA-spec point ATT at county grain."""
    base = g - 1
    tr_counties = _counties_in_states(panel, treated_states, base)
    co_counties = _counties_in_states(panel, control_states, base)
    tr_dy = long_diff_county(panel, outcome, tr_counties, t, base)
    co_dy = long_diff_county(panel, outcome, co_counties, t, base)
    if len(tr_dy) == 0 or len(co_dy) == 0:
        return None, tr_dy, co_dy
    tr_X = _baseline_X_county(panel, tr_counties, base, covariates)
    co_X = _baseline_X_county(panel, co_counties, base, covariates)
    tr_dy = tr_dy.loc[tr_dy.index.intersection(tr_X.index)]
    co_dy = co_dy.loc[co_dy.index.intersection(co_X.index)]
    tr_X = tr_X.loc[tr_dy.index]
    co_X = co_X.loc[co_dy.index]
    if len(co_dy) <= len(covariates) + 2:
        att, _, _ = att_gt_point_county(panel, outcome, g, t,
                                        treated_states, control_states)
        return att, tr_dy, co_dy
    Xc = np.c_[np.ones(len(co_X)), co_X.to_numpy()]
    yc = co_dy.to_numpy()
    beta, *_ = np.linalg.lstsq(Xc, yc, rcond=None)
    Xt = np.c_[np.ones(len(tr_X)), tr_X.to_numpy()]
    tr_pred = Xt @ beta
    return float(tr_dy.to_numpy().mean() - tr_pred.mean()), tr_dy, co_dy


def att_gt_ra_se_county(panel, outcome, g, t, treated_states, control_states,
                        covariates, n_b, rng):
    """RA-spec cluster bootstrap SE at county grain.

    Two-stage weighted-regression bootstrap (mirrors cs_lib.att_gt_ra_se)
    with one weight per STATE rather than one per unit. Within a state
    every county shares the same weight, capturing the within-state
    correlation that is induced by the state-level treatment.
    """
    base = g - 1
    tr_counties = _counties_in_states(panel, treated_states, base)
    co_counties = _counties_in_states(panel, control_states, base)
    tr_dy = long_diff_county(panel, outcome, tr_counties, t, base)
    co_dy = long_diff_county(panel, outcome, co_counties, t, base)
    if len(tr_dy) < 2 or len(co_dy) < 2:
        return float("nan")
    tr_X = _baseline_X_county(panel, tr_counties, base, covariates)
    co_X = _baseline_X_county(panel, co_counties, base, covariates)
    tr_dy = tr_dy.loc[tr_dy.index.intersection(tr_X.index)]
    co_dy = co_dy.loc[co_dy.index.intersection(co_X.index)]
    tr_X = tr_X.loc[tr_dy.index]
    co_X = co_X.loc[co_dy.index]
    if len(co_dy) <= len(covariates) + 2:
        return att_gt_se_county(panel, tr_dy, co_dy, n_b, rng)
    tr_state = _state_for_counties(panel, tr_dy.index.tolist()).reindex(tr_dy.index)
    co_state = _state_for_counties(panel, co_dy.index.tolist()).reindex(co_dy.index)
    tr_states = sorted(tr_state.dropna().unique().tolist())
    co_states = sorted(co_state.dropna().unique().tolist())
    tr_state_idx = np.array([tr_states.index(s) for s in tr_state.to_numpy()])
    co_state_idx = np.array([co_states.index(s) for s in co_state.to_numpy()])
    yc = co_dy.to_numpy()
    Xc = np.c_[np.ones(len(co_X)), co_X.to_numpy()]
    Xt = np.c_[np.ones(len(tr_X)), tr_X.to_numpy()]
    yt = tr_dy.to_numpy()
    n_tr_states = len(tr_states)
    n_co_states = len(co_states)
    boots = np.empty(n_b)
    for b in range(n_b):
        wt_co_states = rng.choice([0.5, 1.5], size=n_co_states)
        wt_co = wt_co_states[co_state_idx]
        W = np.sqrt(wt_co)[:, None]
        beta_b, *_ = np.linalg.lstsq(Xc * W, yc * W.flatten(), rcond=None)
        wt_tr_states = rng.choice([0.5, 1.5], size=n_tr_states)
        wt_tr = wt_tr_states[tr_state_idx]
        boots[b] = ((yt - Xt @ beta_b) * wt_tr).mean() / wt_tr.mean()
    return float(np.std(boots, ddof=1))


def run_one_outcome_county(panel, outcome, cohorts, never_treated,
                           spec, control_rule,
                           strict_rule_vars,
                           strict_rule_values):
    """Compute the per-(g, t) ATT panel for one outcome at county grain.

    cohorts: dict {g: [state_fips]} from derive_state_cohorts_for_county.
    never_treated: set of state_fips strings.
    spec: "or" (long-difference) or "ra" (regression-adjustment).
    control_rule: "broad" (every never-treated state) or "strict"
                  (apply strict_rule_vars / strict_rule_values filter).

    Returns a tidy DataFrame (one row per (g, t) cell) with:
        outcome, spec, control_rule, g_cohort, t_year, event_time,
        n_treated_states, n_control_states,
        n_treated_counties, n_control_counties,
        att, se
    """
    rng = np.random.default_rng(RANDOM_SEED)
    rows = []
    for g in sorted(cohorts):
        treated_states = cohorts[g]
        if control_rule == "strict":
            control_states = strict_control_pool_county(
                panel, sorted(never_treated), g,
                strict_rule_vars, strict_rule_values)
        else:
            control_states = sorted(never_treated)
        if not control_states:
            continue
        for t in range(ANALYSIS_YEARS[0], ANALYSIS_YEARS[1] + 1):
            if t == g - 1:
                continue
            if spec == "or":
                att, tr, co = att_gt_point_county(panel, outcome, g, t,
                                                  treated_states, control_states)
                if att is None:
                    continue
                se = att_gt_se_county(panel, tr, co, N_BOOTSTRAP, rng)
            else:
                att, tr, co = att_gt_ra_county(panel, outcome, g, t,
                                               treated_states, control_states,
                                               RA_COVARIATES_COUNTY)
                if att is None:
                    continue
                se = att_gt_ra_se_county(panel, outcome, g, t,
                                         treated_states, control_states,
                                         RA_COVARIATES_COUNTY,
                                         N_BOOTSTRAP, rng)
            rows.append(OrderedDict([
                ("outcome", outcome),
                ("spec", spec),
                ("control_rule", control_rule),
                ("g_cohort", g),
                ("t_year", t),
                ("event_time", t - g),
                ("n_treated_states", int(len(treated_states))),
                ("n_control_states", int(len(control_states))),
                ("n_treated_counties", int(len(tr))),
                ("n_control_counties", int(len(co))),
                ("att", float(att)),
                ("se", se),
            ]))
    return pd.DataFrame(rows)


# ----------- Aggregations -----------------------------------------------

def event_study_aggregations_county(att_df):
    """Aggregate the (g, t) panel to event-time, weighted by number of
    treated counties (which is much more granular than the state-grain
    weighting and gives larger cohorts more pull).
    """
    rows = []
    for (outcome, spec, control_rule), group in att_df.groupby(
            ["outcome", "spec", "control_rule"]):
        for e in range(EVENT_WINDOW[0], EVENT_WINDOW[1] + 1):
            sub = group[group["event_time"] == e]
            if sub.empty:
                continue
            w = sub["n_treated_counties"].to_numpy(dtype=float)
            if w.sum() == 0:
                continue
            w = w / w.sum()
            att_e = float((w * sub["att"]).sum())
            se_e = float(np.sqrt((w**2 * sub["se"]**2).sum()))
            rows.append(OrderedDict([
                ("outcome", outcome), ("spec", spec),
                ("control_rule", control_rule),
                ("event_time", e), ("att", att_e), ("se", se_e),
                ("n_cohorts", int(len(sub))),
                ("total_treated_counties", int(sub["n_treated_counties"].sum())),
                ("total_treated_states", int(sub["n_treated_states"].sum())),
            ]))
    return pd.DataFrame(rows)


def overall_att_county(att_df):
    """Average post-treatment ATT, weighted by treated-county count.
    Pre-trends average uses event_time in [EVENT_WINDOW[0], -2]."""
    rows = []
    for (outcome, spec, control_rule), group in att_df.groupby(
            ["outcome", "spec", "control_rule"]):
        post = group[group["event_time"] >= 0]
        if post.empty:
            continue
        w = post["n_treated_counties"].to_numpy(dtype=float)
        if w.sum() == 0:
            continue
        w = w / w.sum()
        att_bar = float((w * post["att"]).sum())
        se_bar = float(np.sqrt((w**2 * post["se"]**2).sum()))
        pre = group[(group["event_time"] <= -2)
                    & (group["event_time"] >= EVENT_WINDOW[0])]
        if not pre.empty and pre["n_treated_counties"].sum() > 0:
            wpr = (pre["n_treated_counties"].to_numpy(dtype=float)
                   / pre["n_treated_counties"].sum())
            pre_att = float((wpr * pre["att"]).sum())
            pre_se = float(np.sqrt((wpr**2 * pre["se"]**2).sum()))
            pre_z = pre_att / pre_se if pre_se > 0 else float("nan")
        else:
            pre_att = pre_se = pre_z = float("nan")
        rows.append(OrderedDict([
            ("outcome", outcome), ("spec", spec),
            ("control_rule", control_rule),
            ("att_overall_post", att_bar), ("se_overall_post", se_bar),
            ("z", att_bar / se_bar if se_bar > 0 else float("nan")),
            ("att_pretrends_avg", pre_att),
            ("se_pretrends_avg", pre_se),
            ("z_pretrends", pre_z),
            ("n_post_cells", int(len(post))),
            ("n_pre_cells", int(len(pre))),
        ]))
    return pd.DataFrame(rows)


# ----------- SVG figure (matplotlib-free fallback) ----------------------

def plot_event_study_county(es_df, path, spec, outcomes_dict,
                            title_suffix=""):
    """Pure-Python SVG event-study figure. No matplotlib dependency.

    `path` should end in .svg (or any extension; we always write SVG).
    `outcomes_dict` is the mapping {outcome_var: title} you want
    panelled. With more than 4 outcomes the layout extends downward.
    """
    es_df = es_df[es_df["spec"] == spec]
    plot_event_study_svg_county(es_df, path.with_suffix(".svg"), spec,
                                outcomes_dict, title_suffix)


def plot_event_study_svg_county(es_df, path, spec, outcomes_dict,
                                title_suffix=""):
    PANEL_W, PANEL_H = 380, 260
    GAP = 30
    PAD_L, PAD_R, PAD_T, PAD_B = 60, 18, 50, 50
    n_outcomes = len(outcomes_dict)
    n_cols = 2
    n_rows = (n_outcomes + n_cols - 1) // n_cols
    FIG_W = n_cols * PANEL_W + (n_cols - 1) * GAP + 30
    FIG_H = n_rows * PANEL_H + (n_rows - 1) * GAP + 70
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {FIG_W} {FIG_H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="11">',
        f'<text x="{FIG_W/2}" y="22" text-anchor="middle" '
        f'font-size="14" font-weight="600">'
        f"Callaway-Sant'Anna ATT by event time, county grain "
        f"({spec.upper()}) {title_suffix}</text>",
    ]
    layout = list(outcomes_dict.items())
    for idx, (var, title) in enumerate(layout):
        sub = es_df[es_df["outcome"] == var].sort_values("event_time")
        col = idx % n_cols
        row = idx // n_cols
        x0 = 15 + col * (PANEL_W + GAP)
        y0 = 40 + row * (PANEL_H + GAP)
        parts.append(
            f'<rect x="{x0}" y="{y0}" width="{PANEL_W}" height="{PANEL_H}" '
            f'fill="#fafaf7" stroke="#e2e2dc"/>')
        parts.append(
            f'<text x="{x0 + PANEL_W/2}" y="{y0 + 18}" '
            f'text-anchor="middle" font-weight="600">{title}</text>')
        if sub.empty:
            parts.append(
                f'<text x="{x0 + PANEL_W/2}" y="{y0 + PANEL_H/2}" '
                f'text-anchor="middle" fill="#888">no data</text>')
            continue
        e = sub["event_time"].to_numpy()
        att = sub["att"].to_numpy()
        se = sub["se"].to_numpy()
        x_lo, x_hi = float(e.min()) - 0.5, float(e.max()) + 0.5
        lower = att - 1.96 * se
        upper = att + 1.96 * se
        y_lo = float(min(lower.min(), 0.0))
        y_hi = float(max(upper.max(), 0.0))
        if y_lo == y_hi:
            y_lo, y_hi = y_lo - 1, y_hi + 1
        ix0 = x0 + PAD_L
        iy0 = y0 + PAD_T
        iw = PANEL_W - PAD_L - PAD_R
        ih = PANEL_H - PAD_T - PAD_B

        def px(v):
            return ix0 + (v - x_lo) / (x_hi - x_lo) * iw

        def py(v):
            return iy0 + ih - (v - y_lo) / (y_hi - y_lo) * ih

        if y_lo <= 0 <= y_hi:
            parts.append(
                f'<line x1="{ix0}" y1="{py(0)}" x2="{ix0+iw}" y2="{py(0)}" '
                f'stroke="#aaaaaa" stroke-width="0.7"/>')
        # Dot-and-whisker (Grier-Krieger-Munger 2024 / Roth-SA 2023 style):
        # solid dot for significant cells (|z| >= 1.96), hollow dot for ns,
        # whiskers spanning the 95% CI.
        with np.errstate(divide="ignore", invalid="ignore"):
            z = np.where(se > 0, att / se, 0.0)
        sig_mask = np.abs(z) >= 1.96
        SIG_COLOR = "#1f3a5f"; WHISKER_CAP = 4; DOT_R = 3.2
        for ei, ai, lo_, hi_, sig in zip(e, att, lower, upper, sig_mask):
            cx = px(ei); cy_pt = py(ai); cy_lo = py(lo_); cy_hi = py(hi_)
            opacity = 1.0 if sig else 0.35
            parts.append(
                f'<line x1="{cx:.1f}" y1="{cy_lo:.1f}" x2="{cx:.1f}" y2="{cy_hi:.1f}" '
                f'stroke="{SIG_COLOR}" stroke-width="1.4" opacity="{opacity:.2f}"/>')
            parts.append(
                f'<line x1="{cx-WHISKER_CAP:.1f}" y1="{cy_lo:.1f}" x2="{cx+WHISKER_CAP:.1f}" y2="{cy_lo:.1f}" '
                f'stroke="{SIG_COLOR}" stroke-width="1.2" opacity="{opacity:.2f}"/>')
            parts.append(
                f'<line x1="{cx-WHISKER_CAP:.1f}" y1="{cy_hi:.1f}" x2="{cx+WHISKER_CAP:.1f}" y2="{cy_hi:.1f}" '
                f'stroke="{SIG_COLOR}" stroke-width="1.2" opacity="{opacity:.2f}"/>')
            if sig:
                parts.append(f'<circle cx="{cx:.1f}" cy="{cy_pt:.1f}" r="{DOT_R}" fill="{SIG_COLOR}"/>')
            else:
                parts.append(f'<circle cx="{cx:.1f}" cy="{cy_pt:.1f}" r="{DOT_R}" fill="white" '
                             f'stroke="{SIG_COLOR}" stroke-width="1.3" opacity="{opacity:.2f}"/>')
        parts.append(
            f'<line x1="{px(-0.5):.1f}" y1="{iy0}" '
            f'x2="{px(-0.5):.1f}" y2="{iy0+ih}" '
            f'stroke="#b9461a" stroke-dasharray="3 3"/>')
        parts.append(
            f'<line x1="{ix0}" y1="{iy0+ih}" '
            f'x2="{ix0+iw}" y2="{iy0+ih}" stroke="#444"/>')
        parts.append(
            f'<line x1="{ix0}" y1="{iy0}" '
            f'x2="{ix0}" y2="{iy0+ih}" stroke="#444"/>')
        for ti in sorted(set(int(v) for v in e)):
            x = px(ti)
            parts.append(
                f'<line x1="{x:.1f}" y1="{iy0+ih}" '
                f'x2="{x:.1f}" y2="{iy0+ih+3}" stroke="#444"/>')
            parts.append(
                f'<text x="{x:.1f}" y="{iy0+ih+15}" '
                f'text-anchor="middle" fill="#444">{ti}</text>')
        for k in range(5):
            v = y_lo + (y_hi - y_lo) * k / 4
            y = py(v)
            parts.append(
                f'<line x1="{ix0-3}" y1="{y:.1f}" '
                f'x2="{ix0}" y2="{y:.1f}" stroke="#444"/>')
            parts.append(
                f'<text x="{ix0-6}" y="{y+3:.1f}" '
                f'text-anchor="end" fill="#444">{v:.2g}</text>')
        parts.append(
            f'<text x="{ix0+iw/2}" y="{iy0+ih+34}" '
            f'text-anchor="middle" fill="#444">'
            f"Event time (years from state-level adoption)</text>")
        parts.append(
            f'<text x="{x0+12}" y="{iy0+ih/2}" '
            f'text-anchor="middle" fill="#444" '
            f'transform="rotate(-90 {x0+12} {iy0+ih/2})">'
            f"ATT (per 100k)</text>")
    parts.append(
        f'<text x="{FIG_W-15}" y="{FIG_H-12}" '
        f'text-anchor="end" fill="#888" font-size="10">'
        f"Shaded band: pointwise 95% CI from state-clustered Rademacher "
        f"bootstrap. Vertical dashed line marks the year before adoption.</text>")
    parts.append("</svg>")
    path.write_text("\n".join(parts))
