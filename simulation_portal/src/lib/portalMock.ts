import type { BehavioralPayload, BankLoginPayload, BankTransferPayload } from './portalApi';

export type PortalVerdict = 'LEGITIMATE' | 'FORGETFUL_USER' | 'HACKER';

export interface MockPortalUser {
  userId: string;
  email: string;
  password: string;
  displayName: string;
  role: string;
  account: {
    balance: number;
    accountMasked: string;
    income: number;
    expenses: number;
    creditScore: number;
    savingsGoal: number;
  };
  behaviorProfile: 'steady' | 'forgetful' | 'risky';
  transactions: Array<{
    id: string;
    type: 'DEBIT' | 'CREDIT';
    merchant: string;
    amount: number;
    date: string;
    category: string;
    status: string;
  }>;
}

export interface MockDashboardData {
  displayName: string;
  role: string;
  account: MockPortalUser['account'];
  transactions: MockPortalUser['transactions'];
}

type MockSandbox = { active: boolean; mode?: string; sandboxToken?: string; sandboxPath?: string } | null;

type MockState = {
  currentSessionId: string | null;
  currentUserId: string | null;
  verdict: PortalVerdict;
  confidence: number;
  snnScore: number;
  lnnClass: string;
  xgbClass: string;
  behavioralDelta: number;
  sandbox: MockSandbox;
  eventsBySession: Record<string, Array<Record<string, unknown>>>;
  replayBySession: Record<string, Array<Record<string, unknown>>>;
  recentVerdictsByUser: Record<string, Array<{ id: string; verdict: PortalVerdict; score: number; timestamp: string }>>;
};

const STORAGE_KEY = 'novatrust.portal.mock_state';

export const MOCK_USERS: MockPortalUser[] = [
  {
    userId: 'usr-4012',
    email: 'test@novatrust.com',
    password: 'password123',
    displayName: 'Ava Morales',
    role: 'Platinum Personal Banking',
    behaviorProfile: 'steady',
    account: {
      balance: 124560.12,
      accountMasked: '**** 8824',
      income: 8420,
      expenses: 4128.5,
      creditScore: 781,
      savingsGoal: 0.72,
    },
    transactions: [
      { id: 'tx-a1', type: 'DEBIT', merchant: 'Apple Store', amount: -1299, date: 'Apr 24, 2026', category: 'Technology', status: 'Settled' },
      { id: 'tx-a2', type: 'CREDIT', merchant: 'Remote Work Corp', amount: 4500, date: 'Apr 22, 2026', category: 'Income', status: 'Settled' },
      { id: 'tx-a3', type: 'DEBIT', merchant: 'Whole Foods Market', amount: -156.42, date: 'Apr 21, 2026', category: 'Groceries', status: 'Settled' },
      { id: 'tx-a4', type: 'DEBIT', merchant: 'Stripe SaaS Billing', amount: -49, date: 'Apr 20, 2026', category: 'Business', status: 'Settled' },
      { id: 'tx-a5', type: 'CREDIT', merchant: 'Stock Dividend', amount: 124.5, date: 'Apr 18, 2026', category: 'Investment', status: 'Settled' },
      { id: 'tx-a6', type: 'DEBIT', merchant: 'Metro Energy', amount: -212.14, date: 'Apr 16, 2026', category: 'Utilities', status: 'Settled' },
      { id: 'tx-a7', type: 'DEBIT', merchant: 'Bayview Gym', amount: -89, date: 'Apr 15, 2026', category: 'Health', status: 'Settled' },
      { id: 'tx-a8', type: 'CREDIT', merchant: 'Freelance Retainer', amount: 1850, date: 'Apr 12, 2026', category: 'Income', status: 'Settled' },
    ],
  },
  {
    userId: 'usr-4018',
    email: 'leo@novatrust.demo',
    password: 'Leo@1234',
    displayName: 'Leo Bennett',
    role: 'Business Checking',
    behaviorProfile: 'forgetful',
    account: {
      balance: 38420.77,
      accountMasked: '**** 4410',
      income: 12600,
      expenses: 9788.18,
      creditScore: 704,
      savingsGoal: 0.44,
    },
    transactions: [
      { id: 'tx-l1', type: 'DEBIT', merchant: 'Cloud Runtime Inc', amount: -980, date: 'Apr 24, 2026', category: 'Infrastructure', status: 'Settled' },
      { id: 'tx-l2', type: 'CREDIT', merchant: 'Client Wire', amount: 7900, date: 'Apr 23, 2026', category: 'Income', status: 'Settled' },
      { id: 'tx-l3', type: 'DEBIT', merchant: 'Airline Booking', amount: -612.8, date: 'Apr 21, 2026', category: 'Travel', status: 'Pending' },
      { id: 'tx-l4', type: 'DEBIT', merchant: 'Office Depot', amount: -218.45, date: 'Apr 19, 2026', category: 'Office', status: 'Settled' },
      { id: 'tx-l5', type: 'DEBIT', merchant: 'Ad Platform', amount: -1260, date: 'Apr 17, 2026', category: 'Marketing', status: 'Settled' },
      { id: 'tx-l6', type: 'CREDIT', merchant: 'Project Milestone Payout', amount: 5400, date: 'Apr 14, 2026', category: 'Income', status: 'Settled' },
      { id: 'tx-l7', type: 'DEBIT', merchant: 'Payroll Transfer', amount: -2900, date: 'Apr 10, 2026', category: 'Payroll', status: 'Settled' },
    ],
  },
  {
    userId: 'usr-4023',
    email: 'mia@novatrust.demo',
    password: 'Mia@1234',
    displayName: 'Mia Chen',
    role: 'Family Wealth',
    behaviorProfile: 'risky',
    account: {
      balance: 905880.45,
      accountMasked: '**** 1902',
      income: 44250,
      expenses: 28610.2,
      creditScore: 812,
      savingsGoal: 0.91,
    },
    transactions: [
      { id: 'tx-m1', type: 'DEBIT', merchant: 'International Escrow', amount: -25000, date: 'Apr 24, 2026', category: 'Wire', status: 'Review' },
      { id: 'tx-m2', type: 'CREDIT', merchant: 'Treasury Sweep', amount: 31000, date: 'Apr 22, 2026', category: 'Investment', status: 'Settled' },
      { id: 'tx-m3', type: 'DEBIT', merchant: 'Luxury Travel Group', amount: -8400, date: 'Apr 21, 2026', category: 'Travel', status: 'Settled' },
      { id: 'tx-m4', type: 'DEBIT', merchant: 'Art Brokerage', amount: -11850, date: 'Apr 19, 2026', category: 'Collectibles', status: 'Pending' },
      { id: 'tx-m5', type: 'CREDIT', merchant: 'Bond Coupon Payment', amount: 12400, date: 'Apr 16, 2026', category: 'Investment', status: 'Settled' },
      { id: 'tx-m6', type: 'DEBIT', merchant: 'Property Tax Office', amount: -7620.55, date: 'Apr 13, 2026', category: 'Property', status: 'Settled' },
      { id: 'tx-m7', type: 'DEBIT', merchant: 'Private Aviation Charter', amount: -14250, date: 'Apr 11, 2026', category: 'Travel', status: 'Settled' },
    ],
  },
];

