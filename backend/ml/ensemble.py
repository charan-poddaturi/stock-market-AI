"""
Ensemble Prediction Engine
Combines classical ML and deep learning models into a weighted ensemble.
Outputs predicted price direction, probability of increase, and confidence score.
"""
import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from ml.classical import predict_all_classifiers
from ml.deep_learning import (
    LSTMModel, GRUModel, CNNLSTMModel, TransformerModel,
    predict_model, load_model, build_model
)

logger = logging.getLogger(__name__)

# Model weights for ensemble (can be learned via stacking)
DEFAULT_WEIGHTS = {
    "random_forest": 0.15,
    "xgboost": 0.20,
    "lightgbm": 0.20,
    "gradient_boosting": 0.10,
    "svm": 0.05,
    "logistic_regression": 0.05,
    "knn": 0.05,
    "lstm": 0.10,
    "gru": 0.05,
    "transformer": 0.05,
}


def run_ensemble_prediction(
    ticker: str,
    X_flat: np.ndarray,      # 2D array for classical models
    X_seq: np.ndarray,       # 3D array (1, seq_len, features) for DL models
    input_size: int,
    seq_len: int = 60,
    current_price: float = 0.0,
) -> Dict[str, Any]:
    """
    Run full ensemble prediction.
    Returns predicted direction, probability, confidence, and per-model breakdown.
    """
    all_predictions = {}
    all_probabilities = {}

    # ─── Classical Models ─────────────────────────────────────────────────────
    try:
        classical_preds = predict_all_classifiers(X_flat, ticker)
        for name, result in classical_preds.items():
            all_predictions[name] = result.get("prediction", 0)
            all_probabilities[name] = result.get("probability_up", 0.5)
    except Exception as e:
        logger.error(f"Classical prediction error: {e}")

    # ─── Deep Learning Models ─────────────────────────────────────────────────
    dl_models = ["lstm", "gru", "transformer"]
    for model_name in dl_models:
        try:
            model = build_model(model_name, input_size=input_size, seq_len=seq_len)
            loaded = load_model(model, ticker, model_name)
            if loaded is not None:
                preds, probs = predict_model(loaded, X_seq)
                all_predictions[model_name] = int(preds[-1]) if len(preds) > 0 else 0
                all_probabilities[model_name] = float(probs[-1]) if len(probs) > 0 else 0.5
        except Exception as e:
            logger.error(f"DL prediction error ({model_name}): {e}")

    if not all_probabilities:
        return {
            "ticker": ticker,
            "error": "No trained models found",
            "prediction": "hold",
            "probability_up": 0.5,
            "confidence": 0.0,
        }

    # ─── Weighted Ensemble ────────────────────────────────────────────────────
    total_weight = 0.0
    weighted_prob_sum = 0.0

    for model_name, prob in all_probabilities.items():
        weight = DEFAULT_WEIGHTS.get(model_name, 0.05)
        weighted_prob_sum += weight * prob
        total_weight += weight

    ensemble_prob = weighted_prob_sum / max(total_weight, 1e-9)

    # ─── Confidence Score ─────────────────────────────────────────────────────
    # Confidence = how much models agree
    probs_array = np.array(list(all_probabilities.values()))
    agreement = 1.0 - np.std(probs_array)  # High std = low agreement
    confidence = round(float(np.clip(agreement, 0, 1)), 4)

    # ─── Direction & Signal ───────────────────────────────────────────────────
    prediction_direction = "up" if ensemble_prob > 0.5 else "down"
    if ensemble_prob > 0.6:
        signal = "strong_buy"
    elif ensemble_prob > 0.52:
        signal = "buy"
    elif ensemble_prob < 0.4:
        signal = "strong_sell"
    elif ensemble_prob < 0.48:
        signal = "sell"
    else:
        signal = "hold"

    # ─── Price Targets ────────────────────────────────────────────────────────
    # Simple confidence-weighted price target
    if current_price > 0:
        magnitude = (ensemble_prob - 0.5) * 2 * confidence * 0.03  # Max 3% move
        price_target_1d = round(current_price * (1 + magnitude), 2)
        price_target_5d = round(current_price * (1 + magnitude * 2.5), 2)
        price_target_30d = round(current_price * (1 + magnitude * 8), 2)
    else:
        price_target_1d = price_target_5d = price_target_30d = None

    return {
        "ticker": ticker,
        "prediction_direction": prediction_direction,
        "probability_up": round(ensemble_prob, 4),
        "probability_down": round(1 - ensemble_prob, 4),
        "confidence_score": confidence,
        "signal": signal,
        "models_used": len(all_predictions),
        "price_target_1d": price_target_1d,
        "price_target_5d": price_target_5d,
        "price_target_30d": price_target_30d,
        "model_breakdown": [
            {
                "model": name,
                "probability_up": round(prob, 4),
                "prediction": "up" if prob > 0.5 else "down",
                "weight": DEFAULT_WEIGHTS.get(name, 0.05),
            }
            for name, prob in all_probabilities.items()
        ],
    }


def compare_models(ticker: str, X_test: np.ndarray, y_test: np.ndarray) -> List[Dict]:
    """Compare all trained models on a test set."""
    from ml.classical import evaluate_classifier
    results = []
    model_names = ["random_forest", "xgboost", "lightgbm", "gradient_boosting", "svm", "logistic_regression", "knn"]
    for name in model_names:
        metrics = evaluate_classifier(name, ticker, X_test, y_test)
        if "error" not in metrics:
            results.append({"model": name, "type": "classical", **metrics})
    return sorted(results, key=lambda x: x.get("f1_score", 0), reverse=True)
