import { apiClient, buildWsUrl, getApiBaseUrl } from "../lib/apiClient";
import {
  createMockAlert,
  mockAlerts,
  mockModelStatus,
  mockStats,
} from "../mocks/data";

const MAX_ALERTS = 50;
const DEV_MOCK_STREAM_INTERVAL_MS = 6000;

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
  const { data } = await apiClient.get("/api/stats");
  return data;
}

export async function getModelVersion() {
  const { data } = await apiClient.get("/api/model/version");
  return data;
}

export async function getAlerts() {
  const { data } = await apiClient.get("/api/alerts");
  return sortAlerts(Array.isArray(data) ? data : []);
}

export function subscribeToAlerts({ onMessage, onStatusChange, onError }) {
  if (!getApiBaseUrl() && import.meta.env.DEV) {
    onStatusChange?.("connected");

    const intervalId = window.setInterval(() => {
      onMessage?.(normalizeAlert(createMockAlert()));
    }, DEV_MOCK_STREAM_INTERVAL_MS);

    return () => {
      window.clearInterval(intervalId);
      onStatusChange?.("disconnected");
    };
  }

  let socket;
  let reconnectTimer;
  let isClosed = false;

  const connect = () => {
    if (isClosed) {
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
      onError?.(new Error("Alert stream connection error"));
    };

    socket.onclose = () => {
      onStatusChange?.("reconnecting");
      if (!isClosed) {
        reconnectTimer = window.setTimeout(connect, 3000);
      }
    };
  };

  connect();

  return () => {
    isClosed = true;
    window.clearTimeout(reconnectTimer);
    if (socket && socket.readyState < WebSocket.CLOSING) {
      socket.close();
    }
    onStatusChange?.("disconnected");
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