const FALLBACK_DASHBOARD_DATA: MockDashboardData = {
  displayName: 'Alex Carter',
  role: 'Premier Checking',
  account: {
    balance: 8432.67,
    accountMasked: '**** 8742',
    income: 6120,
    expenses: 4289.23,
    creditScore: 728,
    savingsGoal: 0.58,
  },
  transactions: [
    { id: 'tx-f1', type: 'DEBIT', merchant: 'Corner Market', amount: -84.19, date: 'Apr 24, 2026', category: 'Groceries', status: 'Settled' },
    { id: 'tx-f2', type: 'CREDIT', merchant: 'Primary Payroll', amount: 2800, date: 'Apr 23, 2026', category: 'Income', status: 'Settled' },
    { id: 'tx-f3', type: 'DEBIT', merchant: 'City Utilities', amount: -147.6, date: 'Apr 20, 2026', category: 'Utilities', status: 'Settled' },
    { id: 'tx-f4', type: 'DEBIT', merchant: 'Fuel Station', amount: -62.77, date: 'Apr 18, 2026', category: 'Transport', status: 'Settled' },
    { id: 'tx-f5', type: 'CREDIT', merchant: 'Tax Refund', amount: 920, date: 'Apr 13, 2026', category: 'Refund', status: 'Settled' },
  ],
};

export function getMockDashboardData(userIdOrEmail?: string): MockDashboardData {
  const profile = getMockUser(userIdOrEmail);
  if (!profile) {
    return FALLBACK_DASHBOARD_DATA;
  }

  return {
    displayName: profile.displayName,
    role: profile.role,
    account: profile.account,
    transactions: profile.transactions,
  };
}

