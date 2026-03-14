"""Backtesting Router"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from data.ingestion import yahoo
from data.pipeline import clean_data, engineer_features
from analytics.backtesting import BacktestEngine

router = APIRouter()


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


@router.post("/")
async def run_backtest(req: BacktestRequest):
    """Run a full backtesting simulation."""
    ticker = req.ticker.upper()

    df = yahoo.fetch_ohlcv(ticker, period=req.period, start=req.start, end=req.end)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")

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
        raise HTTPException(status_code=400, detail=result["error"])

    result["ticker"] = ticker
    result["strategy"] = req.strategy
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
