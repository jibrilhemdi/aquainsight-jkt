from io import BytesIO

import pandas as pd
import pytest

from aquainsight.analytics import filter_observations, map_sites, site_coverage, summary
from aquainsight.cleaning import parse_date, parse_number
from aquainsight.ingestion import excel_sheets, normalize, read_file
from aquainsight.reports import csv_bytes, monitoring_report, quality_json
from aquainsight.standards import compare, load_standards

META = {
    "source_name": "Fixture",
    "source_file": "test.csv",
    "source_url": "https://example.org/source",
    "data_mode": "USER-UPLOADED",
}


def data(parameter="BOD", value="3", unit="mg/L"):
    return normalize(
        pd.DataFrame(
            [
                {
                    "site_id": "s1",
                    "sample_date": "2023-02-14",
                    "parameter": parameter,
                    "value": value,
                    "unit": unit,
                }
            ]
        ),
        META,
        decimal=".",
    )


def test_csv_xlsx_and_wide(tmp_path):
    frame = pd.DataFrame(
        {"lokasi": ["Station"], "tanggal": ["2023-02-14"], "BOD": ["2,5"], "pH": ["7.2"]}
    )
    content = frame.to_csv(index=False, sep=";").encode("utf-8-sig")
    raw = read_file(content, "fixture.csv")
    out = normalize(raw, META, wide={"BOD": ("BOD", "mg/L"), "pH": ("pH", "pH")})
    assert out.observations.value_numeric.tolist() == [2.5, 7.2]
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="Monitoring", index=False)
    assert excel_sheets(buf.getvalue()) == ["Monitoring"]
    assert len(read_file(buf.getvalue(), "fixture.xlsx", "Monitoring")) == 1
    assert (
        read_file(
            "lokasi;parameter;nilai\nCafé;BOD;2".encode("cp1252"), "f.csv", encoding="cp1252"
        ).iloc[0, 0]
        == "Café"
    )


@pytest.mark.parametrize("raw,expected", [("2,5", 2.5), ("2.5", 2.5), ("0", 0), ("-2", -2)])
def test_numeric(raw, expected):
    assert parse_number(raw)[0] == expected


def test_ambiguities_censoring_dates():
    assert parse_number("1,234")[1] == "ambiguous"
    assert parse_number("1.234,56")[1] == "ambiguous"
    assert parse_number("1.234,56", ",")[0] == 1234.56
    assert parse_number("1,234.56", ".")[0] == 1234.56
    assert parse_number("12,34.56", ".")[1] == "invalid"
    for raw in ["<0.01", "≤0.01", "ND", ">2", "BDL"]:
        assert parse_number(raw)[:2] == (None, "censored")
    assert pd.isna(parse_date("03/04/2023")[0])
    assert str(parse_date("03/04/2023", "dayfirst")[0].date()) == "2023-04-03"
    assert str(parse_date("14/02/2023")[0].date()) == "2023-02-14"
    assert pd.isna(parse_date("2023-02-31")[0])


def test_preservation_rejection_duplicates_coordinates():
    frame = pd.DataFrame(
        [
            {
                "site_id": "s",
                "parameter": "BOD",
                "value": "<0.01",
                "latitude": "99",
                "longitude": "106",
            }
        ]
        * 2
        + [{"site_id": "", "parameter": "BOD", "value": "4"}]
    )
    out = normalize(frame, META)
    assert len(out.original) == 3 and len(out.rejected) == 1
    assert out.observations.value_raw.tolist() == ["<0.01"] * 2
    assert out.observations.source_url.eq(META["source_url"]).all()
    assert out.quality["duplicate_candidates"] == 2
    assert out.quality["missing_site_names"] == 2
    assert out.observations.latitude.isna().all()
    assert map_sites(out.observations).empty
    assert out.quality["invalid_coordinates"] == 2


@pytest.mark.parametrize("klass", [1, 2, 3, 4])
@pytest.mark.parametrize("parameter", ["pH", "DO", "BOD", "COD", "TSS", "NO3-N"])
def test_threshold_boundaries(klass, parameter):
    rule = load_standards()["rules"][parameter]
    limit = rule["limits"][klass - 1]
    if rule["kind"] == "range":
        cases = [
            (limit[0] - 0.1, "outside_reference"),
            (limit[0], "within_reference"),
            (7, "within_reference"),
            (limit[1], "within_reference"),
            (limit[1] + 0.1, "outside_reference"),
        ]
    elif rule["kind"] == "minimum":
        cases = [
            (limit - 0.1, "outside_reference"),
            (limit, "within_reference"),
            (limit + 0.1, "within_reference"),
        ]
    else:
        cases = [
            (limit - 0.1, "within_reference"),
            (limit, "within_reference"),
            (limit + 0.1, "outside_reference"),
        ]
    for value, expected in cases:
        out = compare(
            data(parameter, str(value), rule["unit"]).observations, klass, ph_applicable=True
        )
        assert out.iloc[0].reference_status == expected


