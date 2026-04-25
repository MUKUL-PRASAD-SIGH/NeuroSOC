export interface BehavioralPayload {
  userId: string;
  sessionId: string;
  events: Array<Record<string, unknown>>;
  page?: string;
  sourceIp?: string;
}

export interface BankLoginPayload {
  email: string;
  password: string;
  sessionId: string;
  sourceIp?: string;
}

export interface BankTransferPayload {
  userId: string;
  sessionId: string;
  sourceIp?: string;
  destination: string;
  amount: number;
  memo?: string;
  confirmRoutingNumber?: string;
}

export interface RawIngestEvent {
  src_ip: string;
  dst_ip: string;
  src_port: number;
  dst_port: number;
  protocol: string;
  length: number;
  ttl?: number;
  flags?: Record<string, unknown>;
  extra?: Record<string, unknown>;
}

export interface RawIngestPayload {
  userId?: string;
  sessionId?: string;
  events: RawIngestEvent[];
}

export interface BehavioralCaptureResponse {
  status: string;
  userId?: string;
  sessionId: string;
  eventCount?: number;
  count?: number;
  vector?: number[];
}

export interface PortalVerdictSnapshot {
  sessionId?: string | null;
  userId?: string;
  verdict: string;
  confidence: number;
  snnScore: number;
  lnnClass: string;
  xgbClass: string;
  behavioralDelta: number;
  modelVersion?: string;
  sandbox?: { active: boolean; mode?: string; sandboxToken?: string; sandboxPath?: string } | null;
  recentVerdicts?: Array<{ id: string; verdict: string; score: number; timestamp: string | number }>;
  history?: Array<Record<string, unknown>>;
}

export interface ModelVersionResponse {
  version: string;
  versions?: Array<{ label: string; value: string }>;
  validationF1?: Array<{ label: string; value: number }>;
  lastRetrainedAt?: string;
  activeModels?: string[];
}

export interface AlertPayload {
  id: string;
  severity: string;
  verdict: string;
  message: string;
  timestamp: string | number;
  sourceIp?: string;
  userId?: string;
  userName?: string;
  locationLabel?: string;
  score?: number;
  dimensions?: string[];
  recentVerdicts?: Array<{ id: string; verdict: string; score: number; timestamp: string | number }>;
  modelVersion?: string;
}

const API_BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true';

export function buildApiUrl(path: string) {
  return API_BASE_URL ? `${API_BASE_URL}${path}` : path;
}

async function requestJson<T>(input: string, init?: RequestInit): Promise<T> {
  if (USE_MOCKS) {
    return mockRequestJson<T>(input, init);
  }

  const response = await fetch(buildApiUrl(input), {
    credentials: 'include',
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message =
      (typeof data?.detail === 'string' && data.detail) ||
      (typeof data?.error === 'string' && data.error) ||
      `Request failed with status ${response.status}`;
    throw new Error(message);
  }
  return data as T;
}

async function mockRequestJson<T>(input: string, init?: RequestInit): Promise<T> {
  const {
    mockAlerts,
    mockCurrentVerdict,
    mockHoneypotHit,
    mockLoginBank,
    mockModelVersion,
    mockPostBehavioral,
    mockSandboxReplay,
    mockTransferBank,
    mockUserVerdict,
    mockWebAttack,
  } = await import('./portalMock');
  const body = init?.body ? JSON.parse(String(init.body)) : {};

  if (input === '/api/behavioral') {
    return mockPostBehavioral({
      userId: body.user_id,
      sessionId: body.session_id,
      events: body.events || [],
      page: body.page,
    }) as Promise<T>;
  }

  if (input === '/api/bank/login') {
    return mockLoginBank({
      email: body.email,
      password: body.password,
      sessionId: body.session_id,
    }) as Promise<T>;
  }

  if (input === '/api/bank/transfer') {
    return mockTransferBank({
      userId: body.user_id,
      sessionId: body.session_id,
      destination: body.destination,
      amount: body.amount,
      memo: body.memo,
      confirmRoutingNumber: body.confirm_routing_number,
    }) as Promise<T>;
  }

  if (input === '/api/bank/honeypot-hit') {
    return mockHoneypotHit(body.source, body.user_id, body.session_id) as Promise<T>;
  }

  if (input === '/api/bank/web-attack-detected') {
    return mockWebAttack(body.user_id, body.session_id, body.payload) as Promise<T>;
  }

  if (input === '/api/verdicts/current') {
    return mockCurrentVerdict() as Promise<T>;
  }

  if (input === '/api/model/version') {
    return mockModelVersion() as Promise<T>;
  }

  if (input === '/api/alerts') {
    return mockAlerts() as Promise<T>;
  }

  if (input === '/ingest') {
    return Promise.resolve({
      status: 'ok',
      published: Array.isArray(body.events) ? body.events.length : 0,
      mode: 'mock',
    } as T);
  }

  const userVerdictMatch = input.match(/^\/api\/verdicts\/([^/]+)$/);
  if (userVerdictMatch) {
    return mockUserVerdict(decodeURIComponent(userVerdictMatch[1])) as Promise<T>;
  }

  const replayMatch = input.match(/^\/api\/sandbox\/([^/]+)\/replay$/);
  if (replayMatch) {
    return mockSandboxReplay(decodeURIComponent(replayMatch[1])) as Promise<T>;
  }

  throw new Error(`No mock handler registered for ${input}`);
}

export function postBehavioral(payload: BehavioralPayload) {
  return requestJson<BehavioralCaptureResponse>('/api/behavioral', {
    method: 'POST',
    body: JSON.stringify({
      user_id: payload.userId,
      session_id: payload.sessionId,
      source_ip: payload.sourceIp,
      events: payload.events,
      page: payload.page,
    }),
  });
}

export function loginBank(payload: BankLoginPayload) {
  return requestJson<{
    authenticated: boolean;
    user_id: string;
    displayName?: string;
    sessionId: string;
    verdict: string;
    confidence: number;
    sandbox?: { active: boolean; mode?: string; sandboxToken?: string; sandboxPath?: string } | null;
    next: string;
    account?: { balance?: number; accountMasked?: string };
    error?: string;
  }>('/api/bank/login', {
    method: 'POST',
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
      session_id: payload.sessionId,
      source_ip: payload.sourceIp,
    }),
  });
}

