'use client';
import { useState } from 'react';
import { fetchInsights, fetchSentiment, resolveTicker } from '@/lib/api';
import { Lightbulb, RefreshCw, TrendingUp, TrendingDown, Minus, ExternalLink } from 'lucide-react';
import toast from 'react-hot-toast';

export default function AIInsightsPage() {
  const [ticker, setTicker] = useState('AAPL');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);

  const handleFetch = async () => {
    setLoading(true);
    try {
      const symbol = await resolveTicker(ticker);
      setTicker(symbol);
      const result = await fetchInsights(symbol);
      setData(result);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to fetch insights');
    }
    setLoading(false);
  };

  const moodColor = (mood: string) => {
    if (['bullish', 'mildly_bullish'].includes(mood)) return '#00e676';
    if (['bearish', 'mildly_bearish'].includes(mood)) return '#ff4757';
    return '#64748b';
  };

  const moodEmoji = (mood: string) => {
    if (mood === 'bullish' || mood === 'strong_buy') return '🚀';
    if (mood === 'mildly_bullish') return '📈';
    if (mood === 'bearish') return '🐻';
    if (mood === 'mildly_bearish') return '📉';
    return '⚖️';
  };

  const sentLabel = data?.sentiment?.label;
  const sentScore = data?.sentiment?.score ?? 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Lightbulb size={24} style={{ color: '#ffd700' }} /> AI Insights Panel
        </h1>
        <p className="text-slate-400 text-sm mt-1">AI-generated market narratives powered by FinBERT + technical analysis</p>
      </div>

      {/* Input */}
      <div className="glass-card p-5">
        <div className="flex gap-3 items-end">
          <div className="flex-1 max-w-xs">
            <label className="block text-xs text-slate-400 mb-1.5">Ticker Symbol</label>
            <input className="input-dark uppercase" value={ticker} onChange={e => setTicker(e.target.value)} placeholder="AAPL" onKeyDown={e => e.key === 'Enter' && handleFetch()} />
          </div>
          <button onClick={handleFetch} disabled={loading} className="btn-primary flex items-center gap-2">
            {loading ? <RefreshCw size={15} className="animate-spin" /> : <Lightbulb size={15} />}
            Generate Insights
          </button>
        </div>
      </div>

      {!data && !loading && (
        <div className="glass-card p-12 text-center">
          <Lightbulb size={40} className="mx-auto mb-3" style={{ color: '#1e293b' }} />
          <p className="text-slate-500">Enter a ticker to get AI-generated market narrative and sentiment</p>
        </div>
      )}

      {loading && (
        <div className="glass-card p-12 text-center">
          <div className="spinner mx-auto mb-3" />
          <p className="text-slate-500">Fetching news, analyzing sentiment, generating narrative...</p>
        </div>
      )}

      {data && !loading && (
        <>
          {/* Company header */}
          <div className="glass-card p-5 flex items-center justify-between flex-wrap gap-4"
            style={{ background: 'linear-gradient(135deg, rgba(0,212,255,0.05) 0%, rgba(0,50,100,0.04) 100%)' }}>
            <div>
              <h2 className="text-xl font-bold text-white">{data.name} ({data.ticker})</h2>
              <div className="text-sm text-slate-400">{data.sector}</div>
            </div>
            <div className="text-right">
              <div className="text-3xl">{moodEmoji(data.mood?.mood)}</div>
              <div className="text-sm font-semibold" style={{ color: moodColor(data.mood?.mood) }}>
                {data.mood?.mood?.replace('_', ' ').toUpperCase()}
              </div>
            </div>
          </div>

          {/* Sentiment Gauge */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-white mb-3">News Sentiment</h3>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-slate-400">{data.sentiment?.article_count} articles analyzed</span>
                <span className={`text-sm font-bold badge-${sentLabel === 'positive' ? 'bull' : sentLabel === 'negative' ? 'bear' : 'neutral'} px-2 py-0.5 rounded-full`}>
                  {sentLabel?.toUpperCase()}
                </span>
              </div>
              {/* Gauge bar */}
              <div className="h-3 rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }}>
                <div className="h-full rounded-full transition-all duration-1000"
                  style={{
                    width: `${((sentScore + 1) / 2) * 100}%`,
                    background: sentScore > 0.05 ? 'linear-gradient(90deg, #00e676, #00b8a9)' : sentScore < -0.05 ? 'linear-gradient(90deg, #ff4757, #ff6b6b)' : '#64748b',
                  }}
                />
              </div>
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>🐻 Bearish</span>
                <span>Score: {sentScore?.toFixed(3)}</span>
                <span>Bullish 🚀</span>
              </div>
            </div>

            {/* Analyst Rating */}
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-white mb-3">Analyst Consensus</h3>
              <div className="text-3xl font-bold mb-1 capitalize" style={{ color: '#00d4ff' }}>
                {data.analyst?.rating?.replace('_', ' ') ?? 'N/A'}
              </div>
              <div className="text-xs text-slate-400 mb-2">Price Target</div>
              <div className="text-2xl font-bold text-white">
                {data.analyst?.target_price ? `$${data.analyst.target_price?.toFixed(2)}` : 'N/A'}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                P/E: {data.analyst?.pe_ratio?.toFixed(1) ?? 'N/A'}
              </div>
            </div>

            {/* Key Metrics */}
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-white mb-3">Key Metrics</h3>
              <div className="space-y-2">
                {[
                  { label: 'Current Price', value: `$${data.key_metrics?.current_price?.toFixed(2)}` },
                  { label: 'RSI (14)', value: data.key_metrics?.rsi_14?.toFixed(1) },
                  { label: 'Volatility', value: `${data.key_metrics?.volatility?.toFixed(1)}%` },
                  { label: '1M Return', value: `${data.key_metrics?.month_return > 0 ? '+' : ''}${data.key_metrics?.month_return?.toFixed(2)}%`, color: data.key_metrics?.month_return >= 0 ? '#00e676' : '#ff4757' },
                ].map(m => (
                  <div key={m.label} className="flex justify-between text-xs">
                    <span className="text-slate-400">{m.label}</span>
                    <span className="font-mono font-semibold" style={{ color: (m as any).color || '#e2e8f0' }}>{m.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* AI Narrative */}
          <div className="glass-card p-6" style={{ border: '1px solid rgba(0,212,255,0.15)', background: 'linear-gradient(135deg, rgba(0,212,255,0.04) 0%, rgba(0,50,100,0.03) 100%)' }}>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full animate-pulse-slow" style={{ background: '#00d4ff' }} />
              <h3 className="text-sm font-semibold" style={{ color: '#00d4ff' }}>AI Market Narrative</h3>
            </div>
            <div className="text-slate-300 leading-relaxed text-sm" dangerouslySetInnerHTML={{ __html: data.narrative?.replace(/\*\*(.*?)\*\*/g, '<strong style="color:#e2e8f0">$1</strong>') }} />
            <div className="mt-3 text-xs text-slate-500 italic">Generated by FinBERT + Technical Analysis Engine</div>
          </div>

          {/* Patterns */}
          {data.patterns?.length > 0 && (
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-white mb-3">Detected Patterns</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {data.patterns.map((p: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 p-2 rounded-lg text-xs" style={{ background: 'rgba(255,255,255,0.03)' }}>
                    <span>{p.sentiment === 'bullish' ? '🟢' : p.sentiment === 'bearish' ? '🔴' : '🟡'}</span>
                    <div>
                      <div className="font-medium text-white">{p.pattern?.replace(/_/g, ' ')}</div>
                      <div className="text-slate-500">{p.date}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* News Feed */}
          {data.news?.length > 0 && (
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-white mb-3">Latest News</h3>
              <div className="space-y-3">
                {data.news.map((article: any, i: number) => {
                  const score = article.sentiment?.score ?? 0;
                  const label = article.sentiment?.label ?? 'neutral';
                  return (
                    <div key={i} className="flex gap-3 p-3 rounded-xl" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.04)' }}>
                      <div className="flex-shrink-0 w-2 h-2 rounded-full mt-1.5" style={{
                        background: label === 'positive' ? '#00e676' : label === 'negative' ? '#ff4757' : '#64748b'
                      }} />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-slate-300 line-clamp-2">{article.title}</div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-slate-500">{article.source}</span>
                          <span className="text-xs text-slate-600">·</span>
                          <span className="text-xs" style={{ color: label === 'positive' ? '#00e676' : label === 'negative' ? '#ff4757' : '#64748b' }}>
                            {label}
                          </span>
                          {article.url && (
                            <a href={article.url} target="_blank" rel="noopener noreferrer" className="ml-auto text-slate-600 hover:text-cyan-400 transition-colors">
                              <ExternalLink size={11} />
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
