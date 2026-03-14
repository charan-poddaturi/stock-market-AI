"""
Stocks Router: OHLCV data, indicators, fundamentals, market indices.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import pandas as pd
from data.ingestion import yahoo
from data.pipeline import clean_data, engineer_features
from data.sentiment import fetch_news_sentiment
from analytics.patterns import detect_patterns, get_pattern_signals, get_support_resistance
from analytics.correlation import compute_correlation_matrix
from ml.anomaly import IsolationForestDetector

router = APIRouter()
_anomaly = IsolationForestDetector()


@router.get("/{ticker}")
async def get_stock_data(
    ticker: str,
    period: str = Query("1y", description="Data period: 1mo, 3mo, 6mo, 1y, 2y, 5y"),
    interval: str = Query("1d", description="Data interval: 1d, 1h, 5m"),
    include_indicators: bool = Query(True),
):
    """Fetch OHLCV data with technical indicators."""
    ticker = ticker.upper()
    df = yahoo.fetch_ohlcv(ticker, period=period, interval=interval)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    df = clean_data(df)
    if include_indicators and len(df) >= 30:
        try:
            df = engineer_features(df)
            # Keep only key columns for API response
            keep_cols = [
                "open", "high", "low", "close", "volume",
                "sma_20", "sma_50", "ema_12", "ema_26",
                "rsi_14", "macd", "macd_signal", "macd_hist",
                "bb_upper", "bb_lower", "bb_middle", "bb_pct", "bb_width",
                "atr_14", "atr_pct", "vwap", "volume_ratio",
                "volatility_21", "stoch_k", "stoch_d",
            ]
            cols_present = [c for c in keep_cols if c in df.columns]
            df = df[cols_present]
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error engineering features: {e}")
            # Proceed with raw data if indicators fail

    # Convert to list of records
    df = df.round(4)
    df = df.fillna(0.0)
    df.index = df.index.strftime("%Y-%m-%d %H:%M" if interval != "1d" else "%Y-%m-%d")

    return {
        "ticker": ticker,
        "period": period,
        "interval": interval,
        "data_points": len(df),
        "data": df.reset_index().rename(columns={"index": "date"}).to_dict("records"),
    }


@router.get("/{ticker}/fundamentals")
async def get_fundamentals(ticker: str):
    """Get company fundamentals and info."""
    ticker = ticker.upper()
    info = yahoo.fetch_fundamentals(ticker)
    if not info:
        raise HTTPException(status_code=404, detail=f"Fundamentals not found for {ticker}")
    return {"ticker": ticker, **info}


@router.get("/{ticker}/options")
async def get_options(ticker: str):
    """Get options chain summary."""
    ticker = ticker.upper()
    data = yahoo.fetch_options_data(ticker)
    return {"ticker": ticker, **data}


@router.get("/{ticker}/patterns")
async def get_patterns(
    ticker: str,
    period: str = Query("3mo"),
):
    """Detect candlestick patterns."""
    ticker = ticker.upper()
    df = yahoo.fetch_ohlcv(ticker, period=period)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")
    df = clean_data(df)
    signals = get_pattern_signals(df)
    sr = get_support_resistance(df)
    return {"ticker": ticker, "patterns": signals, "support_resistance": sr}


@router.get("/{ticker}/anomalies")
async def get_anomalies(ticker: str, period: str = Query("1y")):
    """Detect anomalous market behavior."""
    ticker = ticker.upper()
    df = yahoo.fetch_ohlcv(ticker, period=period)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")
    df = clean_data(df)
    df = engineer_features(df)
    return _anomaly.get_anomaly_summary(df, ticker)


@router.get("/indices/overview")
async def get_market_indices():
    """Fetch major market indices."""
    return yahoo.fetch_market_indices()


@router.post("/correlation")
async def correlation_heatmap(
    tickers: list[str],
    period: str = "1y",
):
    """Compute correlation matrix for a list of tickers."""
    if len(tickers) < 2 or len(tickers) > 20:
        raise HTTPException(status_code=400, detail="Provide 2-20 tickers")
    return compute_correlation_matrix(tickers, period=period)


@router.get("/search/{query}")
async def search_stocks(query: str, limit: int = Query(10, le=20)):
    """Search for stock tickers."""
    results = yahoo.search_tickers(query, limit=limit)
    return {"query": query, "results": results}
