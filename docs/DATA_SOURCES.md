# Official source audit

Updated **2026-11-08 (Asia/Jakarta)** after the user downloaded both official catalog CSVs into `data/raw`. The files were inspected locally and now load automatically in Streamlit. Original automated retrieval failures are no longer a runtime blocker. Files remain gitignored because a specific redistribution license has not been established.

## Publisher and provenance

Publisher: **Provinsi DKI Jakarta**, via the national Satu Data catalog and Jakarta Satu Data. The 2022 description attributes monitoring to Dinas Lingkungan Hidup. Agency context: https://lingkunganhidup.jakarta.go.id/ and https://lingkunganhidup.jakarta.go.id/publikasi/laporan-kualitas-air . No government endorsement is implied.

| Attribute | 2023 | 2022 |
|---|---|---|
| Catalog | https://data.go.id/dataset/dataset/data-kualitas-air-sungai-tahun-2023 | https://data.go.id/dataset/dataset/data-kualitas-air-sungai-2022 |
| Publisher page | https://satudata.jakarta.go.id/open-data/detail/data-kualitas-air-sungai-tahun-2023 | https://satudata.jakarta.go.id/open-data/detail/data-kualitas-air-sungai-2022 |
| Local filename | `Filedata Data Kualitas Air Sungai Tahun 2023.csv` | `Filedata Data Kualitas Air Sungai 2022.csv` |
| Format | UTF-8 CSV, comma delimiter, decimal point, extra BOM in first header | UTF-8 CSV, comma delimiter, decimal comma, extra BOM in first header |
| Source rows | 10,911 | 14,512 |
| Retained measurements | 10,911 | 13,560 |
| Excluded with diagnostics | 0 | 950 derived IP/status summaries + 2 missing-parameter rows |
| Site IDs / rivers / parameters | 120 / 23 / 23 | 120 / 23 / 30 |
| Sampling months | 2023-02, 2023-05, 2023-08, 2023-09 | 2022-03, 2022-06, 2022-08, 2022-10 |
| Exact sampling days | Not supplied | Not supplied |
| Retained rows per month | 2,760; 2,631; 2,760; 2,760 | 3,598; 3,602; 2,760; 3,600 |
| Missing readings (`-`) | 0 | 480 |
| Invalid textual reading | 0 | 1 (`Cemar sedang` in a Sianida measurement, source row 3901) |
| Censored readings / exact duplicate rows | 0 / 0 | 0 / 0 |
| Measurement units | **No unit column**; concentration units remain unknown | `mg L`, `mg l`, `MPN 100 ml`, `Pt-Co Unit`, `-` (pH) |
| Coordinates | Explicit decimal-degree south/east columns | Explicit latitude/longitude columns, decimal comma |
| Map locations retained | 114 | 118 |

Both years have 480 site-month combinations; this is not a count of identified laboratory samples. No physical sample IDs, exact collection times, laboratory methods or per-record detection limits are supplied. Catalog publication dates (2023 catalog: 02-12-2025; 2022: 05-12-2025; both modified 03-09-2026) are distinct from sampling months. Both catalogs state open access (`Terbuka`) but a specific license has not been verified. Direct downloadable resource URLs remain unrecorded; the user supplied the catalog downloads rather than a resource URL.

### Exact inspected headers

2023: `titik_sampel`, `lintang_selatan`, `bujur_timur`, `jenis_parameter`, `parameter`, `baku_mutu`, `hasil_pengukuran`, `periode_data`, `periode_pemantauan`, `bulan_sampling`, `nama_sungai`, `alamat`.

2022: `periode_data`, `tahun`, `periode`, `bulan_sampling`, `titik_sampel`, `sungai`, `alamat`, `lintang`, `bujur`, `jenis_parameter`, `parameter`, `satuan`, `baku_mutu`, `hasil_pengukuran`.

CSV decoding removes leading BOM characters from header names. The original source row and raw reading are retained. `baku_mutu` is preserved as `source_reference_raw` but is not adopted as an authenticated rule or legal class designation.

### Parameters and units

