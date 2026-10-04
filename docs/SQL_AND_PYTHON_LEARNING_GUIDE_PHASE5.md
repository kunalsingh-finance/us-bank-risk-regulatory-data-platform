# SQL and Python Learning Guide — Phase 5

DuckDB creates one-row-per-bank-quarter modelling tables, assigns chronological splits, filters eligible statuses, masks test outcomes, and reconciles row counts. Python fits fold-specific pipelines and calculates rare-event metrics.

Five modelling controls:

1. `WHERE label_status IN ('POSITIVE','NEGATIVE')` prevents censored rows from becoming false negatives.
2. A date `CASE` expression assigns each observation to exactly one chronological split.
3. `Pipeline(SimpleImputer, StandardScaler, LogisticRegression)` fits preprocessing only when the model is fitted on a training fold.
4. PR-AUC compares precision and recall across thresholds and must be interpreted against prevalence.
5. Grouping alerts by reporting quarter makes a 5% review budget operationally comparable through time.

Example SQL:

```sql
SELECT split_assignment, COUNT(*) observations, SUM(outcome) positives
FROM core.model_dataset_failure_4q
WHERE outcome IS NOT NULL
GROUP BY split_assignment;
```

Example Python:

```python
pipeline.fit(training_features, training_target)
validation_probability = pipeline.predict_proba(validation_features)[:, 1]
```

Training-only preprocessing, chronological validation, and test isolation protect the evaluation from leakage. Event-level capture complements row-level metrics, while calibration determines whether model outputs can be interpreted as probabilities.
