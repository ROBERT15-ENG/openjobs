#!/usr/bin/env python3
"""
Seed a staging database with realistic demo data so the search, facets, company
profiles and alerts have something to show.

    python api/seed_demo.py [--db path/to/jobs.db] [--jobs 180] [--force]

Creates demo employer + seeker accounts (password: Demo1234!), ~180 job ads spread
across classifications, Australian cities, salary bands and the last 30 days, plus a
handful of company reviews and one saved-search alert. Idempotent: re-running does
nothing unless --force, which removes previously seeded demo data first.

Do NOT run against a production database.
"""
import argparse
import datetime
import os
import random
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash  # noqa: E402
from db_schema import init_db  # noqa: E402
from taxonomy import derive_state  # noqa: E402

DEMO_TAG = 'demo-seed'          # stored in jobs.video_url so demo rows can be identified/removed
DEMO_PASSWORD = 'Demo1234!'

COMPANIES = [
    ('Atlassian', 'Sydney NSW'), ('Canva', 'Sydney NSW'), ('Afterpay', 'Melbourne VIC'), ('REA Group', 'Richmond VIC'),
    ('Woolworths Group', 'Bella Vista NSW'), ('Telstra', 'Melbourne VIC'), ('Commonwealth Bank', 'Sydney NSW'),
    ('BHP', 'Perth WA'), ('Rio Tinto', 'Perth WA'), ('Qantas', 'Mascot NSW'), ('Ramsay Health Care', 'Brisbane QLD'),
    ('Bunnings', 'Hawthorn East VIC'), ('Flight Centre', 'Brisbane QLD'), ('Xero', 'Melbourne VIC'), ('Deloitte Australia', 'Sydney NSW'),
    ('SA Health', 'Adelaide SA'), ('Tasmanian Government', 'Hobart TAS'), ('ACT Government', 'Canberra ACT'), ('Territory Generation', 'Darwin NT'),
    ('Coles Group', 'Melbourne VIC'), ('Lendlease', 'Barangaroo NSW'), ('Domino\'s Pizza Enterprises', 'Brisbane QLD'),
    ('Culture Amp', 'Remote'), ('SafetyCulture', 'Sydney NSW'), ('Linktree', 'Melbourne VIC'),
]

LOCATIONS = ['Sydney NSW', 'North Sydney NSW', 'Parramatta NSW', 'Newcastle NSW', 'Melbourne VIC', 'Docklands VIC', 'Geelong VIC',
             'Brisbane QLD', 'Gold Coast QLD', 'Sunshine Coast QLD', 'Perth WA', 'Fremantle WA', 'Adelaide SA', 'Hobart TAS',
             'Canberra ACT', 'Darwin NT', 'Remote', 'Remote - Australia wide']

# classification -> [(title, subclassification, skills, salary_lo, salary_hi)]
ROLES = {
    'Information & Communication Technology': [
        ('Senior Python Developer', 'Developers/Programmers', 'Python, Django, PostgreSQL, AWS, Docker', 140000, 180000),
        ('Full Stack Engineer (React/Node)', 'Engineering - Software', 'React, TypeScript, Node.js, GraphQL', 120000, 160000),
        ('Data Engineer', 'Database Development & Administration', 'Python, Spark, Airflow, Snowflake, SQL', 130000, 170000),
        ('DevOps Engineer', 'Networks & Systems Administration', 'Kubernetes, Terraform, AWS, CI/CD, Linux', 135000, 175000),
        ('Cyber Security Analyst', 'Security', 'SIEM, Incident Response, ISO 27001, Splunk', 110000, 150000),
        ('IT Support Officer', 'Help Desk & IT Support', 'Windows, Office 365, Active Directory, ServiceNow', 65000, 80000),
        ('Product Manager', 'Product Management & Development', 'Roadmaps, Agile, Analytics, Stakeholder management', 140000, 185000),
        ('QA Automation Engineer', 'Testing & Quality Assurance', 'Playwright, Selenium, Python, CI', 100000, 130000),
        ('Business Analyst', 'Business/Systems Analysts', 'Requirements, UML, SQL, Jira, Agile', 105000, 135000),
        ('Machine Learning Engineer', 'Engineering - Software', 'Python, PyTorch, MLOps, LLMs, AWS', 150000, 200000),
    ],
    'Healthcare & Medical': [
        ('Registered Nurse - Emergency', 'Nursing - General', 'AHPRA registration, Triage, Patient care', 78000, 98000),
        ('Aged Care Registered Nurse', 'Aged Care Nursing', 'AHPRA, Aged care, Medication management', 75000, 92000),
        ('Physiotherapist', 'Physiotherapy', 'AHPRA, Musculoskeletal, Rehabilitation', 80000, 105000),
        ('Pharmacist', 'Pharmacy', 'AHPRA, Dispensing, Community pharmacy', 85000, 110000),
        ('Medical Receptionist', 'Medical Administration', 'Best Practice, Medicare billing, Customer service', 55000, 65000),
        ('Psychologist', 'Psychology & Counselling', 'AHPRA, CBT, Assessment, Telehealth', 95000, 130000),
    ],
    'Trades & Services': [
        ('Electrician', 'Electricians', 'A-Grade licence, Commercial, Fault finding', 85000, 110000),
        ('Plumber', 'Plumbers', 'Plumbing licence, Maintenance, Gas fitting', 80000, 105000),
        ('Carpenter', 'Carpentry & Cabinet Making', 'Framing, Fit-out, White card', 75000, 95000),
        ('Diesel Mechanic', 'Automotive Trades', 'Heavy vehicle, Diagnostics, Hydraulics', 90000, 120000),
        ('Commercial Cleaner', 'Cleaning Services', 'Police check, Reliability, Night shift', 50000, 60000),
    ],
    'Accounting': [
        ('Senior Accountant', 'Financial Accounting', 'CA/CPA, IFRS, Month-end, Xero', 100000, 130000),
        ('Accounts Payable Officer', 'Accounts Payable/Receivable', 'AP processing, Reconciliations, SAP', 65000, 78000),
        ('Payroll Officer', 'Payroll', 'Payroll, Awards, Superannuation, Chris21', 75000, 90000),
        ('Tax Accountant', 'Taxation', 'CA, Tax compliance, BAS, Trusts', 90000, 120000),
    ],
    'Sales': [
        ('Business Development Manager', 'New Business Development', 'B2B sales, Pipeline, Salesforce, Negotiation', 110000, 150000),
        ('Account Manager', 'Account & Relationship Management', 'Client management, Renewals, CRM', 90000, 120000),
        ('Sales Representative', 'Sales Representatives/Consultants', 'Retail, Customer service, Targets', 60000, 80000),
    ],
    'Marketing & Communications': [
        ('Digital Marketing Manager', 'Digital & Search Marketing', 'SEO, SEM, Google Ads, HubSpot, Analytics', 110000, 140000),
        ('Marketing Coordinator', 'Marketing Assistants/Coordinators', 'Content, Social media, Canva, Campaigns', 65000, 80000),
        ('Content Writer', 'Marketing Communications', 'Copywriting, SEO, CMS, Editing', 70000, 90000),
    ],
    'Administration & Office Support': [
        ('Executive Assistant', 'Personal Assistants', 'Diary management, Travel, Board papers', 85000, 105000),
        ('Office Administrator', 'Administrative Assistants', 'Reception, MS Office, Scheduling', 60000, 72000),
        ('Data Entry Officer', 'Data Entry', 'Accuracy, Excel, Typing 60wpm', 52000, 60000),
    ],
    'Engineering': [
        ('Civil Engineer', 'Civil/Structural Engineering', 'Civil design, 12d, AutoCAD, RPEQ', 100000, 140000),
        ('Mechanical Engineer', 'Mechanical Engineering', 'SolidWorks, FEA, Manufacturing', 95000, 130000),
        ('Electrical Engineer', 'Electrical/Electronic Engineering', 'Power systems, PLC, HV design', 105000, 145000),
        ('Project Engineer', 'Project Engineering', 'Project delivery, Scheduling, Contracts', 110000, 150000),
    ],
    'Construction': [
        ('Site Supervisor', 'Foreperson/Supervisors', 'Residential construction, WHS, Scheduling', 110000, 140000),
        ('Estimator', 'Estimating', 'Take-offs, Buildsoft, Tendering', 100000, 130000),
        ('Construction Project Manager', 'Project Management', 'Commercial construction, Contracts, Procore', 150000, 200000),
    ],
    'Hospitality & Tourism': [
        ('Head Chef', 'Chefs/Cooks', 'Menu design, Kitchen management, Food safety', 80000, 100000),
        ('Barista', 'Bar & Beverage Staff', 'Coffee, Customer service, Speed', 50000, 60000),
        ('Hotel Front Office Manager', 'Front Office & Guest Services', 'Opera PMS, Guest relations, Rostering', 70000, 85000),
    ],
    'Education & Training': [
        ('Primary School Teacher', 'Teaching - Primary', 'Teaching registration, Curriculum, Classroom management', 78000, 115000),
        ('Early Childhood Educator', 'Childcare & Outside School Hours Care', 'Diploma ECE, EYLF, First aid', 60000, 75000),
        ('Secondary Maths Teacher', 'Teaching - Secondary', 'Teaching registration, Mathematics, VCE/HSC', 80000, 118000),
    ],
    'Banking & Financial Services': [
        ('Financial Planner', 'Financial Planning', 'FASEA, Advice, Xplan, Compliance', 100000, 140000),
        ('Credit Analyst', 'Analysis & Reporting', 'Credit risk, Financial analysis, Excel', 85000, 110000),
        ('Mortgage Broker', 'Mortgages', 'Cert IV Finance, Lending, Client acquisition', 80000, 150000),
    ],
    'Human Resources & Recruitment': [
        ('HR Business Partner', 'Consulting & Generalist HR', 'ER/IR, Workday, Coaching, Change', 120000, 150000),
        ('Recruitment Consultant', 'Recruitment - Agency', 'Sourcing, LinkedIn Recruiter, Business development', 70000, 110000),
        ('WHS Advisor', 'Occupational Health & Safety', 'WHS legislation, Audits, Incident investigation', 95000, 120000),
    ],
    'Retail & Consumer Products': [
        ('Store Manager', 'Management - Store', 'Retail leadership, P&L, Visual merchandising', 65000, 85000),
        ('Retail Assistant', 'Retail Assistants', 'Customer service, POS, Stock', 48000, 58000),
    ],
    'Manufacturing, Transport & Logistics': [
        ('Warehouse Storeperson', 'Warehousing, Storage & Distribution', 'Forklift licence, RF scanning, Pick/pack', 55000, 65000),
        ('HC Truck Driver', 'Road Transport', 'HC licence, Linehaul, Fatigue management', 80000, 100000),
        ('Procurement Specialist', 'Purchasing, Procurement & Inventory', 'Sourcing, Contracts, SAP Ariba', 100000, 130000),
    ],
    'Legal': [
        ('Commercial Lawyer', 'Corporate & Commercial Law', 'Contracts, M&A, Admitted in Australia', 130000, 190000),
        ('Paralegal', 'Law Clerks & Paralegals', 'Legal research, Document management, Litigation support', 65000, 85000),
    ],
    'Design & Architecture': [
        ('UX/UI Designer', 'UX/UI Design', 'Figma, Design systems, User research, Prototyping', 110000, 145000),
        ('Architect', 'Architecture', 'Revit, Registration, Residential/Commercial', 95000, 130000),
        ('Graphic Designer', 'Graphic Design', 'Adobe CC, Branding, Print & digital', 65000, 85000),
    ],
    'Mining, Resources & Energy': [
        ('Mining Engineer', 'Mining - Engineering & Maintenance', 'Mine planning, Deswik, FIFO', 150000, 210000),
        ('Plant Operator (FIFO)', 'Mining - Operations', 'Heavy machinery, FIFO 2:1, Safety', 110000, 140000),
    ],
    'Call Centre & Customer Service': [
        ('Customer Service Consultant', 'Customer Service - Call Centre', 'Inbound calls, CRM, Problem solving', 55000, 68000),
        ('Team Leader - Contact Centre', 'Supervisors/Team Leaders', 'Coaching, KPIs, Workforce planning', 80000, 95000),
    ],
    'Community Services & Development': [
        ('Disability Support Worker', 'Aged & Disability Support', 'NDIS, Cert III, Manual handling', 55000, 70000),
        ('Case Manager', 'Housing & Homelessness', 'Case management, Trauma-informed, Reporting', 80000, 95000),
    ],
    'Government & Defence': [
        ('Policy Officer (APS6)', 'Policy, Planning & Regulation', 'Policy analysis, Briefings, Stakeholder engagement', 95000, 108000),
        ('Compliance Officer', 'Government - State', 'Regulation, Investigations, Report writing', 85000, 100000),
    ],
}