function defaultState(): MockState {
  return {
    currentSessionId: null,
    currentUserId: null,
    verdict: 'LEGITIMATE',
    confidence: 0.88,
    snnScore: 0.21,
    lnnClass: 'LEGITIMATE',
    xgbClass: 'LEGITIMATE',
    behavioralDelta: 0.14,
    sandbox: null,
    eventsBySession: {},
    replayBySession: {},
    recentVerdictsByUser: {},
  };
}

function readState(): MockState {
  if (typeof window === 'undefined') return defaultState();
  try {
    return { ...defaultState(), ...JSON.parse(window.localStorage.getItem(STORAGE_KEY) || '{}') };
  } catch {
    return defaultState();
  }
}

function writeState(state: MockState) {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }
  return state;
}

function getUserByEmail(email: string) {
  return MOCK_USERS.find((user) => user.email.toLowerCase() === email.trim().toLowerCase());
}

export function getMockUser(userIdOrEmail?: string) {
  return MOCK_USERS.find((user) => user.userId === userIdOrEmail || user.email === userIdOrEmail);
}

function scoreSession(user: MockPortalUser | undefined, payload: { passwordOk?: boolean; amount?: number; destination?: string; memo?: string; honeypot?: boolean }) {
  let risk = user?.behaviorProfile === 'risky' ? 0.54 : user?.behaviorProfile === 'forgetful' ? 0.36 : 0.16;
  if (payload.passwordOk === false) risk += 0.3;
  if (payload.honeypot) risk += 0.55;
  if ((payload.amount || 0) > 10000) risk += 0.25;
  if ((payload.amount || 0) > 50000) risk += 0.25;
  if (/(select|union|drop|script|--|or\s+1=1)/i.test(`${payload.destination || ''} ${payload.memo || ''}`)) risk += 0.7;
  risk = Math.min(0.99, risk);

  const verdict: PortalVerdict = risk >= 0.78 ? 'HACKER' : risk >= 0.42 ? 'FORGETFUL_USER' : 'LEGITIMATE';
  return {
    verdict,
    confidence: Number((0.74 + Math.min(risk, 0.24)).toFixed(2)),
    snnScore: Number(risk.toFixed(3)),
    lnnClass: verdict,
    xgbClass: risk > 0.66 ? 'HACKER' : verdict,
    behavioralDelta: Number(Math.min(0.98, risk + 0.08).toFixed(3)),
    sandbox: verdict === 'HACKER'
      ? { active: true, mode: 'isolation', sandboxToken: `sbx-${Date.now().toString(36)}`, sandboxPath: '/security-alert' }
      : null,
  };
}

function pushVerdict(state: MockState, userId: string | null, score: ReturnType<typeof scoreSession>) {
  if (!userId) return;
  const previous = state.recentVerdictsByUser[userId] || [];
  state.recentVerdictsByUser[userId] = [
    { id: `verdict-${Date.now()}`, verdict: score.verdict, score: score.snnScore, timestamp: new Date().toISOString() },
    ...previous,
  ].slice(0, 12);
}

function applyScore(state: MockState, sessionId: string, userId: string | null, score: ReturnType<typeof scoreSession>) {
  state.currentSessionId = sessionId;
  state.currentUserId = userId;
  state.verdict = score.verdict;
  state.confidence = score.confidence;
  state.snnScore = score.snnScore;
  state.lnnClass = score.lnnClass;
  state.xgbClass = score.xgbClass;
  state.behavioralDelta = score.behavioralDelta;
  state.sandbox = score.sandbox;
  pushVerdict(state, userId, score);
}

export async function mockPostBehavioral(payload: BehavioralPayload) {
  const state = readState();
  state.eventsBySession[payload.sessionId] = [
    ...(state.eventsBySession[payload.sessionId] || []),
    ...payload.events,
  ].slice(-200);
  state.replayBySession[payload.sessionId] = [
    ...(state.replayBySession[payload.sessionId] || []),
    ...payload.events.map((event) => ({ ...event, page: payload.page })),
  ].slice(-100);
  writeState(state);
  return { status: 'captured', sessionId: payload.sessionId, count: state.eventsBySession[payload.sessionId].length };
}

export async function mockLoginBank(payload: BankLoginPayload) {
  const user = getUserByEmail(payload.email);
  const passwordOk = Boolean(user && user.password === payload.password);
  const score = scoreSession(user, { passwordOk });
  const state = readState();
  applyScore(state, payload.sessionId, user?.userId || null, score);
  writeState(state);

  if (!user) {
    return {
      authenticated: false,
      user_id: 'unknown-user',
      sessionId: payload.sessionId,
      verdict: 'FORGETFUL_USER',
      confidence: 0.81,
      sandbox: null,
      next: '/login',
      error: 'Unknown demo user. Pick one of the three seeded accounts.',
    };
  }

  return {
    authenticated: passwordOk,
    user_id: user.userId,
    displayName: user.displayName,
    sessionId: payload.sessionId,
    verdict: score.verdict,
    confidence: score.confidence,
    sandbox: score.sandbox,
    next: score.sandbox?.active ? '/security-alert' : passwordOk ? '/dashboard' : '/login',
    account: user.account,
    error: passwordOk ? undefined : 'Password did not match this demo profile.',
  };
}

