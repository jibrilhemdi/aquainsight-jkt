# Monitoring data

Put the original Jakarta catalog downloads in `raw/`:

- `Filedata Data Kualitas Air Sungai Tahun 2023.csv`
- `Filedata Data Kualitas Air Sungai 2022.csv`

Streamlit loads available official files automatically. `raw/` stays gitignored except `.gitkeep`; these locally supplied files are not redistributed by this repository. You may also load genuine monitoring observations through the CSV/XLSX upload screen. Uploads remain in session memory. There is no generated fallback or bundled observation example.

Record source attribution, download/access date, original units and license when importing. See `docs/DATA_SOURCES.md` for the verified file schemas, counts, month precision, missing 2023 units and coordinate exclusions.
