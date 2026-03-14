"""
Anomaly Detection: Isolation Forest + LSTM Autoencoder
Detects abnormal price/volume behavior in market data.
"""
import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from sklearn.ensemble import IsolationForest
import joblib

logger = logging.getLogger(__name__)
MODEL_DIR = "models/saved"


class IsolationForestDetector:
    """Detects anomalies using Isolation Forest."""

    def __init__(self, contamination: float = 0.05, n_estimators: int = 100):
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42,
            n_jobs=-1,
        )
        self.feature_cols = ["close", "volume", "return_1d", "rsi_14", "atr_pct", "volume_ratio"]

    def fit(self, df: pd.DataFrame, ticker: str) -> None:
        available = [c for c in self.feature_cols if c in df.columns]
        X = df[available].fillna(0).values
        self.model.fit(X)
        path = os.path.join(MODEL_DIR, f"{ticker}_isolation_forest.pkl")
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump((self.model, available), path)
        logger.info(f"Isolation Forest fitted for {ticker}")

    def detect(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        path = os.path.join(MODEL_DIR, f"{ticker}_isolation_forest.pkl")
        if os.path.exists(path):
            self.model, feature_cols = joblib.load(path)
        else:
            feature_cols = [c for c in self.feature_cols if c in df.columns]
            self.model.fit(df[feature_cols].fillna(0).values)

        X = df[[c for c in feature_cols if c in df.columns]].fillna(0).values
        scores = self.model.decision_function(X)
        labels = self.model.predict(X)  # -1 = anomaly, 1 = normal

        result = df.copy()
        result["anomaly_score"] = -scores  # Higher = more anomalous
        result["is_anomaly"] = labels == -1
        return result

    def get_anomaly_summary(self, df: pd.DataFrame, ticker: str) -> Dict[str, Any]:
        detected = self.detect(df, ticker)
        anomalies = detected[detected["is_anomaly"]].copy()

        events = []
        for idx, row in anomalies.iterrows():
            event_type = "unknown"
            details = ""
            if "volume_ratio" in row and row.get("volume_ratio", 1) > 3:
                event_type = "volume_spike"
                details = f"Volume {row['volume_ratio']:.1f}x above average"
            elif "return_1d" in row and abs(row.get("return_1d", 0)) > 0.05:
                ret = row["return_1d"] * 100
                event_type = "price_move"
                details = f"Unusual {ret:+.1f}% daily return"
            elif "rsi_14" in row and (row.get("rsi_14", 50) > 80 or row.get("rsi_14", 50) < 20):
                event_type = "extreme_rsi"
                details = f"RSI at extreme: {row['rsi_14']:.1f}"

            events.append({
                "date": str(idx.date() if hasattr(idx, "date") else idx),
                "type": event_type,
                "details": details,
                "anomaly_score": round(float(row.get("anomaly_score", 0)), 4),
                "close": round(float(row.get("close", 0)), 2),
                "volume": int(row.get("volume", 0)),
            })

        return {
            "ticker": ticker,
            "total_periods": len(detected),
            "anomalies_found": len(anomalies),
            "anomaly_rate": round(len(anomalies) / max(len(detected), 1), 4),
            "events": sorted(events, key=lambda x: x["anomaly_score"], reverse=True)[:20],
        }


class AutoencoderDetector:
    """LSTM Autoencoder for reconstruction-error-based anomaly detection."""

    def __init__(self, seq_len: int = 10, threshold_percentile: float = 95.0):
        self.seq_len = seq_len
        self.threshold_percentile = threshold_percentile
        self.threshold = None
        self.model = None

    def _build_autoencoder(self, input_size: int):
        import torch.nn as nn

        class LSTMAutoencoder(nn.Module):
            def __init__(self, input_size, hidden_size=32):
                super().__init__()
                self.encoder = nn.LSTM(input_size, hidden_size, batch_first=True)
                self.decoder = nn.LSTM(hidden_size, input_size, batch_first=True)

            def forward(self, x):
                _, (h, _) = self.encoder(x)
                h_expanded = h.permute(1, 0, 2).expand(-1, x.size(1), -1)
                out, _ = self.decoder(h_expanded)
                return out

        return LSTMAutoencoder(input_size)

    def detect_simple(self, df: pd.DataFrame) -> pd.DataFrame:
        """Simple statistical anomaly detection without neural network."""
        cols = ["close", "volume"]
        available = [c for c in cols if c in df.columns]
        result = df.copy()
        scores = np.zeros(len(df))

        for col in available:
            vals = df[col].values.astype(float)
            mean, std = np.nanmean(vals), np.nanstd(vals)
            z_scores = np.abs((vals - mean) / (std + 1e-9))
            scores += z_scores

        result["anomaly_score"] = scores / len(available)
        threshold = np.percentile(scores, self.threshold_percentile)
        result["is_anomaly"] = scores > threshold
        return result
