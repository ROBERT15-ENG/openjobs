"""Email notification system for OpenJobs.

Delivery model
--------------
``send_email`` does not talk to SMTP inside the request. It writes a row to the
``email_outbox`` table and kicks a best-effort background drain. The durable
backstop is ``scripts/send_outbox.py`` (cron) or ``POST /api/admin/email/drain``.
This keeps request latency independent of the mail provider and means a
provider outage never loses mail — rows stay ``pending`` and are retried.

Set ``EMAIL_DELIVERY=sync`` to send inline (handy for one-off scripts).
"""
import html
import logging
import os
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger(__name__)

# SMTP Config - set via environment variables
SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
SMTP_TIMEOUT = int(os.environ.get('SMTP_TIMEOUT', '15'))
FROM_NAME = os.environ.get('FROM_NAME', 'OpenJobs')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@openjobs.com.au')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5700')
EMAIL_DELIVERY = os.environ.get('EMAIL_DELIVERY', 'outbox').lower()
MAX_ATTEMPTS = int(os.environ.get('EMAIL_MAX_ATTEMPTS', '5'))

_drain_lock = threading.Lock()


def is_configured():
    """Check if SMTP is configured"""
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASS)


def deliver_email(to_email: str, subject: str, html_body: str, text_body: str = None) -> dict:
    """Synchronously hand one message to SMTP."""
    if not is_configured():
        return {"success": False, "error": "SMTP not configured"}

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(text_body or html_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _connect(db_path=None):
    from db import connect  # api/ is on sys.path for every caller

    return connect(db_path)


def enqueue_email(to_email: str, subject: str, html_body: str, text_body: str = None,
                  db_path: str = None) -> dict:
    from timeutil import utcnow_iso

    conn = _connect(db_path)
    try:
        cur = conn.execute(
            """INSERT INTO email_outbox (to_email, subject, html_body, text_body, status, created_at)
               VALUES (?, ?, ?, ?, 'pending', ?)""",
            (to_email, subject, html_body, text_body, utcnow_iso()),
        )
        conn.commit()
        return {"success": True, "queued": True, "id": cur.lastrowid}
    finally:
        conn.close()


def drain_outbox(limit: int = 50, db_path: str = None, deliver=None) -> dict:
    """Send pending outbox rows. Safe to run from several processes at once:
    each row is claimed with a conditional UPDATE before delivery."""
    from timeutil import utcnow_iso

    deliver = deliver or deliver_email
    summary = {"sent": 0, "failed": 0, "skipped": 0}
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            """SELECT id, to_email, subject, html_body, text_body FROM email_outbox
               WHERE status = 'pending' AND attempts < ? ORDER BY id LIMIT ?""",
            (MAX_ATTEMPTS, limit),
        ).fetchall()
        for row in rows:
            claimed = conn.execute(
                "UPDATE email_outbox SET status = 'sending', attempts = attempts + 1 "
                "WHERE id = ? AND status = 'pending'",
                (row['id'],),
            ).rowcount
            conn.commit()
            if claimed != 1:
                summary["skipped"] += 1
                continue
            result = deliver(row['to_email'], row['subject'], row['html_body'], row['text_body'])
            if result.get("success"):
                conn.execute(
                    "UPDATE email_outbox SET status = 'sent', sent_at = ?, last_error = NULL WHERE id = ?",
                    (utcnow_iso(), row['id']),
                )
                summary["sent"] += 1
            else:
                attempts = conn.execute(
                    'SELECT attempts FROM email_outbox WHERE id = ?', (row['id'],)
                ).fetchone()['attempts']
                final = attempts >= MAX_ATTEMPTS
                conn.execute(
                    "UPDATE email_outbox SET status = ?, last_error = ? WHERE id = ?",
                    ('failed' if final else 'pending', str(result.get("error"))[:1000], row['id']),
                )
                summary["failed"] += 1
            conn.commit()
    finally:
        conn.close()
    return summary


def _drain_in_background(db_path=None):
    if not _drain_lock.acquire(blocking=False):
        return

    def _run():
        try:
            drain_outbox(db_path=db_path)
        except Exception:
            log.exception('outbox drain failed')
        finally:
            _drain_lock.release()

    threading.Thread(target=_run, name='email-outbox-drain', daemon=True).start()


def send_email(to_email: str, subject: str, html_body: str, text_body: str = None) -> dict:
    """Queue an email for delivery (or send inline when EMAIL_DELIVERY=sync)."""
    if not is_configured():
        return {"success": False, "error": "SMTP not configured"}
    if EMAIL_DELIVERY == 'sync':
        return deliver_email(to_email, subject, html_body, text_body)
    try:
        result = enqueue_email(to_email, subject, html_body, text_body)
    except Exception as exc:
        log.exception('outbox enqueue failed; falling back to inline send')
        return deliver_email(to_email, subject, html_body, text_body) | {"enqueue_error": str(exc)}
    _drain_in_background()
    return result

