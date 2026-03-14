'use client';
import { useEffect, useState } from 'react';
import { fetchMarketIndices, screenStocks } from '@/lib/api';
import { TrendingUp, TrendingDown, BarChart3, Zap, Activity, DollarSign, Globe, Shield } from 'lucide-react';

const WATCHLIST = [
  { ticker: 'AAPL', name: 'Apple Inc.' },
  { ticker: 'MSFT', name: 'Microsoft Corp.' },
  { ticker: 'NVDA', name: 'Nvidia Corp.' },
  { ticker: 'TSLA', name: 'Tesla Inc.' },
  { ticker: 'AMZN', name: 'Amazon.com Inc.' },
  { ticker: 'GOOGL', name: 'Alphabet Inc.' },
  { ticker: 'META', name: 'Meta Platforms Inc.' }
];
const FEATURES = [
  { icon: Activity, title: 'Live Predictions', desc: 'LSTM + Ensemble ML forecasts updated in real-time' },
  { icon: Shield, title: 'Risk Analytics', desc: 'VaR, CVaR, Sharpe, Max Drawdown analysis' },
  { icon: BarChart3, title: 'Backtesting Engine', desc: 'Test strategies on 5+ years of historical data' },
  { icon: Globe, title: 'Sentiment Analysis', desc: 'FinBERT news analysis across 20+ sources' },
];

export default function Dashboard() {
  const [indices, setIndices] = useState<any>({});
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [indData, screenData] = await Promise.allSettled([
          fetchMarketIndices(),
          screenStocks({ rsi_max: 40, min_volume: 500000, above_sma50: true }),
        ]);
        if (indData.status === 'fulfilled') setIndices(indData.value);
        if (screenData.status === 'fulfilled') setOpportunities(screenData.value.results?.slice(0, 5) || []);
      } catch {}
      setLoading(false);
    };
    load();
  }, []);

  const formatChange = (val: number) => (val >= 0 ? `+${val?.toFixed(2)}%` : `${val?.toFixed(2)}%`);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Hero */}
      <div className="glass-card p-6 relative overflow-hidden" style={{ background: 'linear-gradient(135deg, rgba(0,212,255,0.06) 0%, rgba(0,50,120,0.08) 100%)' }}>
        <div className="absolute right-6 top-0 opacity-5 pointer-events-none" style={{ fontSize: 200, lineHeight: 1 }}>📈</div>
        <div className="relative">
          <div className="text-xs font-medium mb-2 flex items-center gap-2" style={{ color: '#00d4ff' }}>
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse-slow" />
            AI MARKET INTELLIGENCE PLATFORM
          </div>
          <h1 className="text-3xl font-bold text-white mb-2" style={{ letterSpacing: '-0.5px' }}>
            Welcome to StockAI
          </h1>
          <p className="text-slate-400 max-w-xl" style={{ lineHeight: 1.6 }}>
            Next-generation AI-powered market analysis combining deep learning, NLP sentiment, and quantitative finance.
          </p>
          <div className="flex gap-3 mt-4">
            <a href="/explorer" className="btn-primary text-sm">Explore Markets →</a>
            <a href="/prediction" className="btn-secondary text-sm">Run Prediction</a>
          </div>
        </div>
      </div>

      {/* Market Indices */}
      <div>
        <h2 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">Market Overview</h2>
        {loading ? (
          <div className="flex justify-center py-8"><div className="spinner" /></div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3">
            {Object.entries(indices).map(([name, data]: any) => {
              const positive = data.change_pct >= 0;
              return (
                <div key={name} className="metric-tile text-center">
                  <div className="text-xs text-slate-500 mb-1 truncate">{name}</div>
                  <div className="text-base font-bold text-white">
                    {name === 'VIX' ? data.value.toFixed(2) : data.value?.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  </div>
                  <div className={`text-xs font-medium mt-0.5 ${positive ? 'text-green-400' : 'text-red-400'}`}>
                    {positive ? '▲' : '▼'} {formatChange(data.change_pct)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Watchlist */}
        <div className="glass-card p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <BarChart3 size={16} style={{ color: '#00d4ff' }} /> Watchlist
            </h2>
            <span className="text-xs text-slate-500">Click to explore →</span>
          </div>
          <div className="space-y-2">
            {WATCHLIST.map(({ ticker, name }) => (
              <a href={`/explorer?ticker=${ticker}`} key={ticker}
                className="flex items-center justify-between p-3 rounded-xl hover:bg-white/5 transition-all group"
                style={{ border: '1px solid rgba(255,255,255,0.04)' }}
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold"
                    style={{ background: 'rgba(0,212,255,0.1)', color: '#00d4ff' }}>
                    {ticker[0]}
                  </div>
                  <div>
                    <div className="font-semibold text-sm text-white flex items-center gap-2">
                        {ticker} <span className="text-xs text-slate-400 font-normal">{name}</span>
                    </div>
                    <div className="text-xs text-slate-500">→ Explore</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-medium badge-cyan px-2 py-0.5 rounded-full">Track</div>
                </div>
              </a>
            ))}
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-4">
          {/* AI Opportunities */}
          <div className="glass-card p-5">
            <h2 className="font-semibold text-white mb-3 flex items-center gap-2">
              <Zap size={16} style={{ color: '#ffd700' }} /> AI Opportunities
            </h2>
            {opportunities.length > 0 ? (
              <div className="space-y-2">
                {opportunities.map(stock => (
                  <a href={`/explorer?ticker=${stock.ticker}`} key={stock.ticker}
                    className="flex items-center justify-between p-2 rounded-lg hover:bg-white/5 transition-all"
                  >
                    <div>
                      <div className="text-sm font-semibold text-white flex items-center gap-1">
                          {stock.ticker} <span className="text-[10px] text-slate-400 font-normal truncate max-w-[120px]">{stock.name}</span>
                      </div>
                      <div className="text-xs text-slate-500">RSI {stock.rsi} · Vol {stock.volume_ratio}x</div>
                    </div>
                    <div className="text-xs font-semibold" style={{ color: '#00e676' }}>Score {stock.score}</div>
                  </a>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 text-center py-4">Run Screener to populate</p>
            )}
          </div>

          {/* Platform Features */}
          <div className="glass-card p-5">
            <h2 className="font-semibold text-white mb-3">Platform Capabilities</h2>
            <div className="space-y-3">
              {FEATURES.map(({ icon: Icon, title, desc }) => (
                <div key={title} className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: 'rgba(0,212,255,0.1)' }}>
                    <Icon size={14} style={{ color: '#00d4ff' }} />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-white">{title}</div>
                    <div className="text-xs text-slate-500">{desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { href: '/prediction', label: '🤖 Run ML Prediction', desc: 'LSTM + Ensemble forecast' },
          { href: '/strategy-lab', label: '🧪 Backtest Strategy', desc: 'Test trading strategies' },
          { href: '/portfolio', label: '💼 Build Portfolio', desc: 'Simulate allocations' },
          { href: '/ai-insights', label: '💡 Get AI Insights', desc: 'Natural language analysis' },
        ].map(({ href, label, desc }) => (
          <a key={href} href={href} className="glass-card p-4 hover:border-cyan-700 transition-all">
            <div className="font-semibold text-sm text-white mb-0.5">{label}</div>
            <div className="text-xs text-slate-500">{desc}</div>
          </a>
        ))}
      </div>
    </div>
  );
}
