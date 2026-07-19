# Temporal Split Methodology

Splits were selected from event counts and coverage before model performance was inspected. Training spans 2001 Q1–2013 Q4 and includes the pre-crisis, financial-crisis, and early recovery periods. Validation spans 2014 Q1–2018 Q4. Its 2014–2016 portion fits calibration; 2017–2018 selects calibration and the F2 threshold. The locked test spans 2019 Q1–2024 Q4 and contains 58 positive observations from 17 banks.

The test is intentionally recent but statistically small. It is not enlarged or moved after results. The same bank may occur in multiple chronological splits, reflecting real deployment, while each observation date belongs to exactly one split. `reports/institution_overlap_by_split.csv` discloses repeated-bank exposure. Outcome eligibility is horizon-specific, so row counts differ across four-quarter, eight-quarter, and deterioration datasets.
