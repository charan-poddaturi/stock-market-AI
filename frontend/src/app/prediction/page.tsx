'use client';
import { useState } from 'react';
import { runPrediction, trainModels, compareModels, getTimeframePredictions, fetchFundamentals, resolveTicker } from '@/lib/api';
import { Brain, Zap, BarChart3, Target, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

export default function PredictionPage() {
  const [ticker, setTicker] = useState('AAPL');
  const [period, setPeriod] = useState('2y');
  const [loading, setLoading] = useState(false);
  const [trainLoading, setTrainLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [comparison, setComparison] = useState<any>(null);
  const [timeframes, setTimeframes] = useState<any>(null);
  const [tab, setTab] = useState<'predict' | 'compare' | 'timeframes'>('predict');
  const [companyName, setCompanyName] = useState<string>('');

  const loadName = async (t: string) => {
    try {
      const fd = await fetchFundamentals(t);
      if (fd?.shortName) setCompanyName(fd.shortName);
    } catch {}
  };

  const handlePredict = async () => {
    setLoading(true);
    try {
      const symbol = await resolveTicker(ticker);
      setTicker(symbol);
      loadName(symbol);
      const data = await runPrediction(symbol, 'ensemble', period);
      setResult(data);
      setTab('predict');
      toast.success('Prediction complete!');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Prediction failed');
    }
    setLoading(false);
  };

  const handleTrain = async () => {
    setTrainLoading(true);
    toast('🚀 Training started in background — may take 1-2 min', { duration: 5000 });
    try {
      const symbol = await resolveTicker(ticker);
      setTicker(symbol);
      await trainModels(symbol, period);
      toast.success('Training queued!');
    } catch (e: any) {
      toast.error('Training failed');
    }
    setTrainLoading(false);
  };

  const handleCompare = async () => {
    setLoading(true);
    try {
      const symbol = await resolveTicker(ticker);
      setTicker(symbol);
      const data = await compareModels(symbol, period);
      setComparison(data);
      setTab('compare');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Model comparison failed');
    }
    setLoading(false);
  };

  const handleTimeframes = async () => {
    setLoading(true);
    try {
      const symbol = await resolveTicker(ticker);
      setTicker(symbol);
      const data = await getTimeframePredictions(symbol);
      setTimeframes(data);
      setTab('timeframes');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to load timeframe predictions');
    }
    setLoading(false);
  };

  const isUp = result?.prediction_direction === 'up';
  const prob = result?.probability_up ?? 0.5;
  const confidence = result?.confidence_score ?? 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Brain size={24} style={{ color: '#00d4ff' }} /> Prediction Panel
        </h1>
        <p className="text-slate-400 text-sm mt-1">ML ensemble + deep learning price direction forecasts</p>
      </div>

      {/* Controls */}
      <div className="glass-card p-5">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[140px]">
            <label className="block text-xs text-slate-400 mb-1.5">Ticker Symbol</label>
            <input className="input-dark uppercase" value={ticker} onChange={e => setTicker(e.target.value)} placeholder="AAPL" />
          </div>
          <div className="w-32">
            <label className="block text-xs text-slate-400 mb-1.5">Training Period</label>
            <select className="input-dark" value={period} onChange={e => setPeriod(e.target.value)}>
              <option value="1y">1 Year</option>
              <option value="2y">2 Years</option>
              <option value="5y">5 Years</option>
            </select>
          </div>
          <button onClick={handlePredict} disabled={loading} className="btn-primary flex items-center gap-2">
            {loading ? <RefreshCw size={15} className="animate-spin" /> : <Zap size={15} />} Predict
          </button>
          <button onClick={handleTrain} disabled={trainLoading} className="btn-secondary flex items-center gap-2">
            <Brain size={15} /> Train Models
          </button>
          <button onClick={handleCompare} disabled={loading} className="btn-secondary flex items-center gap-2">
            <BarChart3 size={15} /> Compare
          </button>
          <button onClick={handleTimeframes} disabled={loading} className="btn-secondary flex items-center gap-2">
            <Target size={15} /> Multi-TF
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        {(['predict', 'compare', 'timeframes'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-all capitalize"
            style={{
              background: tab === t ? 'rgba(0,212,255,0.12)' : 'rgba(255,255,255,0.03)',
              color: tab === t ? '#00d4ff' : '#64748b',
              border: tab === t ? '1px solid rgba(0,212,255,0.25)' : '1px solid transparent',
            }}
          >{t === 'predict' ? 'Ensemble Prediction' : t === 'compare' ? 'Model Comparison' : 'Multi-Timeframe'}</button>
        ))}
      </div>

      {/* Prediction Results */}
      {tab === 'predict' && result && (
        <div className="space-y-5">
          {/* Main signal card */}
          <div className="glass-card p-6" style={{ background: isUp ? 'linear-gradient(135deg, rgba(0,230,118,0.08), rgba(0,100,40,0.05))' : 'linear-gradient(135deg, rgba(255,71,87,0.08), rgba(100,0,20,0.05))' }}>
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <div className="text-xs text-slate-400 mb-1">AI Signal for {companyName || result.ticker} ({result.ticker})</div>
                <div className="flex items-center gap-3">
                  {isUp ? <TrendingUp size={32} style={{ color: '#00e676' }} /> : <TrendingDown size={32} style={{ color: '#ff4757' }} />}
                  <div>
                    <div className="text-3xl font-bold" style={{ color: isUp ? '#00e676' : '#ff4757' }}>
                      {result.signal?.toUpperCase().replace('_', ' ')}
                    </div>
                    <div className="text-sm text-slate-400">{result.prediction_direction?.toUpperCase()} direction predicted</div>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-4xl font-bold text-white">{(prob * 100).toFixed(1)}%</div>
                <div className="text-sm text-slate-400">Probability Up</div>
              </div>
            </div>

            {/* Probability bar */}
            <div className="mt-4">
              <div className="flex justify-between text-xs text-slate-400 mb-1">
                <span>Bearish ← {((1 - prob) * 100).toFixed(1)}%</span>
                <span>{(prob * 100).toFixed(1)}% → Bullish</span>
              </div>
              <div className="h-3 rounded-full" style={{ background: 'rgba(255,255,255,0.08)' }}>
                <div className="h-full rounded-full transition-all duration-1000"
                  style={{ width: `${prob * 100}%`, background: isUp ? 'linear-gradient(90deg, #00e676, #00b8a9)' : 'linear-gradient(90deg, #ff4757, #ff6b6b)' }} />
              </div>
            </div>
          </div>

          {/* Price Targets & Confidence */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="metric-tile">
              <div className="text-xs text-slate-500 mb-1">Current Price</div>
              <div className="text-xl font-bold text-white">${result.current_price?.toFixed(2)}</div>
            </div>
            <div className="metric-tile">
              <div className="text-xs text-slate-500 mb-1">1-Day Target</div>
              <div className="text-xl font-bold" style={{ color: '#00d4ff' }}>${result.price_target_1d?.toFixed(2) ?? '—'}</div>
            </div>
            <div className="metric-tile">
              <div className="text-xs text-slate-500 mb-1">5-Day Target</div>
              <div className="text-xl font-bold" style={{ color: '#00d4ff' }}>${result.price_target_5d?.toFixed(2) ?? '—'}</div>
            </div>
            <div className="metric-tile">
              <div className="text-xs text-slate-500 mb-1">Confidence Score</div>
              <div className="text-xl font-bold text-white">{(confidence * 100).toFixed(1)}%</div>
              <div className="confidence-bar-track mt-2">
                <div className="confidence-bar-fill" style={{ width: `${confidence * 100}%`, background: 'rgba(0,212,255,0.7)' }} />
              </div>
            </div>
          </div>

          {/* Model Breakdown */}
          {result.model_breakdown?.length > 0 && (
            <div className="glass-card p-5">
              <h3 className="font-semibold text-white mb-3">Model Breakdown</h3>
              <div className="space-y-2">
                {result.model_breakdown.map((m: any) => (
                  <div key={m.model} className="flex items-center gap-3">
                    <div className="text-xs text-slate-400 w-28 flex-shrink-0 font-mono">{m.model.replace(/_/g, ' ')}</div>
                    <div className="flex-1 h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }}>
                      <div className="h-full rounded-full"
                        style={{ width: `${m.probability_up * 100}%`, background: m.probability_up > 0.5 ? '#00e676' : '#ff4757', opacity: 0.7 }} />
                    </div>
                    <div className="text-xs font-mono w-10 text-right" style={{ color: m.probability_up > 0.5 ? '#00e676' : '#ff4757' }}>
                      {(m.probability_up * 100).toFixed(0)}%
                    </div>
                    <div className={`text-xs px-2 py-0.5 rounded-full ${m.prediction === 'up' ? 'badge-bull' : 'badge-bear'}`}>
                      {m.prediction}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Model Comparison */}
      {tab === 'compare' && comparison?.model_comparison && (
        <div className="glass-card p-5">
          <h3 className="font-semibold text-white mb-4">Model Performance Comparison</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-slate-400 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
                  <th className="pb-2 text-left">Model</th>
                  <th className="pb-2 text-right">Accuracy</th>
                  <th className="pb-2 text-right">Precision</th>
                  <th className="pb-2 text-right">Recall</th>
                  <th className="pb-2 text-right">F1 Score</th>
                </tr>
              </thead>
              <tbody>
                {comparison.model_comparison.map((m: any, i: number) => (
                  <tr key={m.model} className="border-b" style={{ borderColor: 'rgba(255,255,255,0.04)' }}>
                    <td className="py-2.5 font-medium text-white flex items-center gap-2">
                      {i === 0 && <span className="text-xs" title="Best model">🏆</span>}
                      {m.model.replace(/_/g, ' ')}
                    </td>
                    <td className="py-2.5 text-right text-slate-300">{(m.accuracy * 100).toFixed(1)}%</td>
                    <td className="py-2.5 text-right text-slate-300">{(m.precision * 100).toFixed(1)}%</td>
                    <td className="py-2.5 text-right text-slate-300">{(m.recall * 100).toFixed(1)}%</td>
                    <td className="py-2.5 text-right font-semibold" style={{ color: '#00d4ff' }}>{(m.f1_score * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Multi-Timeframe */}
      {tab === 'timeframes' && timeframes?.timeframes && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(timeframes.timeframes).map(([key, tf]: any) => (
            <div key={key} className="glass-card p-5">
              <div className="text-xs text-slate-400 mb-1">{tf.horizon}</div>
              <div className="text-2xl font-bold text-white mb-1">${tf.target?.toFixed(2) ?? '—'}</div>
              <div className="text-sm font-semibold mb-3"
                style={{ color: tf.probability_up > 0.5 ? '#00e676' : '#ff4757' }}>
                {tf.signal?.toUpperCase().replace('_', ' ')} · {(tf.probability_up * 100)?.toFixed(1)}%↑
              </div>
              <div className="confidence-bar-track">
                <div className="confidence-bar-fill" style={{ width: `${tf.probability_up * 100}%`, background: '#00d4ff' }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!result && !comparison && !timeframes && !loading && (
        <div className="glass-card p-10 text-center">
          <Brain size={40} className="mx-auto mb-3" style={{ color: '#1e293b' }} />
          <p className="text-slate-500">Enter a ticker and click <strong className="text-white">Predict</strong> to run the ML ensemble</p>
          <p className="text-slate-600 text-sm mt-1">First run will auto-train models (~30-60 seconds)</p>
        </div>
      )}
    </div>
  );
}
