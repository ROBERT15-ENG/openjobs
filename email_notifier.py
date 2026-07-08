"""Email notification system for JobSeek"""
import smtplib
import os
import html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# SMTP Config - set via environment variables
SMTP_HOST  = os.environ.get('SMTP_HOST', '')
SMTP_PORT  = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER  = os.environ.get('SMTP_USER', '')
SMTP_PASS  = os.environ.get('SMTP_PASS', '')
FROM_NAME  = os.environ.get('FROM_NAME', 'JobSeek')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@jobseek.com')
APP_URL    = os.environ.get('APP_URL', 'http://localhost:5700')


def _safe(text: str) -> str:
    """Escape HTML to prevent XSS in email content."""
    return html.escape(str(text), quote=True)


def is_configured():
    """Check if SMTP is configured"""
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASS)


def send_email(to_email: str, subject: str, html_body: str, text_body: str = None) -> dict:
    """Send an email"""
    if not is_configured():
        return {"success": False, "error": "SMTP not configured"}

    try:
        msg = MIMEMultipart('alternative')
        msg['From']    = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg['To']      = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(text_body or html_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_job_alert(to_email: str, user_name: str, jobs: list, keywords: str) -> dict:
    """Send job alert email"""
    jobs_html = ""
    for job in jobs[:5]:
        title   = _safe(job.get('title', 'Untitled'))
        company = _safe(job.get('company', 'N/A'))
        loc     = _safe(job.get('location', 'Remote'))
        salary  = _safe(job.get('salary', 'Competitive'))
        link    = _safe(job.get('link', f'{APP_URL}/job.html'))

        jobs_html += f"""
        <div style="background:#1e1e2f;padding:15px;margin:10px 0;border-radius:8px;">
            <h3 style="margin:0 0 10px;color:#00d4ff;">{title}</h3>
            <p style="margin:5px 0;"><strong>Company:</strong> {company}</p>
            <p style="margin:5px 0;"><strong>Location:</strong> {loc}</p>
            <p style="margin:5px 0;"><strong>Salary:</strong> {salary}</p>
            <a href="{link}" style="background:#00d4ff;color:#000;padding:10px 20px;text-decoration:none;border-radius:5px;display:inline-block;margin-top:10px;">Apply Now</a>
        </div>
        """

    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f0f0f;color:#fff;padding:20px;">
        <div style="max-width:600px;margin:0 auto;">
            <h1 style="color:#00d4ff;">🔔 New Jobs Matching "{_safe(keywords)}"</h1>
            <p>Hi {_safe(user_name)}, we found {len(jobs)} new jobs matching your criteria:</p>
            {jobs_html}
            <p style="margin-top:20px;color:#888;">
                <a href="{APP_URL}/alerts.html" style="color:#00d4ff;">Manage your job alerts</a>
            </p>
        </div>
    </body></html>
    """
    return send_email(to_email, f"🔔 {len(jobs)} New Jobs: {keywords}", html_body)


def send_welcome_email(to_email: str, user_name: str) -> dict:
    """Send welcome email"""
    safe_name = _safe(user_name)
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f0f0f;color:#fff;padding:20px;">
        <div style="max-width:600px;margin:0 auto;text-align:center;">
            <h1 style="color:#00d4ff;">🚀 Welcome to JobSeek!</h1>
            <p>Hi {safe_name}, ready to find your dream job?</p>
            <div style="margin:30px 0;">
                <a href="{APP_URL}" style="background:#00d4ff;color:#000;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:bold;">Browse Jobs</a>
            </div>
            <p style="color:#888;">Set up job alerts to get notified when new jobs match your skills!</p>
        </div>
    </body></html>
    """
    return send_email(to_email, "🚀 Welcome to JobSeek!", html_body)


def send_application_confirm(to_email: str, job_title: str, company: str) -> dict:
    """Send application confirmation"""
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f0f0f;color:#fff;padding:20px;">
        <div style="max-width:600px;margin:0 auto;">
            <h1 style="color:#00ff88;">✅ Application Sent!</h1>
            <p>Your application for <strong>{_safe(job_title)}</strong> at <strong>{_safe(company)}</strong> has been submitted.</p>
            <p>We'll notify you when the employer responds.</p>
            <p style="margin-top:30px;color:#888;">
                <a href="{APP_URL}/user.html" style="color:#00d4ff;">View your applications</a>
            </p>
        </div>
    </body></html>
    """
    return send_email(to_email, f"✅ Application Sent: {job_title}", html_body)



def send_employer_new_application(to_email: str, employer_name: str, applicant_name: str, job_title: str, company: str, job_url: str) -> dict:
    """Notify employer that a new application has been received."""
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f0f0f;color:#fff;padding:20px;">
        <div style="max-width:600px;margin:0 auto;">
            <h1 style="color:#00d4ff;">📥 New Application Received</h1>
            <p>Hi <strong>{_safe(employer_name)}</strong>,</p>
            <p><strong>{_safe(applicant_name)}</strong> just applied for <strong>{_safe(job_title)}</strong> at <strong>{_safe(company)}</strong>.</p>
            <div style="margin:24px 0;">
                <a href="{job_url}" style="background:#00d4ff;color:#000;padding:12px 24px;text-decoration:none;border-radius:8px;font-weight:bold;">Review Application</a>
            </div>
            <p style="color:#888;font-size:13px;">Log in to your OpenJobs dashboard to view the full application, resume, and move them through the hiring pipeline.</p>
        </div>
    </body></html>
    """
    return send_email(to_email, f"📥 New Application: {job_title}", html_body)



def send_rejection_email(to_email: str, applicant_name: str, job_title: str, company: str) -> dict:
    """Send a rejection notification when employer moves candidate to rejected."""
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f0f0f;color:#fff;padding:20px;">
        <div style="max-width:600px;margin:0 auto;">
            <h1 style="color:#ff6b6b;">❌ Application Update</h1>
            <p>Hi <strong>{_safe(applicant_name)}</strong>,</p>
            <p>Thank you for applying for the <strong>{_safe(job_title)}</strong> role at <strong>{_safe(company)}</strong>.</p>
            <p>After careful review, we've decided to move forward with other candidates at this time. We encourage you to apply for other roles that match your skills — new positions are posted daily.</p>
            <p style="margin-top:24px;color:#888;font-size:13px;">This decision is not a reflection of your abilities. We wish you the very best in your job search.</p>
            <hr style="border-color:#333;margin:24px 0;">
            <p style="color:#888;font-size:13px;">Best regards,<br>The {company} Team</p>
            <p style="color:#555;font-size:12px;margin-top:16px;">You're receiving this because you applied for a position on OpenJobs. <a href="{APP_URL}" style="color:#00d4ff;">View all open positions</a></p>
        </div>
    </body></html>
    """
    return send_email(to_email, f"Update on your application: {job_title}", html_body)


if __name__ == "__main__":
    print(f"SMTP Configured: {is_configured()}")
