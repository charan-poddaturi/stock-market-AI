"""
Stock Screener: Filter stocks by technical, fundamental, and sentiment criteria.
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from data.ingestion import yahoo
from data.pipeline import engineer_features, clean_data
from data.sentiment import fetch_news_sentiment

logger = logging.getLogger(__name__)

# Commonly watched stocks for screening
DEFAULT_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "NFLX",
    "AMD", "INTC", "BABA", "JPM", "BAC", "GS", "MS", "WMT", "PG",
    "JNJ", "UNH", "CVX", "XOM", "V", "MA", "PYPL", "DIS", "NKE",
    "UBER", "LYFT", "SNAP", "TWTR", "CRM", "ORCL", "ADBE", "SAP",
]


import concurrent.futures

class StockScreener:
    def screen(
        self,
        filters: Dict[str, Any],
        universe: Optional[List[str]] = None,
        period: str = "3mo",
    ) -> List[Dict[str, Any]]:
        """
        Apply filters to universe of stocks concurrently.
        """
        tickers = universe or DEFAULT_UNIVERSE
        results = []

        def _screen_ticker(ticker):
            try:
                df = yahoo.fetch_ohlcv(ticker, period=period, interval="1d")
                if df.empty or len(df) < 30:
                    return None

                df = clean_data(df)
                df = engineer_features(df)
                if df.empty:
                    return None

                latest = df.iloc[-1]
                passed, metrics = self._apply_filters(latest, df, filters)

                if passed:
                    fundamentals = yahoo.fetch_fundamentals(ticker)
                    return {
                        "ticker": ticker,
                        "name": fundamentals.get("shortName") or fundamentals.get("longName") or ticker,
                        "sector": fundamentals.get("sector", "N/A"),
                        "score": self._compute_score(latest, metrics),
                        **metrics,
                    }
            except Exception as e:
                logger.debug(f"Screener skip {ticker}: {e}")
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(_screen_ticker, t) for t in tickers]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    results.append(res)

        # Sort by composite score
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results

    def _apply_filters(
        self, latest: pd.Series, df: pd.DataFrame, filters: Dict
    ) -> tuple:
        """Apply all filters; return (passed, metrics_dict)."""
        metrics = {}

        # Extract metrics
        rsi = float(latest.get("rsi_14", 50))
        volume = float(latest.get("volume", 0))
        vol_ratio = float(latest.get("volume_ratio", 1))
        close = float(latest.get("close", 0))
        sma20 = float(latest.get("sma_20", close))
        sma50 = float(latest.get("sma_50", close))
        macd = float(latest.get("macd", 0))
        bb_pct = float(latest.get("bb_pct", 0.5))
        month_return = float(df["close"].pct_change(21).iloc[-1]) * 100 if len(df) > 21 else 0

        metrics = {
            "rsi": round(rsi, 1),
            "close": round(close, 2),
            "volume": int(volume),
            "volume_ratio": round(vol_ratio, 2),
            "macd_positive": macd > 0,
            "above_sma20": close > sma20,
            "above_sma50": close > sma50,
            "return_1m": round(month_return, 2),
            "bb_pct": round(bb_pct, 3),
        }

        # Apply filters
        if "rsi_max" in filters and rsi > filters["rsi_max"]:
            return False, metrics
        if "rsi_min" in filters and rsi < filters["rsi_min"]:
            return False, metrics
        if "min_volume" in filters and volume < filters["min_volume"]:
            return False, metrics
        if "volume_ratio_min" in filters and vol_ratio < filters["volume_ratio_min"]:
            return False, metrics
        if "price_min" in filters and close < filters["price_min"]:
            return False, metrics
        if "price_max" in filters and close > filters["price_max"]:
            return False, metrics
        if "min_return_1m" in filters and month_return < filters["min_return_1m"]:
            return False, metrics
        if "max_return_1m" in filters and month_return > filters["max_return_1m"]:
            return False, metrics
        if filters.get("above_sma20") and close < sma20:
            return False, metrics
        if filters.get("above_sma50") and close < sma50:
            return False, metrics
        if filters.get("macd_positive") and macd <= 0:
            return False, metrics

        return True, metrics

    def _compute_score(self, latest: pd.Series, metrics: Dict) -> float:
        """Composite ranking score for screened stocks."""
        score = 0.0
        rsi = metrics.get("rsi", 50)
        vol_ratio = metrics.get("volume_ratio", 1)
        ret = metrics.get("return_1m", 0)

        # RSI near oversold = opportunity
        if 25 < rsi < 40:
            score += (40 - rsi) * 0.5
        elif rsi < 25:
            score += 7.5

        # Volume spike
        if vol_ratio > 2:
            score += min(vol_ratio * 2, 10)

        # Positive momentum
        if ret > 0:
            score += min(ret * 0.5, 5)

        # Above MAs
        if metrics.get("above_sma20"):
            score += 2
        if metrics.get("above_sma50"):
            score += 3

        # Positive MACD
        if metrics.get("macd_positive"):
            score += 2

        return round(score, 2)
