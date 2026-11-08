"""Marker-only charts preserve the discrete nature of sampling."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COLOR = ["#087f8c", "#ee964b", "#5667a3", "#cf597e"]


def time_field(df: pd.DataFrame) -> str:
    return (
        "sample_month"
        if not df.sample_date.notna().any()
        and "sample_month" in df
        and df.sample_month.ne("").any()
        else "sample_date"
    )


def measurements(df: pd.DataFrame) -> go.Figure:
    if df.parameter_code.nunique() > 1 or df.unit_normalized.nunique() > 1:
        raise ValueError("Select one parameter and unit for a shared measurement axis")
    axis = time_field(df)
    known_time = df[axis].ne("") if axis == "sample_month" else df[axis].notna()
    valid = df.loc[known_time & df.value_numeric.notna() & df.qualifier.eq("exact")]
    unit = (df.unit_normalized.iloc[0] if len(df) else "") or "unit not supplied"
    fig = px.scatter(
        valid,
        x=axis,
        y="value_numeric",
        color="site_id",
        hover_data=["value_raw", "source_name", "site_name"],
        color_discrete_sequence=COLOR,
        labels={
            "sample_date": "Measurement date",
            "sample_month": "Sampling month (exact day unavailable)",
            "value_numeric": f"Observed reading ({unit})",
            "site_id": "Site",
        },
    )
    fig.update_traces(marker={"size": 10, "opacity": 0.85})
    if axis == "sample_month":
        fig.update_xaxes(
            type="category",
            categoryorder="array",
            categoryarray=sorted(valid.sample_month.unique()),
        )
    fig.update_layout(template="plotly_white", height=390, legend_title_text="Site")
    return fig


def coverage_chart(df: pd.DataFrame) -> go.Figure:
    axis = time_field(df)
    dated = df.loc[df[axis].ne("")] if axis == "sample_month" else df.dropna(subset=[axis])
    counts = dated.groupby(axis).size().rename("observations").reset_index()
    return px.bar(
        counts,
        x=axis,
        y="observations",
        color_discrete_sequence=COLOR,
        labels={
            "sample_date": "Measurement date",
            "sample_month": "Sampling month (exact day unavailable)",
            "observations": "Observation count",
        },
        template="plotly_white",
    )


def parameter_coverage(df: pd.DataFrame) -> go.Figure:
    counts = df.groupby("parameter_code").size().rename("observations").reset_index()
    return px.bar(
        counts,
        x="observations",
        y="parameter_code",
        orientation="h",
        color_discrete_sequence=COLOR,
        labels={"parameter_code": "Parameter", "observations": "Observation count"},
        template="plotly_white",
    )
