"""
Data Pipeline: Cleaning, Feature Engineering, Normalization
Generates 30+ technical indicators for ML training.
"""
import pandas as pd
import numpy as np
import logging
from typing import Tuple, Optional
from sklearn.preprocessing import MinMaxScaler, StandardScaler
import joblib
import os

logger = logging.getLogger(__name__)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicates, fill gaps, handle outliers."""
    if df.empty:
        return df

    df = df.copy()
    df = df[~df.index.duplicated(keep="last")]
    df = df.sort_index()

    # Forward fill then backward fill small gaps
    df = df.ffill().bfill()

    # Remove extreme outliers via IQR on returns
    if "close" in df.columns and len(df) > 10:
        returns = df["close"].pct_change().dropna()
        q1, q3 = returns.quantile(0.01), returns.quantile(0.99)
        iqr = q3 - q1
        mask = (returns >= q1 - 3 * iqr) & (returns <= q3 + 3 * iqr)
        df = df[mask.reindex(df.index, fill_value=True)]

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Generate comprehensive technical indicator set."""
    if df.empty or len(df) < 30:
        return df

    df = df.copy()
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    open_ = df["open"]

    # ── Trend Indicators ─────────────────────────────────────────────────────
    df["sma_5"] = close.rolling(5).mean()
    df["sma_10"] = close.rolling(10).mean()
    df["sma_20"] = close.rolling(20).mean()
    df["sma_50"] = close.rolling(50).mean()
    df["sma_200"] = close.rolling(200).mean()
    df["ema_9"] = close.ewm(span=9, adjust=False).mean()
    df["ema_12"] = close.ewm(span=12, adjust=False).mean()
    df["ema_26"] = close.ewm(span=26, adjust=False).mean()
    df["ema_50"] = close.ewm(span=50, adjust=False).mean()

    # Price position relative to MAs
    df["price_vs_sma20"] = (close - df["sma_20"]) / df["sma_20"]
    df["price_vs_sma50"] = (close - df["sma_50"]) / df["sma_50"]
    df["sma20_vs_sma50"] = (df["sma_20"] - df["sma_50"]) / df["sma_50"]

    # ── Momentum Indicators ───────────────────────────────────────────────────
    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # RSI divergence from 50
    df["rsi_signal"] = df["rsi_14"] - 50

    # MACD
    df["macd"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    df["macd_cross"] = np.where(df["macd"] > df["macd_signal"], 1, -1)

    # Stochastic Oscillator
    low_14 = low.rolling(14).min()
    high_14 = high.rolling(14).max()
    df["stoch_k"] = 100 * (close - low_14) / (high_14 - low_14 + 1e-9)
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    # Williams %R
    df["williams_r"] = -100 * (high_14 - close) / (high_14 - low_14 + 1e-9)

    # ROC
    df["roc_5"] = close.pct_change(5) * 100
    df["roc_10"] = close.pct_change(10) * 100
    df["roc_21"] = close.pct_change(21) * 100

    # CCI
    typical_price = (high + low + close) / 3
    sma_tp = typical_price.rolling(20).mean()
    mad = typical_price.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean())
    df["cci"] = (typical_price - sma_tp) / (0.015 * mad + 1e-9)

    # ── Volatility Indicators ─────────────────────────────────────────────────
    # Bollinger Bands
    bb_sma = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df["bb_upper"] = bb_sma + 2 * bb_std
    df["bb_lower"] = bb_sma - 2 * bb_std
    df["bb_middle"] = bb_sma
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / (bb_sma + 1e-9)
    df["bb_pct"] = (close - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-9)

    # ATR
    tr = pd.DataFrame({
        "hl": high - low,
        "hc": (high - close.shift()).abs(),
        "lc": (low - close.shift()).abs(),
    }).max(axis=1)
    df["atr_14"] = tr.rolling(14).mean()
    df["atr_pct"] = df["atr_14"] / close

    # Historical Volatility
    log_ret = np.log(close / close.shift(1))
    df["volatility_10"] = log_ret.rolling(10).std() * np.sqrt(252)
    df["volatility_21"] = log_ret.rolling(21).std() * np.sqrt(252)

    # ── Volume Indicators ─────────────────────────────────────────────────────
    # VWAP (approximated daily)
    df["vwap"] = (close * volume).rolling(20).sum() / volume.rolling(20).sum()
    df["price_vs_vwap"] = (close - df["vwap"]) / (df["vwap"] + 1e-9)

    # OBV
    obv = volume.copy()
    obv[close.diff() < 0] *= -1
    df["obv"] = obv.cumsum()
    df["obv_signal"] = df["obv"].ewm(span=9).mean()

    # Volume ratio
    df["volume_sma20"] = volume.rolling(20).mean()
    df["volume_ratio"] = volume / (df["volume_sma20"] + 1e-9)

    # ── Price Features ────────────────────────────────────────────────────────
    df["candle_body"] = (close - open_).abs()
    df["candle_range"] = high - low
    df["candle_body_ratio"] = df["candle_body"] / (df["candle_range"] + 1e-9)
    df["upper_shadow"] = high - pd.concat([close, open_], axis=1).max(axis=1)
    df["lower_shadow"] = pd.concat([close, open_], axis=1).min(axis=1) - low

    # Log returns
    df["log_return"] = np.log(close / close.shift(1))
    df["return_1d"] = close.pct_change(1)
    df["return_5d"] = close.pct_change(5)
    df["return_21d"] = close.pct_change(21)

    # ── Lag Features ──────────────────────────────────────────────────────────
    for lag in [1, 2, 3, 5, 10, 21]:
        df[f"close_lag{lag}"] = close.shift(lag)
        df[f"return_lag{lag}"] = df["log_return"].shift(lag)

    # Rolling statistics
    for window in [5, 10, 21]:
        df[f"rolling_mean_{window}"] = close.rolling(window).mean()
        df[f"rolling_std_{window}"] = close.rolling(window).std()
        df[f"rolling_max_{window}"] = close.rolling(window).max()
        df[f"rolling_min_{window}"] = close.rolling(window).min()

    # ── Target Variable ───────────────────────────────────────────────────────
    df["target_1d"] = (close.shift(-1) > close).astype(int)   # Next day direction
    df["target_return_1d"] = close.pct_change(1).shift(-1)    # Next day return
    df["future_close_1d"] = close.shift(-1)                   # Next day price
    df["future_close_5d"] = close.shift(-5)                   # 5-day future close
    df["future_close_21d"] = close.shift(-21)                 # 21-day future close

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["close", "rsi_14", "macd"])

    logger.info(f"Feature engineering complete: {df.shape[1]} features, {len(df)} rows")
    return df


