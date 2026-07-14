import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import SaveButton from "@/components/SaveButton";
import {
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  UsersIcon,
} from "@/components/icons";
import { getJob, getSavedJobIds } from "@/lib/api";
import { getSessionUser } from "@/lib/session";
import {
  WORK_TYPE_BADGE,
  arrangementBadgeClass,
  arrangementLabel,
  formatSalary,
  skillList,
  timeAgo,
  workTypeLabel,
} from "@/lib/format";

const LEGACY_BASE =
  process.env.NEXT_PUBLIC_LEGACY_BASE ?? "http://localhost:5700";

type Params = Promise<{ id: string }>;

export async function generateMetadata({
  params,
}: {
  params: Params;
}): Promise<Metadata> {
  const { id } = await params;
  const job = Number.isInteger(Number(id)) ? await getJob(Number(id)) : null;
  if (!job) return { title: "Job not found" };
  return {
    title: `${job.title} at ${job.company}`,
    description: job.description.slice(0, 160),
  };
}

export default async function JobPage({ params }: { params: Params }) {
  const { id } = await params;
  const jobId = Number(id);
  if (!Number.isInteger(jobId) || jobId <= 0) notFound();

  const [job, user] = await Promise.all([getJob(jobId), getSessionUser()]);
  if (!job) notFound();

  const saved = user ? (await getSavedJobIds(user.id)).includes(jobId) : false;
  const salary = formatSalary(job);
  const skills = skillList(job);
  const workType = workTypeLabel(job.work_type);
  const arrangement = arrangementLabel(job.work_arrangement);

  return (
    <article className="job-detail">
      <Link href="/" className="back-link">
        ← All jobs
      </Link>

      <div className="detail-head">
        <div className="detail-logo" aria-hidden>
          {job.company?.charAt(0).toUpperCase() || "•"}
        </div>
        <div>
          <h1>{job.title}</h1>
          <p className="detail-company">
            <strong>{job.company}</strong>
            {job.location ? <> · {job.location}</> : null}
          </p>
        </div>
      </div>

      <div className="badges">
        {job.is_featured ? (
          <span className="badge badge-featured">★ Featured</span>
        ) : null}
        {arrangement && (
          <span className={`badge ${arrangementBadgeClass(job.work_arrangement)}`}>
            {arrangement}
          </span>
        )}
        {workType && (
          <span
            className={`badge ${WORK_TYPE_BADGE[job.work_type ?? ""] ?? ""}`}
          >
            {workType}
          </span>
        )}
        {job.category && <span className="badge">{job.category}</span>}
      </div>

      <div className="detail-actions">
        {/* Apply stays on the legacy page until the flow is migrated */}
        <a
          className="btn btn-primary btn-lg"
          href={`${LEGACY_BASE}/job?id=${job.id}`}
        >
          Apply for this role
        </a>
        {user ? (
          <SaveButton jobId={job.id} initialSaved={saved} />
        ) : (
          <Link className="btn btn-ghost" href="/login">
            Log in to save
          </Link>
        )}
        {salary && <span className="job-salary">{salary}</span>}
      </div>

      <div className="detail-card">
        <div className="detail-meta">
          {job.location && (
            <span className="job-meta-item">
              <MapPinIcon size={15} /> {job.location}
            </span>
          )}
          <span className="job-meta-item">
            <ClockIcon size={15} /> Posted {timeAgo(job.created_at)}
          </span>
          <span className="job-meta-item">
            <UsersIcon size={15} />{" "}
            {job.application_count === 1
              ? "1 applicant"
              : `${job.application_count} applicants`}
          </span>
          {job.expires_at && (
            <span className="job-meta-item">
              <CalendarIcon size={15} /> Closes{" "}
              {new Date(job.expires_at).toLocaleDateString("en-AU", {
                day: "numeric",
                month: "short",
                year: "numeric",
              })}
            </span>
          )}
        </div>

        <section className="detail-section">
          <h2>About this role</h2>
          <div className="job-desc">{job.description}</div>
        </section>

        {skills.length > 0 && (
          <section className="detail-section">
            <h2>Skills</h2>
            <div className="detail-skills">
              {skills.map((s) => (
                <span key={s} className="skill-tag">
                  {s}
                </span>
              ))}
            </div>
          </section>
        )}
      </div>
    </article>
  );
}
