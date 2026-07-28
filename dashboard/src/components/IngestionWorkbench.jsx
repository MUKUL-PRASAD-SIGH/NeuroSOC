import { useMemo, useState } from "react";
import { useDashboardStore } from "../store/dashboardStore";
import { SCENARIO_LIBRARY, liveScenarioRunners } from "../services/liveScripts";

const THEATER_PHASES = [
  { id: "portal", label: "Portal Session", code: "P01" },
  { id: "behavioral", label: "Behavior Stream", code: "P02" },
  { id: "ensemble", label: "SNN + LNN + XGB", code: "P03" },
  { id: "decision", label: "Decision Layer", code: "P04" },
  { id: "route", label: "Route Outcome", code: "P05" },
  { id: "feedback", label: "Feedback Loop", code: "P06" },
  { id: "retraining", label: "Retrain Guard", code: "P07" },
];

const PHASE_ORDER = THEATER_PHASES.reduce((acc, phase, index) => {
  acc[phase.id] = index;
  return acc;
}, {});

const ACCENT_TOKENS = {
  emerald: {
    halo: "from-emerald-500/20 via-emerald-400/10 to-transparent",
    border: "border-emerald-400/45",
    badge: "border-emerald-400/35 bg-emerald-400/10 text-emerald-300",
    text: "text-emerald-300",
    orb: "bg-emerald-400",
    soft: "bg-emerald-500/10",
  },
  amber: {
    halo: "from-amber-500/20 via-amber-400/10 to-transparent",
    border: "border-amber-400/45",
    badge: "border-amber-400/35 bg-amber-400/10 text-amber-300",
    text: "text-amber-300",
    orb: "bg-amber-400",
    soft: "bg-amber-500/10",
  },
  rose: {
    halo: "from-rose-500/20 via-rose-400/10 to-transparent",
    border: "border-rose-400/45",
    badge: "border-rose-400/35 bg-rose-400/10 text-rose-300",
    text: "text-rose-300",
    orb: "bg-rose-400",
    soft: "bg-rose-500/10",
  },
  cyan: {
    halo: "from-soc-electric/20 via-soc-electric/10 to-transparent",
    border: "border-soc-electric/45",
    badge: "border-soc-electric/35 bg-soc-electric/10 text-soc-electric",
    text: "text-soc-electric",
    orb: "bg-soc-electric",
    soft: "bg-soc-electric/10",
  },
  neutral: {
    halo: "from-slate-500/14 via-slate-400/8 to-transparent",
    border: "border-soc-border/70",
    badge: "border-soc-border/70 bg-soc-panelSoft/35 text-soc-muted",
    text: "text-soc-text",
    orb: "bg-soc-muted",
    soft: "bg-soc-panelSoft/35",
  },
};

const ROUTE_LANES = [
  {
    key: "safe",
    title: "No Sandbox",
    detail: "Real portal, clean outcome, customer stays happy.",
  },
  {
    key: "review",
    title: "Soft Review Timeout",
    detail: "Session pauses, reload returns the user safely.",
  },
  {
    key: "sandbox",
    title: "Hard Sandbox",
    detail: "Decoy-only isolation with replay capture.",
  },
];

const EMPTY_SCENE = {
  browser: {
    tone: "neutral",
    eyebrow: "Scenario theater idle",
    title: "Choose one of the three live roles",
    subtitle: "The dashboard will animate the real pipeline while the endpoints are being hit.",
    lines: [
      "Trusted customer → real dashboard.",
      "Flagged but innocent → timeout and safe reload.",
      "Active hacker → hard sandbox with feedback and retraining eligibility.",
    ],
    badge: "READY",
  },
  route: {
    kind: "idle",
    title: "Decision route waiting",
    detail: "No branch has been selected yet.",
    footer: "Pick a role to drive the full story.",
  },
  feedback: {
    tone: "neutral",
    title: "Feedback loop idle",
    detail: "No session has produced a label yet.",
    chips: ["Awaiting run"],
  },
  retraining: {
    tone: "neutral",
    title: "Retraining loop idle",
    detail: "The model remains on the current production version until a run earns a strong label.",
    chips: ["No delta"],
  },
};

