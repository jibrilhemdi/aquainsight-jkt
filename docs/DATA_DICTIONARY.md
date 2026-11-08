# Canonical observation dictionary

Each row is one reported parameter reading; it is not necessarily a distinct physical sample. Nullable columns are retained, and unknown attributes are never inferred.

| Field | Meaning |
|---|---|
| source_id/name/url/file | Dataset identity and uploader-supplied provenance; not independently authenticated |
| source_row | 1-based source row with header counted (Excel row for ordinary header-at-top files) |
| import_file/import_row | Current import file and row; canonical re-imports retain original source lineage separately |
| site_id | Supplied identity; falls back to supplied site_name when ID absent |
| site_name, river_name | Original supplied labels, blank if absent |
| sample_id | Explicit identifier only; never synthesized in uploaded observations |
| sample_date_raw | Original date representation; raw bulan_sampling for official monthly sources |
| sample_month/sample_date_precision | Verified YYYY-MM month and month precision; exact sample_date remains null |
| monitoring_period/address/parameter_group | Source monitoring period, address and parameter category |
| source_reference_raw | Source baku_mutu text; never establishes legal class or replaces verified rules |
| latitude_raw/longitude_raw/unit_basis_note | Raw coordinate strings and explanation of unit/basis handling |
| sample_date | Parsed date at midnight; NaT if missing, ambiguous or invalid |
| latitude, longitude | Numeric, paired global-range coordinates or null |
| coordinates_verified | Uploader asserted exact source station coordinates; false for demo |
| parameter_original_name | Source label |
| parameter_code | Explicit bilingual alias or unchanged unknown name; chemical bases remain distinct |
| value_raw | Source text, including censoring symbols and missing string |
| value_numeric | Finite parsed exact value; null for censored/missing/invalid/ambiguous strings |
| unit_original/normalized | Original unit and limited explicit spelling normalization |
| qualifier | exact, missing, censored, ambiguous, invalid, or preserved source qualifier |
| quality_note/date_issue/coordinate_issue | Human-readable parsing and validation diagnostics |
| duplicate_candidate | Matching source/site/date/sample/parameter/raw value/unit; retained for review |
| data_mode/data_notice | OFFICIAL, USER-UPLOADED or SYNTHETIC DEMO; explicit demo warning on exports |
| reference_blocker | One primary machine-readable reason when comparison is unavailable; blank for comparable readings |
| reference_* | Selected class, status/reason, inclusive limit/kind/unit, regulation URL and table entry |

Parameter aliases: derajat keasaman → pH; oksigen terlarut → DO; kebutuhan oksigen biokimiawi → BOD; kebutuhan oksigen kimiawi → COD; padatan tersuspensi total → TSS; nitrat sebagai N → NO3-N. Unspecified nitrate is not assigned an N basis. Phosphate aliases do not imply total phosphorus and have no implemented reference rule.

The verified Jakarta 2022/2023 layouts are implemented in official.py; exact headers and explicit mappings are documented in DATA_SOURCES.md. Other Indonesian aliases remain generic upload suggestions.
