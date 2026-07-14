import type { Metadata } from "next";
import JobForm from "@/components/employer/JobForm";
import { getSessionUser } from "@/lib/session";

export const metadata: Metadata = { title: "Post a Job" };

export default async function PostJobPage() {
  const user = await getSessionUser();

  return (
    <>
      <h1 className="page-title">Post a New Job</h1>
      <p className="page-sub">
        Fill in the details below to publish your job listing.
      </p>
      <p className="notice">
        🧪 Free while OpenJobs is in beta — paid placement plans are coming
        later.
      </p>
      <JobForm defaultCompany={user?.company ?? ""} />
    </>
  );
}
