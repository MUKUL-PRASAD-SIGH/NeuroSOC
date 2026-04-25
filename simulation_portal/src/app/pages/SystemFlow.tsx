import { useEffect, useMemo, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { getModelVersion, type PortalVerdictSnapshot } from '../../lib/portalApi';
import {
  PORTAL_SCENARIO_LIBRARY,
  portalScenarioRunners,
  type FlowInfoPanel,
  type FlowLog,
  type FlowPhase,
  type FlowScene,
  type FlowScenePatch,
  type ScenarioMeta,
} from '../../lib/systemFlowScenarios';

const THEATER_PHASES: Array<{ id: FlowPhase; label: string; code: string }> = [
  { id: 'portal', label: 'Portal Session', code: 'P01' },
  { id: 'behavioral', label: 'Behavior Stream', code: 'P02' },
  { id: 'ensemble', label: 'SNN + LNN + XGB', code: 'P03' },
  { id: 'decision', label: 'Decision Layer', code: 'P04' },
  { id: 'route', label: 'Route Outcome', code: 'P05' },
  { id: 'feedback', label: 'Feedback Loop', code: 'P06' },
  { id: 'retraining', label: 'Retrain Guard', code: 'P07' },
];

const PHASE_ORDER = THEATER_PHASES.reduce<Record<string, number>>((accumulator, phase, index) => {
  accumulator[phase.id] = index;
  return accumulator;
}, {});

const ACCENT_TOKENS = {
  emerald: {
    halo: 'from-emerald-500/28 via-emerald-400/14 to-transparent',
    border: 'border-emerald-300/60',
    badge: 'border-emerald-300/60 bg-emerald-500/12 text-emerald-100',
    text: 'text-emerald-100',
    soft: 'bg-emerald-500/12',
    chip: 'border-emerald-200/35 bg-emerald-400/10 text-emerald-50',
  },
  amber: {
    halo: 'from-amber-500/28 via-amber-300/14 to-transparent',
    border: 'border-amber-300/60',
    badge: 'border-amber-300/60 bg-amber-500/12 text-amber-100',
    text: 'text-amber-100',
    soft: 'bg-amber-500/12',
    chip: 'border-amber-200/35 bg-amber-400/10 text-amber-50',
  },
  rose: {
    halo: 'from-rose-500/28 via-rose-300/14 to-transparent',
    border: 'border-rose-300/60',
    badge: 'border-rose-300/60 bg-rose-500/12 text-rose-100',
    text: 'text-rose-100',
    soft: 'bg-rose-500/12',
    chip: 'border-rose-200/35 bg-rose-400/10 text-rose-50',
  },
  cyan: {
    halo: 'from-sky-400/28 via-cyan-300/14 to-transparent',
    border: 'border-cyan-300/60',
    badge: 'border-cyan-300/60 bg-cyan-500/12 text-cyan-100',
    text: 'text-cyan-100',
    soft: 'bg-cyan-500/12',
    chip: 'border-cyan-200/35 bg-cyan-400/10 text-cyan-50',
  },
  neutral: {
    halo: 'from-slate-400/18 via-slate-200/8 to-transparent',
    border: 'border-slate-300/55',
    badge: 'border-slate-300/55 bg-white/10 text-slate-100',
    text: 'text-slate-100',
    soft: 'bg-white/8',
    chip: 'border-slate-200/35 bg-white/8 text-slate-100',
  },
} as const;

const ROUTE_LANES = [
  {
    key: 'safe',
    title: 'No Sandbox',
    detail: 'Real portal, clean outcome, customer stays happy.',
  },
  {
    key: 'review',
    title: 'Soft Review Timeout',
    detail: 'Session pauses, reload returns the user safely.',
  },
  {
    key: 'sandbox',
    title: 'Hard Sandbox',
    detail: 'Decoy-only isolation with replay capture.',
  },
];

const dashboardInputs = [
  {
    title: 'Analyst stats',
    endpoint: 'GET /api/stats',
    detail: 'Top-row totals in the NeuroSOC dashboard.',
  },
  {
    title: 'Model status',
    endpoint: 'GET /api/model/version',
    detail: 'Primary model, ruleset, validation F1, and last retrain time.',
  },
  {
    title: 'Alert feed',
    endpoint: 'GET /api/alerts + WS /ws/alerts',
    detail: 'Backlog plus live streaming alerts for the analyst surface.',
  },
];

const ingestPaths = [
  {
    title: 'Raw network ingest',
    endpoint: 'POST /ingest',
    detail: 'Packet-like events go to the ingestion service, then Kafka, feature extraction, and inference.',
  },
  {
    title: 'Behavioral portal ingest',
    endpoint: 'POST /api/behavioral',
    detail: 'Keystrokes, mouse movement, page context, and the portal session id.',
  },
  {
    title: 'Bank actions',
    endpoint: 'POST /api/bank/login + POST /api/bank/transfer',
    detail: 'The live NovaTrust simulation flows that produce verdicts and alerts.',
  },
];

const EMPTY_SCENE: FlowScene = {
  browser: {
    tone: 'neutral',
    eyebrow: 'Scenario theater idle',
    title: 'Choose one of the three live roles',
    subtitle: 'The portal will animate the real pipeline while the endpoints are being hit.',
    lines: [
      'Trusted customer -> real dashboard.',
      'Flagged but innocent -> timeout and safe reload.',
      'Active hacker -> hard sandbox with feedback and retraining eligibility.',
    ],
    badge: 'READY',
  },
  route: {
    kind: 'idle',
    title: 'Decision route waiting',
    detail: 'No branch has been selected yet.',
    footer: 'Pick a role to drive the full story.',
  },
  feedback: {
    tone: 'neutral',
    title: 'Feedback loop idle',
    detail: 'No session has produced a label yet.',
    chips: ['Awaiting run'],
  },
  retraining: {
    tone: 'neutral',
    title: 'Retraining loop idle',
    detail: 'The model remains on the current production version until a run earns a strong label.',
    chips: ['No delta'],
  },
};

function mergeScene(previous: FlowScene, patch: FlowScenePatch = {}): FlowScene {
  return {
    ...previous,
    ...patch,
    browser: patch.browser || previous.browser,
    route: patch.route || previous.route,
    feedback: patch.feedback || previous.feedback,
    retraining: patch.retraining || previous.retraining,
  };
}

function tokenFor(tone: keyof typeof ACCENT_TOKENS) {
  return ACCENT_TOKENS[tone] || ACCENT_TOKENS.neutral;
}

function statusClasses(status: FlowLog['status']) {
  if (status === 'success') return 'border-emerald-200/40 bg-emerald-500/12 text-emerald-100';
  if (status === 'warning') return 'border-amber-200/40 bg-amber-500/12 text-amber-100';
  if (status === 'error') return 'border-rose-200/45 bg-rose-500/12 text-rose-100';
  return 'border-cyan-200/40 bg-cyan-500/12 text-cyan-100';
}

function ActorAvatar({ scenario, large = false }: { scenario: ScenarioMeta; large?: boolean }) {
  const tokens = tokenFor(scenario.accent);

  return (
    <div
      className={`relative inline-flex items-center justify-center overflow-hidden rounded-[24px] border font-semibold ${tokens.border} ${tokens.soft} ${
        large ? 'h-16 w-16 text-xl' : 'h-12 w-12 text-sm'
      }`}
    >
      <div className={`absolute inset-0 bg-gradient-to-br ${tokens.halo}`} />
      <span className="relative text-white">{scenario.initials}</span>
    </div>
  );
}

function ScenarioCard({
  scenario,
  isActive,
  isRunning,
  onRun,
}: {
  scenario: ScenarioMeta;
  isActive: boolean;
  isRunning: boolean;
  onRun: (scenarioKey: string) => void;
}) {
  const tokens = tokenFor(scenario.accent);

  return (
    <article
      className={`relative overflow-hidden rounded-[26px] border bg-[rgba(7,17,31,0.92)] p-4 transition-all duration-300 ${
        isActive ? `${tokens.border} shadow-[0_20px_60px_rgba(2,6,23,0.45)]` : 'border-white/10'
      }`}
    >
      <div className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${tokens.halo}`} />
      <div className="relative">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <ActorAvatar scenario={scenario} />
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">{scenario.role}</p>
              <h3 className="mt-1 text-base font-semibold text-white">{scenario.title}</h3>
              <p className="text-sm text-slate-300">{scenario.actorName}</p>
            </div>
          </div>
          <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${tokens.badge}`}>
            {scenario.expectedLane}
          </span>
        </div>

        <div className="mt-4 grid gap-2 text-sm text-slate-200">
          <p><span className="font-semibold text-slate-400">Source IP:</span> {scenario.ipAddress}</p>
          <p><span className="font-semibold text-slate-400">Device:</span> {scenario.device}</p>
          <p className="text-slate-300">{scenario.expectation}</p>
        </div>

        <button
          type="button"
          disabled={isRunning}
          onClick={() => onRun(scenario.key)}
          className={`mt-4 inline-flex rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition-colors ${
            isActive ? `${tokens.badge} hover:brightness-110` : 'border-white/15 bg-white/5 text-white hover:border-cyan-200/40'
          } disabled:cursor-not-allowed disabled:opacity-50`}
        >
          {isRunning && isActive ? 'Running...' : 'Run Live'}
        </button>
      </div>
    </article>
  );
}

