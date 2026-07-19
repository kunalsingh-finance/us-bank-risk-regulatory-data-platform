# Class-Imbalance Policy

FDIC failure is rare, so PR-AUC is the primary metric and the positive prevalence is always reported as the no-skill PR-AUC. Candidate learners use class weights or cost-sensitive learning. SMOTE is not part of the primary experiment.

Operational evaluation ranks banks within each quarter and flags top 1%, 5%, and 10% budgets. The top 5% is primary. Both bank-quarter recall and unique-failure-event capture are reported. Ordinary accuracy is labelled misleading because predicting nearly all banks as non-failures can appear accurate while providing little warning value.
