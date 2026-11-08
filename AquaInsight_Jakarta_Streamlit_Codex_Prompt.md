# Codex Master Prompt — AquaInsight Jakarta (Streamlit Monitoring Platform)

You are a senior Python software engineer, data engineer, environmental-data analyst, and Streamlit application developer. **Build and verify a working, portfolio-quality Streamlit application in the current workspace.** Do not stop after planning, generating mockups, or scaffolding. Implement the code, run the tests, fix problems, document the project, and provide exact run instructions.

## 1. Product definition

**Project:** AquaInsight Jakarta  
**Tagline:** An interactive Jakarta river water-quality monitoring and analytics platform.  
**Main objective:** Transform verified historical river-water-quality monitoring observations into an accessible, explainable, interactive Streamlit platform for exploring measurement trends, monitoring-site coverage, reference-threshold flags, and data quality.

**This is a software and data-engineering project.** Focus on the working product, sound analytical logic, reliable code, usability, and documentation. **Do not add change-management plans, stakeholder matrices, adoption roadmaps, hypothetical interviews, UX research plans, or related deliverables.**

The application analyzes **historical monitoring data**, not live sensor readings. Never claim real-time monitoring or operational alerts unless an independently verified live data source actually exists and is implemented (not required). It is an independent portfolio project; never imply DHI, Jakarta government, or environmental regulators endorse it.

Priorities, in order:
1. Successfully load genuine public monitoring observations, if accessible, or provide a reliable CSV/XLSX upload workflow.
2. Build a robust, tested ingestion and data-validation pipeline.
3. Build a useful Streamlit monitoring app with interactive exploration and trustworthy reference comparisons.
4. Add site mapping when actual verified coordinates exist.
5. Provide useful downloads, concise documentation, tests, and a polished repository.

If a feature conflicts with data integrity, **data integrity wins**.

## 2. How to work: execute end-to-end

1. Inspect the current repository and installed environment. Preserve any useful existing files. For an empty workspace, create the project.
2. Write a concise milestone checklist in `docs/IMPLEMENTATION_PLAN.md`; **immediately start implementing it**.
3. Proceed in stages: **A. source audit → B. ingestion/validation → C. analytical logic → D. Streamlit UI → E. exports → F. tests/CI → G. README/polish.**
4. After each stage, run the relevant checks and repair failures before proceeding. Prefer fully functioning MVP features over half-implemented extras.
5. Choose sensible defaults without asking routine questions; ask only if a genuinely necessary restricted source or local file requires the user's action.
6. Never claim a test ran, a dataset loaded, a screenshot was created, or a feature works unless you actually verified it.
7. If network access is blocked, still create a working, explicitly labeled **synthetic DEMO** mode plus an import path for genuine observations. Don't block the entire project on one website.
8. Provide a brief final handover with files created, data status, commands executed, test outcomes, remaining limitations, and how to start the app.

## 3. Official source audit — inspect before inventing assumptions

Start with these authoritative resources; follow their actual downloadable resources and verify their contents:

- Jakarta river-water quality 2023: https://data.go.id/dataset/dataset/data-kualitas-air-sungai-tahun-2023
- Jakarta river-water quality 2022: https://data.go.id/dataset/dataset/data-kualitas-air-sungai-2022
- Jakarta open-data publisher: https://satudata.jakarta.go.id/open-data/detail/data-kualitas-air-sungai-tahun-2023
- Jakarta environmental agency: https://lingkunganhidup.jakarta.go.id/
- National water-quality reference standard, PP 22/2021, Appendix VI (river-water section): https://ppkl.menlhk.go.id/website/filebox/999/2107071507067.%20Lampiran%20VI%20Salinan%20PP%20Nomor%2022%20Tahun%202021.pdf
- Regulation listing: https://peraturan.bpk.go.id/Details/161852/pp-no-22tahun-2021

Create `docs/DATA_SOURCES.md` recording: publisher; dataset/resource URLs; download method; retrieval date; data period vs publication date; actual file type and sheets; true column names; site identifiers; available parameters and units; sampling frequency; number of records; missing values; stated license; and discovered limitations. Distinguish **verified** facts from assumptions.

**Do not infer a dataset's structure from the catalog description.** Inspect the raw file. If a portal page has a “Download” label but the file cannot be accessed in this environment, explain the precise blocker and use upload support. Do not invent measurements, coordinates, timestamps, legal classes, downloads, or citations.

