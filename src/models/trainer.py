"""Governed chronological CV, validation selection, calibration, and pre-test artifacts."""

from __future__ import annotations

import json
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.pipeline import Pipeline

from src.database.manifest import JsonObject, sha256_file

from .baselines import fit_rule_parameters, prevalence_probability, rule_probability
from .calibration import apply_calibrator, fit_calibrator
from .config import included_features, load_hashed_config, require_string
from .evaluator import (
    calibration_intercept_slope,
    evaluate_predictions,
    expected_calibration_error,
    reliability_table,
)
from .interpretability import logistic_coefficients, permutation_importance_frame
from .logistic import logistic_pipeline
from .manifest import canonical_hash, write_manifest
from .registry import replace_table_from_frame
from .thresholds import quarter_budget_flags, select_f2_threshold
from .tree_models import gradient_boosting_pipeline, random_forest_pipeline


@dataclass(frozen=True)
class CandidateSpec:
    model_id: str
    family: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class FittedCandidate:
    specification: CandidateSpec
    artifact: Any


def load_model_frame(database_path: Path, table_name: str) -> pd.DataFrame:
    connection: duckdb.DuckDBPyConnection = duckdb.connect(str(database_path), read_only=True)
    frame: pd.DataFrame = connection.execute(
        f"SELECT * FROM core.{table_name} WHERE split_assignment IN ('TRAIN','VALIDATION') ORDER BY reporting_date,cert"
    ).fetch_df()
    connection.close()
    return frame


def candidate_specs(config: JsonObject) -> tuple[CandidateSpec, ...]:
    families: object = config.get("families")
    if not isinstance(families, dict):
        raise TypeError("model_candidates families must be an object")
    result: list[CandidateSpec] = []
    for family, raw in families.items():
        if not isinstance(raw, dict) or not isinstance(raw.get("grid"), list):
            raise TypeError(f"Invalid candidate family: {family}")
        for index, parameters in enumerate(raw["grid"], start=1):
            if not isinstance(parameters, dict):
                raise TypeError(f"Invalid candidate parameters: {parameters!r}")
            result.append(CandidateSpec(f"{family}__{index}", str(family), dict(parameters)))
    return tuple(result)


def fit_candidate(
    specification: CandidateSpec,
    features: pd.DataFrame,
    target: np.ndarray,
    candidate_config: JsonObject,
    seed: int,
) -> FittedCandidate:
    if specification.family == "prevalence_baseline":
        return FittedCandidate(specification, {"prevalence": float(target.mean())})
    if specification.family == "rule_score":
        names: tuple[str, ...] = tuple(str(value) for value in specification.parameters["features"])
        return FittedCandidate(specification, {"feature_names": names, "parameters": fit_rule_parameters(features,names)})
    families: dict[str, object] = candidate_config["families"]  # type: ignore[assignment]
    family_config: object = families[specification.family]
    if not isinstance(family_config, dict):
        raise TypeError(f"Invalid candidate family configuration: {specification.family}")
    if specification.family in ("logistic", "regularized_logistic"):
        model: Pipeline = logistic_pipeline(specification.parameters,int(family_config["max_iter"]),seed)
    elif specification.family == "random_forest":
        model = random_forest_pipeline(specification.parameters,seed)
    elif specification.family == "hist_gradient_boosting":
        model = gradient_boosting_pipeline(specification.parameters,seed)
    else:
        raise ValueError(f"Unsupported candidate family: {specification.family}")
    model.fit(features,target)
    return FittedCandidate(specification,model)


def predict_candidate(fitted: FittedCandidate, features: pd.DataFrame) -> np.ndarray:
    if fitted.specification.family == "prevalence_baseline":
        return np.full(len(features),float(fitted.artifact["prevalence"]),dtype=float)
    if fitted.specification.family == "rule_score":
        return rule_probability(features,fitted.artifact["feature_names"],fitted.artifact["parameters"])
    return np.asarray(fitted.artifact.predict_proba(features)[:,1],dtype=float)


