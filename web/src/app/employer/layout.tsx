import Link from "next/link";
import { redirect } from "next/navigation";
import EmployerNav from "@/components/employer/EmployerNav";
import { getSessionUser } from "@/lib/session";

export const metadata = {
  title: { default: "Employer", template: "%s — OpenJobs Employer" },
};

export default async function EmployerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = await getSessionUser();
  if (!user) redirect("/login");

  if (user.role !== "employer") {
    return (
      <div className="auth-wrap">
        <div className="auth-card" style={{ textAlign: "center" }}>
          <h1>Employer account required</h1>
          <p className="auth-sub" style={{ marginTop: "0.5rem" }}>
            You&apos;re signed in as a job seeker ({user.email}). The employer
            dashboard needs an employer account.
          </p>
          <p>
            <Link className="btn btn-primary" href="/register/employer">
              Create an employer account
            </Link>
          </p>
          <p className="auth-alt">
            or <Link href="/">go back to browsing jobs</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="employer-layout">
      <aside className="employer-sidebar">
        <div className="side-label">Navigation</div>
        <EmployerNav />
      </aside>
      <div className="employer-content">{children}</div>
    </div>
  );
}
