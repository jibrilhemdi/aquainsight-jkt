"""Run with: streamlit run app/streamlit_app.py."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from zipfile import BadZipFile

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from aquainsight import DEMO_WARNING, DISCLAIMER
from aquainsight.analytics import filter_observations, map_sites, site_coverage, summary
from aquainsight.demo import demo_frame, load_demo
from aquainsight.ingestion import excel_sheets, normalize, read_file
from aquainsight.mappings import ALIASES, suggest_mapping
from aquainsight.official import (
    OFFICIAL_SCHEMA_VERSION,
    available_official_files,
    identify_official_schema,
    load_official,
    normalize_official,
)
from aquainsight.reports import csv_bytes, monitoring_report, quality_json
from aquainsight.standards import compare, load_standards
from aquainsight.insights import (
    PARAMETER_NAMES,
    blocker_counts,
    comparison_coverage,
    exact_readings,
    group_statistics,
    period_statistics,
)
from aquainsight.visualization import (
    COPPER,
    GREEN,
    SLATE,
    coverage_chart,
    measurements,
    parameter_coverage,
    period_distribution,
    polish,
    reference_outcomes,
    reference_readings,
    river_comparison,
    site_heatmap,
    station_atlas,
    unit_label,
)

st.set_page_config(
    page_title="AquaInsight Jakarta", page_icon=":material/monitoring:", layout="wide"
)
st.markdown(
    """<style>
