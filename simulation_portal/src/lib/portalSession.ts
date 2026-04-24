export interface PortalAccount {
  balance?: number;
  accountMasked?: string;
}

export interface PortalSandbox {
  active: boolean;
  mode?: string;
  sandboxToken?: string;
  sandboxPath?: string;
}

export interface PortalUserSession {
  sessionId: string;
  userId?: string;
  email?: string;
  displayName?: string;
  authenticated?: boolean;
  verdict?: string;
  confidence?: number;
  account?: PortalAccount;
  sandbox?: PortalSandbox | null;
}

const STORAGE_KEY = 'novatrust.portal.session';

function createSessionId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `portal-${crypto.randomUUID()}`;
  }
  return `portal-${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
}

export function readPortalSession(): PortalUserSession {
  if (typeof window === 'undefined') {
    return { sessionId: createSessionId() };
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      const fresh = { sessionId: createSessionId() };
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(fresh));
      return fresh;
    }

    const parsed = JSON.parse(raw) as Partial<PortalUserSession>;
    if (!parsed.sessionId) {
      parsed.sessionId = createSessionId();
    }
    return parsed as PortalUserSession;
  } catch {
    return { sessionId: createSessionId() };
  }
}

export function writePortalSession(next: Partial<PortalUserSession>): PortalUserSession {
  const current = readPortalSession();
  const merged = {
    ...current,
    ...next,
    sessionId: next.sessionId || current.sessionId || createSessionId(),
  };

  if (typeof window !== 'undefined') {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
  }

  return merged;
}

export function clearPortalSession(): PortalUserSession {
  const fresh = { sessionId: createSessionId() };
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(fresh));
  }
  return fresh;
}

export function setDebugToken(token: string) {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem('debug_token', token);
}
