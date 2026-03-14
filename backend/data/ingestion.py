"""
Data Ingestion Module
Fetches OHLCV, fundamentals, and macroeconomic data from multiple sources.
Primary: Yahoo Finance (free)
Optional: Alpha Vantage, Polygon (require API keys)
"""
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from config import settings
import concurrent.futures
from functools import lru_cache

logger = logging.getLogger(__name__)


class YahooFinanceConnector:
    """Primary data source — free, no API key required."""

    @staticmethod
    def fetch_ohlcv(
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        try:
            stock = yf.Ticker(ticker)
            if start and end:
                df = stock.history(start=start, end=end, interval=interval)
            else:
                df = stock.history(period=period, interval=interval)

            if df.empty:
                logger.warning(f"No data returned for {ticker}")
                return pd.DataFrame()

            df.index = pd.to_datetime(df.index)
            df.index = df.index.tz_localize(None)
            df.columns = [c.lower() for c in df.columns]
            df = df[["open", "high", "low", "close", "volume"]]
            df = df.dropna()
            logger.info(f"Fetched {len(df)} rows for {ticker} [{interval}]")
            return df
        except Exception as e:
            logger.error(f"Error fetching {ticker}: {e}")
            return pd.DataFrame()

    @staticmethod
    @lru_cache(maxsize=200)
    def fetch_fundamentals(ticker: str) -> Dict[str, Any]:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            keys = [
                "shortName", "longName", "sector", "industry", "country",
                "marketCap", "trailingPE", "forwardPE", "priceToBook",
                "dividendYield", "beta", "52WeekChange", "fiftyTwoWeekHigh",
                "fiftyTwoWeekLow", "averageVolume", "earningsGrowth",
                "revenueGrowth", "profitMargins", "currentPrice",
                "targetMeanPrice", "recommendationMean", "recommendationKey",
            ]
            return {k: info.get(k) for k in keys}
        except Exception as e:
            logger.error(f"Fundamentals error for {ticker}: {e}")
            return {}

    @staticmethod
    def fetch_options_data(ticker: str) -> Dict[str, Any]:
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options
            if not expirations:
                return {}
            # Fetch nearest expiry
            chain = stock.option_chain(expirations[0])
            calls_summary = {
                "total_open_interest": int(chain.calls["openInterest"].sum()),
                "total_volume": int(chain.calls["volume"].sum()),
                "avg_iv": float(chain.calls["impliedVolatility"].mean()),
            }
            puts_summary = {
                "total_open_interest": int(chain.puts["openInterest"].sum()),
                "total_volume": int(chain.puts["volume"].sum()),
                "avg_iv": float(chain.puts["impliedVolatility"].mean()),
            }
            put_call_ratio = (
                puts_summary["total_open_interest"] / max(calls_summary["total_open_interest"], 1)
            )
            return {
                "expirations": list(expirations[:5]),
                "nearest_expiry": expirations[0],
                "calls": calls_summary,
                "puts": puts_summary,
                "put_call_ratio": round(put_call_ratio, 3),
            }
        except Exception as e:
            logger.error(f"Options error for {ticker}: {e}")
            return {}

    @staticmethod
    def search_tickers(query: str, limit: int = 10) -> List[Dict]:
        """Search for tickers using yfinance."""
        try:
            results = yf.Search(query, max_results=limit)
            quotes = results.quotes
            return [
                {
                    "symbol": q.get("symbol", ""),
                    "name": q.get("shortname", q.get("longname", "")),
                    "exchange": q.get("exchange", ""),
                    "type": q.get("quoteType", ""),
                }
                for q in quotes
                if q.get("symbol")
            ]
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    @staticmethod
    def fetch_market_indices() -> Dict[str, Any]:
        """Fetch major market indices concurrently."""
        indices = {
            "S&P 500": "^GSPC",
            "NASDAQ": "^IXIC",
            "Dow Jones": "^DJI",
            "VIX": "^VIX",
            "Gold": "GC=F",
            "Crude Oil": "CL=F",
            "10Y Treasury": "^TNX",
        }
        
        def _fetch_one(name, ticker):
            try:
                data = yf.Ticker(ticker).history(period="2d")
                if len(data) >= 2:
                    curr = float(data["Close"].iloc[-1])
                    prev = float(data["Close"].iloc[-2])
                    change = curr - prev
                    change_pct = (change / prev) * 100
                    return name, {
                        "value": round(curr, 2),
                        "change": round(change, 2),
                        "change_pct": round(change_pct, 3),
                    }
            except Exception:
                pass
            return name, None

        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_fetch_one, n, t) for n, t in indices.items()]
            for future in concurrent.futures.as_completed(futures):
                name, data = future.result()
                if data:
                    results[name] = data
        return results


