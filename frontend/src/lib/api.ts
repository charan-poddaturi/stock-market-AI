import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  timeout: 60000, // 60s for slow ML endpoints
  headers: { 'Content-Type': 'application/json' },
});

// ─── Stock Data ───────────────────────────────────────────────────────────────
export const fetchStockData = (ticker: string, period = '1y', interval = '1d', indicators = true) =>
  api.get(`/stocks/${ticker}`, { params: { period, interval, include_indicators: indicators } }).then(r => r.data);

export const fetchFundamentals = (ticker: string) =>
  api.get(`/stocks/${ticker}/fundamentals`).then(r => r.data);

export const fetchOptions = (ticker: string) =>
  api.get(`/stocks/${ticker}/options`).then(r => r.data);

export const fetchPatterns = (ticker: string, period = '3mo') =>
  api.get(`/stocks/${ticker}/patterns`, { params: { period } }).then(r => r.data);

export const fetchAnomalies = (ticker: string, period = '1y') =>
  api.get(`/stocks/${ticker}/anomalies`, { params: { period } }).then(r => r.data);

export const fetchMarketIndices = () =>
  api.get('/stocks/indices/overview').then(r => r.data);

export const fetchCorrelation = (tickers: string[], period = '1y') =>
  api.post('/stocks/correlation', { tickers }, { params: { period } }).then(r => r.data);

export const searchStocks = (query: string) =>
  api.get(`/stocks/search/${query}`).then(r => r.data);

export const resolveTicker = async (input: string) => {
  const query = input.trim();
  if (!query) return '';
  // Search if it contains a space or is longer than 5 chars (likely a company name)
  if (query.includes(' ') || query.length > 5) {
    try {
      const res = await searchStocks(query);
      if (res.results && res.results.length > 0) {
        return res.results[0].symbol;
      }
    } catch (e) {
      console.warn('Auto-resolve failed', e);
    }
  }
  return query.toUpperCase();
};

// ─── Predictions ──────────────────────────────────────────────────────────────
export const runPrediction = (ticker: string, model = 'ensemble', period = '2y', retrain = false) =>
  api.post('/predict/', { ticker, model, period, retrain }).then(r => r.data);

export const trainModels = (ticker: string, period = '2y', epochs = 30) =>
  api.post('/predict/train', { ticker, period, epochs }).then(r => r.data);

export const compareModels = (ticker: string, period = '1y') =>
  api.get(`/predict/compare/${ticker}`, { params: { period } }).then(r => r.data);

export const getTimeframePredictions = (ticker: string) =>
  api.get(`/predict/timeframes/${ticker}`).then(r => r.data);

// ─── Sentiment ────────────────────────────────────────────────────────────────
export const fetchSentiment = (ticker: string, days = 7, model = 'vader') =>
  api.get(`/sentiment/${ticker}`, { params: { days_back: days, model } }).then(r => r.data);

// ─── Portfolio ────────────────────────────────────────────────────────────────
export const simulatePortfolio = (positions: { ticker: string; weight: number }[], capital = 100000, period = '1y') =>
  api.post('/portfolio/simulate', { positions, initial_capital: capital, period }).then(r => r.data);

export const getPortfolioPresets = () =>
  api.get('/portfolio/presets').then(r => r.data);

// ─── Backtesting ──────────────────────────────────────────────────────────────
export const runBacktest = (params: {
  ticker: string;
  strategy: string;
  period?: string;
  initial_capital?: number;
  commission?: number;
  short_window?: number;
  long_window?: number;
}) => api.post('/backtest/', params).then(r => r.data);

export const getStrategies = () =>
  api.get('/backtest/strategies').then(r => r.data);

// ─── Screener ─────────────────────────────────────────────────────────────────
export const screenStocks = (filters: Record<string, any>, universe?: string[]) =>
  api.post('/screen/', { filters, universe }).then(r => r.data);

export const getScreenerPresets = () =>
  api.get('/screen/presets').then(r => r.data);

// ─── Insights ─────────────────────────────────────────────────────────────────
export const fetchInsights = (ticker: string) =>
  api.get(`/insights/${ticker}`).then(r => r.data);

// ─── Health ───────────────────────────────────────────────────────────────────
export const checkHealth = () =>
  api.get('/health').then(r => r.data);

export default api;
