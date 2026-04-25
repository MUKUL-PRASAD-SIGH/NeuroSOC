import { apiClient, buildWsUrl, getApiBaseUrl } from "../lib/apiClient";
import {
  createMockAlert,
  mockAlerts,
  mockModelStatus,
  mockStats,
} from "../mocks/data";

const MAX_ALERTS = 50;
const DEV_MOCK_STREAM_INTERVAL_MS = 6000;
const SOCKET_RECONNECT_DELAY_MS = 3000;
let preferMockData = false;

function isDevelopmentMockFallbackEnabled() {
  return import.meta.env.DEV;
}

function isNetworkError(error) {
  if (!error) {
    return false;
  }

  if (error.name === "AxiosError") {
    return !error.response;
  }

  if (error instanceof TypeError) {
    return /fetch|network/i.test(error.message);
  }

  return false;
}

async function withMockFallback(loadLiveData, loadMockData) {
  if (preferMockData && isDevelopmentMockFallbackEnabled()) {
    return loadMockData();
  }

  try {
    return await loadLiveData();
  } catch (error) {
    if (isDevelopmentMockFallbackEnabled() && isNetworkError(error)) {
      preferMockData = true;
      return loadMockData();
    }
    throw error;
  }
}

function startMockAlertStream({ onMessage, onStatusChange }) {
  onStatusChange?.("connected");

  const intervalId = window.setInterval(() => {
    onMessage?.(normalizeAlert(createMockAlert()));
  }, DEV_MOCK_STREAM_INTERVAL_MS);

  return () => {
    window.clearInterval(intervalId);
    onStatusChange?.("disconnected");
  };
}

function normalizeAlert(alert) {
  return {
    id: alert.id,
    severity: alert.severity || "medium",
    verdict: alert.verdict || "LEGITIMATE",
    message: alert.message,
    timestamp: alert.timestamp,
    sourceIp: alert.sourceIp || "",
    userId: alert.userId || "unknown-user",
    userName: alert.userName || "Unknown User",
    locationLabel: alert.locationLabel || "Unknown location",
    score: typeof alert.score === "number" ? alert.score : 0,
    dimensions: Array.isArray(alert.dimensions) ? alert.dimensions : [],
    recentVerdicts: Array.isArray(alert.recentVerdicts) ? alert.recentVerdicts : [],
    modelVersion: alert.modelVersion || null,
  };
}

function sortAlerts(alerts) {
  return [...alerts]
    .map(normalizeAlert)
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, MAX_ALERTS);
}

export async function getStats() {
  if (!getApiBaseUrl()) {
    return mockStats;
  }
  return withMockFallback(
    async () => {
      const { data } = await apiClient.get("/api/stats");
      return data;
    },
    () => mockStats
  );
}

export async function getModelVersion() {
  if (!getApiBaseUrl()) {
    return mockModelStatus;
  }
  return withMockFallback(
    async () => {
      const { data } = await apiClient.get("/api/model/version");
      return data;
    },
    () => mockModelStatus
  );
}

export async function getAlerts() {
  if (!getApiBaseUrl()) {
    return sortAlerts(mockAlerts);
  }
  return withMockFallback(
    async () => {
      const { data } = await apiClient.get("/api/alerts");
      return sortAlerts(Array.isArray(data) ? data : []);
    },
    () => sortAlerts(mockAlerts)
  );
}

export function subscribeToAlerts({ onMessage, onStatusChange, onError }) {
  if ((!getApiBaseUrl() && import.meta.env.DEV) || (preferMockData && isDevelopmentMockFallbackEnabled())) {
    return startMockAlertStream({ onMessage, onStatusChange });
  }

  let socket;
  let reconnectTimer;
  let isClosed = false;
  let stopMockStream;

  const switchToMockStream = () => {
    if (isClosed || stopMockStream) {
      return;
    }

    stopMockStream = startMockAlertStream({ onMessage, onStatusChange });
  };

  const connect = () => {
    if (isClosed || stopMockStream) {
      return;
    }

    onStatusChange?.("connecting");

    socket = new WebSocket(buildWsUrl("/ws/alerts"));

    socket.onopen = () => {
      onStatusChange?.("connected");
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const alerts = Array.isArray(payload) ? payload : [payload];
        alerts.map(normalizeAlert).forEach((alert) => onMessage?.(alert));
      } catch (error) {
        onError?.(error);
      }
    };

    socket.onerror = () => {
      const error = new Error("Alert stream connection error");
      if (isDevelopmentMockFallbackEnabled()) {
        preferMockData = true;
        switchToMockStream();
        return;
      }
      onError?.(error);
    };

    socket.onclose = () => {
      if (stopMockStream) {
        return;
      }

      onStatusChange?.("reconnecting");
      if (!isClosed) {
        reconnectTimer = window.setTimeout(connect, SOCKET_RECONNECT_DELAY_MS);
      }
    };
  };

  connect();

  return () => {
    isClosed = true;
    window.clearTimeout(reconnectTimer);
    stopMockStream?.();
    if (socket && socket.readyState < WebSocket.CLOSING) {
      socket.close();
    }
    if (!stopMockStream) {
      onStatusChange?.("disconnected");
    }
  };
}

export function getMockBootstrap() {
  return {
    stats: mockStats,
    model: mockModelStatus,
    alerts: sortAlerts(mockAlerts),
  };
}

export { MAX_ALERTS };
