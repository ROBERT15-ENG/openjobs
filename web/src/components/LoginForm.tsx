"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

export default function LoginForm({
  justRegistered,
}: {
  justRegistered: boolean;
}) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await fetch("/api/session/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.message ?? data.error ?? "Login failed — try again.");
        return;
      }
      router.push("/");
      router.refresh();
    } catch {
      setError("Could not reach the server — is the API running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="auth-card" onSubmit={onSubmit}>
      <div className="auth-logo" aria-hidden>
        ⚡
      </div>
      <h1>Welcome back</h1>
      <p className="auth-sub">Log in to save jobs and track applications.</p>

      {justRegistered && (
        <p className="form-alert success">Account created — log in below.</p>
      )}
      {error && <p className="form-alert error">{error}</p>}

      <div className="field">
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>

      <div className="field">
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>

      <button type="submit" className="btn btn-primary btn-lg" disabled={busy}>
        {busy ? "Logging in…" : "Log in"}
      </button>

      <p className="auth-alt">
        New to OpenJobs? <Link href="/register">Create an account</Link>
      </p>
    </form>
  );
}
