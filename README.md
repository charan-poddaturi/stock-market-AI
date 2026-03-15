# 🚀 AI Stock Market Analysis & Prediction Platform

A next-generation financial intelligence platform combining **ML/DL forecasting**, **NLP sentiment analysis**, **backtesting**, **portfolio simulation**, and an elite modern UI — built with FastAPI, Next.js, and PyTorch.

---

## ✨ Features

| Module | Description |
|--------|-------------|
| 📊 Dashboard | Live market overview, watchlist, AI signal feed |
| 🔍 Stock Explorer | Candlestick charts, 30+ technical indicators, multi-TF predictions |
| 🤖 Prediction Panel | LSTM/XGBoost/Ensemble forecasts with SHAP explainability |
| 🧪 Strategy Lab | Full backtesting engine with Sharpe, Sortino, drawdown metrics |
| 💼 Portfolio Simulator | Capital allocation, VaR/CVaR, performance analytics |
| 🧠 AI Insights | FinBERT sentiment, news feed, AI narrative generation |
| 🔎 Stock Screener | RSI < 30, volume spike, positive sentiment filters |
| 📡 Anomaly Detection | Isolation Forest + Autoencoder for unusual market behavior |

---

## 🛠 Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, asyncpg
- **ML/DL**: PyTorch, Scikit-learn, XGBoost, LightGBM
- **NLP**: Transformers (FinBERT), VADER Sentiment
- **Database**: PostgreSQL 15, Redis 7
- **Frontend**: Next.js 14, TailwindCSS, Plotly.js
- **Infrastructure**: Docker Compose

---

## ⚡ Quick Start

### Option A: Docker (Recommended)
```bash
# 1. Copy environment file
cp .env.example .env

# 2. Launch all services
docker-compose up -d

# 3. Open the app
open http://localhost:3000
open http://localhost:8000/docs   # Swagger API docs
```

### Option B: Manual Setup

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate          
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Database (requires PostgreSQL running locally):**
```bash
psql -U postgres -c "CREATE DATABASE stockai;"
psql -U stockai -d stockai -f backend/db/schema.sql
```

---

## ⚙️ Performance & Caching (Recommended)

This project is tuned for speed:
- **Async endpoints** and **thread offloading** keep the API responsive even under load.
- **Model caching** keeps ML models and scalers in memory across requests.
- **Redis cache** (included in Docker) accelerates repeated calls (stock data, predictions, backtests, screener results).

To maximize performance:
1. Run the backend with multiple workers in production:
   ```bash
   cd backend
   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   ```
2. Build and run the frontend in production mode:
   ```bash
   cd frontend
   npm install
   npm run build
   npm run start
   ```
3. Keep the `models/saved` directory mounted (Docker does this via `model_cache`) so trained models and scalers are reused.
4. Use `docker-compose` for a production-like startup (Redis + Postgres pre-configured for caching and persistence).

Minimal smoke checks after startup:
- Visit `http://localhost:3000` and exercise:
  - Dashboard tiles and AI Opportunities
  - Stock Explorer for several tickers/periods
  - Prediction Panel (Predict, Train, Compare, Multi-TF)
  - Strategy Lab backtests
  - Portfolio Simulator runs
  - AI Insights narratives
- Confirm `http://localhost:8000/health` returns a healthy status and `http://localhost:8000/docs` loads without errors.

---

## �📁 Project Structure

```
├── backend/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings / environment
│   ├── database.py          # DB connection
│   ├── data/                # Data ingestion & pipeline
│   ├── ml/                  # ML/DL models
│   ├── analytics/           # Backtesting, portfolio, screener
│   ├── routers/             # API route handlers
│   ├── models/              # SQLAlchemy ORM models
│   └── db/schema.sql        # Database schema
├── frontend/
│   ├── src/app/             # Next.js 14 app router pages
│   ├── src/components/      # Reusable UI components
│   └── src/lib/             # API client, utilities
├── docker-compose.yml
└── .env.example
```

---

## 🔑 API Keys (All Optional)

The platform works **100% without API keys** using Yahoo Finance.  
For premium data, add keys to `.env`:

| Key | Source | Free Tier |
|-----|--------|-----------|
| `ALPHA_VANTAGE_KEY` | [alphavantage.co](https://alphavantage.co) | 25 req/day |
| `POLYGON_KEY` | [polygon.io](https://polygon.io) | 5 req/min |
| `NEWS_API_KEY` | [newsapi.org](https://newsapi.org) | 100 req/day |

**Global Market Support:**  
This platform supports stocks from multiple exchanges worldwide via Yahoo Finance.  
- **US (NASDAQ/NYSE):** Use standard tickers (e.g., `AAPL`, `GOOGL`).  
- **India (NSE/BSE):** Append `.NS` or `.BO` (e.g., `RELIANCE.NS`, `TCS.BO`).  
- **Other regions:** Check Yahoo Finance for ticker formats (e.g., `.L` for London, `.TO` for Toronto).  
No code changes needed — just enter the correct ticker in the UI or API calls.

---

## 📖 API Documentation

Once running, visit **http://localhost:8000/docs** for the full interactive Swagger UI.

Key endpoints:
- `GET /stocks/{ticker}` — OHLCV + indicators
- `POST /predict` — Ensemble ML predictions
- `GET /sentiment/{ticker}` — News sentiment score
- `POST /backtest` — Strategy backtesting
- `POST /screen` — Stock screener
- `GET /insights/{ticker}` — AI market narrative
