"""Shared spatial regression-discontinuity machinery used by the per-policy
runners (run_rdd_permitless_carry.py, run_rdd_red_flag.py, run_rdd_ubc.py).

The identification strategy adapts Dube, Lester & Reich (2010, RESTAT) to
firearm policy: counties that sit close to a state border on opposite sides
of a policy boundary serve as treated/control pairs, with state-pair x year
fixed effects absorbing common regional shocks. The geometry layer
(`data/processed/county_border_distances.csv`, Section 2.12 of the data
appendix) defines each county's nearest other-state county and the
great-circle centroid distance between them; that distance is our band-
width selector and operational definition of "near a state border."

Pure Python; depends only on numpy and pandas. No econometrics packages.

Public API:

    OUTCOMES_PRIMARY            ordered dict of true-county-level crime outcomes
    OUTCOMES_SECONDARY          state-joined-down mortality (no within-state variation)
    BANDWIDTHS                  default bandwidth grid (km)
    DONUTS                      default donut-radius grid (km)
    ANALYSIS_YEARS              county panel window
    HEADLINE_BANDWIDTH_KM       100 km
    RANDOM_SEED                 shared RNG seed
    RA_COVARIATES               default covariates for the with-controls spec

    load_county_panel_with_borders()                              DataFrame
    derive_state_cohorts(panel, treatment_var, direction)         dict[year -> list[state_fips]]
    treatment_indicator(panel, treatment_var, direction)          Series (1 if treated in that year)

    build_border_sample(panel, treatment_var, direction,
                        bandwidth_km, donut_km=0,
                        drop_spillover_pairs=False)               DataFrame
        Returns the county-year subset with bandwidth/donut applied.
        Adds columns: state_pair, signed_distance_km, treat,
        pair_straddles_in_year, post.

    estimate_dlr(sample, outcome,
                 fe="pair_year",
                 cluster="state",
                 covariates=None,
                 weights=None)                                    dict
        Within-FE TWFE via iterative Frisch-Waugh-Lovell demeaning.
        Returns beta (ATT), SE, z, sample sizes.

    estimate_event_study(sample, outcome,
                         leads=5, lags=5, ...)                    DataFrame
        Per-event-time coefficients with the same FE/SE conventions.

    plot_event_study_svg(es_df, path, outcomes_dict, title_suffix)
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"

ANALYSIS_YEARS = (2009, 2024)
BANDWIDTHS = (50, 100, 200)
DONUTS = (0, 10, 25)
HEADLINE_BANDWIDTH_KM = 100
RANDOM_SEED = 7

# True county-level outcomes (Kaplan UCR aggregated). These are the outcomes
# where the spatial RDD adds genuine identification because there IS within-
# state county variation.
OUTCOMES_PRIMARY = OrderedDict([
    ("county_violent_crime_rate",   "County violent crime rate (per 100,000)"),
    ("county_murder_rate",          "County murder rate (per 100,000)"),
    ("county_property_crime_rate",  "County property crime rate (per 100,000)"),
    ("county_burglary_rate",        "County burglary rate (per 100,000) [placebo]"),
    ("county_motor_vehicle_theft_rate",
                                    "County motor vehicle theft rate (per 100,000) [placebo]"),
])

# State-joined-down mortality. Reported for completeness only -- by
# construction these have NO within-state county variation (every county in
# state s in year t carries state s's value), so the RDD on these outcomes
# reduces to a population-weighted state-level comparison restricted to the
# border-strip subsample. Methodology doc must be explicit about this.
OUTCOMES_SECONDARY = OrderedDict([
    ("state_firearm_suicide_rate",     "State firearm suicide rate (per 100,000)"),
    ("state_total_suicide_rate",       "State total suicide rate (per 100,000)"),
    ("state_nonfirearm_suicide_rate",  "State non-firearm suicide rate (per 100,000) [substitution]"),
    ("state_firearm_homicide_rate",    "State firearm homicide rate (per 100,000)"),
])

# Default covariates for the with-controls spec. Mirror the CS21 work
# (cs_lib.RA_COVARIATES) but use county-level versions and avoid log-scaling
# population since DLR pair-FE absorbs cross-sectional level differences.
RA_COVARIATES = [
    # County-grain demographics + economics already in county_panel
    "unemployment_rate",
    "poverty_pct_all_ages",
    "share_white_nh",
    "share_black_nh",
    "share_hispanic",
    "share_male",
    "share_age_15_24",
    "share_age_25_44",
    "share_bachelors_plus",
    # State-joined CJ controls (Section 2.13). Per the literature scan
    # (DAW 2019, Webster 2014), incarceration + police are required
    # in modern lethal-violence specs.
    "imprisonment_rate",
    "state_sworn_officers_per_100k",
    # State-joined alcohol per capita (NIAAA SR-122). McClellan-Tekin 2017,
    # Luca-Malhotra-Poliquin 2017, Koper-Roth 2001 all use it.
    "alcohol_per_capita_ethanol_gallons",
]


# ----------- Panel loading + treatment derivation -----------------------

def load_county_panel_with_borders() -> pd.DataFrame:
    """Load the county-year panel and join the border-distance geometry +
    the CJ-controls layer (Section 2.13 of data_appendix).

    Returns a DataFrame with all county_panel_2009_2024 columns plus:
        nearest_other_state_fips, distance_to_nearest_other_state_km,
        nearest_other_state_county_fips, lat, lon (geometry layer)
        county_sworn_officers_per_100k (county-grain CJ)
        imprisonment_rate, police_expenditure_per_capita_real_2024,
        has_death_penalty, executions_count,
        sworn_officers_per_100k (state-joined CJ)

    Also derives state_nonfirearm_suicide_rate where the components exist.
    """
    str_cols = {"county_fips": str, "state_fips": str}
    panel = pd.read_csv(PROC / "county_panel_2009_2024.csv", dtype=str_cols)
    panel["county_fips"] = panel["county_fips"].str.zfill(5)
    panel["state_fips"] = panel["state_fips"].str.zfill(2)

    bd = pd.read_csv(
        PROC / "county_border_distances.csv",
        dtype={
            "county_fips": str, "state_fips": str,
            "nearest_other_state_fips": str,
            "nearest_other_state_county_fips": str,
        },
    )
    bd["county_fips"] = bd["county_fips"].str.zfill(5)
    bd["state_fips"] = bd["state_fips"].str.zfill(2)
    bd["nearest_other_state_fips"] = bd["nearest_other_state_fips"].str.zfill(2)
    bd["nearest_other_state_county_fips"] = bd["nearest_other_state_county_fips"].str.zfill(5)

    panel = panel.merge(
        bd[["county_fips", "lat", "lon",
            "nearest_other_state_fips", "distance_to_nearest_other_state_km",
            "nearest_other_state_county_fips"]],
        on="county_fips", how="left",
    )

    # County-grain CJ controls (sworn officers per 100k). Optional -- if
    # the file is absent the merge silently no-ops.
    county_cj = PROC / "county_cj_controls_2009_2024.csv"
    if county_cj.exists():
        cc = pd.read_csv(county_cj, dtype={"county_fips": str, "state_fips": str})
        cc["county_fips"] = cc["county_fips"].str.zfill(5)
        keep = ["county_fips", "year", "county_sworn_officers_per_100k"]
        cc = cc[[c for c in keep if c in cc.columns]]
        panel = panel.merge(cc, on=["county_fips", "year"], how="left")

    # State-grain CJ controls joined down by (state_fips, year). All four
    # variables apply at the state grain; every county in the same state-
    # year carries the same value (no within-state variation, by design).
    state_cj = PROC / "state_cj_controls_1979_2024.csv"
    if state_cj.exists():
        sc = pd.read_csv(state_cj, dtype={"state_fips": str})
        sc["state_fips"] = sc["state_fips"].str.zfill(2)
        keep = ["state_fips", "year",
                "imprisonment_rate",
                "police_expenditure_per_capita_real_2024",
                "has_death_penalty", "executions_count",
                "sworn_officers_per_100k"]
        sc = sc[[c for c in keep if c in sc.columns]]
        # Rename state-grain sworn officers to disambiguate from the
        # county-grain version above.
        if "sworn_officers_per_100k" in sc.columns:
            sc = sc.rename(columns={"sworn_officers_per_100k": "state_sworn_officers_per_100k"})
        panel = panel.merge(sc, on=["state_fips", "year"], how="left")

    # NIAAA per-capita ethanol consumption (state-year, joined down).
    alc_path = PROC / "state_alcohol_per_capita_1977_2023.csv"
    if alc_path.exists():
        # File uses state_abbr; need state_fips bridge. Build from FIPS_TO_ABBR
        # used elsewhere; cs_lib already has the mapping but we'll inline since
        # lib_rdd otherwise doesn't depend on cs_lib.
        ABBR_TO_FIPS = {
            "AL":"01","AK":"02","AZ":"04","AR":"05","CA":"06","CO":"08","CT":"09","DE":"10",
            "DC":"11","FL":"12","GA":"13","HI":"15","ID":"16","IL":"17","IN":"18","IA":"19",
            "KS":"20","KY":"21","LA":"22","ME":"23","MD":"24","MA":"25","MI":"26","MN":"27",
            "MS":"28","MO":"29","MT":"30","NE":"31","NV":"32","NH":"33","NJ":"34","NM":"35",
            "NY":"36","NC":"37","ND":"38","OH":"39","OK":"40","OR":"41","PA":"42","RI":"44",
            "SC":"45","SD":"46","TN":"47","TX":"48","UT":"49","VT":"50","VA":"51","WA":"53",
            "WV":"54","WI":"55","WY":"56",
        }
        alc = pd.read_csv(alc_path)
        alc["state_fips"] = alc["state_abbr"].map(ABBR_TO_FIPS)
        alc = alc.dropna(subset=["state_fips"])[
            ["state_fips", "year", "alcohol_per_capita_ethanol_gallons"]]
        panel = panel.merge(alc, on=["state_fips", "year"], how="left")

    # CDC drug overdose mortality (state-year, joined down).
    od_path = PROC / "state_drug_overdose_2003_2021.csv"
    if od_path.exists():
        od = pd.read_csv(od_path)
        od["state_fips"] = od["state_abbr"].map(ABBR_TO_FIPS)
        od = od.dropna(subset=["state_fips"])[
            ["state_fips", "year", "drug_overdose_per_100k"]]
        panel = panel.merge(od, on=["state_fips", "year"], how="left")

    # Religious adherence (2020 cross-section; broadcast across years).
    rel_path = PROC / "state_religious_adherence_2020.csv"
    if rel_path.exists():
        rel = pd.read_csv(rel_path)
        rel["state_fips"] = rel["state_abbr"].map(ABBR_TO_FIPS)
        rel = rel.dropna(subset=["state_fips"])[
            ["state_fips", "religion_adherents_pct_2020"]]
        panel = panel.merge(rel, on="state_fips", how="left")

    # Derived non-firearm suicide rate (state-joined).
    if ("state_total_suicide_rate" in panel.columns
            and "state_firearm_suicide_rate" in panel.columns
            and "state_nonfirearm_suicide_rate" not in panel.columns):
        panel["state_nonfirearm_suicide_rate"] = (
            panel["state_total_suicide_rate"] - panel["state_firearm_suicide_rate"]
        )

    panel = panel[(panel["year"] >= ANALYSIS_YEARS[0]) & (panel["year"] <= ANALYSIS_YEARS[1])]
    return panel.reset_index(drop=True)


def treatment_indicator(panel: pd.DataFrame, treatment_var: str,
                        direction: str) -> pd.Series:
    """Return a 0/1 Series aligned to `panel` saying whether the policy is in
    force in that county-year.

    direction:
        "0to1" -- treated when the variable equals 1 (e.g., gvro==1 means
                  state has civilian-petition red-flag).
        "1to0" -- treated when the variable equals 0 (e.g., permitconcealed==0
                  means state is permitless).
    """
    v = panel[treatment_var]
    if direction == "0to1":
        return (v == 1).astype(int)
    if direction == "1to0":
        return (v == 0).astype(int)
    raise ValueError(f"unknown direction {direction!r}")


def derive_state_cohorts(panel: pd.DataFrame, treatment_var: str,
                         direction: str) -> dict[int, list[str]]:
    """For each state, find the first year the policy switches in the
    requested direction. Returns {adoption_year: [state_fips, ...]}.

    States that never switch are not represented.
    """
    cohorts: dict[int, list[str]] = {}
    for sf, g in panel.sort_values(["state_fips", "year"]).groupby("state_fips"):
        prev = None
        adoption_year = None
        for _, r in g.iterrows():
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
        if adoption_year is not None:
            cohorts.setdefault(adoption_year, []).append(sf)
    return cohorts


def build_border_sample(panel: pd.DataFrame,
                        treatment_var: str,
                        direction: str,
                        bandwidth_km: float,
                        donut_km: float = 0.0,
                        drop_spillover_pairs: bool = False) -> pd.DataFrame:
    """Build the border-strip county-year subset for one policy.

    Filters:
        - distance_to_nearest_other_state_km <= bandwidth_km
        - distance_to_nearest_other_state_km >= donut_km
        - drop county-years with missing treatment_var
        - drop Hawaii (15) and Puerto Rico (72): no usable cross-border
          policy comparison (nearest other-state centroid is across an ocean).

    Adds columns:
        treat                 -- 0/1 policy in force in this county-year
        state_pair            -- "AA-BB" with sorted state FIPS pair
        signed_distance_km    -- +d on the side that is treated, -d on the
                                  side that is control. Equals 0 only if
                                  both sides match treatment, in which case
                                  pair_straddles_in_year == 0.
        pair_straddles_in_year -- 1 if exactly one side of the pair has the
                                  policy in this year, else 0.
        pair_year             -- "{state_pair}_{year}" composite for the
                                  pair x year fixed effect.
        post                  -- alias of treat for DiD readers.

    `drop_spillover_pairs`: per Knight (2013), border counties may be partly
    treated by their *neighbor's* policy via gun flows. Setting this True
    drops state-pair-years where the control-side state itself borders a
    third state with the policy already in force, which would contaminate
    the control side.
    """
    df = panel.copy()
    df = df[df["distance_to_nearest_other_state_km"].notna()]
    df = df[df["state_fips"].isin(["15", "72"]) == False]
    df = df[df["nearest_other_state_fips"].isin(["15", "72"]) == False]
    df = df[df["distance_to_nearest_other_state_km"] <= bandwidth_km]
    df = df[df["distance_to_nearest_other_state_km"] >= donut_km]
    df = df.dropna(subset=[treatment_var])

    df["treat"] = treatment_indicator(df, treatment_var, direction).astype(int)
    df["post"] = df["treat"]

    # Build symmetric state-pair label.
    sa = df["state_fips"].to_numpy()
    sb = df["nearest_other_state_fips"].to_numpy()
    pair = np.where(sa < sb, sa + "-" + sb, sb + "-" + sa)
    df["state_pair"] = pair

    # Pair straddles a policy boundary in year t if exactly one of the two
    # states has the policy in that year.
    state_treat_by_year = (df.groupby(["state_fips", "year"])["treat"].max()
                           .reset_index().rename(columns={"treat": "_state_treat"}))
    df = df.merge(state_treat_by_year, on=["state_fips", "year"], how="left")
    df = df.merge(
        state_treat_by_year.rename(columns={
            "state_fips": "nearest_other_state_fips",
            "_state_treat": "_other_state_treat",
        }),
        on=["nearest_other_state_fips", "year"], how="left",
    )
    df["pair_straddles_in_year"] = (
        (df["_state_treat"].fillna(0) != df["_other_state_treat"].fillna(0))
    ).astype(int)
    df["signed_distance_km"] = np.where(
        df["treat"] == 1,
        df["distance_to_nearest_other_state_km"],
        -df["distance_to_nearest_other_state_km"],
    )
    df["pair_year"] = df["state_pair"].astype(str) + "_" + df["year"].astype(str)

    if drop_spillover_pairs:
        # For each (state_pair, year), test whether either state has another
        # already-treated neighbor besides its pair partner. We approximate
        # with state-level adjacency through the panel: for each state s in
        # year t, gather the set of OTHER states whose counties have s as
        # their nearest_other_state. If any of those third states is also
        # treated AND s is the "control" side of the current pair, drop the
        # county-year row.
        # This is a coarse first-pass spillover guard.
        pair_year_keep = _spillover_filter_pair_years(df, panel)
        df = df[df["pair_year"].isin(pair_year_keep)]

    df = df.drop(columns=["_state_treat", "_other_state_treat"])
    return df.reset_index(drop=True)


def _spillover_filter_pair_years(sample: pd.DataFrame,
                                 full_panel: pd.DataFrame) -> set:
    """Return the set of pair_year keys that survive the spillover filter."""
    treated_states_by_year = (
        sample.groupby("year")
        .apply(lambda g: set(g.loc[g["treat"] == 1, "state_fips"].unique()))
        .to_dict()
    )
    keep = set()
    for (pair, year), g in sample.groupby(["state_pair", "year"]):
        sa, sb = pair.split("-")
        treated_in_year = treated_states_by_year.get(year, set())
        # Identify which side is the "control" side of this pair.
        sa_treat = sa in treated_in_year
        sb_treat = sb in treated_in_year
        if sa_treat == sb_treat:
            keep.add(f"{pair}_{year}")
            continue
        control_state = sb if sa_treat else sa
        # Other states adjacent to control_state via the geometry layer.
        adj = set(full_panel.loc[full_panel["state_fips"] == control_state,
                                 "nearest_other_state_fips"].dropna().unique())
        adj |= set(full_panel.loc[full_panel["nearest_other_state_fips"] == control_state,
                                  "state_fips"].dropna().unique())
        adj.discard(control_state)
        adj.discard(sa if sa_treat else sb)
        if adj & treated_in_year:
            continue
        keep.add(f"{pair}_{year}")
    return keep


# ----------- Within-FE estimation (Frisch-Waugh-Lovell) ---------------

def _codes(s: pd.Series) -> tuple[np.ndarray, int]:
    """Map a categorical series to integer codes 0..n_groups-1."""
    cat = pd.Categorical(s)
    return cat.codes.astype(np.int64), len(cat.categories)


def _demean_one(x: np.ndarray, codes: np.ndarray, n_groups: int,
                w: np.ndarray) -> np.ndarray:
    """Subtract weighted group means from x (for one FE).

    Uses np.bincount for O(n) demeaning -- much faster than pandas groupby
    for our problem sizes (~50k rows, a few thousand groups).
    """
    sums = np.bincount(codes, weights=x * w, minlength=n_groups)
    counts = np.bincount(codes, weights=w, minlength=n_groups)
    means = np.where(counts > 0, sums / np.maximum(counts, 1e-12), 0.0)
    return x - means[codes]


def _demean_iterative(x: np.ndarray, fe_codes: list[tuple[np.ndarray, int]],
                      w: np.ndarray, max_iter: int = 50,
                      tol: float = 1e-9) -> np.ndarray:
    """Iteratively demean x by each (codes, n_groups) in fe_codes until the
    L_inf change between iterations is < tol. For two non-nested FEs this
    converges in ~5-15 iterations on our problem sizes.
    """
    out = x.astype(float).copy()
    for _ in range(max_iter):
        prev = out.copy()
        for codes, n_groups in fe_codes:
            out = _demean_one(out, codes, n_groups, w)
        if np.max(np.abs(out - prev)) < tol:
            break
    return out


def _build_fe_codes(sample: pd.DataFrame, fe: str) -> list[tuple[np.ndarray, int]]:
    """Translate a fixed-effects shorthand to a list of (codes, n_groups) tuples."""
    if fe == "pair_year":
        return [_codes(sample["county_fips"]), _codes(sample["pair_year"])]
    if fe == "twoway":
        return [_codes(sample["county_fips"]), _codes(sample["year"].astype(str))]
    if fe == "pair_only":
        return [_codes(sample["county_fips"]), _codes(sample["state_pair"])]
    if fe == "year":
        return [_codes(sample["year"].astype(str))]
    raise ValueError(f"unknown fe {fe!r}")


def _cluster_sandwich(X: np.ndarray, resid: np.ndarray, w: np.ndarray,
                      cluster_codes: np.ndarray, n_clusters: int,
                      n_params: int) -> np.ndarray:
    """One-way cluster-robust covariance matrix via the Liang-Zeger sandwich.

    cov = (X' W X)^-1 [G/(G-1) * n/(n-k)] sum_g (X_g' W_g e_g)(X_g' W_g e_g)' (X' W X)^-1
    """
    XwX = (X.T * w) @ X
    XwXinv = np.linalg.pinv(XwX)
    score = X * (resid * w)[:, None]
    cluster_sums = np.zeros((n_clusters, X.shape[1]))
    np.add.at(cluster_sums, cluster_codes, score)
    G = n_clusters
    n = len(resid)
    correction = (G / max(G - 1, 1)) * (n / max(n - n_params, 1))
    return correction * (XwXinv @ (cluster_sums.T @ cluster_sums) @ XwXinv)


def _twoway_cluster_sandwich(X: np.ndarray, resid: np.ndarray, w: np.ndarray,
                             c1_codes: np.ndarray, n1: int,
                             c2_codes: np.ndarray, n2: int,
                             c12_codes: np.ndarray, n12: int,
                             n_params: int) -> np.ndarray:
    """Cameron-Gelbach-Miller (2011) two-way clustering: V = V1 + V2 - V12."""
    V1 = _cluster_sandwich(X, resid, w, c1_codes, n1, n_params)
    V2 = _cluster_sandwich(X, resid, w, c2_codes, n2, n_params)
    V12 = _cluster_sandwich(X, resid, w, c12_codes, n12, n_params)
    return V1 + V2 - V12


def estimate_dlr(sample: pd.DataFrame, outcome: str,
                 fe: str = "pair_year",
                 cluster: str = "state",
                 covariates: list[str] | None = None,
                 weights: pd.Series | str | None = None) -> dict:
    """Estimate the DLR-style ATT in:

        Y = beta * treat + alpha (county FE) + gamma (state-pair x year FE)
            (+ delta * X)
            + eps

    via iterative within-FE Frisch-Waugh-Lovell demeaning.

    fe: see _build_fe_codes.
    cluster: 'state' (primary), 'state_pair', 'border_segment' (alias of
             state_pair for now), 'twoway_state_year', 'county'.
    weights: optional Series (regression weights), or 'population' to use
             county population, or None for unweighted.

    Returns dict {beta, se, z, n, n_clusters, n_pairs, n_treated_post,
    n_straddling_pair_years, fe, cluster, covariates}.
    """
    cols = [outcome, "treat", "county_fips", "pair_year", "state_pair",
            "state_fips", "year", "pair_straddles_in_year", "population"]
    if covariates:
        cols += [c for c in covariates if c not in cols]
    df = sample[cols].dropna(subset=[outcome, "treat"]).copy()
    if covariates:
        df = df.dropna(subset=[c for c in covariates])
    if len(df) < 20:
        return {"beta": float("nan"), "se": float("nan"), "z": float("nan"),
                "n": len(df), "fe": fe, "cluster": cluster,
                "error": "insufficient observations after filtering"}

    if isinstance(weights, str):
        if weights == "population":
            w = df["population"].astype(float).to_numpy()
        else:
            raise ValueError(f"unknown weights spec {weights!r}")
    elif weights is not None:
        w = weights.loc[df.index].astype(float).to_numpy()
    else:
        w = np.ones(len(df))

    fe_codes = _build_fe_codes(df, fe)

    # Demean Y, treat, and covariates.
    y = _demean_iterative(df[outcome].astype(float).to_numpy(), fe_codes, w)
    t = _demean_iterative(df["treat"].astype(float).to_numpy(), fe_codes, w)
    if covariates:
        Xs = [t]
        for c in covariates:
            Xs.append(_demean_iterative(df[c].astype(float).to_numpy(), fe_codes, w))
        X = np.column_stack(Xs)
    else:
        X = t[:, None]

    Wsqrt = np.sqrt(w)[:, None]
    beta, *_ = np.linalg.lstsq(X * Wsqrt, y * Wsqrt.flatten(), rcond=None)
    resid = y - (X @ beta).flatten()

    # Cluster-robust SE.
    n_params = X.shape[1]
    if cluster in ("state",):
        codes, n_g = _codes(df["state_fips"])
        cov = _cluster_sandwich(X, resid, w, codes, n_g, n_params)
        n_clusters = n_g
    elif cluster in ("state_pair", "border_segment"):
        codes, n_g = _codes(df["state_pair"])
        cov = _cluster_sandwich(X, resid, w, codes, n_g, n_params)
        n_clusters = n_g
    elif cluster == "county":
        codes, n_g = _codes(df["county_fips"])
        cov = _cluster_sandwich(X, resid, w, codes, n_g, n_params)
        n_clusters = n_g
    elif cluster == "twoway_state_year":
        c1, n1 = _codes(df["state_fips"])
        c2, n2 = _codes(df["year"].astype(str))
        c12, n12 = _codes(df["state_fips"] + "_" + df["year"].astype(str))
        cov = _twoway_cluster_sandwich(X, resid, w, c1, n1, c2, n2, c12, n12, n_params)
        n_clusters = (n1, n2)
    else:
        raise ValueError(f"unknown cluster {cluster!r}")

    se_beta = float(np.sqrt(max(cov[0, 0], 0.0)))
    return {
        "beta": float(beta[0]),
        "se": se_beta,
        "z": float(beta[0] / se_beta) if se_beta > 0 else float("nan"),
        "n": int(len(df)),
        "n_counties": int(df["county_fips"].nunique()),
        "n_pairs": int(df["state_pair"].nunique()),
        "n_treated_post": int((df["treat"] == 1).sum()),
        "n_straddling_pair_years": int(
            df.loc[df["pair_straddles_in_year"] == 1, "pair_year"].nunique()
        ),
        "n_clusters": n_clusters,
        "fe": fe,
        "cluster": cluster,
        "covariates": list(covariates) if covariates else [],
    }


def estimate_event_study(sample: pd.DataFrame, outcome: str,
                         leads: int = 5, lags: int = 5,
                         omit: int = -1,
                         fe: str = "pair_year",
                         cluster: str = "state",
                         covariates: list[str] | None = None,
                         weights: str | None = None,
                         cohorts: dict[int, list[str]] | None = None) -> pd.DataFrame:
    """Event-study version of estimate_dlr.

    Requires `cohorts` (mapping adoption_year -> list of state_fips) so we
    can compute event_time = year - adoption_year for treated states. For
    never-treated states event_time is set to NaN; they always contribute
    to the FE-absorbed control mean rather than a specific event-time bin.

    Returns one row per event_time in [-leads, +lags] with beta, SE, z, n.
    """
    if cohorts is None:
        raise ValueError("cohorts is required for event-study spec")
    state_to_g = {sf: g for g, ss in cohorts.items() for sf in ss}
    df = sample.copy()
    df["adoption_year"] = df["state_fips"].map(state_to_g)
    df["event_time"] = (df["year"] - df["adoption_year"]).where(
        df["adoption_year"].notna(), other=np.nan
    )
    rows = []
    for e in range(-leads, lags + 1):
        if e == omit:
            rows.append({"event_time": e, "beta": 0.0, "se": 0.0, "z": 0.0,
                         "n": 0, "omitted": True})
            continue
        df["treat"] = ((df["event_time"] == e) & df["adoption_year"].notna()).astype(int)
        out = estimate_dlr(df, outcome, fe=fe, cluster=cluster,
                           covariates=covariates, weights=weights)
        rows.append({
            "event_time": e, "beta": out["beta"], "se": out["se"],
            "z": out["z"], "n": out["n"], "omitted": False,
        })
    return pd.DataFrame(rows)


# ----------- SVG figure (matches cs_lib.plot_event_study_svg house style) ---

def plot_event_study_svg(es_df: pd.DataFrame, path: Path,
                         outcomes_dict: OrderedDict,
                         title_suffix: str = "") -> None:
    PANEL_W, PANEL_H = 380, 260
    GAP = 30
    PAD_L, PAD_R, PAD_T, PAD_B = 60, 18, 50, 50
    n_outcomes = len(outcomes_dict)
    n_cols = 2
    n_rows = (n_outcomes + n_cols - 1) // n_cols
    FIG_W = n_cols * PANEL_W + (n_cols - 1) * GAP + 30
    FIG_H = n_rows * PANEL_H + (n_rows - 1) * GAP + 70
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {FIG_W} {FIG_H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" font-size="11">',
        f'<text x="{FIG_W/2}" y="22" text-anchor="middle" font-size="14" font-weight="600">'
        f"Spatial RDD event study {title_suffix}</text>",
    ]
    for idx, (var, title) in enumerate(outcomes_dict.items()):
        sub = es_df[es_df["outcome"] == var].sort_values("event_time")
        col = idx % n_cols
        row = idx // n_cols
        x0 = 15 + col * (PANEL_W + GAP)
        y0 = 40 + row * (PANEL_H + GAP)
        parts.append(f'<rect x="{x0}" y="{y0}" width="{PANEL_W}" height="{PANEL_H}" fill="#fafaf7" stroke="#e2e2dc"/>')
        parts.append(f'<text x="{x0 + PANEL_W/2}" y="{y0 + 18}" text-anchor="middle" font-weight="600">{title}</text>')
        if sub.empty:
            parts.append(f'<text x="{x0 + PANEL_W/2}" y="{y0 + PANEL_H/2}" text-anchor="middle" fill="#888">no data</text>')
            continue
        e = sub["event_time"].to_numpy()
        beta = sub["beta"].to_numpy()
        se = sub["se"].to_numpy()
        x_lo, x_hi = float(e.min()) - 0.5, float(e.max()) + 0.5
        lower = beta - 1.96 * se
        upper = beta + 1.96 * se
        y_lo = float(min(lower.min(), 0.0))
        y_hi = float(max(upper.max(), 0.0))
        if y_lo == y_hi:
            y_lo, y_hi = y_lo - 1, y_hi + 1
        ix0 = x0 + PAD_L
        iy0 = y0 + PAD_T
        iw = PANEL_W - PAD_L - PAD_R
        ih = PANEL_H - PAD_T - PAD_B
        def px(v): return ix0 + (v - x_lo) / (x_hi - x_lo) * iw
        def py(v): return iy0 + ih - (v - y_lo) / (y_hi - y_lo) * ih
        if y_lo <= 0 <= y_hi:
            parts.append(f'<line x1="{ix0}" y1="{py(0)}" x2="{ix0+iw}" y2="{py(0)}" stroke="#aaaaaa" stroke-width="0.7"/>')
        band_pts = [(px(e[i]), py(upper[i])) for i in range(len(e))] + \
                   [(px(e[i]), py(lower[i])) for i in range(len(e) - 1, -1, -1)]
        band_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in band_pts)
        parts.append(f'<polygon points="{band_str}" fill="#1f3a5f" opacity="0.18"/>')
        line_pts = " ".join(f"{px(ei):.1f},{py(ai):.1f}" for ei, ai in zip(e, beta))
        parts.append(f'<polyline points="{line_pts}" fill="none" stroke="#1f3a5f" stroke-width="1.6"/>')
        for ei, ai in zip(e, beta):
            parts.append(f'<circle cx="{px(ei):.1f}" cy="{py(ai):.1f}" r="2.6" fill="#1f3a5f"/>')
        parts.append(f'<line x1="{px(-0.5):.1f}" y1="{iy0}" x2="{px(-0.5):.1f}" y2="{iy0+ih}" stroke="#b9461a" stroke-dasharray="3 3"/>')
        parts.append(f'<line x1="{ix0}" y1="{iy0+ih}" x2="{ix0+iw}" y2="{iy0+ih}" stroke="#444"/>')
        parts.append(f'<line x1="{ix0}" y1="{iy0}" x2="{ix0}" y2="{iy0+ih}" stroke="#444"/>')
        for ti in sorted(set(int(v) for v in e)):
            xv = px(ti)
            parts.append(f'<line x1="{xv:.1f}" y1="{iy0+ih}" x2="{xv:.1f}" y2="{iy0+ih+3}" stroke="#444"/>')
            parts.append(f'<text x="{xv:.1f}" y="{iy0+ih+15}" text-anchor="middle" fill="#444">{ti}</text>')
        for k in range(5):
            v = y_lo + (y_hi - y_lo) * k / 4
            yv = py(v)
            parts.append(f'<line x1="{ix0-3}" y1="{yv:.1f}" x2="{ix0}" y2="{yv:.1f}" stroke="#444"/>')
            parts.append(f'<text x="{ix0-6}" y="{yv+3:.1f}" text-anchor="end" fill="#444">{v:.2g}</text>')
        parts.append(f'<text x="{ix0+iw/2}" y="{iy0+ih+34}" text-anchor="middle" fill="#444">Event time (years from adoption)</text>')
        parts.append(f'<text x="{x0+12}" y="{iy0+ih/2}" text-anchor="middle" fill="#444" transform="rotate(-90 {x0+12} {iy0+ih/2})">Coefficient (per 100k)</text>')
    parts.append(f'<text x="{FIG_W-15}" y="{FIG_H-12}" text-anchor="end" fill="#888" font-size="10">'
                 'Shaded band: pointwise 95% CI from cluster-robust SE. Vertical dashed line marks the year before adoption.</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts))


# ----------- Battery runner (called by per-policy runners) ---------------

# The "core" robustness battery run for every policy. Each entry is one
# named spec with its variation from the headline. The Step-4 sensitivity
# agent will expand this grid; the per-policy runners stick to the core 10.
BATTERY_SPECS = [
    # (name, bandwidth_km, donut_km, fe, cluster, with_covariates, drop_spillover)
    ("headline",         100, 0,  "pair_year", "state",             False, False),
    ("bw_50km",          50,  0,  "pair_year", "state",             False, False),
    ("bw_200km",         200, 0,  "pair_year", "state",             False, False),
    ("donut_10km",       100, 10, "pair_year", "state",             False, False),
    ("donut_25km",       100, 25, "pair_year", "state",             False, False),
    ("fe_twoway",        100, 0,  "twoway",    "state",             False, False),
    ("cluster_pair",     100, 0,  "pair_year", "state_pair",        False, False),
    ("cluster_twoway",   100, 0,  "pair_year", "twoway_state_year", False, False),
    ("with_covariates",  100, 0,  "pair_year", "state",             True,  False),
    ("drop_spillover",   100, 0,  "pair_year", "state",             False, True),
]


def run_full_battery(panel: pd.DataFrame,
                     treatment_var: str,
                     direction: str,
                     policy_name: str,
                     out_dir: Path,
                     outcomes_primary: OrderedDict | None = None,
                     outcomes_secondary: OrderedDict | None = None,
                     covariates: list[str] | None = None,
                     event_study_leads: int = 5,
                     event_study_lags: int = 5) -> dict:
    """Run the full DLR-style RDD battery for one policy.

    Writes:
        out_dir/cohort_n.csv         one row per (cohort_year, n_states, states)
        out_dir/headline.csv         one row per outcome at the headline spec
        out_dir/robustness.csv       all 10 BATTERY_SPECS x all outcomes
        out_dir/event_study.csv      per (outcome, event_time) at headline spec
        out_dir/figures/event_study_primary.svg
        out_dir/figures/event_study_secondary.svg

    Returns a dict of summary stats for inline reporting.
    """
    if outcomes_primary is None:
        outcomes_primary = OUTCOMES_PRIMARY
    if outcomes_secondary is None:
        outcomes_secondary = OUTCOMES_SECONDARY
    if covariates is None:
        covariates = RA_COVARIATES

    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== {policy_name} ({treatment_var}, direction={direction}) ===")

    # 1) Cohorts
    cohorts = derive_state_cohorts(panel, treatment_var, direction)
    print(f"cohorts: {len(cohorts)} (years {sorted(cohorts)})")
    cohort_rows = [
        {"cohort_year": g, "n_states": len(s), "state_fips": ",".join(s)}
        for g, s in sorted(cohorts.items())
    ]
    pd.DataFrame(cohort_rows).to_csv(out_dir / "cohort_n.csv", index=False)

    # 2) Robustness battery
    all_outcomes = OrderedDict()
    all_outcomes.update(outcomes_primary)
    all_outcomes.update(outcomes_secondary)

    rows = []
    sample_cache: dict[tuple[float, float, bool], pd.DataFrame] = {}
    for spec_name, bw, donut, fe, cluster, with_cov, drop_spill in BATTERY_SPECS:
        cache_key = (bw, donut, drop_spill)
        if cache_key not in sample_cache:
            sample_cache[cache_key] = build_border_sample(
                panel, treatment_var, direction,
                bandwidth_km=bw, donut_km=donut,
                drop_spillover_pairs=drop_spill,
            )
        sample = sample_cache[cache_key]

        for outcome in all_outcomes:
            if outcome not in sample.columns:
                continue
            cov_list = covariates if with_cov else None
            res = estimate_dlr(
                sample, outcome, fe=fe, cluster=cluster, covariates=cov_list,
            )
            rows.append({
                "policy": policy_name,
                "spec_name": spec_name,
                "outcome": outcome,
                "outcome_label": all_outcomes[outcome],
                "outcome_stratum": "primary" if outcome in outcomes_primary else "secondary",
                "bandwidth_km": bw,
                "donut_km": donut,
                "fe": fe,
                "cluster": cluster,
                "covariates": ";".join(cov_list) if cov_list else "",
                "drop_spillover_pairs": int(drop_spill),
                "beta": res.get("beta"),
                "se": res.get("se"),
                "z": res.get("z"),
                "n": res.get("n"),
                "n_counties": res.get("n_counties"),
                "n_pairs": res.get("n_pairs"),
                "n_treated_post": res.get("n_treated_post"),
                "n_straddling_pair_years": res.get("n_straddling_pair_years"),
            })
        print(f"  {spec_name:18s} bw={bw:>3} donut={donut:>2} fe={fe:<10} cluster={cluster:<22} cov={int(with_cov)} spill={int(drop_spill)}")

    rob = pd.DataFrame(rows)
    rob.to_csv(out_dir / "robustness.csv", index=False)
    headline = rob[rob["spec_name"] == "headline"].copy()
    headline.to_csv(out_dir / "headline.csv", index=False)

    print("\nHeadline (bw=100, fe=pair_year, cluster=state, no covariates):")
    for _, r in headline.iterrows():
        marker = "*" if abs(r["z"] or 0) > 1.96 else " "
        print(f"  {marker} {r['outcome']:35s} beta={r['beta']:>+8.3f} se={r['se']:>6.3f} z={r['z']:>+5.2f} n={r['n']:>5}")

    # 3) Event study at headline spec
    print("\nEvent study at headline spec ...")
    sample_headline = sample_cache[(100, 0, False)]
    es_rows = []
    for outcome in all_outcomes:
        if outcome not in sample_headline.columns:
            continue
        es = estimate_event_study(
            sample_headline, outcome,
            leads=event_study_leads, lags=event_study_lags,
            fe="pair_year", cluster="state", cohorts=cohorts,
        )
        es["outcome"] = outcome
        es["outcome_label"] = all_outcomes[outcome]
        es["policy"] = policy_name
        es_rows.append(es)
    es_full = pd.concat(es_rows, ignore_index=True) if es_rows else pd.DataFrame()
    es_full.to_csv(out_dir / "event_study.csv", index=False)

    # 4) Event study figures
    if not es_full.empty:
        plot_event_study_svg(
            es_full, fig_dir / "event_study_primary.svg",
            outcomes_primary, title_suffix=f"({policy_name}, primary outcomes)",
        )
        plot_event_study_svg(
            es_full, fig_dir / "event_study_secondary.svg",
            outcomes_secondary, title_suffix=f"({policy_name}, secondary outcomes)",
        )

    return {
        "policy": policy_name,
        "n_cohorts": len(cohorts),
        "n_treated_states": sum(len(s) for s in cohorts.values()),
        "headline_rows": len(headline),
        "robustness_rows": len(rob),
        "event_study_rows": len(es_full),
    }
