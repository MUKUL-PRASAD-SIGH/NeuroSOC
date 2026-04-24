import axios from "axios";

const API_BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export const apiClient = axios.create({
  baseURL: API_BASE_URL || undefined,
  headers: {
    "Content-Type": "application/json",
  },
});

export function getApiBaseUrl() {
  return API_BASE_URL;
}

export function buildWsUrl(path) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (!API_BASE_URL) {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}${normalizedPath}`;
  }

  const httpUrl = new URL(API_BASE_URL, window.location.origin);
  httpUrl.protocol = httpUrl.protocol === "https:" ? "wss:" : "ws:";
  httpUrl.pathname = normalizedPath;
  httpUrl.search = "";
  httpUrl.hash = "";

  return httpUrl.toString();
}
