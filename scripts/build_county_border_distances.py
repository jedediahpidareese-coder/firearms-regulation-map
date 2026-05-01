"""Geometry layer: distance from each U.S. county to its nearest other-state county.

This is the foundation for a planned spatial regression-discontinuity analysis on
state borders. For each county, we want the great-circle distance from its
population centroid to the population centroid of the closest county in a
different state. That serves as the operational definition of
"distance to a state border" in our county panel: small values mean the county
sits near a state border where firearm-regulation regimes potentially differ;
large values mean the county is in a state's interior.

Inputs:

- Census 2020 Centers of Population for counties:
  https://www2.census.gov/geo/docs/reference/cenpop2020/county/CenPop2020_Mean_CO.txt
  Cached at data/county/CenPop2020_Mean_CO.txt (~171 KB) so re-runs do not re-fetch.
  Columns: STATEFP, COUNTYFP, COUNAME, STNAME, POPULATION, LATITUDE, LONGITUDE.

Method:

- Concatenate STATEFP (2 digits) + COUNTYFP (3 digits) -> 5-digit county_fips,
  matching the convention in data/processed/county_panel_2009_2024.csv.
- Compute the full pairwise great-circle distance matrix with the Haversine
  formula (R = 6371 km) using vectorized numpy. ~3,144 counties means
  ~9.9 million pairs, < 1 second on a laptop and ~80 MB float64.
- For each county, mask all same-state counties and take argmin over the
  remaining row.

Output:

    data/processed/county_border_distances.csv

with columns:
    county_fips, state_fips, lat, lon, nearest_other_state_fips,
    distance_to_nearest_other_state_km, nearest_other_state_county_fips
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "county" / "CenPop2020_Mean_CO.txt"
OUT = ROOT / "data" / "processed" / "county_border_distances.csv"
SOURCE_URL = (
    "https://www2.census.gov/geo/docs/reference/cenpop2020/county/CenPop2020_Mean_CO.txt"
)

EARTH_RADIUS_KM = 6371.0


def download_centroids() -> None:
    if RAW.exists():
        return
    RAW.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {SOURCE_URL} -> {RAW}")
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "firearms-regulation-research"})
    with urllib.request.urlopen(req, timeout=60) as r:
        RAW.write_bytes(r.read())
    print(f"  saved {RAW.stat().st_size:,} bytes")


def load_centroids() -> pd.DataFrame:
    df = pd.read_csv(
        RAW,
        dtype={"STATEFP": str, "COUNTYFP": str},
        encoding="utf-8-sig",
    )
    df["STATEFP"] = df["STATEFP"].str.zfill(2)
    df["COUNTYFP"] = df["COUNTYFP"].str.zfill(3)
    df["county_fips"] = df["STATEFP"] + df["COUNTYFP"]
    df = df.rename(
        columns={
            "STATEFP": "state_fips",
            "LATITUDE": "lat",
            "LONGITUDE": "lon",
            "POPULATION": "population",
            "COUNAME": "county_name",
            "STNAME": "state_name",
        }
    )
    return df[["county_fips", "state_fips", "county_name", "state_name", "population", "lat", "lon"]]


def haversine_matrix_km(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Full pairwise great-circle distance matrix in km."""
    lat_r = np.radians(lat)
    lon_r = np.radians(lon)
    dlat = lat_r[:, None] - lat_r[None, :]
    dlon = lon_r[:, None] - lon_r[None, :]
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat_r[:, None]) * np.cos(lat_r[None, :]) * np.sin(dlon / 2.0) ** 2
    a = np.clip(a, 0.0, 1.0)
    c = 2.0 * np.arcsin(np.sqrt(a))
    return EARTH_RADIUS_KM * c


def nearest_other_state(df: pd.DataFrame) -> pd.DataFrame:
    n = len(df)
    lat = df["lat"].to_numpy()
    lon = df["lon"].to_numpy()
    state = df["state_fips"].to_numpy()
    fips = df["county_fips"].to_numpy()

    print(f"Computing {n}x{n} Haversine matrix...")
    dist = haversine_matrix_km(lat, lon)

    # Mask same-state pairs (and the diagonal, trivially) with +inf so argmin skips them.
    same_state = state[:, None] == state[None, :]
    dist_other = np.where(same_state, np.inf, dist)

    j = np.argmin(dist_other, axis=1)
    nearest_dist = dist_other[np.arange(n), j]

    out = df[["county_fips", "state_fips", "lat", "lon"]].copy()
    out["nearest_other_state_county_fips"] = fips[j]
    out["nearest_other_state_fips"] = state[j]
    out["distance_to_nearest_other_state_km"] = nearest_dist
    return out[
        [
            "county_fips",
            "state_fips",
            "lat",
            "lon",
            "nearest_other_state_fips",
            "distance_to_nearest_other_state_km",
            "nearest_other_state_county_fips",
        ]
    ]


def diagnostic(out: pd.DataFrame) -> None:
    n = len(out)
    d = out["distance_to_nearest_other_state_km"]
    print(f"\nCounties: {n}")
    print(f"  with nearest other-state centroid < 50 km : {(d < 50).sum():>5}")
    print(f"  with nearest other-state centroid < 100 km: {(d < 100).sum():>5}")
    print(f"  with nearest other-state centroid < 200 km: {(d < 200).sum():>5}")
    print(f"  median distance: {d.median():.1f} km")
    print(f"  max distance:    {d.max():.1f} km (often a Hawaii or remote-Alaska county)")
    print(f"\nFurthest 5 counties from any other-state centroid:")
    far = out.nlargest(5, "distance_to_nearest_other_state_km")
    for _, row in far.iterrows():
        print(f"    {row['county_fips']} (state {row['state_fips']}): {row['distance_to_nearest_other_state_km']:8.1f} km -> {row['nearest_other_state_county_fips']}")


def main() -> None:
    download_centroids()
    df = load_centroids()
    print(f"Loaded {len(df)} county centroids across {df['state_fips'].nunique()} state FIPS codes.")
    out = nearest_other_state(df)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"\nWrote {OUT} ({len(out)} rows)")
    diagnostic(out)


if __name__ == "__main__":
    main()
