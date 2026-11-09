from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
PAGES = [
    "Overview",
    "Explore Measurements",
    "Reference Thresholds & Flags",
    "Sites & Map",
    "Data Quality & Sources",
    "Upload & Export",
]


def uploaded_app(dataset):
    app = AppTest.from_file(str(APP))
    app.session_state["loaded_dataset"] = dataset
    app.session_state["data_source"] = "User upload"
    return app.run(timeout=30)


@pytest.mark.parametrize("page", PAGES)
def test_all_views(page, observation_dataset):
    app = uploaded_app(observation_dataset)
    app.sidebar.radio[0].set_value(page).run(timeout=30)
    assert not app.exception
    assert any("USER-UPLOADED" in c.value for c in app.caption)


def test_empty_filters_and_upload_mode(observation_dataset):
    app = uploaded_app(observation_dataset)
    app.sidebar.multiselect[1].set_value([]).run()
    assert not app.exception
    assert any("No observations" in i.value for i in app.info)
    app.sidebar.radio[0].set_value("Reference Thresholds & Flags").run()
    assert not app.exception
    app.sidebar.selectbox[0].set_value("User upload").run()
    assert not app.exception
    app.sidebar.radio[0].set_value("Upload & Export").run()
    assert not app.exception


def test_uploaded_preview_load_and_views(observation_dataset):
    from io import BytesIO
    from unittest.mock import patch

    class Uploaded(BytesIO):
        name = "observations.csv"

    uploaded = Uploaded(
        b"site_id,sample_date,parameter,value,unit\nUP-01,2023-02-14,BOD,2.5,mg/L\nUP-01,2023-05-18,BOD,4,mg/L\n"
    )
    app = uploaded_app(observation_dataset)
    app.sidebar.radio[0].set_value("Upload & Export")
    with patch("streamlit.file_uploader", return_value=uploaded):
        app.run()
        assert not app.exception
        assert any("Normalized preview" in item.value for item in app.subheader)
        load = next(
            button for button in app.button if button.label == "Load validated observations"
        )
        load.click().run()
        assert not app.exception
    app.sidebar.selectbox[0].set_value("User upload")
    for page in PAGES:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception
        assert any("USER-UPLOADED" in c.value for c in app.caption)
    app.sidebar.radio[0].set_value("Overview").run()
    assert app.metric[0].value == "2"


def test_invalid_upload_is_actionable(observation_dataset):
    from io import BytesIO
    from unittest.mock import patch

    class Uploaded(BytesIO):
        name = "broken.xlsx"

    app = uploaded_app(observation_dataset)
    app.sidebar.radio[0].set_value("Upload & Export")
    with patch("streamlit.file_uploader", return_value=Uploaded(b"not an excel file")):
        app.run()
        assert not app.exception
        assert any("Cannot normalize" in item.value for item in app.error)


def test_sparse_upload_without_dates_units_or_coordinates(observation_dataset):
    import pandas as pd

    from aquainsight.ingestion import normalize

    dataset = normalize(
        pd.DataFrame({"site_id": ["only-site"], "parameter": ["unknown"], "value": ["ND"]}),
        {"source_name": "Sparse fixture", "data_mode": "USER-UPLOADED"},
    )
    app = AppTest.from_file(str(APP))
    app.session_state["loaded_dataset"] = dataset
    app.run(timeout=30)
    app.sidebar.selectbox[0].set_value("User upload")
    for page in PAGES:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception
    app.sidebar.radio[0].set_value("Overview").run()
    assert app.metric[0].value == "1"
    assert any("No verified measurement dates" in item.value for item in app.caption)


@pytest.mark.parametrize("page", PAGES)
def test_empty_selection_all_views(page, observation_dataset):
    app = uploaded_app(observation_dataset)
    app.sidebar.multiselect[1].set_value([])
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception


@pytest.mark.parametrize("page", PAGES[:-1])
def test_graph_views_defer_raw_tables(page, observation_dataset):
    app = uploaded_app(observation_dataset)
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception
    assert len(app.dataframe) == 0
    if page == "Overview":
        next(toggle for toggle in app.toggle if toggle.key == "records_overview").set_value(
            True
        ).run()
        assert not app.exception and len(app.dataframe) == 1


def test_exploration_views_and_parameter_switches(observation_dataset):
    app = uploaded_app(observation_dataset)
    app.sidebar.radio[0].set_value("Explore Measurements").run()
    for view in ["Between rivers", "Across sites", "Across rounds"]:
        next(radio for radio in app.radio if radio.label == "View").set_value(view).run()
        assert not app.exception and len(app.get("plotly_chart")) >= 1
    next(select for select in app.selectbox if select.label == "Parameter to explore").set_value(
        "pH"
    ).run()
    assert not app.exception
    assert len(app.dataframe) == 0


def test_reference_gaps_are_explanations_not_violations(observation_dataset):
    app = uploaded_app(observation_dataset)
    app.sidebar.radio[0].set_value("Reference Thresholds & Flags").run()
    assert not app.exception
    assert any("Denominator:" in text.value for text in app.markdown)
    assert any("pH has a natural peat-water exception" in text.value for text in app.caption)
    assert app.metric[2].label == "Comparison unavailable"


@pytest.mark.parametrize("page", PAGES)
def test_no_data_requires_loading_real_observations(page, monkeypatch):
    from aquainsight import official

    monkeypatch.setattr(official, "available_official_files", lambda: {})
    app = AppTest.from_file(str(APP)).run(timeout=30)
    app.sidebar.radio[0].set_value(page).run(timeout=30)
    assert not app.exception
    assert app.sidebar.selectbox[0].options == ["User upload"]
    assert any("No dataset loaded" in message.value for message in app.info)
    assert len(app.metric) == 0
    if page == "Upload & Export":
        assert len(app.get("file_uploader")) == 1


def test_unsupported_previous_session_source_is_cleared(observation_dataset, monkeypatch):
    from aquainsight import official

    monkeypatch.setattr(official, "available_official_files", lambda: {})
    observation_dataset.metadata["data_mode"] = "ARCHIVED"
    observation_dataset.observations["data_mode"] = "ARCHIVED"
    app = AppTest.from_file(str(APP))
    app.session_state["loaded_dataset"] = observation_dataset
    app.session_state["data_source"] = "Unavailable source"
    app.run(timeout=30)
    assert not app.exception
    assert app.sidebar.selectbox[0].value == "User upload"
    assert app.session_state["loaded_dataset"] is None
    assert len(app.metric) == 0
