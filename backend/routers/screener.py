"""Screener Router"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from analytics.screener import StockScreener

router = APIRouter()
_screener = StockScreener()


class ScreenerRequest(BaseModel):
    filters: Dict[str, Any] = {}
    universe: Optional[List[str]] = None
    period: str = "3mo"


@router.post("/")
async def screen_stocks(req: ScreenerRequest):
    """Screen stocks based on technical and fundamental filters."""
    results = _screener.screen(
        filters=req.filters,
        universe=req.universe,
        period=req.period,
    )
    return {
        "count": len(results),
        "filters_applied": req.filters,
        "results": results,
    }


@router.get("/presets")
async def screener_presets():
    """Common screener filter presets."""
    return {
        "presets": [
            {
                "name": "Oversold Bounce",
                "description": "Stocks with RSI < 30 — potential reversal candidates",
                "filters": {"rsi_max": 30, "min_volume": 500000},
            },
            {
                "name": "Momentum Leaders",
                "description": "Stocks above MAs with high volume",
                "filters": {"above_sma20": True, "above_sma50": True, "volume_ratio_min": 1.5, "min_return_1m": 5},
            },
            {
                "name": "MACD Breakout",
                "description": "Bullish MACD crossovers",
                "filters": {"macd_positive": True, "above_sma20": True, "min_volume": 1000000},
            },
            {
                "name": "Value Plays",
                "description": "Pulling back to support — RSI 35-50 range",
                "filters": {"rsi_min": 35, "rsi_max": 50, "above_sma50": True},
            },
        ]
    }
