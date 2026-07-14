"use client";

import { useMemo, useState } from "react";
import type { EmployerApplication } from "@/lib/types";
import { timeAgo } from "@/lib/format";
import StatusBadge from "./StatusBadge";

const FILTERS = ["all", "pending", "reviewing", "interview", "offer", "hired", "rejected"];
const SETTABLE = ["pending", "reviewing", "interview", "offer", "rejected"];

export default function ApplicationsTable({
  initial,
}: {
  initial: EmployerApplication[];
}) {
  const [apps, setApps] = useState(initial);
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState<"applied_at" | "applicant_name">("applied_at");
  const [busyId, setBusyId] = useState<number | null>(null);

  const visible = useMemo(() => {
    const filtered =
      filter === "all" ? apps : apps.filter((a) => a.status === filter);
    return [...filtered].sort((a, b) =>
      sort === "applied_at"
        ? b.applied_at.localeCompare(a.applied_at)
        : (a.applicant_name ?? "").localeCompare(b.applicant_name ?? ""),
    );
  }, [apps, filter, sort]);

  async function setStatus(id: number, status: string) {
    const prev = apps;
    setApps((cur) => cur.map((a) => (a.id === id ? { ...a, status } : a)));
    setBusyId(id);
    try {
      const res = await fetch(`/api/proxy/applications/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) setApps(prev);
    } catch {
      setApps(prev);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <div className="chip-filter-row">
        <span className="label">Filter</span>
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            className={`city-chip${filter === f ? " active" : ""}`}
            onClick={() => setFilter(f)}
          >
            {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
        <span className="label" style={{ marginLeft: "0.5rem" }}>
          Sort
        </span>
        <button
          type="button"
          className={`city-chip${sort === "applied_at" ? " active" : ""}`}
          onClick={() => setSort("applied_at")}
        >
          Newest
        </button>
        <button
          type="button"
          className={`city-chip${sort === "applicant_name" ? " active" : ""}`}
          onClick={() => setSort("applicant_name")}
        >
          Name A→Z
        </button>
        <span
          style={{
            marginLeft: "auto",
            fontSize: "var(--type-caption)",
            color: "var(--color-text-muted)",
          }}
        >
          {visible.length} of {apps.length}
        </span>
      </div>

      {visible.length === 0 ? (
        <div className="empty-state">
          <div className="emoji">📥</div>
          <h3>No applications{filter !== "all" ? ` in “${filter}”` : " yet"}</h3>
          <p>Try a different filter, or wait for new applicants.</p>
        </div>
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Applicant</th>
                  <th>Job</th>
                  <th>Status</th>
                  <th>Applied</th>
                  <th>Set status</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <strong>{a.applicant_name ?? "Unknown"}</strong>
                      <div
                        style={{
                          color: "var(--color-text-muted)",
                          fontSize: "var(--type-caption)",
                        }}
                      >
                        {a.applicant_email ?? "—"}
                      </div>
                    </td>
                    <td>{a.job_title}</td>
                    <td>
                      <StatusBadge status={a.status} />
                    </td>
                    <td>{timeAgo(a.applied_at)}</td>
                    <td>
                      <select
                        className="status-select"
                        value={SETTABLE.includes(a.status) ? a.status : ""}
                        disabled={busyId === a.id}
                        onChange={(e) => {
                          if (e.target.value) setStatus(a.id, e.target.value);
                        }}
                        aria-label={`Status for ${a.applicant_name ?? "applicant"}`}
                      >
                        {!SETTABLE.includes(a.status) && (
                          <option value="">{a.status}…</option>
                        )}
                        {SETTABLE.map((s) => (
                          <option key={s} value={s}>
                            {s.charAt(0).toUpperCase() + s.slice(1)}
                          </option>
                        ))}
                      </select>
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
