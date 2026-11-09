"""Descriptive year comparisons with explicit month, unit and location gates."""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class YearComparison:
    observations: pd.DataFrame
    location_audit: pd.DataFrame
    pairs: pd.DataFrame
    summary: pd.DataFrame
    unit: str
    limitation: str
    parameter: str
    month: str | None


def common_parameters(years: dict[int, pd.DataFrame]) -> list[str]:
    return sorted(set.intersection(*(set(df.parameter_code) for df in years.values())))


def common_months(years: dict[int, pd.DataFrame]) -> list[str]:
    return sorted(
        set.intersection(*(set(df.sample_month.str[-2:]) - {""} for df in years.values()))
    )


def station_alignment(
    left: pd.DataFrame, right: pd.DataFrame, tolerance_m: float = 10
) -> pd.DataFrame:
    """Source-coordinate consistency is a screen, not independent site authentication."""
    if tolerance_m < 0:
        raise ValueError("Coordinate tolerance must be nonnegative")
    rows = []
    for site in sorted(set(left.site_id) | set(right.site_id)):
        a, b = left.loc[left.site_id.eq(site)], right.loc[right.site_id.eq(site)]
        row = {"site_id": site, "location_status": "", "distance_m": None, "river_name": ""}
        if a.empty or b.empty:
            row["location_status"] = "Site ID absent in one year"
        else:
            rivers_a, rivers_b = set(a.river_name), set(b.river_name)
            row["river_name"] = " / ".join(sorted(rivers_a | rivers_b))
            if len(rivers_a) != 1 or rivers_a != rivers_b or "" in rivers_a:
                row["location_status"] = "River identity inconsistent or missing"
            else:
                coords_a = a[["latitude", "longitude"]].drop_duplicates()
                coords_b = b[["latitude", "longitude"]].drop_duplicates()
                if (
                    not a.coordinates_verified.all()
                    or not b.coordinates_verified.all()
                    or len(coords_a) != 1
                    or len(coords_b) != 1
                    or coords_a.isna().any().any()
                    or coords_b.isna().any().any()
                ):
                    row["location_status"] = "Source coordinates conflicting, shared or unverified"
                else:
                    lat_a, lon_a = map(float, coords_a.iloc[0])
                    lat_b, lon_b = map(float, coords_b.iloc[0])
                    if not all(
                        [
                            -90 <= lat_a <= 90,
                            -90 <= lat_b <= 90,
                            -180 <= lon_a <= 180,
                            -180 <= lon_b <= 180,
                        ]
                    ):
                        row["location_status"] = "Coordinates outside valid range"
                    else:
                        r_a, r_b = np.radians([lat_a, lat_b])
                        delta_lat, delta_lon = r_b - r_a, np.radians(lon_b - lon_a)
                        hav = (
                            np.sin(delta_lat / 2) ** 2
                            + np.cos(r_a) * np.cos(r_b) * np.sin(delta_lon / 2) ** 2
                        )
                        distance = float(6371000 * 2 * np.arcsin(np.sqrt(np.clip(hav, 0, 1))))
                        row["distance_m"] = distance
                        row["location_status"] = (
                            "Consistent source location"
                            if distance <= tolerance_m
                            else "Coordinates differ by more than 10 m"
                            if tolerance_m == 10
                            else f"Coordinates differ by more than {tolerance_m:g} m"
                        )
        rows.append(row)
    return pd.DataFrame(rows, columns=["site_id", "river_name", "location_status", "distance_m"])


