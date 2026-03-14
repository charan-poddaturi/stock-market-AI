"""
Sentiment Analysis Module
Uses VADER (lightweight) by default, FinBERT for deeper analysis.
Aggregates news and social sentiment for a ticker.
"""
import logging
from typing import List, Dict, Optional, Any
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from data.ingestion import news_connector

logger = logging.getLogger(__name__)

# Global VADER analyser
_vader = SentimentIntensityAnalyzer()

# FinBERT loaded lazily to avoid startup delay
_finbert_pipeline = None


def _get_finbert():
    global _finbert_pipeline
    if _finbert_pipeline is None:
        try:
            from transformers import pipeline
            _finbert_pipeline = pipeline(
                "text-classification",
                model="ProsusAI/finbert",
                max_length=512,
                truncation=True,
                top_k=None,
            )
            logger.info("FinBERT loaded successfully")
        except Exception as e:
            logger.warning(f"FinBERT unavailable ({e}), falling back to VADER")
    return _finbert_pipeline


def analyze_text_vader(text: str) -> Dict[str, float]:
    """VADER sentiment — fast, no GPU needed."""
    scores = _vader.polarity_scores(str(text)[:512])
    label = "positive" if scores["compound"] > 0.05 else "negative" if scores["compound"] < -0.05 else "neutral"
    return {
        "label": label,
        "score": round(scores["compound"], 4),
        "positive": round(scores["pos"], 4),
        "negative": round(scores["neg"], 4),
        "neutral": round(scores["neu"], 4),
    }


def analyze_text_finbert(text: str) -> Dict[str, float]:
    """FinBERT sentiment — financial domain trained."""
    pipe = _get_finbert()
    if pipe is None:
        return analyze_text_vader(text)

    try:
        results = pipe(str(text)[:512])
        # results is list of list of dicts
        preds = results[0] if results else []
        label_map = {r["label"].lower(): r["score"] for r in preds}
        dominant = max(label_map, key=label_map.get)
        return {
            "label": dominant,
            "score": round((label_map.get("positive", 0) - label_map.get("negative", 0)), 4),
            "positive": round(label_map.get("positive", 0), 4),
            "negative": round(label_map.get("negative", 0), 4),
            "neutral": round(label_map.get("neutral", 0), 4),
        }
    except Exception as e:
        logger.warning(f"FinBERT inference error: {e}")
        return analyze_text_vader(text)


def analyze_sentiment(
    text: str,
    model: str = "vader",
) -> Dict[str, float]:
    """Unified sentiment analysis interface."""
    if model == "finbert":
        return analyze_text_finbert(text)
    return analyze_text_vader(text)


def fetch_news_sentiment(ticker: str, days_back: int = 7, model: str = "vader") -> Dict[str, Any]:
    """
    Fetch news headlines for a ticker and aggregate sentiment.
    Returns overall sentiment score, per-article analysis, and summary stats.
    """
    headlines = news_connector.fetch_news(ticker, days_back=days_back)

    if not headlines:
        return {
            "ticker": ticker,
            "overall_score": 0.0,
            "label": "neutral",
            "article_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "articles": [],
        }

    articles_with_sentiment = []
    scores = []
    counts = {"positive": 0, "negative": 0, "neutral": 0}

    for article in headlines:
        text = f"{article.get('title', '')} {article.get('description', '')}".strip()
        if not text:
            continue

        sentiment = analyze_sentiment(text, model=model)
        article["sentiment"] = sentiment
        articles_with_sentiment.append(article)
        scores.append(sentiment["score"])
        counts[sentiment["label"]] = counts.get(sentiment["label"], 0) + 1

    overall_score = sum(scores) / len(scores) if scores else 0.0
    overall_label = (
        "positive" if overall_score > 0.05
        else "negative" if overall_score < -0.05
        else "neutral"
    )

    return {
        "ticker": ticker,
        "overall_score": round(overall_score, 4),
        "label": overall_label,
        "article_count": len(articles_with_sentiment),
        "positive_count": counts["positive"],
        "negative_count": counts["negative"],
        "neutral_count": counts["neutral"],
        "articles": articles_with_sentiment[:10],  # Return top 10
    }


def generate_market_mood(
    sentiment_score: float,
    rsi: Optional[float] = None,
    macd_positive: Optional[bool] = None,
    volume_spike: Optional[bool] = None,
    above_sma: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Generate a composite market mood signal combining technical + sentiment.
    Returns mood label, composite score, and narrative.
    """
    score_components = [sentiment_score]
    narrative_parts = []

    # Sentiment contribution
    if sentiment_score > 0.2:
        narrative_parts.append("strongly positive news sentiment")
    elif sentiment_score > 0.05:
        narrative_parts.append("positive market news")
    elif sentiment_score < -0.2:
        narrative_parts.append("negative news sentiment")
    elif sentiment_score < -0.05:
        narrative_parts.append("mixed/negative news")

    # RSI contribution
    if rsi is not None:
        if rsi < 30:
            score_components.append(-0.3)
            narrative_parts.append("oversold RSI conditions (potential reversal)")
        elif rsi > 70:
            score_components.append(0.1)
            narrative_parts.append("overbought RSI (momentum but risk of pullback)")
        elif 45 < rsi < 65:
            score_components.append(0.2)
            narrative_parts.append("healthy RSI momentum")

    # MACD
    if macd_positive is True:
        score_components.append(0.2)
        narrative_parts.append("positive MACD crossover")
    elif macd_positive is False:
        score_components.append(-0.2)
        narrative_parts.append("bearish MACD signal")

    # Volume
    if volume_spike is True:
        score_components.append(0.15)
        narrative_parts.append("significant volume spike confirming move")

    # Price vs MA
    if above_sma is True:
        score_components.append(0.15)
        narrative_parts.append("trading above key moving average")
    elif above_sma is False:
        score_components.append(-0.15)
        narrative_parts.append("trading below key moving average")

    composite = sum(score_components) / len(score_components)
    composite = max(-1.0, min(1.0, composite))

    if composite > 0.3:
        mood = "bullish"
    elif composite > 0.05:
        mood = "mildly_bullish"
    elif composite < -0.3:
        mood = "bearish"
    elif composite < -0.05:
        mood = "mildly_bearish"
    else:
        mood = "neutral"

    narrative = " and ".join(narrative_parts) if narrative_parts else "mixed signals"
    narrative = f"The stock shows {mood.replace('_', ' ')} momentum driven by {narrative}."

    return {
        "mood": mood,
        "composite_score": round(composite, 4),
        "narrative": narrative,
    }
