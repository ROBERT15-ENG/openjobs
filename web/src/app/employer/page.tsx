import type { Metadata } from "next";
import Link from "next/link";
import StatusBadge from "@/components/employer/StatusBadge";
import {
  ChartIcon,
  EyeIcon,
  InboxIcon,
  UsersIcon,
} from "@/components/icons";
import {
  getEmployerApplications,
  getEmployerDashboard,
} from "@/lib/employer-api";
import { getSessionUser, getToken } from "@/lib/session";
import { timeAgo } from "@/lib/format";

export const metadata: Metadata = { title: "Overview" };

export default async function EmployerOverview() {
  const [token, user] = await Promise.all([getToken(), getSessionUser()]);
  const [dash, applications] = await Promise.all([
    getEmployerDashboard(token!),
    getEmployerApplications(token!),
  ]);

  // The dashboard's recent_applications rows lack applicant names —
  // join them in from the applications endpoint.
  const nameById = new Map(
    applications.map((a) => [a.id, a.applicant_name ?? "Unknown"]),
  );
  const recent = dash.recent_applications.slice(0, 8);

  const stats = [
    { icon: ChartIcon, value: dash.stats.active_jobs, label: "Active Jobs" },
    { icon: UsersIcon, value: dash.stats.total_applicants, label: "Total Applicants" },
    { icon: EyeIcon, value: dash.stats.job_views, label: "Job Views" },
    { icon: InboxIcon, value: dash.stats.pending, label: "Pending Review" },
  ];

  return (
    <>
      <h1 className="page-title">Dashboard Overview</h1>
      <p className="page-sub">Welcome back, {user?.name}!</p>

      <div className="stats-grid">
        {stats.map(({ icon: Icon, value, label }) => (
          <div key={label} className="stat-card">
            <div className="stat-icon">
              <Icon />
            </div>
            <div className="stat-value">{value}</div>
            <div className="stat-label">{label}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title">Recent Applications</div>
          <Link className="btn btn-ghost" href="/employer/applications">
            View All →
          </Link>
        </div>
        {recent.length === 0 ? (
          <div className="empty-state">
            <div className="emoji">📥</div>
            <h3>No applications yet</h3>
            <p>Applications to your listings will show up here.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Applicant</th>
                  <th>Job</th>
                  <th>Status</th>
                  <th>Applied</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <strong>{nameById.get(a.id) ?? "Unknown"}</strong>
                    </td>
                    <td>{a.job_title}</td>
                    <td>
                      <StatusBadge status={a.status} />
                    </td>
                    <td>{timeAgo(a.applied_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title">Quick Actions</div>
        </div>
        <div className="form-actions">
          <Link className="btn btn-primary" href="/employer/post">
            + Post New Job
          </Link>
          <Link className="btn btn-ghost" href="/employer/listings">
            Manage Listings
          </Link>
          <Link className="btn btn-ghost" href="/employer/pipeline">
            Open Pipeline
          </Link>
        </div>
      </div>
    </>
  );
}
