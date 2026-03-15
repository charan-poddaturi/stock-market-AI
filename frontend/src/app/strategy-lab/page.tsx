'use client';
import { useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { runBacktest, getStrategies, resolveTicker } from '@/lib/api';
import { FlaskConical, TrendingUp, TrendingDown, BarChart3, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

export default function StrategyLabPage() {
  const [ticker, setTicker] = useState('AAPL');
  const [strategy, setStrategy] = useState('sma_crossover');
  const [period, setPeriod] = useState('2y');
  const [capital, setCapital] = useState(10000);
  const [shortW, setShortW] = useState(20);
  const [longW, setLongW] = useState(50);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const STRATEGIES = [
    { id: 'sma_crossover', label: 'SMA Crossover' },
    { id: 'rsi_mean_reversion', label: 'RSI Mean Reversion' },
    { id: 'bollinger_breakout', label: 'Bollinger Breakout' },
    { id: 'macd', label: 'MACD Signal' },
    { id: 'buy_and_hold', label: 'Buy & Hold' },
  ];

  const handleRun = async () => {
    setLoading(true);
    try {
      const symbol = await resolveTicker(ticker);
      setTicker(symbol);
      const data = await runBacktest({ ticker: symbol, strategy, period, initial_capital: capital, short_window: shortW, long_window: longW });
      setResult(data);
      toast.success('Backtest complete!');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Backtest failed');
    }
    setLoading(false);
  };

  const totalReturn = result?.total_return ?? 0;
  const isPositive = totalReturn >= 0;

  const equityChart = useMemo(() => {
    if (!result?.portfolio_history?.length) return null;
    const x = result.portfolio_history.map((p: any) => p.date);
    const y = result.portfolio_history.map((p: any) => p.value);
    return {
      data: [{
        type: 'scatter',
        mode: 'lines',
        x,
        y,
        fill: 'tozeroy',
        fillcolor: isPositive ? 'rgba(0,230,118,0.08)' : 'rgba(255,71,87,0.08)',
        line: { color: isPositive ? '#00e676' : '#ff4757', width: 2 },
        name: 'Portfolio Value',
      }],
      layout: {
        paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
        font: { color: '#94a3b8', family: 'Inter', size: 11 },
        xaxis: { gridcolor: 'rgba(255,255,255,0.04)', linecolor: 'rgba(255,255,255,0.06)' },
        yaxis: { gridcolor: 'rgba(255,255,255,0.04)', linecolor: 'rgba(255,255,255,0.06)', side: 'right', tickprefix: '$' },
        margin: { t: 0, r: 60, b: 40, l: 8 },
        showlegend: false,
      },
    };
  }, [result, isPositive]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <FlaskConical size={24} style={{ color: '#00d4ff' }} /> Backtest Strategies
        </h1>
        <p className="text-slate-400 text-sm mt-1">See how simple trading ideas would have performed in the past.</p>
      </div>

      {/* Config */}
      <div className="glass-card p-6">
        <h3 className="font-semibold text-white mb-4">Backtest Configuration</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="col-span-2 md:col-span-1">
            <label className="block text-xs text-slate-400 mb-1.5">Ticker</label>
            <input className="input-dark uppercase" value={ticker} onChange={e => setTicker(e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className="block text-xs text-slate-400 mb-1.5">Strategy</label>
            <select className="input-dark" value={strategy} onChange={e => setStrategy(e.target.value)}>
              {STRATEGIES.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">Period</label>
            <select className="input-dark" value={period} onChange={e => setPeriod(e.target.value)}>
              <option value="1y">1 Year</option>
              <option value="2y">2 Years</option>
              <option value="5y">5 Years</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">Capital ($)</label>
            <input type="number" className="input-dark" value={capital} onChange={e => setCapital(Number(e.target.value))} />
          </div>
          {strategy === 'sma_crossover' && <>
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">Short MA</label>
              <input type="number" className="input-dark" value={shortW} onChange={e => setShortW(Number(e.target.value))} />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">Long MA</label>
              <input type="number" className="input-dark" value={longW} onChange={e => setLongW(Number(e.target.value))} />
            </div>
          </>}
        </div>
        <button onClick={handleRun} disabled={loading} className="btn-primary mt-4 flex items-center gap-2">
          {loading ? <RefreshCw size={15} className="animate-spin" /> : <FlaskConical size={15} />} Run Backtest
        </button>
      </div>

      {/* Results */}
      {result && (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
            {[
              { label: 'Total Return', value: `${totalReturn > 0 ? '+' : ''}${totalReturn?.toFixed(2)}%`, color: isPositive ? '#00e676' : '#ff4757' },
              { label: 'Final Value', value: `$${result.final_value?.toLocaleString()}`, color: 'white' },
              { label: 'Sharpe Ratio', value: result.sharpe_ratio?.toFixed(3), color: result.sharpe_ratio > 1 ? '#00e676' : result.sharpe_ratio > 0 ? '#ffd700' : '#ff4757' },
              { label: 'Sortino Ratio', value: result.sortino_ratio?.toFixed(3), color: '#00d4ff' },
              { label: 'Max Drawdown', value: `-${Math.abs(result.max_drawdown)?.toFixed(2)}%`, color: '#ff4757' },
              { label: 'Win Rate', value: `${result.win_rate?.toFixed(1)}%`, color: result.win_rate > 50 ? '#00e676' : '#ff4757' },
              { label: 'Profit Factor', value: result.profit_factor?.toFixed(2), color: result.profit_factor > 1 ? '#00e676' : '#ff4757' },
              { label: 'Num Trades', value: result.num_trades, color: '#64748b' },
            ].map(m => (
              <div key={m.label} className="metric-tile text-center col-span-1">
                <div className="text-xs text-slate-500 mb-1">{m.label}</div>
                <div className="text-base font-bold" style={{ color: m.color }}>{m.value}</div>
              </div>
            ))}
          </div>

          {/* Equity Curve */}
          {equityChart && (
            <div className="glass-card p-5" style={{ height: 320 }}>
              <h3 className="font-semibold text-white mb-3">Equity Curve</h3>
              <Plot
                data={equityChart.data}
                layout={equityChart.layout}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%', height: '260px' }}
              />
            </div>
          )}

          {/* B&H Comparison */}
          <div className="glass-card p-5">
            <h3 className="font-semibold text-white mb-3">Strategy vs Buy & Hold</h3>
            <div className="flex gap-6">
              <div>
                <div className="text-xs text-slate-400 mb-1">{strategy.replace(/_/g, ' ').toUpperCase()}</div>
                <div className={`text-2xl font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>{totalReturn > 0 ? '+' : ''}{totalReturn?.toFixed(2)}%</div>
              </div>
              <div className="border-l" style={{ borderColor: 'rgba(255,255,255,0.08)' }} />
              <div>
                <div className="text-xs text-slate-400 mb-1">BUY & HOLD</div>
                <div className={`text-2xl font-bold ${result.buy_hold_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>{result.buy_hold_return > 0 ? '+' : ''}{result.buy_hold_return?.toFixed(2)}%</div>
              </div>
              <div className="border-l" style={{ borderColor: 'rgba(255,255,255,0.08)' }} />
              <div>
                <div className="text-xs text-slate-400 mb-1">ALPHA</div>
                <div className={`text-2xl font-bold ${result.alpha >= 0 ? 'text-green-400' : 'text-red-400'}`}>{result.alpha > 0 ? '+' : ''}{result.alpha?.toFixed(2)}%</div>
              </div>
            </div>
          </div>
        </>
      )}

      {!result && !loading && (
        <div className="glass-card p-10 text-center">
          <FlaskConical size={40} className="mx-auto mb-3" style={{ color: '#1e293b' }} />
          <p className="text-slate-500">Configure parameters and click <strong className="text-white">Run Backtest</strong></p>
        </div>
      )}
    </div>
  );
}