def get_feature_columns(df: pd.DataFrame, exclude_targets: bool = True) -> list:
    """Return list of feature column names."""
    base_cols = ["open", "high", "low", "close", "volume"]
    target_cols = [c for c in df.columns if c.startswith("target_") or c.startswith("future_")]

    feature_cols = [
        c for c in df.columns
        if c not in base_cols and (not exclude_targets or c not in target_cols)
    ]
    return feature_cols


def normalize_features(
    df: pd.DataFrame,
    feature_cols: list,
    scaler_type: str = "standard",
    scaler_path: Optional[str] = None,
    fit: bool = True,
) -> Tuple[pd.DataFrame, object]:
    """Normalize features using StandardScaler or MinMaxScaler."""
    df = df.copy()

    if scaler_type == "minmax":
        scaler = MinMaxScaler()
    else:
        scaler = StandardScaler()

    if scaler_path and os.path.exists(scaler_path) and not fit:
        scaler = joblib.load(scaler_path)
        df[feature_cols] = scaler.transform(df[feature_cols].fillna(0))
    else:
        df[feature_cols] = scaler.fit_transform(df[feature_cols].fillna(0))
        if scaler_path:
            os.makedirs(os.path.dirname(scaler_path), exist_ok=True)
            joblib.dump(scaler, scaler_path)

    return df, scaler


def prepare_sequences(
    df: pd.DataFrame,
    feature_cols: list,
    target_col: str = "target_1d",
    sequence_length: int = 60,
) -> Tuple[np.ndarray, np.ndarray]:
    """Create LSTM/GRU ready (X, y) sequence arrays."""
    X, y = [], []
    data = df[feature_cols].values
    targets = df[target_col].values

    for i in range(sequence_length, len(data) - 1):
        X.append(data[i - sequence_length:i])
        y.append(targets[i])

    return np.array(X), np.array(y)
