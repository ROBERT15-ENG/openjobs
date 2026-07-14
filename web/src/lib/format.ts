import type { Job } from "./types";

export const WORK_TYPE_LABELS: Record<string, string> = {
  full_time: "Full-time",
  part_time: "Part-time",
  contract: "Contract",
  internship: "Internship",
};

export const ARRANGEMENT_LABELS: Record<string, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  on_site: "On-site",
};

/** The legacy employer form posted `onsite` (no underscore) — tolerate both. */
export const ARRANGEMENT_ALIASES: Record<string, string> = {
  onsite: "on_site",
};

/** Legacy badge variant classes (globals.css) */
export const WORK_TYPE_BADGE: Record<string, string> = {
  full_time: "badge-fulltime",
  part_time: "badge-parttime",
  contract: "badge-contract",
  internship: "badge-internship",
};

export const ARRANGEMENT_BADGE: Record<string, string> = {
  remote: "badge-remote",
  hybrid: "badge-hybrid",
  on_site: "badge-onsite",
};

export function workTypeLabel(value: string | null): string | null {
  if (!value) return null;
  return WORK_TYPE_LABELS[value] ?? value.replace(/_/g, " ");
}

export function arrangementLabel(value: string | null): string | null {
  if (!value) return null;
  const canonical = ARRANGEMENT_ALIASES[value] ?? value;
  return ARRANGEMENT_LABELS[canonical] ?? canonical.replace(/_/g, " ");
}

export function arrangementBadgeClass(value: string | null): string {
  if (!value) return "";
  const canonical = ARRANGEMENT_ALIASES[value] ?? value;
  return ARRANGEMENT_BADGE[canonical] ?? "";
}

function compact(n: number): string {
  return n >= 1000 ? `${Math.round(n / 1000)}k` : String(n);
}

/** The list endpoint pre-formats `salary`; other endpoints return the raw row,
 *  so fall back to building it from min/max. */
export function formatSalary(job: Job): string | null {
  if (job.salary) return job.salary;
  const cur = job.salary_currency ?? "AUD";
  if (job.salary_min && job.salary_max)
    return `${cur} ${compact(job.salary_min)} – ${compact(job.salary_max)}`;
  if (job.salary_min) return `${cur} ${compact(job.salary_min)}+`;
  if (job.salary_max) return `up to ${cur} ${compact(job.salary_max)}`;
  return null;
}

export function skillList(job: Job): string[] {
  if (!job.skills) return [];
  return job.skills
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const mins = Math.max(0, Math.floor((Date.now() - then) / 60000));
  if (mins < 60) return mins <= 1 ? "just now" : `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `${weeks}w ago`;
  return new Date(iso).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
}
