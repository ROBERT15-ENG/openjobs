import { Suspense } from "react";
import FilterSidebar from "@/components/FilterSidebar";
import JobCard from "@/components/JobCard";
import Pagination from "@/components/Pagination";
import SearchBar from "@/components/SearchBar";
import { getJobs, getSavedJobIds } from "@/lib/api";
import { getSessionUser } from "@/lib/session";
import type { Job } from "@/lib/types";

type SP = Record<string, string | string[] | undefined>;

function first(v: string | string[] | undefined): string {
  return (Array.isArray(v) ? v[0] : v) ?? "";
}

/** Site-wide stats from the newest 100 jobs — plenty at current scale. */
function computeStats(all: Job[], total: number) {
  const companies = new Set(all.map((j) => j.company)).size;
  const weekAgo = Date.now() - 7 * 24 * 3600 * 1000;
  const newThisWeek = all.filter(
    (j) => new Date(j.created_at).getTime() > weekAgo,
  ).length;
  const remoteFriendly = all.filter(
    (j) => j.work_arrangement === "remote" || j.work_arrangement === "hybrid",
  ).length;
  return { total, companies, newThisWeek, remoteFriendly };
}

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const sp = await searchParams;
  const q = first(sp.q);
  const location = first(sp.location);
  const type = first(sp.type);
  const mode = first(sp.mode);
  const category = first(sp.category);
  const salary = first(sp.salary);
  const page = Math.max(1, parseInt(first(sp.page), 10) || 1);

  const apiParams = new URLSearchParams({ page: String(page), limit: "20" });
  if (q) apiParams.set("q", q);
  if (location) apiParams.set("location", location);
  if (type) apiParams.set("work_type", type);
  if (mode) apiParams.set("work_arrangement", mode);
  if (category) apiParams.set("category", category);
  if (salary) apiParams.set("min_salary", salary);

  const user = await getSessionUser();
  const [data, allData, savedIds] = await Promise.all([
    getJobs(apiParams),
    getJobs(new URLSearchParams({ limit: "100" })),
    user ? getSavedJobIds(user.id) : Promise.resolve([]),
  ]);
  const saved = new Set(savedIds);
  const { jobs, pagination } = data;
  const stats = computeStats(allData.jobs, allData.pagination.total);
  const categories = [
    ...new Set(allData.jobs.map((j) => j.category).filter(Boolean)),
  ].sort() as string[];
  const filtered = Boolean(q || location || type || mode || category || salary);

  return (
    <>
      <section className="hero">
        <h1>
          Find Your Next
          <br />
          <span className="gradient">Dream Job</span>
        </h1>
        <p>
          {stats.total} open roles from {stats.companies}{" "}
          {stats.companies === 1 ? "company" : "companies"} across Australia.
          Updated daily. Powered by AI matching.
        </p>
        <Suspense fallback={null}>
          <SearchBar />
        </Suspense>
      </section>

      <section className="stats-bar" aria-label="Platform stats">
        <div className="stat">
          <div className="stat-val">{stats.total}</div>
          <div className="stat-lbl">Active Jobs</div>
        </div>
        <div className="stat">
          <div className="stat-val">{stats.companies}</div>
          <div className="stat-lbl">Companies</div>
        </div>
        <div className="stat">
          <div className="stat-val">{stats.newThisWeek}</div>
          <div className="stat-lbl">New This Week</div>
        </div>
        <div className="stat">
          <div className="stat-val">{stats.remoteFriendly}</div>
          <div className="stat-lbl">Remote-Friendly</div>
        </div>
      </section>

      <div className="main-layout">
        <Suspense fallback={null}>
          <FilterSidebar categories={categories} />
        </Suspense>

        <section aria-label="Job listings">
          <div className="listings-header">
            <span className="results-count">
              <strong>{pagination.total}</strong>{" "}
              {pagination.total === 1 ? "job" : "jobs"} found
              {filtered ? " with your filters" : ""}
            </span>
          </div>

          {jobs.length === 0 ? (
            <div className="empty-state">
              <div className="emoji">🔍</div>
              <h3>No roles match those filters</h3>
              <p>Try widening the search — fewer filters, broader keywords.</p>
            </div>
          ) : (
            <ul className="jobs-list">
              {jobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  canSave={Boolean(user)}
                  saved={saved.has(job.id)}
                />
              ))}
            </ul>
          )}

          <Pagination
            page={pagination.page}
            pages={pagination.pages}
            params={{
              ...(q && { q }),
              ...(location && { location }),
              ...(type && { type }),
              ...(mode && { mode }),
              ...(category && { category }),
              ...(salary && { salary }),
            }}
          />
        </section>
      </div>
    </>
  );
}