def save_pickle(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(value,handle)
    return sha256_file(path)


def date_subset(frame: pd.DataFrame, start: object, end: object) -> pd.DataFrame:
    dates: pd.Series = pd.to_datetime(frame["reporting_date"])
    return frame.loc[(dates>=pd.Timestamp(start))&(dates<=pd.Timestamp(end))].copy()


def identifiers(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[["cert","rssdid","reporting_date"]].reset_index(drop=True)


def features_target(frame: pd.DataFrame, feature_names: tuple[str,...]) -> tuple[pd.DataFrame,np.ndarray]:
    values: pd.DataFrame = frame.loc[:,feature_names].astype(float).replace([np.inf,-np.inf],np.nan).reset_index(drop=True)
    target: np.ndarray = frame["outcome"].astype(int).to_numpy()
    return values,target


def cross_validate(
    frame: pd.DataFrame,
    feature_names: tuple[str,...],
    specifications: tuple[CandidateSpec,...],
    protocol: JsonObject,
    candidates_config: JsonObject,
    metrics_config: JsonObject,
) -> tuple[pd.DataFrame,pd.DataFrame]:
    cv: object = protocol.get("cross_validation")
    if not isinstance(cv,dict) or not isinstance(cv.get("folds"),list):
        raise TypeError("Invalid cross-validation protocol")
    budgets: tuple[float,...] = tuple(float(value) for value in metrics_config["alert_budgets"])  # type: ignore[index]
    rows: list[dict[str,Any]] = []
    coefficients: list[pd.DataFrame] = []
    seed: int = 20260718
    for raw_fold in cv["folds"]:
        if not isinstance(raw_fold,dict):
            raise TypeError("Invalid fold")
        train: pd.DataFrame = date_subset(frame,raw_fold["train"][0],raw_fold["train"][1])
        validation: pd.DataFrame = date_subset(frame,raw_fold["validation"][0],raw_fold["validation"][1])
        train_x,train_y = features_target(train,feature_names)
        validation_x,validation_y = features_target(validation,feature_names)
        for specification in specifications:
            fitted: FittedCandidate = fit_candidate(specification,train_x,train_y,candidates_config,seed)
            probability: np.ndarray = predict_candidate(fitted,validation_x)
            threshold: float = select_f2_threshold(validation_y,probability)
            result: dict[str,Any] = evaluate_predictions(identifiers(validation),validation_y,probability,threshold,budgets)
            rows.append({"fold":raw_fold["fold"],"model_id":specification.model_id,"family":specification.family,
                         "train_start":raw_fold["train"][0],"train_end":raw_fold["train"][1],
                         "validation_start":raw_fold["validation"][0],"validation_end":raw_fold["validation"][1],**result})
            if specification.family in ("logistic","regularized_logistic"):
                coefficient: pd.DataFrame = logistic_coefficients(fitted.artifact,feature_names)
                coefficient["fold"] = raw_fold["fold"]
                coefficient["model_id"] = specification.model_id
                coefficients.append(coefficient)
    return pd.DataFrame(rows),pd.concat(coefficients,ignore_index=True)


def family_winners(cv_results: pd.DataFrame,specifications: tuple[CandidateSpec,...]) -> tuple[CandidateSpec,...]:
    summary: pd.DataFrame = cv_results.groupby(["model_id","family"],as_index=False).agg(mean_average_precision=("average_precision","mean"),mean_brier_score=("brier_score","mean"))
    winners: list[CandidateSpec] = []
    by_id: dict[str,CandidateSpec] = {item.model_id:item for item in specifications}
    for family,group in summary.groupby("family"):
        selected: pd.Series = group.sort_values(["mean_average_precision","mean_brier_score","model_id"],ascending=[False,True,True]).iloc[0]
        winners.append(by_id[str(selected["model_id"])])
    return tuple(sorted(winners,key=lambda item:item.family))


def validation_compare(
    frame: pd.DataFrame,
    feature_names: tuple[str,...],
    winners: tuple[CandidateSpec,...],
    candidates_config: JsonObject,
    metrics_config: JsonObject,
    artifact_dir: Path,
) -> tuple[pd.DataFrame,dict[str,FittedCandidate],dict[str,pd.DataFrame]]:
    train: pd.DataFrame = frame.loc[frame["split_assignment"]=="TRAIN"].copy()
    validation: pd.DataFrame = frame.loc[frame["split_assignment"]=="VALIDATION"].copy()
    train_x,train_y = features_target(train,feature_names)
    validation_x,validation_y = features_target(validation,feature_names)
    budgets: tuple[float,...] = tuple(float(value) for value in metrics_config["alert_budgets"])  # type: ignore[index]
    rows: list[dict[str,Any]] = []
    fitted_by_id: dict[str,FittedCandidate] = {}
    prediction_by_id: dict[str,pd.DataFrame] = {}
    for specification in winners:
        fitted: FittedCandidate = fit_candidate(specification,train_x,train_y,candidates_config,20260718)
        probability: np.ndarray = predict_candidate(fitted,validation_x)
        threshold: float = select_f2_threshold(validation_y,probability)
        result: dict[str,Any] = evaluate_predictions(identifiers(validation),validation_y,probability,threshold,budgets)
        rows.append({"model_id":specification.model_id,"family":specification.family,"split":"VALIDATION_RAW",**result})
        predictions: pd.DataFrame = validation[["cert","rssdid","reporting_date","asset_size_band","bank_class","feature_quality_status"]].reset_index(drop=True)
        predictions["target"] = validation_y
        predictions["raw_probability"] = probability
        prediction_by_id[specification.model_id] = predictions
        fitted_by_id[specification.model_id] = fitted
        save_pickle(artifact_dir/f"candidate__{specification.model_id}.pkl",fitted)
    comparison: pd.DataFrame = pd.DataFrame(rows).sort_values(["average_precision","brier_score","model_id"],ascending=[False,True,True])
    return comparison,fitted_by_id,prediction_by_id


def select_calibration(
    validation_predictions: pd.DataFrame,
    protocol: JsonObject,
    metrics_config: JsonObject,
) -> tuple[dict[str,Any],pd.DataFrame,float,pd.DataFrame]:
    splits: dict[str,object] = protocol["splits"]  # type: ignore[assignment]
    fit_start,fit_end = splits["calibration_fit"]  # type: ignore[misc]
    select_start,select_end = splits["validation_selection"]  # type: ignore[misc]
    dates: pd.Series = pd.to_datetime(validation_predictions["reporting_date"])
    fit_mask: pd.Series = (dates>=pd.Timestamp(fit_start))&(dates<=pd.Timestamp(fit_end))
    select_mask: pd.Series = (dates>=pd.Timestamp(select_start))&(dates<=pd.Timestamp(select_end))
    fit_y: np.ndarray = validation_predictions.loc[fit_mask,"target"].to_numpy(dtype=int)
    fit_p: np.ndarray = validation_predictions.loc[fit_mask,"raw_probability"].to_numpy(dtype=float)
    select_y: np.ndarray = validation_predictions.loc[select_mask,"target"].to_numpy(dtype=int)
    select_raw: np.ndarray = validation_predictions.loc[select_mask,"raw_probability"].to_numpy(dtype=float)
    methods: list[str] = ["none","platt"]
    if int(fit_y.sum()) >= 20:
        methods.append("isotonic")
    rows: list[dict[str,Any]] = []
    fitted: dict[str,dict[str,Any]] = {}
    for method in methods:
        calibrator: dict[str,Any] = fit_calibrator(method,fit_y,fit_p)
        probability: np.ndarray = apply_calibrator(calibrator,select_raw)
        intercept,slope = calibration_intercept_slope(select_y,probability)
        rows.append({"method":method,"fit_observations":len(fit_y),"fit_positives":int(fit_y.sum()),
                     "selection_observations":len(select_y),"selection_positives":int(select_y.sum()),
                     "brier_score":float(brier_score_loss(select_y,probability)),
                     "average_precision":float(average_precision_score(select_y,probability)),
                     "calibration_intercept":intercept,"calibration_slope":slope,
                     "expected_calibration_error":expected_calibration_error(select_y,probability,10)})
        fitted[method] = calibrator
    comparison: pd.DataFrame = pd.DataFrame(rows).sort_values(["brier_score","expected_calibration_error","method"])
    method: str = str(comparison.iloc[0]["method"])
    selected_calibrator: dict[str,Any] = fitted[method]
    selected_probability: np.ndarray = apply_calibrator(selected_calibrator,select_raw)
    threshold: float = select_f2_threshold(select_y,selected_probability)
    selection_predictions: pd.DataFrame = validation_predictions.loc[select_mask].copy()
    selection_predictions["probability"] = selected_probability
    reliability: pd.DataFrame = reliability_table(select_y,selected_probability,10)
    return selected_calibrator,comparison,threshold,reliability


def write_csv(frame: pd.DataFrame,path: Path) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    frame.to_csv(path,index=False,lineterminator="\n")


def develop_models(root: Path) -> JsonObject:
    protocol: JsonObject = load_hashed_config(root/"configs/experiment_protocol.yaml")
    feature_config: JsonObject = load_hashed_config(root/"configs/model_features.yaml")
    candidates_config: JsonObject = load_hashed_config(root/"configs/model_candidates.yaml")
    metrics_config: JsonObject = load_hashed_config(root/"configs/evaluation_metrics.yaml")
    feature_names: tuple[str,...] = included_features(feature_config)
    database_path: Path = root/"database/bank_risk_models.duckdb"
    frame: pd.DataFrame = load_model_frame(database_path,"model_dataset_failure_4q")
    specifications: tuple[CandidateSpec,...] = candidate_specs(candidates_config)
    cv_results,coefficients = cross_validate(frame,feature_names,specifications,protocol,candidates_config,metrics_config)
    report_dir: Path = root/"reports"
    write_csv(cv_results,report_dir/"candidate_model_results.csv")
    winners: tuple[CandidateSpec,...] = family_winners(cv_results,specifications)
    artifact_dir: Path = root/"artifacts/models/phase5"
    comparison,fitted_by_id,predictions_by_id = validation_compare(frame,feature_names,winners,candidates_config,metrics_config,artifact_dir)
    write_csv(comparison,report_dir/"validation_model_comparison.csv")
    selected_id: str = str(comparison.iloc[0]["model_id"])
    selected_spec: CandidateSpec = next(item for item in winners if item.model_id==selected_id)
    selected_fitted: FittedCandidate = fitted_by_id[selected_id]
    selected_predictions: pd.DataFrame = predictions_by_id[selected_id]
    calibrator,calibration_comparison,threshold,reliability = select_calibration(selected_predictions,protocol,metrics_config)
    calibration_comparison["selected"] = calibration_comparison["method"]==calibrator["method"]
    write_csv(calibration_comparison,report_dir/"validation_calibration.csv")
    write_csv(reliability.assign(split="VALIDATION_SELECTION",method=calibrator["method"]),report_dir/"validation_reliability_table.csv")
    model_hash: str = save_pickle(artifact_dir/"selected_primary_model.pkl",selected_fitted)
    calibrator_hash: str = save_pickle(artifact_dir/"selected_primary_calibrator.pkl",calibrator)
    budgets: tuple[float,...] = tuple(float(value) for value in metrics_config["alert_budgets"])  # type: ignore[index]
    dates: pd.Series = pd.to_datetime(selected_predictions["reporting_date"])
    selection_window: object = protocol["splits"]  # type: ignore[index]
    selection_start,selection_end = selection_window["validation_selection"]  # type: ignore[index]
    selection_mask: pd.Series = (dates>=pd.Timestamp(selection_start))&(dates<=pd.Timestamp(selection_end))
    final_validation: pd.DataFrame = selected_predictions.loc[selection_mask].copy()
    final_validation["probability"] = apply_calibrator(calibrator,final_validation["raw_probability"].to_numpy(dtype=float))
    final_metrics: dict[str,Any] = evaluate_predictions(identifiers(final_validation),final_validation["target"].to_numpy(dtype=int),final_validation["probability"].to_numpy(dtype=float),threshold,budgets)
    threshold_rows: list[dict[str,Any]] = []
    for budget in budgets:
        flags: np.ndarray = quarter_budget_flags(identifiers(final_validation),final_validation["probability"].to_numpy(dtype=float),budget)
        target: np.ndarray = final_validation["target"].to_numpy(dtype=int)
        captured: int = int(target[flags].sum())
        threshold_rows.append({"outcome_name":"failure_4q","model_id":selected_id,"split":"VALIDATION_SELECTION","threshold_type":"SAME_QUARTER_BUDGET","threshold_value":None,"alert_budget":budget,"precision":captured/int(flags.sum()),"recall":captured/int(target.sum()),"alerts":int(flags.sum()),"false_alerts":int(flags.sum())-captured})
    threshold_rows.append({"outcome_name":"failure_4q","model_id":selected_id,"split":"VALIDATION_SELECTION","threshold_type":"F2_PROBABILITY","threshold_value":threshold,"alert_budget":None,"precision":final_metrics["precision"],"recall":final_metrics["recall"],"alerts":None,"false_alerts":None})
    write_csv(pd.DataFrame(threshold_rows),report_dir/"validation_threshold_results.csv")
    # Train horizon-specific models using the primary selected family/hyperparameters without test access.
    outcome_specs: tuple[tuple[str,str],...] = (("failure_4q","model_dataset_failure_4q"),("failure_8q","model_dataset_failure_8q"),("deterioration_4q","model_dataset_deterioration_4q"))
    outcome_selections: dict[str,JsonObject] = {}
    validation_prediction_rows: list[pd.DataFrame] = []
    for outcome_name,table_name in outcome_specs:
        outcome_frame: pd.DataFrame = frame if outcome_name=="failure_4q" else load_model_frame(database_path,table_name)
        train: pd.DataFrame = outcome_frame.loc[outcome_frame["split_assignment"]=="TRAIN"].copy()
        validation: pd.DataFrame = outcome_frame.loc[outcome_frame["split_assignment"]=="VALIDATION"].copy()
        train_x,train_y = features_target(train,feature_names)
        validation_x,validation_y = features_target(validation,feature_names)
        fitted: FittedCandidate = selected_fitted if outcome_name=="failure_4q" else fit_candidate(selected_spec,train_x,train_y,candidates_config,20260718)
        raw_probability: np.ndarray = predict_candidate(fitted,validation_x)
        prediction_frame: pd.DataFrame = validation[["cert","rssdid","reporting_date","asset_size_band","bank_class","feature_quality_status"]].reset_index(drop=True)
        prediction_frame["target"] = validation_y
        prediction_frame["raw_probability"] = raw_probability
        outcome_calibrator,outcome_calibration,outcome_threshold,_ = select_calibration(prediction_frame,protocol,metrics_config)
        prediction_frame["probability"] = apply_calibrator(outcome_calibrator,raw_probability)
        prediction_frame["outcome_name"] = outcome_name
        prediction_frame["model_id"] = selected_id
        prediction_frame["protocol_hash"] = require_string(protocol,"configuration_hash")
        validation_prediction_rows.append(prediction_frame[["cert","rssdid","reporting_date","outcome_name","model_id","target","raw_probability","probability","asset_size_band","bank_class","feature_quality_status","protocol_hash"]])
        model_artifact: Path = artifact_dir/f"selected_{outcome_name}_model.pkl"
        calibration_artifact: Path = artifact_dir/f"selected_{outcome_name}_calibrator.pkl"
        outcome_selections[outcome_name] = {"model_id":selected_id,"family":selected_spec.family,"parameters":selected_spec.parameters,
            "model_path":str(model_artifact.relative_to(root)).replace("\\","/"),"model_sha256":save_pickle(model_artifact,fitted),
            "calibrator_path":str(calibration_artifact.relative_to(root)).replace("\\","/"),"calibrator_sha256":save_pickle(calibration_artifact,outcome_calibrator),
            "calibration_method":outcome_calibrator["method"],"classification_threshold":outcome_threshold,
            "validation_calibration_candidates":outcome_calibration.to_dict("records")}
    validation_predictions: pd.DataFrame = pd.concat(validation_prediction_rows,ignore_index=True)
    replace_table_from_frame(database_path,"modeling.validation_predictions",validation_predictions)
    # Interpretability uses the selected primary model and a bounded validation sample.
    selected_family: str = selected_spec.family
    if selected_family in ("logistic","regularized_logistic"):
        importance: pd.DataFrame = logistic_coefficients(selected_fitted.artifact,feature_names)
    elif selected_family not in ("prevalence_baseline","rule_score"):
        validation_sample: pd.DataFrame = frame.loc[frame["split_assignment"]=="VALIDATION"].sort_values(["reporting_date","cert"]).iloc[::max(1,len(frame.loc[frame["split_assignment"]=="VALIDATION"] )//10000)].head(10000)
        sample_x,sample_y = features_target(validation_sample,feature_names)
        importance = permutation_importance_frame(selected_fitted.artifact,sample_x,sample_y,feature_names,20260718)
    else:
        importance = pd.DataFrame({"feature_name":selected_spec.parameters.get("features",[]),"importance_mean":np.nan,"importance_std":np.nan,"importance_type":"preregistered_rule"})
    importance["model_id"] = selected_id
    write_csv(importance,report_dir/"model_feature_importance.csv")
    write_csv(coefficients,report_dir/"coefficient_stability.csv")
    direction: pd.DataFrame = coefficients.groupby(["model_id","feature_name"],as_index=False).agg(mean_coefficient=("standardized_coefficient","mean"),minimum_coefficient=("standardized_coefficient","min"),maximum_coefficient=("standardized_coefficient","max"),folds=("fold","nunique"))
    direction["sign_consistent"] = np.sign(direction["minimum_coefficient"])==np.sign(direction["maximum_coefficient"])
    write_csv(direction,report_dir/"feature_direction_consistency.csv")
    # Training-only preprocessing audit for selected primary pipeline.
    if isinstance(selected_fitted.artifact,Pipeline):
        imputer = selected_fitted.artifact.named_steps["preprocessor"].named_steps["imputer"]
        audit: pd.DataFrame = pd.DataFrame({"feature_name":feature_names,"training_median":imputer.statistics_[:len(feature_names)]})
        audit["fit_population"] = "TRAIN_ONLY_2001Q1_2013Q4"
        audit["validation_or_test_used"] = False
    else:
        audit = pd.DataFrame([{"feature_name":"BASELINE","training_median":None,"fit_population":"TRAIN_ONLY_2001Q1_2013Q4","validation_or_test_used":False}])
    write_csv(audit,report_dir/"preprocessing_audit.csv")
    write_csv(pd.DataFrame(columns=["exception_id","category","severity","description","status"]),report_dir/"model_quality_exceptions.csv")
    selection: JsonObject = {"status":"PRE_TEST_SELECTION_READY","protocol_hash":require_string(protocol,"configuration_hash"),
        "selected_primary_model":selected_id,"selected_family":selected_family,"selected_parameters":selected_spec.parameters,
        "selected_calibration_method":calibrator["method"],"classification_threshold":threshold,"operational_alert_budget":0.05,
        "validation_selection_metrics":final_metrics,"primary_model_sha256":model_hash,"primary_calibrator_sha256":calibrator_hash,
        "outcome_selections":outcome_selections,"locked_test_accessed":False}
    write_manifest(root/"manifests/model_experiment/validation_selection_manifest.json",selection)
    return selection
