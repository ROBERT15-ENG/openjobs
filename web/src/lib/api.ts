import type { Job, JobsResponse } from "./types";

/** Server-side only — the browser never talks to Flask directly. */
export const API_BASE = process.env.API_BASE ?? "http://127.0.0.1:5700";

export function flaskFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${API_BASE}${path}`, { cache: "no-store", ...init });
}

export async function getJobs(params: URLSearchParams): Promise<JobsResponse> {
  const res = await flaskFetch(`/api/jobs?${params.toString()}`);
  if (!res.ok) throw new Error(`GET /api/jobs failed: ${res.status}`);
  return res.json();
}

export async function getJob(id: number): Promise<Job | null> {
  const res = await flaskFetch(`/api/jobs/${id}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`GET /api/jobs/${id} failed: ${res.status}`);
  return res.json();
}

/** NOTE: the Flask endpoint trusts a client-supplied user_id (no auth) —
 *  known backend issue. We only ever call it server-side with the id from
 *  the verified session cookie. */
export async function getSavedJobs(userId: number): Promise<Job[]> {
  const res = await flaskFetch(`/api/saved_jobs?user_id=${userId}`);
  if (!res.ok) throw new Error(`GET /api/saved_jobs failed: ${res.status}`);
  return res.json();
}

export async function getSavedJobIds(userId: number): Promise<number[]> {
  const jobs = await getSavedJobs(userId);
  return jobs.map((j) => j.id);
}

export async function setJobSaved(userId: number, jobId: number, save: boolean): Promise<boolean> {
  const res = await flaskFetch("/api/saved_jobs", {
    method: save ? "POST" : "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, job_id: jobId }),
  });
  return res.ok;
}