.stApp {background:#f7f7f2} h1,h2,h3 {color:#183b3b;letter-spacing:-.035em}
h1 {font-weight:650 !important;font-size:2.4rem !important}
[data-testid="stSidebar"] {background:#edf0e9;border-right:1px solid #dde4da}
[data-testid="stMetric"] {border-bottom:1px solid #d5ded3;padding:6px 0 14px}
[data-testid="stMetricLabel"] {text-transform:uppercase;font-size:11px;letter-spacing:.08em;color:#647571}
.block-container {padding-top:2.5rem;max-width:1480px}
.eyebrow {color:#668177;letter-spacing:.16em;font-size:11px;font-weight:650;margin-bottom:12px}
.brand {font:650 28px Georgia,serif;letter-spacing:-1.2px;color:#183b3b;margin:12px 0 2px}
.brand-sub {font-size:9px;letter-spacing:.2em;color:#647571;margin-bottom:26px}
[data-testid="stExpander"] {border:1px solid #dce3d8}
</style>""",
    unsafe_allow_html=True,
)


@st.cache_data
def cached_demo():
    return load_demo()


@st.cache_data
def cached_official(path: str, size: int, modified_ns: int, schema_version: str):
    file = Path(path)
    year = identify_official_schema(read_file(file.read_bytes(), file.name))
    if year is None:
        raise ValueError("Unrecognized Jakarta official schema")
    return load_official(file, year)


st.sidebar.markdown(
    '<div class="brand">AquaInsight</div><div class="brand-sub">JAKARTA / RIVER OBSERVATORY</div>',
    unsafe_allow_html=True,
)
official_files = available_official_files()
official_choices = {f"Official Jakarta {year}": path for year, path in official_files.items()}
pages = [
    "Overview",
    "Compare years",
    "Explore Measurements",
    "Reference Thresholds & Flags",
    "Sites & Map",
    "Data Quality & Sources",
    "Upload & Export",
]
page = st.sidebar.radio("Workspace", pages)
if page == "Compare years":
    from aquainsight.comparison_ui import render_comparison

    render_comparison(official_files, cached_official)
    st.stop()
mode = st.sidebar.selectbox(
    "Data source", [*official_choices, "Synthetic demo", "User upload"], key="data_source"
)
if "loaded_dataset" not in st.session_state:
    st.session_state.loaded_dataset = None
if mode in official_choices:
    source_path = official_choices[mode]
    stat = source_path.stat()
    try:
        with st.spinner("Loading official historical observations…"):
            dataset = cached_official(
                str(source_path), stat.st_size, stat.st_mtime_ns, OFFICIAL_SCHEMA_VERSION
            )
    except (ValueError, OSError, pd.errors.ParserError) as exc:
        st.error(f"Cannot load official data: {exc}")
        st.stop()
else:
    dataset = st.session_state.loaded_dataset if mode == "User upload" else cached_demo()
if dataset is None:
    st.info("No user dataset loaded. Open Upload & Export to preview and load a CSV or XLSX.")
    if page != "Upload & Export":
        st.stop()
    df = cached_demo().observations.iloc[:0]
else:
    df = dataset.observations

st.markdown('<div class="eyebrow">AQUAINSIGHT / JAKARTA</div>', unsafe_allow_html=True)
st.title(page if page != "Overview" else "A closer look at Jakarta’s rivers.")
st.caption(
    "Historical monitoring · measured variation, transparent comparisons · independent project"
)
is_demo = dataset is not None and (
    dataset.metadata.get("data_mode") == "SYNTHETIC DEMO" or df.data_mode.eq("SYNTHETIC DEMO").any()
)
if is_demo:
    st.warning(DEMO_WARNING)
elif dataset is not None:
    st.caption(
        "OFFICIAL · Historical observations from the locally supplied Jakarta catalog export"
        if dataset.metadata.get("data_mode") == "OFFICIAL"
        else "USER-UPLOADED · Historical observations · Source attribution supplied by uploader"
    )
if dataset is not None:
    st.caption(
        f"Dataset: {dataset.metadata.get('source_name', 'User upload')} · Mode: {'SYNTHETIC DEMO' if is_demo else dataset.metadata.get('data_mode', 'USER-UPLOADED')}"
    )
    if dataset.metadata.get("date_precision", "").startswith("month"):
        st.caption(
            "Sampling months only; exact days were not supplied. Use Compare years for an explicitly aligned view; cross-year method equivalence is unverified."
        )

st.sidebar.divider()
filter_panel = st.sidebar.expander("Refine observations", expanded=False)
filters = {}
for label, col, key in [
    ("River", "river_name", "rivers"),
    ("Site", "site_id", "sites"),
    ("Parameter", "parameter_code", "parameters"),
]:
    options = sorted(df[col].unique())
    filters[key] = filter_panel.multiselect(
        label,
        options,
        default=options,
        key=f"{mode}_{key}",
        format_func=lambda value: value or "(Not supplied)",
    )
valid_dates = df.sample_date.dropna()
dates = None
if len(valid_dates):
    selected_dates = filter_panel.date_input(
        "Measurement date range",
        value=(valid_dates.min().date(), valid_dates.max().date()),
        min_value=valid_dates.min().date(),
        max_value=valid_dates.max().date(),
        key=f"{mode}_dates",
    )
    if len(selected_dates) == 2:
        dates = tuple(selected_dates)
    else:
        filter_panel.info("Select both date endpoints to apply a date filter.")
include_undated = filter_panel.checkbox("Include undated observations", value=True)
month_options = sorted(set(df.sample_month) - {""})
months = (
    filter_panel.multiselect(
        "Sampling month", month_options, default=month_options, key=f"{mode}_months"
    )
    if month_options
    else None
)
filters.update(dates=dates, include_undated=include_undated, months=months)
filtered = filter_observations(df, **filters)
reference_class = st.sidebar.selectbox(
    "Exploratory reference class",
    [1, 2, 3, 4],
    index=0,
    help="A selection does not establish any site's legally designated class.",
)
ph_applicable = st.sidebar.checkbox("Confirm pH peat-water exception does not apply", value=False)


@st.cache_data(show_spinner=False, max_entries=8)
def cached_comparisons(observations, selected_class, ph_context):
    return compare(observations, selected_class, ph_context)


flags = cached_comparisons(filtered, reference_class, ph_applicable)
export_filters = {**filters, "ph_applicability_confirmed": ph_applicable}
st.sidebar.caption(
    "Discrete historical samples. No real-time alerts or official compliance findings."
)


def table(data: pd.DataFrame):
    st.dataframe(data, hide_index=True, width="stretch")


def download(data: pd.DataFrame, label: str, name: str):
    st.download_button(label, csv_bytes(data), name, "text/csv")


def graph(figure):
    st.plotly_chart(
        figure,
        width="stretch",
        config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
    )


def record_details(data, label, key, search=False):
    # Collapsed expanders still execute in Streamlit; defer heavy tables explicitly.
    with st.expander(f"{label} · {len(data):,} records"):
        if st.toggle("Show records", key=f"records_{key}"):
            query = st.text_input("Search records", key=f"search_{key}") if search else ""
            shown = (
                data.loc[
                    data.astype(str)
                    .apply(lambda c: c.str.contains(query, case=False, regex=False))
                    .any(axis=1)
                ]
                if query
                else data
            )
            table(shown)
            download(shown, "Download these records", f"aquainsight_{key}.csv")
        else:
            st.caption(
                "Open the record viewer when you need to audit or export the underlying data."
            )


def focus_parameter(data, key):
    options = sorted(data.parameter_code.unique())
    preferred = "BOD" if "BOD" in options else options[0]
    left, right = st.columns([3, 1])
    parameter = left.selectbox(
        "Parameter to explore",
        options,
        index=options.index(preferred),
        format_func=lambda p: f"{p} · {PARAMETER_NAMES.get(p, 'Reported parameter')}",
        key=f"focus_{mode}_{key}",
    )
    subset = data.loc[data.parameter_code.eq(parameter)]
    unit = right.selectbox(
        "Measurement scale",
        sorted(subset.unit_normalized.unique()),
        format_func=lambda u: u or "Unit not supplied",
        key=f"unit_{mode}_{key}",
    )
    subset = subset.loc[subset.unit_normalized.eq(unit)]
    if not unit:
        st.caption(
            "Source values are shown on their reported scale. The file supplies no unit, so these readings cannot be compared with concentration limits."
        )
    return parameter, subset


def period_note(data):
    stats = period_statistics(data)
    if stats.empty:
        return
    latest = stats.iloc[-1]
    st.markdown(
        f"**{latest.period_label}: median {latest['median']:,.3g}** across {int(latest['n']):,} exact readings. The middle half spans {latest.q1:,.3g}–{latest.q3:,.3g} ({unit_label(data)})."
    )
    st.caption(
        "Boxes show distributions, points show individual samples. No line implies continuous monitoring; changing sample coverage can affect medians."
    )


if page == "Overview":
    info = summary(filtered)
    for card, label, value in zip(
        st.columns(4),
        [
            "Observations",
            "Monitoring sites",
            "Parameters",
            "Site-months" if month_options else "Dated site visits",
        ],
        [
            info["observations"],
            info["sites"],
            info["parameters"],
            info["site_months"] if month_options else info["dated_site_visits"],
        ],
    ):
        card.metric(label, f"{value:,}")
    period = (
        "No verified measurement dates"
        if pd.isna(info["first"])
        else f"{info['first']:%d %b %Y} – {info['latest']:%d %b %Y}"
    )
    if info["first_month"]:
        period = f"{info['first_month']} – {info['latest_month']} · sampling months, exact days unavailable"
    st.caption(f"Monitoring period: {period}. Counts follow active filters.")
    if filtered.empty:
        st.info("No observations match these filters. Select additional options in the sidebar.")
    else:
        parameter, focused = focus_parameter(filtered, "overview")
        if not period_statistics(focused).empty:
            st.subheader(f"How does {parameter} vary between sampling rounds?")
            period_note(focused)
            graph(period_distribution(focused))
        else:
            st.info(
                "Time chart unavailable: no verified dates or sampling months with exact readings."
            )
        stats = group_statistics(focused)
        if len(stats):
            st.subheader(f"Where are the higher reported {parameter} readings?")
            first = stats.iloc[0]
            st.caption(
                f"{first.river_name or 'River not supplied'} has the highest selected river median ({first['median']:,.3g}; n={int(first['n'])}). Dots are medians; whiskers span the middle 50%. This is a reading comparison, not a river-health ranking."
            )
            graph(river_comparison(focused))
            if len(stats) > 12:
                st.caption(
                    f"Showing the 12 highest river medians out of {len(stats)}. Narrow the river filter to inspect others."
                )
        with st.expander("How much monitoring data is available?"):
            graph(coverage_chart(filtered))
            graph(parameter_coverage(filtered))
        record_details(filtered, "Underlying observations", "overview")

elif page == "Explore Measurements":
    if filtered.empty:
        st.info("No matching observations. Adjust sidebar filters.")
    else:
        parameter, focused = focus_parameter(filtered, "explore")
        view = st.radio(
            "View", ["Across rounds", "Between rivers", "Across sites"], horizontal=True
        )
        if exact_readings(focused).empty:
            st.info(
                "No exact numeric readings available for this selection. Qualified values remain in the record viewer."
            )
        elif view == "Between rivers":
            st.subheader(f"River differences in {parameter}")
            st.caption(
                "Median and middle 50% of exact reported readings; hover for sample counts. Up to 12 highest medians are shown."
            )
            graph(river_comparison(focused))
        elif view == "Across sites":
            if period_statistics(focused).empty:
                st.info("Site-period chart unavailable: no dated exact readings.")
            else:
                st.subheader(f"Which sites have higher {parameter} readings?")
                st.caption(
                    "Up to 25 sites with the highest selected median. Each cell is a site-period median; hover for count. Blank cells mean no exact reading, never zero. Use sidebar site filters to inspect any specific site."
                )
                graph(site_heatmap(focused))
        elif period_statistics(focused).empty:
            st.info("No dated exact numeric readings available for this chart.")
        else:
            st.subheader(f"Individual {parameter} readings across rounds")
            period_note(focused)
            graph(measurements(focused))
        record_details(filtered, "Search and audit observations", "explore", search=True)
        download(filtered, "Download filtered observations", "aquainsight_filtered.csv")

elif page == "Reference Thresholds & Flags":
    st.caption(DISCLAIMER)
    coverage = comparison_coverage(flags)
    st.subheader("What can this dataset actually be compared against?")
    for col, label, value in zip(
        st.columns(3),
        ["Readings compared", "Outside selected reference", "Comparison unavailable"],
        [coverage["compared"], coverage["outside"], coverage["unavailable"]],
    ):
        col.metric(label, f"{value:,}")
    if coverage["compared"]:
        st.markdown(
            f"**{coverage['outside_pct']:.1f}% of compared readings are outside Class {reference_class}.** Denominator: {coverage['compared']:,} comparable readings, not all {coverage['total']:,} observations."
        )
        st.subheader("Which parameters fall outside the reference?")
        graph(reference_outcomes(flags))
        available = sorted(
            flags.loc[flags.reference_status.ne("not_evaluable"), "parameter_code"].unique()
        )
        parameter = st.selectbox("Inspect compared parameter", available)
        st.caption(
            "Each point is a comparable sample. Dashed lines show the selected inclusive limit/range; units are converted explicitly when needed."
        )
        graph(reference_readings(flags, parameter))
    elif coverage["total"]:
        st.info(
            "No readings in this selection can be compared safely yet. This is a comparison-coverage gap, not evidence of poor water quality."
        )
    else:
        st.info("No observations match the active filters.")
    blocked = blocker_counts(flags)
    if len(blocked):
        st.subheader("Why are some comparisons unavailable?")
        fig = px.bar(
            blocked.sort_values("observations"),
            x="observations",
            y="reason",
            orientation="h",
            text="observations",
            color_discrete_sequence=[SLATE],
            labels={"observations": "Readings with this primary blocker", "reason": ""},
        )
        graph(polish(fig, max(240, 45 * len(blocked) + 65)))
        if blocked.blocker.eq("unit_missing").any():
            st.markdown(
                "**Missing unit:** the 2023 catalog export does not include a unit column. A reading of `10` cannot safely be compared with `10 mg/L` without establishing its scale. The app keeps the reading but makes no assumption."
            )
            if "Official Jakarta 2022" in official_choices and mode != "Official Jakarta 2022":

                def use_2022():
                    st.session_state["data_source"] = "Official Jakarta 2022"

                st.button("Explore 2022 reference comparisons · units supplied", on_click=use_2022)
        if blocked.blocker.eq("rule_not_configured").any():
            st.markdown(
                "**Rule not configured:** the app currently verifies only pH, DO, BOD, COD, TSS and nitrate-as-N. Other parameters may have regulatory entries, but this app has not implemented and verified them; this does not mean they failed a standard."
            )
        if blocked.blocker.eq("chemical_basis_unknown").any():
            st.caption(
                "Nitrate/phosphate names alone do not establish whether results are expressed as N, P, NO₃ or PO₄. Their chemical bases must match the reference."
            )
        if blocked.blocker.eq("ph_context").any():
            st.caption(
                "pH has a natural peat-water exception. Confirm its applicability using the sidebar control only when you know the source context."
            )
    statuses = st.multiselect(
        "Record export statuses",
        ["within_reference", "outside_reference", "not_evaluable"],
        default=["outside_reference", "not_evaluable"],
        format_func=lambda x: {
            "within_reference": "Within reference",
            "outside_reference": "Outside reference",
            "not_evaluable": "Comparison unavailable",
        }[x],
    )
    shown = flags.loc[flags.reference_status.isin(statuses)]
    download(shown, "Download reference outcomes", "aquainsight_reference_flags.csv")
    record_details(shown, "Audit comparison outcomes", "reference")
    with st.expander("Verified rules and interpretation"):
        rules = load_standards()
        st.write(rules["reference"])
        st.link_button("Read source regulation", rules["source_url"])
        st.caption(
            "Class selection establishes no legal designation. DO is a minimum; pH is a range; concentration limits are maxima. Missing/censored readings never create an alert."
        )
        if st.toggle("Show rule table", key="show_rules"):
            table(
                pd.DataFrame([{"parameter": p, **r} for p, r in rules["rules"].items()]).astype(str)
            )

elif page == "Sites & Map":
    mapped = map_sites(filtered)
    counts = site_coverage(filtered)
    for col, label, value in zip(
        st.columns(3),
        ["Sites in selection", "Mapped locations", "Locations withheld"],
        [filtered.site_id.nunique(), len(mapped), max(0, filtered.site_id.nunique() - len(mapped))],
    ):
        col.metric(label, f"{value:,}")
    if mapped.empty:
        st.info(
            "Map omitted: no verified, valid and stable station coordinate pairs. Fictional demo stations have no coordinates."
        )
    else:
        st.subheader("Station atlas")
        st.caption(
            "Geographic layout of source station coordinates. The default has no map tiles or external basemap downloads; pan and zoom to inspect locations. Conflicting/shared coordinate pairs remain withheld."
        )
        map_mode = st.radio(
            "Map context", ["Instant atlas · no tiles", "Street context · online"], horizontal=True
        )
        if map_mode.startswith("Instant"):
            st.plotly_chart(
                station_atlas(mapped, filtered),
                width="stretch",
                config={"displaylogo": False, "scrollZoom": True},
            )
        else:
            fig = px.scatter_map(
                mapped,
                lat="latitude",
                lon="longitude",
                hover_name="site_id",
                hover_data=["river_name", "site_name"],
                zoom=9.7,
                height=540,
                map_style="carto-darkmatter",
                color_discrete_sequence=["#8cd0b3"],
            )
            fig.update_traces(marker_size=10)
            st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
            st.caption(
                "Street context uses CARTO tiles and needs network access. Switch back to Instant atlas if tiles are slow."
            )
        st.caption(
            "Markers show source-supplied coordinates, not geocoded or independently surveyed positions. No river channels or boundaries have been invented."
        )
    if len(filtered):
        site = st.selectbox("Inspect a monitoring site", sorted(filtered.site_id.unique()))
        site_data = filtered.loc[filtered.site_id.eq(site)]
        st.subheader(f"{site} · sample history")
        parameter, focused = focus_parameter(site_data, "site")
        if not period_statistics(focused).empty:
            graph(measurements(focused))
        else:
            st.info("No dated exact readings for this site/parameter.")
        record_details(site_data, "Site records", "site")
    record_details(counts, "Full coverage inventory", "coverage")

elif page == "Data Quality & Sources":
    st.caption(
        "Diagnostics describe the full loaded source. Reading status is separate from regulatory comparison coverage."
    )
    quality = dataset.quality
    categories = {
        "Exact numeric": int(df.qualifier.eq("exact").sum()),
        "Missing": int(df.qualifier.eq("missing").sum()),
        "Censored": int(df.qualifier.eq("censored").sum()),
        "Invalid / ambiguous": int(df.qualifier.isin(["invalid", "ambiguous"]).sum()),
        "Other qualifiers": int(
            (~df.qualifier.isin(["exact", "missing", "censored", "invalid", "ambiguous"])).sum()
        ),
    }
    st.subheader("How usable are the reported readings?")
    fig = go.Figure()
    for label, color in zip(categories, [GREEN, SLATE, "#aeb69a", COPPER, "#869bb5"]):
        if categories[label]:
            fig.add_trace(
                go.Bar(
                    x=[categories[label]],
                    y=["Source readings"],
                    name=label,
                    orientation="h",
                    marker_color=color,
                    text=[f"{label}: {categories[label]:,}"],
                    textposition="auto",
                )
            )
    fig.update_layout(barmode="stack", xaxis_title="Retained observations", yaxis_title="")
    graph(polish(fig, 230))
    for col, label, value in zip(
        st.columns(4),
        ["Input rows", "Retained readings", "Excluded / summary rows", "Missing units"],
        [
            quality["source_rows"],
            len(df),
            len(dataset.rejected),
            int(df.unit_normalized.eq("").sum()),
        ],
    ):
        col.metric(label, f"{value:,}")
    if quality.get("excluded_summary_rows", 0):
        st.caption(
            f"{quality['excluded_summary_rows']:,} publisher IP/status summaries are preserved in excluded diagnostics, not treated as parameter readings."
        )
    if df.sample_month.ne("").any():
        st.caption(
            f"{df.sample_month.ne('').sum():,} observations have month precision. An unavailable exact day is not a date-parsing error."
        )
    st.subheader("Monitoring coverage across rounds")
    graph(coverage_chart(filtered))
    st.subheader("Source & interpretation")
    st.write(dataset.metadata.get("source_name", "User upload"))
    source_url = dataset.metadata.get("source_url", "")
    if source_url.startswith(("https://", "http://")):
        st.link_button("Open source catalog", source_url)
    st.caption(dataset.metadata.get("license", "License not supplied"))
    st.download_button(
        "Download complete quality report",
        quality_json(dataset),
        "aquainsight_quality.json",
        "application/json",
    )
    with st.expander("Technical diagnostics & provenance"):
        st.json(dataset.quality)
        st.json(dataset.metadata)
    record_details(
        df.loc[df.quality_note.ne("") | df.duplicate_candidate],
        "Reading diagnostics",
        "diagnostics",
    )
    record_details(dataset.rejected, "Excluded source rows", "rejected")
    record_details(dataset.original, "Original source rows", "original")
    with st.expander("Official source audit"):
        st.markdown((Path(__file__).resolve().parents[1] / "docs" / "DATA_SOURCES.md").read_text())

elif page == "Upload & Export":
    st.subheader("Import historical observations")
    st.info(
        "Local Jakarta files in data/raw load automatically from the sidebar. You can also preview and load CSV/XLSX here; Jakarta 2022/2023 layouts are recognized."
    )
    uploaded = st.file_uploader("CSV or XLSX", type=["csv", "xlsx"])
    st.download_button(
        "Download labeled synthetic input example",
        csv_bytes(demo_frame()),
        "synthetic_observations.csv",
        "text/csv",
    )
    if uploaded is not None:
        try:
            content = uploaded.getvalue()
            sheet = (
                st.selectbox("Excel sheet", excel_sheets(content))
                if uploaded.name.lower().endswith(".xlsx")
                else 0
            )
            a, b = st.columns(2)
            encoding = a.selectbox("CSV encoding", ["utf-8-sig", "cp1252", "latin-1"])
            delimiter = b.selectbox("CSV delimiter", ["Auto", ",", ";", "\t"])
            raw = read_file(
                content, uploaded.name, sheet, encoding, None if delimiter == "Auto" else delimiter
            )
            st.caption(f"Source preview: {len(raw):,} rows · {len(raw.columns)} columns")
            table(raw.head(20))
            detected_year = identify_official_schema(raw)
            use_jakarta_layout = detected_year is not None and st.checkbox(
                f"Use Jakarta {detected_year} source layout", value=True
            )
            layout = "Jakarta source layout"
            mapping = {}
            if use_jakarta_layout:
                st.caption(
                    "Source months, coordinates, units and excluded summary rows follow the verified Jakarta layout. Custom decimal/date controls below apply only to custom mappings."
                )
            else:
                layout = st.radio(
                    "Source layout", ["Long: one parameter per row", "Wide: parameters in columns"]
                )
                suggestions = suggest_mapping(list(raw.columns))
                mapping = {}
                with st.expander("Column mapping", expanded=True):
                    choices = ["(unmapped)", *raw.columns]
                    fields = list(ALIASES)
                    if layout.startswith("Wide"):
                        fields = [
                            f
                            for f in fields
                            if f
                            not in {
                                "parameter_original_name",
                                "value_raw",
                                "unit_original",
                                "qualifier",
                            }
                        ]
                    for field in fields:
                        default = suggestions.get(
                            field, field if field in raw.columns else "(unmapped)"
                        )
                        choice = st.selectbox(
                            field,
                            choices,
                            index=choices.index(default),
                            key=f"map_{uploaded.name}_{layout}_{field}",
                        )
                        if choice != "(unmapped)":
                            mapping[field] = choice
            wide = None
            if layout.startswith("Wide"):
                cols = st.multiselect(
                    "Measurement columns", [c for c in raw.columns if c not in mapping.values()]
                )
                wide = {}
                for c in cols:
                    a, b = st.columns(2)
                    name = a.text_input(f"Parameter for {c}", c)
                    unit = b.text_input(f"Unit for {c}", key=f"unit_{c}")
                    wide[c] = (name, unit)
                if not wide:
                    st.info("Select at least one measurement column.")
            a, b = st.columns(2)
            decimal = a.selectbox(
                "Decimal convention",
                ["auto", ".", ","],
                help="Auto refuses ambiguous decimal/thousands strings.",
            )
            date_order = b.selectbox("Date order", ["auto", "dayfirst", "monthfirst"])
            source_name = st.text_input("Dataset/source name", uploaded.name)
            source_url = st.text_input("Source URL (optional)")
            license_note = st.text_input("License/usage note", "Not specified by uploader")
            verified_coords = st.checkbox(
                "Coordinates are exact station coordinates verified against this source",
                value=False,
            )
            metadata = {
                "source_name": source_name,
                "source_file": uploaded.name,
                "source_id": uploaded.name,
                "source_url": source_url,
                "license": license_note,
                "access_date": datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat(),
                "data_mode": "USER-UPLOADED",
                "coordinates_verified": verified_coords,
                "sheet": sheet,
                "decimal_convention": decimal,
                "date_order": date_order,
            }
            if not layout.startswith("Wide") or wide:
                preview = (
                    normalize_official(raw, detected_year, metadata)
                    if use_jakarta_layout
                    else normalize(raw, metadata, mapping, wide, decimal, date_order)
                )
                st.subheader("Normalized preview · review before loading")
                table(preview.observations.head(20))
                st.json(preview.quality)
                if preview.observations.empty:
                    st.error(
                        "No identifiable observations. Supply site identity and parameter mappings."
                    )
                elif st.button("Load validated observations", type="primary"):
                    st.session_state.loaded_dataset = preview
                    for key in [
                        "User upload_rivers",
                        "User upload_sites",
                        "User upload_parameters",
                        "User upload_dates",
                        "User upload_months",
                    ]:
                        st.session_state.pop(key, None)
                    st.success("Dataset loaded. Select User upload in the sidebar to explore it.")
        except (
            ValueError,
            KeyError,
            TypeError,
            OSError,
            UnicodeError,
            BadZipFile,
            pd.errors.ParserError,
        ) as exc:
            st.error(f"Cannot normalize this file: {exc}")
    st.divider()
    st.subheader("Export current selection")
    if dataset is not None:
        st.caption(
            f"{len(filtered):,} observations · current sidebar filters · reference Class {reference_class}"
        )
        download(
            filtered, "Download normalized filtered observations", "aquainsight_normalized.csv"
        )
        st.download_button(
            "Download self-contained monitoring report",
            monitoring_report(filtered, flags, export_filters, dataset.metadata, reference_class),
            "aquainsight_monitoring_summary.html",
            "text/html",
        )
        st.download_button(
            "Download full quality report",
            quality_json(dataset),
            "aquainsight_quality.json",
            "application/json",
        )
        st.caption(DISCLAIMER)
