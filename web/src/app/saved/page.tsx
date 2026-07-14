import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import JobCard from "@/components/JobCard";
import { getSavedJobs } from "@/lib/api";
import { getSessionUser } from "@/lib/session";

export const metadata: Metadata = { title: "Saved jobs" };

export default async function SavedPage() {
  const user = await getSessionUser();
  if (!user) redirect("/login");

  const jobs = await getSavedJobs(user.id);

  return (
    <div className="page-wrap">
      <div className="listings-header">
        <h1>Saved jobs</h1>
        <span className="results-count">
          <strong>{jobs.length}</strong> {jobs.length === 1 ? "job" : "jobs"}
        </span>
      </div>

      {jobs.length === 0 ? (
        <div className="empty-state">
          <div className="emoji">🔖</div>
          <h3>Nothing saved yet</h3>
          <p>Hit the bookmark on any job to keep it here.</p>
          <p style={{ marginTop: "1.5rem" }}>
            <Link className="btn btn-primary" href="/">
              Browse jobs
            </Link>
          </p>
        </div>
      ) : (
        <ul className="jobs-list">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} canSave saved />
          ))}
        </ul>
      )}
    </div>
  );
}
