"use client";

import { useRouter } from "next/navigation";

export default function PipelineJobSelect({
  jobs,
  selected,
}: {
  jobs: Array<{ id: number; title: string }>;
  selected: number;
}) {
  const router = useRouter();

  return (
    <select
      className="form-select"
      value={selected}
      onChange={(e) => router.push(`/employer/pipeline?job=${e.target.value}`)}
      aria-label="Select job"
    >
      {jobs.map((j) => (
        <option key={j.id} value={j.id}>
          {j.title}
        </option>
      ))}
    </select>
  );
}
