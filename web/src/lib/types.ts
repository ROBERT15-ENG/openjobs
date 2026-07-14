export type Job = {
  id: number;
  title: string;
  company: string;
  location: string | null;
  salary: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  description: string;
  category: string | null;
  work_type: string | null;
  work_arrangement: string | null;
  skills: string | null;
  created_at: string;
  is_active: number;
  expires_at: string | null;
  views?: number;
  view_count?: number;
  is_featured: number;
  application_count: number;
  company_rating: number;
};

export type Pagination = {
  page: number;
  limit: number;
  total: number;
  pages: number;
};

export type JobsResponse = {
  jobs: Job[];
  pagination: Pagination;
};

export type SessionUser = {
  id: number;
  name: string;
  email: string;
  role: string;
  employer_id: number | null;
  skills?: string | null;
  phone?: string | null;
  company?: string | null;
  preferred_location?: string | null;
  created_at?: string;
};

/* ── Employer side ── */

export type EmployerStats = {
  active_jobs: number;
  total_applicants: number;
  pending: number;
  interviewing: number;
  job_views: number;
};

export type RecentApplication = {
  id: number;
  user_id: number | null;
  job_id: number;
  status: string;
  applied_at: string;
  cover_letter?: string | null;
  cv_link?: string | null;
  job_title: string;
  company: string;
};

export type EmployerDashboard = {
  stats: EmployerStats;
  my_jobs: Job[];
  recent_applications: RecentApplication[];
};

export type EmployerApplication = {
  id: number;
  user_id: number | null;
  job_id: number;
  status: string;
  applied_at: string;
  cover_letter?: string | null;
  cv_link?: string | null;
  ats_score?: number | null;
  job_title: string;
  company: string;
  applicant_name: string | null;
  applicant_email: string | null;
};

export const KANBAN_STAGES = [
  "applied",
  "screening",
  "interview",
  "offer",
  "hired",
  "rejected",
] as const;

export type KanbanStage = (typeof KANBAN_STAGES)[number];

export type KanbanCard = {
  id: number;
  status: string;
  applied_at: string;
  ats_score: number | null;
  cover_letter: string | null;
  applicant_name: string;
  applicant_email: string;
};

export type KanbanBoard = Record<KanbanStage, KanbanCard[]>;
