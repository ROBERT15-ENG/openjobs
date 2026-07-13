#!/usr/bin/env python3
"""
AI-Powered Job Matching using Ollama
- Resume parsing
- Skill gap analysis  
- Semantic job matching

NOTE: Ollama is only called when user explicitly uses AI features.
Set JOBSEEK_AI_ENABLED=false to disable all AI features.
"""

import json
import re
import requests
import os
import sqlite3
from typing import Dict, List, Optional

# DB path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(PROJECT_ROOT, 'jobs.db'))

# Only load these when AI is actually needed
AI_ENABLED = os.environ.get('JOBSEEK_AI_ENABLED', 'true').lower() == 'true'

# Ollama endpoint - only configure if AI enabled
if AI_ENABLED:
    OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://127.0.0.1:11434/api/generate')
    DEFAULT_MODEL = os.environ.get('OLLAMA_MODEL', 'gemma3:4b')


def track_ai_usage(endpoint: str, prompt: str, response: str, model: str):
    """Track AI usage to database"""
    try:
        prompt_tokens = len(prompt) // 4
        response_tokens = len(response) // 4
        total_tokens = prompt_tokens + response_tokens
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO ai_usage (endpoint, tokens_used, model) VALUES (?, ?, ?)",
                    (endpoint, total_tokens, model))
        conn.commit()
        conn.close()
    except:
        pass


def is_ollama_running():
    """Check if Ollama is available"""
    if not AI_ENABLED:
        return False
    try:
        resp = requests.get(f"{OLLAMA_URL.replace('/api/generate', '')}/api/tags", timeout=2)
        return resp.status_code == 200
    except:
        return False


def call_ollama(prompt: str, model: str = None, endpoint: str = 'general') -> str:
    """Call Ollama for AI processing"""
    if not AI_ENABLED:
        return json.dumps({"error": "AI disabled"})
    
    if model is None:
        model = DEFAULT_MODEL
        
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": model,
            "prompt": prompt,
            "stream": False
        }, timeout=60)
        result = resp.json().get("response", "")
        track_ai_usage(endpoint, prompt, result, model)
        return result
    except Exception as e:
        return f"Error: {e}"

def parse_resume(resume_text: str) -> Dict:
    """Parse resume using Ollama - extract skills, experience, education"""
    
    prompt = f"""Parse this resume and extract structured information.
Return ONLY valid JSON (no markdown, no explanation):

{{
  "name": "extracted name or null",
  "email": "extracted email or null", 
  "phone": "extracted phone or null",
  "skills": ["skill1", "skill2", ...],
  "experience_years": number or null,
  "job_titles": ["title1", "title2"],
  "education": "degree level or null",
  "summary": "2-3 sentence career summary"
}}

Resume:
{resume_text[:2000]}
"""
    
    result = call_ollama(prompt)
    
    # Clean JSON from response
    try:
        # Find JSON in response
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    
    # Fallback: basic parsing
    return {
        "skills": extract_skills(resume_text),
        "experience_years": estimate_experience(resume_text),
        "summary": ""
    }

def extract_skills(text: str) -> List[str]:
    """Basic skill extraction fallback"""
    skill_keywords = [
        "python", "javascript", "java", "golang", "rust", "c++", "c#", "ruby",
        "php", "swift", "kotlin", "typescript", "scala", "r", "matlab",
        "react", "vue", "angular", "node", "django", "flask", "fastapi",
        "aws", "gcp", "azure", "docker", "kubernetes", "terraform",
        "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
        "machine learning", "deep learning", "tensorflow", "pytorch", "keras",
        "nlp", "computer vision", "data science", "data analysis", "analytics",
        "git", "linux", "bash", "ci/cd", "jenkins", "jira",
        "figma", "sketch", "adobe", "photoshop", "illustrator",
        "product", "agile", "scrum", "project management",
        "communication", "leadership", "teamwork"
    ]
    
    text_lower = text.lower()
    found = [s for s in skill_keywords if s in text_lower]
    return list(set(found))[:15]

