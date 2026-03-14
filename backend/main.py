from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os

from config import settings

# ─── Routers ─────────────────────────────────────────────────────────────────
from routers import stocks, predictions, sentiment, portfolio, backtesting, screener, insights

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown."""
    logger.info("🚀 StockAI Platform starting up...")

    # Ensure model cache dir exists
    os.makedirs(settings.model_cache_dir, exist_ok=True)

    # Redis ping
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        logger.info("✅ Redis connected")
        await r.aclose()
    except Exception as e:
        logger.warning(f"⚠️  Redis unavailable: {e} — caching disabled")

    # DB init
    try:
        from database import engine, Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.warning(f"⚠️  Database unavailable: {e} — running without persistence")

    logger.info("✅ StockAI Platform ready!")
    yield
    logger.info("👋 StockAI Platform shutting down...")


# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="StockAI Platform API",
    description="Next-generation AI-powered Stock Market Analysis & Prediction Platform",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register Routers ─────────────────────────────────────────────────────────
app.include_router(stocks.router, prefix="/stocks", tags=["📈 Market Data"])
app.include_router(predictions.router, prefix="/predict", tags=["🤖 Predictions"])
app.include_router(sentiment.router, prefix="/sentiment", tags=["🧠 Sentiment"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["💼 Portfolio"])
app.include_router(backtesting.router, prefix="/backtest", tags=["🧪 Backtesting"])
app.include_router(screener.router, prefix="/screen", tags=["🔍 Screener"])
app.include_router(insights.router, prefix="/insights", tags=["💡 AI Insights"])


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "version": settings.app_version, "env": settings.environment}


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "StockAI Platform API",
        "docs": "/docs",
        "version": settings.app_version,
    }