@pytest.mark.parametrize(
    "parameter,value,unit",
    [
        ("NO3", "11", "mg/L"),
        ("BOD", "ND", "mg/L"),
        ("BOD", "", "mg/L"),
        ("BOD", "2", "mg/L as N"),
        ("BOD", "-1", "mg/L"),
        ("BOD", "2", ""),
        ("unknown", "1", "mg/L"),
    ],
)
def test_not_evaluable(parameter, value, unit):
    assert (
        compare(data(parameter, value, unit).observations, 1).reference_status.iloc[0]
        == "not_evaluable"
    )


def test_ph_applicability_and_conversion():
    assert (
        compare(data("pH", "7", "pH").observations, 1).reference_status.iloc[0] == "not_evaluable"
    )
    assert (
        compare(data("BOD", "2000", "ug/l").observations, 1).reference_status.iloc[0]
        == "within_reference"
    )


def test_filters_counts_and_empty(observation_dataset):
    out = observation_dataset
    stats = summary(out.observations)
    assert stats["observations"] == 10 and stats["sites"] == 2 and stats["parameters"] == 4
    assert stats["dated_site_visits"] == 6 and stats["identified_samples"] == 7
    selected = filter_observations(
        out.observations,
        sites=["S1"],
        parameters=["BOD"],
        dates=("2023-01-01", "2023-02-28"),
        include_undated=False,
    )
    assert len(selected) == 2 and len(site_coverage(selected)) == 1
    empty = filter_observations(out.observations, sites=[])
    assert summary(empty)["observations"] == 0 and compare(empty, 1).empty


def test_exports_provenance_and_escaped_html(observation_dataset):
    dataset = observation_dataset
    df = filter_observations(dataset.observations, sites=["S1"])
    flags = compare(df, 3)
    html = monitoring_report(
        df,
        flags,
        {"sites": ["S1"]},
        {**dataset.metadata, "source_name": "<script>evil</script>"},
        3,
    )
    assert "Class 3" in html and "S2" not in html
    assert "<script>evil</script>" not in html and "&lt;script&gt;" in html
    assert dataset.metadata["source_url"] in html
    assert "USER-UPLOADED" in quality_json(dataset)
    assert len(pd.read_csv(BytesIO(csv_bytes(df)))) == len(df)
    source = data().observations
    source.loc[0, "site_name"] = '=HYPERLINK("bad")'
    assert "'=HYPERLINK" in csv_bytes(source).decode("utf-8-sig")
    assert source.site_name.iloc[0].startswith("=")


def test_invalid_schema_and_empty_frame():
    with pytest.raises(ValueError, match="Missing mappings"):
        normalize(pd.DataFrame({"x": [1]}), META)
    out = normalize(pd.DataFrame(columns=["site_id", "parameter", "value"]), META)
    assert out.observations.empty and out.quality["source_rows"] == 0


def test_stable_verified_coordinates_only():
    frame = pd.DataFrame(
        {
            "site_id": ["a", "a", "b"],
            "parameter": ["BOD"] * 3,
            "value": ["2"] * 3,
            "latitude": [-6.1, -6.2, -6.3],
            "longitude": [106.8] * 3,
        }
    )
    obs = normalize(frame, {**META, "coordinates_verified": True}).observations
    assert map_sites(obs).site_id.tolist() == ["b"]


def test_canonical_roundtrip_provenance_and_empty_exports(observation_dataset):
    dataset = observation_dataset
    imported = normalize(
        read_file(csv_bytes(dataset.observations), "roundtrip.csv"),
        {**META, "source_file": "roundtrip.csv"},
        decimal=".",
    )
    assert imported.observations.source_name.eq(dataset.metadata["source_name"]).all()
    assert imported.observations.source_file.eq("unit-input.csv").all()
    assert imported.observations.import_file.eq("roundtrip.csv").all()
    assert imported.observations.qualifier.eq("censored").sum() == 1
    assert imported.observations.sample_id.nunique() == 7
    empty = filter_observations(dataset.observations, sites=[])
    assert pd.read_csv(BytesIO(csv_bytes(empty))).empty
    flags = compare(empty, 1)
    assert pd.read_csv(BytesIO(csv_bytes(flags))).empty
    assert "USER-UPLOADED" in monitoring_report(empty, flags, {"sites": []}, META, 1)


def test_reimport_preserves_ambiguous_original_date(observation_dataset):
    original = observation_dataset
    imported = normalize(
        read_file(csv_bytes(original.observations), "again.csv"), META, decimal="."
    )
    assert (
        imported.observations.sample_date_raw.tolist()
        == original.observations.sample_date_raw.tolist()
    )
    assert imported.observations.sample_date.isna().sum() == 1
    assert (
        imported.observations.source_row.astype(str).tolist()
        == original.observations.source_row.astype(str).tolist()
    )


@pytest.mark.parametrize("mode", ["GENERATED", "UNKNOWN"])
def test_unsupported_source_mode_is_rejected(mode):
    frame = pd.DataFrame({"site_id": ["s"], "parameter": ["BOD"], "value": ["2"]})
    with pytest.raises(ValueError, match="Unsupported data mode"):
        normalize(frame, {**META, "data_mode": mode})
    frame["data_mode"] = mode
    with pytest.raises(ValueError, match="Unsupported data mode in file"):
        normalize(frame, META)
