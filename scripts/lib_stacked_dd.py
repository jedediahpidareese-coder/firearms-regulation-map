"""Shared stacked difference-in-differences (Cengiz et al. 2019) machinery
with optional entropy balancing (Hainmueller 2012). Used as a parallel
implementation to the Callaway-Sant'Anna ATT(g, t) work in cs_lib.py.

The stacked-DiD recipe (per Grier, Krieger, Munger 2024 AJPS, citing
Cengiz et al. 2019 and Baker, Larcker, Wang 2022):

  1. For each treatment cohort g:
       Build a "stack" that contains
         - treated state(s) in cohort g, observed across [g-K, g+H]
         - "clean" control states observed across [g-K, g+H]
       Each row is identified by (stack_id = g, state, year, event_time).
  2. Concatenate all stacks. The same state can appear as a control in
     multiple stacks; that's fine and is handled by clustering at the
     state level.
  3. Run a TWFE regression with stack-by-state and stack-by-event-time
     fixed effects:
         Y = beta * (treated * post) + alpha_{stack,state} + delta_{stack,event_time} + eps
     where post = 1{event_time >= 0}. beta is the average post-treatment
     ATT.
  4. Optionally weight controls within each stack so their baseline
     covariate distribution matches the treated unit's. Entropy balancing
     (Hainmueller 2012) is the most flexible such reweighting; it solves
     for nonnegative weights summing to one that match a chosen set of
     covariate moments while staying as close as possible to uniform
     weights in the entropy sense.
  5. Cluster-robust SEs at the state level.

This module exposes:

    build_stacks(panel, cohorts, never_treated, K, H, treatment_var)
        Returns a long DataFrame with columns
        [stack_id, state_abbr, year, event_time, treated_in_stack, post,
         population, ...all panel columns].
    entropy_balance(X_control, target, max_iter, tol)
        Hainmueller weights for one stack's controls.
    twfe_within(stacked, outcome, weights=None)
        Within-FE estimate of beta = ATT_post via Frisch-Waugh-Lovell:
        partial out stack-state and stack-event-time fixed effects from
        Y and from the treatment indicator, then regress.
    twfe_event_study(stacked, outcome, weights=None, leads=5, lags=5)
        Same but with full leads/lags interaction terms (omitting e=-1).
    cluster_robust_se(...)
        State-cluster sandwich SE for within-FE OLS.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"


# --------------- Stack construction --------------------------------------

def build_stacks(panel: pd.DataFrame,
                 cohorts: dict[int, list[str]],
                 never_treated: set[str],
                 K: int = 5, H: int = 5,
                 strict_pool_fn=None) -> pd.DataFrame:
    """Build a stacked DataFrame.

    K = pre-window size; H = post-window size (event time = -K..+H).

    For each cohort g we keep all panel rows for treated states and for
    the control pool, restricted to calendar years [g-K, g+H]. The same
    state may appear multiple times (across different stacks) when used
    as a control.

    strict_pool_fn(panel, never_treated, g) -> list of state_abbrs is an
    optional callback to apply policy-specific filtering of the control
    pool per cohort (the same hook the CS21 code uses).
    """
    pieces = []
    for g, treated_states in sorted(cohorts.items()):
        if strict_pool_fn is not None:
            controls = strict_pool_fn(panel, sorted(never_treated), g)
        else:
            controls = sorted(never_treated)
        if not controls:
            continue
        years = list(range(g - K, g + H + 1))
        keep = treated_states + controls
        sub = panel[(panel["state_abbr"].isin(keep))
                    & (panel["year"].isin(years))].copy()
        sub["stack_id"] = g
        sub["event_time"] = sub["year"] - g
        sub["treated_in_stack"] = sub["state_abbr"].isin(treated_states).astype(int)
        sub["post"] = (sub["event_time"] >= 0).astype(int)
        pieces.append(sub)
    if not pieces:
        return pd.DataFrame()
    out = pd.concat(pieces, ignore_index=True)
    out["stack_state"] = out["stack_id"].astype(str) + "_" + out["state_abbr"]
    out["stack_event"] = out["stack_id"].astype(str) + "_" + out["event_time"].astype(str)
    return out


# --------------- Entropy balancing (Hainmueller 2012) --------------------

def entropy_balance(X_control: np.ndarray, target: np.ndarray,
                    max_iter: int = 500, tol: float = 1e-9):
    """Hainmueller entropy balancing.

    X_control: (n, m) covariates of control units (centered or raw).
    target:    (m,)   target moment values (treated unit's covariate means).

    Returns w: (n,) nonneg weights summing to 1 that minimize Shannon
    entropy distance to uniform subject to (X_control.T @ w == target).

    Implementation: solve the convex dual via Newton's method. The dual
    objective in lambda is sum_i exp(-1 - sum_k lam_k * (X[i,k] - target_k))
    which is convex; gradient = weighted (X - target); Hessian is the
    weighted covariance of (X - target).
    """
    n, m = X_control.shape
    Z = X_control - target  # gradient becomes 0 when weighted Z = 0
    lam = np.zeros(m)
    converged = False
    for _ in range(max_iter):
        eta = -Z @ lam
        eta = eta - eta.max()  # numeric stability
        w = np.exp(eta)
        w = w / w.sum()
        grad = w @ Z  # (m,)
        if np.max(np.abs(grad)) < tol:
            converged = True
            break
        # Hessian: w-weighted covariance of Z (around its w-mean)
        Zbar = w @ Z
        Zc = Z - Zbar
        H = (Zc * w[:, None]).T @ Zc
        # Solve H step = grad with safety net.
        try:
            step = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            step, *_ = np.linalg.lstsq(H, grad, rcond=None)
        lam = lam + step
    return w, converged


def stack_eb_weights(stacked: pd.DataFrame,
                     covariates: list[str],
                     anchor_event_time: int = -1) -> pd.Series:
    """For each (stack_id, state) cell, assign an entropy-balancing weight
    (1.0 for treated; EB weight for controls). The weight is computed PER
    STACK using the covariate values at anchor_event_time (default e = -1,
    the omitted-year baseline) and the treated state's anchor values as
    the target moments.

    The weight is broadcast to all panel rows of that (stack_id, state),
    so that a single state-stack contributes a constant weight across all
    its years inside the stack.
    """
    weights = pd.Series(1.0, index=stacked.index)
    for stack_id, sg in stacked.groupby("stack_id"):
        anchor = sg[sg["event_time"] == anchor_event_time]
        if anchor.empty:
            continue
        treated = anchor[anchor["treated_in_stack"] == 1]
        controls = anchor[anchor["treated_in_stack"] == 0]
        if len(treated) == 0 or len(controls) == 0:
            continue
        cov_t = treated[covariates].mean().to_numpy()
        cov_c = controls[covariates].to_numpy()
        # Replace any NaN in controls with the mean to avoid blowing up.
        if np.isnan(cov_c).any():
            col_mean = np.nanmean(cov_c, axis=0)
            inds = np.where(np.isnan(cov_c))
            cov_c[inds] = np.take(col_mean, inds[1])
        if np.isnan(cov_t).any():
            continue
        try:
            w_c, ok = entropy_balance(cov_c, cov_t)
        except Exception:
            continue
        # Map control weights back: each control state gets a single weight
        # we broadcast to all of its rows in the stack.
        # Normalize so the average control weight is 1 (so the regression
        # interprets weighted control rows on the same scale as treated).
        w_c = w_c * len(w_c) / w_c.sum()
        for state, w in zip(controls["state_abbr"].to_numpy(), w_c):
            mask = (stacked["stack_id"] == stack_id) & (stacked["state_abbr"] == state)
            weights.loc[mask] = float(w)
    return weights


# --------------- Within-transformed TWFE regression ---------------------

def _demean(x: np.ndarray, group: pd.Series) -> np.ndarray:
    """Subtract group means from a numeric array; group is a categorical."""
    s = pd.Series(x, index=group.index)
    means = s.groupby(group).transform("mean")
    return (s - means).to_numpy()


def _wdemean(x: np.ndarray, group: pd.Series, w: np.ndarray) -> np.ndarray:
    """Weighted within-demean: subtract group weighted means from x."""
    s = pd.Series(x, index=group.index)
    ws = pd.Series(w, index=group.index)
    sw = (s * ws).groupby(group).transform("sum")
    swt = ws.groupby(group).transform("sum").replace(0, np.nan)
    means = (sw / swt).fillna(0)
    return (s - means).to_numpy()


def twfe_within(stacked: pd.DataFrame, outcome: str,
                weights: pd.Series | None = None,
                covariates: list[str] | None = None) -> dict:
    """Estimate beta in:
        Y = beta * (treated * post) + alpha_{stack,state} + delta_{stack,event}
            (+ gamma * X)
            + eps
    via Frisch-Waugh-Lovell within-FE partialling.

    weights: optional Series of regression weights (e.g. EB weights).
    covariates: optional list of column names to control for linearly.

    Returns {beta, se, n, n_clusters}.
    """
    df = stacked[[outcome, "treated_in_stack", "post", "stack_state",
                  "stack_event", "state_abbr"]
                 + (list(covariates) if covariates else [])
                 ].dropna(subset=[outcome])
    df = df.copy()
    df["DD"] = df["treated_in_stack"] * df["post"]
    if weights is not None:
        w = weights.loc[df.index].to_numpy(dtype=float)
    else:
        w = np.ones(len(df))
    # Demean Y and DD by stack-state then by stack-event (and the
    # covariates if any).
    cols_to_demean = ["DD", outcome] + (list(covariates) if covariates else [])
    arrs = {}
    for c in cols_to_demean:
        x = df[c].to_numpy(dtype=float)
        x = _wdemean(x, df["stack_state"], w)
        x = _wdemean(x, df["stack_event"], w)
        arrs[c] = x
    y = arrs[outcome]
    if covariates:
        X = np.column_stack([arrs["DD"]] + [arrs[c] for c in covariates])
    else:
        X = arrs["DD"][:, None]
    Wsqrt = np.sqrt(w)[:, None]
    beta, *_ = np.linalg.lstsq(X * Wsqrt, y * Wsqrt.flatten(), rcond=None)
    resid = y - (X @ beta).flatten()
    n = len(y)
    k = X.shape[1]
    # Cluster-robust SE at state level.
    XwX = (X.T * w) @ X
    XwXinv = np.linalg.pinv(XwX)
    score = X * resid[:, None] * w[:, None]
    cluster_sums = pd.DataFrame(score, index=df.index).groupby(df["state_abbr"]).sum().to_numpy()
    G = cluster_sums.shape[0]
    meat = cluster_sums.T @ cluster_sums
    # Small-cluster correction:
    correction = (G / max(G - 1, 1)) * (n / max(n - k, 1))
    cov = correction * XwXinv @ meat @ XwXinv
    se_beta = float(np.sqrt(cov[0, 0]))
    return {
        "beta": float(beta[0]),
        "se": se_beta,
        "z": float(beta[0] / se_beta) if se_beta > 0 else float("nan"),
        "n": int(n),
        "n_clusters": int(G),
        "covariates": list(covariates) if covariates else [],
    }


def twfe_event_study(stacked: pd.DataFrame, outcome: str,
                     weights: pd.Series | None = None,
                     covariates: list[str] | None = None,
                     leads: int = 5, lags: int = 5,
                     omit: int = -1) -> pd.DataFrame:
    """Event-study version of twfe_within. Returns one row per event_time
    with beta_e, SE_e, z_e."""
    df = stacked[[outcome, "treated_in_stack", "event_time",
                  "stack_state", "stack_event", "state_abbr"]
                 + (list(covariates) if covariates else [])
                 ].dropna(subset=[outcome]).copy()
    if weights is not None:
        w = weights.loc[df.index].to_numpy(dtype=float)
    else:
        w = np.ones(len(df))
    e_grid = list(range(-leads, lags + 1))
    out_rows = []
    for e in e_grid:
        if e == omit:
            out_rows.append({"event_time": e, "beta": 0.0, "se": 0.0, "z": 0.0,
                             "n": 0, "omitted": True})
            continue
        # Build a dummy = treated_in_stack * 1{event_time == e} for each e
        # and fit one regression per e (interaction-style). For simplicity
        # we fit each e independently using the full sample (the within-FE
        # absorbs other event-times' main effects via stack_event FE).
        df["DD_e"] = df["treated_in_stack"] * (df["event_time"] == e).astype(int)
        cols = ["DD_e", outcome] + (list(covariates) if covariates else [])
        arrs = {}
        for c in cols:
            x = df[c].to_numpy(dtype=float)
            x = _wdemean(x, df["stack_state"], w)
            x = _wdemean(x, df["stack_event"], w)
            arrs[c] = x
        y = arrs[outcome]
        if covariates:
            X = np.column_stack([arrs["DD_e"]] + [arrs[c] for c in covariates])
        else:
            X = arrs["DD_e"][:, None]
        Wsqrt = np.sqrt(w)[:, None]
        beta, *_ = np.linalg.lstsq(X * Wsqrt, y * Wsqrt.flatten(), rcond=None)
        resid = y - (X @ beta).flatten()
        n, k = len(y), X.shape[1]
        XwX = (X.T * w) @ X
        XwXinv = np.linalg.pinv(XwX)
        score = X * resid[:, None] * w[:, None]
        cs = pd.DataFrame(score, index=df.index).groupby(df["state_abbr"]).sum().to_numpy()
        G = cs.shape[0]
        meat = cs.T @ cs
        correction = (G / max(G - 1, 1)) * (n / max(n - k, 1))
        cov = correction * XwXinv @ meat @ XwXinv
        se_beta = float(np.sqrt(cov[0, 0]))
        out_rows.append({"event_time": e, "beta": float(beta[0]), "se": se_beta,
                         "z": float(beta[0] / se_beta) if se_beta > 0 else float("nan"),
                         "n": int(n), "omitted": False})
    return pd.DataFrame(out_rows)