WORK_TYPES = ['full_time'] * 6 + ['part_time', 'contract', 'contract', 'casual', 'internship']
ARRANGEMENTS = ['onsite'] * 5 + ['hybrid'] * 4 + ['remote'] * 2

DESCRIPTION = """About the role
{company} is looking for a {title} to join our {team} team in {location}. You will {duty1}, {duty2} and {duty3}, working closely with a supportive and experienced group of colleagues.

What you'll bring
- Demonstrated experience in a similar {title_lower} role
- Strong skills across {skills}
- Excellent communication and a collaborative, can-do attitude
- {extra}

What we offer
- {salary_text}
- {perk1}
- {perk2}
- Genuine career progression and learning budget

{company} is an equal opportunity employer. Applications close in 30 days — apply now with your resume and a short cover note."""

DUTIES = ['own key deliverables end to end', 'partner with stakeholders across the business', 'drive continuous improvement',
          'mentor junior team members', 'contribute to planning and reporting', 'deliver high-quality outcomes on time',
          'keep safety and compliance front of mind', 'help shape how the team works']
PERKS = ['Flexible / hybrid working arrangements', 'Additional leave and wellbeing days', 'Salary packaging and novated leasing',
         'Paid parental leave (18 weeks)', 'Employee share plan', 'Free onsite parking', 'Health insurance discounts',
         'Modern CBD office close to public transport', 'Tools of trade and vehicle allowance']
