# Verification record

Local environment: macOS arm64, Python 3.14.7. Last updated 2026-11-09 (Asia/Jakarta).

## Application and analysis checks

The test suite exercises CSV/XLSX reading, long/wide mappings, numeric/date ambiguity, censoring, source-value preservation, duplicate candidates, coordinate guards, all four reference classes, max/min/range boundaries, unsupported-source rejection, filtering, empty selections, graph summaries, comparison denominators, unit conversion, exports and HTML/CSV escaping.

Streamlit AppTest verifies all seven workspaces, user-file preview/load, replacing an already loaded file, source mapping, optional record viewers, graph selectors, no-file onboarding, source-mode migration and two-year comparison behavior. Isolated unit inputs exist only under tests; the application requires official files or monitoring-data uploads.

Real-file integration checks run against the locally provided Jakarta CSVs:

- 2023: 10,911 retained measurements, 120 site IDs, 23 parameters, 114 mapped locations.
- 2022: 13,560 retained measurements, 120 site IDs, 30 parameters, 118 mapped locations; 952 summary/missing-identity exclusions remain in diagnostics.
- Both preserve sampling months without inventing exact days.
- 2023 concentration units are not inferred. Unit/basis/context gaps remain explicit comparison blockers.
- Two-year comparison: August is the only shared calendar month; 112 IDs pass the full-source river/coordinate consistency screen and supply 112 exact paired pH values. Concentration deltas remain disabled; pH percentage changes are not calculated.

## Commands

- `ruff check .`: passed.
- `python -m pytest -q`: **105 passed**, including both actual local files and no-file/upload-only behavior.
- `python -m compileall -q app src`: passed.
- `git diff --check`: passed before publication.

Earlier local startup checks verified a running Streamlit server, an `ok` health response and HTTP 200 from the root page. AppTest checks execution and widget interactions without leaving a background server running.

## Limits of verification

The browser inventory available to this session was empty. No screenshot, pixel-layout verification, browser download-click test, browser rendering-speed measurement or online CARTO tile delivery is claimed. Figure specifications verify the default atlas has one coordinate trace and no external basemap assets.

CI is configured for Python 3.11/3.12. Unit tests run without private/local files; real-file integration checks skip when the separately obtained CSVs are absent. Raw files remain gitignored. CI results are distinct from local test results and are not claimed unless actually inspected.