2023: TDS, TSS, pH, BOD, COD, DO, Nitrat, Nitrit, Total P, F, H2S, Klorin Bebas, Hg, Cd, Zn, Cu, Pb, Cr6+, Minyak dan Lemak, MBAS, Fenol, Total Coliform, Fecal Coliform.

2022 includes corresponding labels (expanded metal names, `COD  dichromat`, `Zat Padat Terlarut  TDS`, `Zat Padat Tersuspensi  TSS`) plus Warna, Sulfat, Klorida, Amoniak, Total N, Ni and Sianida. Expanded names are mapped explicitly; raw names stay intact. The nitrate labels do not establish nitrate-as-N, so they are not compared with the NO3-N rule. Total P is not assumed equivalent to a particular phosphate basis.

2022 units are normalized by explicit spelling mappings to mg/L, MPN/100 mL and Pt-Co Unit. pH is intrinsically dimensionless; `unit_original` remains `-` in 2022 and blank in 2023 while the normalized pH scale is explicit. **No 2023 concentration units are borrowed from 2022, inferred from `baku_mutu`, or assumed from common practice.** Thus 2023 concentration reference results are `not_evaluable`; pH can be compared only after the existing applicability confirmation.

### Station-coordinate diagnostics and comparability

Coordinates fall within latitude -6.370171 to -6.098833 and longitude 106.683389 to 106.969556 in both sources. This numerical range does not independently authenticate a station location.

2023 has conflicting coordinates for CDG-7 and shared coordinate pairs involving BRN-1/BRN-2, CDG-6/CDG-7 and CLW3-1/CLW3-2. All six IDs are omitted from the map, including after sidebar filtering. 2022 has conflicting coordinates for CLW1-2 and a shared pair with CLW1-1; both IDs are omitted. Observations remain available in tables and analytics. Remaining markers show source-supplied coordinates, not geocoded or independently surveyed locations.

Source years and provenance remain explicit. Identical IDs alone do not establish location or method equivalence. The Compare years workspace screens ID, river and coordinate consistency within 10 m, then uses shared calendar months and explicit units for descriptive pairing. August is the only common month; 112 IDs pass the source-location screen. pH can be paired; concentration deltas remain unavailable because 2023 units are missing. Full-year coverage remains descriptive. See YEAR_COMPARISON.md; no certified trend or causal interpretation is offered.

### File integrity

SHA-256 of inspected original bytes:

- 2023: `a5d5e74487809b825957c5234776cc7c00890c24b5610d47c7990424fca36a82`
- 2022: `26364c87499fab6888c265bc3d6db926fbdf674963c5be5996b787f7d6dc7625`

Runtime provenance recalculates each file hash. The cache invalidates on file size/mtime or adapter schema-version changes. `original` keeps the complete source table; `rejected` records summary/invalid-identity exclusions; canonical observations preserve months, period labels, raw coordinates, units and source row numbers.

## Reference regulation

[PP 22/2021 Appendix VI PDF](https://ppkl.menlhk.go.id/website/filebox/999/2107071507067.%20Lampiran%20VI%20Salinan%20PP%20Nomor%2022%20Tahun%202021.pdf). Verified indexed table text: section I, river water, entries 3, 5–8 and 11, pages 1–2. Only this subset is implemented with per-entry citations in `config/standards.yaml`. River TSS Class 1 is 40 mg/L, differing from the lake table. pH has a natural peat-water exception requiring confirmation. Numerical rules do not establish legally designated river classes. Regulation listing: https://peraturan.bpk.go.id/Details/161852/pp-no-22-tahun-2021 . Screenshot requests supplied no viewable payload, so transcription relies on retrieved table text.

## Initial retrieval and fallback history

Automated catalog pages exposed Download labels without usable resource URLs; the Jakarta publisher page was inaccessible through the web tool and direct curl returned a DNS failure even outside the sandbox. The user subsequently provided the actual files audited above. A deterministic 73-row synthetic fixture remains available as an explicit optional demo, CC0, with fictional stations and no coordinates. If neither official file is present, the app defaults to that labeled demo and retains its CSV/XLSX upload workflow. Uploaded copies remain USER-UPLOADED even when a recognized Jakarta schema is used.
