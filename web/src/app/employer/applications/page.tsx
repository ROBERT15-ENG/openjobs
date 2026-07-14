import type { Metadata } from "next";
import ApplicationsTable from "@/components/employer/ApplicationsTable";
import { getEmployerApplications } from "@/lib/employer-api";
import { getToken } from "@/lib/session";

export const metadata: Metadata = { title: "Applications" };

export default async function ApplicationsPage() {
  const token = await getToken();
  const applications = await getEmployerApplications(token!);

  return (
    <>
      <h1 className="page-title">Applications</h1>
      <p className="page-sub">Review and manage applicants for your jobs.</p>
      <ApplicationsTable initial={applications} />
    </>
  );
}
