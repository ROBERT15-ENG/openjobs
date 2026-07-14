"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import type { Job } from "@/lib/types";

const CATEGORIES = [
  "Software Development",
  "Engineering",
  "Design",
  "DevOps / Sysadmin",
  "Fintech",
  "Technology",
  "Sales",
  "Marketing",
  "Data Science",
  "Data",
  "Product",
  "General",
];

type Values = {
  title: string;
  company: string;
  location: string;
  category: string;
  work_type: string;
  work_arrangement: string;
  salary_min: string;
  salary_max: string;
  description: string;
  skills: string;
};

function fromJob(job?: Job | null, defaultCompany?: string): Values {
  return {
    title: job?.title ?? "",
    company: job?.company ?? defaultCompany ?? "",
    location: job?.location ?? "",
    category: job?.category ?? "",
    work_type: job?.work_type ?? "full_time",
    work_arrangement: job?.work_arrangement ?? "on_site",
    salary_min: job?.salary_min ? String(job.salary_min) : "",
    salary_max: job?.salary_max ? String(job.salary_max) : "",
    description: job?.description ?? "",
    skills: job?.skills ?? "",
  };
}

export default function JobForm({
  job,
  defaultCompany,
}: {
  job?: Job | null;
  defaultCompany?: string;
}) {
  const router = useRouter();
  const editing = Boolean(job);
  const [v, setV] = useState<Values>(() => fromJob(job, defaultCompany));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function set<K extends keyof Values>(key: K, value: string) {
    setV((prev) => ({ ...prev, [key]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const body = {
        title: v.title.trim(),
        company: v.company.trim(),
        location: v.location.trim(),
        category: v.category || "General",
        work_type: v.work_type,
        work_arrangement: v.work_arrangement,
        salary_min: v.salary_min ? Number(v.salary_min) : null,
        salary_max: v.salary_max ? Number(v.salary_max) : null,
        description: v.description.trim(),
        skills: v.skills
          .split(",")
          .map((s) => s.trim().toLowerCase())
          .filter(Boolean)
          .join(","),
      };
      const res = await fetch(
        editing ? `/api/proxy/jobs/${job!.id}` : "/api/proxy/jobs",
        {
          method: editing ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.error ?? "Something went wrong — try again.");
        return;
      }
      router.push(`/employer/listings?${editing ? "updated" : "posted"}=1`);
      router.refresh();
    } catch {
      setError("Could not reach the server — is the API running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card" onSubmit={onSubmit}>
      <div className="card-title" style={{ marginBottom: "1.25rem" }}>
        Job Details
      </div>
      {error && <p className="alert alert-error">{error}</p>}
      <div className="form-grid">
        <div className="form-group">
          <label className="form-label" htmlFor="jf-title">
            Job Title *
          </label>
          <input
            id="jf-title"
            className="form-input"
            placeholder="e.g. Senior Python Engineer"
            required
            value={v.title}
            onChange={(e) => set("title", e.target.value)}
          />
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="jf-company">
            Company Name *
          </label>
          <input
            id="jf-company"
            className="form-input"
            placeholder="Your company name"
            required
            value={v.company}
            onChange={(e) => set("company", e.target.value)}
          />
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="jf-location">
            Location *
          </label>
          <input
            id="jf-location"
            className="form-input"
            placeholder="e.g. Sydney, NSW or Remote"
            required
            value={v.location}
            onChange={(e) => set("location", e.target.value)}
          />
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="jf-category">
            Category *
          </label>
          <select
            id="jf-category"
            className="form-select"
            required
            value={v.category}
            onChange={(e) => set("category", e.target.value)}
          >
            <option value="">Select category…</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="jf-worktype">
            Work Type *
          </label>
          <select
            id="jf-worktype"
            className="form-select"
            value={v.work_type}
            onChange={(e) => set("work_type", e.target.value)}
          >
            <option value="full_time">Full-time</option>
            <option value="part_time">Part-time</option>
            <option value="contract">Contract</option>
            <option value="internship">Internship</option>
          </select>
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="jf-arrangement">
            Work Arrangement
          </label>
          <select
            id="jf-arrangement"
            className="form-select"
            value={v.work_arrangement}
            onChange={(e) => set("work_arrangement", e.target.value)}
          >
            <option value="on_site">On-site</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
          </select>
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="jf-salmin">
            Salary Min (AUD)
          </label>
          <input
            id="jf-salmin"
            className="form-input"
            type="number"
            min={0}
            placeholder="80000"
            value={v.salary_min}
            onChange={(e) => set("salary_min", e.target.value)}
          />
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="jf-salmax">
            Salary Max (AUD)
          </label>
          <input
            id="jf-salmax"
            className="form-input"
            type="number"
            min={0}
            placeholder="120000"
            value={v.salary_max}
            onChange={(e) => set("salary_max", e.target.value)}
          />
        </div>
        <div className="form-group full">
          <label className="form-label" htmlFor="jf-desc">
            Job Description *
          </label>
          <textarea
            id="jf-desc"
            className="form-textarea"
            placeholder="Describe the role, responsibilities, requirements, and what makes your company great…"
            required
            value={v.description}
            onChange={(e) => set("description", e.target.value)}
          />
        </div>
        <div className="form-group full">
          <label className="form-label" htmlFor="jf-skills">
            Skills (comma-separated)
          </label>
          <input
            id="jf-skills"
            className="form-input"
            placeholder="e.g. Python, JavaScript, React, AWS, Docker"
            value={v.skills}
            onChange={(e) => set("skills", e.target.value)}
          />
        </div>
        <div className="form-group full form-actions">
          <button type="submit" className="btn btn-primary btn-lg" disabled={busy}>
            {busy
              ? editing
                ? "Saving…"
                : "Publishing…"
              : editing
                ? "Save Changes"
                : "Publish Job →"}
          </button>
        </div>
      </div>
    </form>
  );
}
