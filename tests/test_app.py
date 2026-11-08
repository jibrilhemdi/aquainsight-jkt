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


def demo_app():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    app.sidebar.selectbox[0].set_value("Synthetic demo").run(timeout=30)
    return app


@pytest.mark.parametrize("page", PAGES)
def test_all_views(page):
    app = demo_app()
    app.sidebar.radio[0].set_value(page).run(timeout=30)
    assert not app.exception
    assert any("SYNTHETIC DEMO" in w.value for w in app.warning)


def test_empty_filters_and_upload_mode():
    app = demo_app()
    app.sidebar.multiselect[1].set_value([]).run()
    assert not app.exception
    assert any("No observations" in i.value for i in app.info)
    app.sidebar.radio[0].set_value("Reference Thresholds & Flags").run()
    assert not app.exception
    app.sidebar.selectbox[0].set_value("User upload").run()
    assert not app.exception
    app.sidebar.radio[0].set_value("Upload & Export").run()
    assert not app.exception


def test_uploaded_preview_load_and_views():
    from io import BytesIO
    from unittest.mock import patch

    class Uploaded(BytesIO):
        name = "observations.csv"

    uploaded = Uploaded(
        b"site_id,sample_date,parameter,value,unit\nUP-01,2023-02-14,BOD,2.5,mg/L\nUP-01,2023-05-18,BOD,4,mg/L\n"
    )
    app = demo_app()
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
        assert not any("SYNTHETIC DEMO" in w.value for w in app.warning)
    app.sidebar.radio[0].set_value("Overview").run()
    assert app.metric[0].value == "2"


def test_invalid_upload_is_actionable():
    from io import BytesIO
    from unittest.mock import patch

    class Uploaded(BytesIO):
        name = "broken.xlsx"

    app = demo_app()
    app.sidebar.radio[0].set_value("Upload & Export")
    with patch("streamlit.file_uploader", return_value=Uploaded(b"not an excel file")):
        app.run()
        assert not app.exception
        assert any("Cannot normalize" in item.value for item in app.error)


def test_sparse_upload_without_dates_units_or_coordinates():
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
    assert any("No verified measurement dates" in item.value for item in app.markdown)


@pytest.mark.parametrize("page", PAGES)
def test_empty_selection_all_views(page):
    app = demo_app()
    app.sidebar.multiselect[1].set_value([])
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception
