"""Cascade helpers for hard deletes.

SQLite cannot add ON DELETE CASCADE to existing tables, and foreign keys are
now enforced on every connection, so dependent rows must be removed explicitly
and in dependency order.
"""


def delete_job_cascade(db, job_id: int) -> None:
    db.execute(
        'DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE job_id = ?)',
        (job_id,),
    )
    db.execute('DELETE FROM conversations WHERE job_id = ?', (job_id,))
    db.execute('DELETE FROM job_alert_sends WHERE job_id = ?', (job_id,))
    db.execute('DELETE FROM job_reports WHERE job_id = ?', (job_id,))
    db.execute('DELETE FROM saved_jobs WHERE job_id = ?', (job_id,))
    db.execute('DELETE FROM applications WHERE job_id = ?', (job_id,))
    db.execute('DELETE FROM jobs WHERE id = ?', (job_id,))


def delete_user_cascade(db, user_id: int) -> None:
    # Conversations the user is party to (and their messages)
    db.execute(
        """DELETE FROM messages WHERE conversation_id IN (
               SELECT id FROM conversations WHERE seeker_id = ? OR employer_id = ?
           )""",
        (user_id, user_id),
    )
    db.execute('DELETE FROM conversations WHERE seeker_id = ? OR employer_id = ?', (user_id, user_id))
    db.execute('DELETE FROM messages WHERE sender_id = ?', (user_id,))

    # Seeker-owned rows
    db.execute(
        'DELETE FROM job_alert_sends WHERE alert_id IN (SELECT id FROM job_alerts WHERE user_id = ?)',
        (user_id,),
    )
    db.execute('DELETE FROM job_alerts WHERE user_id = ?', (user_id,))
    db.execute('DELETE FROM saved_jobs WHERE user_id = ?', (user_id,))
    db.execute('DELETE FROM applications WHERE user_id = ?', (user_id,))
    db.execute('UPDATE job_reports SET reporter_id = NULL WHERE reporter_id = ?', (user_id,))

    # Employer-owned rows: listings are closed and detached rather than destroyed,
    # so applicants keep their history.
    db.execute('UPDATE jobs SET is_active = 0, employer_id = NULL WHERE employer_id = ?', (user_id,))
    db.execute('DELETE FROM organization_members WHERE user_id = ?', (user_id,))

    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
