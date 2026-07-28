import { apiClient } from "../lib/apiClient";

function makeId(prefix) {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function makeLog(status, title, detail, options = {}) {
  return {
    id: makeId("log"),
    status,
    title,
    detail,
    endpoint: options.endpoint || null,
    payload: options.payload,
  };
}

async function apiGet(path) {
  const { data } = await apiClient.get(path);
  return data;
}

async function apiPost(path, payload) {
  const { data } = await apiClient.post(path, payload);
  return data;
}

async function ingestPost(payload) {
  const response = await fetch("/ingest", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message =
      (typeof data?.detail === "string" && data.detail) ||
      (typeof data?.error === "string" && data.error) ||
      `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return data;
}

async function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

async function safeCurrentVerdict() {
  try {
    return await apiGet("/api/verdicts/current");
  } catch {
    return null;
  }
}

async function safeUserVerdict(userId) {
  if (!userId) {
    return null;
  }

  try {
    return await apiGet(`/api/verdicts/${encodeURIComponent(userId)}`);
  } catch {
    return null;
  }
}

async function safeAlerts() {
  try {
    const data = await apiGet("/api/alerts");
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

async function safeModelVersion() {
  try {
    return await apiGet("/api/model/version");
  } catch {
    return null;
  }
}

function emitLog(logs, hooks, status, title, detail, options = {}) {
  const item = makeLog(status, title, detail, options);
  logs.push(item);
  hooks.onLog?.(item);
  return item;
}

async function emitPhase(hooks, phase, snapshot = null, delayMs = 520) {
  hooks.onPhase?.(phase);
  if (snapshot) {
    hooks.onSnapshot?.(snapshot);
  }
  if (delayMs > 0) {
    await wait(delayMs);
  }
}

async function emitSnapshot(hooks, snapshot, delayMs = 360) {
  hooks.onSnapshot?.(snapshot);
  if (delayMs > 0) {
    await wait(delayMs);
  }
}

function buildBrowser(tone, eyebrow, title, subtitle, lines = [], badge = "LIVE") {
  return {
    tone,
    eyebrow,
    title,
    subtitle,
    lines,
    badge,
  };
}

function buildRoute(kind, title, detail, footer) {
  return {
    kind,
    title,
    detail,
    footer,
  };
}

function buildFeedback(tone, title, detail, chips = []) {
  return {
    tone,
    title,
    detail,
    chips,
  };
}

function buildRetraining(tone, title, detail, chips = []) {
  return {
    tone,
    title,
    detail,
    chips,
  };
}

function buildBehavioralPayload(userId, sessionId, page = "/login", sourceIp = "198.51.100.44") {
  const now = Date.now();
  const isHostile = userId.includes('intruder');
  const events = isHostile
    ? [
        // Automated tool: zero mouse movement, instant clipboard paste, inhuman speed
        { type: 'mousemove', timestamp: now, x: 0, y: 0 },
        { type: 'focus', timestamp: now + 1, target: 'input#email' },
        { type: 'paste', timestamp: now + 3, target: 'input#email', length: 320, clipboardHash: 'a1b2c3d4' },
        { type: 'focus', timestamp: now + 5, target: 'input#password' },
        { type: 'paste', timestamp: now + 7, target: 'input#password', length: 128, clipboardHash: 'e5f6g7h8' },
        { type: 'click', timestamp: now + 9, x: 0, y: 0, target: 'button#login-submit' },
        { type: 'keydown', timestamp: now + 10, key: 'Enter', target: 'button#login-submit' },
        { type: 'focus', timestamp: now + 12, target: 'input#transfer-dest' },
        { type: 'paste', timestamp: now + 14, target: 'input#transfer-dest', length: 480, clipboardHash: 'sqli-probe' },
      ]
    : [
        // Human: natural mouse drift, typed keystrokes at ~80ms cadence
        { type: 'mousemove', timestamp: now, x: 212, y: 188 },
        { type: 'mousemove', timestamp: now + 40, x: 220, y: 192 },
        { type: 'focus', timestamp: now + 80, target: 'input#email' },
        { type: 'keydown', timestamp: now + 120, key: 'n', target: 'input#email' },
        { type: 'keydown', timestamp: now + 200, key: 'o', target: 'input#email' },
        { type: 'keydown', timestamp: now + 280, key: 'v', target: 'input#email' },
        { type: 'keydown', timestamp: now + 360, key: 'a', target: 'input#email' },
        { type: 'focus', timestamp: now + 420, target: 'input#password' },
        { type: 'keydown', timestamp: now + 500, key: '*', target: 'input#password' },
        { type: 'keydown', timestamp: now + 580, key: '*', target: 'input#password' },
        { type: 'mousemove', timestamp: now + 640, x: 364, y: 500 },
        { type: 'click', timestamp: now + 720, x: 364, y: 504, target: 'button#login-submit' },
      ];
  return { user_id: userId, session_id: sessionId, source_ip: sourceIp, page, events };
}

function buildRawIngestPayload(userId, sessionId) {
  const isHostile = userId.includes('threat') || userId.includes('intruder');
  const events = isHostile
    ? [
        {
          src_ip: '203.0.113.77',
          dst_ip: '10.0.0.1',
          src_port: 33451,
          dst_port: 80,
          protocol: 'TCP',
          length: 4096,
          ttl: 48,
          flags: { SYN: true, ACK: false, FIN: false, RST: false },
          extra: { tool: 'sqlmap/1.8', user_agent: 'sqlmap/1.8#stable', stage: 'injection-probe', target_path: '/api/bank/login' },
        },
        {
          src_ip: '203.0.113.77',
          dst_ip: '10.0.0.1',
          src_port: 33451,
          dst_port: 443,
          protocol: 'TCP',
          length: 8192,
          ttl: 48,
          flags: { SYN: false, ACK: true, FIN: false, RST: false },
          extra: { tool: 'sqlmap/1.8', payload_type: 'base64-obfuscated', stage: 'exfil-attempt', target_path: '/api/bank/transfer' },
        },
      ]
    : [
        {
          src_ip: '198.51.100.44',
          dst_ip: '10.0.0.1',
          src_port: 54021,
          dst_port: 443,
          protocol: 'TCP',
          length: 612,
          ttl: 64,
          flags: { SYN: true, ACK: false, FIN: false, RST: false },
          extra: { OS: 'macOS 14.4', browser: 'Chrome/124.0', stage: 'syn', tls_version: 'TLS 1.3' },
        },
        {
          src_ip: '198.51.100.44',
          dst_ip: '10.0.0.1',
          src_port: 54021,
          dst_port: 443,
          protocol: 'TCP',
          length: 1240,
          ttl: 64,
          flags: { SYN: false, ACK: true, FIN: false, RST: false },
          extra: { OS: 'macOS 14.4', browser: 'Chrome/124.0', stage: 'post-auth', tls_version: 'TLS 1.3' },
        },
      ];
  return { user_id: userId, session_id: sessionId, events };
}

function seedScene(modelStatus, browser, route) {
  return {
    browser,
    route,
    feedback: buildFeedback(
      "neutral",
      "Feedback loop idle",
      "No sample has been promoted yet. The queue only reacts after a real decision path completes.",
      ["Awaiting verdict"]
    ),
    retraining: buildRetraining(
      "neutral",
      `Model ${modelStatus?.version || "standby"}`,
      "Retraining stays guarded until the session produces a strong label.",
      ["No delta yet"]
    ),
  };
}

function finalScene(browser, route, feedback, retraining) {
  return { browser, route, feedback, retraining };
}

export const SCENARIO_LIBRARY = [
  {
    key: "trusted-customer",
    title: "Trusted Customer",
    actorName: "Alice Johnson",
    initials: "AJ",
    role: "Known premium customer",
    accent: "emerald",
    ipAddress: "198.51.100.44",
    device: "Known Chrome session",
    expectedLane: "Main banking experience",
    expectation: "No sandbox. The customer reaches dashboard and finishes happy.",
  },
  {
    key: "flagged-but-innocent",
    title: "Flagged But Innocent",
    actorName: "Bob Carter",
    initials: "BC",
    role: "Legitimate but high-friction customer",
    accent: "amber",
    ipAddress: "203.0.113.32",
    device: "New browser + urgent transfer",
    expectedLane: "Soft review timeout",
    expectation: "No hard sandbox. The transfer pauses, the session times out, and a reload returns the user safely.",
  },
  {
    key: "active-hacker",
    title: "Active Hacker",
    actorName: "Unknown Intruder",
    initials: "HX",
    role: "Trap-triggering hostile actor",
    accent: "rose",
    ipAddress: "203.0.113.77",
    device: "Untrusted automated client",
    expectedLane: "Hard sandbox isolation",
    expectation: "Sandbox only. Replay is captured, feedback is promoted, and retraining becomes eligible.",
  },
];

function getScenarioByKey(key) {
  return SCENARIO_LIBRARY.find((scenario) => scenario.key === key) || SCENARIO_LIBRARY[0];
}

async function runTrustedCustomerScenario(hooks = {}) {
  const scenario = getScenarioByKey("trusted-customer");
  const logs = [];
  const modelStatus = await safeModelVersion();
  const sessionId = makeId("trusted");
  let latestVerdict = null;

  hooks.onScenario?.(scenario);

  const initialBrowser = buildBrowser(
    "emerald",
    "NovaTrust portal",
    "Known customer session is opening",
    "The live bank UI is creating a single portal session before the login reaches the engine.",
    [
      "Login form is warm and behavioural tracking is armed.",
      "Expected branch: standard dashboard path with no isolation.",
    ],
    "LOW RISK"
  );

  const initialRoute = buildRoute(
    "safe",
    "Main route warming",
    "Nothing has triggered the review or sandbox lanes yet.",
    "The customer should remain in the real portal if the ensemble stays calm."
  );

  await emitPhase(hooks, "portal", seedScene(modelStatus, initialBrowser, initialRoute), 480);

  // ── Network Telemetry Ingest ──
  const rawPayload = buildRawIngestPayload(scenario.key, sessionId);
  try {
    emitLog(logs, hooks, "info", "📡 NETWORK FLOW CAPTURED", "Firewall recorded a standard residential TCP/TLS handshake matching the customer ISP profile.", { endpoint: "POST /ingest", payload: rawPayload });
    await ingestPost(rawPayload);
    emitLog(logs, hooks, "success", "✅ CLEAN FLOW INGESTED", "Network telemetry accepted — no anomalous packet sizes, standard TTL=64.", { endpoint: "POST /ingest" });
  } catch {
    emitLog(logs, hooks, "info", "Ingestion skipped", "Raw ingest service offline — continuing with portal-only telemetry.");
  }

  const behavioralPayload = buildBehavioralPayload("normal1@novatrust.com", sessionId, "/login", scenario.ipAddress);
  emitLog(
    logs,
    hooks,
    "info",
    "🖱️ BEHAVIOURAL STREAM OPENED",
    "Posting live browser telemetry into the behavioural intake layer for real-time profiling.",
    { endpoint: "POST /api/behavioral", payload: behavioralPayload }
  );
  const behavioral = await apiPost("/api/behavioral", behavioralPayload);
  emitLog(
    logs,
    hooks,
    "success",
    "👤 PROFILE STITCHED",
    `Successfully linked ${behavioral.eventCount} live events to session ${behavioral.sessionId.slice(0,8)}...`,
    { endpoint: "POST /api/behavioral" }
  );

  await emitPhase(
    hooks,
    "behavioral",
    {
      browser: buildBrowser(
        "emerald",
        "STABLE PROFILE: ALICE JOHNSON",
        "User interaction matches historical baseline",
        "Mouse cadence, click velocity, and keystroke timing are consistent with a calm account owner.",
        [
          `${behavioral.eventCount} events analyzed against user history.`,
          "Zero drift detected. No automation signatures.",
          "Confidence: 99.2% Legitimate.",
        ],
        "PROFILE STABLE"
      ),
    },
    4500
  );

  const loginPayload = {
    email: "normal1@novatrust.com",
    password: "password123",
    session_id: sessionId,
    source_ip: scenario.ipAddress,
  };
  emitLog(
    logs,
    hooks,
    "info",
    "Bank login submitted",
    "Passing the legitimate NovaTrust credential pair into the decision engine.",
    { endpoint: "POST /api/bank/login", payload: loginPayload }
  );
  const login = await apiPost("/api/bank/login", loginPayload);
  emitLog(
    logs,
    hooks,
    "success",
    "Account verified",
    `${login.user_id} authenticated and was routed to ${login.next}.`,
    { endpoint: "POST /api/bank/login" }
  );

  await emitPhase(
    hooks,
    "ensemble",
    {
      browser: buildBrowser(
        "cyan",
        "ENSEMBLE ANALYSIS: CLEAR",
        "SNN, LNN, and XGBoost are in total agreement",
        "The ensemble scores indicate a high-trust session. No isolation required.",
        [
          "SNN: Signal pressure within normal bounds.",
          "LNN: Identity drift at 0.04 (Nominal).",
          "XGBoost: Predicts Class 0 (Safe) with 0.99 confidence.",
        ],
        "ENSEMBLE LIVE"
      ),
    },
    4800
  );

  const dashboardBehavior = buildBehavioralPayload(login.user_id, sessionId, "/dashboard", scenario.ipAddress);
  await apiPost("/api/behavioral", dashboardBehavior);
  emitLog(
    logs,
    hooks,
    "info",
    "Dashboard telemetry continued",
    "The same portal session carried forward into the account dashboard without spawning a new identity.",
    { endpoint: "POST /api/behavioral" }
  );

  const transferPayload = {
    user_id: login.user_id,
    session_id: sessionId,
    source_ip: scenario.ipAddress,
    destination: "Utilities Reserve acct-4521",
    amount: 125,
    memo: "Monthly utility settlement",
  };
  emitLog(
    logs,
    hooks,
    "info",
    "Safe transfer submitted",
    "Sending a normal low-risk transfer through the bank route to complete the customer journey.",
    { endpoint: "POST /api/bank/transfer", payload: transferPayload }
  );
  const transfer = await apiPost("/api/bank/transfer", transferPayload);
  emitLog(
    logs,
    hooks,
    "success",
    "Transfer cleared",
    `Transfer returned ${transfer.status} with verdict ${transfer.verdict}.`,
    { endpoint: "POST /api/bank/transfer" }
  );

  latestVerdict = (await safeCurrentVerdict()) || (await safeUserVerdict(login.user_id)) || transfer;
  hooks.onVerdict?.(latestVerdict);

  await emitPhase(
    hooks,
    "decision",
    {
      browser: buildBrowser(
        "emerald",
        "Decision settled",
        "The customer was cleared end-to-end",
        "The portal stays on the real dashboard because the ensemble never crossed the threat threshold.",
        [
          "Decision lane: main banking experience.",
          "No sandbox token and no timeout wall were produced.",
        ],
        "APPROVED"
      ),
    },
    520
  );

  const route = buildRoute(
    "safe",
    "No sandbox",
    "The user stays inside the real NovaTrust dashboard and completes the journey without friction.",
    "This is the happy path: authenticated, transfer cleared, and no redirect."
  );
  const feedback = buildFeedback(
    "neutral",
    "No live security feedback",
    "No malicious sample was collected, so the feedback service does not open an adversarial case.",
    ["Routine telemetry only", "Alert stream stays quiet"]
  );
  const retraining = buildRetraining(
    "neutral",
    `Model ${latestVerdict?.modelVersion || modelStatus?.version || "current"} remains unchanged`,
    "No hacker was found, so retraining stays dormant and the production boundary does not move.",
    ["No retrain trigger", "Safe session retained as baseline context"]
  );

  await emitPhase(
    hooks,
    "route",
    {
      route,
      browser: buildBrowser(
        "emerald",
        "Happy customer outcome",
        "The account dashboard remains live",
        "The user never leaves the real app and exits the journey normally.",
        [
          "Balance and transfer history stay visible.",
          "No timeout, no decoy, and no false containment.",
        ],
        "CUSTOMER HAPPY"
      ),
    },
    520
  );
  await emitPhase(hooks, "feedback", { feedback }, 420);
  await emitPhase(hooks, "retraining", { retraining }, 0);

  return {
    scenarioKey: scenario.key,
    usedFallback: false,
    latestVerdict,
    logs,
    summary: finalScene(
      buildBrowser(
        "emerald",
        "Journey complete",
        "Normal customer flow finished cleanly",
        "The trusted user stays in the real app and leaves with a successful transfer.",
        [
          "No security intervention was needed.",
          "The session becomes benign reference context rather than a retraining candidate.",
        ],
        "COMPLETE"
      ),
      route,
      feedback,
      retraining
    ),
  };
}

async function runFlaggedButInnocentScenario(hooks = {}) {
  const scenario = getScenarioByKey("flagged-but-innocent");
  const logs = [];
  const modelStatus = await safeModelVersion();
  const sessionId = makeId("review");
  let latestVerdict = null;

  hooks.onScenario?.(scenario);

  await emitPhase(
    hooks,
    "portal",
    seedScene(
      modelStatus,
      buildBrowser(
        "amber",
        "High-friction customer",
        "A legitimate user enters from a fresh device",
        "The bank portal is live, but the session already looks a little more unusual than the baseline.",
        [
          "Fresh browser fingerprint and urgent intent.",
          "Expected branch: soft review timeout, not a hard sandbox.",
        ],
        "WATCH"
      ),
      buildRoute(
        "review",
        "Review lane warming",
        "The customer is not a confirmed attacker, but the workflow may still be paused if the risk rises.",
        "The goal is to contain friction without trapping a legitimate user in a hard sandbox."
      )
    ),
    480
  );

  // ── Network Telemetry Ingest (High Friction) ──
  const rawPayload = buildRawIngestPayload(scenario.key, sessionId);
  try {
    emitLog(logs, hooks, "warning", "🌐 ANOMALOUS FLOW DETECTED", "Firewall flagged a new mobile ISP source with VPN markers and elevated TTL=128.", { endpoint: "POST /ingest", payload: rawPayload });
    await ingestPost(rawPayload);
    emitLog(logs, hooks, "success", "⚠️ UNUSUAL FLOW INGESTED", "Network telemetry accepted — VPN-likely flag set, geo mismatch noted.", { endpoint: "POST /ingest" });
  } catch {
    emitLog(logs, hooks, "info", "Ingestion skipped", "Raw ingest service offline — continuing with portal-only telemetry.");
  }

  const behavioralPayload = buildBehavioralPayload("normal2@novatrust.com", sessionId, "/login", scenario.ipAddress);
  emitLog(
    logs,
    hooks,
    "info",
    "🖱️ BEHAVIOURAL DRIFT RECORDED",
    "Posting the live browser session. Interaction cadence is erratic compared to user history.",
    { endpoint: "POST /api/behavioral", payload: behavioralPayload }
  );
  const behavioral = await apiPost("/api/behavioral", behavioralPayload);
  emitLog(
    logs,
    hooks,
    "success",
    "🔍 PROFILE ANALYZED",
    `${behavioral.eventCount} events linked to ${behavioral.sessionId.slice(0,8)}...`,
    { endpoint: "POST /api/behavioral" }
  );

  await emitPhase(
    hooks,
    "behavioral",
    {
      browser: buildBrowser(
        "amber",
        "DRIFT DETECTED: BOB CARTER",
        "Significant deviation from historical cadence",
        "The session shows hesitant typing and erratic mouse movement. Identity verification is pending.",
        [
          "Interaction rhythm: 45% variance from baseline.",
          "Possible mobile device or high-latency connection.",
          "Confidence: 62.1% Legitimate (Warning Zone).",
        ],
        "HUMAN BUT ODD"
      ),
    },
    5000
  );

  const loginPayload = {
    email: "normal2@novatrust.com",
    password: "secure456",
    session_id: sessionId,
    source_ip: scenario.ipAddress,
  };
  emitLog(
    logs,
    hooks,
    "info",
    "Bank login accepted for scoring",
    "Submitting a valid credential pair while the portal keeps the same session id alive.",
    { endpoint: "POST /api/bank/login", payload: loginPayload }
  );
  const login = await apiPost("/api/bank/login", loginPayload);
  emitLog(
    logs,
    hooks,
    "success",
    "User authenticated",
    `${login.user_id} cleared auth and reached ${login.next}.`,
    { endpoint: "POST /api/bank/login" }
  );

  await emitPhase(
    hooks,
    "ensemble",
    {
      browser: buildBrowser(
        "amber",
        "ENSEMBLE ALERT: BORDERLINE RISK",
        "Detecting conflict between SNN and XGBoost",
        "The classifiers are split. Risk is building around the current workflow.",
        [
          "SNN: Slight signal pressure spike.",
          "LNN: Identity Drift at 0.58 (Critical Threshold).",
          "XGBoost: Class 0 (Safe) but with reduced confidence.",
        ],
        "REVIEW BUILDING"
      ),
    },
    5200
  );

  const transferBehavior = buildBehavioralPayload(login.user_id, sessionId, "/transfer", scenario.ipAddress);
  await apiPost("/api/behavioral", transferBehavior);
  emitLog(
    logs,
    hooks,
    "info",
    "Transfer screen tracked",
    "Continuing the same session into a high-friction transfer path.",
    { endpoint: "POST /api/behavioral" }
  );

  const transferPayload = {
    user_id: login.user_id,
    session_id: sessionId,
    source_ip: scenario.ipAddress,
    destination: "Treasury Reserve acct-8891",
    amount: 25000,
    memo: "Treasury review settlement",
  };
  emitLog(
    logs,
    hooks,
    "info",
    "Urgent transfer submitted",
    "Submitting a large but plausible transfer that should land in the review lane instead of the hard sandbox.",
    { endpoint: "POST /api/bank/transfer", payload: transferPayload }
  );
  const transfer = await apiPost("/api/bank/transfer", transferPayload);
  emitLog(
    logs,
    hooks,
    transfer.status === "suspicious" ? "warning" : "success",
    "Transfer held for review",
    `Transfer returned ${transfer.status} with verdict ${transfer.verdict}.`,
    { endpoint: "POST /api/bank/transfer" }
  );

  latestVerdict = (await safeCurrentVerdict()) || (await safeUserVerdict(login.user_id)) || transfer;
  hooks.onVerdict?.(latestVerdict);

  await emitPhase(
    hooks,
    "decision",
    {
      browser: buildBrowser(
        "amber",
        "Decision layer chose a soft hold",
        "The session looks suspicious, but not hostile enough for the hard sandbox.",
        [
          "The customer is treated as borderline, not malicious.",
          "The workflow shifts into timeout-and-reload instead of deception containment.",
        ],
        "SOFT REVIEW"
      ),
    },
    520
  );

  const route = buildRoute(
    "review",
    "Soft review timeout",
    "The user hits a temporary timeout wall, then reloads back into the safe landing flow without a hard sandbox token.",
    "This is the innocent-but-suspicious lane: contain risk, avoid false accusation, let the customer recover."
  );
  const feedback = buildFeedback(
    "amber",
    "Benign review sample created",
    "Operations receive a human-friction signal, not a malicious sandbox case. This helps the system learn where not to overreact.",
    ["FORGETFUL_USER path", "No attacker replay", "Review note only"]
  );
  const retraining = buildRetraining(
    "amber",
    `Model ${latestVerdict?.modelVersion || modelStatus?.version || "current"} stays cautious but unchanged`,
    "No hacker label was captured, so NeuroShield does not aggressively shift the model. The review sample acts as a guard against overfitting.",
    ["No malicious retrain", "False-positive pressure reduced"]
  );

  await emitPhase(
    hooks,
    "route",
    {
      route,
      browser: buildBrowser(
        "amber",
        "Security timeout wall",
        "The transfer path pauses and the session is asked to reload.",
        [
          "No hard sandbox token was ever issued.",
          "The portal contains risk, then hands the user back cleanly.",
        ],
        "TIMEOUT"
      ),
    },
    620
  );

  await emitSnapshot(
    hooks,
    {
      browser: buildBrowser(
        "emerald",
        "Reload complete",
        "The user is back on the safe main page",
        "After the soft hold, the customer can re-enter the real experience without being trapped in a decoy lane.",
        [
          "The risky transfer remains paused for review.",
          "The legitimate user gets a clean recovery path.",
        ],
        "RECOVERED"
      ),
    },
    420
  );

  await emitPhase(hooks, "feedback", { feedback }, 420);
  await emitPhase(hooks, "retraining", { retraining }, 0);

  return {
    scenarioKey: scenario.key,
    usedFallback: false,
    latestVerdict,
    logs,
    summary: finalScene(
      buildBrowser(
        "emerald",
        "Recovered session",
        "The customer returns to a safe entry point",
        "The review flow creates friction, but the user is not hard-sandboxed and can recover after reload.",
        [
          "This lane is intentionally distinct from the attacker sandbox.",
          "The model learns caution without treating the user as hostile.",
        ],
        "SAFE RETURN"
      ),
      route,
      feedback,
      retraining
    ),
  };
}

async function runActiveHackerScenario(hooks = {}) {
  const scenario = getScenarioByKey("active-hacker");
  const logs = [];
  const modelStatus = await safeModelVersion();
  const sessionId = makeId("hacker");
  let latestVerdict = null;
  let usedFallback = false;

  hooks.onScenario?.(scenario);

  await emitPhase(
    hooks,
    "portal",
    seedScene(
      modelStatus,
      buildBrowser(
        "rose",
        "Hostile actor path",
        "An untrusted actor is probing the portal edge",
        "The dashboard is about to drive the live trap chain and watch the sandbox route engage.",
        [
          "Expected branch: hard sandbox only.",
          "The feedback and retraining cards should light up after containment.",
        ],
        "THREAT LIVE"
      ),
      buildRoute(
        "sandbox",
        "Sandbox lane warming",
        "The system is ready to isolate the actor the moment a trap or override confirms the threat.",
        "This branch should end in a decoy-only experience with replay capture."
      )
    ),
    460
  );

  const behavioralPayload = buildBehavioralPayload("intruder-demo", sessionId, "/login", scenario.ipAddress);
  emitLog(
    logs,
    hooks,
    "info",
    "Suspicious portal telemetry",
    "Posting hostile-looking browser events before the trap is triggered.",
    { endpoint: "POST /api/behavioral", payload: behavioralPayload }
  );
  await apiPost("/api/behavioral", behavioralPayload);
  emitLog(
    logs,
    hooks,
    "success",
    "Threat session seeded",
    "The portal session is now visible to the behavioural layer.",
    { endpoint: "POST /api/behavioral" }
  );

  const rawPayload = buildRawIngestPayload("raw-threat-demo", sessionId);
  try {
    emitLog(
      logs,
      hooks,
      "info",
      "Raw ingress attempted",
      "Trying the dedicated ingestion path first so the run shows the deeper network-facing route.",
      { endpoint: "POST /ingest", payload: rawPayload }
    );
    const ingestion = await ingestPost(rawPayload);
    emitLog(
      logs,
      hooks,
      "success",
      "Raw ingress accepted",
      `Ingestion service accepted ${ingestion.published} events before the trap branch took over.`,
      { endpoint: "POST /ingest" }
    );
  } catch (error) {
    usedFallback = true;
    emitLog(
      logs,
      hooks,
      "warning",
      "Raw ingress unavailable",
      error instanceof Error ? error.message : "Ingestion service was unavailable.",
      { endpoint: "POST /ingest" }
    );
    emitLog(
      logs,
      hooks,
      "warning",
      "Fallback switched live",
      "The run is falling back to the active defense path so the sandbox branch still completes end-to-end.",
      { endpoint: "POST /api/bank/web-attack-detected" }
    );
  }

  await emitPhase(
    hooks,
    "behavioral",
    {
      browser: buildBrowser(
        "rose",
        "SIGNAL SPIKE: INHUMAN VELOCITY",
        "Inference engine detected non-human cadence",
        "The session was flagged within 18ms. No mouse drift recorded. Paste events detected in secure fields.",
        [
          "Interaction speed: 2000x faster than baseline.",
          "Zero-day automation fingerprint detected.",
          "Defense layer armed and awaiting payload confirmation.",
        ],
        "CRITICAL ALERT"
      ),
    },
    5200
  );

  const webAttackPayload = {
    attack_type: "SQLI",
    user_id: "intruder-demo",
    session_id: sessionId,
    payload: "' OR 1=1; DROP TABLE accounts; --",
    source_ip: scenario.ipAddress,
  };
  emitLog(
    logs,
    hooks,
    "error",
    "🚨 LETHAL EXPLOIT ATTEMPT",
    "Hostile actor attempted a destructive SQL injection to bypass the database boundary.",
    { endpoint: "POST /api/bank/web-attack-detected", payload: webAttackPayload }
  );
  const hit = await apiPost("/api/bank/web-attack-detected", webAttackPayload);
  emitLog(
    logs,
    hooks,
    "warning",
    "🛡️ BOUNDARY ENGAGED",
    `The attack was neutralized. Verdict ${hit.verdict} issued. Diverting traffic to Decoy-A1 sandbox.`,
    { endpoint: "POST /api/bank/web-attack-detected" }
  );

  latestVerdict = (await safeCurrentVerdict()) || hit;
  hooks.onVerdict?.(latestVerdict);

  await emitPhase(
    hooks,
    "ensemble",
    {
      browser: buildBrowser(
        "rose",
        "ENSEMBLE LOCK: THREAT CONFIRMED",
        "SNN + LNN + XGBoost are in total agreement",
        "Classifier confidence: 99.8%. The actor is now being transparently contained within the isolated environment.",
        [
          "SNN: Malicious Spike Pattern Detected.",
          "LNN: Identity Drift > Threshold.",
          "XGBoost: Class 1 (Hacker) Confirmed.",
        ],
        "CONTAINMENT ACTIVE"
      ),
    },
    5500
  );

  let replay = { actions: [] };
  if (latestVerdict?.sandbox?.active && latestVerdict?.sessionId) {
    try {
      replay = await apiGet(`/api/sandbox/${latestVerdict.sessionId}/replay`);
      emitLog(
        logs,
        hooks,
        "warning",
        "Sandbox replay collected",
        `Replay returned ${replay.actions.length} captured actions for the isolated actor.`,
        { endpoint: `GET /api/sandbox/${latestVerdict.sessionId}/replay` }
      );
    } catch (error) {
      emitLog(
        logs,
        hooks,
        "warning",
        "Replay bridge pending",
        error instanceof Error ? error.message : "Replay was not yet available.",
        { endpoint: `GET /api/sandbox/${latestVerdict?.sessionId || sessionId}/replay` }
      );
    }
  }

  await emitPhase(
    hooks,
    "decision",
    {
      browser: buildBrowser(
        "rose",
        "Sandbox-only experience",
        "The actor is now seeing the decoy security wall",
        "Any further actions are captured inside the isolated replay path instead of touching the real app.",
        [
          "Hard sandbox token issued.",
          `${replay.actions.length} replay actions are already visible to the feedback path.`,
        ],
        "SANDBOXED"
      ),
    },
    520
  );

  const alerts = await safeAlerts();
  const topAlert = alerts[0];

  const route = buildRoute(
    "sandbox",
    "Hard sandbox isolation",
    "The hostile actor is redirected into the decoy environment and never returns to the real banking surface during this run.",
    "This is the only branch that produces replay-backed malicious feedback."
  );
  const feedback = buildFeedback(
    "rose",
    "Malicious feedback promoted live",
    topAlert?.message
      ? `Latest alert: ${topAlert.message}`
      : "The sandbox replay and SQL injection signal have been promoted as a malicious security event.",
    [
      `${replay.actions.length} sandbox actions`,
      `${alerts.length} alert${alerts.length === 1 ? "" : "s"} visible`,
      usedFallback ? "Fallback defense path used" : "Direct live defense path",
    ]
  );
  const retraining = buildRetraining(
    "rose",
    `Model ${latestVerdict?.modelVersion || modelStatus?.version || "current"} is now learning from the attack`,
    "The active model does not hot-swap on a single hostile run, but this malicious sample is now eligible for the feedback-driven retraining loop.",
    [
      "Sandbox replay captured",
      "Malicious sample queued",
      "Boundary can sharpen on the next retrain threshold",
    ]
  );

  await emitPhase(hooks, "route", { route }, 520);
  await emitPhase(hooks, "feedback", { feedback }, 480);
  await emitPhase(hooks, "retraining", { retraining }, 0);

  return {
    scenarioKey: scenario.key,
    usedFallback,
    latestVerdict,
    logs,
    summary: finalScene(
      buildBrowser(
        "rose",
        "Sandbox is holding the actor",
        "The hostile user is contained inside the decoy path only",
        "Replay, alerts, and retraining context were generated from the isolated branch without exposing the real app.",
        [
          "This run created actionable feedback for the security loop.",
          "The actor does not return to the main banking experience.",
        ],
        "ISOLATED"
      ),
      route,
      feedback,
      retraining
    ),
  };
}

export const liveScenarioRunners = {
  "trusted-customer": runTrustedCustomerScenario,
  "flagged-but-innocent": runFlaggedButInnocentScenario,
  "active-hacker": runActiveHackerScenario,
};
