"""
Predictions Router: ML/DL model training, prediction, and model comparison.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import numpy as np
import logging
from data.ingestion import yahoo
from data.pipeline import clean_data, engineer_features, get_feature_columns, normalize_features, prepare_sequences
from ml.classical import train_all_classifiers
from ml.deep_learning import build_model, train_model, save_model, load_model, predict_model
from ml.ensemble import run_ensemble_prediction, compare_models
from config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


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


@router.post("/")
async def predict(req: PredictRequest):
    """Run prediction for a ticker using specified model."""
    ticker = req.ticker.upper()

    # Fetch and process data
    df = yahoo.fetch_ohlcv(ticker, period=req.period)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")

    df = clean_data(df)
    df = engineer_features(df)

    if len(df) < settings.sequence_length + 10:
        raise HTTPException(status_code=400, detail="Insufficient data for prediction")

    feature_cols = get_feature_columns(df, exclude_targets=True)
    df_norm, scaler = normalize_features(df, feature_cols, fit=True)

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

    # Add market context
    result["current_price"] = current_price
    result["latest_rsi"] = round(float(df.get("rsi_14", df["close"]).iloc[-1]), 2)
    result["ticker"] = ticker

    return result


@router.post("/train")
async def train_models(req: TrainRequest, background_tasks: BackgroundTasks):
    """Train all models for a ticker (can be slow, runs in background)."""
    ticker = req.ticker.upper()

    async def _train():
        try:
            df = yahoo.fetch_ohlcv(ticker, period=req.period)
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
            df_norm, _ = normalize_features(df, feature_cols, fit=True,
                                            scaler_path=f"models/saved/{ticker}_scaler.pkl")
            X_seq, y_seq = prepare_sequences(df_norm, feature_cols, "target_1d", seq_len)
            if len(X_seq) > 50:
                split_seq = int(len(X_seq) * 0.8)
                X_tr, X_val = X_seq[:split_seq], X_seq[split_seq:]
                y_tr, y_val = y_seq[:split_seq], y_seq[split_seq:]

                for model_name in ["lstm", "gru", "transformer"]:
                    if model_name in req.model_types:
                        try:
                            model = build_model(model_name, input_size=len(feature_cols), seq_len=seq_len)
                            train_model(model, X_tr, y_tr, X_val, y_val, epochs=req.epochs)
                            save_model(model, ticker, model_name)
                            logger.info(f"Trained {model_name} for {ticker}")
                        except Exception as e:
                            logger.error(f"DL training error {model_name}: {e}")

        except Exception as e:
            logger.error(f"Training pipeline error: {e}")

    background_tasks.add_task(_train)
    return {"message": f"Training started for {ticker} in background", "ticker": ticker}


@router.get("/compare/{ticker}")
async def compare_model_predictions(ticker: str, period: str = "1y"):
    """Compare all trained models on test data."""
    ticker = ticker.upper()
    df = yahoo.fetch_ohlcv(ticker, period=period)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")

    df = clean_data(df)
    df = engineer_features(df)
    feature_cols = get_feature_columns(df, exclude_targets=True)
    df_norm, _ = normalize_features(df, feature_cols, fit=True)

    X = df_norm[feature_cols].fillna(0).values
    y = df["target_1d"].fillna(0).values
    split = int(len(X) * 0.8)
    X_test, y_test = X[split:], y[split:]

    if len(X_test) < 10:
        raise HTTPException(status_code=400, detail="Insufficient test data")

    results = compare_models(ticker, X_test, y_test)
    return {"ticker": ticker, "model_comparison": results}


@router.get("/timeframes/{ticker}")
async def multi_timeframe_prediction(ticker: str):
    """Generate predictions for 1d, 1w, 1m timeframes."""
    ticker = ticker.upper()
    df = yahoo.fetch_ohlcv(ticker, period="2y")
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")

    df = clean_data(df)
    df = engineer_features(df)
    feature_cols = get_feature_columns(df, exclude_targets=True)
    df_norm, _ = normalize_features(df, feature_cols, fit=True)

    seq_len = settings.sequence_length
    X_flat = df_norm[feature_cols].fillna(0).values[-1:].reshape(1, -1)
    X_seq = df_norm[feature_cols].fillna(0).values[-seq_len:].reshape(1, seq_len, -1) if len(df_norm) >= seq_len else np.zeros((1, seq_len, len(feature_cols)))
    current_price = float(df["close"].iloc[-1])

    result = run_ensemble_prediction(ticker, X_flat, X_seq, len(feature_cols), seq_len, current_price)

    return {
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
