import { cookies } from "next/headers";
import { flaskFetch } from "./api";
import type { SessionUser } from "./types";

export const SESSION_COOKIE = "oj_session";

/** Matches the Flask JWT lifetime (7 days). */
export const SESSION_MAX_AGE = 60 * 60 * 24 * 7;

export async function getToken(): Promise<string | null> {
  const jar = await cookies();
  return jar.get(SESSION_COOKIE)?.value ?? null;
}

/** Resolves the session cookie to a user via Flask /api/auth/me.
 *  Returns null for missing, expired, or revoked tokens. */
export async function getSessionUser(): Promise<SessionUser | null> {
  const token = await getToken();
  if (!token) return null;
  try {
    const res = await flaskFetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { user?: SessionUser };
    return data.user ?? null;
  } catch {
    return null;
  }
}
