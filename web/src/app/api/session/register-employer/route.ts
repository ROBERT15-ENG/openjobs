import { NextResponse } from "next/server";
import { flaskFetch } from "@/lib/api";
import { SESSION_COOKIE, SESSION_MAX_AGE } from "@/lib/session";

/** Registers an employer, then logs straight in. We deliberately discard the
 *  token register-employer returns — it's a legacy base64 pseudo-JWT that
 *  /api/auth/me rejects — and get a real one from /api/auth/login. */
export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));

  let reg: Response;
  try {
    reg = await flaskFetch("/api/auth/register-employer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    return NextResponse.json({ error: "API unreachable" }, { status: 502 });
  }
  const regData = await reg.json().catch(() => ({ error: "Registration failed" }));
  if (!reg.ok) return NextResponse.json(regData, { status: reg.status });

  const login = await flaskFetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: body.email, password: body.password }),
  });
  const loginData = await login.json().catch(() => ({}));
  if (!login.ok || !loginData.token) {
    // Account exists but auto-login failed — let the user log in manually.
    return NextResponse.json({ success: true, autoLogin: false }, { status: 201 });
  }

  const out = NextResponse.json(
    { success: true, autoLogin: true, user: loginData.user },
    { status: 201 },
  );
  out.cookies.set(SESSION_COOKIE, loginData.token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SESSION_MAX_AGE,
  });
  return out;
}
