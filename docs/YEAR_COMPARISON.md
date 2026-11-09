# Comparing the 2022 and 2023 sources

The **Compare years** workspace loads both locally supplied official CSVs and keeps source-year provenance explicit. Its controls are independent of the single-year source picker and sidebar filters. The six existing views retain their single-year behavior.

## Default comparison

Both source files include **August**, their only shared calendar sampling month. There are 22 common canonical parameter labels and **112 site IDs** with the same river name and internally consistent, valid, non-shared source coordinates within **10 metres** across years. The default parameter is **pH**, which is intrinsically dimensionless in both files. The local files supply 112 exact August pH readings in each year for this accepted location set.

The 10 m tolerance is a documented conservative coordinate-consistency screen for source precision differences, not independent station verification or proof of identical laboratory methods. It is not chosen from the observed readings. Full-source coordinate anomalies are checked before month, parameter or user filters, so narrowing the scope cannot conceal a conflicting coordinate. Eight IDs fail this screen in the current files and remain in the downloadable location audit.

A paired point consists of the median exact reported value for one accepted site and calendar month in each year. Its difference is **2023 minus 2022**, using the same explicit normalized unit. If several exact readings exist within that site/month, counts remain in the export and each site contributes one median. Qualified/missing readings cannot generate paired values; absent observations do not become zero. The median of site differences is computed from those differences, not by subtracting the two overall year medians. No percentage change is calculated for logarithmic pH.

## What the graphs mean

- Separate panels show each year's source distributions with actual sampling months, scale and exact-reading counts.
- Coverage bars show observation counts by original year/month, not assumed monitoring frequency.
- When units/months can be aligned, a paired scatter has an equality diagonal and a river summary shows median site differences. Higher/lower pH is not automatically better/worse water quality.
- Full-year mode shows the actual, different sets of source months. It offers descriptive source distributions and coverage, but no paired numerical difference.

These are descriptions of the supplied historical samples. Method equivalence remains unverified; no causal, regulatory or certified environmental-change finding is made. There is no automatic pooling into a cross-year water-health score or continuous trend.

## Missing concentration units

The 2023 file has no concentration-unit column. BOD, COD, DO, TSS and other concentration parameters may be inspected side by side on **separate source scales**, with explicit unit warnings. No concentration units are borrowed from 2022, inferred from baku_mutu or enabled through an assumption checkbox. Their numerical deltas remain disabled. Nitrate labels whose chemical basis cannot be harmonized are not forced into a common parameter.

## Exports and fallback

Downloads include both years' selected normalized observations with original provenance, a full-source location audit, safe paired differences when available and a self-contained HTML summary of filters, per-year counts/scales, interpretation limits, source URLs and file hashes. Raw tables remain optional in the UI. If either file is absent, the comparison workspace displays an actionable message and other app views still work.
