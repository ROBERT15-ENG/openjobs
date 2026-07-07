#!/usr/bin/env python3
"""
AI Job Filter using Ollama
Analyzes and scores jobs with local AI
"""

import requests
import json
import os
from typing import Dict, List

OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')

DATA_DIR = "/Users/agentx/.openclaw/workspace/spyder-trader/jobseek/data"

def query_ollama(prompt: str, system: str = None) -> str:
    """Query Ollama for completion"""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }
    if system:
        payload["system"] = system
    
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.json().get('response', '')
    except Exception as e:
        print(f"Ollama error: {e}")
    return ""

def analyze_job(job: Dict) -> Dict:
    """Analyze a job using AI"""
    text = f"""
Job: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}
Description: {job.get('description', '')[:300]}
"""
    
    prompt = f"""Analyze this job. Return JSON with:
- is_remote: true/false (check for remote, work from home, WFH)
- is_visa: true/false (check for visa, sponsorship, relocation, work permit)
- salary: salary if mentioned, else "Not specified"
- skills: key skills as comma list
- score: 1-100 quality score
- warning: any red flags

{text}

Return ONLY valid JSON:"""

    result = query_ollama(prompt)
    
    # Parse JSON from result
    try:
        # Extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    
    return fallback_analyze(job)

def fallback_analyze(job: Dict) -> Dict:
    """Keyword-based fallback"""
    text = (f"{job.get('title', '')} {job.get('description', '')}").lower()
    
    remote_kw = ['remote', 'work from home', 'wfh', 'flexible', 'telecommute', 'home based']
    visa_kw = ['visa', 'sponsorship', 'relocation', 'work permit', 'h1b', 'permit', 'relocate']
    scam_kw = ['urgent', 'easy money', 'no experience', 'guaranteed', 'cash', 'envelope', 'wire']
    
    is_remote = any(k in text for k in remote_kw)
    is_visa = any(k in text for k in visa_kw)
    is_scam = any(k in text for k in scam_kw)
    
    salary = "Not specified"
    if '$' in text:
        salary = "Salary mentioned"
    
    score = 50
    if is_remote: score += 15
    if is_visa: score += 20
    if is_scam: score -= 40
    if len(job.get('description', '')) > 100: score += 10
    
    return {
        'is_remote': is_remote,
        'is_visa': is_visa,
        'salary': salary,
        'skills': [],
        'score': min(100, max(10, score)),
        'warning': 'Scam warning' if is_scam else ''
    }

def filter_jobs(jobs: List[Dict]) -> List[Dict]:
    """Filter and score all jobs with AI"""
    filtered = []
    
    for job in jobs:
        analysis = analyze_job(job)
        job.update({
            'is_remote': analysis.get('is_remote', False),
            'is_visa': analysis.get('is_visa', False),
            'salary': analysis.get('salary', 'Not specified'),
            'ai_score': analysis.get('score', 50),
            'warning': analysis.get('warning', '')
        })
        
        # Filter scams and low scores
        if analysis.get('warning') or job.get('ai_score', 0) < 30:
            continue
        
        filtered.append(job)
    
    filtered.sort(key=lambda x: x.get('ai_score', 0), reverse=True)
    return filtered

def save_filtered(jobs: List[Dict], filename="ai_filtered_jobs.json"):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w') as f:
        json.dump(jobs, f, indent=2)
    print(f"💾 Saved {len(jobs)} AI-filtered jobs to {path}")
    return path

if __name__ == "__main__":
    # Test
    test_job = {
        'title': 'Remote Software Engineer',
        'company': 'TechCorp',
        'location': 'Remote (Work from Home)',
        'description': 'We are hiring a software engineer. Visa sponsorship available. $80k-120k salary.',
    }
    result = analyze_job(test_job)
    print("Test analysis:", json.dumps(result, indent=2))