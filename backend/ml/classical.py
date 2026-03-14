"""
Classical ML Models: RandomForest, XGBoost, LightGBM, SVM, KNN, LinearRegression, LogisticRegression
Supports training, persistence, prediction, and feature importance.
"""
import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.svm import SVC, SVR
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    mean_squared_error, mean_absolute_error, r2_score
)
import xgboost as xgb
import lightgbm as lgb
import joblib

logger = logging.getLogger(__name__)

MODEL_DIR = "models/saved"


def _model_path(ticker: str, model_name: str) -> str:
    os.makedirs(MODEL_DIR, exist_ok=True)
    return os.path.join(MODEL_DIR, f"{ticker}_{model_name}.pkl")


def train_all_classifiers(
    X_train: np.ndarray,
    y_train: np.ndarray,
    ticker: str,
    n_estimators: int = 200,
) -> Dict[str, Any]:
    """Train all classical classifiers and persist them."""
    models = {
        "random_forest": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(n_estimators=n_estimators, n_jobs=-1, random_state=42)),
        ]),
        "xgboost": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", xgb.XGBClassifier(
                n_estimators=n_estimators, learning_rate=0.05,
                max_depth=6, use_label_encoder=False,
                eval_metric="logloss", random_state=42, n_jobs=-1,
            )),
        ]),
        "lightgbm": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", lgb.LGBMClassifier(
                n_estimators=n_estimators, learning_rate=0.05,
                max_depth=6, random_state=42, n_jobs=-1, verbose=-1,
            )),
        ]),
        "gradient_boosting": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(n_estimators=100, random_state=42)),
        ]),
        "svm": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", SVC(kernel="rbf", probability=True, C=1.0, random_state=42)),
        ]),
        "logistic_regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, C=1.0, random_state=42)),
        ]),
        "knn": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", KNeighborsClassifier(n_neighbors=5, n_jobs=-1)),
        ]),
    }

    results = {}
    tscv = TimeSeriesSplit(n_splits=5)

    for name, model in models.items():
        try:
            model.fit(X_train, y_train)
            # CV on training
            cv_scores = cross_val_score(model, X_train, y_train, cv=tscv, scoring="accuracy")
            joblib.dump(model, _model_path(ticker, name))
            results[name] = {
                "status": "trained",
                "cv_accuracy_mean": round(cv_scores.mean(), 4),
                "cv_accuracy_std": round(cv_scores.std(), 4),
            }
            logger.info(f"Trained {name}: CV={results[name]['cv_accuracy_mean']:.4f}")
        except Exception as e:
            logger.error(f"Failed to train {name}: {e}")
            results[name] = {"status": "failed", "error": str(e)}

    return results


def predict_all_classifiers(
    X: np.ndarray,
    ticker: str,
) -> Dict[str, Dict]:
    """Load and run all trained classifiers, returning probabilities."""
    predictions = {}
    model_names = [
        "random_forest", "xgboost", "lightgbm", "gradient_boosting",
        "svm", "logistic_regression", "knn",
    ]

    for name in model_names:
        path = _model_path(ticker, name)
        if not os.path.exists(path):
            continue
        try:
            model = joblib.load(path)
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(X)
                pred = model.predict(X)
                prob_up = float(proba[:, 1].mean()) if proba.shape[1] > 1 else float(proba[:, 0].mean())
            else:
                pred = model.predict(X)
                prob_up = float(pred.mean())

            predictions[name] = {
                "prediction": int(pred[-1]) if len(pred) > 0 else 0,
                "probability_up": round(prob_up, 4),
                "signal": "buy" if prob_up > 0.55 else "sell" if prob_up < 0.45 else "hold",
            }
        except Exception as e:
            logger.error(f"Prediction error {name}: {e}")

    return predictions


def get_feature_importance(ticker: str, feature_names: list) -> Dict[str, list]:
    """Extract feature importance from tree-based models."""
    importance_data = {}
    tree_models = ["random_forest", "xgboost", "lightgbm", "gradient_boosting"]

    for name in tree_models:
        path = _model_path(ticker, name)
        if not os.path.exists(path):
            continue
        try:
            model = joblib.load(path)
            clf = model.named_steps.get("clf")
            if hasattr(clf, "feature_importances_"):
                importances = clf.feature_importances_
                sorted_idx = np.argsort(importances)[::-1][:20]
                importance_data[name] = [
                    {"feature": feature_names[i] if i < len(feature_names) else f"f{i}",
                     "importance": round(float(importances[i]), 6)}
                    for i in sorted_idx
                ]
        except Exception as e:
            logger.error(f"Feature importance error {name}: {e}")

    return importance_data


def evaluate_classifier(
    model_name: str,
    ticker: str,
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> Dict[str, float]:
    """Evaluate a trained classifier on test data."""
    path = _model_path(ticker, model_name)
    if not os.path.exists(path):
        return {"error": "Model not found"}
    try:
        model = joblib.load(path)
        y_pred = model.predict(X_test)
        return {
            "accuracy": round(accuracy_score(y_test, y_pred), 4),
            "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
            "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
            "f1_score": round(f1_score(y_test, y_pred, zero_division=0), 4),
        }
    except Exception as e:
        return {"error": str(e)}
