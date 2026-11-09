# Verification record

Verified locally on **2026-11-08, Asia/Jakarta**, macOS arm64, Python **3.14.7**.

## Completed checks

- `.venv/bin/python -m pip install -e '.[dev]'`: succeeded (build dependencies needed approved network access). Earlier no-build-isolation attempt failed because setuptools was absent; normal installation resolved it.
- `.venv/bin/python -m pip check`: no broken requirements.
- `.venv/bin/ruff check .`: all checks passed.
- `.venv/bin/python -m pytest -q`: **73 passed**. Includes all six views in demo, uploaded and empty-selection modes; sparse undated/unitless data; mocked file-uploader preview → load → view navigation; corrupt XLSX error handling; CSV and XLSX reading; wide mappings; parsers; provenance/censoring round trips; duplicate retention; map coordinate guards; filters/sample counts; all four reference classes and boundaries; not-evaluable cases; report escaping and filtered exports; formula neutralization; demo labels including zero-record exports.
- `.venv/bin/python -m compileall -q app src`: succeeded.
- `.venv/bin/python scripts/generate_demo.py`: wrote the labeled 73-row fixture.
- `.venv/bin/streamlit run app/streamlit_app.py --server.headless true --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false`: server started, Uvicorn on localhost:8501. Initial sandbox launch failed port binding; approved launch outside sandbox succeeded.
- `curl --fail --max-time 10 http://127.0.0.1:8501/_stcore/health`: returned `ok` outside sandbox.
- `curl --fail --max-time 10 -I http://127.0.0.1:8501/`: returned **HTTP 200 OK** outside sandbox.

## Browser limitations

Attempted to open the running application using the browser automation tool; in-app browser was unavailable. Browser inventory returned an empty list. **No visual browser verification, actual browser download-click verification, or app screenshot is claimed.** AppTest verifies Streamlit execution and widget interactions, not pixel layout or browser file delivery. CSV/JSON/HTML serialization is tested independently.

## Source limitations

Official catalog and regulation indexed text were inspected with web tools. The user subsequently supplied both actual official CSVs in data/raw; their schemas, units, source months, coordinates, file hashes and anomalies were audited locally. Dedicated adapters load 10,911 (2023) and 13,560 (2022) measurements, with 952 excluded 2022 records retained in diagnostics. Cross-year methods/station equivalence and 2023 concentration units remain unverified. Details: DATA_SOURCES.md. Numerical references remain exploratory and do not establish legally designated classes.

CI is configured for Python 3.11/3.12 but was not executed on a remote runner during this session. `requirements-lock.txt` records the exact local dependency versions, not a guarantee that all platforms support those wheels.

## Official data follow-up checks

- Final local test suite: **73 passed** (`python -m pytest -q`), including real-file integration tests for both local CSVs and every official-data view.
- Lint: `ruff check .` passed.
- Verified official counts, exact source-row preservation, month-only precision, decimal conventions, missing 2023 units, explicit 2022 units, schema-recognized uploads (still USER-UPLOADED), coordinate exclusions and exported OFFICIAL labels.
- Each year has 120 site IDs and 480 site-month combinations; 2023 maps 114 IDs and 2022 maps 118 after suppressing conflicting/shared coordinates.
- Portable synthetic schema fixtures run in CI. Four additional integration/view tests skip in CI if user-downloaded files are absent; raw files remain gitignored.

## Missing metadata column fix

The official adapter now restores its month/unit/provenance fields explicitly, aligning by original source-row identity rather than relying on the generic normalizer to pass those fields through. A regression test for each year removes these fields from the base normalizer output and confirms correct pH/BOD metadata after an excluded row. Official-data cache keys include the adapter schema version. Both local years and all views pass in the 73-test suite. The existing long-running Streamlit process was restarted to discard previously imported modules.

## Graph-first redesign — 2026-11-09

- `ruff check .`: passed.
- `python -m pytest -q`: **86 passed**. Includes existing ingestion/official-data/threshold tests plus single-parameter/unit summaries, exact-reading-only distributions, compared-only percentage denominators, primary comparison blocker classification, threshold drawing with µg/L conversion, single-trace atlas without remote assets, graph-first pages with zero default tables, optional record-table loading and exploration view/parameter switching.
- `python -m compileall -q app src`: passed.
- `git diff --check`: passed; only data/raw/.gitkeep is tracked in the raw directory.
- Streamlit restarted on localhost:8501 with the redesigned application.
- Browser inventory is still empty. No screenshot, visual layout approval, measured browser loading speed or online CARTO tile delivery is claimed. The default atlas has no basemap requests by construction, verified in its figure specification.
- Git baseline published to origin/main as d3d01e2; redesign is published as a separate tested milestone.

## Dedicated year comparison — 2026-11-09

- `ruff check .`: passed.
- `python -m pytest -q`: **96 passed**. Added tests for month intersection, paired-site differences and counts, unverified/moved/absent/invalid coordinate rejection, full-source conflict checks before filtering, missing-unit delta suppression, unequal annual sampling windows, qualified readings, empty selections, same-site median reduction, actual local source counts, comparison-view controls/fallback and navigation back to single-year views.
- The real files yield 112 consistent source locations and 112 exact pH pairs for August; BOD has no paired delta because 2023 units are missing. No pH percentage-change statistic is produced.
- Browser visual verification remains unavailable; Streamlit AppTest verifies interactions and figure construction.
