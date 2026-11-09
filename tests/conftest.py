"""Small isolated inputs for edge-case tests; never loaded by the application."""

import pandas as pd
import pytest

from aquainsight.ingestion import normalize


@pytest.fixture
def observation_dataset():
    rows = []
    for site, values in [("S1", ["2", "3", "<1"]), ("S2", ["5", "6", "7"])]:
        for date, value in zip(["2023-01-15", "2023-02-15", "2023-03-15"], values):
            rows.append(
                {
                    "site_id": site,
                    "site_name": f"Test site {site}",
                    "river_name": "Test river A" if site == "S1" else "Test river B",
                    "sample_id": f"{site}-{date}",
                    "sample_date": date,
                    "parameter": "BOD",
                    "value": value,
                    "unit": "mg/L",
                }
            )
    rows.extend(
        [
            {
                "site_id": "S1",
                "site_name": "Test site S1",
                "river_name": "Test river A",
                "sample_id": "S1-2023-01-15",
                "sample_date": "2023-01-15",
                "parameter": "pH",
                "value": "7",
                "unit": "pH",
            },
            {
                "site_id": "S2",
                "site_name": "Test site S2",
                "river_name": "Test river B",
                "sample_id": "S2-2023-01-15",
                "sample_date": "2023-01-15",
                "parameter": "pH",
                "value": "7.2",
                "unit": "pH",
            },
            {
                "site_id": "S1",
                "site_name": "Test site S1",
                "river_name": "Test river A",
                "sample_id": "S1-unresolved",
                "sample_date": "03/04/2023",
                "parameter": "TSS",
                "value": "12.5",
                "unit": "mg/L",
            },
            {
                "site_id": "S1",
                "site_name": "Test site S1",
                "river_name": "Test river A",
                "sample_id": "S1-2023-02-15",
                "sample_date": "2023-02-15",
                "parameter": "DO",
                "value": "",
                "unit": "mg/L",
            },
        ]
    )
    return normalize(
        pd.DataFrame(rows),
        {
            "source_id": "unit-input",
            "source_name": "Unit-test input",
            "source_file": "unit-input.csv",
            "source_url": "https://example.org/test-input",
            "data_mode": "USER-UPLOADED",
        },
        decimal=".",
    )
