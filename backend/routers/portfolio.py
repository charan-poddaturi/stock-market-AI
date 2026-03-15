"""Portfolio Router"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Tuple
import asyncio
from analytics.portfolio import PortfolioSimulator
from utils.cache import TTLCache

router = APIRouter()

# Cache portfolio simulation results for short-lived response caching
_PORTFOLIO_CACHE = TTLCache(ttl_seconds=120, maxsize=200)


class Position(BaseModel):
    ticker: str
    weight: float = 1.0


class PortfolioRequest(BaseModel):
    positions: List[Position]
    initial_capital: float = 100000.0
    period: str = "1y"


def _portfolio_key(req: PortfolioRequest) -> Tuple:
    positions = tuple(sorted([(p.ticker.upper(), p.weight) for p in req.positions]))
    return (positions, req.initial_capital, req.period)


def _run_portfolio_sync(req: PortfolioRequest):
    sim = PortfolioSimulator(initial_capital=req.initial_capital)
    result = sim.simulate(
        positions=[{"ticker": p.ticker.upper(), "weight": p.weight} for p in req.positions],
        period=req.period,
    )
    return result


@router.post("/simulate")
async def simulate_portfolio(req: PortfolioRequest):
    """Run portfolio simulation with risk metrics."""
    if not req.positions:
        raise HTTPException(status_code=400, detail="No positions provided")

    cache_key = _portfolio_key(req)
    cached = _PORTFOLIO_CACHE.get(cache_key)
    if cached is not None:
        return cached

    result = await asyncio.to_thread(_run_portfolio_sync, req)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    _PORTFOLIO_CACHE.set(cache_key, result)
    return result


@router.get("/presets")
async def get_preset_portfolios():
    """Return common portfolio presets."""
    return {
        "presets": [
            {
                "name": "Tech Giants",
                "positions": [
                    {"ticker": "AAPL", "weight": 0.25},
                    {"ticker": "MSFT", "weight": 0.25},
                    {"ticker": "NVDA", "weight": 0.20},
                    {"ticker": "GOOGL", "weight": 0.15},
                    {"ticker": "META", "weight": 0.15},
                ],
            },
            {
                "name": "Balanced Growth",
                "positions": [
                    {"ticker": "SPY", "weight": 0.40},
                    {"ticker": "QQQ", "weight": 0.20},
                    {"ticker": "GLD", "weight": 0.15},
                    {"ticker": "TLT", "weight": 0.15},
                    {"ticker": "VNQ", "weight": 0.10},
                ],
            },
            {
                "name": "Warren Buffett Style",
                "positions": [
                    {"ticker": "KO", "weight": 0.20},
                    {"ticker": "BAC", "weight": 0.20},
                    {"ticker": "AXP", "weight": 0.15},
                    {"ticker": "AAPL", "weight": 0.25},
                    {"ticker": "OXY", "weight": 0.20},
                ],
            },
        ]
    }
