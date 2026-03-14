from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(200))
    sector = Column(String(100))
    industry = Column(String(100))
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

class StockPrice(Base):
    __tablename__ = "stock_prices"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True, nullable=False)
    date = Column(DateTime, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True, nullable=False)
    model = Column(String(50))
    predicted_direction = Column(String(10))
    probability_up = Column(Float)
    confidence_score = Column(Float)
    price_target_1d = Column(Float)
    price_target_5d = Column(Float)
    price_target_30d = Column(Float)
    signal = Column(String(20))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    initial_capital = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class BacktestResult(Base):
    __tablename__ = "backtest_results"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20))
    strategy = Column(String(50))
    total_return = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    num_trades = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SentimentData(Base):
    __tablename__ = "sentiment_data"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True)
    sentiment_score = Column(Float)
    label = Column(String(20))
    article_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
