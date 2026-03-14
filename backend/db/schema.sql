-- StockAI Platform Database Schema

CREATE TABLE IF NOT EXISTS stocks (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(200),
    sector VARCHAR(100),
    industry VARCHAR(100),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stock_prices (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4),
    volume BIGINT,
    UNIQUE(ticker, date)
);

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    model VARCHAR(50),
    predicted_direction VARCHAR(10),
    probability_up DECIMAL(6,4),
    confidence_score DECIMAL(6,4),
    price_target_1d DECIMAL(12,4),
    price_target_5d DECIMAL(12,4),
    price_target_30d DECIMAL(12,4),
    signal VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS portfolios (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    initial_capital DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    strategy VARCHAR(50),
    total_return DECIMAL(10,4),
    sharpe_ratio DECIMAL(8,4),
    sortino_ratio DECIMAL(8,4),
    max_drawdown DECIMAL(8,4),
    win_rate DECIMAL(6,4),
    profit_factor DECIMAL(8,4),
    num_trades INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sentiment_data (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    sentiment_score DECIMAL(6,4),
    label VARCHAR(20),
    article_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stock_prices_ticker ON stock_prices(ticker);
CREATE INDEX IF NOT EXISTS idx_predictions_ticker ON predictions(ticker, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_ticker ON sentiment_data(ticker, created_at DESC);
