"""
Backtesting Engine
Simulates trading strategies on historical OHLCV data.
Calculates Sharpe, Sortino, Max Drawdown, Win Rate, Profit Factor, CAGR.
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Full backtesting simulator with portfolio tracking and strategy execution."""

    def __init__(self, initial_capital: float = 10000.0, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission  # 0.1% per trade

    def run(
        self,
        df: pd.DataFrame,
        strategy: str = "sma_crossover",
        strategy_params: Optional[Dict] = None,
        short_window: int = 20,
        long_window: int = 50,
    ) -> Dict[str, Any]:
        """Execute a backtest and return full results."""
        if df.empty or len(df) < max(short_window, long_window) + 5:
            return {"error": "Insufficient data for backtesting"}

        params = strategy_params or {}
        signals = self._generate_signals(df, strategy, short_window, long_window, params)
        return self._calculate_metrics(df, signals)

    def _generate_signals(
        self,
        df: pd.DataFrame,
        strategy: str,
        short_window: int,
        long_window: int,
        params: Dict,
    ) -> pd.Series:
        """Generate buy/sell/hold signals (1=buy, -1=sell, 0=hold)."""
        signals = pd.Series(0, index=df.index)
        close = df["close"]

        if strategy == "sma_crossover":
            sma_short = close.rolling(short_window).mean()
            sma_long = close.rolling(long_window).mean()
            signals[sma_short > sma_long] = 1
            signals[sma_short < sma_long] = -1

        elif strategy == "rsi_mean_reversion":
            rsi = params.get("rsi", df.get("rsi_14", close.rolling(14).mean()))
            oversold = params.get("oversold", 30)
            overbought = params.get("overbought", 70)
            if isinstance(rsi, pd.Series):
                signals[rsi < oversold] = 1
                signals[rsi > overbought] = -1

        elif strategy == "bollinger_breakout":
            sma = close.rolling(20).mean()
            std = close.rolling(20).std()
            upper = sma + 2 * std
            lower = sma - 2 * std
            signals[close > upper] = 1
            signals[close < lower] = -1

        elif strategy == "macd":
            ema12 = close.ewm(span=12).mean()
            ema26 = close.ewm(span=26).mean()
            macd = ema12 - ema26
            signal_line = macd.ewm(span=9).mean()
            signals[macd > signal_line] = 1
            signals[macd < signal_line] = -1

        elif strategy == "buy_and_hold":
            signals[:] = 1

        return signals

    def _calculate_metrics(
        self, df: pd.DataFrame, signals: pd.Series
    ) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""
        capital = self.initial_capital
        position = 0  # shares held
        prev_signal = 0
        portfolio_values = []
        trades = []
        entry_price = 0.0

        for i, (date, row) in enumerate(df.iterrows()):
            price = float(row["close"])
            signal = int(signals.iloc[i])

            # Trade execution
            if signal != prev_signal:
                if signal == 1 and position == 0:  # Buy
                    shares = (capital * (1 - self.commission)) / price
                    position = shares
                    capital = 0
                    entry_price = price
                    trades.append({"date": str(date), "action": "buy", "price": price, "shares": shares})

                elif signal != 1 and position > 0:  # Sell
                    proceeds = position * price * (1 - self.commission)
                    pnl = proceeds - (position * entry_price)
                    capital = proceeds
                    trades.append({
                        "date": str(date), "action": "sell", "price": price,
                        "pnl": round(pnl, 2), "pnl_pct": round((pnl / (position * entry_price)) * 100, 2)
                    })
                    position = 0

            prev_signal = signal
            # Portfolio value
            portfolio_value = capital + position * price
            portfolio_values.append({"date": str(date.date() if hasattr(date, "date") else date), "value": round(portfolio_value, 2)})

        # Final liquidation
        if position > 0:
            final_price = float(df["close"].iloc[-1])
            capital += position * final_price * (1 - self.commission)

        final_value = capital
        portfolio_series = pd.Series([p["value"] for p in portfolio_values])

        # ─── Metrics ─────────────────────────────────────────────────────────
        total_return = (final_value - self.initial_capital) / self.initial_capital
        n_days = len(df)
        n_years = n_days / 252
        cagr = (final_value / self.initial_capital) ** (1 / max(n_years, 0.01)) - 1

        daily_returns = portfolio_series.pct_change().dropna()
        sharpe = self._sharpe_ratio(daily_returns)
        sortino = self._sortino_ratio(daily_returns)
        max_dd = self._max_drawdown(portfolio_series)

        # Win rate
        sell_trades = [t for t in trades if t.get("action") == "sell"]
        wins = sum(1 for t in sell_trades if t.get("pnl", 0) > 0)
        win_rate = wins / max(len(sell_trades), 1)

        # Profit factor
        gross_profit = sum(t.get("pnl", 0) for t in sell_trades if t.get("pnl", 0) > 0)
        gross_loss = abs(sum(t.get("pnl", 0) for t in sell_trades if t.get("pnl", 0) < 0))
        profit_factor = gross_profit / max(gross_loss, 0.01)

        # Buy & hold comparison
        bh_return = (float(df["close"].iloc[-1]) - float(df["close"].iloc[0])) / float(df["close"].iloc[0])

        return {
            "initial_capital": self.initial_capital,
            "final_value": round(final_value, 2),
            "total_return": round(total_return * 100, 2),
            "total_return_pct": f"{total_return*100:+.2f}%",
            "cagr": round(cagr * 100, 2),
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": round(max_dd * 100, 2),
            "win_rate": round(win_rate * 100, 2),
            "profit_factor": round(profit_factor, 3),
            "num_trades": len(sell_trades),
            "buy_hold_return": round(bh_return * 100, 2),
            "alpha": round((total_return - bh_return) * 100, 2),
            "portfolio_history": portfolio_values[::max(1, len(portfolio_values)//200)],  # Downsample
            "trades": trades[-50:],  # Last 50 trades
        }

    @staticmethod
    def _sharpe_ratio(daily_returns: pd.Series, risk_free: float = 0.05) -> float:
        excess = daily_returns - risk_free / 252
        if daily_returns.std() == 0:
            return 0.0
        return round(float(excess.mean() / daily_returns.std() * np.sqrt(252)), 3)

    @staticmethod
    def _sortino_ratio(daily_returns: pd.Series, risk_free: float = 0.05) -> float:
        excess = daily_returns - risk_free / 252
        downside = daily_returns[daily_returns < 0].std()
        if downside == 0:
            return 0.0
        return round(float(excess.mean() / downside * np.sqrt(252)), 3)

    @staticmethod
    def _max_drawdown(portfolio_series: pd.Series) -> float:
        if len(portfolio_series) < 2:
            return 0.0
        cummax = portfolio_series.cummax()
        drawdown = (portfolio_series - cummax) / cummax
        return float(drawdown.min())
