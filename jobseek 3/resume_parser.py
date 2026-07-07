"""
Resume Parser - Extract text from PDF/DOCX resumes
"""
import re
import json
from datetime import datetime

try:
    import PyPDF2
except:
    PyPDF2 = None

try:
    import pdfplumber
except:
    pdfplumber = None

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    text = ""
    
    if pdfplumber:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        except:
            pass
    
    if PyPDF2:
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
            return text
        except:
            pass
    
    return text

def parse_resume(text):
    """Parse resume text into structured data"""
    data = {
        'name': None,
        'email': None,
        'phone': None,
        'skills': [],
        'experience': [],
        'education': [],
        'summary': None
    }
    
    # Extract email
    email_match = re.search(r'[\w.-]+@[\w.-]+\.\w+', text)
    if email_match:
        data['email'] = email_match.group()
    
    # Extract phone
    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    if phone_match:
        data['phone'] = phone_match.group()
    
    # Extract skills (common tech skills)
    skill_keywords = [
        'Python', 'JavaScript', 'Java', 'C++', 'C#', 'Ruby', 'Go', 'Rust',
        'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring',
        'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Terraform',
        'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis',
        'Git', 'CI/CD', 'Jira', 'Agile', 'Scrum',
        'Machine Learning', 'AI', 'Data Science', 'TensorFlow', 'PyTorch',
        'HTML', 'CSS', 'REST', 'GraphQL', 'Linux', 'Bash'
    ]
    
    text_lower = text.lower()
    for skill in skill_keywords:
        if skill.lower() in text_lower:
            data['skills'].append(skill)
    
    # Extract name (usually at top)
    lines = text.split('\n')
    for line in lines[:5]:
        line = line.strip()
        if line and len(line) > 2 and len(line) < 50:
            if not('@' in line or 'http' in line or any(c.isdigit() for c in line)):
                if data['name'] is None:
                    data['name'] = line.title()
    
    # Extract summary (look for summary/objective section)
    summary_patterns = [
        r'summary[:\n](.{100,500})',
        r'objective[:\n](.{100,500})',
        r'profile[:\n](.{100,500})'
    ]
    for pattern in summary_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['summary'] = match.group(1).strip()[:500]
            break
    
    return data

def calculate_ats_score(resume_data, job_requirements):
    """
    Calculate ATS compatibility score
    job_requirements: list of required skills
    """
    if not resume_data.get('skills'):
        return 0
    
    resume_skills = [s.lower() for s in resume_data['skills']]
    required = [r.lower() for r in job_requirements]
    
    matches = sum(1 for r in required if any(r in s or s in r for s in resume_skills))
    
    if not required:
        return 50
    
    score = int((matches / len(required)) * 100)
    return min(score, 100)

# API endpoints for resume parsing
if __name__ == "__main__":
    # Test
    print("Resume Parser Module Ready")
    print("Functions:")
    print("  - extract_text_from_pdf(file_path)")
    print("  - parse_resume(text)")
    print("  - calculate_ats_score(resume_data, job_requirements)")