def build_comparison(
    years: dict[int, pd.DataFrame],
    parameter: str,
    month: str | None = "08",
    rivers: list[str] | None = None,
    sites: list[str] | None = None,
) -> YearComparison:
    if set(years) != {2022, 2023}:
        raise ValueError("Comparison requires separate 2022 and 2023 observations")
    if parameter not in common_parameters(years):
        raise ValueError("Choose a parameter present in both years")
    if month is not None and month not in common_months(years):
        raise ValueError("Choose a calendar month observed in both years")
    audit = station_alignment(years[2022], years[2023])
    # Full-source audit precedes parameter, river, site and month filters.
    accepted = set(audit.loc[audit.location_status.eq("Consistent source location"), "site_id"])
    frames = []
    for year in [2022, 2023]:
        scope = (
            years[year]
            .loc[years[year].parameter_code.eq(parameter) & years[year].site_id.isin(accepted)]
            .copy()
        )
        if month is not None:
            scope = scope.loc[scope.sample_month.str[-2:].eq(month)]
        if rivers is not None:
            scope = scope.loc[scope.river_name.isin(rivers)]
        if sites is not None:
            scope = scope.loc[scope.site_id.isin(sites)]
        scope["source_year"] = year
        frames.append(scope)
    observations = pd.concat(frames, ignore_index=True)
    modes = set().union(*(set(frame.data_mode) for frame in years.values()))
    mode = (
        "SYNTHETIC DEMO"
        if "SYNTHETIC DEMO" in modes
        else "OFFICIAL"
        if modes == {"OFFICIAL"}
        else "USER-UPLOADED"
    )
    observations.attrs = {
        "data_mode": mode,
        "comparison_scope": "Separate-year observations at consistent source locations; no inferred units/methods",
    }
    rows = []
    units = {}
    for year, frame in zip([2022, 2023], frames):
        exact = frame.loc[frame.qualifier.eq("exact") & frame.value_numeric.notna()]
        # Empty selections are gaps, not zero medians or zero concentrations.
        units[year] = set(frame.unit_normalized)
        rows.append(
            {
                "year": year,
                "observations": len(frame),
                "exact_readings": len(exact),
                "sites": frame.site_id.nunique(),
                "median": exact.value_numeric.median(),
                "q1": exact.value_numeric.quantile(0.25),
                "q3": exact.value_numeric.quantile(0.75),
                "months": ", ".join(sorted(frame.sample_month.unique())),
                "unit": ", ".join(sorted(units[year])) or "Not supplied",
            }
        )
    summary = pd.DataFrame(rows)
    shared_unit = units[2022] == units[2023] and len(units[2022]) == 1 and "" not in units[2022]
    unit = next(iter(units[2022])) if shared_unit else ""
    limitation = ""
    if any(frame.empty for frame in frames):
        limitation = "No observations remain for one or both years under these filters."
    elif not shared_unit:
        limitation = "A shared measurement unit is not established. Separate source scales only; no numerical year-to-year delta is calculated."
    elif month is None:
        limitation = "Sampling months differ across years. Full-year distributions are descriptive; paired differences require a shared calendar month."
    pairs = pd.DataFrame(
        columns=[
            "site_id",
            "river_name",
            "value_2022",
            "value_2023",
            "n_2022",
            "n_2023",
            "difference",
            "unit",
            "calendar_month",
            "location_status",
        ]
    )
    if not limitation:
        parts = []
        for year, frame in zip([2022, 2023], frames):
            exact = frame.loc[frame.qualifier.eq("exact") & frame.value_numeric.notna()]
            part = (
                exact.groupby(["site_id", "river_name"])
                .value_numeric.agg(**{f"value_{year}": "median", f"n_{year}": "count"})
                .reset_index()
            )
            parts.append(part)
        pairs = parts[0].merge(
            parts[1], on=["site_id", "river_name"], how="inner", validate="one_to_one"
        )
        pairs["difference"] = pairs.value_2023 - pairs.value_2022
        pairs["unit"] = unit
        pairs["calendar_month"] = month
        pairs["location_status"] = (
            "Consistent source location; laboratory-method equivalence unverified"
        )
        if pairs.empty:
            limitation = "No site has an exact reading in both years for this selection."
    for year, frame in zip([2022, 2023], frames):
        for field in ["source_id", "source_name", "source_file", "source_url"]:
            pairs[f"{field}_{year}"] = " | ".join(sorted(set(frame[field])))
            audit[f"{field}_{year}"] = " | ".join(sorted(set(years[year][field])))
    audit["location_tolerance_m"] = 10
    audit["data_mode"] = mode
    audit.attrs = dict(observations.attrs)
    pairs["data_mode"] = mode
    pairs["comparison_note"] = (
        "Descriptive within-month difference; source location consistency screened within 10 m; laboratory-method equivalence unverified."
    )
    pairs.attrs = dict(observations.attrs)
    return YearComparison(observations, audit, pairs, summary, unit, limitation, parameter, month)
