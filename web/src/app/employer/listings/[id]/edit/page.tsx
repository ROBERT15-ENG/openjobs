import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import JobForm from "@/components/employer/JobForm";
import { getJob } from "@/lib/api";

export const metadata: Metadata = { title: "Edit Job" };

export default async function EditJobPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const jobId = Number(id);
  if (!Number.isInteger(jobId) || jobId <= 0) notFound();

  const job = await getJob(jobId);
  if (!job) notFound();

  return (
    <>
      <Link href="/employer/listings" className="back-link">
        ← My Listings
      </Link>
      <h1 className="page-title">Edit Job</h1>
      <p className="page-sub">{job.title}</p>
      <JobForm job={job} />
    </>
  );
}
