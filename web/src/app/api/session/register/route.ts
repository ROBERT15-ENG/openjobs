import { NextResponse } from "next/server";
import { flaskFetch } from "@/lib/api";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  let res: Response;
  try {
    res = await flaskFetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    return NextResponse.json({ error: "API unreachable" }, { status: 502 });
  }

  const data = await res.json().catch(() => ({ error: "Registration failed" }));
  return NextResponse.json(data, { status: res.status });
}
