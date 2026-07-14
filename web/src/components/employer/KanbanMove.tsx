"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { KANBAN_STAGES, type KanbanStage } from "@/lib/types";

export default function KanbanMove({
  jobId,
  applicationId,
  current,
}: {
  jobId: number;
  applicationId: number;
  current: KanbanStage;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function move(stage: string) {
    if (!stage || stage === current) return;
    setBusy(true);
    try {
      const res = await fetch(`/api/proxy/kanban/${jobId}/move`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ application_id: applicationId, stage }),
      });
      if (res.ok) router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <select
      className="status-select kanban-move"
      value=""
      disabled={busy}
      onChange={(e) => move(e.target.value)}
      aria-label="Move to stage"
    >
      <option value="">Move…</option>
      {KANBAN_STAGES.filter((s) => s !== current).map((s) => (
        <option key={s} value={s}>
          {s.charAt(0).toUpperCase() + s.slice(1)}
        </option>
      ))}
    </select>
  );
}
