"""A dedicated, graph-first comparison workspace, independent of single-year filters."""

import calendar
import json
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from aquainsight.comparison import build_comparison, common_months, common_parameters
from aquainsight.insights import PARAMETER_NAMES
from aquainsight.official import OFFICIAL_SCHEMA_VERSION
from aquainsight.reports import csv_bytes
from aquainsight.visualization import COPPER, GREEN, period_distribution, polish


@st.cache_data(show_spinner=False, max_entries=8)
def cached_year_comparison(years, parameter, month, rivers, sites):
    return build_comparison(years, parameter, month, rivers, sites)


def render_comparison(files, loader):
    st.markdown(
        '<div class="eyebrow">AQUAINSIGHT / TWO-YEAR EXPLORER</div>', unsafe_allow_html=True
    )
    st.title("Compare 2022 & 2023")
    st.caption(
        "OFFICIAL · Local Jakarta catalog exports · descriptive comparisons, no causal or compliance conclusion"
    )
    if not {2022, 2023}.issubset(files):
        st.info(
            "Add both official 2022 and 2023 CSVs to data/raw to enable comparison. Single-year exploration and uploads remain available in the sidebar."
        )
        return
    datasets = {}
    try:
        with st.spinner("Aligning the two source datasets…"):
            for year in [2022, 2023]:
                path = files[year]
                stat = path.stat()
                datasets[year] = loader(
                    str(path), stat.st_size, stat.st_mtime_ns, OFFICIAL_SCHEMA_VERSION
                )
    except (ValueError, OSError, pd.errors.ParserError) as exc:
        st.error(f"Cannot load comparison sources: {exc}")
        return
    years = {year: ds.observations for year, ds in datasets.items()}
    parameters = common_parameters(years)
    if not parameters:
        st.info("The two files have no common canonical parameters.")
        return
    left, right = st.columns([2, 1])
    parameter = left.selectbox(
        "Compare parameter",
        parameters,
        index=parameters.index("pH") if "pH" in parameters else 0,
        format_func=lambda p: f"{p} · {PARAMETER_NAMES.get(p, 'Reported parameter')}",
        key="compare_parameter",
    )
    window = right.radio(
        "Comparison window", ["Shared calendar month", "All available rounds"], key="compare_window"
    )
    available_months = common_months(years)
    month = None
    if window == "Shared calendar month":
        if not available_months:
            st.info(
                "There are no shared calendar months. Choose All available rounds for descriptive source distributions."
            )
            return
        month = st.selectbox(
            "Calendar month",
            available_months,
            format_func=lambda m: calendar.month_name[int(m)],
            key="compare_month",
        )
        st.caption(
            f"{calendar.month_name[int(month)]} is aligned by calendar month, not by monitoring-period number. Exact sampling days and laboratory-method equivalence are unavailable."
        )
    else:
        st.caption(
            "Each source keeps its own sampling months. Annual distributions use different sampling windows; no paired numerical difference is calculated."
        )
    rivers_available = sorted(set(years[2022].river_name) & set(years[2023].river_name))
    sites_available = sorted(set(years[2022].site_id) & set(years[2023].site_id))
    with st.expander("Refine the comparison"):
        rivers = st.multiselect(
            "Comparison rivers", rivers_available, default=rivers_available, key="compare_rivers"
        )
        sites = st.multiselect(
            "Comparison sites", sites_available, default=sites_available, key="compare_sites"
        )
        st.caption(
            "These controls apply to both years. Single-year source and sidebar filters are independent."
        )
    result = cached_year_comparison(years, parameter, month, rivers, sites)
    audit = result.location_audit
    matched_locations = audit.loc[audit.location_status.eq("Consistent source location")]
    cards = st.columns(4)
    for col, label, value in zip(
        cards,
        [
            "2022 observations",
            "2023 observations",
            "Consistent source locations",
            "Paired numeric locations",
        ],
        [
            int(result.summary.iloc[0].observations),
            int(result.summary.iloc[1].observations),
            int(result.observations.site_id.nunique()),
            len(result.pairs),
        ],
    ):
        col.metric(label, f"{value:,}")
    st.caption(
        f"Location screen: same site ID, same river and valid consistent coordinates within 10 m. {len(matched_locations)} IDs pass in the complete sources; {len(audit) - len(matched_locations)} do not. Source-coordinate consistency does not independently prove station or laboratory-method equivalence."
    )
    if result.limitation:
        st.info(result.limitation)
    if result.observations.empty:
        st.info("No observations match the comparison filters. Broaden the selected rivers/sites.")
    else:
        st.subheader(f"{parameter}: the two source distributions")
        columns = st.columns(2)
        for column, year in zip(columns, [2022, 2023]):
            frame = result.observations.loc[result.observations.source_year.eq(year)]
            with column:
                st.markdown(f"**{year}**")
                stats = result.summary.loc[result.summary.year.eq(year)].iloc[0]
                st.caption(
                    f"{int(stats.exact_readings):,} exact readings · {stats.months or 'no months'} · {stats.unit}"
                )
                if len(frame) and frame.qualifier.eq("exact").any():
                    st.plotly_chart(
                        period_distribution(frame), width="stretch", config={"displaylogo": False}
                    )
                else:
                    st.info("No exact readings in this year/selection.")
        if not result.unit:
            st.caption(
                "Separate vertical axes preserve each source scale. The 2023 concentration unit is missing: no shared scale, percentage difference or improvement/deterioration claim is implied."
            )
        elif month is not None:
            st.caption(
                f"Both distributions use {result.unit}. Same-month distributions can still have different exact-reading coverage; paired charts below use only sites with an exact reading in both years."
            )
        st.subheader("Where does observation coverage differ?")
        counts = (
            result.observations.groupby(["source_year", "sample_month"])
            .size()
            .rename("observations")
            .reset_index()
        )
        counts["source_year"] = counts.source_year.astype(str)
        fig = px.bar(
            counts,
            x="sample_month",
            y="observations",
            color="source_year",
            text_auto=True,
            color_discrete_map={"2022": GREEN, "2023": COPPER},
            labels={
                "sample_month": "Actual source sampling month",
                "observations": "Reported parameter observations",
                "source_year": "Year",
            },
        )
        st.plotly_chart(polish(fig, 300), width="stretch", config={"displaylogo": False})
    if len(result.pairs):
        pairs = result.pairs
        median_delta = pairs.difference.median()
        st.subheader(f"Paired {parameter} differences at consistent source locations")
        st.markdown(
            f"**Median site difference: {median_delta:+.3g} {result.unit} (2023 − 2022)** across {len(pairs):,} paired sites in {calendar.month_name[int(month)]}. Each site contributes one median per year; the original reading counts remain available in the export."
        )
        st.caption(
            "This describes the supplied samples; it does not establish environmental change or identical laboratory methods. No percentage change is computed for pH, which is logarithmic."
        )
        scatter = px.scatter(
            pairs,
            x="value_2022",
            y="value_2023",
            color="river_name",
            hover_data=["site_id", "n_2022", "n_2023", "difference"],
            labels={
                "value_2022": f"2022 ({result.unit})",
                "value_2023": f"2023 ({result.unit})",
                "river_name": "River",
            },
        )
        lower = min(pairs.value_2022.min(), pairs.value_2023.min())
        upper = max(pairs.value_2022.max(), pairs.value_2023.max())
        pad = max((upper - lower) * 0.05, 0.05)
        scatter.add_shape(
            type="line",
            x0=lower - pad,
            y0=lower - pad,
            x1=upper + pad,
            y1=upper + pad,
            line=dict(color="#8d9b9d", dash="dash"),
        )
        scatter.update_xaxes(range=[lower - pad, upper + pad])
        scatter.update_yaxes(range=[lower - pad, upper + pad], scaleanchor="x", scaleratio=1)
        scatter.update_traces(marker_size=8, marker_opacity=0.8)
        st.plotly_chart(polish(scatter, 480), width="stretch", config={"displaylogo": False})
        st.caption(
            "The dashed diagonal means equal reported readings. Points above it are higher in 2023; points below are lower. Higher pH is not automatically better."
        )
        stats = (
            pairs.groupby("river_name")
            .difference.agg(median="median", n="count")
            .sort_values("median")
            .reset_index()
        )
        fig = go.Figure(
            go.Bar(
                x=stats["median"],
                y=stats.river_name,
                orientation="h",
                marker_color=[COPPER if value > 0 else GREEN for value in stats["median"]],
                customdata=stats[["n"]],
                hovertemplate="%{y}<br>Median site difference %{x:+.3g}<br>%{customdata[0]} paired sites<extra></extra>",
            )
        )
        fig.add_vline(x=0, line_color="#183b3b")
        fig.update_layout(
            xaxis_title=f"Median paired difference · 2023 − 2022 ({result.unit})", yaxis_title=None
        )
        st.plotly_chart(
            polish(fig, max(280, 25 * len(stats) + 90)),
            width="stretch",
            config={"displaylogo": False},
        )
    st.subheader("Export this comparison")
    filters = {
        "parameter": parameter,
        "calendar_month": month,
        "window": window,
        "rivers": rivers,
        "sites": sites,
        "location_tolerance_m": 10,
        "method_equivalence": "unverified",
        "numeric_difference_available": bool(len(result.pairs)),
    }
    st.download_button(
        "Download both years’ selected observations",
        csv_bytes(result.observations),
        "aquainsight_year_comparison_observations.csv",
        "text/csv",
    )
    if len(result.pairs):
        st.download_button(
            "Download paired differences",
            csv_bytes(result.pairs),
            "aquainsight_paired_differences.csv",
            "text/csv",
        )
    st.download_button(
        "Download location-matching audit",
        csv_bytes(audit),
        "aquainsight_location_alignment.csv",
        "text/csv",
    )
    provenance = {str(year): ds.metadata for year, ds in datasets.items()}
    report = f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>AquaInsight year comparison</title><style>body{{font:15px system-ui;margin:40px;max-width:1100px;color:#183b3b}}table{{border-collapse:collapse}}td,th{{padding:7px;border:1px solid #ddd}}</style><h1>AquaInsight · 2022 &amp; 2023</h1><p>OFFICIAL · Descriptive source comparison. No official compliance, causal or method-equivalence conclusion.</p><h2>Active comparison filters</h2><pre>{escape(json.dumps(filters, indent=2))}</pre><p>{escape(result.limitation)}</p><p>Exact sampling days are unavailable. Source locations must share ID/river and consistent coordinates within 10 m. A shared unit and calendar month are required for paired differences. Unknown units are never inferred; pH has no percentage-change calculation.</p><h2>Per-year coverage and separate-scale summaries</h2>{result.summary.to_html(index=False)}<h2>Paired site differences ({len(result.pairs)})</h2>{result.pairs.to_html(index=False)}<h2>Sources and file hashes</h2><pre>{escape(json.dumps(provenance, indent=2, default=str))}</pre></html>"""
    st.download_button(
        "Download comparison summary", report, "aquainsight_year_comparison.html", "text/html"
    )
    with st.expander("Matching details and records"):
        st.caption(
            "Matching identifies source-coordinate consistency only. Source addresses and methods may still differ. Excluded sites never reappear by filtering to one parameter/month."
        )
        if st.toggle("Show comparison records", key="comparison_records"):
            st.dataframe(result.observations, hide_index=True, width="stretch")
            st.dataframe(audit, hide_index=True, width="stretch")
