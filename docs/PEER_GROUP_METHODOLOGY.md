# Peer Group Methodology

Peer benchmarks use only information available in the bank's reporting quarter. Assets are reported in USD thousands, so the stable dollar bands translate to thresholds of 100,000; 500,000; 1,000,000; 10,000,000; 50,000,000; and 250,000,000 in the source field.

Primary groups are reporting quarter × asset band × reported bank class. A detailed group requires at least 20 banks. Otherwise, the bank receives the same-quarter broad asset-band fallback. Benchmarking applies a second feature-specific test: if fewer than 20 banks in the detailed group have a non-null feature, that feature falls back to the broad same-quarter asset band.

For each of 27 eligible features the platform stores peer count, mean, median, 25th and 75th percentiles, bank percentile, risk-direction-adjusted percentile, distance from median, median absolute deviation, and robust z-score. Robust z-score is null when MAD is zero. Higher-safety features reverse the percentile as `1 - bank_percentile`; non-monotonic and descriptive features receive no risk-adjusted percentile.

Results:

- 688,584 bank-quarters used detailed bank groups; 10,220 used broad asset-band fallback.
- 18,133,416 feature observations used a detailed feature group; 260,566 used feature-specific broad fallback.
- 93,890 benchmark rows still had fewer than 20 non-null peers after the documented broad fallback. They are flagged and should be excluded from later peer-relative modelling.
- Median feature-peer count was 765; observed range was 1–3,220.

No state grouping or business-model grouping was used because it would create excessive small groups or circularity. All peer IDs include the reporting date, preventing future peer populations from entering historical benchmarks.
