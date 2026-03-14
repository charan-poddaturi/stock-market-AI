'use client';
import { useState } from 'react';
import { Search, Bell, User, Cpu, Zap } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { resolveTicker } from '@/lib/api';

export default function TopBar() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      setLoading(true);
      const symbol = await resolveTicker(query);
      router.push(`/explorer?ticker=${symbol}`);
      setLoading(false);
    }
  };

  return (
    <header
      className="fixed top-0 right-0 z-30 flex items-center gap-4 px-6 py-3"
      style={{
        left: '220px',
        background: 'rgba(7,11,20,0.85)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        backdropFilter: 'blur(20px)',
        height: '64px',
      }}
    >
      {/* Search */}
      <form onSubmit={handleSearch} className="flex-1 max-w-lg">
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: '#4b5563' }} />
          <input
            type="text"
            placeholder={loading ? "Resolving..." : "Search ticker or company (AAPL, Tesla...)"}
            value={query}
            onChange={e => setQuery(e.target.value)}
            disabled={loading}
            className="input-dark pl-9 text-sm w-full"
            style={{ height: '38px', opacity: loading ? 0.7 : 1 }}
          />
        </div>
      </form>

      {/* Status badge */}
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium" style={{ background: 'rgba(0,230,118,0.08)', color: '#00e676', border: '1px solid rgba(0,230,118,0.2)' }}>
        <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse-slow" />
        Markets Live
      </div>

      {/* Mode toggle */}
      <div className="flex items-center rounded-full p-0.5 text-xs font-medium" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
        <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-full" style={{ background: 'rgba(0,212,255,0.12)', color: '#00d4ff' }}>
          <Zap size={12} /> Beginner
        </button>
        <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-full" style={{ color: '#64748b' }}>
          <Cpu size={12} /> Expert
        </button>
      </div>

      {/* Actions */}
      <button className="w-9 h-9 rounded-full flex items-center justify-center" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
        <Bell size={16} style={{ color: '#64748b' }} />
      </button>
      <button className="w-9 h-9 rounded-full flex items-center justify-center" style={{ background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.2)' }}>
        <User size={16} style={{ color: '#00d4ff' }} />
      </button>
    </header>
  );
}
