"""Sprint 1-6: job alerts matcher, AI endpoints, employer registration."""

import os
import sys

API = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api'))
sys.path.insert(0, API)

from conftest import auth_headers, auth_token  # noqa: E402
from job_alert_matcher import job_matches_alert, run_job_alert_matching  # noqa: E402


def test_register_employer_endpoint(client):
    res = client.post('/api/auth/register-employer', json={
        'name': 'Acme HR',
        'email': 'hr@acme.test',
        'password': 'SecurePass1',
        'company': 'Acme Corp',
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data['user']['role'] == 'employer'
    assert data['user']['company'] == 'Acme Corp'


def test_job_matches_alert_keyword_and_remote():
    job = {
        'title': 'Senior Python Engineer',
        'description': 'Build APIs with Flask',
        'skills': 'Python, Flask',
        'company': 'TechCo',
        'location': 'Sydney',
        'work_arrangement': 'remote',
        'salary_min': 120000,
    }
    alert = {'keyword': 'Python', 'location': 'Sydney', 'remote_only': 1, 'salary_min': 100000}
    assert job_matches_alert(job, alert) is True

    alert_no_match = {'keyword': 'Java', 'remote_only': 0}
    assert job_matches_alert(job, alert_no_match) is False


def test_notify_alerts_for_job_records_send(client):
    token = auth_token(client)
    client.post('/api/job_alerts', headers=auth_headers(token), json={
        'keyword': 'Python',
        'remote_only': True,
    })

    emp_token = auth_token(client, email='employer@test.com')
    create = client.post('/api/jobs', headers=auth_headers(emp_token), json={
        'title': 'Python Developer',
        'company': 'Acme',
        'location': 'Remote',
        'description': 'Python backend role',
        'skills': 'Python, Flask',
        'work_arrangement': 'remote',
        'salary_min': 90000,
    })
    assert create.status_code == 201

    import sqlite3
    db_path = os.environ['DATABASE_PATH']
    conn = sqlite3.connect(db_path)
    sends = conn.execute('SELECT COUNT(*) FROM job_alert_sends').fetchone()[0]
    conn.close()
    assert sends >= 1


def test_run_job_alert_matching_dry_run(client):
    token = auth_token(client)
    client.post('/api/job_alerts', headers=auth_headers(token), json={'keyword': 'Backend'})

    db_path = os.environ['DATABASE_PATH']
    result = run_job_alert_matching(since_hours=168, dry_run=True, db_path=db_path)
    assert result['dry_run'] is True
    assert result['alerts_checked'] >= 1


def test_ai_score_resume_without_ollama(client):
    res = client.post('/api/ai/ollama/score/resume', json={
        'job_description': 'Python developer with Flask experience required',
        'resume_text': 'Experienced Python developer. Built Flask APIs for 5 years.',
    })
    assert res.status_code == 200
    data = res.get_json()
    assert 'score' in data
    assert data['score'] >= 0
    assert data['source'] in ('keyword', 'ollama')


def test_ai_cover_letter_fallback(client):
    res = client.post('/api/ai/ollama/generate/cover-letter', json={
        'job_title': 'Software Engineer',
        'company': 'OpenJobs',
        'resume_text': 'Full-stack developer',
    })
    assert res.status_code == 200
    data = res.get_json()
    assert 'cover_letter' in data
    assert 'OpenJobs' in data['cover_letter']


def test_ai_interview_prep_fallback(client):
    res = client.post('/api/ai/ollama/interview-prep', json={'job_title': 'Data Analyst'})
    assert res.status_code == 200
    data = res.get_json()
    assert 'questions' in data
    assert 'Data Analyst' in data['questions']


def test_cad_redirects_to_search(client):
    res = client.get('/cad', follow_redirects=False)
    assert res.status_code == 302
    assert res.headers['Location'].endswith('/?q=autocad')


def test_admin_run_job_alerts(client):
    admin_token = auth_token(client, email='admin@test.com')
    res = client.post(
        '/api/admin/job-alerts/run',
        headers=auth_headers(admin_token),
        json={'dry_run': True, 'since_hours': 168},
    )
    assert res.status_code == 200
    assert res.get_json()['success'] is True
