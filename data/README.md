# Data handling

`demo/synthetic_observations.csv` is project-authored fictional data, CC0, never actual Jakarta observations. Reproduce with `python scripts/generate_demo.py` after installing the project. It contains 73 observations, including one retained duplicate, two censored values, one missing reading and one ambiguous date. No station coordinates.

`raw/` is ignored except its placeholder. Local user-downloaded official files load automatically with their original names: `Filedata Data Kualitas Air Sungai Tahun 2023.csv` and `Filedata Data Kualitas Air Sungai 2022.csv`. These files are not committed or redistributed. Uploaded files remain in session memory. Record publisher URL, access date and license when importing. Generic aliases and a user-facing mapper support CSV/XLSX, and both actual Jakarta layouts have dedicated verified adapters. See docs/DATA_SOURCES.md for counts, month precision, missing 2023 units and coordinate exclusions.
