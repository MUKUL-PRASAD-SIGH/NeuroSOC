export interface BehavioralPayload {
  userId: string;
  sessionId: string;
  events: Array<Record<string, unknown>>;
  page?: string;
}

export interface BankLoginPayload {
  email: string;
  password: string;
  sessionId: string;
}

export interface BankTransferPayload {
  userId: string;
  sessionId: string;
  destination: string;
  amount: number;
  memo?: string;
  confirmRoutingNumber?: string;
}

import { getMockUser } from './portalMock';

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

function normalizeSandbox(sandbox: any) {
  if (!sandbox) {
    return null;
  }

  return {
    active: sandbox.active !== false,
    mode: sandbox.mode || 'live',
    sandboxToken: sandbox.sandboxToken || sandbox.sandbox_token || null,
    sandboxPath: sandbox.sandboxPath || sandbox.sandbox_path || '/security-alert',
  };
}

async function mockRequestJson<T>(input: string, init?: RequestInit): Promise<T> {
  const {
    mockCurrentVerdict,
    mockHoneypotHit,
    mockLoginBank,
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
  return requestJson('/api/behavioral', {
    method: 'POST',
    body: JSON.stringify({
      user_id: payload.userId,
      session_id: payload.sessionId,
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
    }),
  }).then((raw: any) => {
    if (USE_MOCKS) {
      return raw;
    }

    const profile = getMockUser(payload.email);
    const authenticated = Boolean(profile && profile.password === payload.password);
    const sandbox = normalizeSandbox(raw.sandbox);
    const verdict = raw.verdict || (authenticated ? 'LEGITIMATE' : 'FORGETFUL_USER');

    return {
      authenticated,
      user_id: raw.user_id || profile?.userId || payload.email,
      displayName: raw.displayName || profile?.displayName,
      sessionId: raw.sessionId || raw.session_id || payload.sessionId,
      verdict,
      confidence: typeof raw.confidence === 'number' ? raw.confidence : 0.85,
      sandbox: sandbox || (verdict === 'HACKER' ? { active: true, mode: 'live', sandboxToken: null, sandboxPath: '/security-alert' } : null),
      next: raw.next || ((sandbox?.active || verdict === 'HACKER') ? '/security-alert' : authenticated ? '/dashboard' : '/login'),
      account: raw.account || profile?.account
        ? {
            balance: raw.account?.balance ?? profile?.account.balance,
            accountMasked: raw.account?.accountMasked ?? profile?.account.accountMasked,
          }
        : undefined,
      error: authenticated ? undefined : raw.error || 'Invalid credentials. Please try again.',
    };
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
      recipient: payload.destination,
      amount: payload.amount,
      memo: payload.memo,
      confirm_routing_number: payload.confirmRoutingNumber || undefined,
    }),
  }).then((raw: any) => {
    if (USE_MOCKS) {
      return raw;
    }

    const sandbox = normalizeSandbox(raw.sandbox);
    return {
      status: raw.status || (sandbox?.active ? 'sandboxed' : 'accepted'),
      sessionId: raw.sessionId || raw.session_id || payload.sessionId,
      verdict: raw.verdict || 'LEGITIMATE',
      confidence: typeof raw.confidence === 'number' ? raw.confidence : 0.82,
      sandbox: sandbox,
      message: raw.message || (sandbox?.active ? 'Transfer moved into sandbox review.' : 'Transfer accepted for processing.'),
    };
  });
}

export function reportHoneypotHit(source: string, userId: string, sessionId: string) {
  return requestJson<{
    status: string;
    sessionId: string;
    verdict: string;
    sandbox?: { active: boolean; mode?: string; sandboxToken?: string; sandboxPath?: string } | null;
  }>('/api/bank/honeypot-hit', {
    method: 'POST',
    body: JSON.stringify({
      source,
      user_id: userId,
      session_id: sessionId,
    }),
  }).then((raw: any) => {
    if (USE_MOCKS) {
      return raw;
    }

    return {
      status: raw.status || 'captured',
      sessionId: raw.sessionId || raw.session_id || sessionId,
      verdict: raw.verdict || 'HACKER',
      sandbox: normalizeSandbox(raw.sandbox),
    };
  });
}

export function reportWebAttack(userId: string, sessionId: string, payload: string) {
  return requestJson<{
    status: string;
    sessionId: string;
    verdict: string;
    sandbox?: { active: boolean; mode?: string; sandboxToken?: string; sandboxPath?: string } | null;
  }>('/api/bank/web-attack-detected', {
    method: 'POST',
    body: JSON.stringify({
      attack_type: 'SQLI',
      payload,
      user_id: userId,
      session_id: sessionId,
    }),
  }).then((raw: any) => {
    if (USE_MOCKS) {
      return raw;
    }

    return {
      status: raw.status || 'captured',
      sessionId: raw.sessionId || raw.session_id || sessionId,
      verdict: raw.verdict || 'HACKER',
      sandbox: normalizeSandbox(raw.sandbox),
    };
  });
}

export function getCurrentVerdict() {
  return requestJson<{
    sessionId?: string | null;
    verdict: string;
    confidence: number;
    snnScore: number;
    lnnClass: string;
    xgbClass: string;
    behavioralDelta: number;
    sandbox?: { active: boolean; mode?: string; sandboxToken?: string; sandboxPath?: string } | null;
  }>('/api/verdicts/current');
}

export function getUserVerdict(userId: string) {
  return requestJson<{
    sessionId?: string | null;
    verdict: string;
    confidence: number;
    snnScore: number;
    lnnClass: string;
    xgbClass: string;
    behavioralDelta: number;
    sandbox?: { active: boolean; mode?: string; sandboxToken?: string; sandboxPath?: string } | null;
    recentVerdicts?: Array<{ id: string; verdict: string; score: number; timestamp: string | number }>;
  }>(`/api/verdicts/${userId}`);
}

export function getSandboxReplay(sessionId: string) {
  return requestJson<{
    session_id?: string;
    sandbox_token?: string;
    mode?: string;
    actions: Array<Record<string, unknown>>;
  }>(`/api/sandbox/${sessionId}/replay`);
}
