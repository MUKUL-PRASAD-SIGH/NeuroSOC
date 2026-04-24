import { useEffect, useMemo, useState } from 'react';
import { Activity, ShieldAlert } from 'lucide-react';
import { getCurrentVerdict, getSandboxReplay } from '../lib/portalApi';
import { readPortalSession } from '../lib/portalSession';

type VerdictSnapshot = {
  sessionId?: string | null;
  verdict: string;
  confidence: number;
  snnScore: number;
  lnnClass: string;
  xgbClass: string;
  behavioralDelta: number;
  sandbox?: { active: boolean; mode?: string; sandboxToken?: string; sandboxPath?: string } | null;
};

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export default function VerdictDisplayPage() {
  const [data, setData] = useState<VerdictSnapshot | null>(null);
  const [history, setHistory] = useState<VerdictSnapshot[]>([]);
  const [replayCount, setReplayCount] = useState<number | null>(null);
  const [sessionRef, setSessionRef] = useState(() => readPortalSession().sessionId);

  useEffect(() => {
    let mounted = true;

    const poll = async () => {
      try {
        const session = readPortalSession();
        if (mounted) {
          setSessionRef(session.sessionId);
        }

        const verdict = await getCurrentVerdict();
        if (!mounted) {
          return;
        }

        setData(verdict);
        setHistory((previous) => {
          const last = previous[0];
          if (
            last &&
            last.sessionId === verdict.sessionId &&
            last.verdict === verdict.verdict &&
            Math.abs(last.confidence - verdict.confidence) < 0.0001
          ) {
            return previous;
          }
          return [verdict, ...previous].slice(0, 10);
        });

        if (verdict.sessionId && verdict.sandbox?.active) {
          const replay = await getSandboxReplay(verdict.sessionId);
          if (mounted) {
            setReplayCount(replay.actions.length);
          }
        } else if (mounted) {
          setReplayCount(null);
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    };

    void poll();
    const interval = window.setInterval(() => {
      void poll();
    }, 2000);

    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, []);

  const iframePath = useMemo(() => {
    if (data?.sandbox?.active || data?.verdict === 'HACKER') {
      return '/security-alert';
    }
    return '/login';
  }, [data]);

  const signalRows = [
    { label: 'SNN Score', value: data ? data.snnScore.toFixed(3) : '0.000', accent: 'border-amber-400' },
    { label: 'LNN Class', value: data?.lnnClass || 'INCONCLUSIVE', accent: 'border-emerald-400' },
    { label: 'XGB Class', value: data?.xgbClass || 'INCONCLUSIVE', accent: 'border-rose-400' },
    { label: 'Behavior Δ', value: data ? data.behavioralDelta.toFixed(3) : '0.000', accent: 'border-slate-400' },
  ];

  const bars = [
    { label: 'SNN', value: data?.snnScore ?? 0, color: 'bg-amber-400' },
    { label: 'Behavior', value: data?.behavioralDelta ?? 0, color: 'bg-rose-400' },
    { label: 'Confidence', value: data?.confidence ?? 0, color: 'bg-emerald-400' },
  ];

  return (
    <div className="flex h-[calc(100vh-104px)] overflow-hidden bg-bank-bg p-6 gap-6">
      <div className="w-[450px] bg-white border border-slate-200 shadow-sm flex flex-col rounded-lg overflow-hidden shrink-0">
        <div className="h-12 bg-slate-50 border-b border-slate-200 flex items-center px-4 justify-between shrink-0">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-tighter">
            Endpoint Preview: {iframePath}
          </span>
          <div className="flex gap-1.5">
            <div className="w-2 h-2 rounded-full bg-slate-200" />
            <div className="w-2 h-2 rounded-full bg-slate-200" />
            <div className="w-2 h-2 rounded-full bg-slate-200" />
          </div>
        </div>
        <div className="flex-1 overflow-hidden">
          <iframe src={iframePath} className="w-full h-full border-none" title="NovaTrust Banking Simulation" />
        </div>
        <div className="p-4 bg-slate-50 text-center border-t border-slate-200">
          <span className="text-[9px] text-slate-400 uppercase tracking-[0.3em] font-bold">
            CLIENT_SESSION: {sessionRef || 'PENDING'}
          </span>
        </div>
      </div>

      <section className="flex-1 bg-white border border-slate-200 shadow-sm flex flex-col rounded-lg overflow-hidden">
        <div className="h-12 bg-bank-navy flex items-center px-6 justify-between shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold text-white uppercase tracking-widest">NeuroShield Analysis Panel</span>
            <span className="px-2 py-0.5 bg-rose-500 text-[10px] text-white font-mono rounded font-bold">
              LIVE THREAT MONITOR
            </span>
          </div>
          <span className="text-white/40 text-[10px] font-mono">
            {data?.sandbox?.active ? `sandbox:${data.sandbox.mode || 'live'}` : 'monitoring'}
          </span>
        </div>

        {data ? (
          <div className="p-6 grid grid-cols-2 gap-6 flex-1 overflow-hidden">
            <div className="col-span-2 grid grid-cols-4 gap-4 mb-2">
              {signalRows.map((row) => (
                <div key={row.label} className={`p-4 bg-slate-50 border-l-4 ${row.accent} rounded-r-md`}>
                  <div className="text-[10px] font-bold text-slate-500 uppercase mb-1">{row.label}</div>
                  <div className="text-xl font-mono font-bold text-slate-800 tracking-tight">{row.value}</div>
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-4 overflow-hidden">
              <div className="flex-1 border border-slate-100 p-5 rounded bg-slate-50/50 flex flex-col">
                <h3 className="text-[11px] font-bold uppercase text-slate-400 mb-4 tracking-widest">Session State</h3>
                <div className="space-y-3 font-mono text-xs text-slate-600">
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span>SESSION_ID</span>
                    <span className="font-bold">{data.sessionId || 'pending'}</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span>FINAL_VERDICT</span>
                    <span className={`font-bold ${data.verdict === 'HACKER' ? 'text-rose-600' : data.verdict === 'FORGETFUL_USER' ? 'text-amber-600' : 'text-emerald-600'}`}>
                      {data.verdict}
                    </span>
                  </div>
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span>CONFIDENCE</span>
                    <span className="font-bold">{formatPercent(data.confidence)}</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span>SANDBOX</span>
                    <span className="font-bold uppercase">{data.sandbox?.active ? data.sandbox.mode || 'active' : 'inactive'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>REPLAY_ACTIONS</span>
                    <span className="font-bold">{replayCount ?? 0}</span>
                  </div>
                </div>
              </div>

              <div className="h-40 border border-slate-100 p-5 rounded bg-slate-50/50 flex flex-col">
                <h3 className="text-[11px] font-bold uppercase text-slate-400 mb-4 tracking-widest">Confidence Matrix</h3>
                <div className="flex items-end gap-3 flex-1 px-2 pb-2">
                  {bars.map((bar) => (
                    <div key={bar.label} className="flex flex-1 flex-col items-center justify-end gap-2">
                      <div className="h-full w-full rounded-sm bg-slate-200/60 flex items-end overflow-hidden">
                        <div className={`${bar.color} w-full rounded-sm`} style={{ height: `${Math.max(bar.value * 100, 6)}%` }} />
                      </div>
                      <span className="text-[9px] font-bold uppercase tracking-widest text-slate-400">{bar.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="border border-slate-100 p-5 rounded bg-slate-50/50 flex flex-col overflow-hidden">
              <h3 className="text-[11px] font-bold uppercase text-slate-400 mb-4 tracking-widest">Live Security Log</h3>
              <div className="flex-1 overflow-auto space-y-2.5 font-mono text-[10px] custom-scrollbar">
                {history.map((entry, index) => (
                  <div key={`${entry.sessionId || 'session'}-${index}`} className="text-slate-500 flex gap-3 border-b border-slate-100 pb-2 last:border-0">
                    <span className="opacity-40">[{new Date().toLocaleTimeString([], { hour12: false })}]</span>
                    <span className={`font-bold uppercase ${entry.verdict === 'HACKER' ? 'text-rose-600' : entry.verdict === 'FORGETFUL_USER' ? 'text-amber-600' : 'text-slate-800'}`}>
                      {entry.verdict}
                    </span>
                    <span className="text-slate-400 ml-auto">P: {entry.confidence.toFixed(3)}</span>
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
            <span className="font-bold uppercase">Replay: /api/sandbox/{data?.sessionId || 'current'}/replay</span>
          </div>
          <div className="flex items-center gap-2 font-mono font-bold">
            {data?.sandbox?.active ? <ShieldAlert className="w-3.5 h-3.5 text-rose-500" /> : null}
            <span>VERDICT_ID: {(data?.sessionId || sessionRef || 'pending').toUpperCase()}</span>
          </div>
        </div>
      </section>
    </div>
  );
}
