# Implementation milestones

- [x] A. Audited 2023/2022 official catalogs, publisher/agency resources and river-water regulation. Recorded raw-file access failures; no official schema invented.
- [x] B. Implemented conservative CSV/XLSX ingestion, explicit long/wide mapping, original-value/provenance preservation and separate rejected diagnostics.
- [x] C. Implemented filters, coverage, sample/visit counts and verified inclusive max/min/range reference comparisons for six parameters and four classes.
- [x] D. Built all six Streamlit views with data-mode notices, empty/sparse-data behavior and guarded maps.
- [x] E. Added filtered CSV, full quality JSON, rejected diagnostics and self-contained HTML monitoring summary.
- [x] F. Passed lint and the initial 61 tests; repaired sample-ID mapping, absent river filters, re-import lineage and zero-row demo export labels. Verified Streamlit server and HTTP health/root response. Browser unavailable; documented honestly.
- [x] G. Completed README, dictionary, methodology, source audit, limitations, verification record, CI and exact launch instructions.

Architecture: source frames → explicit mapping and conservative parsing → canonical observations + separate rejected diagnostics → independently testable analytics/standards → Plotly + Streamlit → provenance-preserving exports. Immutable synthetic fixture is cached; uploads remain in session memory. No database or external runtime API is required.

## Official data integration follow-up

- [x] Inspected both user-downloaded raw CSVs and recorded exact headers, units, months, row counts, file hashes and anomalies.
- [x] Added verified 2022/2023 adapters, automatic local-file discovery, default official 2023 selection and separate-year navigation.
- [x] Added month-precision filters/charts/coverage, without inventing dates or sample identifiers.
- [x] Preserved missing 2023 units and source chemical bases; excluded derived IP/status records with diagnostics.
- [x] Mapped validated source coordinates while suppressing full-source conflicting/shared station pairs.
- [x] Tested both real local files and all six official views; added portable synthetic-schema fixtures for CI.