function PipelineNode({ phase, activePhase }: { phase: (typeof THEATER_PHASES)[number]; activePhase: FlowPhase | null }) {
  const currentIndex = activePhase ? PHASE_ORDER[activePhase] : undefined;
  const thisIndex = PHASE_ORDER[phase.id];
  const isActive = phase.id === activePhase;
  const isComplete = currentIndex !== undefined && thisIndex < currentIndex;

  return (
    <div
      className={`nt-flow-node rounded-[22px] border px-4 py-3 ${
        isActive
          ? 'nt-flow-node-active border-cyan-300/50 bg-cyan-500/12'
          : isComplete
            ? 'border-emerald-300/40 bg-emerald-500/12'
            : 'border-white/12 bg-white/5'
      }`}
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">{phase.code}</p>
          <p className={`mt-1 text-sm font-semibold ${isActive ? 'text-cyan-100' : 'text-white'}`}>{phase.label}</p>
        </div>
        <div
          className={`h-2.5 w-2.5 rounded-full ${
            isActive ? 'bg-cyan-300 shadow-[0_0_18px_rgba(103,232,249,0.7)]' : isComplete ? 'bg-emerald-300' : 'bg-slate-500'
          }`}
        />
      </div>
    </div>
  );
}

function BrowserMock({ browser, scenario }: { browser: FlowScene['browser']; scenario: ScenarioMeta }) {
  const tokens = tokenFor(browser.tone);

  return (
    <div className="nt-flow-tilt-panel rounded-[30px] border border-white/10 bg-[#070c18] p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-rose-400" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-300" />
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-300" />
        </div>
        <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${tokens.badge}`}>
          {browser.badge}
        </span>
      </div>

      <div className="mt-4 rounded-[24px] border border-white/10 bg-[rgba(14,22,38,0.88)] p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">{browser.eyebrow}</p>
            <h3 className="mt-1 text-lg font-semibold text-white">{browser.title}</h3>
            <p className="mt-2 text-sm text-slate-300">{browser.subtitle}</p>
          </div>
          <ActorAvatar scenario={scenario} />
        </div>

        <div className="mt-4 space-y-2">
          {(Array.isArray(browser.lines) ? browser.lines : []).map((line) => (
            <div key={line} className="rounded-[18px] border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-100">
              {line}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RouteBoard({ route }: { route: FlowScene['route'] }) {
  return (
    <div className="rounded-[26px] border border-white/10 bg-black/20 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Route Board</p>
      <div className="mt-4 grid gap-3">
        {ROUTE_LANES.map((lane) => {
          const active = route.kind === lane.key;
          const color =
            lane.key === 'safe'
              ? active
                ? 'border-emerald-300/40 bg-emerald-500/12 text-emerald-100'
                : 'border-white/10 bg-white/5 text-slate-400'
              : lane.key === 'review'
                ? active
                  ? 'border-amber-300/40 bg-amber-500/12 text-amber-100'
                  : 'border-white/10 bg-white/5 text-slate-400'
                : active
                  ? 'border-rose-300/45 bg-rose-500/12 text-rose-100'
                  : 'border-white/10 bg-white/5 text-slate-400';

          return (
            <div key={lane.key} className={`rounded-[18px] border px-3 py-3 transition-all ${color}`}>
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold">{lane.title}</p>
                <span className="text-[10px] font-semibold uppercase tracking-[0.16em]">{active ? 'active' : 'idle'}</span>
              </div>
              <p className="mt-2 text-xs">{active ? route.detail : lane.detail}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-4 rounded-[18px] border border-white/10 bg-white/5 px-3 py-3">
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">Current route summary</p>
        <p className="mt-2 text-sm font-semibold text-white">{route.title}</p>
        <p className="mt-2 text-sm text-slate-300">{route.footer}</p>
      </div>
    </div>
  );
}

function InfoCard({
  label,
  panel,
}: {
  label: string;
  panel: FlowInfoPanel;
}) {
  const tokens = tokenFor(panel.tone);

  return (
    <div className="rounded-[24px] border border-white/10 bg-black/20 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{label}</p>
        <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${tokens.badge}`}>
          {panel.tone}
        </span>
      </div>
      <h3 className="mt-3 text-base font-semibold text-white">{panel.title}</h3>
      <p className="mt-2 text-sm text-slate-300">{panel.detail}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {panel.chips.map((chip) => (
          <span key={chip} className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${tokens.chip}`}>
            {chip}
          </span>
        ))}
      </div>
    </div>
  );
}

function VerdictCard({ verdict }: { verdict: PortalVerdictSnapshot | null }) {
  if (!verdict) {
    return (
      <div className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Decision Telemetry</p>
        <p className="mt-3 text-sm text-slate-500">Verdict metrics will appear here as soon as the live run reaches the decision layer.</p>
      </div>
    );
  }

  const verdictLabel = verdict.verdict || 'INCONCLUSIVE';
  const verdictTone =
    verdictLabel === 'HACKER' ? 'rose' : verdictLabel === 'FORGETFUL_USER' ? 'amber' : verdictLabel === 'LEGITIMATE' ? 'emerald' : 'neutral';
  const tokens = tokenFor(verdictTone);

  const metricCards = [
    { label: 'Confidence', value: `${Math.round((Number(verdict.confidence || 0) || 0) * 100)}%` },
    { label: 'SNN', value: `${Math.round((Number(verdict.snnScore || 0) || 0) * 100)}%` },
    { label: 'LNN', value: verdict.lnnClass || '—' },
    { label: 'XGBoost', value: verdict.xgbClass || '—' },
  ];

  return (
    <div className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Decision Telemetry</p>
        <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${tokens.badge.replace('text-', 'text-').replace('bg-', 'bg-')}`}>
          {verdictLabel}
        </span>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {metricCards.map((metric) => (
          <div key={metric.label} className="rounded-[18px] border border-slate-200 bg-slate-50 px-3 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">{metric.label}</p>
            <p className={`mt-2 text-sm font-semibold ${verdictTone === 'rose' ? 'text-rose-700' : verdictTone === 'amber' ? 'text-amber-700' : verdictTone === 'emerald' ? 'text-emerald-700' : 'text-slate-700'}`}>
              {metric.value}
            </p>
          </div>
        ))}
      </div>
      <div className="mt-4 rounded-[18px] border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-500">
        Session <span className="font-semibold text-slate-800">{verdict.sessionId || 'pending'}</span>
        {verdict.sandbox?.active ? (
          <span className="ml-2 rounded-full border border-rose-200 bg-rose-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-rose-700">
            sandbox active
          </span>
        ) : null}
      </div>
    </div>
  );
}

function TracePanel({ logs, runError, usedFallback }: { logs: FlowLog[]; runError: string; usedFallback: boolean }) {
  return (
    <div className="rounded-[26px] border border-white/10 bg-[rgba(7,17,31,0.92)] p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Execution Trace</p>
        {usedFallback ? (
          <span className="rounded-full border border-amber-200/40 bg-amber-500/12 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-amber-100">
            fallback used
          </span>
        ) : null}
      </div>

      {runError ? (
        <div className="mt-4 rounded-[18px] border border-rose-200/45 bg-rose-500/12 px-4 py-3 text-sm text-rose-100">
          {runError}
        </div>
      ) : null}

      <div className="mt-4 space-y-3">
        {logs.length === 0 ? (
          <div className="rounded-[18px] border border-dashed border-white/12 bg-black/20 px-4 py-5 text-sm text-slate-400">
            Pick one of the three roles and the portal will animate the live path while the trace fills in.
          </div>
        ) : null}

        {logs.map((item) => (
          <article key={item.id} className="rounded-[18px] border border-white/10 bg-black/20 p-3">
            <div className="flex items-center justify-between gap-3">
              <h4 className="text-sm font-semibold text-white">{item.title}</h4>
              <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${statusClasses(item.status)}`}>
                {item.status}
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-300">{item.detail}</p>
            {item.endpoint ? <p className="mt-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-cyan-100">{item.endpoint}</p> : null}
            {item.payload ? (
              <pre className="mt-3 overflow-x-auto rounded-[16px] border border-white/10 bg-[#040914] p-3 text-xs text-slate-200">
                {JSON.stringify(item.payload, null, 2)}
              </pre>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}

// ── Step Popup ────────────────────────────────────────────────────────────────

const PHASE_VISUALS: Record<string, { icon: string; color: string; glow: string; bg: string; border: string }> = {
  portal:     { icon: '🏦', color: 'text-cyan-100',   glow: 'rgba(103,232,249,0.35)',  bg: 'rgba(8,145,178,0.18)',   border: 'rgba(103,232,249,0.4)' },
  behavioral: { icon: '🖱️', color: 'text-violet-100', glow: 'rgba(167,139,250,0.35)', bg: 'rgba(109,40,217,0.18)',  border: 'rgba(167,139,250,0.4)' },
  ensemble:   { icon: '🧠', color: 'text-sky-100',    glow: 'rgba(56,189,248,0.35)',  bg: 'rgba(2,132,199,0.18)',   border: 'rgba(56,189,248,0.4)'  },
  decision:   { icon: '⚖️', color: 'text-amber-100',  glow: 'rgba(251,191,36,0.35)',  bg: 'rgba(180,83,9,0.18)',    border: 'rgba(251,191,36,0.4)'  },
  route:      { icon: '🔀', color: 'text-emerald-100',glow: 'rgba(52,211,153,0.35)',  bg: 'rgba(4,120,87,0.18)',    border: 'rgba(52,211,153,0.4)'  },
  feedback:   { icon: '📡', color: 'text-rose-100',   glow: 'rgba(251,113,133,0.35)', bg: 'rgba(159,18,57,0.18)',   border: 'rgba(251,113,133,0.4)' },
  retraining: { icon: '🔁', color: 'text-orange-100', glow: 'rgba(251,146,60,0.35)',  bg: 'rgba(154,52,18,0.18)',   border: 'rgba(251,146,60,0.4)'  },
};

const PHASE_HUMAN: Record<string, { title: string; what: string }> = {
  portal:     { title: 'Portal Session Opening',       what: 'The bank portal creates a live session and arms the behavioural tracker.' },
  behavioral: { title: 'Behavioural Stream Active',    what: 'Keystrokes, mouse moves, and click timing are being captured and vectorised.' },
  ensemble:   { title: 'SNN + LNN + XGBoost Scoring',  what: 'Three models fuse their scores — spike anomaly, behavioural drift, and traffic class.' },
  decision:   { title: 'Decision Layer Firing',        what: 'The weighted confidence score is compared against the sandbox threshold.' },
  route:      { title: 'Route Outcome Determined',     what: 'The session is assigned to safe, review, or hard sandbox based on the verdict.' },
  feedback:   { title: 'Feedback Loop Triggered',      what: 'The outcome is labelled and queued for the security feedback pipeline.' },
  retraining: { title: 'Retraining Guard Evaluated',   what: 'The model checks whether this run earns a malicious sample for the next retrain cycle.' },
};

interface StepPopupProps {
  phase: FlowPhase | null;
  browser: FlowScene['browser'] | null;
  verdict: PortalVerdictSnapshot | null;
  triggerKey: number;
  onDismiss: () => void;
}

function StepPopup({ phase, browser, verdict, triggerKey, onDismiss }: StepPopupProps) {
  const [progress, setProgress] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!phase || triggerKey === 0) return;
    setProgress(0);
    setVisible(true);
    const start = performance.now();
    const duration = 4500;
    let raf: number;
    const tick = (now: number) => {
      const pct = Math.min(100, ((now - start) / duration) * 100);
      setProgress(pct);
      if (pct < 100) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    const timer = window.setTimeout(() => {
      setVisible(false);
    }, duration + 300);
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(timer);
    };
  }, [phase, triggerKey]);

  if (!phase || !visible) return null;

  const vis = PHASE_VISUALS[phase] || PHASE_VISUALS.portal;
  const human = PHASE_HUMAN[phase] || { title: phase, what: '' };
  const phaseIndex = THEATER_PHASES.findIndex((p) => p.id === phase);
  const totalPhases = THEATER_PHASES.length;

  const showVerdictBadge = ['decision', 'route', 'feedback', 'retraining'].includes(phase);
  const verdictLabel = showVerdictBadge ? (verdict?.verdict || browser?.badge || null) : null;
  const verdictColor =
    verdictLabel === 'HACKER' ? '#f87171' :
    verdictLabel === 'LEGITIMATE' ? '#6ee7b7' :
    verdictLabel === 'FORGETFUL_USER' ? '#fcd34d' : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(2,6,23,0.82)', backdropFilter: 'blur(18px)' }}
      onClick={onDismiss}
    >
      {/* Glow blob */}
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <div style={{
          width: '520px', height: '520px', borderRadius: '50%',
          background: `radial-gradient(circle, ${vis.glow} 0%, transparent 70%)`,
          filter: 'blur(40px)',
        }} />
      </div>

      <div
        className="relative mx-4 w-full max-w-lg overflow-hidden rounded-[32px] p-8"
        style={{
          background: `linear-gradient(135deg, ${vis.bg}, rgba(4,9,20,0.95))`,
          border: `1px solid ${vis.border}`,
          boxShadow: `0 40px 120px rgba(0,0,0,0.6), 0 0 60px ${vis.glow}`,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Step counter */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {THEATER_PHASES.map((p, i) => (
              <div
                key={p.id}
                className="rounded-full transition-all duration-300"
                style={{
                  width: i === phaseIndex ? '24px' : '8px',
                  height: '8px',
                  background: i === phaseIndex ? vis.border : i < phaseIndex ? 'rgba(255,255,255,0.4)' : 'rgba(255,255,255,0.12)',
                }}
              />
            ))}
          </div>
          <span className="text-[11px] font-semibold tracking-widest" style={{ color: vis.border }}>
            {phaseIndex + 1} / {totalPhases}
          </span>
        </div>

        {/* Icon */}
        <div className="mb-5 flex items-center gap-4">
          <div
            className="flex h-20 w-20 flex-shrink-0 items-center justify-center rounded-[22px] text-4xl"
            style={{ background: vis.bg, border: `1px solid ${vis.border}`, boxShadow: `0 0 30px ${vis.glow}` }}
          >
            {vis.icon}
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em]" style={{ color: vis.border }}>
              {THEATER_PHASES[phaseIndex]?.code} · Pipeline Step
            </p>
            <h2 className="mt-1 text-2xl font-bold text-white leading-tight">{human.title}</h2>
          </div>
        </div>

        {/* What's happening */}
        <p className="mb-5 text-base leading-relaxed" style={{ color: 'rgba(255,255,255,0.7)' }}>
          {human.what}
        </p>

        {/* Live browser state */}
        {browser && (
          <div
            className="mb-5 rounded-[20px] p-4"
            style={{ background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(255,255,255,0.08)' }}
          >
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] mb-2" style={{ color: vis.border }}>
              {browser.eyebrow}
            </p>
            <p className="text-base font-semibold text-white mb-1">{browser.title}</p>
            <p className="text-sm" style={{ color: 'rgba(255,255,255,0.55)' }}>{browser.subtitle}</p>
            {(Array.isArray(browser.lines) ? browser.lines : []).slice(0, 2).map((line) => (
              <div
                key={line}
                className="mt-2 rounded-xl px-3 py-2 text-sm"
                style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.75)' }}
              >
                {line}
              </div>
            ))}
          </div>
        )}

        {/* Verdict badge if available */}
        {verdictLabel && verdictColor && (
          <div className="mb-6 rounded-[24px] p-5" style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.06)', boxShadow: 'inset 0 0 20px rgba(0,0,0,0.5)' }}>
            <div className="flex items-center justify-between mb-4">
              <div
                className="rounded-full px-4 py-2 text-sm font-bold tracking-widest"
                style={{ background: `${verdictColor}22`, border: `1px solid ${verdictColor}88`, color: verdictColor, textShadow: `0 0 12px ${verdictColor}` }}
              >
                {verdictLabel.replace(/_/g, ' ')}
              </div>
              {verdict?.confidence && (
                <span className="text-xl font-bold tracking-widest animate-pulse" style={{ color: verdictColor, textShadow: `0 0 20px ${verdictColor}` }}>
                  {Math.round(verdict.confidence * 100)}% RISK
                </span>
              )}
            </div>
            
            {verdict?.confidence && (
              <div className="relative h-2.5 w-full overflow-hidden rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }}>
                <div
                  className="absolute inset-y-0 left-0 rounded-full"
                  style={{
                    width: `${Math.round(verdict.confidence * 100)}%`,
                    background: `linear-gradient(90deg, transparent, ${verdictColor})`,
                    boxShadow: `0 0 15px ${verdictColor}`,
                    transition: 'width 1.5s cubic-bezier(0.16, 1, 0.3, 1)',
                  }}
                />
              </div>
            )}

            {verdict?.sandbox?.active && phase === 'route' && (
              <div className="mt-4 flex items-center gap-3 rounded-xl border border-rose-500/40 bg-rose-500/10 p-3">
                <span className="text-2xl animate-bounce">🚧</span>
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-rose-400">Hard Sandbox Isolation</p>
                  <p className="text-[11px] text-rose-200/70">Session redirected to decoy environment. Actions are being captured for replay.</p>
                </div>
              </div>
            )}
            
            {verdictLabel === 'FORGETFUL_USER' && phase === 'route' && (
              <div className="mt-4 flex items-center gap-3 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3">
                <span className="text-2xl animate-spin-slow" style={{ animationDuration: '3s' }}>⏳</span>
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-amber-400">Soft Review Timeout</p>
                  <p className="text-[11px] text-amber-200/70">Transaction paused. Forcing safe reload back to portal to contain risk.</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Progress bar */}
        <div className="relative h-1.5 w-full overflow-hidden rounded-full" style={{ background: 'rgba(255,255,255,0.08)' }}>
          <div
            className="absolute inset-y-0 left-0 rounded-full transition-none"
            style={{
              width: `${progress}%`,
              background: `linear-gradient(90deg, ${vis.border}, rgba(255,255,255,0.8))`,
              boxShadow: `0 0 12px ${vis.glow}`,
              transition: 'width 0.05s linear',
            }}
          />
        </div>

        <p className="mt-3 text-center text-[11px]" style={{ color: 'rgba(255,255,255,0.3)' }}>
          Click anywhere to dismiss
        </p>
      </div>
    </div>
  );
}

export default function SystemFlow() {
  const [activeScenarioKey, setActiveScenarioKey] = useState(PORTAL_SCENARIO_LIBRARY[0].key);
  const [activePhase, setActivePhase] = useState<FlowPhase | null>(null);
  const [scene, setScene] = useState<FlowScene>(EMPTY_SCENE);
  const [logs, setLogs] = useState<FlowLog[]>([]);
  const [latestVerdict, setLatestVerdict] = useState<PortalVerdictSnapshot | null>(null);
  const [runError, setRunError] = useState('');
  const [usedFallback, setUsedFallback] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [activeModelVersion, setActiveModelVersion] = useState('loading');

  // Popup state
  const [popupPhase, setPopupPhase] = useState<FlowPhase | null>(null);
  const [popupBrowser, setPopupBrowser] = useState<FlowScene['browser'] | null>(null);
  const [popupVerdict, setPopupVerdict] = useState<PortalVerdictSnapshot | null>(null);
  const [popupTrigger, setPopupTrigger] = useState(0);
  const dismissPopup = useCallback(() => setPopupPhase(null), []);

  const activeScenario = useMemo(
    () => PORTAL_SCENARIO_LIBRARY.find((scenario) => scenario.key === activeScenarioKey) || PORTAL_SCENARIO_LIBRARY[0],
    [activeScenarioKey]
  );

  const judgeScenarios = useMemo(
    () =>
      PORTAL_SCENARIO_LIBRARY.map((scenario, index) => ({
        title: `Scenario ${String.fromCharCode(65 + index)}`,
        label: scenario.title,
        verdict: scenario.key === 'active-hacker' ? 'HACKER + SANDBOX' : scenario.key === 'flagged-but-innocent' ? 'FORGETFUL_USER' : 'LEGITIMATE',
        detail: scenario.expectation,
      })),
    []
  );

  async function refreshModelVersion() {
    try {
      const model = await getModelVersion();
      setActiveModelVersion(model.version || 'live');
    } catch {
      setActiveModelVersion('live');
    }
  }

  useEffect(() => {
    void refreshModelVersion();
  }, []);

  async function runScenario(scenarioKey: string) {
    const runner = portalScenarioRunners[scenarioKey];
    const scenario = PORTAL_SCENARIO_LIBRARY.find((entry) => entry.key === scenarioKey);
    if (!runner || !scenario || isRunning) {
      return;
    }

    setIsRunning(true);
    setActiveScenarioKey(scenarioKey);
    setActivePhase('portal');
    setScene(EMPTY_SCENE);
    setLogs([]);
    setLatestVerdict(null);
    setRunError('');
    setUsedFallback(false);
    setPopupPhase(null);
    setPopupBrowser(null);
    setPopupVerdict(null);

    try {
      const result = await runner({
        onScenario: (meta) => {
          setActiveScenarioKey(meta.key);
        },
        onPhase: (phase) => {
          setActivePhase(phase);
          setPopupPhase(phase);
          setPopupTrigger((t) => t + 1);
        },
        onSnapshot: (snapshot) => {
          setScene((previous) => mergeScene(previous, snapshot));
          if (snapshot.browser) setPopupBrowser(snapshot.browser);
        },
        onLog: (item) => {
          setLogs((previous) => [...previous, item]);
        },
        onVerdict: (verdict) => {
          setLatestVerdict(verdict);
          setPopupVerdict(verdict);
          if (verdict?.modelVersion) {
            setActiveModelVersion(verdict.modelVersion);
          }
        },
      });

      if (result.summary) {
        setScene((previous) => mergeScene(previous, result.summary));
      }
      if (result.latestVerdict) {
        setLatestVerdict(result.latestVerdict);
        if (result.latestVerdict.modelVersion) {
          setActiveModelVersion(result.latestVerdict.modelVersion);
        }
      }
      setUsedFallback(Boolean(result.usedFallback));
      setActivePhase('retraining');
      await refreshModelVersion();
    } catch (error) {
      setRunError(error instanceof Error ? error.message : 'Unable to run the live scenario.');
      setActivePhase(null);
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f8fafc_0%,#eef2f8_100%)]">
      <StepPopup
        phase={popupPhase}
        browser={popupBrowser}
        verdict={popupVerdict}
        triggerKey={popupTrigger}
        onDismiss={dismissPopup}
      />
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded bg-[#002147]">
              <span className="text-xl font-bold text-white">NT</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[#002147]">NovaTrust Bank</h1>
              <p className="text-[11px] uppercase tracking-[0.22em] text-slate-400">NeuroShield Live System Flow</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link to="/" className="text-sm text-slate-500 transition-colors hover:text-[#002147]">
              Home
            </Link>
            <Link to="/login" className="rounded-lg bg-[#002147] px-5 py-2 text-white transition-colors hover:bg-[#003366]">
              Sign In
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-8 px-6 py-10">
        <section className="overflow-hidden rounded-[30px] border border-slate-200 bg-white shadow-sm">
          <div className="grid gap-6 px-8 py-8 lg:grid-cols-[1.25fr_0.75fr]">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Where To Ingest</p>
              <h2 className="mt-3 max-w-4xl text-4xl font-bold leading-tight text-[#002147]">
                Three live roles. One bank portal. One visual path from intake to decision, feedback, and retraining.
              </h2>
              <p className="mt-4 max-w-3xl text-slate-600">
                This page drives the real NovaTrust endpoints from inside the simulation portal. Each run shows the portal session, behavioural intake,
                ensemble scoring, decision route, feedback consequences, and whether the model stays calm or earns a malicious sample for future retraining.
              </p>
            </div>

            <div className="rounded-[26px] border border-cyan-100 bg-[linear-gradient(135deg,rgba(0,33,71,0.96),rgba(10,27,53,0.92))] p-5 text-white shadow-[0_18px_55px_rgba(2,6,23,0.24)]">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-100/80">Active model</p>
              <p className="mt-2 text-2xl font-semibold">{activeModelVersion}</p>
              <p className="mt-3 text-sm text-slate-200">
                The retraining card below will show whether the run changes nothing, creates a benign review sample, or queues a replay-backed attack sample.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <span className="rounded-full border border-white/15 bg-white/8 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-white">
                  Live endpoints
                </span>
                <span className="rounded-full border border-white/15 bg-white/8 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-white">
                  3 roles only
                </span>
                <span className="rounded-full border border-white/15 bg-white/8 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-white">
                  Feedback visible
                </span>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-[26px] border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-2xl font-bold text-[#002147]">Dashboard Input</h3>
            <div className="mt-4 space-y-3">
              {dashboardInputs.map((item) => (
                <div key={item.endpoint} className="rounded-[18px] border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <h4 className="font-semibold text-[#002147]">{item.title}</h4>
                    <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-[#002147]">{item.endpoint}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">{item.detail}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[26px] border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-2xl font-bold text-[#002147]">Live Ingestion Paths</h3>
            <div className="mt-4 space-y-3">
              {ingestPaths.map((item) => (
                <div key={item.endpoint} className="rounded-[18px] border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <h4 className="font-semibold text-[#002147]">{item.title}</h4>
                    <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-[#002147]">{item.endpoint}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">{item.detail}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="rounded-[26px] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Judge Scenarios</p>
              <h3 className="mt-2 text-2xl font-bold text-[#002147]">The docs now collapse the demo into three live roles.</h3>
            </div>
            <div className="rounded-[18px] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 lg:max-w-md">
              Raw-ingest fallback is baked into the <span className="font-semibold">Active Hacker</span> role. If the network path is down, the portal shifts to the live honeypot route and still completes the sandbox story.
            </div>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {judgeScenarios.map((scenario) => (
              <article key={scenario.title} className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
                <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-400">{scenario.title}</p>
                <h4 className="mt-2 text-lg font-semibold text-[#002147]">{scenario.label}</h4>
                <p className="mt-2 text-sm text-slate-600">{scenario.detail}</p>
                <p className="mt-3 text-[11px] font-bold uppercase tracking-[0.16em] text-[#002147]">Expected: {scenario.verdict}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
          <aside className="space-y-4">
            <div className="rounded-[26px] border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Role Selector</p>
                  <h3 className="mt-1 text-lg font-semibold text-[#002147]">Three scenarios only</h3>
                </div>
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                  {isRunning ? 'live run' : 'ready'}
                </span>
              </div>

              <div className="mt-4 space-y-3">
                {PORTAL_SCENARIO_LIBRARY.map((scenario) => (
                  <ScenarioCard
                    key={scenario.key}
                    scenario={scenario}
                    isActive={scenario.key === activeScenarioKey}
                    isRunning={isRunning}
                    onRun={runScenario}
                  />
                ))}
              </div>
            </div>

            <VerdictCard verdict={latestVerdict} />
          </aside>

          <div className="space-y-4">
            <section className="relative overflow-hidden rounded-[30px] border border-[#0b1d3a] bg-[#040914] p-5 shadow-[0_28px_90px_rgba(2,6,23,0.38)]">
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.12),transparent_32%),radial-gradient(circle_at_80%_22%,rgba(244,63,94,0.13),transparent_26%),linear-gradient(180deg,rgba(255,255,255,0.03),transparent_55%)]" />
              <div className="relative">
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Live Run Canvas</p>
                    <h3 className="mt-1 text-xl font-semibold text-white">
                      {activeScenario.title} · {activeScenario.actorName}
                    </h3>
                  </div>
                  <span className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${tokenFor(activeScenario.accent).badge}`}>
                    {isRunning ? 'animating live' : activePhase ? 'last run loaded' : 'awaiting run'}
                  </span>
                </div>

                <div className="mt-5 grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)_320px]">
                  <div className="space-y-4">
                    <div className="rounded-[24px] border border-white/10 bg-black/20 p-4">
                      <div className="flex items-center gap-3">
                        <ActorAvatar scenario={activeScenario} large />
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{activeScenario.role}</p>
                          <h4 className="mt-1 text-lg font-semibold text-white">{activeScenario.actorName}</h4>
                          <p className="text-sm text-slate-300">{activeScenario.device}</p>
                        </div>
                      </div>
                      <div className="mt-4 space-y-2 text-sm text-slate-100">
                        <p><span className="font-semibold text-slate-400">Source IP:</span> {activeScenario.ipAddress}</p>
                        <p><span className="font-semibold text-slate-400">Expected lane:</span> {activeScenario.expectedLane}</p>
                        <p className="text-slate-300">{activeScenario.expectation}</p>
                      </div>
                    </div>

                    <InfoCard label="Live Feedback" panel={scene.feedback} />
                    <InfoCard label="Retraining Story" panel={scene.retraining} />
                  </div>

                  <div className="space-y-4">
                    <div className="rounded-[28px] border border-white/10 bg-white/5 p-4" style={{ perspective: '1400px' }}>
                      <div className="nt-flow-tilt-panel rounded-[24px] border border-white/10 bg-black/20 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Decision Pipeline</p>
                          <span className="rounded-full border border-cyan-200/35 bg-cyan-500/12 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-cyan-100">
                            {activePhase || 'idle'}
                          </span>
                        </div>

                        <div className="mt-4 space-y-3">
                          {THEATER_PHASES.map((phase, index) => (
                            <div key={phase.id}>
                              <PipelineNode phase={phase} activePhase={activePhase} />
                              {index < THEATER_PHASES.length - 1 ? (
                                <div className="ml-8 mt-1 h-4 w-px bg-[linear-gradient(180deg,rgba(103,232,249,0.85),rgba(103,232,249,0.05))]" />
                              ) : null}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    <RouteBoard route={scene.route} />
                  </div>

                  <BrowserMock browser={scene.browser} scenario={activeScenario} />
                </div>
              </div>
            </section>

            <TracePanel logs={logs} runError={runError} usedFallback={usedFallback} />
          </div>
        </section>
      </main>
    </div>
  );
}
