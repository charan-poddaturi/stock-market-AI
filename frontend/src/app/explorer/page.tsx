'use client';
import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import { fetchStockData, fetchPatterns, fetchAnomalies, fetchFundamentals, resolveTicker } from '@/lib/api';
import { BarChart3, TrendingUp, Activity, AlertTriangle } from 'lucide-react';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const PERIODS = ['5d', '1mo', '3mo', '6mo', '1y', '2y', '5y'];
const INDICATORS = ['sma_20', 'sma_50', 'ema_12', 'bb_upper', 'bb_lower'];

function ExplorerContent() {
  const params = useSearchParams();
  const [ticker, setTicker] = useState(params?.get('ticker') || 'AAPL');
  const [inputTicker, setInputTicker] = useState(ticker);
  const [period, setPeriod] = useState('1y');
  const [data, setData] = useState<any>(null);
  const [patterns, setPatterns] = useState<any>(null);
  const [fundamentals, setFundamentals] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeIndicators, setActiveIndicators] = useState<string[]>(['sma_20', 'sma_50']);

  const load = async (t: string, p: string) => {
    setLoading(true);
    try {
      const [sd, pd, fd] = await Promise.allSettled([
        fetchStockData(t, p),
        fetchPatterns(t, '6mo'),
        fetchFundamentals(t),
      ]);
      if (sd.status === 'fulfilled') setData(sd.value);
      if (pd.status === 'fulfilled') setPatterns(pd.value);
      if (fd.status === 'fulfilled') setFundamentals(fd.value);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(ticker, period); }, [ticker, period]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (inputTicker.trim()) {
      setLoading(true);
      const symbol = await resolveTicker(inputTicker);
      setTicker(symbol);
      setInputTicker(symbol);
      // load effect will trigger automatically due to deps
    }
  };

  const chartData = data?.data || [];
  const dates = chartData.map((d: any) => d.date);
  const currentPrice = chartData.length > 0 ? chartData[chartData.length - 1].close : 0;
  const prevPrice = chartData.length > 1 ? chartData[chartData.length - 2].close : currentPrice;
  const priceChange = currentPrice - prevPrice;
  const changePct = prevPrice ? (priceChange / prevPrice) * 100 : 0;
  const isPositive = priceChange >= 0;

  const candlestickTrace: any = {
    type: 'candlestick',
    x: dates,
    open: chartData.map((d: any) => d.open),
    high: chartData.map((d: any) => d.high),
    low: chartData.map((d: any) => d.low),
    close: chartData.map((d: any) => d.close),
    name: ticker,
    increasing: { line: { color: '#00e676' }, fillcolor: 'rgba(0,230,118,0.3)' },
    decreasing: { line: { color: '#ff4757' }, fillcolor: 'rgba(255,71,87,0.3)' },
  };

  const indicatorTraces = activeIndicators.map(ind => ({
    type: 'scatter',
    x: dates,
    y: chartData.map((d: any) => d[ind]),
    name: ind.toUpperCase().replace('_', ' '),
    line: { width: 1.5, dash: ind.includes('bb') ? 'dot' : 'solid' },
    opacity: 0.8,
  }));

  const volumeTrace: any = {
    type: 'bar',
    x: dates,
    y: chartData.map((d: any) => d.volume),
    name: 'Volume',
    marker: {
      color: chartData.map((d: any, i: number) =>
        i > 0 && d.close > chartData[i - 1].close ? 'rgba(0,230,118,0.4)' : 'rgba(255,71,87,0.4)',
      ),
    },
    yaxis: 'y2',
  };

  const layout: any = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: '#94a3b8', family: 'Inter', size: 11 },
    xaxis: {
      gridcolor: 'rgba(255,255,255,0.04)',
      linecolor: 'rgba(255,255,255,0.08)',
      tickfont: { size: 10 },
      rangeslider: { visible: false },
    },
    yaxis: {
      gridcolor: 'rgba(255,255,255,0.04)',
      linecolor: 'rgba(255,255,255,0.08)',
      side: 'right',
    },
    yaxis2: { overlaying: 'y', side: 'left', showticklabels: false, showgrid: false },
    legend: { x: 0, y: 1.05, orientation: 'h', font: { size: 10 } },
    margin: { t: 10, r: 8, b: 40, l: 8 },
    showlegend: true,
  };

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{data?.ticker || ticker}</h1>
          <div className="text-sm text-slate-400">{fundamentals?.shortName || ''} · {fundamentals?.sector || ''}</div>
        </div>
        {currentPrice > 0 && (
          <div className="text-right">
            <div className="text-3xl font-bold text-white">${currentPrice.toFixed(2)}</div>
            <div className={`text-sm font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
              {isPositive ? '▲' : '▼'} {Math.abs(priceChange).toFixed(2)} ({Math.abs(changePct).toFixed(2)}%)
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="glass-card p-4">
        <div className="flex flex-wrap gap-3 items-center justify-between">
          {/* Ticker search */}
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              className="input-dark text-sm w-36"
              value={inputTicker}
              onChange={e => setInputTicker(e.target.value.toUpperCase())}
              placeholder="Ticker..."
            />
            <button type="submit" className="btn-primary text-sm px-4">Go</button>
          </form>
          {/* Period selector */}
          <div className="flex gap-1">
            {PERIODS.map(p => (
              <button key={p} onClick={() => setPeriod(p)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                style={{
                  background: period === p ? 'rgba(0,212,255,0.15)' : 'rgba(255,255,255,0.03)',
                  color: period === p ? '#00d4ff' : '#64748b',
                  border: period === p ? '1px solid rgba(0,212,255,0.3)' : '1px solid transparent',
                }}
              >{p}</button>
            ))}
          </div>
          {/* Indicator toggles */}
          <div className="flex gap-2 flex-wrap">
            {INDICATORS.map(ind => (
              <button key={ind} onClick={() => setActiveIndicators(prev =>
                prev.includes(ind) ? prev.filter(i => i !== ind) : [...prev, ind]
              )}
                className="px-2 py-1 rounded-lg text-xs font-medium transition-all"
                style={{
                  background: activeIndicators.includes(ind) ? 'rgba(0,212,255,0.1)' : 'rgba(255,255,255,0.03)',
                  color: activeIndicators.includes(ind) ? '#00d4ff' : '#4b5563',
                  border: `1px solid ${activeIndicators.includes(ind) ? 'rgba(0,212,255,0.25)' : 'transparent'}`,
                }}
              >{ind.toUpperCase().replace('_', ' ')}</button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="glass-card p-4" style={{ height: 420 }}>
        {loading ? (
          <div className="flex items-center justify-center h-full"><div className="spinner" /></div>
        ) : chartData.length > 0 ? (
          <Plot
            data={[candlestickTrace, ...indicatorTraces, volumeTrace]}
            layout={layout}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%', height: '100%' }}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-slate-500">No data available</div>
        )}
      </div>

      {/* Technical Metrics */}
      {!loading && chartData.length > 0 && (() => {
        const last = chartData[chartData.length - 1];
        const metrics = [
          { label: 'RSI (14)', value: last.rsi_14?.toFixed(1), status: last.rsi_14 < 30 ? 'oversold' : last.rsi_14 > 70 ? 'overbought' : 'neutral' },
          { label: 'MACD', value: last.macd?.toFixed(3), status: last.macd > 0 ? 'bull' : 'bear' },
          { label: 'BB %', value: `${(last.bb_pct * 100)?.toFixed(0)}%`, status: 'neutral' },
          { label: 'Vol Ratio', value: `${last.volume_ratio?.toFixed(2)}x`, status: last.volume_ratio > 2 ? 'bull' : 'neutral' },
          { label: 'ATR %', value: `${(last.atr_pct * 100)?.toFixed(2)}%`, status: 'neutral' },
          { label: 'Volatility', value: `${(last.volatility_21 * 100)?.toFixed(1)}%`, status: 'neutral' },
        ];
        return (
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            {metrics.map(m => (
              <div key={m.label} className="metric-tile text-center">
                <div className="text-xs text-slate-500 mb-1">{m.label}</div>
                <div className="text-sm font-bold text-white">{m.value ?? 'N/A'}</div>
                <div className={`text-xs mt-0.5 ${m.status === 'bull' || m.status === 'oversold' ? 'text-green-400' : m.status === 'bear' || m.status === 'overbought' ? 'text-red-400' : 'text-slate-500'}`}>
                  {m.status}
                </div>
              </div>
            ))}
          </div>
        );
      })()}

      {/* Patterns */}
      {patterns?.patterns?.length > 0 && (
        <div className="glass-card p-5">
          <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
            <Activity size={15} style={{ color: '#00d4ff' }} /> Detected Patterns
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {patterns.patterns.slice(0, 6).map((p: any, i: number) => (
              <div key={i} className="flex items-center gap-2 p-2 rounded-lg" style={{ background: 'rgba(255,255,255,0.03)' }}>
                <span>{p.sentiment === 'bullish' ? '🟢' : p.sentiment === 'bearish' ? '🔴' : '🟡'}</span>
                <div>
                  <div className="text-xs font-semibold text-white">{p.pattern.replace(/_/g, ' ')}</div>
                  <div className="text-xs text-slate-500">{p.date}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ExplorerPage() {
  return <Suspense fallback={<div className="flex justify-center items-center h-64"><div className="spinner" /></div>}><ExplorerContent /></Suspense>;
}
