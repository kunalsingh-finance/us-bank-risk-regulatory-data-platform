# Phase 6 Dashboard Readiness

Final verdict: **Approved as ranking model only**.

1. The constrained histogram-gradient-boosting four-quarter failure model is approved for presentation.
2. It is approved only as a ranking model, not a probability model.
3. Calibration is inadequate: locked-test intercept -4.188 and slope 0.315.
4. Locked-test PR-AUC is 0.148342.
5. No-skill PR-AUC is 0.000513.
6. PR-AUC lift is 289.3×.
7. Unique-failure capture is 58.8% at top 1%, 58.8% at top 5%, and 70.6% at top 10%.
8. Median top-5%-captured lead time is 284 days.
9. False-alert bank-quarters are 1,110, 5,637, and 11,287 at the 1%, 5%, and 10% budgets.
10. The most influential validation drivers are equity-to-assets, year-over-year and quarter-over-quarter equity change, asset growth, return on equity, capital volatility, loan growth, and loans-to-deposits.
11. Importance rankings and linear coefficient directions vary across folds; they are associative, not causal.
12. Banks below $100 million and $100–500 million have enough positive observations for cautious assessment. The $50–250 billion group has 12 positives but weak performance.
13. Other asset bands, many bank classes, and most single-year slices have insufficient events.
14. Performance is not stable across time, particularly in 2022 and 2024.
15. Dashboard scores should be displayed as within-quarter percentiles and risk tiers.
16. Warnings must cover public-data limitations, non-regulatory status, poor probability calibration, sparse failures, subgroup uncertainty, score ties, missingness, false alerts, and non-causal interpretation.
17. The four-quarter model is suitable for a controlled demonstration of analyst prioritization.
18. Eight-quarter failure and severe deterioration may appear as clearly separated secondary views; deterioration must not be described as failure.
19. Phase 6 explainable-alert and dashboard development may begin under these restrictions.
