"""
Candlestick Pattern Detection
Detects common patterns: Doji, Hammer, Engulfing, Morning/Evening Star, etc.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any


def detect_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect common candlestick patterns.
    Adds boolean columns for each pattern to the dataframe.
    """
    if df.empty or len(df) < 3:
        return df

    result = df.copy()
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    body = (c - o).abs()
    body_top = pd.concat([o, c], axis=1).max(axis=1)
    body_bot = pd.concat([o, c], axis=1).min(axis=1)
    upper_shadow = h - body_top
    lower_shadow = body_bot - l
    candle_range = h - l
    is_bullish = c > o
    is_bearish = c < o

    # ── Doji ─────────────────────────────────────────────────────────────────
    result["doji"] = (body / candle_range.replace(0, np.nan)) < 0.1

    # ── Hammer (bullish reversal) ────────────────────────────────────────────
    result["hammer"] = (
        (lower_shadow >= 2 * body) &
        (upper_shadow < body * 0.5) &
        (body > 0)
    )

    # ── Inverted Hammer ───────────────────────────────────────────────────────
    result["inverted_hammer"] = (
        (upper_shadow >= 2 * body) &
        (lower_shadow < body * 0.5) &
        (body > 0)
    )

    # ── Bullish Engulfing ────────────────────────────────────────────────────
    prev_is_bearish = is_bearish.shift(1)
    result["bullish_engulfing"] = (
        is_bullish &
        prev_is_bearish &
        (c > o.shift(1)) &
        (o < c.shift(1))
    )

    # ── Bearish Engulfing ────────────────────────────────────────────────────
    prev_is_bullish = is_bullish.shift(1)
    result["bearish_engulfing"] = (
        is_bearish &
        prev_is_bullish &
        (o > c.shift(1)) &
        (c < o.shift(1))
    )

    # ── Morning Star (3-candle bullish) ─────────────────────────────────────
    result["morning_star"] = (
        is_bearish.shift(2) &
        (body.shift(1) < body.shift(2) * 0.3) &
        is_bullish &
        (c > (o.shift(2) + c.shift(2)) / 2)
    )

    # ── Evening Star (3-candle bearish) ──────────────────────────────────────
    result["evening_star"] = (
        is_bullish.shift(2) &
        (body.shift(1) < body.shift(2) * 0.3) &
        is_bearish &
        (c < (o.shift(2) + c.shift(2)) / 2)
    )

    # ── Shooting Star (bearish reversal) ─────────────────────────────────────
    result["shooting_star"] = (
        (upper_shadow >= 2 * body) &
        (lower_shadow < body * 0.3) &
        is_bearish
    )

    # ── Three White Soldiers (strong bullish) ────────────────────────────────
    result["three_white_soldiers"] = (
        is_bullish & is_bullish.shift(1) & is_bullish.shift(2) &
        (c > c.shift(1)) & (c.shift(1) > c.shift(2)) &
        (o < c.shift(1)) & (o.shift(1) < c.shift(2))
    )

    # ── Three Black Crows (strong bearish) ───────────────────────────────────
    result["three_black_crows"] = (
        is_bearish & is_bearish.shift(1) & is_bearish.shift(2) &
        (c < c.shift(1)) & (c.shift(1) < c.shift(2))
    )

    return result


def get_pattern_signals(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Return list of detected patterns with dates and descriptions."""
    df_with_patterns = detect_patterns(df)

    pattern_info = {
        "doji": {"description": "Doji — indecision, potential reversal", "sentiment": "neutral"},
        "hammer": {"description": "Hammer — bullish reversal after downtrend", "sentiment": "bullish"},
        "inverted_hammer": {"description": "Inverted Hammer — potential bullish reversal", "sentiment": "bullish"},
        "bullish_engulfing": {"description": "Bullish Engulfing — strong bullish reversal", "sentiment": "bullish"},
        "bearish_engulfing": {"description": "Bearish Engulfing — strong bearish reversal", "sentiment": "bearish"},
        "morning_star": {"description": "Morning Star — strong bullish reversal", "sentiment": "bullish"},
        "evening_star": {"description": "Evening Star — strong bearish reversal", "sentiment": "bearish"},
        "shooting_star": {"description": "Shooting Star — bearish reversal at resistance", "sentiment": "bearish"},
        "three_white_soldiers": {"description": "Three White Soldiers — strong bullish trend", "sentiment": "bullish"},
        "three_black_crows": {"description": "Three Black Crows — strong bearish trend", "sentiment": "bearish"},
    }

    signals = []
    pattern_cols = list(pattern_info.keys())

    for i in range(len(df_with_patterns) - 1, max(len(df_with_patterns) - 30, -1), -1):
        row = df_with_patterns.iloc[i]
        date = str(df_with_patterns.index[i].date() if hasattr(df_with_patterns.index[i], "date") else df_with_patterns.index[i])
        for col in pattern_cols:
            if col in row.index and bool(row[col]):
                info = pattern_info[col]
                signals.append({
                    "date": date,
                    "pattern": col,
                    "description": info["description"],
                    "sentiment": info["sentiment"],
                    "close": round(float(row.get("close", 0)), 2),
                })

    return signals[:20]  # Return most recent 20 signals


def get_support_resistance(df: pd.DataFrame, window: int = 20) -> Dict[str, list]:
    """Calculate support and resistance levels."""
    if len(df) < window:
        return {"support": [], "resistance": []}

    close = df["close"]
    high = df["high"]
    low = df["low"]

    # Pivot points
    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)

    latest_pivot = float(pivot.iloc[-1])
    return {
        "pivot": round(latest_pivot, 2),
        "resistance": [round(float(r1.iloc[-1]), 2), round(float(r2.iloc[-1]), 2)],
        "support": [round(float(s1.iloc[-1]), 2), round(float(s2.iloc[-1]), 2)],
    }
