import type { DashboardPayload } from "./types";

/** Vite 의 base path 를 반영해 정적 JSON 을 fetch 한다. */
export async function loadLatest(): Promise<DashboardPayload> {
  const url = new URL("data/latest.json", new URL(import.meta.env.BASE_URL, window.location.href));
  const resp = await fetch(url.href, { cache: "no-cache" });
  if (!resp.ok) {
    throw new Error(`Failed to load data (${resp.status} ${resp.statusText}). url=${url.href}`);
  }
  return resp.json();
}
