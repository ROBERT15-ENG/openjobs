"""Applicant tracking score helpers."""

from semantic_matcher import keyword_score


def compute_ats_score(resume_text: str, job_skills: str, job_description: str = '') -> int:
    """Return 0-100 fit score from résumé vs job skills (keyword overlap)."""
    if not resume_text:
        return 0
    skills = job_skills or ''
    if not skills and job_description:
        skills = job_description[:2000]
    score, _, _ = keyword_score(skills, resume_text)
    return score
