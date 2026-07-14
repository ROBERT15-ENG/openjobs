import { NextResponse } from "next/server";
import { flaskFetch } from "@/lib/api";
import { getToken } from "@/lib/session";

/** Authenticated pass-through for client-side mutations. The browser never
 *  holds the JWT, so authed writes come here and get the Bearer attached
 *  from the httpOnly cookie. Only allowlisted method+path pairs forward —
 *  this must not become an open proxy. */
const ALLOW: Record<string, RegExp[]> = {
  POST: [/^jobs$/, /^jobs\/\d+\/feature$/, /^kanban\/\d+\/move$/],
  PATCH: [/^jobs\/\d+$/, /^applications\/\d+$/, /^user\/profile$/],
  PUT: [/^employer\/calendly$/],
  DELETE: [/^jobs\/\d+$/],
};

async function forward(
  req: Request,
  params: Promise<{ path: string[] }>,
): Promise<NextResponse> {
  const token = await getToken();
  if (!token) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { path } = await params;
  const joined = path.join("/");
  const allowed = (ALLOW[req.method] ?? []).some((re) => re.test(joined));
  if (!allowed) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  let res: Response;
  try {
    res = await flaskFetch(`/api/${joined}`, {
      method: req.method,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: req.method === "DELETE" ? undefined : await req.text(),
    });
  } catch {
    return NextResponse.json({ error: "API unreachable" }, { status: 502 });
  }

  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function POST(req: Request, { params }: Ctx) {
  return forward(req, params);
}

export async function PATCH(req: Request, { params }: Ctx) {
  return forward(req, params);
}

export async function PUT(req: Request, { params }: Ctx) {
  return forward(req, params);
}

export async function DELETE(req: Request, { params }: Ctx) {
  return forward(req, params);
}
