"""Coverage counts never average unlike parameters or units."""

import pandas as pd


def filter_observations(
    df: pd.DataFrame,
    sites: list[str] | None = None,
    parameters: list[str] | None = None,
    rivers: list[str] | None = None,
    dates: tuple | None = None,
    include_undated: bool = True,
    months: list[str] | None = None,
) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    for column, values in [
        ("site_id", sites),
        ("parameter_code", parameters),
        ("river_name", rivers),
    ]:
        if values is not None:
            mask &= df[column].isin(values)
    if dates:
        mask &= df.sample_date.between(pd.Timestamp(dates[0]), pd.Timestamp(dates[1])) | (
            df.sample_date.isna() & include_undated
        )
    elif not include_undated:
        mask &= df.sample_date.notna() | df.get("sample_month", pd.Series("", index=df.index)).ne(
            ""
        )
    if months is not None:
        mask &= df.sample_month.isin(months)
    return df.loc[mask].copy()


def summary(df: pd.DataFrame) -> dict:
    # Date/site combinations are sampling visits, not inferred laboratory sample IDs.
    visits = df.loc[
        df.sample_date.notna(), ["source_id", "site_id", "sample_date"]
    ].drop_duplicates()
    samples = df.loc[df.sample_id.ne(""), ["source_id", "sample_id"]].drop_duplicates()
    months = df.get("sample_month", pd.Series("", index=df.index))
    month_visits = df.loc[months.ne(""), ["source_id", "site_id", "sample_month"]].drop_duplicates()
    return {
        "observations": len(df),
        "sites": df.site_id.nunique(),
        "parameters": df.parameter_code.nunique(),
        "dated_site_visits": len(visits),
        "identified_samples": len(samples),
        "first": df.sample_date.min(),
        "latest": df.sample_date.max(),
        "first_month": months.loc[months.ne("")].min() if months.ne("").any() else "",
        "latest_month": months.loc[months.ne("")].max() if months.ne("").any() else "",
        "site_months": len(month_visits),
    }


def site_coverage(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for site, group in df.groupby("site_id", sort=True):
        dates = group.sample_date.dropna().drop_duplicates().sort_values()
        gaps = dates.diff().dt.days.dropna()
        rows.append(
            {
                "site_id": site,
                "site_name": " / ".join(sorted(set(group.site_name) - {""})),
                "river_name": " / ".join(sorted(set(group.river_name) - {""})),
                "first_sample": group.sample_date.min(),
                "last_sample": group.sample_date.max(),
                "first_sample_month": group.sample_month.min() if "sample_month" in group else "",
                "last_sample_month": group.sample_month.max() if "sample_month" in group else "",
                "month_precision_observations": int(group.sample_month.ne("").sum())
                if "sample_month" in group
                else 0,
                "observations": len(group),
                "parameters": group.parameter_code.nunique(),
                "exact_readings_pct": round(100 * group.qualifier.eq("exact").mean(), 1),
                "dated_readings_pct": round(100 * group.sample_date.notna().mean(), 1),
                "largest_observed_gap_days": int(gaps.max()) if len(gaps) else None,
            }
        )
    return pd.DataFrame(rows)


def map_sites(df: pd.DataFrame) -> pd.DataFrame:
    valid = df.loc[
        df.coordinates_verified.eq(True) & df.latitude.notna() & df.longitude.notna()
    ].copy()
    # Moving/conflicting coordinates require investigation, not an averaged fake point.
    pairs = valid[["source_id", "site_id", "latitude", "longitude"]].drop_duplicates()
    stable = pairs.groupby(["source_id", "site_id"]).size()
    keys = set(stable[stable == 1].index)
    valid = valid.loc[[(a, b) in keys for a, b in zip(valid.source_id, valid.site_id)]]
    return valid.drop_duplicates(["source_id", "site_id"])
