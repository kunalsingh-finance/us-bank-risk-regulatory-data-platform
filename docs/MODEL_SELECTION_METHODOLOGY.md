# Model Selection Methodology

All ten preregistered candidates are reported. Hyperparameters are selected within family using mean expanding-window PR-AUC, then mean Brier score. Family winners are compared on the separate validation period using PR-AUC and the frozen tie-breakers.

The constrained histogram-gradient-boosting configuration with learning rate 0.05, 150 iterations, 15 leaf nodes, minimum leaf size 50, and L2 regularization 1.0 won the validation comparison. Random forest led mean internal-fold PR-AUC, an important stability caveat. The final selection was not changed to reconcile that difference.
