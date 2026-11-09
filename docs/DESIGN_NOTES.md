# Graph-first monitoring workspace

Updated 2026-11-09 following user feedback.

## Readings before record tables

Overview asks how one chosen parameter varies across sampling rounds and rivers. Round distributions show every exact reading, median, IQR and sample count. River comparisons use medians with IQR whiskers, explicitly limited to the 12 highest selected river medians. Neither chart is a river-health score. The exploration view provides individual observations, river comparisons and a site-by-period heatmap (up to 25 sites with highest selected median); the site filter can inspect any site outside that selection.

A shared chart axis always uses one parameter and one unit. Unknown units stay labeled as the source scale. No interpolation, invented sampling days, causal attribution or fabricated map geometry is introduced. Sampling coverage can differ between rounds, so changes in distributions are not attributed solely to changing water conditions.

Raw observation, coverage and diagnostic tables are optional record viewers. A collapsed expander alone does not prevent Streamlit execution; the additional Show records toggle defers DataFrame rendering and table searches until requested. Source/normalized upload previews remain visible because users need to review mappings before loading.

## Reference coverage is separate from reference outcomes

The internal status `not_evaluable` is displayed as **Comparison unavailable**. Every unavailable comparison has one primary blocker: missing unit, incompatible unit, unconfigured rule, uncertain chemical basis, missing/qualified reading, pH context or negative concentration. Blocker counts do not overlap. Source data can be a valid reading even when it cannot be compared with a configured reference.

2023 lacks concentration units: those units are never inferred from 2022 or the source baku_mutu text. pH is intrinsically dimensionless but requires applicability confirmation. The verified app rule subset is only pH, DO, BOD, COD, TSS and nitrate-as-N. Unconfigured parameters may have government reference entries, but the app does not pretend to implement them. A direct button switches to the available 2022 dataset with supplied units.

Percent outside selected reference uses **only comparable readings** as denominator, with both counts printed. Within/outside charts omit unavailable cases. Threshold scatter plots use one parameter, show the actual selected max/min/range and explicitly convert µg/L to mg/L when necessary. These are exploratory comparisons, not official compliance findings.

## Station atlas and identity

The default atlas is a dark, geographic coordinate scatter, implemented as one WebGL trace with fixed latitude/longitude aspect. It downloads no map tiles, GeoJSON or remote basemap. Its grid is a coordinate reference, not a claimed river network or boundary. Hover identifies the source station, river, address and observation count. Panning/zooming operates locally.

An optional Street context view uses CARTO Dark Matter tiles and requires network access. The existing full-source coordinate conflict/shared-pair exclusions apply in both views. Locations are not independently surveyed. No geocoding or invented river lines are used.

The product identity is a plain AquaInsight wordmark, restrained green/cream palette and monitoring favicon. The water emoji was removed.

## Performance and verification

Official file loading is cached by file stat and schema version; reference comparisons are cached for up to eight recent filter/class/context combinations. The default atlas avoids tile network latency, table rendering is deferred, and individual-reading charts use at most two traces rather than one trace per station. Browser rendering speed depends on the user's device; no browser timing claim is made. Figure semantics and view interactions are tested with Plotly data assertions and Streamlit AppTest.
