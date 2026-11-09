"""Unit-level schema checks and integration checks against local official files."""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from aquainsight.analytics import filter_observations, map_sites, summary
from aquainsight.ingestion import read_file
from aquainsight.official import (
    available_official_files,
    identify_official_schema,
    load_official,
    normalize_official,
)
from aquainsight.reports import csv_bytes, monitoring_report, quality_json
from aquainsight.standards import compare
from aquainsight.visualization import coverage_chart, measurements


def fixture(year):
    # Isolated test inputs using the inspected source headers.
    common = {
        "titik_sampel": ["FIXTURE-1"] * 2,
        "jenis_parameter": ["Kimia"] * 2,
        "parameter": ["BOD", "pH"],
        "baku_mutu": ["3", "6-9"],
        "hasil_pengukuran": ["2,5", "7,1"] if year == 2022 else ["2.5", "7.1"],
        "periode_data": [str(year)] * 2,
        "bulan_sampling": ["202203"] * 2 if year == 2022 else ["2"] * 2,
        "alamat": ["Test site"] * 2,
    }
    if year == 2022:
        common.update(
            tahun=["2022"] * 2,
            periode=["1"] * 2,
            sungai=["Test river"] * 2,
            lintang=["-6,2"] * 2,
            bujur=["106,8"] * 2,
            satuan=["mg L", "-"],
        )
    else:
        common.update(
            periode_pemantauan=["Periode 1 (Musim Hujan)"] * 2,
            nama_sungai=["Test river"] * 2,
            lintang_selatan=["-6.2"] * 2,
            bujur_timur=["106.8"] * 2,
        )
    return pd.DataFrame(common)


@pytest.mark.parametrize("year", [2022, 2023])
def test_verified_schema_months_units_and_provenance(year):
    raw = fixture(year)
    raw.columns = ["\ufeff" + c if c == "titik_sampel" else c for c in raw.columns]
    assert identify_official_schema(raw) == year
    raw = read_file(raw.to_csv(index=False).encode("utf-8-sig"), "fixture.csv")
    result = normalize_official(
        raw, year, {"data_mode": "USER-UPLOADED", "source_file": "schema-input.csv"}
    )
    obs = result.observations
    assert obs.sample_date.isna().all() and obs.sample_id.eq("").all()
    assert obs.sample_month.eq("2022-03" if year == 2022 else "2023-02").all()
    assert obs.value_numeric.tolist() == [2.5, 7.1]
    assert obs.unit_original.tolist() == (["mg L", "-"] if year == 2022 else ["", ""])
    assert obs.unit_normalized.tolist() == (["mg/L", "pH"] if year == 2022 else ["", "pH"])
    assert obs.sample_date_raw.tolist() == raw.bulan_sampling.tolist()
    assert obs.latitude.tolist() == [-6.2] * 2
    assert len(filter_observations(obs, months=[])) == 0
    assert len(filter_observations(obs, include_undated=False)) == 2
    assert summary(obs)["site_months"] == 1 and summary(obs)["dated_site_visits"] == 0
    flags = compare(obs, 2, ph_applicable=True)
    assert flags.reference_status.tolist() == (
        ["within_reference"] * 2 if year == 2022 else ["not_evaluable", "within_reference"]
    )
    assert "exact day unavailable" in measurements(obs.iloc[:1]).layout.xaxis.title.text
    assert "exact day unavailable" in coverage_chart(obs).layout.xaxis.title.text


def test_exclude_summaries_and_keep_source_row_numbers():
    raw = fixture(2022)
    extra = pd.concat([raw.iloc[[0]]] * 3, ignore_index=True)
    extra["jenis_parameter"] = ["nilai IP", "status IP", " "]
    extra["parameter"] = "-"
    result = normalize_official(
        pd.concat([extra, raw], ignore_index=True), 2022, {"data_mode": "USER-UPLOADED"}
    )
    assert len(result.original) == 5 and len(result.rejected) == 3
    assert result.observations.source_row.tolist() == [5, 6]
    assert result.quality["excluded_summary_rows"] == 2
    assert result.quality["missing_parameter_rows"] == 1
    assert result.rejected.reason.str.contains("summary").sum() == 2


def test_invalid_month_rejected_and_coordinate_conflicts_survive_filter():
    raw = fixture(2023)
    raw.loc[0, "bulan_sampling"] = "13"
    with pytest.raises(ValueError, match="Sampling month/year"):
        normalize_official(raw, 2023, {})
    raw = fixture(2023)
    raw.loc[1, "lintang_selatan"] = "-6.3"
    obs = normalize_official(raw, 2023, {"coordinates_verified": True}).observations
    assert not obs.coordinates_verified.any()
    assert map_sites(obs.iloc[:1]).empty


