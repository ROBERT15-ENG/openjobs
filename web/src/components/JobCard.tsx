import Link from "next/link";
import type { Job } from "@/lib/types";
import {
  WORK_TYPE_BADGE,
  arrangementBadgeClass,
  arrangementLabel,
  formatSalary,
  skillList,
  timeAgo,
  workTypeLabel,
} from "@/lib/format";
import { ClockIcon, MapPinIcon, UsersIcon } from "./icons";
import SaveButton from "./SaveButton";

export default function JobCard({
  job,
  canSave,
  saved,
}: {
  job: Job;
  canSave: boolean;
  saved: boolean;
}) {
  const salary = formatSalary(job);
  const skills = skillList(job).slice(0, 6);
  const workType = workTypeLabel(job.work_type);
  const arrangement = arrangementLabel(job.work_arrangement);

  return (
    <li>
      <article className="job-card">
        <div className="job-logo" aria-hidden>
          {job.company?.charAt(0).toUpperCase() || "•"}
        </div>

        <div className="job-content">
          <div className="job-top">
            <div>
              <h3 className="job-title">
                <Link href={`/jobs/${job.id}`}>{job.title}</Link>
              </h3>
              <p className="job-company">
                {job.company}
                {job.location ? <> · {job.location}</> : null}
              </p>
            </div>
            <div className="job-actions">
              {canSave && <SaveButton jobId={job.id} initialSaved={saved} />}
              <Link className="btn-apply" href={`/jobs/${job.id}`}>
                Apply
              </Link>
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
          </div>

          {skills.length > 0 && (
            <div className="job-skills">
              {skills.map((s) => (
                <span key={s} className="skill-tag">
                  {s}
                </span>
              ))}
            </div>
          )}

          {job.description && <p className="job-summary">{job.description}</p>}

          <div className="job-footer">
            <div className="job-meta">
              {job.location && (
                <span className="job-meta-item">
                  <MapPinIcon /> {job.location}
                </span>
              )}
              <span className="job-meta-item">
                <ClockIcon /> {timeAgo(job.created_at)}
              </span>
              <span className="job-meta-item">
                <UsersIcon />{" "}
                {job.application_count === 1
                  ? "1 applied"
                  : `${job.application_count} applied`}
              </span>
            </div>
            {salary && <span className="job-salary">{salary}</span>}
          </div>
        </div>
      </article>
    </li>
  );
}
