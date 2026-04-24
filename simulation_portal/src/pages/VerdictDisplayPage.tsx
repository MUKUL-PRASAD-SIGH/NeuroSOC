import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Shield, BrainCircuit, Activity, ChevronRight, AlertTriangle, CheckCircle } from 'lucide-react';
import { apiJson } from '../lib/apiClient';

export default function VerdictDisplayPage() {
  const [data, setData] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    const poll = async () => {
      try {
        const json = await apiJson<any>('/api/verdicts/current');
        setData(json);
        setHistory(prev => [json, ...prev.slice(0, 9)]);
      } catch (e) {
        console.error('Polling error:', e);
      }
    };

    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (val: number) => {
    if (val < 0.3) return 'text-green-500';
    if (val < 0.7) return 'text-amber-500';
    return 'text-red-500';
  };

  const getBgColor = (verdict: string) => {
    if (verdict === 'TRUSTED' || verdict === 'LEGITIMATE') return 'bg-green-500/10 border-green-500/20';
    if (verdict === 'HACKER') return 'bg-red-500/10 border-red-500/20';
    return 'bg-amber-500/10 border-amber-500/20';
  };

  return (
    <div className="flex h-[calc(100vh-104px)] overflow-hidden bg-bank-bg p-6 gap-6">
      {/* Simulation Iframe Container */}
      <div className="w-[450px] bg-white border border-slate-200 shadow-sm flex flex-col rounded-lg overflow-hidden shrink-0">
        <div className="h-12 bg-slate-50 border-b border-slate-200 flex items-center px-4 justify-between shrink-0">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-tighter">Endpoint Preview: /login</span>
          <div className="flex gap-1.5">
            <div className="w-2 h-2 rounded-full bg-slate-200" />
            <div className="w-2 h-2 rounded-full bg-slate-200" />
            <div className="w-2 h-2 rounded-full bg-slate-200" />
          </div>
        </div>
        <div className="flex-1 overflow-hidden">
          <iframe 
            src="/login" 
            className="w-full h-full border-none"
            title="NovaTrust Banking Simulation"
          />
        </div>
        <div className="p-4 bg-slate-50 text-center border-t border-slate-200">
          <span className="text-[9px] text-slate-400 uppercase tracking-[0.3em] font-bold">CLIENT_SESSION: NT-8842-XKB</span>
        </div>
      </div>

      {/* Analysis Panel */}
      <section className="flex-1 bg-white border border-slate-200 shadow-sm flex flex-col rounded-lg overflow-hidden">
        <div className="h-12 bg-bank-navy flex items-center px-6 justify-between shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold text-white uppercase tracking-widest">NeuroShield Analysis Panel</span>
            <span className="px-2 py-0.5 bg-rose-500 text-[10px] text-white font-mono rounded font-bold">LIVE THREAT MONITOR</span>
          </div>
          <span className="text-white/40 text-[10px] font-mono">v4.2.1-stable</span>
        </div>

        {data ? (
          <div className="p-6 grid grid-cols-2 gap-6 flex-1 overflow-hidden">
            <div className="col-span-2 grid grid-cols-4 gap-4 mb-2">
              <div className="p-4 bg-slate-50 border-l-4 border-amber-400 rounded-r-md">
                <div className="text-[10px] font-bold text-slate-500 uppercase mb-1">SNN Score</div>
                <div className="text-2xl font-mono font-bold text-slate-800">{data.snnScore.toFixed(3)}</div>
              </div>
              <div className="p-4 bg-slate-50 border-l-4 border-emerald-400 rounded-r-md">
                <div className="text-[10px] font-bold text-slate-500 uppercase mb-1">LNN Class</div>
                <div className="text-2xl font-mono font-bold text-slate-800 tracking-tighter">NOMINAL</div>
              </div>
              <div className="p-4 bg-slate-50 border-l-4 border-rose-400 rounded-r-md">
                <div className="text-[10px] font-bold text-slate-500 uppercase mb-1">XGBoost Prob</div>
                <div className="text-2xl font-mono font-bold text-slate-800">{(data.confidence * 100).toFixed(1)}%</div>
              </div>
              <div className="p-4 bg-slate-900 text-white border-l-4 border-amber-500 rounded-r-md shadow-lg">
                <div className="text-[10px] font-bold text-amber-500 uppercase mb-1">Final Verdict</div>
                <div className={`text-2xl font-bold tracking-tight ${data.verdict === 'HACKER' ? 'text-rose-500' : 'text-emerald-400'}`}>
                  {data.verdict}
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-4 overflow-hidden">
              <div className="flex-1 border border-slate-100 p-5 rounded bg-slate-50/50 flex flex-col">
                <h3 className="text-[11px] font-bold uppercase text-slate-400 mb-4 tracking-widest">Behavioral Delta (Δ)</h3>
                <div className="space-y-3 font-mono text-xs text-slate-600">
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span>EYE_TRACK_LATENCY:</span>
                    <span className="text-amber-600 font-bold">+12.4ms</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span>KEY_DWELL_AVG:</span>
                    <span className="text-emerald-600 font-bold">48ms</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span>HOVER_ENTROPY:</span>
                    <span className="text-slate-800 font-bold">0.842 bits</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span>PATH_NONLINEARITY:</span>
                    <span className="text-rose-600 font-bold">HIGH</span>
                  </div>
                  <div className="flex justify-between">
                    <span>BOT_HONEYPOT:</span>
                    <span className="text-emerald-600 font-bold uppercase">Safe</span>
                  </div>
                </div>
              </div>
              
              <div className="h-40 border border-slate-100 p-5 rounded bg-slate-50/50 flex flex-col">
                <h3 className="text-[11px] font-bold uppercase text-slate-400 mb-4 tracking-widest">Confidence Matrix</h3>
                <div className="flex items-end gap-1.5 flex-1 px-2 pb-2">
                  {[...Array(8)].map((_, i) => (
                    <motion.div 
                      key={i}
                      initial={{ height: 0 }}
                      animate={{ height: `${Math.random() * 80 + 20}%` }}
                      className={`flex-1 rounded-t-sm ${i > 5 ? 'bg-amber-400' : 'bg-emerald-400'}`} 
                    />
                  ))}
                </div>
                <div className="flex justify-between text-[8px] text-slate-400 uppercase mt-2 font-bold tracking-widest">
                  <span>T-10s</span>
                  <span>Real-time Buffer</span>
                  <span>Active</span>
                </div>
              </div>
            </div>

            <div className="border border-slate-100 p-5 rounded bg-slate-50/50 flex flex-col overflow-hidden">
              <h3 className="text-[11px] font-bold uppercase text-slate-400 mb-4 tracking-widest">Live Security Log</h3>
              <div className="flex-1 overflow-auto space-y-2.5 font-mono text-[10px] custom-scrollbar">
                {history.map((h, i) => (
                  <div key={i} className="text-slate-500 flex gap-3 border-b border-slate-100 pb-2 last:border-0">
                    <span className="opacity-40">[{new Date().toLocaleTimeString([], { hour12: false })}]</span>
                    <span className={`font-bold uppercase ${h.verdict === 'HACKER' ? 'text-rose-600' : 'text-slate-800'}`}>
                      {h.verdict}
                    </span>
                    <span className="text-slate-400 ml-auto">P: {h.confidence.toFixed(3)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 text-slate-400 bg-slate-50/30">
            <Activity className="w-8 h-8 animate-pulse" />
            <span className="text-[11px] font-bold uppercase tracking-[0.2em]">Synchronizing Neural Core...</span>
          </div>
        )}

        <div className="h-12 px-6 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400 shrink-0">
          <div className="flex gap-6">
            <span className="font-bold uppercase">Endpoint: /api/verdicts/current</span>
            <span className="font-bold uppercase">Stream: Webhook/NeuroChannel [v4]</span>
          </div>
          <span className="font-mono font-bold">VERDICT_ID: {Math.random().toString(36).substring(2, 10).toUpperCase()}</span>
        </div>
      </section>
    </div>
  );
}
