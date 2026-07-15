"""Shared application status update (PATCH + kanban + bulk)."""

import datetime


def update_application_status(db, app_id, new_status, *, send_email=True, actor_role=None):
    """
    Update status and optionally email the seeker.
    Returns (success, app_dict_or_error_message, old_status).
    """
    app_row = db.execute(
        """
        SELECT a.id, a.user_id, a.status, j.employer_id, j.title as job_title, j.company as job_company,
               u.email as applicant_email, u.name as applicant_name
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN users u ON u.id = a.user_id
        WHERE a.id = ?
        """,
        (app_id,),
    ).fetchone()
    if not app_row:
        return False, 'Application not found', None

    from status import normalize_status
    old_status = normalize_status(app_row['status'])
    new_status = normalize_status(new_status)

    db.execute(
        'UPDATE applications SET status = ?, updated_at = ? WHERE id = ?',
        (new_status, datetime.datetime.now().isoformat(), app_id),
    )
    db.commit()
    updated = db.execute('SELECT * FROM applications WHERE id = ?', (app_id,)).fetchone()

    if (
        send_email
        and actor_role in ('employer', 'admin')
        and app_row['applicant_email']
        and new_status != old_status
    ):
        try:
            if new_status == 'rejected':
                from email_notifier import send_rejection_email
                send_rejection_email(
                    app_row['applicant_email'],
                    app_row['applicant_name'] or 'there',
                    app_row['job_title'] or 'your application',
                    app_row['job_company'] or '',
                )
            else:
                from email_notifier import send_application_status_update
                send_application_status_update(
                    app_row['applicant_email'],
                    app_row['applicant_name'] or 'there',
                    app_row['job_title'] or 'your application',
                    app_row['job_company'] or '',
                    new_status,
                )
        except Exception as exc:
            print(f'[application_status] email error: {exc}')

    return True, dict(updated), old_status
