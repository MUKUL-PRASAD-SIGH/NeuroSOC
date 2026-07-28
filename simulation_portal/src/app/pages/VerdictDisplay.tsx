import { useEffect, useMemo, useState } from 'react';
import { getCurrentVerdict, getSandboxReplay } from '../../lib/portalApi';
import { readPortalSession } from '../../lib/portalSession';

interface Verdict {
  sessionId?: string | null;
  userId?: string;
  snnScore: number;
  lnnClass: string;
  xgbClass: string;
  behavioralDelta: number;
  confidence: number;
  verdict: 'LEGITIMATE' | 'FORGETFUL_USER' | 'HACKER' | string;
  timestamp: string;
  sandbox?: { active: boolean; mode?: string; sandboxToken?: string; sandboxPath?: string } | null;
}

export default function VerdictDisplay() {
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [replayCount, setReplayCount] = useState<number | null>(null);
  const [sessionRef, setSessionRef] = useState(() => readPortalSession().sessionId);

  useEffect(() => {
    let mounted = true;

    const fetchVerdict = async () => {
      try {
        const session = readPortalSession();
        if (mounted) {
          setSessionRef(session.sessionId);
        }

        const data = await getCurrentVerdict();
        if (!mounted) {
          return;
        }

        setVerdict({
          ...data,
          timestamp: new Date().toISOString(),
        });
        setError(null);
        setLoading(false);

        if (data.sessionId && data.sandbox?.active) {
          const replay = await getSandboxReplay(data.sessionId);
          if (mounted) {
            setReplayCount(replay.actions.length);
          }
        } else if (mounted) {
          setReplayCount(null);
        }
      } catch (err) {
        if (!mounted) {
          return;
        }
        setError('Failed to fetch verdict');
        setLoading(false);
      }
    };

    // Initial fetch
    fetchVerdict();

    // Poll every 2 seconds
    const interval = setInterval(fetchVerdict, 2000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const iframePath = useMemo(() => {
    if (verdict?.sandbox?.active || verdict?.verdict === 'HACKER') {
      return '/security-alert';
    }
    return '/login';
  }, [verdict]);

  const getVerdictColor = (verdict: string, confidence: number) => {
    if (confidence < 0.5) return 'text-yellow-600 bg-yellow-100';
    if (verdict === 'HACKER') return 'text-red-600 bg-red-100';
    if (verdict === 'SUSPICIOUS' || verdict === 'FORGETFUL_USER') return 'text-amber-600 bg-amber-100';
    return 'text-green-600 bg-green-100';
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-500';
    if (confidence >= 0.5) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div className="h-screen flex">
      {/* Left Panel - Login iframe */}
      <div className="w-1/2 border-r border-gray-300">
        <div className="h-full flex flex-col">
          <div className="bg-[#002147] text-white px-6 py-4">
            <h2 className="font-['Playfair_Display'] text-xl font-bold">User Session</h2>
          </div>
          <iframe
            src={iframePath}
            className="flex-1 w-full h-full"
            title="User Session"
          />
        </div>
      </div>

      {/* Right Panel - Live Analysis */}
      <div className="w-1/2 bg-gray-900 text-white overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-blue-600 rounded flex items-center justify-center">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <h2 className="font-['Playfair_Display'] text-2xl font-bold">NeuroShield Analysis</h2>
              <p className="text-sm text-gray-400 font-['Inter']">Real-time threat detection</p>
            </div>
          </div>

          {loading && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-white mb-4"></div>
              <p className="text-gray-400 font-['Inter']">Waiting for session data...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-900/30 border border-red-500 rounded-lg p-4">
              <p className="text-red-300 font-['Inter']">{error}</p>
            </div>
          )}

          {verdict && (
            <div className="space-y-4">
              {/* Verdict Badge */}
              <div className={`rounded-lg p-6 ${getVerdictColor(verdict.verdict, verdict.confidence)}`}>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-['Playfair_Display'] text-2xl font-bold">
                    {verdict.verdict}
                  </h3>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-current rounded-full animate-pulse"></div>
                    <span className="text-sm font-['Inter']">LIVE</span>
                  </div>
                </div>
                <p className="text-sm opacity-90 font-['Inter']">User: {verdict.userId || sessionRef || 'active-session'}</p>
              </div>

              {/* Confidence Meter */}
              <div className="bg-gray-800 rounded-lg p-6">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-['Inter'] font-semibold">Confidence</h4>
                  <span className="text-2xl font-bold font-['Inter']">
                    {(verdict.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-3 overflow-hidden">
                  <div
                    className={`h-full ${getConfidenceColor(verdict.confidence)} transition-all duration-500`}
                    style={{ width: `${verdict.confidence * 100}%` }}
                  />
                </div>
              </div>

              {/* Model Outputs */}
              <div className="bg-gray-800 rounded-lg p-6">
                <h4 className="font-['Inter'] font-semibold mb-4">Neural Network Outputs</h4>
                <div className="space-y-3">
                  <div className="flex items-center justify-between py-2 border-b border-gray-700">
                    <span className="text-gray-400 font-['Inter']">SNN Score</span>
                    <span className="font-mono text-lg font-bold">
                      {verdict.snnScore.toFixed(4)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b border-gray-700">
                    <span className="text-gray-400 font-['Inter']">LNN Classification</span>
                    <span className="font-mono text-lg font-bold">
                      {verdict.lnnClass}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b border-gray-700">
                    <span className="text-gray-400 font-['Inter']">XGBoost Class</span>
                    <span className="font-mono text-lg font-bold">
                      {verdict.xgbClass}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <span className="text-gray-400 font-['Inter']">Behavioral Δ</span>
                    <span className="font-mono text-lg font-bold">
                      {verdict.behavioralDelta > 0 ? '+' : ''}
                      {verdict.behavioralDelta.toFixed(3)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Timestamp */}
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="flex items-center gap-2 text-sm text-gray-400 font-['Inter']">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>Last updated: {new Date(verdict.timestamp).toLocaleTimeString()}</span>
                </div>
                <div className="mt-2 flex items-center gap-2 text-sm text-gray-400 font-['Inter']">
                  <span>Iframe target: {iframePath}</span>
                  <span>•</span>
                  <span>Replay actions: {replayCount ?? 0}</span>
                </div>
              </div>

              {/* System Status */}
              <div className="bg-gray-800 rounded-lg p-6">
                <h4 className="font-['Inter'] font-semibold mb-4">System Status</h4>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-gray-400 font-['Inter']">Behavioral Tracking Active</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-gray-400 font-['Inter']">Neural Networks Online</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-gray-400 font-['Inter']">Honeypot Monitors Active</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-gray-400 font-['Inter']">API Integration Healthy</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${verdict.sandbox?.active ? 'bg-red-500' : 'bg-green-500'}`}></div>
                    <span className="text-sm text-gray-400 font-['Inter']">
                      Sandbox {verdict.sandbox?.active ? `${verdict.sandbox.mode || 'active'} (${replayCount ?? 0} actions)` : 'inactive'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
