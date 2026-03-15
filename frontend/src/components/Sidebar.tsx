'use client';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard, Search, Brain, FlaskConical,
  Briefcase, Lightbulb, TrendingUp, Settings
} from 'lucide-react';

const navItems = [
  { href: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/explorer', icon: Search, label: 'Stock Explorer' },
  { href: '/prediction', icon: Brain, label: 'Price Forecasts' },
  { href: '/strategy-lab', icon: FlaskConical, label: 'Backtest Strategies' },
  { href: '/portfolio', icon: Briefcase, label: 'Portfolio Builder' },
  { href: '/ai-insights', icon: Lightbulb, label: 'AI Insights' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <aside
      className="sidebar fixed left-0 top-0 h-full z-40 flex flex-col"
      style={{
        width: '220px',
        background: 'linear-gradient(180deg, #0a0f1e 0%, #070b14 100%)',
        borderRight: '1px solid rgba(255,255,255,0.06)',
        backdropFilter: 'blur(20px)',
      }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 pt-6 pb-8">
        <div
          className="flex items-center justify-center rounded-xl"
          style={{
            width: 36, height: 36,
            background: 'linear-gradient(135deg, rgba(0,212,255,0.9) 0%, rgba(0,100,255,0.9) 100%)',
            boxShadow: '0 0 20px rgba(0,212,255,0.4)',
          }}
        >
          <TrendingUp size={18} style={{ color: '#070b14' }} strokeWidth={2.5} />
        </div>
        <div>
          <div className="font-bold text-sm text-white" style={{ letterSpacing: '-0.3px' }}>StockAI</div>
          <div className="text-xs" style={{ color: '#00d4ff', opacity: 0.7 }}>Market Intelligence</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 space-y-1">
        {navItems.map(({ href, icon: Icon, label }) => {
          const isActive = pathname === href;
          return (
            <button
              key={href}
              onClick={() => router.push(href)}
              className={`nav-link w-full text-left ${isActive ? 'active' : ''}`}
            >
              <Icon size={16} />
              <span>{label}</span>
              {isActive && (
                <div
                  className="ml-auto w-1.5 h-1.5 rounded-full"
                  style={{ background: '#00d4ff', boxShadow: '0 0 6px #00d4ff' }}
                />
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom */}
      <div className="px-3 pb-6 space-y-1">
        <div className="border-t mb-3" style={{ borderColor: 'rgba(255,255,255,0.06)' }} />
        <div className="nav-link" style={{ cursor: 'default' }}>
          <Settings size={16} />
          <span>Settings</span>
        </div>
        <div className="px-3 py-2 rounded-xl text-xs leading-relaxed" style={{ background: 'rgba(0,212,255,0.06)', color: '#64748b' }}>
          <div className="text-green-400 text-xs mb-1 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block animate-pulse-slow" />
            Live Market Data
          </div>
          Powered by Yahoo Finance & ML models
        </div>
      </div>
    </aside>
  );
}