@pytest.mark.parametrize(
    "year,raw_count,retained,parameters,mappable",
    [(2023, 10911, 10911, 23, 114), (2022, 14512, 13560, 30, 118)],
)
def test_local_downloads_end_to_end(year, raw_count, retained, parameters, mappable):
    files = available_official_files()
    if year not in files:
        pytest.skip("User-downloaded official files are intentionally not committed")
    result = load_official(files[year], year)
    obs = result.observations
    assert len(result.original) == raw_count and len(obs) == retained
    assert obs.site_id.nunique() == 120 and obs.parameter_code.nunique() == parameters
    assert len(map_sites(obs)) == mappable
    assert obs.sample_date.isna().all() and obs.sample_date_precision.eq("month").all()
    assert obs.data_mode.eq("OFFICIAL").all()
    assert result.quality["duplicate_candidates"] == 0
    assert result.quality["date_parsing_failures"] == 0
    assert result.metadata["sha256"]
    subset = filter_observations(
        obs,
        sites=["ANK-1"],
        parameters=["BOD"],
        months=[f"{year}-03" if year == 2022 else f"{year}-02"],
    )
    assert len(subset) == 1
    flags = compare(subset, 2)
    assert "OFFICIAL" in csv_bytes(subset).decode("utf-8-sig")
    assert "OFFICIAL" in quality_json(result)
    report = monitoring_report(
        subset, flags, {"months": subset.sample_month.tolist()}, result.metadata, 2
    )
    assert "OFFICIAL historical observations" in report
    assert "USER-UPLOADED historical observations" not in report
    assert f"{year}-" in report
    if year == 2023:
        assert (
            compare(obs.loc[obs.parameter_code.ne("pH")], 2)
            .reference_status.eq("not_evaluable")
            .all()
        )


@pytest.mark.parametrize("year", [2023, 2022])
def test_local_official_views(year):
    if year not in available_official_files():
        pytest.skip("Local official file unavailable")
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")
    ).run(timeout=45)
    app.sidebar.selectbox[0].set_value(f"Official Jakarta {year}").run(timeout=45)
    assert not app.exception
    assert app.metric[0].value == ("10,911" if year == 2023 else "13,560")
    for page in [
        "Explore Measurements",
        "Reference Thresholds & Flags",
        "Sites & Map",
        "Data Quality & Sources",
        "Upload & Export",
    ]:
        app.sidebar.radio[0].set_value(page).run(timeout=45)
        assert not app.exception
        assert any("OFFICIAL" in c.value for c in app.caption)
    # Filtering by month must affect the visible counts, including the empty state.
    app.sidebar.multiselect[-1].set_value([])
    app.sidebar.radio[0].set_value("Overview").run(timeout=45)
    assert not app.exception and app.metric[0].value == "0"


def test_numeric_excel_source_cells():
    raw = fixture(2023)
    raw["periode_data"] = 2023
    raw["bulan_sampling"] = 2
    raw["hasil_pengukuran"] = [2.5, 7.1]
    result = normalize_official(raw, 2023, {"data_mode": "USER-UPLOADED"})
    assert result.observations.sample_month.eq("2023-02").all()
    assert result.observations.value_numeric.tolist() == [2.5, 7.1]


def test_jakarta_upload_uses_verified_layout():
    from io import BytesIO
    from unittest.mock import patch

    class Uploaded(BytesIO):
        name = "jakarta_layout_fixture.csv"

    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")
    ).run(timeout=45)
    app.sidebar.selectbox[0].set_value("User upload")
    app.sidebar.radio[0].set_value("Upload & Export")
    with patch(
        "streamlit.file_uploader",
        return_value=Uploaded(fixture(2023).to_csv(index=False).encode("utf-8-sig")),
    ):
        app.run(timeout=45)
        assert not app.exception
        assert any(
            "Use Jakarta 2023 source layout" == box.label and box.value for box in app.checkbox
        )
        next(
            button for button in app.button if button.label == "Load validated observations"
        ).click().run(timeout=45)
        assert not app.exception
    app.sidebar.selectbox[0].set_value("User upload")
    app.sidebar.radio[0].set_value("Overview").run(timeout=45)
    assert not app.exception and app.metric[0].value == "2"
    assert any("2023-02" in item.value for item in app.markdown)
    assert any("USER-UPLOADED" in item.value for item in app.caption)


@pytest.mark.parametrize("year", [2022, 2023])
def test_adapter_retains_metadata_when_base_normalizer_omits_it(year, monkeypatch):
    from aquainsight import official

    current_normalize = official.normalize

    def base_normalizer_without_source_fields(*args, **kwargs):
        dataset = current_normalize(*args, **kwargs)
        dataset.observations = dataset.observations.drop(
            columns=[
                "sample_month",
                "sample_date_precision",
                "monitoring_period",
                "address",
                "parameter_group",
                "source_reference_raw",
                "unit_basis_note",
                "latitude_raw",
                "longitude_raw",
            ]
        )
        return dataset

    monkeypatch.setattr(official, "normalize", base_normalizer_without_source_fields)
    raw = fixture(year)
    # An excluded source row must not shift pH/BOD metadata onto the wrong reading.
    excluded = raw.iloc[[0]].copy()
    excluded["parameter"] = "-"
    raw = pd.concat([excluded, raw], ignore_index=True)
    result = official.normalize_official(raw, year, {"data_mode": "USER-UPLOADED"})
    obs = result.observations
    assert obs.source_row.tolist() == [3, 4]
    assert obs.sample_month.eq("2022-03" if year == 2022 else "2023-02").all()
    assert (
        "intrinsically dimensionless"
        in obs.loc[obs.parameter_code.eq("pH"), "unit_basis_note"].item()
    )
    assert (
        "intrinsically dimensionless"
        not in obs.loc[obs.parameter_code.eq("BOD"), "unit_basis_note"].item()
    )
    assert obs.quality_note.str.contains(obs.unit_basis_note.iloc[0], regex=False).iloc[0]
