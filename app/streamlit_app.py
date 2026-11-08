"""Run with: streamlit run app/streamlit_app.py."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from zipfile import BadZipFile

import pandas as pd
import plotly.express as px
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
from aquainsight.visualization import coverage_chart, measurements, parameter_coverage

st.set_page_config(page_title="AquaInsight Jakarta", page_icon="💧", layout="wide")
st.markdown(
    """<style>
.stApp {background:#f5f8fa} h1,h2,h3 {color:#123f4a}
[data-testid="stSidebar"] {background:#eaf2f4}
[data-testid="stMetric"] {background:white;border:1px solid #dbe7eb;border-radius:12px;padding:16px}
.block-container {padding-top:2rem} .eyebrow {color:#087f8c;letter-spacing:2px;font-size:12px;font-weight:700}
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


st.sidebar.title("💧 AquaInsight")
st.sidebar.caption("JAKARTA · HISTORICAL WATER DATA")
official_files = available_official_files()
official_choices = {f"Official Jakarta {year}": path for year, path in official_files.items()}
mode = st.sidebar.selectbox("Data source", [*official_choices, "Synthetic demo", "User upload"])
if "loaded_dataset" not in st.session_state:
    st.session_state.loaded_dataset = None
pages = [
    "Overview",
    "Explore Measurements",
    "Reference Thresholds & Flags",
    "Sites & Map",
    "Data Quality & Sources",
    "Upload & Export",
]
page = st.sidebar.radio("Workspace", pages)
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
st.title(page if page != "Overview" else "River water quality, in perspective.")
st.caption(
    "Explore historical samples, monitoring coverage and transparent reference comparisons. Independent portfolio project."
)
is_demo = dataset is not None and (
    dataset.metadata.get("data_mode") == "SYNTHETIC DEMO" or df.data_mode.eq("SYNTHETIC DEMO").any()
)
if is_demo:
    st.warning(DEMO_WARNING)
elif dataset is not None:
    st.info(
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
            "Sampling months only; exact days were not supplied. Years are explored separately because cross-year comparability is unverified."
        )
    if mode == "Official Jakarta 2023":
        st.warning(
            "The 2023 file omits units. Concentration reference comparisons are unavailable; pH is dimensionless. Values retain their original scale."
        )

st.sidebar.divider()
st.sidebar.subheader("Observation filters")
filters = {}
for label, col, key in [
    ("River", "river_name", "rivers"),
    ("Site", "site_id", "sites"),
    ("Parameter", "parameter_code", "parameters"),
]:
    options = sorted(df[col].unique())
    filters[key] = st.sidebar.multiselect(
        label,
        options,
        default=options,
        key=f"{mode}_{key}",
        format_func=lambda value: value or "(Not supplied)",
    )
valid_dates = df.sample_date.dropna()
dates = None
if len(valid_dates):
    selected_dates = st.sidebar.date_input(
        "Measurement date range",
        value=(valid_dates.min().date(), valid_dates.max().date()),
        min_value=valid_dates.min().date(),
        max_value=valid_dates.max().date(),
        key=f"{mode}_dates",
    )
    if len(selected_dates) == 2:
        dates = tuple(selected_dates)
    else:
        st.sidebar.info("Select both date endpoints to apply a date filter.")
include_undated = st.sidebar.checkbox("Include undated observations", value=True)
month_options = sorted(set(df.sample_month) - {""})
months = (
    st.sidebar.multiselect(
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
flags = compare(filtered, reference_class, ph_applicable)
export_filters = {**filters, "ph_applicability_confirmed": ph_applicable}
st.sidebar.caption(
    "Discrete historical samples. No real-time alerts or official compliance findings."
)


def table(data: pd.DataFrame):
    st.dataframe(data, hide_index=True, width="stretch")


def download(data: pd.DataFrame, label: str, name: str):
    st.download_button(label, csv_bytes(data), name, "text/csv")


if page == "Overview":
    info = summary(filtered)
    cards = st.columns(4)
    for card, label, value in zip(
        cards,
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
        period = f"{info['first_month']} – {info['latest_month']} (sampling months; exact days unavailable)"
    st.subheader("Monitoring coverage")
    st.write(f"Measurement period: **{period}**")
    st.caption(
        "Latest sampling month is the end of this period; no exact sampling day is supplied. Counts reflect active filters."
        if month_options
        else "Latest measurement date is the end of this period; this is not the retrieval date. Counts reflect active filters."
    )
    if filtered.empty:
        st.info("No observations match these filters. Select additional options in the sidebar.")
    else:
        a, b = st.columns([1.5, 1])
        with a:
            if filtered.sample_date.notna().any() or filtered.sample_month.ne("").any():
                st.plotly_chart(coverage_chart(filtered), width="stretch")
            else:
                st.info("Time chart unavailable: no verified dates.")
        with b:
            st.plotly_chart(parameter_coverage(filtered), width="stretch")
        st.caption(
            f"{filtered.value_numeric.notna().sum()} numeric readings · {int((filtered.sample_date.isna() & filtered.sample_month.eq('')).sum())} observations with no date or month · {filtered.sample_month.ne('').sum()} month-only observations · {filtered.duplicate_candidate.sum()} duplicate candidates retained. Coverage describes supplied data, not an expected sampling schedule."
        )
        st.subheader("Latest available historical observations")
        table(
            filtered.sort_values(
                "sample_month" if month_options else "sample_date",
                ascending=False,
                na_position="last",
            ).head(12)
        )

elif page == "Explore Measurements":
    if filtered.empty:
        st.info("No matching observations. Adjust sidebar filters.")
    else:
        a, b = st.columns(2)
        parameter = a.selectbox("Chart parameter", sorted(filtered.parameter_code.unique()))
        subset = filtered.loc[filtered.parameter_code.eq(parameter)]
        unit = b.selectbox(
            "Chart unit",
            sorted(subset.unit_normalized.unique()),
            format_func=lambda value: value or "Not supplied by source",
        )
        subset = subset.loc[subset.unit_normalized.eq(unit)]
        if (
            subset.sample_date.notna().any() or subset.sample_month.ne("").any()
        ) and subset.value_numeric.notna().any():
            st.plotly_chart(measurements(subset), width="stretch")
            st.caption(
                "Individual exact readings only; no interpolation. Month labels preserve source precision without an invented sampling day. Censored, invalid and untimed observations remain in the table."
            )
        else:
            st.info("No dated exact numeric readings available for this chart.")
        counts = subset.loc[subset.qualifier.eq("exact")].groupby("site_id").size()
        sufficient = counts[counts >= 3].index
        if len(sufficient):
            eligible = subset.loc[subset.site_id.isin(sufficient) & subset.qualifier.eq("exact")]
            st.plotly_chart(
                px.box(
                    eligible,
                    x="site_id",
                    y="value_numeric",
                    points="all",
                    labels={"value_numeric": f"{parameter} ({unit or 'unit not supplied'})"},
                    title="Site distribution · at least 3 exact readings per site",
                ),
                width="stretch",
            )
            table(counts.rename("exact_reading_count").reset_index())
    query = st.text_input(
        "Search observation table",
        help="Literal search across displayed record fields; export reflects this search.",
    )
    searched = (
        filtered.loc[
            filtered.astype(str)
            .apply(lambda col: col.str.contains(query, case=False, regex=False))
            .any(axis=1)
        ]
        if query
        else filtered
    )
    table(searched)
    download(searched, "Download filtered CSV", "aquainsight_filtered.csv")

elif page == "Reference Thresholds & Flags":
    st.warning(DISCLAIMER)
    st.caption(
        "No legal class designation is inferred. Missing, censored, ambiguous and incompatible readings are not evaluable. pH comparisons require confirmation of the natural peat-water exception."
    )
    counts = flags.reference_status.value_counts()
    for col, status in zip(
        st.columns(3), ["within_reference", "outside_reference", "not_evaluable"]
    ):
        col.metric(status.replace("_", " ").title(), int(counts.get(status, 0)))
    statuses = st.multiselect(
        "Reference status",
        ["within_reference", "outside_reference", "not_evaluable"],
        default=["outside_reference", "not_evaluable"],
    )
    shown = flags.loc[flags.reference_status.isin(statuses)]
    table(shown)
    download(shown, "Download selected reference outcomes", "aquainsight_reference_flags.csv")
    with st.expander("Verified river-water rules and source"):
        rules = load_standards()
        st.write(rules["reference"])
        st.link_button("Read source regulation", rules["source_url"])
        table(pd.DataFrame([{"parameter": p, **r} for p, r in rules["rules"].items()]).astype(str))

elif page == "Sites & Map":
    st.caption(
        "Completeness is the percentage of supplied records with an exact reading or verified date. No expected sampling schedule is assumed."
    )
    table(site_coverage(filtered))
    mapped = map_sites(filtered)
    if mapped.empty:
        st.info(
            "Map omitted: no verified, valid and stable station coordinate pairs. Fictional demo stations have no coordinates."
        )
    else:
        fig = px.scatter_map(
            mapped,
            lat="latitude",
            lon="longitude",
            hover_name="site_id",
            hover_data=["site_name", "river_name", "source_name"],
            zoom=9,
            height=480,
            map_style="open-street-map",
        )
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "Source-supplied station coordinates with valid, consistent pairs are shown. Conflicting or shared source coordinates are omitted for official files. Source locations have not been independently surveyed. Background tiles need network access."
        )
    if len(filtered):
        site = st.selectbox("Inspect site", sorted(filtered.site_id.unique()))
        table(filtered.loc[filtered.site_id.eq(site)])

elif page == "Data Quality & Sources":
    st.subheader("Full source diagnostics")
    st.caption(
        "Diagnostics refer to the complete loaded source; coverage below follows active filters."
    )
    st.json(dataset.quality)
    st.subheader("Provenance & access")
    st.json(dataset.metadata)
    st.caption(
        "Raw source rows and rejected diagnostics remain separate from normalized observations. Date problems do not remove observations from non-time views."
    )
    st.download_button(
        "Download quality report (JSON)",
        quality_json(dataset),
        "aquainsight_quality.json",
        "application/json",
    )
    with st.expander("Rows with diagnostics"):
        table(df.loc[df.quality_note.ne("") | df.duplicate_candidate])
    with st.expander("Rejected observations"):
        table(dataset.rejected)
        if not dataset.rejected.empty:
            download(dataset.rejected, "Download rejected diagnostics", "aquainsight_rejected.csv")
    with st.expander("Original source rows"):
        table(dataset.original)
    table(site_coverage(filtered))
    st.caption(
        "Largest observed gap is between dated site visits, not a claim that a scheduled sample was missed."
    )
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
