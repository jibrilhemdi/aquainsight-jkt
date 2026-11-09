from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from aquainsight.comparison import (
    build_comparison,
    common_months,
    common_parameters,
    station_alignment,
)
from aquainsight.ingestion import normalize
from aquainsight.official import available_official_files, load_official
from aquainsight.reports import csv_bytes

APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


def sources():
    result = {}
    for year in [2022, 2023]:
        raw = pd.DataFrame(
            {
                "site_id": ["A", "B", "A", "B"],
                "site_name": ["Test A", "Test B"] * 2,
                "river_name": ["Test river"] * 4,
                "parameter": ["pH"] * 4,
                "value": ["7", "8", "7.2", "8.2"] if year == 2022 else ["7.5", "7.8", "7.4", "8.4"],
                "unit": ["pH"] * 4,
                "sample_month": [f"{year}-08"] * 2
                + [f"{year}-03" if year == 2022 else f"{year}-02"] * 2,
                "latitude": [-6.1, -6.2] * 2,
                "longitude": [106.8, 106.9] * 2,
            }
        )
        result[year] = normalize(
            raw,
            {
                "source_id": f"test-input-{year}",
                "source_name": f"Test {year}",
                "source_file": f"fixture-{year}.csv",
                "source_url": "https://example.org/test-input",
                "coordinates_verified": True,
                "data_mode": "USER-UPLOADED",
            },
        ).observations
    return result


def test_pair_same_calendar_month_and_difference_of_site_values():
    years = sources()
    assert common_months(years) == ["08"] and common_parameters(years) == ["pH"]
    result = build_comparison(years, "pH")
    assert len(result.observations) == 4 and len(result.pairs) == 2
    assert result.unit == "pH" and result.limitation == ""
    assert result.pairs.difference.tolist() == pytest.approx([0.5, -0.2])
    assert result.pairs.difference.median() == pytest.approx(0.15)
    assert result.pairs.n_2022.tolist() == [1, 1]
    assert result.observations.sample_month.str.endswith("08").all()
    assert "percentage" not in " ".join(result.pairs.columns)
    assert "fixture-2022.csv" in csv_bytes(result.pairs).decode("utf-8-sig")
    assert result.pairs.data_mode.eq("USER-UPLOADED").all()
    assert result.location_audit.source_file_2023.eq("fixture-2023.csv").all()
    assert result.location_audit.location_tolerance_m.eq(10).all()


def test_missing_units_prevent_numeric_delta_and_pooling():
    years = sources()
    years[2023]["unit_normalized"] = ""
    result = build_comparison(years, "pH")
    assert result.pairs.empty and not result.unit
    assert "shared measurement unit" in result.limitation
    assert len(result.observations) == 4
    assert result.summary.unit.tolist() == ["pH", "Not supplied"]


def test_full_year_scope_does_not_pair_different_sampling_months():
    result = build_comparison(sources(), "pH", month=None)
    assert len(result.observations) == 8 and result.pairs.empty
    assert "Sampling months differ" in result.limitation


def test_location_checks_precede_month_filter_and_reject_identity_conflicts():
    years = sources()
    years[2023].loc[
        years[2023].sample_month.eq("2023-02") & years[2023].site_id.eq("A"), "latitude"
    ] = -6.3
    years[2023].loc[years[2023].site_id.eq("B"), "river_name"] = "Another river"
    result = build_comparison(years, "pH")
    assert result.observations.empty and result.pairs.empty
    assert not result.location_audit.location_status.eq("Consistent source location").any()
    assert "No observations remain" in result.limitation


def test_unverified_moved_absent_or_invalid_coordinates_not_matched():
    years = sources()
    years[2023].loc[years[2023].site_id.eq("A"), "latitude"] = -6.3
    years[2023].loc[years[2023].site_id.eq("B"), "coordinates_verified"] = False
    audit = station_alignment(years[2022], years[2023])
    assert audit.location_status.str.contains("more than 10 m").sum() == 1
    assert audit.location_status.str.contains("unverified").sum() == 1
    audit = station_alignment(years[2022], years[2023].iloc[:0])
    assert audit.location_status.eq("Site ID absent in one year").all()
    years = sources()
    years[2023]["latitude"] = 95
    assert (
        station_alignment(years[2022], years[2023])
        .location_status.eq("Coordinates outside valid range")
        .all()
    )