Try 2023 first. Use 2022 as a second dataset only if its schema, sampling definitions, station identity, measurement methods, and units can be harmonized transparently. If cross-year comparability is uncertain, don't produce misleading trend claims.

## 4. Application pages and behavior (required)

Use Streamlit (`app/streamlit_app.py`) with a clear left sidebar and responsive layout. English-language UI is fine; preserve local station/river names and document Indonesian-to-English parameter mappings. Build **six working views**:

### A. Overview

- Display app title, data mode **OFFICIAL / USER-UPLOADED / SYNTHETIC DEMO**, dataset/source name, latest **measurement date** (not latest refresh/download date), monitoring period, observation count, unique site count, parameter count.
- Show coverage and data-quality summary with clear caveats.
- A chart showing measurements or monitoring coverage over time; another summarizing parameter or site coverage.
- Show recent/latest available observations if useful, explicitly labeled historical observations rather than live sensor readings.
- No unsupported “overall river health score.”

### B. Explore Measurements

- Sidebar filters for date range, river, site, and parameter; options depend on what data actually contains.
- Interactive Plotly plot showing observed measurements over time by selected site/parameter. Show individual sample markers. Do not imply continuous monitoring where observations are sparse.
- Optional box/violin chart for site comparisons where observations are sufficient; provide sample count and unit.
- A sortable/searchable observation table including date, location, parameter, reading, unit, qualifier, and provenance.
- Download **filtered CSV** with filters reflected in the export. Handle no-match filters gracefully.
- No inappropriate aggregation of unlike parameters or unlike measurement units.

### C. Reference Thresholds & Flags

- Provide selectable PP 22/2021 river-water reference **Class 1–4** (where verified rules exist).
- Build rules from verified regulation entries, with parameter, unit/basis, class, comparison kind (**maximum**, **minimum**, or **range**), source link, and relevant notes. Include only rules actually verified and correctly matched to dataset units and chemical basis.
- Show a table and summary of readings that are `within_reference`, `outside_reference`, or `not_evaluable`, including **why** a comparison could/couldn't be made.
- Explicitly account for pH as range, dissolved oxygen (DO) as minimum, and concentration limits (e.g. BOD/COD/TSS) as maxima only when verified.
- Display a visible disclaimer: **“Exploratory comparison against a selected reference class; not an official compliance finding.”**
- Selecting a class does not establish the river's legally designated class. Do not assume all sites are Class 2.
- Do not report an “alert” when a value is missing, censored, or not safely comparable. Treat this as `not_evaluable`.
- Provide filterable flagged measurements and downloadable CSV. Use measured value, applicable limit, unit, date, site, and source.

### D. Sites & Map

- Show a table of sites and monitoring coverage: location/river, first/last sample dates, observation count, number of measured parameters, and data completeness.
- When **verified** latitude/longitude exist, show an interactive map with correctly located markers and a meaningful hover/selection summary. Validate numeric coordinates and eliminate invalid/out-of-range values.
- If coordinates are unavailable or doubtful, **omit the map and explain why**. Do not invent coordinates or geocode ambiguous river/site names to pretend stations are exact.
- Allow site selection to filter/inspect its parameter data.

### E. Data Quality & Sources

- Data diagnostics: row counts before and after processing, rejected/invalid rows, missing observations, date parsing failures, duplicate candidates, unusual units, source coverage, monitoring gaps, and censored measurements.
- Show dataset provenance, license/usage notes (if found), download/access date, measurement period, and a clear distinction between real and demo data.
- Export a machine-readable quality report (CSV or JSON).
- Explain what was excluded and why; do not silently discard observations.

### F. Upload & Export

- Upload CSV or XLSX (including sheet selection for Excel). Validate schema and show a preview before loading.
- Support the verified official schema directly; optionally provide user-facing column mappings for plausible alternate schemas.
- If an uploaded file cannot be normalized safely, show an actionable error with missing columns, ambiguous units/dates, or required mappings.
- Allow export of normalized observations and a **downloadable monitoring summary** (self-contained HTML or Markdown is acceptable; PDF only if robustly supported). Include active filters, counts, charts/table summaries as practical, provenance, relevant flags, and interpretation limitations.
- Do not include fabricated cause analysis, legal judgments, or predictions in exports.

