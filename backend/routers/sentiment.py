"""Sentiment Router"""
from fastapi import APIRouter, Query, HTTPException
from data.sentiment import fetch_news_sentiment, generate_market_mood
from data.ingestion import yahoo
from data.pipeline import clean_data, engineer_features

router = APIRouter()


@router.get("/{ticker}")
async def get_sentiment(
    ticker: str,
    days_back: int = Query(7, ge=1, le=30),
    model: str = Query("vader", description="vader or finbert"),
):
    """Get news sentiment analysis for a ticker."""
    ticker = ticker.upper()
    result = fetch_news_sentiment(ticker, days_back=days_back, model=model)

    # Add technical context to mood
    try:
        df = yahoo.fetch_ohlcv(ticker, period="3mo")
        df = clean_data(df)
        df = engineer_features(df)
        if not df.empty:
            last = df.iloc[-1]
            rsi = float(last.get("rsi_14", 50))
            macd_pos = float(last.get("macd", 0)) > 0
            vol_spike = float(last.get("volume_ratio", 1)) > 2
            above_sma = float(last.get("close", 0)) > float(last.get("sma_20", last.get("close", 0)))
            mood = generate_market_mood(
                result["overall_score"], rsi=rsi, macd_positive=macd_pos,
                volume_spike=vol_spike, above_sma=above_sma,
            )
            result["market_mood"] = mood
    except Exception:
        result["market_mood"] = None

    return result
