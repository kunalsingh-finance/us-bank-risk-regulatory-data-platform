# Failure Case Study Methodology

Case roles and selection rules were frozen in `configs/dashboard_case_studies.yaml` before visual review. Deterministic selections include shortest and longest top-5% lead, the highest-scoring top-1% captured event, the earliest event missed at top 10%, the highest-scoring negative observation, a captured sub-$500 million bank, and the largest available asset-band event.

The frozen top-1% and top-5% event-capture sets are identical because of isotonic score ties. Therefore no top-5%-but-not-top-1% captured event exists. The dashboard shows an explicit unavailable record rather than inventing one.

The selected set includes captured and missed events, small and larger banks, different dates, and a false-positive example. Selection is illustrative and does not estimate case frequencies or causal mechanisms.
