"""Deterministic fictional fixture; deliberately no station coordinates."""

import pandas as pd

from aquainsight import DEMO_WARNING
from aquainsight.ingestion import normalize


def demo_frame() -> pd.DataFrame:
    rows = []
    for s in range(3):
        for m, day in enumerate(["2023-02-14", "2023-05-18", "2023-09-21", "2023-12-12"]):
            for p, unit, value in [
                ("pH", "pH", 6.2 + s * 0.7 + m * 0.3),
                ("DO", "mg/L", 2 + s + m * 0.5),
                ("BOD", "mg/L", 2 + s * 3 + m),
                ("COD", "mg/L", 14 + s * 12 + m * 4),
                ("TSS", "mg/L", 30 + s * 20 + m * 7),
                ("NO3-N", "mg/L", 1 + s + m * 0.2),
            ]:
                rows.append(
                    {
                        "site_id": f"DEMO-{s + 1:02}",
                        "site_name": f"Fictional monitoring site {s + 1}",
                        "river_name": f"Fictional river {'A' if s < 2 else 'B'}",
                        "sample_date": day,
                        "sample_id": f"DEMO-{s + 1}-{m + 1}",
                        "parameter": p,
                        "value": f"{value:.2f}",
                        "unit": unit,
                        "data_mode": "SYNTHETIC DEMO",
                        "data_notice": DEMO_WARNING,
                    }
                )
    frame = pd.DataFrame(rows)
    frame.loc[5, "value"] = "<0.01"
    frame.loc[20, "value"] = "ND"
    frame.loc[36, "value"] = ""
    frame.loc[45, "sample_date"] = "03/04/2023"
    return pd.concat([frame, frame.iloc[[0]]], ignore_index=True)


def load_demo():
    return normalize(
        demo_frame(),
        {
            "source_id": "synthetic-v1",
            "source_name": "Deterministic fictional engineering fixture",
            "source_file": "synthetic_observations.csv",
            "source_url": "",
            "data_mode": "SYNTHETIC DEMO",
            "license": "Project-authored synthetic fixture; CC0",
            "access_date": "2026-11-08",
            "coordinates_verified": False,
        },
        decimal=".",
    )
