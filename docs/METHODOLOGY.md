# Methodology

## Ingestion and validation

Read CSV with selectable encoding/delimiter or XLSX with explicit sheet choice. Empty strings are preserved. CSV uses UTF-8 BOM support by default; CP1252/Latin-1 require selection. Long-format mappings require site identity, parameter and value columns. Wide-format imports require explicit parameter/unit assignments for each selected measurement column. Blank cells in selected wide columns become missing observations rather than disappearing.

Preview precedes loading. No implicit sample dates, coordinates, chemical bases or measurement units are created. Source frames, normalized observations and rejected records remain separate. Rows lacking both site ID/name or parameter identity are rejected with a reason; all other observations are retained even when a reading is unevaluable. Missing site names are reported separately when IDs are available.

Auto number parsing accepts simple unambiguous decimal forms and refuses a single separator followed by three digits when it could indicate thousands. Explicit decimal choice enables well-formed thousands grouping. Auto date parsing accepts ISO or unambiguous slash dates; ambiguous dates remain undated until a convention is selected. Numeric Excel serial dates are not guessed; properly formatted Excel date cells are supported. No censored value is replaced by zero or a detection limit. Missing and non-finite values have no numeric reading.

Duplicate candidates are marked and retained; summary counts therefore include them. Keys are for diagnostics, not unique constraints. Original source row numbers support inspection. Negative concentrations stay in the table and are not evaluated against references.

## Analysis

Filters intersect selected rivers, sites, parameters and an optional inclusive measurement-date range. An empty selection gives zero matches. Undated records are included by an explicit toggle but never charted against time. Counts are reported at observation, supplied sample ID and dated site-visit levels; a site visit groups source/site/date without implying a laboratory sample. Station coverage counts unique parameters and first/last valid dates. Completeness percentages use supplied rows as denominator; no expected schedule is inferred. Largest observed date gap is descriptive only.

Measurement charts use discrete markers without interpolated lines. A shared axis is limited to one parameter and one unit. Distribution charts require at least three exact readings per site and display counts; these are descriptive and do not establish statistical comparability.

## References and maps

Verified subset of PP 22/2021 Appendix VI **river** table only. Max/min/range comparisons are inclusive and tested for all four classes. Each result includes reason, rule unit, selected limit and table-entry URL. Only explicit µg/L to mg/L conversion is supported, retaining raw values and original units. pH accepts explicitly supplied pH/dimensionless unit and requires exception applicability confirmation. No inferred chemical-basis conversions; nitrate as NO3 and unknown nitrate have no rule. Censored, missing, ambiguous, incompatible and absent-rule cases are not_evaluable.

Maps require exact source coordinates confirmed by uploader. Numeric pairs must fall in global ranges; multiple distinct coordinate pairs for a source/site cause that site to be omitted rather than averaged. Range validation cannot establish that coordinates truly belong to a Jakarta station. Demo data never maps. No geocoding is performed.

## Exports

Filtered CSV retains normalized values, qualifiers, diagnostics, source and demo labels. Text cells that begin spreadsheet formula characters are prefixed with an apostrophe during CSV serialization only. HTML report is self-contained, escapes untrusted text, includes selected records, class, flags, source, active filters, coverage and limitations, with no remote scripts. JSON quality report describes the full loaded input. Uploads remain in memory. No causal attribution, forecasts, overall river-health score or compliance judgments are generated.

## Verified Jakarta CSV adapters

`official.py` recognizes the actual inspected 2022/2023 headers, strips extra header BOMs, parses each year's documented decimal convention and preserves `bulan_sampling` separately from any exact date. Sampling months are ISO `YYYY-MM` strings. The app offers month selection and categorical month charts, site-month counts and first/latest month coverage; `sample_date` stays null rather than using an invented first day. Source period labels do not establish sample identity.

Original `baku_mutu`, address, parameter group, coordinate strings, unit strings and source row numbers remain available. 2022 derived IP/status rows and missing parameter identities remain in excluded diagnostics. A textual status accidentally present in a Sianida reading remains an invalid measurement, not a numeric result. Explicit `mg L`/`mg l` and microbiology units are normalized; 2023 concentration units are not inferred. Only the intrinsically dimensionless pH scale is named when its source unit is absent.

Each local year is loaded separately and labeled OFFICIAL based on the user's provenance assertion and inspected source layout, with source URL and byte hash. Uploaded copies remain USER-UPLOADED. Both years retain their station IDs, but no method/site equivalence across years is assumed. Valid source coordinates are eligible for mapping only after excluding every source/site with conflicting coordinate pairs and every shared station pair across the full dataset, before user filters; filtering cannot conceal these source anomalies.
