"""Helpers for one-click / easy apply flows."""


def profile_resume_text(user: dict) -> str:
    """Build résumé text from stored profile when the client sends none."""
    resume = (user.get('resume_text') or '').strip()
    if resume:
        return resume
    skills = (user.get('skills') or '').strip()
    if skills:
        return f'Skills: {skills}'
    experience = (user.get('experience') or '').strip()
    if experience:
        return experience
    return ''


def generate_apply_cover_letter(user: dict, job: dict) -> str:
    """Template cover letter from profile + job (no Ollama required)."""
    name = (user.get('name') or 'Applicant').strip()
    title = (job.get('title') or 'this role').strip()
    company = (job.get('company') or 'your company').strip()
    skills = (user.get('skills') or '').strip()
    skills_line = f' My core skills include {skills}.' if skills else ''
    return (
        f'Dear Hiring Manager,\n\n'
        f'I am writing to express my interest in the {title} position at {company}. '
        f'I believe my background is a strong fit for this opportunity.{skills_line}\n\n'
        f'I would welcome the chance to discuss how I can contribute to {company}.\n\n'
        f'Kind regards,\n{name}'
    )
