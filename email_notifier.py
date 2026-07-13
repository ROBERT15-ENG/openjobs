"""Email notification system for OpenJobs"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# SMTP Config - set via environment variables
SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
FROM_NAME = os.environ.get('FROM_NAME', 'OpenJobs')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@openjobs.com.au')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5700')

def is_configured():
    """Check if SMTP is configured"""
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASS)

def send_email(to_email: str, subject: str, html_body: str, text_body: str = None) -> dict:
    """Send an email"""
    if not is_configured():
        return {"success": False, "error": "SMTP not configured"}
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg['To'] = to_email
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
        jobs_html += f"""
        <div style="background: #1e1e2f; padding: 15px; margin: 10px 0; border-radius: 8px;">
            <h3 style="margin: 0 0 10px; color: #00d4ff;">{job.get('title', 'Untitled')}</h3>
            <p style="margin: 5px 0;"><strong>Company:</strong> {job.get('company', 'N/A')}</p>
            <p style="margin: 5px 0;"><strong>Location:</strong> {job.get('location', 'Remote')}</p>
            <p style="margin: 5px 0;"><strong>Salary:</strong> {job.get('salary', 'Competitive')}</p>
            <a href="{job.get('link', BASE_URL + '/')}" style="background: #00d4ff; color: #000; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px;">Apply Now</a>
        </div>
        """
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #0f0f0f; color: #fff; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto;">
            <h1 style="color: #00d4ff;">🔔 New Jobs Matching "{keywords}"</h1>
            <p>Hi {user_name}, we found {len(jobs)} new jobs matching your criteria:</p>
            {jobs_html}
            <p style="margin-top: 20px; color: #888;">
                <a href="{BASE_URL}/user" style="color: #00d4ff;">Manage your job alerts</a>
            </p>
        </div>
    </body>
    </html>
    """
    
    return send_email(to_email, f"🔔 {len(jobs)} New Jobs: {keywords}", html)

def send_welcome_email(to_email: str, user_name: str) -> dict:
    """Send welcome email"""
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #0f0f0f; color: #fff; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; text-align: center;">
            <h1 style="color: #00d4ff;">Welcome to OpenJobs!</h1>
            <p>Hi {user_name}, ready to find your dream job?</p>
            <div style="margin: 30px 0;">
                <a href="{BASE_URL}" style="background: #00d4ff; color: #000; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;">Browse Jobs</a>
            </div>
            <p style="color: #888;">Set up job alerts to get notified when new jobs match your skills!</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(to_email, "Welcome to OpenJobs!", html)

def send_application_confirm(to_email: str, job_title: str, company: str) -> dict:
    """Send application confirmation"""
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #0f0f0f; color: #fff; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto;">
            <h1 style="color: #00ff88;">✅ Application Sent!</h1>
            <p>Your application for <strong>{job_title}</strong> at <strong>{company}</strong> has been submitted.</p>
            <p>We'll notify you when the employer responds.</p>
            <p style="margin-top: 30px; color: #888;">
                <a href="{BASE_URL}/user" style="color: #00d4ff;">View your applications</a>
            </p>
        </div>
    </body>
    </html>
    """
    
    return send_email(to_email, f"✅ Application Sent: {job_title}", html)

if __name__ == "__main__":
    # Test if configured
    print(f"SMTP Configured: {is_configured()}")
