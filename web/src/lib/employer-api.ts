import { flaskFetch } from "./api";
import type {
  EmployerApplication,
  EmployerDashboard,
  KanbanBoard,
} from "./types";

/** Server-side fetchers for the employer surface. All require the
 *  session Bearer token — Flask enforces ownership per employer_id. */

function authed(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export async function getEmployerDashboard(
  token: string,
): Promise<EmployerDashboard> {
  const res = await flaskFetch("/api/employer/dashboard", {
    headers: authed(token),
  });
  if (!res.ok) throw new Error(`GET /api/employer/dashboard ${res.status}`);
  return res.json();
}

export async function getEmployerApplications(
  token: string,
): Promise<EmployerApplication[]> {
  const res = await flaskFetch("/api/employer/applications", {
    headers: authed(token),
  });
  if (!res.ok) throw new Error(`GET /api/employer/applications ${res.status}`);
  const data = await res.json();
  return data.applications ?? [];
}

export async function getKanban(
  token: string,
  jobId: number,
): Promise<KanbanBoard | null> {
  const res = await flaskFetch(`/api/kanban/${jobId}`, {
    headers: authed(token),
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`GET /api/kanban/${jobId} ${res.status}`);
  const data = await res.json();
  return data.board ?? null;
}
