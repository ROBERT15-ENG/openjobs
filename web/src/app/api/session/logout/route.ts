import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { flaskFetch } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/session";

export async function POST(req: Request) {
  const jar = await cookies();
  const token = jar.get(SESSION_COOKIE)?.value;

  if (token) {
    // Best effort — revoke on the Flask blocklist too.
    try {
      await flaskFetch("/api/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // Cookie removal below still logs the browser out.
    }
  }

  // Plain-form POST from the header → redirect back home.
  const out = NextResponse.redirect(new URL("/", req.url), 303);
  out.cookies.set(SESSION_COOKIE, "", { httpOnly: true, path: "/", maxAge: 0 });
  return out;
}
