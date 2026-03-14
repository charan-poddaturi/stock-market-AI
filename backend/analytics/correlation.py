"""
Correlation and Explainability analytics.
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List, Optional
from data.ingestion import yahoo

logger = logging.getLogger(__name__)


def compute_correlation_matrix(
    tickers: List[str],
    period: str = "1y",
    return_type: str = "log",
) -> Dict[str, Any]:
    """Compute pairwise return correlations for a list of stocks."""
    price_data = {}
    for ticker in tickers:
        try:
            df = yahoo.fetch_ohlcv(ticker, period=period)
            if not df.empty:
                price_data[ticker] = df["close"]
        except Exception as e:
            logger.warning(f"Skip {ticker}: {e}")

    if len(price_data) < 2:
        return {"error": "Need at least 2 valid tickers"}

    prices = pd.DataFrame(price_data).dropna()
    if return_type == "log":
        returns = np.log(prices / prices.shift(1)).dropna()
    else:
        returns = prices.pct_change().dropna()

    corr = returns.corr().round(3)
    tickers_found = list(corr.columns)

    return {
        "tickers": tickers_found,
        "correlation_matrix": corr.values.tolist(),
        "labels": tickers_found,
        "period": period,
    }
