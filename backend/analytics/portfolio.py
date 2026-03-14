"""
Portfolio Simulator
Tracks positions, calculates P&L, VaR, CVaR, beta, Sharpe ratio.
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from data.ingestion import yahoo

logger = logging.getLogger(__name__)


class PortfolioSimulator:
    """Simulates a multi-asset portfolio with risk analytics."""

    def __init__(self, initial_capital: float = 100_000.0):
        self.initial_capital = initial_capital

    def simulate(
        self,
        positions: List[Dict],  # [{"ticker": "AAPL", "weight": 0.3, "shares": None}]
        period: str = "1y",
        rebalance: bool = False,
    ) -> Dict[str, Any]:
        """
        Run portfolio simulation.
        positions: list of {ticker, weight} or {ticker, shares}
        """
        if not positions:
            return {"error": "No positions provided"}

        # Normalize weights
        total_weight = sum(p.get("weight", 1) for p in positions)
        for p in positions:
            p["weight"] = p.get("weight", 1) / max(total_weight, 1e-9)

        # Fetch price data for all tickers
        price_data = {}
        for pos in positions:
            df = yahoo.fetch_ohlcv(pos["ticker"], period=period)
            if not df.empty:
                price_data[pos["ticker"]] = df["close"]

        if not price_data:
            return {"error": "Failed to fetch price data"}

        prices_df = pd.DataFrame(price_data).dropna()
        if prices_df.empty:
            return {"error": "No overlapping price data"}

        # Calculate returns
        returns = prices_df.pct_change().dropna()
        weights = np.array([p["weight"] for p in positions if p["ticker"] in price_data])

        if len(weights) != returns.shape[1]:
            return {"error": "Weight/ticker mismatch"}

        weights = weights / weights.sum()  # Re-normalize to account for missing tickers

        # Portfolio returns
        port_returns = returns.values @ weights
        port_returns_series = pd.Series(port_returns, index=returns.index)

        # Portfolio value over time
        portfolio_values = (1 + port_returns_series).cumprod() * self.initial_capital
        final_value = float(portfolio_values.iloc[-1])
        total_return = (final_value - self.initial_capital) / self.initial_capital

        # ─── Risk Metrics ─────────────────────────────────────────────────────
        # VaR and CVaR (95% & 99%)
        var_95 = self._historical_var(port_returns, confidence=0.95)
        var_99 = self._historical_var(port_returns, confidence=0.99)
        cvar_95 = self._historical_cvar(port_returns, confidence=0.95)
        cvar_99 = self._historical_cvar(port_returns, confidence=0.99)

        # Sharpe & Sortino
        ann_return = float(port_returns_series.mean() * 252)
        ann_vol = float(port_returns_series.std() * np.sqrt(252))
        sharpe = round((ann_return - 0.05) / max(ann_vol, 1e-9), 3)
        downside = port_returns_series[port_returns_series < 0].std() * np.sqrt(252)
        sortino = round((ann_return - 0.05) / max(downside, 1e-9), 3)

        # Beta vs S&P 500
        beta = self._calculate_beta(port_returns_series, period=period)

        # Max Drawdown
        cummax = portfolio_values.cummax()
        drawdown_series = (portfolio_values - cummax) / cummax
        max_dd = float(drawdown_series.min()) * 100

        # Per-position attribution
        position_summary = []
        for pos in positions:
            ticker = pos["ticker"]
            if ticker not in prices_df.columns:
                continue
            ticker_return = (prices_df[ticker].iloc[-1] - prices_df[ticker].iloc[0]) / prices_df[ticker].iloc[0]
            position_summary.append({
                "ticker": ticker,
                "weight": round(float(pos["weight"]) * 100, 2),
                "total_return": round(float(ticker_return) * 100, 2),
                "contribution": round(float(ticker_return * pos["weight"]) * 100, 2),
                "current_price": round(float(prices_df[ticker].iloc[-1]), 2),
                "allocation": round(self.initial_capital * pos["weight"], 2),
            })

        # Correlation matrix
        corr_matrix = returns.corr().round(3)

        # Portfolio value history (downsampled)
        pv = portfolio_values.reset_index()
        pv.columns = ["date", "value"]
        pv["date"] = pv["date"].astype(str)
        pv_hist = pv.to_dict("records")
        step = max(1, len(pv_hist) // 200)

        return {
            "initial_capital": self.initial_capital,
            "final_value": round(final_value, 2),
            "total_return": round(total_return * 100, 2),
            "annualized_return": round(ann_return * 100, 2),
            "annualized_volatility": round(ann_vol * 100, 2),
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": round(max_dd, 2),
            "beta": beta,
            "var_95_daily": round(var_95 * 100, 2),
            "var_99_daily": round(var_99 * 100, 2),
            "cvar_95_daily": round(cvar_95 * 100, 2),
            "cvar_99_daily": round(cvar_99 * 100, 2),
            "num_positions": len(position_summary),
            "positions": position_summary,
            "portfolio_history": pv_hist[::step],
            "correlation_matrix": {
                col: corr_matrix[col].to_dict()
                for col in corr_matrix.columns
            },
        }

    def _historical_var(self, returns: np.ndarray, confidence: float = 0.95) -> float:
        """Historical VaR (daily loss not exceeded at confidence level)."""
        return float(-np.percentile(returns, (1 - confidence) * 100))

    def _historical_cvar(self, returns: np.ndarray, confidence: float = 0.95) -> float:
        """Conditional VaR (expected loss beyond VaR)."""
        var = self._historical_var(returns, confidence)
        losses = -returns[returns < -var]
        return float(losses.mean()) if len(losses) > 0 else var

    def _calculate_beta(self, port_returns: pd.Series, period: str = "1y") -> float:
        """Beta vs S&P 500."""
        try:
            spy = yahoo.fetch_ohlcv("SPY", period=period)
            if spy.empty:
                return 1.0
            spy_returns = spy["close"].pct_change().dropna()
            aligned = pd.concat([port_returns, spy_returns], axis=1).dropna()
            if len(aligned) < 10:
                return 1.0
            cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
            beta = cov[0, 1] / max(cov[1, 1], 1e-9)
            return round(float(beta), 3)
        except Exception:
            return 1.0