export async function mockTransferBank(payload: BankTransferPayload) {
  const user = getMockUser(payload.userId);
  const score = scoreSession(user, {
    amount: payload.amount,
    destination: payload.destination,
    memo: payload.memo,
    honeypot: Boolean(payload.confirmRoutingNumber),
  });
  const state = readState();
  applyScore(state, payload.sessionId, user?.userId || payload.userId, score);
  state.replayBySession[payload.sessionId] = [
    ...(state.replayBySession[payload.sessionId] || []),
    { type: 'transfer_submit', timestamp: Date.now(), destination: payload.destination, amount: payload.amount, memo: payload.memo },
  ].slice(-100);
  writeState(state);

  return {
    status: score.verdict === 'LEGITIMATE' || score.verdict === 'FORGETFUL_USER' ? 'accepted' : 'sandboxed',
    sessionId: payload.sessionId,
    verdict: score.verdict,
    confidence: score.confidence,
    sandbox: score.sandbox,
    message: score.sandbox?.active ? 'Transfer moved into sandbox review.' : 'Transfer accepted for processing.',
  };
}

export async function mockHoneypotHit(source: string, userId: string, sessionId: string) {
  const state = readState();
  const score = scoreSession(getMockUser(userId), { honeypot: true });
  applyScore(state, sessionId, userId, score);
  state.replayBySession[sessionId] = [
    ...(state.replayBySession[sessionId] || []),
    { type: 'honeypot', source, timestamp: Date.now() },
  ].slice(-100);
  writeState(state);
  return { status: 'captured', sessionId, verdict: score.verdict, sandbox: score.sandbox };
}

export async function mockWebAttack(userId: string, sessionId: string, payload: string) {
  const state = readState();
  const score = scoreSession(getMockUser(userId), { memo: payload });
  applyScore(state, sessionId, userId, score);
  state.replayBySession[sessionId] = [
    ...(state.replayBySession[sessionId] || []),
    { type: 'web_attack', payload, timestamp: Date.now() },
  ].slice(-100);
  writeState(state);
  return { status: 'captured', sessionId, verdict: score.verdict, sandbox: score.sandbox };
}

export async function mockCurrentVerdict() {
  const state = readState();
  return {
    sessionId: state.currentSessionId,
    verdict: state.verdict,
    confidence: state.confidence,
    snnScore: state.snnScore,
    lnnClass: state.lnnClass,
    xgbClass: state.xgbClass,
    behavioralDelta: state.behavioralDelta,
    sandbox: state.sandbox,
  };
}

export async function mockUserVerdict(userId: string) {
  const state = readState();
  const user = getMockUser(userId);
  if (!state.currentUserId && user) {
    const score = scoreSession(user, {});
    applyScore(state, state.currentSessionId || `portal-${Date.now().toString(36)}`, user.userId, score);
    writeState(state);
  }
  return {
    sessionId: state.currentSessionId,
    verdict: state.currentUserId === userId ? state.verdict : user?.behaviorProfile === 'risky' ? 'FORGETFUL_USER' : 'LEGITIMATE',
    confidence: state.currentUserId === userId ? state.confidence : 0.82,
    snnScore: state.currentUserId === userId ? state.snnScore : 0.22,
    lnnClass: state.currentUserId === userId ? state.lnnClass : 'LEGITIMATE',
    xgbClass: state.currentUserId === userId ? state.xgbClass : 'LEGITIMATE',
    behavioralDelta: state.currentUserId === userId ? state.behavioralDelta : 0.18,
    sandbox: state.currentUserId === userId ? state.sandbox : null,
    recentVerdicts: state.recentVerdictsByUser[userId] || [],
  };
}

export async function mockSandboxReplay(sessionId: string) {
  const state = readState();
  return {
    session_id: sessionId,
    sandbox_token: state.sandbox?.sandboxToken || `sbx-${sessionId.slice(-8)}`,
    mode: state.sandbox?.mode || 'monitor',
    actions: state.replayBySession[sessionId] || state.eventsBySession[sessionId] || [],
  };
}