function mergeScene(previous, patch = {}) {
  return {
    ...previous,
    ...patch,
    browser: patch.browser || previous.browser,
    route: patch.route || previous.route,
    feedback: patch.feedback || previous.feedback,
    retraining: patch.retraining || previous.retraining,
  };
}

function tokenFor(tone) {
  return ACCENT_TOKENS[tone] || ACCENT_TOKENS.neutral;
}

function statusClasses(status) {
  if (status === "success") return "border-soc-green/40 bg-soc-green/10 text-soc-green";
  if (status === "warning") return "border-soc-amber/40 bg-soc-amber/10 text-soc-amber";
  if (status === "error") return "border-soc-red/45 bg-soc-red/10 text-soc-red";
  return "border-soc-electric/35 bg-soc-electric/10 text-soc-electric";
}

function ActorAvatar({ scenario, large = false }) {
  const tokens = tokenFor(scenario.accent);

  return (
    <div
      className={`relative inline-flex items-center justify-center rounded-[24px] border font-semibold ${tokens.border} ${tokens.soft} ${
        large ? "h-16 w-16 text-xl" : "h-12 w-12 text-sm"
      }`}
    >
      <div className={`absolute inset-0 rounded-[24px] bg-gradient-to-br ${tokens.halo}`} />
      <span className="relative text-soc-text">{scenario.initials}</span>
    </div>
  );
}

function ScenarioCard({ scenario, isActive, isRunning, onRun }) {
  const tokens = tokenFor(scenario.accent);

  return (
    <article
      className={`relative overflow-hidden rounded-[24px] border bg-soc-panel/70 p-4 transition-all duration-300 ${
        isActive ? `${tokens.border} shadow-[0_20px_55px_rgba(3,10,24,0.5)]` : "border-soc-border/70"
      }`}
    >
      <div className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${tokens.halo}`} />
      <div className="relative">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <ActorAvatar scenario={scenario} />
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-soc-muted">{scenario.role}</p>
              <h3 className="mt-1 text-base font-semibold text-soc-text">{scenario.title}</h3>
              <p className="text-sm text-soc-muted">{scenario.actorName}</p>
            </div>
          </div>
          <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${tokens.badge}`}>
            {scenario.expectedLane}
          </span>
        </div>

        <div className="mt-4 grid gap-2 text-sm text-soc-text">
          <p><span className="font-semibold text-soc-muted">Source IP:</span> {scenario.ipAddress}</p>
          <p><span className="font-semibold text-soc-muted">Device:</span> {scenario.device}</p>
          <p className="text-soc-muted">{scenario.expectation}</p>
        </div>

        <button
          type="button"
          disabled={isRunning}
          onClick={() => onRun(scenario.key)}
          className={`mt-4 inline-flex rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition-colors ${
            isActive
              ? `${tokens.badge} hover:brightness-110`
              : "border-soc-border/70 bg-soc-panelSoft/40 text-soc-text hover:border-soc-electric/35"
          } disabled:cursor-not-allowed disabled:opacity-50`}
        >
          {isRunning && isActive ? "Running..." : "Run Live"}
        </button>
      </div>
    </article>
  );
}

