"""AI Market Insights Router — generates natural language market narratives using Google Gemini."""
from fastapi import APIRouter, HTTPException
import json
import logging
import asyncio
from data.ingestion import yahoo
from data.pipeline import clean_data, engineer_features
from data.sentiment import fetch_news_sentiment, generate_market_mood
from analytics.patterns import get_pattern_signals
from config import settings
from utils.cache import TTLCache

# Initialize Gemini Client
try:
    from google import genai
    from google.genai import types
    if settings.gemini_api_key and settings.gemini_api_key != "demo":
        gemini_client = genai.Client(api_key=settings.gemini_api_key)
    else:
        gemini_client = None
except ImportError:
    gemini_client = None

logger = logging.getLogger(__name__)
router = APIRouter()

# Cache AI insights per ticker to avoid repeated LLM calls
_INSIGHTS_CACHE = TTLCache(ttl_seconds=300, maxsize=200)


def _generate_gemini_narrative(
    ticker: str,
    name: str,
    fundamentals: dict,
    latest_metrics: dict,
    mood_data: dict,
    patterns: list,
    news: list
) -> str:
    """Uses Gemini Pro to write a dynamic market narrative based on live data."""
    if not gemini_client:
        return _fallback_narrative(ticker, name, latest_metrics, mood_data)

    context = f"""
You are an elite quantitative researcher and AI financial analyst.
Write a highly professional, expert-level market narrative for the following stock based on the provided live metrics.
Make it sound like a premium Bloomberg Terminal or Quant Research report.
Keep it strictly under 150 words. Do not use generic filler.
Use Markdown to **bold** key insights or numbers.

STOCK: {name} ({ticker})
SECTOR: {fundamentals.get('sector', 'Unknown')}
CURRENT PRICE: ${latest_metrics['close']:.2f}
RSI (14): {latest_metrics['rsi_14']:.1f}
MACD: {latest_metrics['macd']:.3f}
VOLUME RATIO: {latest_metrics['volume_ratio']:.1f}x average
1-MONTH RETURN: {latest_metrics['price_change_pct']:.1f}%

RECENT PATTERNS:
{json.dumps([p['pattern'] for p in patterns[:3]])}

RECENT NEWS HEADLINES:
{json.dumps([n['title'] for n in news[:3]])}

OVERALL SENTIMENT MOOD: {mood_data['mood']}
"""
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=context,
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return _fallback_narrative(ticker, name, latest_metrics, mood_data)


def _fallback_narrative(ticker: str, name: str, m: dict, mood: dict) -> str:
    """Fallback if Gemini API key is missing or fails."""
    parts = []
    if m['close'] > m['sma50']:
        parts.append(f"{name} is in an **uptrend**, trading above its 50-day moving average (${m['sma50']:.2f})")
    else:
        parts.append(f"{name} is trading **below** its 50-day moving average (${m['sma50']:.2f}), indicating a downtrend")

    if m['price_change_pct'] > 0:
        parts.append(f"with a recent gain of **+{m['price_change_pct']:.1f}%**")
    elif m['price_change_pct'] < 0:
        parts.append(f"with a recent decline of **{m['price_change_pct']:.1f}%**")

    if m['rsi_14'] > 70:
        parts.append(f"RSI is **overbought at {m['rsi_14']:.0f}**")
    elif m['rsi_14'] < 30:
        parts.append(f"RSI is **oversold at {m['rsi_14']:.0f}**")

    mood_label = mood.get("mood", "neutral").replace("_", " ")
    parts.append(f"Overall market mood: **{mood_label}**")

    return ". ".join(parts) + "."


