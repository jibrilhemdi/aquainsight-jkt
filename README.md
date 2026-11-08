# AquaInsight Jakarta

An interactive Streamlit platform for **historical** river water-quality observations: explore samples, understand coverage, inspect data quality and compare safely against selected reference thresholds.

**Default data: OFFICIAL Jakarta 2023**, when its downloaded CSV is present in `data/raw`. The sidebar also offers the official 2022 file, synthetic demo and user uploads. This is an independent portfolio project with no government or DHI endorsement. No live sensor monitoring or official compliance findings.

## Run locally

Python 3.11+ recommended in a virtual environment. From this project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
streamlit run app/streamlit_app.py
```

Open http://localhost:8501. Official CSVs load directly from `data/raw` without runtime network requests; the demo is available when files are absent. Stop with Ctrl+C. Dependencies and build configuration are in `pyproject.toml`; `requirements-lock.txt` records the exact locally tested environment. Editable installation is required for the `src/` package and repository-relative configuration.

## Working views

- **Overview:** one-parameter sampling-round distributions, medians/IQRs, explicit sample counts and river comparisons. Coverage and records are optional details.
- **Explore Measurements:** individual sample points with period medians, river comparisons and a site-by-period heatmap. Filters and raw record viewers stay out of the way; filtered CSV remains available.
- **Reference Thresholds & Flags:** compared-only outcome charts, visible selected limits and a separate explanation of unavailable comparisons. Percentages always print their comparable-reading denominator.
- **Sites & Map:** a dark station atlas with one coordinate trace and no external basemap downloads, optional CARTO street context and site histories. Only valid, consistent source coordinates are mapped.
- **Data Quality & Sources:** reading-usability and coverage charts, concise provenance, downloadable quality JSON and optional raw/diagnostic record viewers.
- **Upload & Export:** CSV/XLSX sheet selection, bilingual column suggestions, editable long/wide mappings, encoding/date/decimal controls, normalized preview, filtered CSV and portable HTML monitoring report.

The supplied **2023 file loads 10,911 measurements** (23 parameters, 120 site IDs), covering **February–September 2023** across four sampling months. **2022 loads 13,560 measurements** (30 parameters, 120 site IDs), covering **March–October 2022** across four months; 950 derived IP/status rows and two missing-parameter rows remain in excluded diagnostics. Exact sampling days are unavailable, so charts and filters use source months without invented dates. Both years load separately; cross-year method and station comparability is unverified.

2023 has no unit column. Its concentration units remain unknown and concentration reference comparisons are disabled; pH is intrinsically dimensionless. 2022 preserves and normalizes its explicit units. Maps show 114 (2023) or 118 (2022) source-coordinate locations after excluding conflicting/shared pairs. No station geocoding is used.

The optional fictional fixture has **73 observations**, three fictional stations and six parameters, with verified parsed dates **2023-02-14 through 2023-12-12**. One ambiguous raw date remains undated. Missing/censored cases and a duplicate exercise the diagnostics; these are engineering cases, not findings about Jakarta.

## Load genuine observations

Begin with the [2023 national catalog](https://data.go.id/dataset/dataset/data-kualitas-air-sungai-tahun-2023) or its [Jakarta publisher page](https://satudata.jakarta.go.id/open-data/detail/data-kualitas-air-sungai-tahun-2023). The [2022 catalog](https://data.go.id/dataset/dataset/data-kualitas-air-sungai-2022) is a secondary candidate; no cross-year comparability is assumed. Full retrieval evidence and unknown attributes are in [DATA_SOURCES.md](docs/DATA_SOURCES.md).

For automatic loading, keep the original names:

- `data/raw/Filedata Data Kualitas Air Sungai Tahun 2023.csv`
- `data/raw/Filedata Data Kualitas Air Sungai 2022.csv`

Restart/refresh Streamlit and choose **Official Jakarta 2023** or **Official Jakarta 2022** in the sidebar. The latest available local year is selected by default. Raw files are gitignored; deployments need their own copies after checking usage rights.

For other files, open **Upload & Export**. Recognized Jakarta 2022/2023 layouts use the inspected source adapter, with an option to use custom mappings. Choose its sheet and encoding; review the source preview. Map actual column names, or choose wide layout and explicitly assign each parameter column and unit. Select date/decimal conventions only when known. Add source name, URL and license. Inspect the normalized preview and diagnostics, click **Load validated observations**, then choose **User upload** in the sidebar. No file is sent to a separate data service or saved by the app.

Minimal long input (illustrative schema, not actual monitoring observations):

```csv
site_id,site_name,river_name,sample_date,parameter,value,unit
```

At least site ID or name, parameter and value columns are required. Dates and units may be absent; month-only official observations use explicit sampling-month charts, while incompatible comparisons remain unavailable. Use ISO `YYYY-MM-DD` when possible. Keep nitrate-as-N (`NO3-N`) distinct from nitrate-as-NO3 (`NO3`). Preserve `<0.01` and `ND` as written. Re-importing the included demo preserves synthetic labels. Download an example directly in the app or use `data/demo/synthetic_observations.csv`.

## Interpret reference flags

**Exploratory comparison against a selected reference class; not an official compliance finding.** Selecting a class establishes no legal designation. Rules cover pH, DO, BOD, COD, TSS and nitrate-as-N, transcribed from [PP 22/2021 Appendix VI, river section](https://ppkl.menlhk.go.id/website/filebox/999/2107071507067.%20Lampiran%20VI%20Salinan%20PP%20Nomor%2022%20Tahun%202021.pdf). Each rule has its source entry in `config/standards.yaml`. pH requires confirming the natural peat-water exception does not apply. Unit/basis mismatches, missing values and censored readings produce `not_evaluable` (displayed as **Comparison unavailable**) instead of alerts. Missing units, rules not configured in the app, chemical-basis gaps and pH applicability are explained separately. These are comparison-coverage gaps, not evidence of a reference failure. The percentage outside a reference excludes unavailable cases from its denominator. No overall health index, forecasts or cause analysis.

## Architecture and engineering

`official` adapts the inspected Jakarta layouts; `ingestion` reads and expands input → `mappings`/`cleaning` normalize conservatively → `validation.Dataset` separates raw/retained/rejected records → `analytics`/`standards` compute explainable results → `visualization`/`reports` serve Plotly charts and escaped portable exports → `app/streamlit_app.py` presents six views.

Typed reusable Python functions, file-change-aware official caching and immutable demo caching, cached reference evaluation, deferred record rendering, raw-value/provenance retention, explicit ambiguity controls, safe unit conversion, guarded maps and independently testable threshold operations keep the app useful when input coverage is incomplete. No database, API keys or extra services are needed.

## Verify

```bash
ruff check .
python -m pytest -q
```

Tests cover CSV/XLSX, wide conversion, numbers/dates, censoring, duplicates, coordinates, empty filters, counts, all reference classes, incompatible chemical bases, safe exports and all six Streamlit pages via AppTest. GitHub Actions runs lint and tests on Python 3.11/3.12. See [verification record](docs/VERIFICATION.md) for actual local results and browser limitations.

Further details: [methodology](docs/METHODOLOGY.md), [dictionary](docs/DATA_DICTIONARY.md), [limitations](docs/LIMITATIONS.md), [milestones](docs/IMPLEMENTATION_PLAN.md). The actual local schemas are inspected and tested; exact sampling days, 2023 concentration units and cross-year measurement comparability remain unavailable. Highest-impact follow-up: obtain publisher unit/method metadata and resolve coordinate conflicts before adding any cross-year comparisons.

Design rationale and chart interpretation: [DESIGN_NOTES.md](docs/DESIGN_NOTES.md). Git milestone workflow: [DEVELOPMENT.md](docs/DEVELOPMENT.md).