export function transferBank(payload: BankTransferPayload) {
  return requestJson<{
    status: string;
    sessionId: string;
    verdict: string;
    confidence: number;
    sandbox?: { active: boolean; mode?: string; sandboxToken?: string; sandboxPath?: string } | null;
    message: string;
  }>('/api/bank/transfer', {
    method: 'POST',
    body: JSON.stringify({
      user_id: payload.userId,
      session_id: payload.sessionId,
      source_ip: payload.sourceIp,
      destination: payload.destination,
      amount: payload.amount,
      memo: payload.memo,
      confirm_routing_number: payload.confirmRoutingNumber || undefined,
    }),
  });
}

export function reportHoneypotHit(source: string, userId: string, sessionId: string, sourceIp?: string) {
  return requestJson<{
    status: string;
    sessionId: string;
    verdict: string;
    confidence?: number;
    sandbox?: { active: boolean; mode?: string; sandboxToken?: string; sandboxPath?: string } | null;
  }>('/api/bank/honeypot-hit', {
    method: 'POST',
    body: JSON.stringify({
      source,
      user_id: userId,
      session_id: sessionId,
      source_ip: sourceIp,
    }),
  });
}

export function reportWebAttack(userId: string, sessionId: string, payload: string, sourceIp?: string) {
  return requestJson<{
    status: string;
    sessionId: string;
    verdict: string;
    confidence?: number;
    sandbox?: { active: boolean; mode?: string; sandboxToken?: string; sandboxPath?: string } | null;
  }>('/api/bank/web-attack-detected', {
    method: 'POST',
    body: JSON.stringify({
      attack_type: 'SQLI',
      payload,
      user_id: userId,
      session_id: sessionId,
      source_ip: sourceIp,
    }),
  });
}

export function getCurrentVerdict() {
  return requestJson<PortalVerdictSnapshot>('/api/verdicts/current');
}

export function getUserVerdict(userId: string) {
  return requestJson<PortalVerdictSnapshot>(`/api/verdicts/${userId}`);
}

export function getSandboxReplay(sessionId: string) {
  return requestJson<{
    session_id?: string;
    sandbox_token?: string;
    mode?: string;
    actions: Array<Record<string, unknown>>;
  }>(`/api/sandbox/${sessionId}/replay`);
}

export function getModelVersion() {
  return requestJson<ModelVersionResponse>('/api/model/version');
}

export function getAlerts() {
  return requestJson<AlertPayload[]>('/api/alerts');
}

export function postRawIngest(payload: RawIngestPayload) {
  return requestJson<{
    status: string;
    published: number;
    detail?: string;
    mode?: string;
  }>('/ingest', {
    method: 'POST',
    body: JSON.stringify({
      user_id: payload.userId,
      session_id: payload.sessionId,
      events: payload.events,
    }),
  });
}