def estimate_experience(text: str) -> Optional[int]:
    """Estimate years of experience from text"""
    patterns = [
        r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
        r'(\d+)\+?\s*years?\s*(?:in|of|with)',
        r'experience\s*(?:of|in|with)\s*(\d+)\+?'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))
    return None

def analyze_skill_gap(user_skills: List[str], job_skills: List[str]) -> Dict:
    """Analyze skill gaps between user and job requirements"""
    
    user_skills_set = set(s.lower() for s in user_skills)
    job_skills_set = set(s.lower() for s in job_skills)
    
    matched = user_skills_set & job_skills_set
    missing = job_skills_set - user_skills_set
    extra = user_skills_set - job_skills_set
    
    match_percent = len(matched) / len(job_skills_set) * 100 if job_skills_set else 0
    
    return {
        "matched_skills": list(matched),
        "missing_skills": list(missing),
        "user_extra_skills": list(extra),
        "match_percentage": round(match_percent, 1),
        "gap_score": len(missing)  # Lower is better
    }

def semantic_job_match(user_profile: Dict, job: Dict) -> Dict:
    """Use Ollama for deep semantic matching"""
    
    prompt = f"""Analyze how well this candidate fits this job.
Consider: skills match, experience match, location fit, remote preference.

Candidate Profile:
- Skills: {', '.join(user_profile.get('skills', []))}
- Experience: {user_profile.get('experience_years', 'N/A')} years
- Preferred Location: {user_profile.get('preferred_location', 'Any')}
- Visa Required: {user_profile.get('visa_required', False)}

Job:
- Title: {job.get('title')}
- Company: {job.get('company')}
- Location: {job.get('location')}
- Required Skills: {job.get('skills')}
- Remote: {job.get('is_remote')}
- Visa Sponsorship: {job.get('is_visa')}

Return ONLY valid JSON:
{{
  "match_score": 0-100,
  "strengths": ["point1", "point2"],
  "weaknesses": ["point1"],
  "recommendation": "strong_match|good_match|poor_match"
}}
"""
    
    result = call_ollama(prompt, endpoint='career_advice')
    
    try:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    
    # Fallback to basic matching
    gap = analyze_skill_gap(user_profile.get('skills', []), job.get('skills', '').split(','))
    score = gap['match_percentage']
    
    return {
        "match_score": score,
        "strengths": gap['matched_skills'],
        "weaknesses": gap['missing_skills'],
        "recommendation": "strong_match" if score > 70 else "good_match" if score > 40 else "poor_match"
    }

def get_career_advice(user_skills: List[str], target_role: str) -> Dict:
    """Get AI career advice for skill development"""
    
    prompt = f"""Provide career advice for someone wanting to become a {target_role}.
Current skills: {', '.join(user_skills)}

Return ONLY valid JSON:
{{
  "skill_gaps": ["skill1", "skill2"],
  "learning_resources": ["resource1", "resource2"],
  "certifications": ["cert1"],
  "experience_advice": "advice text",
  "timeline_months": number
}}
"""
    
    result = call_ollama(prompt, endpoint='career_advice')
    
    try:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    
    return {"error": "Could not generate advice"}

# CLI test
if __name__ == "__main__":
    # Test resume parsing
    test_resume = """
    John Doe
    Email: john.doe@email.com
    Phone: +254712345678
    
    Skills: Python, JavaScript, React, Node.js, AWS, Docker, PostgreSQL
    5 years experience in software development
    Worked at Google and Amazon
    Bachelor's degree in Computer Science
    """
    
    print("Testing resume parsing...")
    parsed = parse_resume(test_resume)
    print(json.dumps(parsed, indent=2))
    
    print("\nTesting skill gap analysis...")
    gap = analyze_skill_gap(
        ["python", "javascript", "react", "aws", "docker"],
        ["python", "javascript", "react", "aws", "docker", "kubernetes", "golang"]
    )
    print(json.dumps(gap, indent=2))