import { NextResponse } from "next/server";
import { flaskFetch } from "@/lib/api";
import { SESSION_COOKIE, SESSION_MAX_AGE } from "@/lib/session";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  let res: Response;
  try {
    res = await flaskFetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    return NextResponse.json({ error: "API unreachable" }, { status: 502 });
  }

  const data = await res.json().catch(() => ({ error: "Login failed" }));
  if (!res.ok || !data.token) {
    return NextResponse.json(data, { status: res.ok ? 502 : res.status });
  }

  // Token stays server-side: httpOnly cookie, never exposed to page JS.
  const out = NextResponse.json({ success: true, user: data.user });
  out.cookies.set(SESSION_COOKIE, data.token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SESSION_MAX_AGE,
  });
  return out;
}
