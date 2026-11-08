"""Write the deterministic, visibly synthetic example input."""

from pathlib import Path

from aquainsight.demo import demo_frame
from aquainsight.reports import csv_bytes

path = Path(__file__).resolve().parents[1] / "data" / "demo" / "synthetic_observations.csv"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_bytes(csv_bytes(demo_frame()))
print(f"Wrote {path}")
