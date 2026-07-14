import type { Metadata } from "next";
import Link from "next/link";
import KanbanMove from "@/components/employer/KanbanMove";
import PipelineJobSelect from "@/components/employer/PipelineJobSelect";
import { getEmployerDashboard, getKanban } from "@/lib/employer-api";
import { getToken } from "@/lib/session";
import { timeAgo } from "@/lib/format";
import { KANBAN_STAGES } from "@/lib/types";

export const metadata: Metadata = { title: "Pipeline" };

type SP = Record<string, string | string[] | undefined>;

export default async function PipelinePage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const sp = await searchParams;
  const token = await getToken();
  const dash = await getEmployerDashboard(token!);
  const jobs = dash.my_jobs;

  if (jobs.length === 0) {
    return (
      <>
        <h1 className="page-title">Pipeline</h1>
        <p className="page-sub">Move candidates through your hiring stages.</p>
        <div className="empty-state">
          <div className="emoji">📋</div>
          <h3>No jobs yet</h3>
          <p>Post a job first — its applicants will show up here.</p>
          <p style={{ marginTop: "1.5rem" }}>
            <Link className="btn btn-primary" href="/employer/post">
              + Post a Job
            </Link>
          </p>
        </div>
      </>
    );
  }

  const requested = Number(Array.isArray(sp.job) ? sp.job[0] : sp.job);
  const jobId = jobs.some((j) => j.id === requested) ? requested : jobs[0].id;
  const board = await getKanban(token!, jobId);

  return (
    <>
      <h1 className="page-title">Pipeline</h1>
      <p className="page-sub">
        Move candidates between stages with the Move menu on each card.
      </p>

      <div className="pipeline-bar">
        <span className="form-label" style={{ margin: 0 }}>
          Job
        </span>
        <PipelineJobSelect
          jobs={jobs.map((j) => ({ id: j.id, title: j.title }))}
          selected={jobId}
        />
      </div>

      <div className="kanban-board">
        {KANBAN_STAGES.map((stage) => {
          const cards = board?.[stage] ?? [];
          return (
            <div key={stage} className="kanban-col">
              <div className="kanban-col-head">
                <span className={`kanban-dot dot-${stage}`} />
                {stage}
                <span className="kanban-count">{cards.length}</span>
              </div>
              {cards.map((card) => (
                <div key={card.id} className="kanban-card">
                  <div className="kanban-name">{card.applicant_name}</div>
                  <div className="kanban-email">{card.applicant_email}</div>
                  <div className="kanban-foot">
                    <span>{timeAgo(card.applied_at)}</span>
                    {card.ats_score != null && (
                      <span className="kanban-ats">{card.ats_score}%</span>
                    )}
                    <KanbanMove
                      jobId={jobId}
                      applicationId={card.id}
                      current={stage}
                    />
                  </div>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </>
  );
}
