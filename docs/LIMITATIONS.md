# Limitations

- Local official Jakarta 2023/2022 CSVs now load automatically. Exact sampling days are absent, so sampling months are preserved without inventing dates. The 2023 file omits concentration units; only dimensionless pH has an established scale. Laboratory methods, cross-year comparability and a specific redistribution license remain unverified. See DATA_SOURCES.md for the file audit.
- Uploads are USER-UPLOADED, even when the uploader supplies an official URL. Labels and provenance are user assertions, not authentication. The dedicated comparison workspace retains year provenance and screens month/unit/location compatibility; it does not establish laboratory-method equivalence.
- Six verified reference parameters are supported. Class selection is exploratory; site legal designations are unknown. pH natural peat-water exception requires explicit applicability confirmation. Method equivalence and field context require user review. No official compliance classification or pollution index is computed.
- Official maps show source-supplied, numerically valid and consistent coordinates, omitting sites with conflicting/shared pairs. Locations are not independently surveyed. User-upload maps require verification. The default atlas has no background tile requests; optional CARTO street context needs internet. No station geocoding.
- Duplicate candidates are retained and may increase counts. No inference about sampling frequency, missing scheduled samples, causal sources or future conditions.
- CSV/XLSX supports ordinary header rows, long or explicitly mapped wide records. Complex merged headers, multi-table sheets, PDF tables, numeric date serials and custom censoring grammars need preprocessing. Ambiguity is surfaced, not silently resolved.
- In-memory Pandas processing is intended for modest historical datasets, not arbitrarily large files. Refreshing/ending the Streamlit session can discard uploads. Streamlit caches official file loads by file/schema version and recent reference evaluations.
- CI is configured for Python 3.11/3.12; actual local validation uses Python 3.14.7. Test results and server verification are recorded in VERIFICATION.md. Browser verification is reported separately from AppTest.

- Compare years uses a 10 m source-coordinate consistency tolerance and only paired exact readings from a shared calendar month for numerical differences. The current files support paired pH, not concentration deltas. Full-year distributions have different sampling windows. See YEAR_COMPARISON.md.

- This repository does not distribute observation files. If the official CSVs are absent, users must obtain the publisher downloads or upload genuine monitoring data before analysis.