def _build_insights(ticker: str):
    """Build insights payload (blocking)."""
    df = yahoo.fetch_ohlcv(ticker, period="6mo")
    if df.empty:
        raise ValueError(f"No data for {ticker}")

    df = clean_data(df)
    df = engineer_features(df)
    fundamentals = yahoo.fetch_fundamentals(ticker)
    # News sentiment can occasionally fail in third-party libs; fall back gracefully
    try:
        sentiment = fetch_news_sentiment(ticker, days_back=7)
    except Exception as e:
        logger.error(f"News sentiment error for {ticker}: {e}")
        sentiment = {
            "ticker": ticker,
            "overall_score": 0.0,
            "label": "neutral",
            "article_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "articles": [],
        }
    patterns = get_pattern_signals(df)

    # df.empty is already checked above, so iloc[-1] is always valid here
    latest = df.iloc[-1]
    close = float(latest.get("close", 0.0))
    
    if len(df) > 22:
        prev_close = float(df["close"].iloc[-22])
    elif len(df) > 1:
        prev_close = float(df["close"].iloc[0])
    else:
        prev_close = close
            
    price_change_pct = ((close - prev_close) / prev_close) * 100 if prev_close else 0.0

    import pandas as pd
    rsi = float(latest.get("rsi_14", 50)) if pd.notna(latest.get("rsi_14")) else 50.0
    macd_val = latest.get("macd", 0)
    macd_pos = float(macd_val) > 0 if pd.notna(macd_val) else False
    
    vol_ratio = latest.get("volume_ratio", 1)
    vol_spike = float(vol_ratio) > 2 if pd.notna(vol_ratio) else False
    
    sma_20 = latest.get("sma_20", close)
    above_sma = close > float(sma_20) if pd.notna(sma_20) else True

    try:
        mood = generate_market_mood(
            sentiment["overall_score"],
            rsi=rsi,
            macd_positive=macd_pos,
            volume_spike=vol_spike,
            above_sma=above_sma,
        )
    except Exception as e:
        logger.error(f"Market mood generation error for {ticker}: {e}")
        mood = {
            "mood": "neutral",
            "composite_score": 0.0,
            "narrative": "Mixed signals with neutral overall mood.",
        }

    name = fundamentals.get("shortName") or fundamentals.get("longName") or ticker
    
    sma_50 = latest.get("sma_50", close)
    bb_pct = latest.get("bb_pct", 0.5)
    vol_21 = latest.get("volatility_21", 0)
    
    latest_metrics = {
        "close": close,
        "sma50": float(sma_50) if pd.notna(sma_50) else float(close),
        "rsi_14": rsi,
        "macd": float(macd_val) if pd.notna(macd_val) else 0.0,
        "volume_ratio": float(vol_ratio) if pd.notna(vol_ratio) else 1.0,
        "price_change_pct": price_change_pct,
    }

    # Generate LLM Narrative
    narrative = _generate_gemini_narrative(
        ticker, name, fundamentals, latest_metrics, 
        mood, patterns, sentiment.get("articles", [])
    )

    # Key metrics summary for UI
    key_metrics = {
        "current_price": round(close, 2),
        "rsi_14": round(rsi, 1),
        "macd_positive": macd_pos,
        "volume_ratio": round(float(vol_ratio) if pd.notna(vol_ratio) else 1.0, 2),
        "bb_position": round(float(bb_pct) if pd.notna(bb_pct) else 0.5, 3),
        "volatility": round(float(vol_21) if pd.notna(vol_21) else 0.0 * 100, 2),
        "month_return": round(price_change_pct, 2),
    }

    return {
        "ticker": ticker,
        "name": name,
        "sector": fundamentals.get("sector", "Sector N/A"),
        "narrative": narrative,
        "mood": mood,
        "sentiment": {
            "score": sentiment.get("overall_score", 0.0),
            "label": sentiment.get("label", "neutral"),
            "article_count": sentiment.get("article_count", 0),
        },
        "patterns": patterns[:5],
        "key_metrics": key_metrics,
        "analyst": {
            "rating": fundamentals.get("recommendationKey", "N/A"),
            "target_price": fundamentals.get("targetMeanPrice"),
            "pe_ratio": fundamentals.get("trailingPE"),
        },
        "news": sentiment.get("articles", [])[:5],
    }


def _empty_insights(ticker: str) -> dict:
    """Fallback payload when insights generation fails, so UI still works."""
    return {
        "ticker": ticker,
        "name": ticker,
        "sector": "Sector N/A",
        "narrative": "We could not generate a detailed AI insight right now, but market data is available in the Stock Explorer.",
        "mood": {
            "mood": "neutral",
            "composite_score": 0.0,
            "narrative": "Mixed signals with neutral overall mood.",
        },
        "sentiment": {
            "score": 0.0,
            "label": "neutral",
            "article_count": 0,
        },
        "patterns": [],
        "key_metrics": {
            "current_price": 0.0,
            "rsi_14": 50.0,
            "macd_positive": False,
            "volume_ratio": 1.0,
            "bb_position": 0.5,
            "volatility": 0.0,
            "month_return": 0.0,
        },
        "analyst": {
            "rating": "N/A",
            "target_price": None,
            "pe_ratio": None,
        },
        "news": [],
    }


@router.get("/{ticker}")
async def get_ai_insights(ticker: str):
    """Generate comprehensive AI-powered market narrative."""
    ticker = ticker.upper()
    cache_key = (ticker,)
    cached = _INSIGHTS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    try:
        result = await asyncio.to_thread(_build_insights, ticker)
    except Exception:
        logger.exception("Insights generation error, returning fallback insights")
        result = _empty_insights(ticker)

    _INSIGHTS_CACHE.set(cache_key, result)
    return result
