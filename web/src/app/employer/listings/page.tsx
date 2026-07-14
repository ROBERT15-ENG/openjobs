import type { Metadata } from "next";
import Link from "next/link";
import ListingActions from "@/components/employer/ListingActions";
import { getEmployerDashboard } from "@/lib/employer-api";
import { getToken } from "@/lib/session";
import { formatSalary, timeAgo, workTypeLabel } from "@/lib/format";

export const metadata: Metadata = { title: "My Listings" };

type SP = Record<string, string | string[] | undefined>;

export default async function ListingsPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const sp = await searchParams;
  const token = await getToken();
  const dash = await getEmployerDashboard(token!);
  const jobs = dash.my_jobs;

  return (
    <>
      <h1 className="page-title">My Job Listings</h1>
      <p className="page-sub">Manage your published job listings.</p>

      {sp.posted === "1" && (
        <p className="alert alert-success">
          🚀 Job published! It&apos;s live on the board now.
        </p>
      )}
      {sp.updated === "1" && (
        <p className="alert alert-success">Changes saved.</p>
      )}

      {jobs.length === 0 ? (
        <div className="empty-state">
          <div className="emoji">📋</div>
          <h3>No listings yet</h3>
          <p>Post your first job to start receiving applications.</p>
          <p style={{ marginTop: "1.5rem" }}>
            <Link className="btn btn-primary" href="/employer/post">
              + Post a Job
            </Link>
          </p>
        </div>
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Salary</th>
                  <th>Applicants</th>
                  <th>Views</th>
                  <th>Posted</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <strong>
                        <Link
                          href={`/jobs/${job.id}`}
                          style={{ textDecoration: "none", color: "inherit" }}
                        >
                          {job.title}
                        </Link>
                      </strong>
                      <div style={{ color: "var(--color-text-muted)", fontSize: "var(--type-caption)" }}>
                        {job.location} · {workTypeLabel(job.work_type)}
                      </div>
                    </td>
                    <td className="job-salary">{formatSalary(job) ?? "—"}</td>
                    <td>{job.application_count ?? 0}</td>
                    <td>{job.view_count ?? job.views ?? 0}</td>
                    <td>{timeAgo(job.created_at)}</td>
                    <td>
                      <ListingActions
                        jobId={job.id}
                        featured={Boolean(job.is_featured)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}
