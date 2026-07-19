# Time-Series Validation

Hyperparameters are compared with three expanding-window folds: 2001–2006 to 2007–2008, 2001–2008 to 2009–2010, and 2001–2010 to 2011–2013. Every fold refits imputation, missing indicators, scaling, and the model on earlier observations only. No fold is shuffled and no future quarter enters an earlier fit.

Family winners from rolling-origin cross-validation are compared once on the separate 2014–2018 validation period. The locked test is neither a fold nor a source of tuning feedback. This design exposes crisis clustering and temporal instability that a random split would conceal.
