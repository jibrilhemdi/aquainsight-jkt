import pytest

from aquainsight.analytics import filter_observations, map_sites
from aquainsight.demo import load_demo
from aquainsight.insights import (
    blocker_counts,
    comparison_coverage,
    group_statistics,
    period_statistics,
)
from aquainsight.standards import compare
from aquainsight.visualization import (
    measurements,
    reference_outcomes,
    reference_readings,
    site_heatmap,
    station_atlas,
)


def focused():
    return filter_observations(load_demo().observations, parameters=["BOD"])


def test_period_and_river_summary_do_not_mix_parameters_or_units():
    data = focused()
    stats = period_statistics(data)
    assert stats.n.sum() == data.qualifier.eq("exact").sum()
    assert stats.iloc[0]["median"] == 5
    assert stats.iloc[0].q1 <= stats.iloc[0]["median"] <= stats.iloc[0].q3
    groups = group_statistics(data)
    assert groups.n.sum() == data.qualifier.eq("exact").sum()
    with pytest.raises(ValueError, match="one parameter"):
        period_statistics(load_demo().observations)
    data.loc[data.index[0], "unit_normalized"] = "µg/L"
    with pytest.raises(ValueError, match="one unit"):
        group_statistics(data)


def test_coverage_denominator_excludes_unavailable_comparisons():
    data = focused().iloc[:3].copy()
    data["value_numeric"] = [2, 7, float("nan")]
    data["qualifier"] = ["exact", "exact", "missing"]
    result = compare(data, 2)
    summary = comparison_coverage(result)
    assert summary == {
        "total": 3,
        "compared": 2,
        "unavailable": 1,
        "outside": 1,
        "within": 1,
        "outside_pct": 50,
    }
    assert blocker_counts(result).iloc[0].blocker == "reading_unusable"
    data["unit_normalized"] = ""
    result = compare(data, 2)
    assert comparison_coverage(result)["outside_pct"] is None
    assert result.reference_blocker.tolist() == ["unit_missing", "unit_missing", "reading_unusable"]
    assert sum(blocker_counts(result).observations) == 3


def test_blockers_distinguish_missing_units_rule_subset_and_context():
    data = load_demo().observations.iloc[:3].copy()
    data["parameter_code"] = ["unknown", "NO3", "pH"]
    data["parameter_original_name"] = ["unknown", "Nitrat", "pH"]
    data["unit_normalized"] = ["mg/L", "mg/L", "pH"]
    assert compare(data, 1).reference_blocker.tolist() == [
        "rule_not_configured",
        "chemical_basis_unknown",
        "ph_context",
    ]
    empty = compare(data.iloc[:0], 1)
    assert blocker_counts(empty).empty
    assert comparison_coverage(empty)["compared"] == 0


def test_charts_preserve_sample_count_and_show_thresholds():
    data = focused()
    chart = measurements(data)
    assert len(chart.data) <= 2  # no legend trace per station
    assert len(chart.data[0].x) == (data.sample_date.notna() & data.qualifier.eq("exact")).sum()
    heatmap = site_heatmap(data)
    assert heatmap.data[0].type == "heatmap"
    flags = compare(data, 2)
    bar = reference_outcomes(flags)
    assert (
        sum(sum(trace.x) for trace in bar.data) == flags.reference_status.ne("not_evaluable").sum()
    )
    reference = reference_readings(flags, "BOD")
    assert reference.layout.shapes[0].y0 == 3
    assert reference.layout.shapes[0].y1 == 3


def test_atlas_is_one_coordinate_trace_without_remote_assets():
    data = focused().copy()
    data["latitude"] = data.site_id.map({"DEMO-01": -6.1, "DEMO-02": -6.2, "DEMO-03": -6.3})
    data["longitude"] = data.site_id.map({"DEMO-01": 106.7, "DEMO-02": 106.8, "DEMO-03": 106.9})
    data["coordinates_verified"] = True
    sites = map_sites(data)
    fig = station_atlas(sites, data)
    assert len(fig.data) == 1 and fig.data[0].type == "scattergl"
    assert len(fig.data[0].x) == 3
    assert fig.layout.yaxis.scaleanchor == "x"
    payload = fig.to_json()
    assert (
        "https://" not in payload and "mapbox" not in payload and "open-street-map" not in payload
    )


def test_reference_chart_converts_micrograms_before_drawing_limit():
    data = focused().iloc[:1].copy()
    data["unit_normalized"] = "µg/L"
    data["value_numeric"] = 2000
    fig = reference_readings(compare(data, 2), "BOD")
    assert float(fig.data[0].y[0]) == 2
    assert fig.layout.shapes[0].y0 == 3
