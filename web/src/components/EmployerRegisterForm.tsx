"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

function passwordProblem(pw: string): string | null {
  if (pw.length < 8) return "Password must be at least 8 characters.";
  if (!/[A-Z]/.test(pw)) return "Password needs at least 1 uppercase letter.";
  if (!/[a-z]/.test(pw)) return "Password needs at least 1 lowercase letter.";
  if (!/\d/.test(pw)) return "Password needs at least 1 number.";
  return null;
}

export default function EmployerRegisterForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const pwProblem = passwordProblem(password);
    if (pwProblem) {
      setError(pwProblem);
      return;
    }
    setBusy(true);
    try {
      const res = await fetch("/api/session/register-employer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password, company }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.error ?? "Registration failed — try again.");
        return;
      }
      if (data.autoLogin) {
        router.push("/employer");
        router.refresh();
      } else {
        router.push("/login?registered=1");
      }
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
      <h1>Employer account</h1>
      <p className="auth-sub">
        Post jobs, review applicants, and run your hiring pipeline.
      </p>

      {error && <p className="form-alert error">{error}</p>}

      <div className="field">
        <label htmlFor="er-name">Your full name</label>
        <input
          id="er-name"
          autoComplete="name"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>

      <div className="field">
        <label htmlFor="er-email">Work email</label>
        <input
          id="er-email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>

      <div className="field">
        <label htmlFor="er-company">Company name</label>
        <input
          id="er-company"
          required
          value={company}
          onChange={(e) => setCompany(e.target.value)}
        />
      </div>

      <div className="field">
        <label htmlFor="er-password">Password</label>
        <input
          id="er-password"
          type="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <p className="hint">
          8+ characters with an uppercase letter, a lowercase letter, and a number.
        </p>
      </div>

      <button type="submit" className="btn btn-primary btn-lg" disabled={busy}>
        {busy ? "Creating account…" : "Create employer account"}
      </button>

      <p className="auth-alt">
        Looking for a job instead? <Link href="/register">Seeker sign-up</Link>
      </p>
    </form>
  );
}
