# Distress Label Methodology

The deterioration labels are research outcomes built from future observations of Phase 3-validated features. They are not FDIC failure labels, official regulatory classifications, or CAMELS ratings.

At a future bank-quarter, capital evidence is `equity_to_assets <= 5%` or a year-over-year decline of at least 2 percentage points. Asset-quality evidence is a noncurrent-assets proxy of at least 5% of loans or a year-over-year increase of at least 2 percentage points. Earnings evidence requires both ROA at or below -1% and at least two consecutive loss quarters. Liquidity/funding evidence requires estimated deposit outflow of at least 10% together with either loans-to-deposits of at least 100% or FHLB advances of at least 10% of assets. Independently severe capital is `equity_to_assets <= 2%` or `equity_to_assets_change_yoy_pp <= -4`.

The frozen primary event requires independently severe capital evidence or at least two categories on the same future reporting date. This avoids defining distress from one noisy observation. The earlier broad-screening candidate is retained only as documented rejected sensitivity evidence because it was too prevalent for a severe outcome. Four-quarter outcomes search strictly after the predictor date through the inclusive 12-month boundary. Future feature values are stored only as event evidence and are never copied into the predictor layer.

Category-specific labels and a one-category sensitivity rule are retained for face-validity and prevalence comparison. They are sensitivity outcomes, not candidates selected through model performance. Missing category evidence stays missing; conditional and unsupported features are not used.