Make the Streamlit application pleasant to use: consistent labels, compact page navigation, loading indicators, metric cards, clear legends, tooltips, empty-state messages, and caching for costly immutable operations. All pages must work even when the optional map and reference comparisons are unavailable.

## 5. Data model and ingestion pipeline

Use a reusable **canonical long-format observation table**, mapped from the actual imported file(s). Suggested fields, nullable unless genuinely required:

```text
source_id, source_name, source_url, source_file,
site_id, site_name, river_name,
sample_id, sample_date,
latitude, longitude,
parameter_code, parameter_original_name,
value_raw, value_numeric,
unit_original, unit_normalized,
qualifier, quality_note,
data_mode
```

Implement separate modules for file reading, schema mapping, cleaning, validation, analysis, thresholds, plotting, and reporting. The processing pipeline must:

- Handle CSV encoding/BOM, comma-vs-dot decimals and thousands separators **only when unambiguous**, varied/ambiguous dates, Excel sheets, wide-to-long source formats, and missing values.
- Preserve `value_raw` and relevant provenance even if a row is rejected or not evaluable.
- Treat `<0.01`, `≤0.01`, `ND`, and other detection-limit codes as censored/qualified readings, **not zero and not necessarily equal to the stated detection limit**. Avoid numeric threshold comparisons unless the logic can handle the censoring correctly.
- Apply only explicit and scientifically valid unit conversions. Distinguish nitrate-as-N from nitrate-as-NO3, phosphate-as-P from PO4, etc. Unknown or mixed chemical bases must not be compared to the wrong limit.
- Avoid overwriting rows on potentially nonunique keys. Identify possible duplicates and document the handling.
- Keep original observations, cleaned observations, rejected-row diagnostics, and quality metrics logically separate.
- Preserve source dataset name and original observation dates on screen and in exports.
- Gracefully support datasets with no verified dates, no geocoordinates, or only a subset of typical parameters; disable misleading visualizations instead of making values up.

For the initial demo, generate a small **deterministic, explicitly synthetic** fixture with plausible but entirely fictional site IDs/observations and known test cases. Clearly show `SYNTHETIC DEMO — NOT ACTUAL JAKARTA MONITORING DATA` on **every page** and in every exported report/CSV. Never treat demo metrics as findings about Jakarta rivers. Users must be able to switch to official data or uploaded data when available.

## 6. Scientific and analytical safeguards

- This is **historical monitoring analytics**, not a real-time IoT solution and not a certified regulatory compliance service.
- Do not compute an official water-quality index or pollution index unless the complete applicable government formula, parameter coverage, and verification cases are available; exclude from MVP.
- Do not add ML forecasting or generic AI-generated pollution explanations. They are unnecessary for a solid initial project and can be misleading with sparse samples.
- Do not attribute causes to industry, rainfall, upstream discharge, human activity, or any other factor without relevant evidence.
- Use explicit, unit-tested max/min/range threshold operations; include source/table references in `config/standards.yaml` or equivalent for each verified rule.
- Where sampling frequency is sparse or irregular, avoid connecting points in ways that imply continuous monitoring. Label counts and monitoring periods.
- “Outside selected reference” is **not equivalent** to a confirmed contamination event or regulatory violation.
- If input data lacks a field required for a feature, disable that feature with a helpful message instead of producing placeholders that look real.

## 7. Technical stack and repository structure

Use:
- **Python 3.11+**, **Streamlit**, **Pandas**, **NumPy**, **Plotly**.
- **Pytest** for tests, **Ruff** for linting, and typed reusable functions.
- **openpyxl** for Excel; optional **PyArrow**, **Pandera**, and **DuckDB** if genuinely useful, not just for complexity.
- A `pyproject.toml` with clean install and reproducible scripts. Avoid unnecessary services, APIs, databases, authentication, and heavyweight frameworks.

Preferred structure (adapt to actual data):

