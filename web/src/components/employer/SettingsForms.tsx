"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import type { SessionUser } from "@/lib/types";

export default function SettingsForms({ user }: { user: SessionUser }) {
  const router = useRouter();
  const [profile, setProfile] = useState({
    name: user.name ?? "",
    phone: user.phone ?? "",
    preferred_location: user.preferred_location ?? "",
    company: user.company ?? "",
  });
  const [calendly, setCalendly] = useState("");
  const [msg, setMsg] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    setBusy(true);
    try {
      const res = await fetch("/api/proxy/user/profile", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setMsg({ kind: "error", text: data.error ?? "Could not save profile." });
        return;
      }
      setMsg({ kind: "success", text: "Profile saved." });
      router.refresh();
    } catch {
      setMsg({ kind: "error", text: "Could not reach the server." });
    } finally {
      setBusy(false);
    }
  }

  async function saveCalendly(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    setBusy(true);
    try {
      const res = await fetch("/api/proxy/employer/calendly", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ calendly_url: calendly.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setMsg({ kind: "error", text: data.error ?? "Could not save link." });
        return;
      }
      setMsg({ kind: "success", text: "Interview scheduling link saved." });
    } catch {
      setMsg({ kind: "error", text: "Could not reach the server." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {msg && <p className={`alert alert-${msg.kind}`}>{msg.text}</p>}

      <form className="card" onSubmit={saveProfile}>
        <div className="card-title" style={{ marginBottom: "1.25rem" }}>
          Company Profile
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label" htmlFor="st-name">
              Contact Name
            </label>
            <input
              id="st-name"
              className="form-input"
              value={profile.name}
              onChange={(e) => setProfile({ ...profile, name: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="st-email">
              Email
            </label>
            <input
              id="st-email"
              className="form-input"
              value={user.email}
              readOnly
              style={{ opacity: 0.6, cursor: "not-allowed" }}
            />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="st-phone">
              Phone
            </label>
            <input
              id="st-phone"
              className="form-input"
              placeholder="+61 400 000 000"
              value={profile.phone}
              onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="st-location">
              Primary Location
            </label>
            <input
              id="st-location"
              className="form-input"
              placeholder="e.g. Sydney, NSW"
              value={profile.preferred_location}
              onChange={(e) =>
                setProfile({ ...profile, preferred_location: e.target.value })
              }
            />
          </div>
          <div className="form-group full">
            <label className="form-label" htmlFor="st-company">
              Company Name
            </label>
            <input
              id="st-company"
              className="form-input"
              placeholder="Your company"
              value={profile.company}
              onChange={(e) => setProfile({ ...profile, company: e.target.value })}
            />
          </div>
          <div className="form-group full">
            <button type="submit" className="btn btn-primary" disabled={busy}>
              Save Changes
            </button>
          </div>
        </div>
      </form>

      <form className="card" onSubmit={saveCalendly}>
        <div className="card-title" style={{ marginBottom: "0.5rem" }}>
          Interview Scheduling
        </div>
        <p className="page-sub" style={{ marginBottom: "1rem" }}>
          Candidates you move to the interview stage can book time via this
          link (Calendly or similar).
        </p>
        <div className="form-grid">
          <div className="form-group full">
            <label className="form-label" htmlFor="st-calendly">
              Scheduling URL
            </label>
            <input
              id="st-calendly"
              className="form-input"
              type="url"
              placeholder="https://calendly.com/your-company/interview"
              value={calendly}
              onChange={(e) => setCalendly(e.target.value)}
            />
          </div>
          <div className="form-group full">
            <button type="submit" className="btn btn-ghost" disabled={busy}>
              Save Link
            </button>
          </div>
        </div>
      </form>
    </>
  );
}
