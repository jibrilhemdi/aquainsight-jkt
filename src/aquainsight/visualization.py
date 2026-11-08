"""Chart-first views: discrete sampling, explicit units and honest denominators."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from aquainsight.insights import group_statistics, period_statistics, period_values

INK = "#183b3b"
GREEN = "#337765"
COPPER = "#c5653d"
SLATE = "#8d9b9d"
COLOR = [GREEN, COPPER, "#637ba0", "#9a859d", "#b1a16b", "#75aab0"]


def polish(fig: go.Figure, height: int = 400) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=12, r=18, t=38, b=35),
        font=dict(family="Inter, system-ui, sans-serif", color=INK, size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.2, x=0, title_text=""),
        hoverlabel=dict(bgcolor="#fff", font_color=INK),
    )
    fig.update_xaxes(showline=False, zeroline=False, gridcolor="#e6e9e4")
    fig.update_yaxes(showline=False, zeroline=False, gridcolor="#e6e9e4")
    return fig


def time_field(df: pd.DataFrame) -> str:
    return (
        "sample_month"
        if not df.sample_date.notna().any()
        and "sample_month" in df
        and df.sample_month.ne("").any()
        else "sample_date"
    )


def unit_label(df: pd.DataFrame) -> str:
    return (df.unit_normalized.iloc[0] if len(df) else "") or "source scale · unit not supplied"


def measurements(df: pd.DataFrame) -> go.Figure:
    """One subdued point cloud instead of up to 120 site legend traces."""
    valid = period_values(df)
    label = (
        "Sampling month (exact day unavailable)"
        if time_field(df) == "sample_month"
        else "Measurement date"
    )
    fig = px.scatter(
        valid,
        x="period_label",
        y="value_numeric",
        hover_data={
            "site_id": True,
            "river_name": True,
            "value_raw": True,
            "source_name": True,
            "period_label": False,
        },
        labels={"period_label": label, "value_numeric": unit_label(df)},
        color_discrete_sequence=[GREEN],
    )
    fig.update_traces(marker=dict(size=8, opacity=0.65, line=dict(width=0.5, color="white")))
    stats = period_statistics(df)
    if len(stats):
        fig.add_trace(
            go.Scatter(
                x=stats.period_label,
                y=stats["median"],
                mode="markers",
                name="Period median",
                marker=dict(
                    symbol="diamond", size=13, color=INK, line=dict(color="white", width=2)
                ),
                customdata=stats[["n", "q1", "q3"]],
                hovertemplate="Median %{y:.3g}<br>n=%{customdata[0]}<br>IQR %{customdata[1]:.3g}–%{customdata[2]:.3g}<extra></extra>",
            )
        )
    fig.update_xaxes(
        type="category", categoryorder="array", categoryarray=sorted(valid.period_label.unique())
    )
    return polish(fig)


def period_distribution(df: pd.DataFrame) -> go.Figure:
    valid = period_values(df)
    stats = period_statistics(df)
    fig = go.Figure()
    # One category per round; sample counts remain visible in axis labels.
    for row in stats.itertuples(index=False):
        values = valid.loc[valid.period_label.eq(row.period_label)]
        fig.add_trace(
            go.Box(
                y=values.value_numeric,
                name=f"{row.period_label}<br>n={row.n}",
                boxpoints="all",
                jitter=0.32,
                pointpos=0,
                marker=dict(color=GREEN, opacity=0.35, size=4),
                line=dict(color=INK, width=1.4),
                fillcolor="rgba(51,119,101,.12)",
                showlegend=False,
                customdata=values[["site_id", "river_name"]],
                hovertemplate="%{y:.3g}<br>Site %{customdata[0]}<br>%{customdata[1]}<extra></extra>",
            )
        )
    fig.update_layout(
        yaxis_title=unit_label(df),
        xaxis_title="Sampling month (exact day unavailable)"
        if time_field(df) == "sample_month"
        else "Measurement date",
    )
    return polish(fig, 420)


def river_comparison(df: pd.DataFrame, limit: int = 12) -> go.Figure:
    stats = group_statistics(df).head(limit).sort_values("median")
    fig = go.Figure(
        go.Scatter(
            x=stats["median"],
            y=stats.river_name.replace("", "River not supplied"),
            mode="markers",
            marker=dict(size=10, color=GREEN),
            error_x=dict(
                type="data",
                array=stats.q3 - stats["median"],
                arrayminus=stats["median"] - stats.q1,
                color="#9db8ab",
                thickness=3,
                width=0,
            ),
            customdata=stats[["n", "q1", "q3"]],
            hovertemplate="%{y}<br>Median %{x:.3g}<br>n=%{customdata[0]} · IQR %{customdata[1]:.3g}–%{customdata[2]:.3g}<extra></extra>",
        )
    )
    fig.update_layout(xaxis_title=unit_label(df), yaxis_title=None)
    return polish(fig, max(300, 30 * len(stats) + 75))


def site_heatmap(df: pd.DataFrame, limit: int = 25) -> go.Figure:
    valid = period_values(df)
    ordered = valid.groupby("site_id").value_numeric.median().nlargest(limit).index
    pivot = (
        valid.loc[valid.site_id.isin(ordered)]
        .pivot_table(
            index="site_id", columns="period_label", values="value_numeric", aggfunc="median"
        )
        .reindex(ordered)
    )
    counts = valid.pivot_table(
        index="site_id", columns="period_label", values="value_numeric", aggfunc="count"
    ).reindex(index=pivot.index, columns=pivot.columns)
    fig = go.Figure(
        go.Heatmap(
            z=pivot.to_numpy(),
            x=pivot.columns,
            y=pivot.index,
            customdata=counts.to_numpy(),
            colorscale=[[0, "#f0f2dd"], [0.5, "#80af93"], [1, "#24534f"]],
            colorbar=dict(title="Reading"),
            hovertemplate="Site %{y}<br>%{x}<br>Median %{z:.3g}<br>n=%{customdata}<extra></extra>",
        )
    )
    fig.update_layout(xaxis_title="Sampling period", yaxis_title=None)
    fig.update_yaxes(autorange="reversed")
    return polish(fig, max(280, 22 * len(pivot) + 80))


def coverage_chart(df: pd.DataFrame) -> go.Figure:
    axis = time_field(df)
    dated = df.loc[df[axis].ne("")] if axis == "sample_month" else df.dropna(subset=[axis])
    counts = dated.groupby(axis).size().rename("observations").reset_index()
    fig = px.bar(
        counts,
        x=axis,
        y="observations",
        text_auto=True,
        color_discrete_sequence=[GREEN],
        labels={
            "sample_date": "Measurement date",
            "sample_month": "Sampling month (exact day unavailable)",
            "observations": "Observation count",
        },
    )
    return polish(fig, 300)


def parameter_coverage(df: pd.DataFrame) -> go.Figure:
    counts = (
        df.groupby("parameter_code")
        .size()
        .rename("observations")
        .reset_index()
        .sort_values("observations")
    )
    return polish(
        px.bar(
            counts,
            x="observations",
            y="parameter_code",
            orientation="h",
            color_discrete_sequence=[GREEN],
            labels={"parameter_code": "", "observations": "Observation count"},
        )
    )


def reference_outcomes(flags: pd.DataFrame) -> go.Figure:
    valid = flags.loc[flags.reference_status.ne("not_evaluable")]
    counts = (
        valid.groupby(["parameter_code", "reference_status"])
        .size()
        .rename("readings")
        .reset_index()
    )
    counts["status"] = counts.reference_status.map(
        {"within_reference": "Within reference", "outside_reference": "Outside reference"}
    )
    fig = px.bar(
        counts,
        x="readings",
        y="parameter_code",
        color="status",
        orientation="h",
        text="readings",
        color_discrete_map={"Within reference": GREEN, "Outside reference": COPPER},
        labels={"readings": "Compared readings only", "parameter_code": ""},
    )
    return polish(fig, max(280, 48 * valid.parameter_code.nunique() + 90))


def reference_readings(flags: pd.DataFrame, parameter: str) -> go.Figure:
    from aquainsight.standards import load_standards

    subset = flags.loc[
        flags.parameter_code.eq(parameter) & flags.reference_status.ne("not_evaluable")
    ].copy()
    rule = load_standards()["rules"][parameter]
    subset.loc[subset.unit_normalized.eq("µg/L"), "value_numeric"] /= 1000
    subset["unit_normalized"] = rule["unit"]
    valid = period_values(subset)
    valid["status"] = valid.reference_status.map(
        {"within_reference": "Within reference", "outside_reference": "Outside reference"}
    )
    fig = px.scatter(
        valid,
        x="period_label",
        y="value_numeric",
        color="status",
        hover_data=["site_id", "river_name", "value_raw"],
        color_discrete_map={"Within reference": GREEN, "Outside reference": COPPER},
        labels={"value_numeric": rule["unit"], "period_label": "Sampling period"},
    )
    threshold = rule["limits"][int(subset.reference_class.iloc[0]) - 1]
    if rule["kind"] == "range":
        fig.add_hrect(y0=threshold[0], y1=threshold[1], fillcolor=GREEN, opacity=0.08, line_width=0)
        for edge in threshold:
            fig.add_hline(
                y=edge, line_dash="dash", line_color=INK, annotation_text=f"Range edge {edge}"
            )
    else:
        fig.add_hline(
            y=threshold,
            line_dash="dash",
            line_color=INK,
            annotation_text=f"{rule['kind'].title()} {threshold} {rule['unit']}",
        )
    fig.update_traces(marker_size=8, marker_opacity=0.7)
    fig.update_xaxes(
        type="category", categoryorder="array", categoryarray=sorted(valid.period_label.unique())
    )
    return polish(fig, 420)


def station_atlas(mapped: pd.DataFrame, observations: pd.DataFrame) -> go.Figure:
    """Fast geographic scatter: no map tiles, GeoJSON, or external basemap requests."""
    counts = (
        observations.groupby(["source_id", "site_id"]).size().rename("observations").reset_index()
    )
    sites = mapped.merge(counts, on=["source_id", "site_id"], how="left")
    fig = go.Figure(
        go.Scattergl(
            x=sites.longitude,
            y=sites.latitude,
            mode="markers",
            marker=dict(size=10, color="#7ccbb1", line=dict(width=1, color="#d7f2e5"), opacity=0.9),
            customdata=sites[["site_id", "river_name", "site_name", "observations"]],
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>%{customdata[2]}<br>%{customdata[3]} observations<br>%{y:.5f}, %{x:.5f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=540,
        margin=dict(l=45, r=20, t=25, b=40),
        paper_bgcolor="#102c34",
        plot_bgcolor="#102c34",
        font=dict(color="#ccdfdb", family="Inter, system-ui, sans-serif"),
        xaxis=dict(title="Longitude · °E", gridcolor="#244149", zeroline=False, tickformat=".2f"),
        yaxis=dict(
            title="Latitude · °N (negative = south)",
            gridcolor="#244149",
            zeroline=False,
            tickformat=".2f",
            scaleanchor="x",
            scaleratio=1,
        ),
        dragmode="pan",
        hoverlabel=dict(bgcolor="#fff", font_color=INK),
    )
    return fig
