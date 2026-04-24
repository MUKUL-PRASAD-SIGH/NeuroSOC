import { http, HttpResponse } from "msw";
import {
  createMockAlert,
  mockAlerts as seededAlerts,
  mockModelStatus,
  mockStats,
} from "./data";

let alertCache = [...seededAlerts];

function buildStats(alerts) {
  const hackerDetections = alerts.filter((alert) => alert.verdict === "HACKER").length;
  return {
    ...mockStats,
    hackerDetections,
    liveAlerts: alerts.length,
  };
}

export const handlers = [
  http.get("/api/alerts", async () => {
    if (Math.random() > 0.55) {
      alertCache = [createMockAlert(), ...alertCache].slice(0, 50);
    }

    return HttpResponse.json(alertCache);
  }),

  http.get("/api/stats", async () => {
    return HttpResponse.json(buildStats(alertCache));
  }),

  http.get("/api/model/version", async () => {
    return HttpResponse.json(mockModelStatus);
  }),
];
