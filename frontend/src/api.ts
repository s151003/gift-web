import type { PriceSnapshot, Transaction, HealthResponse } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export function fetchLatestSnapshots() {
  return fetchJSON<{ data: PriceSnapshot[] }>(`${BASE_URL}/api/snapshots/latest`);
}

export function fetchSnapshots(hours: number, site?: string) {
  const params = new URLSearchParams({ hours: String(hours) });
  if (site) params.set("site", site);
  return fetchJSON<{ data: PriceSnapshot[] }>(`${BASE_URL}/api/snapshots?${params}`);
}

export function fetchTransactions(hours: number, site?: string) {
  const params = new URLSearchParams({ hours: String(hours) });
  if (site) params.set("site", site);
  return fetchJSON<{ data: Transaction[] }>(`${BASE_URL}/api/transactions?${params}`);
}

export function fetchHealth() {
  return fetchJSON<HealthResponse>(`${BASE_URL}/api/health`);
}