def send_job_alert(to_email: str, user_name: str, jobs: list, keywords: str) -> dict:
    """Send job alert email"""
    safe_name = html.escape(user_name)
    safe_keywords = html.escape(keywords)
    jobs_html = ""
    for job in jobs[:5]:
        title = html.escape(str(job.get('title', 'Untitled')))
        company = html.escape(str(job.get('company', 'N/A')))
        location = html.escape(str(job.get('location', 'Remote')))
        salary = html.escape(str(job.get('salary', 'Competitive')))
        link = html.escape(str(job.get('link', BASE_URL + '/')))
        jobs_html += f"""
        <div style="background: #1e1e2f; padding: 15px; margin: 10px 0; border-radius: 8px;">
            <h3 style="margin: 0 0 10px; color: #00d4ff;">{title}</h3>
            <p style="margin: 5px 0;"><strong>Company:</strong> {company}</p>
            <p style="margin: 5px 0;"><strong>Location:</strong> {location}</p>
            <p style="margin: 5px 0;"><strong>Salary:</strong> {salary}</p>
            <a href="{link}" style="background: #00d4ff; color: #000; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px;">Apply Now</a>
        </div>
        """
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #0f0f0f; color: #fff; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto;">
            <h1 style="color: #00d4ff;">🔔 New Jobs Matching "{safe_keywords}"</h1>
            <p>Hi {safe_name}, we found {len(jobs)} new jobs matching your criteria:</p>
            {jobs_html}
            <p style="margin-top: 20px; color: #888;">
                <a href="{html.escape(BASE_URL + '/user')}" style="color: #00d4ff;">Manage your job alerts</a>
            </p>
        </div>
    </body>
    </html>
    """
    
    return send_email(to_email, f"🔔 {len(jobs)} New Jobs: {keywords}", html_body)

def send_welcome_email(to_email: str, user_name: str) -> dict:
    """Send welcome email"""
    safe_name = html.escape(user_name)
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #0f0f0f; color: #fff; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; text-align: center;">
            <h1 style="color: #00d4ff;">Welcome to OpenJobs!</h1>
            <p>Hi {safe_name}, ready to find your dream job?</p>
            <div style="margin: 30px 0;">
                <a href="{html.escape(BASE_URL)}" style="background: #00d4ff; color: #000; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;">Browse Jobs</a>
            </div>
            <p style="color: #888;">Set up job alerts to get notified when new jobs match your skills!</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(to_email, "Welcome to OpenJobs!", html_body)

def send_application_confirm(to_email: str, job_title: str, company: str) -> dict:
    """Send application confirmation"""
    safe_title = html.escape(job_title)
    safe_company = html.escape(company)
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #0f0f0f; color: #fff; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto;">
            <h1 style="color: #00ff88;">✅ Application Sent!</h1>
            <p>Your application for <strong>{safe_title}</strong> at <strong>{safe_company}</strong> has been submitted.</p>
            <p>We'll notify you when the employer responds.</p>
            <p style="margin-top: 30px; color: #888;">
                <a href="{html.escape(BASE_URL + '/user')}" style="color: #00d4ff;">View your applications</a>
            </p>
        </div>
    </body>
    </html>
    """
    
    return send_email(to_email, f"✅ Application Sent: {job_title}", html_body)

def send_employer_new_application(
    to_email: str,
    employer_name: str,
    job_title: str,
    applicant_name: str,
    ats_score: int = 0,
) -> dict:
    safe_employer = html.escape(employer_name)
    safe_title = html.escape(job_title)
    safe_applicant = html.escape(applicant_name)
    score_line = f'<p><strong>ATS match score:</strong> {int(ats_score)}%</p>' if ats_score else ''
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f0f0f;color:#fff;padding:20px;">
      <div style="max-width:600px;margin:0 auto;">
        <h1 style="color:#00d4ff;">📥 New Application</h1>
        <p>Hi {safe_employer}, <strong>{safe_applicant}</strong> applied for <strong>{safe_title}</strong>.</p>
        {score_line}
        <p><a href="{html.escape(BASE_URL + '/employer')}" style="color:#00d4ff;">Review in your dashboard</a></p>
      </div>
    </body></html>"""
    return send_email(to_email, f"New applicant: {job_title}", html_body)


def send_application_status_update(
    to_email: str,
    user_name: str,
    job_title: str,
    company: str,
    new_status: str,
) -> dict:
    safe_name = html.escape(user_name)
    safe_title = html.escape(job_title)
    safe_company = html.escape(company)
    safe_status = html.escape(new_status.replace('_', ' ').title())
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f0f0f;color:#fff;padding:20px;">
      <div style="max-width:600px;margin:0 auto;">
        <h1 style="color:#00d4ff;">Application update</h1>
        <p>Hi {safe_name}, your application for <strong>{safe_title}</strong> at <strong>{safe_company}</strong>
        is now: <strong>{safe_status}</strong>.</p>
        <p><a href="{html.escape(BASE_URL + '/user')}" style="color:#00d4ff;">View your applications</a></p>
      </div>
    </body></html>"""
    return send_email(to_email, f"Update: {job_title} — {safe_status}", html_body)


def send_rejection_email(to_email: str, applicant_name: str, job_title: str, company: str) -> dict:
    """Dedicated rejection notice (ekip pattern) when status moves to rejected."""
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f0f0f;color:#fff;padding:20px;">
      <div style="max-width:600px;margin:0 auto;">
        <h1 style="color:#ff6b6b;">Application update</h1>
        <p>Hi <strong>{html.escape(applicant_name)}</strong>,</p>
        <p>Thank you for your interest in the <strong>{html.escape(job_title)}</strong> role at
        <strong>{html.escape(company)}</strong>.</p>
        <p>After careful review, we regret to inform you that your application is unlikely to proceed
        further at this stage. This is not a reflection of your abilities — we simply had a high volume
        of qualified candidates.</p>
        <p>We encourage you to keep browsing — new roles are posted regularly.</p>
        <p><a href="{html.escape(BASE_URL)}" style="color:#00d4ff;">View open positions</a></p>
      </div>
    </body></html>"""
    return send_email(to_email, f"Update on your application: {job_title}", html_body)


if __name__ == "__main__":
    # Test if configured
    print(f"SMTP Configured: {is_configured()}")