EXTRAS = ['Full Australian working rights', 'Relevant tertiary qualification or equivalent experience', 'Current driver\'s licence',
          'Ability to obtain a National Police Check', 'Experience in a fast-paced environment']
TEAMS = ['Technology', 'Operations', 'Customer', 'People & Culture', 'Finance', 'Growth', 'Delivery', 'Clinical', 'Projects']

REVIEWS = [
    (5, 'Great culture and genuine flexibility', 'Supportive leaders, real hybrid working and interesting problems to solve.', 'Can be a lot going on at once during peak periods.'),
    (4, 'Good place to grow your career', 'Plenty of internal mobility and training budget. Pay is fair for the market.', 'Some legacy systems slow things down.'),
    (3, 'Solid but very corporate', 'Stable, good benefits, nice offices.', 'Decisions take time and there are many layers of approval.'),
    (4, 'Friendly team, decent pay', 'The people are the best part. Managers listen.', 'Parking is expensive and the commute is long.'),
    (2, 'High workload, low recognition', 'Learned a lot quickly.', 'Understaffed teams and unrealistic deadlines at times.'),
    (5, 'Best employer I have had', 'Transparent leadership, excellent onboarding, strong values that are lived day to day.', 'Not much — occasional travel required.'),
]


def _connect(path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def already_seeded(con) -> bool:
    return con.execute("SELECT 1 FROM jobs WHERE video_url = ? LIMIT 1", (DEMO_TAG,)).fetchone() is not None


def remove_demo(con):
    ids = [r[0] for r in con.execute("SELECT id FROM users WHERE email LIKE '%@demo.openjobs.local'")]
    if ids:
        ph = ','.join('?' * len(ids))
        con.execute(f"DELETE FROM job_alerts WHERE user_id IN ({ph})", ids)
        con.execute(f"DELETE FROM company_reviews WHERE user_id IN ({ph})", ids)
        con.execute(f"DELETE FROM saved_jobs WHERE user_id IN ({ph})", ids)
        con.execute(f"DELETE FROM applications WHERE user_id IN ({ph})", ids)
    con.execute("DELETE FROM applications WHERE job_id IN (SELECT id FROM jobs WHERE video_url = ?)", (DEMO_TAG,))
    con.execute("DELETE FROM saved_jobs WHERE job_id IN (SELECT id FROM jobs WHERE video_url = ?)", (DEMO_TAG,))
    con.execute("DELETE FROM jobs WHERE video_url = ?", (DEMO_TAG,))
    con.execute("DELETE FROM users WHERE email LIKE '%@demo.openjobs.local'")
    con.commit()


def _user(con, name, email, role, company=None):
    row = con.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if row:
        return row['id']
    cur = con.execute(
        "INSERT INTO users (name, email, password_hash, role, email_confirmed, company, created_at) VALUES (?,?,?,?,1,?,?)",
        (name, email, generate_password_hash(DEMO_PASSWORD), role, company, datetime.datetime.now().isoformat()))
    return cur.lastrowid


def seed(db_path, n_jobs=180, seed=42):
    random.seed(seed)
    init_db(db_path)
    con = _connect(db_path)
    try:
        employers = {}
        for i, (company, hq) in enumerate(COMPANIES):
            slug = ''.join(ch for ch in company.lower() if ch.isalnum())
            employers[company] = _user(con, f"{company} Talent Team", f"employer.{slug}@demo.openjobs.local", 'employer', company)
        seeker_id = _user(con, 'Demo Seeker', 'seeker@demo.openjobs.local', 'user')

        now = datetime.datetime.now()
        pool = [(cls, role) for cls, roles in ROLES.items() for role in roles]
        created = 0
        for i in range(n_jobs):
            cls, (title, sub, skills, lo, hi) = random.choice(pool)
            company, hq = random.choice(COMPANIES)
            location = hq if random.random() < 0.5 else random.choice(LOCATIONS)
            arrangement = 'remote' if 'Remote' in location else random.choice(ARRANGEMENTS)
            work_type = random.choice(WORK_TYPES)
            jitter = random.uniform(0.9, 1.1)
            salary_min, salary_max = int(lo * jitter // 1000 * 1000), int(hi * jitter // 1000 * 1000)
            if work_type in ('casual', 'internship') and random.random() < 0.6:
                salary_min = salary_max = None
            # bias towards recent ads so "Listed" facets look alive
            age_days = random.choice([0, 0, 1, 1, 2, 3, 4, 5, 6, 8, 10, 13, 16, 20, 24, 28])
            created_at = (now - datetime.timedelta(days=age_days, hours=random.randint(0, 23), minutes=random.randint(0, 59))).isoformat()
            salary_text = (f"AUD {salary_min:,} – {salary_max:,} + super" if salary_min else 'Competitive hourly rate + super')
            duties = random.sample(DUTIES, 3)
            perks = random.sample(PERKS, 2)
            description = DESCRIPTION.format(
                company=company, title=title, title_lower=title.lower(), team=random.choice(TEAMS), location=location,
                duty1=duties[0], duty2=duties[1], duty3=duties[2], skills=skills, extra=random.choice(EXTRAS),
                salary_text=salary_text, perk1=perks[0], perk2=perks[1])
            con.execute(
                """INSERT INTO jobs (title, company, location, state, description, salary, salary_min, salary_max, salary_currency,
                       category, classification, subclassification, work_type, work_arrangement, skills, search_summary,
                       selling_points, video_url, is_active, is_featured, created_at, expires_at, employer_id, view_count, application_count)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?,?,?,?)""",
                (title, company, location, derive_state(location), description, salary_text if salary_min else '', salary_min, salary_max, 'AUD',
                 cls, cls, sub, work_type, arrangement, skills,
                 f"{title} at {company}, {location}. {salary_text}. {skills}."[:300],
                 '["' + '","'.join(perks) + '"]', DEMO_TAG, 1 if random.random() < 0.08 else 0, created_at,
                 (now + datetime.timedelta(days=30 - age_days)).isoformat(), employers[company],
                 random.randint(5, 900), random.randint(0, 40)))
            created += 1

        # company reviews (one per demo reviewer per company)
        reviewers = [_user(con, f"Reviewer {i}", f"reviewer{i}@demo.openjobs.local", 'user') for i in range(1, 7)]
        for company, _ in COMPANIES:
            for uid in random.sample(reviewers, random.randint(0, 4)):
                rating, title, pros, cons = random.choice(REVIEWS)
                con.execute(
                    """INSERT OR IGNORE INTO company_reviews (company, user_id, rating, title, pros, cons, role, is_current, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (company, uid, rating, title, pros, cons, random.choice(['Engineer', 'Analyst', 'Manager', 'Consultant', 'Coordinator']),
                     random.randint(0, 1), (now - datetime.timedelta(days=random.randint(5, 400))).isoformat()))
            avg = con.execute("SELECT AVG(rating) FROM company_reviews WHERE company = ?", (company,)).fetchone()[0]
            if avg:
                con.execute("UPDATE jobs SET company_rating = ? WHERE company = ?", (round(avg, 1), company))

        con.execute(
            """INSERT INTO job_alerts (user_id, name, keywords, location, frequency, is_active, created_at)
               VALUES (?, 'Python jobs in Sydney', 'python', 'Sydney', 'daily', 1, ?)""", (seeker_id, now.isoformat()))
        con.commit()
        return created
    finally:
        con.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Seed demo data for staging')
    ap.add_argument('--db', default=os.environ.get('DATABASE_URL', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'jobs.db')))
    ap.add_argument('--jobs', type=int, default=180)
    ap.add_argument('--force', action='store_true', help='remove previously seeded demo data first')
    a = ap.parse_args()
    init_db(a.db)
    con = _connect(a.db)
    if already_seeded(con):
        if not a.force:
            print('[seed] demo data already present — use --force to reseed')
            con.close()
            sys.exit(0)
        remove_demo(con)
        print('[seed] removed previous demo data')
    con.close()
    n = seed(a.db, a.jobs)
    print(f"[seed] created {n} jobs across {len(COMPANIES)} companies")
    print(f"[seed] demo logins (password {DEMO_PASSWORD}): seeker@demo.openjobs.local, employer.atlassian@demo.openjobs.local, ...")
