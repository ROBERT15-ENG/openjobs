"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

/** Mirrors the Flask-side rules so users get instant feedback. */
function passwordProblem(pw: string): string | null {
  if (pw.length < 8) return "Password must be at least 8 characters.";
  if (!/[A-Z]/.test(pw)) return "Password needs at least 1 uppercase letter.";
  if (!/[a-z]/.test(pw)) return "Password needs at least 1 lowercase letter.";
  if (!/\d/.test(pw)) return "Password needs at least 1 number.";
  return null;
}

export default function RegisterForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
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
    if (password !== confirm) {
      setError("Passwords don’t match.");
      return;
    }

    setBusy(true);
    try {
      const res = await fetch("/api/session/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password, role: "user" }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.error ?? "Registration failed — try again.");
        return;
      }
      router.push("/login?registered=1");
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
      <h1>Create your account</h1>
      <p className="auth-sub">Free for job seekers. No spam, ever.</p>

      {error && <p className="form-alert error">{error}</p>}

      <div className="field">
        <label htmlFor="name">Full name</label>
        <input
          id="name"
          autoComplete="name"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>

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
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <p className="hint">8+ characters with an uppercase letter, a lowercase letter, and a number.</p>
      </div>

      <div className="field">
        <label htmlFor="confirm">Confirm password</label>
        <input
          id="confirm"
          type="password"
          autoComplete="new-password"
          required
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
        />
      </div>

      <button type="submit" className="btn btn-primary btn-lg" disabled={busy}>
        {busy ? "Creating account…" : "Create account"}
      </button>

      <p className="auth-alt">
        Already have an account? <Link href="/login">Log in</Link>
        <br />
        Hiring? <Link href="/register/employer">Create an employer account</Link>
      </p>
    </form>
  );
}
