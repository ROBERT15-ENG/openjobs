"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { ARRANGEMENT_LABELS, WORK_TYPE_LABELS } from "@/lib/format";

const CITIES = ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"];

const SALARY_STEPS: Array<{ value: string; label: string }> = [
  { value: "", label: "Any" },
  { value: "60000", label: "AUD 60k+" },
  { value: "80000", label: "AUD 80k+" },
  { value: "100000", label: "AUD 100k+" },
  { value: "120000", label: "AUD 120k+" },
  { value: "140000", label: "AUD 140k+" },
];

function parseMulti(value: string | null): Set<string> {
  return new Set((value ?? "").split(",").filter(Boolean));
}

export default function FilterSidebar({ categories }: { categories: string[] }) {
  const router = useRouter();
  const sp = useSearchParams();

  const types = parseMulti(sp.get("type"));
  const modes = parseMulti(sp.get("mode"));
  const category = sp.get("category") ?? "";
  const salary = sp.get("salary") ?? "";
  const location = sp.get("location") ?? "";
  const hasFilters = Boolean(
    types.size || modes.size || category || salary || location || sp.get("q"),
  );

  function push(mutate: (params: URLSearchParams) => void) {
    const params = new URLSearchParams(sp.toString());
    mutate(params);
    params.delete("page");
    const qs = params.toString();
    router.push(qs ? `/?${qs}` : "/");
  }

  function toggleMulti(key: "type" | "mode", current: Set<string>, value: string) {
    push((params) => {
      const next = new Set(current);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      if (next.size) params.set(key, [...next].join(","));
      else params.delete(key);
    });
  }

  function setParam(key: string, value: string) {
    push((params) => {
      if (value) params.set(key, value);
      else params.delete(key);
    });
  }

  return (
    <aside className="sidebar" aria-label="Filters">
      <div className="filter-card">
        <h3>Work type</h3>
        <div className="filter-check-group">
          {Object.entries(WORK_TYPE_LABELS).map(([value, label]) => (
            <label key={value} className="filter-check">
              <input
                type="checkbox"
                checked={types.has(value)}
                onChange={() => toggleMulti("type", types, value)}
              />
              <span>{label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="filter-card">
        <h3>Work arrangement</h3>
        <div className="filter-check-group">
          {Object.entries(ARRANGEMENT_LABELS).map(([value, label]) => (
            <label key={value} className="filter-check">
              <input
                type="checkbox"
                checked={modes.has(value)}
                onChange={() => toggleMulti("mode", modes, value)}
              />
              <span>{label}</span>
            </label>
          ))}
        </div>
      </div>

      {categories.length > 0 && (
        <div className="filter-card">
          <h3>Category</h3>
          <select
            className="filter-select"
            value={category}
            onChange={(e) => setParam("category", e.target.value)}
            aria-label="Category"
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="filter-card">
        <h3>Minimum salary</h3>
        <select
          className="filter-select"
          value={salary}
          onChange={(e) => setParam("salary", e.target.value)}
          aria-label="Minimum salary"
        >
          {SALARY_STEPS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-card">
        <h3>Major cities</h3>
        <div className="city-chips">
          {CITIES.map((c) => (
            <button
              key={c}
              type="button"
              className={`city-chip${location === c ? " active" : ""}`}
              aria-pressed={location === c}
              onClick={() => setParam("location", location === c ? "" : c)}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {hasFilters && (
        <button
          type="button"
          className="clear-filters"
          onClick={() => router.push("/")}
        >
          ✕ Clear all filters
        </button>
      )}
    </aside>
  );
}
