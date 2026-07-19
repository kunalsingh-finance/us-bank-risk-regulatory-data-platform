# Dashboard Limitations

- The locked test contains only 17 unique failing banks; confidence intervals and subgroup estimates are wide.
- Calibration was weak (slope 0.315), so the app presents percentiles, ranks, and tiers instead of calibrated institution-level likelihoods.
- Performance varied materially across years and asset-size bands, including weak 2022 and 2024 results.
- Top-1% and top-5% event capture are identical because score ties reduce budget efficiency.
- The top-5% locked-test budget generated 5,637 false-alert bank-quarters.
- Peer groups can contain fewer than 20 non-null feature observations; warnings remain visible.
- Public FDIC data cannot reproduce confidential supervisory assessments.
- Local perturbations and feature importance are associative, not causal.
- Historical demonstration results do not guarantee future performance.
- The platform supplies neither regulatory nor investment advice.
