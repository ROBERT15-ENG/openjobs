import Link from "next/link";
import { getSessionUser } from "@/lib/session";

export default async function Header() {
  const user = await getSessionUser();

  return (
    <header className="site-header">
      <div className="header-inner">
        <Link href="/" className="logo-block">
          <div className="logo">
            Open<span>Jobs</span>
          </div>
          <div className="logo-sub">AI-Powered Career Platform</div>
        </Link>
        <nav className="site-nav" aria-label="Main">
          <Link href="/">Find Jobs</Link>
          {user && user.role !== "employer" && <Link href="/saved">Saved</Link>}
          <Link href="/employer">For Employers</Link>
        </nav>
        <div className="header-actions">
          {user ? (
            <>
              <span className="user-chip" title={user.email}>
                {user.name}
              </span>
              <form action="/api/session/logout" method="POST">
                <button type="submit" className="btn btn-ghost">
                  Log out
                </button>
              </form>
            </>
          ) : (
            <>
              <Link href="/login" className="btn btn-ghost">
                Log in
              </Link>
              <Link href="/register" className="btn btn-primary">
                Sign Up Free
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
