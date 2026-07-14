import { NextResponse } from "next/server";
import { getSavedJobs, setJobSaved } from "@/lib/api";
import { getSessionUser } from "@/lib/session";

export async function GET() {
  const user = await getSessionUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const jobs = await getSavedJobs(user.id);
  return NextResponse.json({ jobs });
}

export async function POST(req: Request) {
  const user = await getSessionUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json().catch(() => ({}));
  const jobId = Number(body.job_id);
  const save = Boolean(body.save);
  if (!Number.isInteger(jobId) || jobId <= 0) {
    return NextResponse.json({ error: "Invalid job_id" }, { status: 400 });
  }

  const ok = await setJobSaved(user.id, jobId, save);
  if (!ok) return NextResponse.json({ error: "Upstream error" }, { status: 502 });
  return NextResponse.json({ success: true, saved: save });
}
