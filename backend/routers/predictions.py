"""
Predictions Router: ML/DL model training, prediction, and model comparison.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import numpy as np
import logging
from data.ingestion import yahoo
from data.pipeline import clean_data, engineer_features, get_feature_columns, normalize_features, prepare_sequences
from ml.classical import train_all_classifiers
from ml.deep_learning import build_model, train_model, save_model, load_model, predict_model
from ml.ensemble import run_ensemble_prediction, compare_models
from config import settings
from utils.cache import TTLCache

router = APIRouter()
logger = logging.getLogger(__name__)

# Cache prediction results for quick repeated UI interactions
_PREDICTION_CACHE = TTLCache(ttl_seconds=60, maxsize=200)
_MODEL_COMPARISON_CACHE = TTLCache(ttl_seconds=300, maxsize=100)
_TIMEFRAME_CACHE = TTLCache(ttl_seconds=60, maxsize=200)


def _scaler_path(ticker: str) -> str:
    return f"models/saved/{ticker}_scaler.pkl"


def _fallback_from_features(df, current_price: float) -> dict:
    """
    Heuristic fallback when no trained models are available.

    Uses recent RSI, price vs SMA20, and short-term returns to
    generate a probability_up in a smooth but non-trivial way
    instead of always returning 0.5.
    """
    row = df.iloc[-1]

    rsi = float(row.get("rsi_14", 50.0))
    price_vs_sma20 = float(row.get("price_vs_sma20", 0.0))
    roc_5 = float(row.get("roc_5", 0.0))

    # Normalize inputs into a small score around 0
    rsi_component = (rsi - 50.0) / 50.0 * 0.25          # [-0.25, 0.25] roughly
    trend_component = max(min(price_vs_sma20, 0.1), -0.1) * 1.0  # clamp extreme values
    mom_component = max(min(roc_5 / 20.0, 0.1), -0.1)   # scale 5‑day % change

    raw_score = rsi_component * 0.5 + trend_component * 0.3 + mom_component * 0.2

    prob_up = 0.5 + raw_score
    prob_up = float(np.clip(prob_up, 0.05, 0.95))

    # Derive signal similar to ensemble thresholds
    if prob_up > 0.6:
        signal = "strong_buy"
    elif prob_up > 0.52:
        signal = "buy"
    elif prob_up < 0.4:
        signal = "strong_sell"
    elif prob_up < 0.48:
        signal = "sell"
    else:
        signal = "hold"

    # Simple price targets based on confidence
    confidence = float(np.clip(abs(prob_up - 0.5) * 2.0, 0.0, 1.0))
    if current_price > 0:
        magnitude = (prob_up - 0.5) * 2 * confidence * 0.03  # max ~3% move scaled by confidence
        price_target_1d = round(current_price * (1 + magnitude), 2)
        price_target_5d = round(current_price * (1 + magnitude * 2.5), 2)
        price_target_30d = round(current_price * (1 + magnitude * 8), 2)
    else:
        price_target_1d = price_target_5d = price_target_30d = None

    return {
        "prediction_direction": "up" if prob_up > 0.5 else "down",
        "probability_up": prob_up,
        "probability_down": round(1 - prob_up, 4),
        "confidence_score": round(confidence, 4),
        "signal": signal,
        "models_used": 0,
        "price_target_1d": price_target_1d,
        "price_target_5d": price_target_5d,
        "price_target_30d": price_target_30d,
    }


def _prepare_prediction(ticker: str, period: str):
    """Synchronous prediction helper used by async endpoints."""
    cache_key = (ticker.upper(), period)
    cached = _PREDICTION_CACHE.get(cache_key)
    if cached is not None:
        return cached

    df = yahoo.fetch_ohlcv(ticker, period=period)
    if df.empty:
        raise ValueError(f"No data for {ticker}")

    df = clean_data(df)
    df = engineer_features(df)

    if len(df) < settings.sequence_length + 10:
        raise ValueError("Insufficient data for prediction")

    feature_cols = get_feature_columns(df, exclude_targets=True)
    scaler_path = _scaler_path(ticker)
    df_norm, _ = normalize_features(
        df, feature_cols, fit=False, scaler_path=scaler_path
    )

    # Latest data for prediction
    X_flat = df_norm[feature_cols].fillna(0).values[-1:].reshape(1, -1)

    seq_len = settings.sequence_length
    if len(df_norm) >= seq_len:
        X_seq = df_norm[feature_cols].fillna(0).values[-seq_len:].reshape(1, seq_len, -1)
    else:
        X_seq = np.zeros((1, seq_len, len(feature_cols)))

    current_price = float(df["close"].iloc[-1])

    result = run_ensemble_prediction(
        ticker=ticker,
        X_flat=X_flat,
        X_seq=X_seq,
        input_size=len(feature_cols),
        seq_len=seq_len,
        current_price=current_price,
    )

    # If no trained models are available, fall back to a heuristic
    if result.get("error") == "No trained models found" or result.get("models_used", 0) == 0:
        heuristic = _fallback_from_features(df, current_price)
        # Merge heuristic outputs into result so shape stays consistent
        result.update(heuristic)

    # Add market context
    result["current_price"] = current_price
    result["latest_rsi"] = round(float(df.get("rsi_14", df["close"]).iloc[-1]), 2)
    result["ticker"] = ticker

    _PREDICTION_CACHE.set(cache_key, result)
    return result


class PredictRequest(BaseModel):
    ticker: str
    period: str = "2y"
    model: str = "ensemble"  # ensemble, lstm, xgboost, random_forest, etc.
    retrain: bool = False


class TrainRequest(BaseModel):
    ticker: str
    period: str = "2y"
    epochs: int = 30
    model_types: List[str] = ["lstm", "xgboost", "random_forest", "lightgbm"]

    def validate(self) -> None:
        if not self.ticker or not self.ticker.strip():
            raise HTTPException(status_code=400, detail="Ticker is required")
        if self.epochs <= 0:
            raise HTTPException(status_code=400, detail="Epochs must be positive")
        if self.epochs > 100:
            raise HTTPException(status_code=400, detail="Epochs must not exceed 100 for safety")


@router.post("/")
async def predict(req: PredictRequest):
    """Run prediction for a ticker using specified model."""
    ticker = req.ticker.upper()

    try:
        result = await asyncio.to_thread(_prepare_prediction, ticker, req.period)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("No data"):
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        logger.exception("Prediction execution failed")
        raise HTTPException(status_code=500, detail="Prediction failed")

    return result


def _train_sync(ticker: str, period: str, epochs: int, model_types: List[str]):
    """Synchronous training runner used via a worker thread."""
    try:
        df = yahoo.fetch_ohlcv(ticker, period=period)
        if df.empty:
            logger.error(f"No data for {ticker}")
            return

        df = clean_data(df)
        df = engineer_features(df)
        feature_cols = get_feature_columns(df, exclude_targets=True)

        # Classical ML
        X = df[feature_cols].fillna(0).values
        y = df["target_1d"].fillna(0).values
        split = int(len(X) * 0.8)
        train_results = train_all_classifiers(X[:split], y[:split], ticker)
        logger.info(f"Classical training complete for {ticker}: {train_results}")

        # Deep Learning
        seq_len = settings.sequence_length
        scaler_path = _scaler_path(ticker)
        df_norm, _ = normalize_features(
            df, feature_cols, fit=True, force_fit=True, scaler_path=scaler_path
        )
        X_seq, y_seq = prepare_sequences(df_norm, feature_cols, "target_1d", seq_len)
        if len(X_seq) > 50:
            split_seq = int(len(X_seq) * 0.8)
            X_tr, X_val = X_seq[:split_seq], X_seq[split_seq:]
            y_tr, y_val = y_seq[:split_seq], y_seq[split_seq:]

            for model_name in ["lstm", "gru", "transformer"]:
                if model_name in model_types:
                    try:
                        model = build_model(model_name, input_size=len(feature_cols), seq_len=seq_len)
                        train_model(model, X_tr, y_tr, X_val, y_val, epochs=epochs)
                        save_model(model, ticker, model_name)
                        logger.info(f"Trained {model_name} for {ticker}")
                    except Exception as e:
                        logger.error(f"DL training error {model_name}: {e}")

    except Exception as e:
        logger.error(f"Training pipeline error: {e}")


@router.post("/train")
async def train_models(req: TrainRequest, background_tasks: BackgroundTasks):
    """Train all models for a ticker (can be slow, runs in background)."""
    req.validate()
    ticker = req.ticker.upper()
    background_tasks.add_task(
        asyncio.to_thread,
        _train_sync,
        ticker,
        req.period,
        req.epochs,
        req.model_types,
    )
    return {"message": f"Training started for {ticker} in background", "ticker": ticker}


def _compare_sync(ticker: str, period: str):
    cache_key = (ticker.upper(), period)
    cached = _MODEL_COMPARISON_CACHE.get(cache_key)
    if cached is not None:
        return cached

    df = yahoo.fetch_ohlcv(ticker, period=period)
    if df.empty:
        raise ValueError(f"No data for {ticker}")

    df = clean_data(df)
    df = engineer_features(df)
    feature_cols = get_feature_columns(df, exclude_targets=True)
    df_norm, _ = normalize_features(df, feature_cols, fit=False, scaler_path=_scaler_path(ticker))

    X = df_norm[feature_cols].fillna(0).values
    y = df["target_1d"].fillna(0).values
    split = int(len(X) * 0.8)
    X_test, y_test = X[split:], y[split:]

    if len(X_test) < 10:
        raise ValueError("Insufficient test data")

    results = compare_models(ticker, X_test, y_test)
    response = {"ticker": ticker, "model_comparison": results}
    _MODEL_COMPARISON_CACHE.set(cache_key, response)
    return response


@router.get("/compare/{ticker}")
async def compare_model_predictions(ticker: str, period: str = "1y"):
    """Compare all trained models on test data."""
    ticker = ticker.upper()
    try:
        return await asyncio.to_thread(_compare_sync, ticker, period)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("No data"):
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception:
        logger.exception("Model comparison failed")
        raise HTTPException(status_code=500, detail="Model comparison failed")


def _timeframe_sync(ticker: str):
    cache_key = (ticker.upper(), "timeframes")
    cached = _TIMEFRAME_CACHE.get(cache_key)
    if cached is not None:
        return cached

    df = yahoo.fetch_ohlcv(ticker, period="2y")
    if df.empty:
        raise ValueError(f"No data for {ticker}")

    df = clean_data(df)
    df = engineer_features(df)
    feature_cols = get_feature_columns(df, exclude_targets=True)
    df_norm, _ = normalize_features(df, feature_cols, fit=False, scaler_path=_scaler_path(ticker))

    seq_len = settings.sequence_length
    X_flat = df_norm[feature_cols].fillna(0).values[-1:].reshape(1, -1)
    X_seq = df_norm[feature_cols].fillna(0).values[-seq_len:].reshape(1, seq_len, -1) if len(df_norm) >= seq_len else np.zeros((1, seq_len, len(feature_cols)))
    current_price = float(df["close"].iloc[-1])

    result = run_ensemble_prediction(ticker, X_flat, X_seq, len(feature_cols), seq_len, current_price)

    if result.get("error") == "No trained models found" or result.get("models_used", 0) == 0:
        heuristic = _fallback_from_features(df, current_price)
        result.update(heuristic)

    response = {
        "ticker": ticker,
        "current_price": current_price,
        "timeframes": {
            "1d": {
                "horizon": "1 Day",
                "target": result.get("price_target_1d"),
                "signal": result.get("signal"),
                "probability_up": result.get("probability_up"),
            },
            "1w": {
                "horizon": "1 Week",
                "target": result.get("price_target_5d"),
                "signal": result.get("signal"),
                "probability_up": result.get("probability_up"),
            },
            "1m": {
                "horizon": "1 Month",
                "target": result.get("price_target_30d"),
                "signal": result.get("signal"),
                "probability_up": result.get("probability_up"),
            },
        },
        "confidence": result.get("confidence_score"),
    }

    _TIMEFRAME_CACHE.set(cache_key, response)
    return response


@router.get("/timeframes/{ticker}")
async def multi_timeframe_prediction(ticker: str):
    """Generate predictions for 1d, 1w, 1m timeframes."""
    ticker = ticker.upper()
    try:
        return await asyncio.to_thread(_timeframe_sync, ticker)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("No data"):
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception:
        logger.exception("Timeframe prediction failed")
        raise HTTPException(status_code=500, detail="Timeframe prediction failed")
