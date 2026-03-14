'use client';
import { useState } from 'react';
import dynamic from 'next/dynamic';
import { simulatePortfolio, getPortfolioPresets, resolveTicker } from '@/lib/api';
import { Briefcase, Plus, Trash2, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

export default function PortfolioPage() {
  const [positions, setPositions] = useState([
    { ticker: 'AAPL', weight: 25 },
    { ticker: 'MSFT', weight: 25 },
    { ticker: 'NVDA', weight: 25 },
    { ticker: 'GOOGL', weight: 25 },
  ]);
  const [capital, setCapital] = useState(100000);
  const [period, setPeriod] = useState('1y');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const addPosition = () => setPositions(p => [...p, { ticker: '', weight: 10 }]);
  const removePosition = (i: number) => setPositions(p => p.filter((_, idx) => idx !== i));
  const updatePosition = (i: number, key: string, value: any) =>
    setPositions(p => p.map((pos, idx) => idx === i ? { ...pos, [key]: value } : pos));

  const handleSimulate = async () => {
    const valid = positions.filter(p => p.ticker.trim());
    if (!valid.length) return toast.error('Add at least one position');
    setLoading(true);
    try {
      // Resolve all tickers concurrently in case user entered company names
      const resolved = await Promise.all(
        valid.map(async p => ({
          original: p.ticker,
          ticker: await resolveTicker(p.ticker),
          weight: p.weight / 100
        }))
      );

      // Update inputs with resolved tickers
      setPositions(valid.map((_, i) => ({ ticker: resolved[i].ticker, weight: resolved[i].weight * 100 })));

      const data = await simulatePortfolio(
        resolved.map(r => ({ ticker: r.ticker, weight: r.weight })),
        capital, period,
      );
      setResult(data);
      toast.success('Simulation complete!');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Simulation failed');
    }
    setLoading(false);
  };

  const loadPreset = (preset: any) => {
    setPositions(preset.positions.map((p: any) => ({ ticker: p.ticker, weight: p.weight * 100 })));
  };

  const PRESETS = [
    { name: '💻 Tech Giants', positions: [{ ticker: 'AAPL', weight: 0.25 }, { ticker: 'MSFT', weight: 0.25 }, { ticker: 'NVDA', weight: 0.25 }, { ticker: 'GOOGL', weight: 0.25 }] },
    { name: '⚖️ Balanced', positions: [{ ticker: 'SPY', weight: 0.4 }, { ticker: 'QQQ', weight: 0.3 }, { ticker: 'GLD', weight: 0.15 }, { ticker: 'TLT', weight: 0.15 }] },
  ];

  const isPositive = (result?.total_return ?? 0) >= 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Briefcase size={24} style={{ color: '#00d4ff' }} /> Portfolio Simulator
        </h1>
        <p className="text-slate-400 text-sm mt-1">Simulate multi-asset portfolios with risk analytics</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Builder */}
        <div className="space-y-4 lg:col-span-1">
          {/* Presets */}
          <div className="glass-card p-4">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Quick Presets</div>
            <div className="space-y-2">
              {PRESETS.map(p => (
                <button key={p.name} onClick={() => loadPreset(p)} className="btn-secondary w-full text-sm text-left">{p.name}</button>
              ))}
            </div>
          </div>

          {/* Positions */}
          <div className="glass-card p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Positions</div>
              <button onClick={addPosition} className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300">
                <Plus size={12} /> Add
              </button>
            </div>
            <div className="space-y-2">
              {positions.map((pos, i) => (
                <div key={i} className="flex gap-2 items-center">
                  <input className="input-dark text-xs uppercase w-20" value={pos.ticker} onChange={e => updatePosition(i, 'ticker', e.target.value)} placeholder="AAPL" />
                  <div className="flex-1 flex items-center gap-1">
                    <input type="number" className="input-dark text-xs w-16 text-right" value={pos.weight} onChange={e => updatePosition(i, 'weight', Number(e.target.value))} min={0} max={100} />
                    <span className="text-xs text-slate-500">%</span>
                  </div>
                  <button onClick={() => removePosition(i)} className="text-slate-600 hover:text-red-400 transition-colors"><Trash2 size={13} /></button>
                </div>
              ))}
            </div>
            {/* Total weight */}
            <div className="mt-3 pt-3 border-t flex justify-between text-xs" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
              <span className="text-slate-400">Total Weight</span>
              <span className={positions.reduce((a, p) => a + p.weight, 0) === 100 ? 'text-green-400' : 'text-yellow-400'}>
                {positions.reduce((a, p) => a + p.weight, 0)}%
              </span>
            </div>
          </div>

          {/* Settings */}
          <div className="glass-card p-4 space-y-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Initial Capital</label>
              <input type="number" className="input-dark" value={capital} onChange={e => setCapital(Number(e.target.value))} />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Simulation Period</label>
              <select className="input-dark" value={period} onChange={e => setPeriod(e.target.value)}>
                <option value="6mo">6 Months</option> <option value="1y">1 Year</option>
                <option value="2y">2 Years</option> <option value="5y">5 Years</option>
              </select>
            </div>
            <button onClick={handleSimulate} disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
              {loading ? <RefreshCw size={15} className="animate-spin" /> : <Briefcase size={15} />} Simulate
            </button>
          </div>
        </div>

        {/* Results */}
        <div className="lg:col-span-2 space-y-4">
          {result ? (
            <>
              {/* Key metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: 'Total Return', value: `${result.total_return > 0 ? '+' : ''}${result.total_return?.toFixed(2)}%`, color: isPositive ? '#00e676' : '#ff4757' },
                  { label: 'Sharpe Ratio', value: result.sharpe_ratio?.toFixed(3), color: result.sharpe_ratio > 1 ? '#00e676' : '#ffd700' },
                  { label: 'Max Drawdown', value: `-${Math.abs(result.max_drawdown)?.toFixed(2)}%`, color: '#ff4757' },
                  { label: 'Beta', value: result.beta?.toFixed(3), color: '#00d4ff' },
                  { label: 'VaR 95% (1d)', value: `-${result.var_95_daily?.toFixed(2)}%`, color: '#ff6b6b' },
                  { label: 'CVaR 95%', value: `-${result.cvar_95_daily?.toFixed(2)}%`, color: '#ff4757' },
                  { label: 'Ann. Return', value: `${result.annualized_return?.toFixed(2)}%`, color: '#00d4ff' },
                  { label: 'Ann. Volatility', value: `${result.annualized_volatility?.toFixed(2)}%`, color: '#94a3b8' },
                ].map(m => (
                  <div key={m.label} className="metric-tile">
                    <div className="text-xs text-slate-500 mb-1">{m.label}</div>
                    <div className="text-lg font-bold" style={{ color: m.color }}>{m.value}</div>
                  </div>
                ))}
              </div>

              {/* Portfolio history chart */}
              {result.portfolio_history?.length > 0 && (
                <div className="glass-card p-4" style={{ height: 280 }}>
                  <h3 className="text-sm font-semibold text-white mb-2">Portfolio Value Over Time</h3>
                  <Plot
                    data={[{
                      type: 'scatter', mode: 'lines',
                      x: result.portfolio_history.map((p: any) => p.date),
                      y: result.portfolio_history.map((p: any) => p.value),
                      fill: 'tozeroy',
                      fillcolor: isPositive ? 'rgba(0,230,118,0.06)' : 'rgba(255,71,87,0.06)',
                      line: { color: isPositive ? '#00e676' : '#ff4757', width: 2 },
                    }]}
                    layout={{
                      paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
                      font: { color: '#94a3b8', family: 'Inter', size: 10 },
                      xaxis: { gridcolor: 'rgba(255,255,255,0.04)', linecolor: 'rgba(255,255,255,0.06)' },
                      yaxis: { gridcolor: 'rgba(255,255,255,0.04)', linecolor: 'rgba(255,255,255,0.06)', side: 'right', tickprefix: '$', tickformat: ',.0f' },
                      margin: { t: 4, r: 60, b: 35, l: 4 },
                      showlegend: false,
                    }}
                    config={{ responsive: true, displayModeBar: false }}
                    style={{ width: '100%', height: '220px' }}
                  />
                </div>
              )}

              {/* Position breakdown */}
              <div className="glass-card p-4">
                <h3 className="text-sm font-semibold text-white mb-3">Position Attribution</h3>
                <div className="space-y-2">
                  {result.positions?.map((pos: any) => (
                    <div key={pos.ticker} className="flex items-center gap-3">
                      <div className="w-12 text-xs font-bold text-white">{pos.ticker}</div>
                      <div className="flex-1 h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }}>
                        <div className="h-full rounded-full" style={{ width: `${pos.weight}%`, background: 'rgba(0,212,255,0.5)' }} />
                      </div>
                      <div className="text-xs text-slate-400 w-10 text-right">{pos.weight?.toFixed(1)}%</div>
                      <div className="text-xs font-semibold w-16 text-right" style={{ color: pos.total_return >= 0 ? '#00e676' : '#ff4757' }}>
                        {pos.total_return > 0 ? '+' : ''}{pos.total_return?.toFixed(2)}%
                      </div>
                      <div className="text-xs text-slate-500 w-16 text-right">${pos.current_price?.toFixed(2)}</div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="glass-card p-12 text-center">
              <Briefcase size={40} className="mx-auto mb-3" style={{ color: '#1e293b' }} />
              <p className="text-slate-500">Configure positions and click <strong className="text-white">Simulate</strong></p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
