"""Backtesting Router"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, Tuple
import logging
import asyncio
from data.ingestion import yahoo
from data.pipeline import clean_data, engineer_features
from analytics.backtesting import BacktestEngine
from utils.cache import TTLCache

router = APIRouter()

# Cache backtest results for a short period to prevent expensive reruns
_BACKTEST_CACHE = TTLCache(ttl_seconds=300, maxsize=100)
logger = logging.getLogger(__name__)


class BacktestRequest(BaseModel):
    ticker: str
    strategy: str = "sma_crossover"
    start: Optional[str] = None
    end: Optional[str] = None
    period: str = "2y"
    initial_capital: float = 10000.0
    commission: float = 0.001
    short_window: int = 20
    long_window: int = 50
    strategy_params: Optional[Dict[str, Any]] = None

    def validate(self) -> None:
        """Lightweight runtime validation to keep requests safe and sensible."""
        if not self.ticker or not self.ticker.strip():
            raise HTTPException(status_code=400, detail="Ticker is required")
        if self.initial_capital <= 0:
            raise HTTPException(status_code=400, detail="Initial capital must be positive")
        if not (0 <= self.commission < 0.1):
            raise HTTPException(status_code=400, detail="Commission must be between 0 and 0.1")
        if self.short_window <= 0 or self.long_window <= 0:
            raise HTTPException(status_code=400, detail="Windows must be positive integers")
        if self.short_window >= self.long_window:
            raise HTTPException(status_code=400, detail="Short window must be less than long window")


def _backtest_key(req: BacktestRequest) -> Tuple:
    params = req.strategy_params or {}
    params_tuple = tuple(sorted(params.items()))
    return (
        req.ticker.upper(),
        req.strategy,
        req.period,
        req.start,
        req.end,
        req.initial_capital,
        req.commission,
        req.short_window,
        req.long_window,
        params_tuple,
    )


def _run_backtest_sync(req: BacktestRequest):
    ticker = req.ticker.upper()

    df = yahoo.fetch_ohlcv(ticker, period=req.period, start=req.start, end=req.end)
    if df.empty:
        raise ValueError(f"No data for {ticker}")

    df = clean_data(df)
    df = engineer_features(df)

    engine = BacktestEngine(
        initial_capital=req.initial_capital,
        commission=req.commission,
    )

    result = engine.run(
        df=df,
        strategy=req.strategy,
        strategy_params=req.strategy_params,
        short_window=req.short_window,
        long_window=req.long_window,
    )

    if "error" in result:
        raise ValueError(result["error"])

    result["ticker"] = ticker
    result["strategy"] = req.strategy
    return result


@router.post("/")
async def run_backtest(req: BacktestRequest):
    """Run a full backtesting simulation."""
    # Runtime validation to guard against obviously bad or dangerous inputs
    req.validate()
    cache_key = _backtest_key(req)
    cached = _BACKTEST_CACHE.get(cache_key)
    if cached is not None:
        return cached

    try:
        result = await asyncio.to_thread(_run_backtest_sync, req)
    except ValueError as e:
        # User/input-related issues should surface as 400 with a clear message
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Avoid leaking internal error details to clients
        logger.exception("Backtest execution failed")
        raise HTTPException(status_code=500, detail="Backtest failed")

    _BACKTEST_CACHE.set(cache_key, result)
    return result


@router.get("/strategies")
async def list_strategies():
    """List available backtesting strategies."""
    return {
        "strategies": [
            {"id": "sma_crossover", "name": "SMA Crossover", "description": "Buy when short MA crosses above long MA"},
            {"id": "rsi_mean_reversion", "name": "RSI Mean Reversion", "description": "Buy oversold (RSI<30), Sell overbought (RSI>70)"},
            {"id": "bollinger_breakout", "name": "Bollinger Breakout", "description": "Trade breakouts from Bollinger Bands"},
            {"id": "macd", "name": "MACD Signal", "description": "Trade MACD line crossovers"},
            {"id": "buy_and_hold", "name": "Buy & Hold", "description": "Baseline buy and hold strategy"},
        ]
    }
