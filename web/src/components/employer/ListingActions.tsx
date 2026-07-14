"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function ListingActions({
  jobId,
  featured,
}: {
  jobId: number;
  featured: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);

  async function call(path: string, method: string, body?: unknown) {
    setBusy(true);
    try {
      const res = await fetch(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      if (res.ok) router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="form-actions" style={{ justifyContent: "flex-end", flexWrap: "nowrap" }}>
      <button
        type="button"
        className="btn btn-ghost"
        disabled={busy}
        title={featured ? "Remove featured badge" : "Feature this job"}
        onClick={() =>
          call(`/api/proxy/jobs/${jobId}/feature`, "POST", { featured: !featured })
        }
      >
        {featured ? "★ Featured" : "☆ Feature"}
      </button>
      <Link className="btn btn-ghost" href={`/employer/listings/${jobId}/edit`}>
        Edit
      </Link>
      {confirming ? (
        <>
          <button
            type="button"
            className="btn btn-danger"
            disabled={busy}
            onClick={() => call(`/api/proxy/jobs/${jobId}`, "DELETE")}
          >
            Confirm
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => setConfirming(false)}
          >
            Keep
          </button>
        </>
      ) : (
        <button
          type="button"
          className="btn btn-danger"
          disabled={busy}
          onClick={() => setConfirming(true)}
        >
          Remove
        </button>
      )}
    </div>
  );
}