function PipelineNode({ phase, activePhase }) {
  const currentIndex = PHASE_ORDER[activePhase];
  const thisIndex = PHASE_ORDER[phase.id];
  const isActive = phase.id === activePhase;
  const isComplete = currentIndex !== undefined && thisIndex < currentIndex;

  return (
    <div className="flex items-center gap-3">
      <div
        className={`soc-stage-node rounded-[22px] border px-4 py-3 ${
          isActive
            ? "soc-stage-node-active border-soc-electric/50 bg-soc-electric/10"
            : isComplete
              ? "border-soc-green/35 bg-soc-green/10"
              : "border-soc-border/70 bg-soc-panelSoft/35"
        }`}
      >
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-soc-muted">{phase.code}</p>
            <p className={`mt-1 text-sm font-semibold ${isActive ? "text-soc-electric" : "text-soc-text"}`}>
              {phase.label}
            </p>
          </div>
          <div
            className={`h-2.5 w-2.5 rounded-full ${
              isActive ? "bg-soc-electric shadow-[0_0_16px_rgba(25,230,255,0.65)]" : isComplete ? "bg-soc-green" : "bg-soc-muted/70"
            }`}
          />
        </div>
      </div>
    </div>
  );
}

function BrowserMock({ browser, scenario }) {
  const tokens = tokenFor(browser?.tone || scenario?.accent || "neutral");

  return (
    <div className="soc-tilt-panel rounded-[28px] border border-soc-border/70 bg-[#070c18] p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-soc-red" />
          <span className="h-2.5 w-2.5 rounded-full bg-soc-amber" />
          <span className="h-2.5 w-2.5 rounded-full bg-soc-green" />
        </div>
        <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${tokens.badge}`}>
          {browser.badge}
        </span>
      </div>

      <div className="mt-4 rounded-[22px] border border-soc-border/70 bg-soc-panel/70 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-soc-muted">{browser.eyebrow}</p>
            <h3 className="mt-1 text-lg font-semibold text-soc-text">{browser.title}</h3>
            <p className="mt-2 text-sm text-soc-muted">{browser.subtitle}</p>
          </div>
          {scenario ? <ActorAvatar scenario={scenario} /> : null}
        </div>

        <div className="mt-4 space-y-2">
          {(Array.isArray(browser.lines) ? browser.lines : []).map((line) => (
            <div key={line} className="rounded-[16px] border border-soc-border/60 bg-black/20 px-3 py-2 text-sm text-soc-text">
              {line}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RouteBoard({ route }) {
  return (
    <div className="rounded-[26px] border border-soc-border/70 bg-black/20 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-soc-muted">Route Board</p>
      <div className="mt-4 grid gap-3">
        {ROUTE_LANES.map((lane) => {
          const active = route.kind === lane.key;
          const color =
            lane.key === "safe"
              ? active
                ? "border-soc-green/40 bg-soc-green/10 text-soc-green"
                : "border-soc-border/70 bg-soc-panelSoft/30 text-soc-muted"
              : lane.key === "review"
                ? active
                  ? "border-soc-amber/40 bg-soc-amber/10 text-soc-amber"
                  : "border-soc-border/70 bg-soc-panelSoft/30 text-soc-muted"
                : active
                  ? "border-soc-red/45 bg-soc-red/10 text-soc-red"
                  : "border-soc-border/70 bg-soc-panelSoft/30 text-soc-muted";

          return (
            <div key={lane.key} className={`rounded-[18px] border px-3 py-3 transition-all ${color}`}>
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold">{lane.title}</p>
                <span className="text-[10px] font-semibold uppercase tracking-[0.16em]">{active ? "active" : "idle"}</span>
              </div>
              <p className="mt-2 text-xs">{active ? route.detail : lane.detail}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-4 rounded-[18px] border border-soc-border/70 bg-soc-panelSoft/30 px-3 py-3">
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-soc-muted">Current route summary</p>
        <p className="mt-2 text-sm font-semibold text-soc-text">{route.title}</p>
        <p className="mt-2 text-sm text-soc-muted">{route.footer}</p>
      </div>
    </div>
  );
}

function FeedbackCard({ feedback }) {
  const tokens = tokenFor(feedback?.tone || "neutral");

  return (
    <div className="rounded-[24px] border border-soc-border/70 bg-black/20 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-soc-muted">Live Feedback</p>
        <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${tokens.badge}`}>
          {feedback?.tone || "idle"}
        </span>
      </div>
      <h3 className="mt-3 text-base font-semibold text-soc-text">{feedback?.title}</h3>
      <p className="mt-2 text-sm text-soc-muted">{feedback?.detail}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {feedback?.chips?.map((chip) => (
          <span key={chip} className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${tokens.badge}`}>
            {chip}
          </span>
        ))}
      </div>
    </div>
  );
}

function RetrainingCard({ retraining }) {
  const tokens = tokenFor(retraining?.tone || "neutral");

  return (
    <div className="rounded-[24px] border border-soc-border/70 bg-black/20 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-soc-muted">Retraining Story</p>
        <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${tokens.badge}`}>
          {retraining?.tone || "idle"}
        </span>
      </div>
      <h3 className="mt-3 text-base font-semibold text-soc-text">{retraining?.title}</h3>
      <p className="mt-2 text-sm text-soc-muted">{retraining?.detail}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {retraining?.chips?.map((chip) => (
          <span key={chip} className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${tokens.badge}`}>
            {chip}
          </span>
        ))}
      </div>
    </div>
  );
}

function VerdictCard({ verdict }) {
  if (!verdict) {
    return (
      <div className="rounded-[24px] border border-soc-border/70 bg-black/20 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-soc-muted">Decision Telemetry</p>
        <p className="mt-3 text-sm text-soc-muted">Verdict metrics will appear here as soon as the live run reaches the decision layer.</p>
      </div>
    );
  }

  const verdictLabel = verdict.verdict || "INCONCLUSIVE";
  const verdictTone =
    verdictLabel === "HACKER" ? "rose" : verdictLabel === "FORGETFUL_USER" ? "amber" : verdictLabel === "LEGITIMATE" ? "emerald" : "neutral";
  const tokens = tokenFor(verdictTone);

  const metricCards = [
    { label: "Confidence", value: `${Math.round((Number(verdict.confidence || 0) || 0) * 100)}%` },
    { label: "SNN", value: `${Math.round((Number(verdict.snnScore || verdict.snn_score || 0) || 0) * 100)}%` },
    { label: "LNN", value: verdict.lnnClass || verdict.lnn_class || "—" },
    { label: "XGBoost", value: verdict.xgbClass || verdict.xgb_class || "—" },
  ];

  return (
    <div className="rounded-[24px] border border-soc-border/70 bg-black/20 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-soc-muted">Decision Telemetry</p>
        <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${tokens.badge}`}>
          {verdictLabel}
        </span>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {metricCards.map((metric) => (
          <div key={metric.label} className="rounded-[18px] border border-soc-border/70 bg-soc-panelSoft/35 px-3 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-soc-muted">{metric.label}</p>
            <p className={`mt-2 text-sm font-semibold ${tokens.text}`}>{metric.value}</p>
          </div>
        ))}
      </div>
      <div className="mt-4 rounded-[18px] border border-soc-border/70 bg-soc-panelSoft/35 px-3 py-3 text-sm text-soc-muted">
        Session <span className="font-semibold text-soc-text">{verdict.sessionId || verdict.session_id || "pending"}</span>
        {verdict?.sandbox?.active ? (
          <span className="ml-2 rounded-full border border-soc-red/40 bg-soc-red/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-soc-red">
            sandbox active
          </span>
        ) : null}
      </div>
    </div>
  );
}

function TracePanel({ logs, runError, usedFallback }) {
  return (
    <div className="rounded-[24px] border border-soc-border/70 bg-soc-panel/55 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-soc-muted">Execution Trace</p>
        {usedFallback ? (
          <span className="rounded-full border border-soc-amber/40 bg-soc-amber/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-soc-amber">
            fallback used
          </span>
        ) : null}
      </div>

      {runError ? (
        <div className="mt-4 rounded-[18px] border border-soc-red/45 bg-soc-red/10 px-4 py-3 text-sm text-soc-red">
          {runError}
        </div>
      ) : null}

      <div className="mt-4 space-y-3">
        {logs.length === 0 ? (
          <div className="rounded-[18px] border border-dashed border-soc-border/70 bg-black/20 px-4 py-5 text-sm text-soc-muted">
            Pick one of the three roles and the dashboard will animate the live path while the trace fills in.
          </div>
        ) : null}

        {logs.map((item) => (
          <article key={item.id} className="rounded-[18px] border border-soc-border/70 bg-black/20 p-3">
            <div className="flex items-center justify-between gap-3">
              <h4 className="text-sm font-semibold text-soc-text">{item.title}</h4>
              <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${statusClasses(item.status)}`}>
                {item.status}
              </span>
            </div>
            <p className="mt-2 text-sm text-soc-muted">{item.detail}</p>
            {item.endpoint ? (
              <p className="mt-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-soc-electric">{item.endpoint}</p>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}

export default function IngestionWorkbench() {
  const [activeScenarioKey, setActiveScenarioKey] = useState(SCENARIO_LIBRARY[0].key);
  const [activePhase, setActivePhase] = useState(null);
  const [scene, setScene] = useState(EMPTY_SCENE);
  const [logs, setLogs] = useState([]);
  const [latestVerdict, setLatestVerdict] = useState(null);
  const [runError, setRunError] = useState("");
  const [usedFallback, setUsedFallback] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  const fetchStats = useDashboardStore((state) => state.fetchStats);
  const fetchModelStatus = useDashboardStore((state) => state.fetchModelStatus);
  const hydrateAlerts = useDashboardStore((state) => state.hydrateAlerts);
  const liveModel = useDashboardStore((state) => state.modelStatus.data);

  const activeScenario = useMemo(
    () => SCENARIO_LIBRARY.find((scenario) => scenario.key === activeScenarioKey) || SCENARIO_LIBRARY[0],
    [activeScenarioKey]
  );

  async function runScenario(scenarioKey) {
    const runner = liveScenarioRunners[scenarioKey];
    const scenario = SCENARIO_LIBRARY.find((entry) => entry.key === scenarioKey);
    if (!runner || !scenario || isRunning) {
      return;
    }

    setIsRunning(true);
    setActiveScenarioKey(scenarioKey);
    setActivePhase("portal");
    setScene(EMPTY_SCENE);
    setLogs([]);
    setLatestVerdict(null);
    setRunError("");
    setUsedFallback(false);

    try {
      const result = await runner({
        onScenario: (meta) => {
          setActiveScenarioKey(meta.key);
        },
        onPhase: (phase) => {
          setActivePhase(phase);
        },
        onSnapshot: (snapshot) => {
          setScene((previous) => mergeScene(previous, snapshot));
        },
        onLog: (item) => {
          setLogs((previous) => [...previous, item]);
        },
        onVerdict: (verdict) => {
          setLatestVerdict(verdict);
        },
      });

      if (result?.summary) {
        setScene((previous) => mergeScene(previous, result.summary));
      }
      if (result?.latestVerdict) {
        setLatestVerdict(result.latestVerdict);
      }
      setUsedFallback(Boolean(result?.usedFallback));
      setActivePhase("retraining");

      await Promise.all([fetchStats(), fetchModelStatus(), hydrateAlerts()]);
    } catch (error) {
      setRunError(error instanceof Error ? error.message : "Unable to run the live scenario.");
      setActivePhase(null);
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <section className="soc-glass mb-4 p-4 md:p-5">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div className="max-w-4xl">
          <p className="soc-kicker">Live Scenario Theater</p>
          <h2 className="mt-2 text-2xl font-semibold text-soc-text md:text-3xl">
            Three real roles. One live decision stack. One visual story from portal to retraining.
          </h2>
          <p className="mt-3 text-sm text-soc-muted">
            Each run hits the real endpoints, then animates the bank UI, decision layer, route outcome, feedback loop, and retraining consequence so the demo feels like a live system rather than a fake script wall.
          </p>
        </div>

        <div className="rounded-[20px] border border-soc-electric/25 bg-soc-electric/10 px-4 py-3 text-sm text-soc-text xl:w-[360px]">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-soc-electric">Active model</p>
          <p className="mt-2 font-semibold">{liveModel?.version || "loading"}</p>
          <p className="mt-1 text-soc-muted">
            The retraining panel below will show whether this run changes nothing, adds a benign review sample, or queues a malicious sandbox session for the next model cycle.
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <aside className="space-y-4">
          <div className="rounded-[24px] border border-soc-border/70 bg-soc-panel/55 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-soc-muted">Role Selector</p>
                <h3 className="mt-1 text-lg font-semibold text-soc-text">Three scenarios only</h3>
              </div>
              <span className="rounded-full border border-soc-border/70 bg-soc-panelSoft/35 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-soc-muted">
                {isRunning ? "live run" : "ready"}
              </span>
            </div>

            <div className="mt-4 space-y-3">
              {SCENARIO_LIBRARY.map((scenario) => (
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
          <section className="relative overflow-hidden rounded-[28px] border border-soc-border/70 bg-[#040914] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.45)]">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(25,230,255,0.08),transparent_35%),radial-gradient(circle_at_80%_20%,rgba(255,87,117,0.08),transparent_28%),linear-gradient(180deg,rgba(255,255,255,0.03),transparent_55%)]" />
            <div className="relative">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-soc-muted">Live Run Canvas</p>
                  <h3 className="mt-1 text-xl font-semibold text-soc-text">
                    {activeScenario.title} · {activeScenario.actorName}
                  </h3>
                </div>
                <span className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${tokenFor(activeScenario.accent).badge}`}>
                  {isRunning ? "animating live" : activePhase ? "last run loaded" : "awaiting run"}
                </span>
              </div>

              <div className="mt-5 grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)_320px]">
                <div className="space-y-4">
                  <div className="rounded-[24px] border border-soc-border/70 bg-black/20 p-4">
                    <div className="flex items-center gap-3">
                      <ActorAvatar scenario={activeScenario} large />
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-soc-muted">{activeScenario.role}</p>
                        <h4 className="mt-1 text-lg font-semibold text-soc-text">{activeScenario.actorName}</h4>
                        <p className="text-sm text-soc-muted">{activeScenario.device}</p>
                      </div>
                    </div>
                    <div className="mt-4 space-y-2 text-sm text-soc-text">
                      <p><span className="font-semibold text-soc-muted">Source IP:</span> {activeScenario.ipAddress}</p>
                      <p><span className="font-semibold text-soc-muted">Expected lane:</span> {activeScenario.expectedLane}</p>
                      <p className="text-soc-muted">{activeScenario.expectation}</p>
                    </div>
                  </div>

                  <FeedbackCard feedback={scene.feedback} />
                  <RetrainingCard retraining={scene.retraining} />
                </div>

                <div className="space-y-4">
                  <div className="rounded-[28px] border border-soc-border/70 bg-soc-panel/45 p-4" style={{ perspective: "1400px" }}>
                    <div className="soc-tilt-panel rounded-[24px] border border-soc-border/70 bg-black/20 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-soc-muted">Decision Pipeline</p>
                        <span className="rounded-full border border-soc-electric/25 bg-soc-electric/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-soc-electric">
                          {activePhase || "idle"}
                        </span>
                      </div>

                      <div className="mt-4 space-y-3">
                        {THEATER_PHASES.map((phase, index) => (
                          <div key={phase.id}>
                            <PipelineNode phase={phase} activePhase={activePhase} />
                            {index < THEATER_PHASES.length - 1 ? (
                              <div className="ml-8 mt-1 h-4 w-px bg-[linear-gradient(180deg,rgba(25,230,255,0.75),rgba(25,230,255,0.05))]" />
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
      </div>
    </section>
  );
}