def test_qualified_readings_and_empty_filters_never_create_zero_pairs():
    years = sources()
    years[2023].loc[years[2023].site_id.eq("A"), "qualifier"] = "censored"
    result = build_comparison(years, "pH")
    assert len(result.pairs) == 1 and result.pairs.site_id.item() == "B"
    result = build_comparison(years, "pH", sites=[])
    assert result.pairs.empty and result.observations.empty
    assert result.summary["median"].isna().all()
    with pytest.raises(ValueError, match="calendar month"):
        build_comparison(years, "pH", month="03")
    with pytest.raises(ValueError, match="parameter"):
        build_comparison(years, "BOD")


def test_multiple_same_site_readings_reduce_to_one_documented_site_median():
    years = sources()
    duplicate = years[2023].iloc[[0]].copy()
    duplicate["value_numeric"] = 8.5
    years[2023] = pd.concat([years[2023], duplicate], ignore_index=True)
    result = build_comparison(years, "pH")
    assert len(result.pairs) == 2
    a = result.pairs.loc[result.pairs.site_id.eq("A")].iloc[0]
    assert a.n_2023 == 2 and a.value_2023 == 8 and a.difference == 1


def test_local_comparison_view_and_gated_concentrations():
    if not {2022, 2023}.issubset(available_official_files()):
        pytest.skip("Both local official files required")
    app = AppTest.from_file(str(APP)).run(timeout=45)
    app.sidebar.radio[0].set_value("Compare years").run(timeout=45)
    assert not app.exception
    assert [card.value for card in app.metric] == ["112", "112", "112", "112"]
    assert len(app.dataframe) == 0
    assert any("Median site difference" in item.value for item in app.markdown)
    next(select for select in app.selectbox if select.label == "Compare parameter").set_value(
        "BOD"
    ).run(timeout=45)
    assert not app.exception and app.metric[-1].value == "0"
    assert any("shared measurement unit" in message.value for message in app.info)
    assert not any("Median site difference" in item.value for item in app.markdown)
    next(radio for radio in app.radio if radio.label == "Comparison window").set_value(
        "All available rounds"
    ).run(timeout=45)
    assert not app.exception and app.metric[-1].value == "0"
    next(select for select in app.multiselect if select.label == "Comparison sites").set_value(
        []
    ).run(timeout=45)
    assert not app.exception and app.metric[0].value == "0"
    app.sidebar.radio[0].set_value("Overview").run(timeout=45)
    assert not app.exception and app.metric[0].value == "10,911"


def test_comparison_view_without_local_files_is_actionable(monkeypatch):
    from aquainsight import official

    monkeypatch.setattr(official, "available_official_files", lambda: {})
    app = AppTest.from_file(str(APP)).run(timeout=45)
    app.sidebar.radio[0].set_value("Compare years").run(timeout=45)
    assert not app.exception and any("Add both official" in message.value for message in app.info)


def test_actual_local_files_comparison_is_limited_to_safe_shared_scope():
    files = available_official_files()
    if not {2022, 2023}.issubset(files):
        pytest.skip("Both local files required")
    years = {year: load_official(path, year).observations for year, path in files.items()}
    result = build_comparison(years, "pH")
    assert len(result.location_audit) == 120
    assert len(result.pairs) == 112 and len(result.observations) == 224
    assert result.observations.source_year.value_counts().to_dict() == {2022: 112, 2023: 112}
    assert all(result.pairs.unit.eq("pH")) and all(result.pairs.calendar_month.eq("08"))
    blocked = build_comparison(years, "BOD")
    assert blocked.pairs.empty and blocked.unit == ""
