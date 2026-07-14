"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { SearchIcon } from "./icons";

/** Keyword + location search pill. Merges into the existing filter params. */
export default function SearchBar() {
  const router = useRouter();
  const sp = useSearchParams();

  const [q, setQ] = useState(sp.get("q") ?? "");
  const [location, setLocation] = useState(sp.get("location") ?? "");
  useEffect(() => {
    setQ(sp.get("q") ?? "");
    setLocation(sp.get("location") ?? "");
  }, [sp]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const params = new URLSearchParams(sp.toString());
    params.delete("page");
    if (q.trim()) params.set("q", q.trim());
    else params.delete("q");
    if (location.trim()) params.set("location", location.trim());
    else params.delete("location");
    const qs = params.toString();
    router.push(qs ? `/?${qs}` : "/");
  }

  return (
    <div className="search-section">
      <form className="search-box" onSubmit={onSubmit} role="search">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Job title, keyword, or company…"
          aria-label="Search jobs"
        />
        <input
          type="search"
          className="search-location"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="Location…"
          aria-label="Location"
        />
        <button type="submit" className="btn btn-primary">
          <SearchIcon /> Search
        </button>
      </form>
    </div>
  );
}