```text
aquainsight-jakarta/
├── app/
│   └── streamlit_app.py
├── src/aquainsight/
│   ├── __init__.py
│   ├── ingestion.py
│   ├── mappings.py
│   ├── cleaning.py
│   ├── validation.py
│   ├── analytics.py
│   ├── standards.py
│   ├── visualization.py
│   └── reports.py
├── config/
│   ├── column_mappings.yaml
│   └── standards.yaml
├── data/
│   ├── README.md
│   ├── demo/                   # explicitly synthetic only
│   └── raw/                    # gitignored unless legally redistributable
├── docs/
│   ├── IMPLEMENTATION_PLAN.md
│   ├── DATA_SOURCES.md
│   ├── DATA_DICTIONARY.md
│   ├── METHODOLOGY.md
│   └── LIMITATIONS.md
├── tests/
│   ├── fixtures/
│   ├── test_ingestion.py
│   ├── test_cleaning.py
│   ├── test_analytics.py
│   ├── test_standards.py
│   └── test_reports.py
├── .github/workflows/ci.yml
├── .gitignore
├── pyproject.toml
└── README.md
```

Keep core logic outside `streamlit_app.py` so it is independently testable. Add static demo/fixture generation or simple setup script if helpful. Do not commit private uploads, huge raw datasets, caches, or environment secrets.

## 8. Testing and quality gates — required

Automated tests should include at least:

1. File import for representative CSV and XLSX fixtures; correct wide-to-long mappings.
2. Decimal and date parsing, including a case that must be rejected as ambiguous.
3. Preservation of original values and provenance; missing and censored observation behavior.
4. Duplicate observation handling, invalid coordinates, missing site names, and zero-row filter results.
5. Correct unit compatibility and rejection of mismatched chemical bases.
6. Threshold rules: pH below/inside/above a range, DO below/at/above minimum, BOD or COD below/at/above maximum, all four classes where verified.
7. `not_evaluable` classifications for absent rules, missing readings, censored values, incompatible units.
8. Correct site/sample counts and filtering by site/parameter/date.
9. Report exports use actual filtered records and include sources, selected reference class, and demo warnings.
10. Synthetic demo label cannot be confused with official data in the application or exports.

Configure CI to run lint and tests. Run commands such as:

```bash
python -m pip install -e '.[dev]'
ruff check .
python -m pytest -q
streamlit run app/streamlit_app.py
```

Test application startup or a Streamlit smoke test as feasible. If a browser is available, interact with each page and confirm that filtering, downloads, and empty states work. If browser access is unavailable, say so instead of claiming visual verification.

## 9. README and user documentation

Provide a strong `README.md` covering:
- What AquaInsight Jakarta does; screenshot(s) from the **actual app** if you can produce them.
- Verified data source URLs, genuine-vs-demo status, latest available **observation** dates, and limitations.
- Platform features and architecture diagram or concise component summary.
- Local installation/launch instructions and supported input formats.
- How to load the official dataset and upload CSV/XLSX; example normalized schema.
- Interpretation of threshold flags; why this is not official compliance analysis.
- Running automated tests, exports, and deployment (optional Streamlit Community Cloud guidance).
- A short portfolio-ready engineering summary, describing **only completed features**.

All docs should focus on **the monitoring platform and engineering decisions**. No stakeholder research, adoption/change-management sections, or invented fieldwork.

## 10. Definition of done (check each item before declaring completion)

- [ ] Runnable Streamlit application with all six views and useful behavior.
- [ ] Official observations loaded with documented provenance **OR** complete user-upload workflow plus unmistakably synthetic demo mode.
- [ ] Verified source schema mapping and robust, independently tested data-processing pipeline.
- [ ] Interactive date/site/parameter exploration with truthful sampling presentation.
- [ ] Reference comparisons using verified rules, correct max/min/range logic, and explicit non-compliance caveat.
- [ ] Monitoring-site coverage table; map only if trustworthy coordinates exist.
- [ ] Data-quality diagnostics and download of filtered observations and report.
- [ ] No fabricated measurements, station coordinates, threshold references, real-time labels, or causal claims.
- [ ] README + data-source/methodology/limitations documentation.
- [ ] Tests and lint successfully run, or exact verified blockers are listed.
- [ ] No change-management or stakeholder-adoption deliverables.

## 11. Final Codex response format

When done, report succinctly:
1. **Built:** completed features and main code paths.
2. **Data:** source name/URL, actual records and date range if loaded, or synthetic/upload-only status and blocker.
3. **Tests:** commands really run and pass/fail results.
4. **Start locally:** exact commands to install and launch the app.
5. **Limitations:** unavailable data/coordinates/thresholds or unverified UI behavior.
6. **Next engineering upgrades:** at most three, ranked by impact.

**Begin now. Inspect the workspace and sources, write the short checklist, then implement the complete Streamlit monitoring platform. Do not stop at planning.**