class AlphaVantageConnector:
    """Optional premium data source."""
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.alpha_vantage_key
        self.enabled = self.api_key and self.api_key != "demo"

    def fetch_intraday(self, ticker: str, interval: str = "5min") -> pd.DataFrame:
        if not self.enabled:
            return pd.DataFrame()
        try:
            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": ticker,
                "interval": interval,
                "outputsize": "compact",
                "apikey": self.api_key,
            }
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            data = resp.json()
            key = f"Time Series ({interval})"
            if key not in data:
                return pd.DataFrame()
            df = pd.DataFrame(data[key]).T
            df.index = pd.to_datetime(df.index)
            df.columns = ["open", "high", "low", "close", "volume"]
            df = df.astype(float)
            return df.sort_index()
        except Exception as e:
            logger.error(f"Alpha Vantage error: {e}")
            return pd.DataFrame()


class PolygonConnector:
    """Polygon.io real-time data connector."""
    BASE_URL = "https://api.polygon.io"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.polygon_key
        self.enabled = bool(self.api_key and self.api_key not in ("demo", None))

    def fetch_snapshot(self, ticker: str) -> Dict[str, Any]:
        """Fetch real-time snapshot (last trade, OHLCV, prev close) from Polygon."""
        if not self.enabled:
            return {}
        try:
            url = f"{self.BASE_URL}/v2/snapshot/locale/us/markets/stocks/tickers/{ticker.upper()}"
            resp = requests.get(url, params={"apiKey": self.api_key}, timeout=10)
            data = resp.json()
            if data.get("status") != "OK":
                logger.warning(f"Polygon snapshot error for {ticker}: {data.get('error', '')}")
                return {}
            ticker_data = data.get("ticker", {})
            day = ticker_data.get("day", {})
            prev = ticker_data.get("prevDay", {})
            last_trade = ticker_data.get("lastTrade", {})
            return {
                "open": day.get("o"),
                "high": day.get("h"),
                "low": day.get("l"),
                "close": day.get("c"),
                "volume": day.get("v"),
                "vwap": day.get("vw"),
                "prev_close": prev.get("c"),
                "last_price": last_trade.get("p"),
                "change": ticker_data.get("todaysChange"),
                "change_pct": ticker_data.get("todaysChangePerc"),
                "source": "polygon",
            }
        except Exception as e:
            logger.error(f"Polygon snapshot error for {ticker}: {e}")
            return {}

    def fetch_previous_close(self, ticker: str) -> Dict[str, Any]:
        """Get previous day OHLCV from Polygon."""
        if not self.enabled:
            return {}
        try:
            url = f"{self.BASE_URL}/v2/aggs/ticker/{ticker.upper()}/prev"
            resp = requests.get(url, params={"adjusted": "true", "apiKey": self.api_key}, timeout=10)
            data = resp.json()
            if data.get("resultsCount", 0) == 0:
                return {}
            result = data["results"][0]
            return {
                "open": result.get("o"),
                "high": result.get("h"),
                "low": result.get("l"),
                "close": result.get("c"),
                "volume": result.get("v"),
                "vwap": result.get("vw"),
                "source": "polygon",
            }
        except Exception as e:
            logger.error(f"Polygon prev close error for {ticker}: {e}")
            return {}


class NewsConnector:
    """Fetches financial news headlines."""
    NEWSAPI_URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.news_api_key
        self.enabled = self.api_key and self.api_key != "demo"

    def fetch_news(self, ticker: str, days_back: int = 7) -> List[Dict]:
        headlines = []
        # Try NewsAPI
        if self.enabled:
            try:
                from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
                params = {
                    "q": ticker,
                    "from": from_date,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "apiKey": self.api_key,
                    "pageSize": 20,
                }
                resp = requests.get(self.NEWSAPI_URL, params=params, timeout=10)
                data = resp.json()
                articles = data.get("articles", [])
                headlines = [
                    {
                        "title": a.get("title", ""),
                        "description": a.get("description", ""),
                        "url": a.get("url", ""),
                        "published_at": a.get("publishedAt", ""),
                        "source": a.get("source", {}).get("name", ""),
                    }
                    for a in articles
                    if a.get("title")
                ]
            except Exception as e:
                logger.error(f"NewsAPI error: {e}")

        # Fallback: Yahoo Finance news
        if not headlines:
            try:
                stock = yf.Ticker(ticker)
                news = stock.news or []
                headlines = [
                    {
                        "title": n.get("content", {}).get("title", ""),
                        "description": n.get("content", {}).get("summary", ""),
                        "url": n.get("content", {}).get("canonicalUrl", {}).get("url", ""),
                        "published_at": datetime.fromtimestamp(
                            n.get("content", {}).get("pubDate", 0) or 0
                        ).isoformat(),
                        "source": n.get("content", {}).get("provider", {}).get("displayName", "Yahoo Finance"),
                    }
                    for n in news[:20]
                    if n.get("content", {}).get("title")
                ]
            except Exception as e:
                logger.error(f"Yahoo news error: {e}")

        return headlines


# ─── Singleton connectors ────────────────────────────────────────────────────
yahoo = YahooFinanceConnector()
alphavantage = AlphaVantageConnector()
polygon = PolygonConnector()
news_connector = NewsConnector()
