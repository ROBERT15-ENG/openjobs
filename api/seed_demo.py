#!/usr/bin/env python3
"""
Seed a staging database with realistic demo data so the search, facets, company
profiles and alerts have something to show.

    python api/seed_demo.py [--db path/to/jobs.db] [--jobs 180] [--force]

Creates demo employer + seeker accounts (password: Demo1234!), ~180 job ads spread
across classifications, Kenyan towns/counties, KES monthly salary bands and the last 30 days, plus a
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
    ('Safaricom', 'Westlands, Nairobi'), ('Equity Bank', 'Upper Hill, Nairobi'), ('KCB Group', 'Nairobi CBD'), ('M-KOPA', 'Kilimani, Nairobi'),
    ('Twiga Foods', 'Industrial Area, Nairobi'), ('Kenya Airways', 'Embakasi, Nairobi'), ('Britam', 'Upper Hill, Nairobi'),
    ('Jumia Kenya', 'Westlands, Nairobi'), ('Nation Media Group', 'Nairobi CBD'), ('East African Breweries (EABL)', 'Ruaraka, Nairobi'),
    ('Co-operative Bank of Kenya', 'Nairobi CBD'), ('Cellulant', 'Westlands, Nairobi'), ('Kenya Power (KPLC)', 'Nairobi'),
    ('Aga Khan University Hospital', 'Parklands, Nairobi'), ('Naivas Supermarkets', 'Nairobi'), ('Carrefour Kenya (Majid Al Futtaim)', 'Karen, Nairobi'),
    ('Bamburi Cement', 'Mombasa'), ('Kenya Ports Authority', 'Mombasa'), ('Serena Hotels', 'Nyali, Mombasa'), ('Kisumu County Government', 'Kisumu'),
    ('James Finlay Kenya', 'Kericho'), ('Kakuzi PLC', 'Thika, Kiambu'), ('Oserian Development Company', 'Naivasha, Nakuru'),
    ('Moi Teaching & Referral Hospital', 'Eldoret'), ('Kenya Red Cross Society', 'South C, Nairobi'), ('Amref Health Africa', 'Lang\'ata, Nairobi'),
    ('BURN Manufacturing', 'Ruiru, Kiambu'), ('Sanergy', 'Mukuru, Nairobi'), ('Andela', 'Remote'), ('Ajua', 'Remote'),
]

# What each employer mostly hires for (a minority of ads still fall outside, like real boards)
ICT, BANK, HEALTH, NGO, AGRI, MFG, HOSP, RETAIL, SALES, MKT, ACC, ADMIN, ENG, ENERGY, GOV, EDU, CS = (
    'Information & Communication Technology', 'Banking & Financial Services', 'Healthcare & Medical',
    'NGO, Development & Humanitarian', 'Agriculture, Animals & Conservation', 'Manufacturing, Transport & Logistics',
    'Hospitality & Tourism', 'Retail & Consumer Products', 'Sales', 'Marketing & Communications', 'Accounting',
    'Administration & Office Support', 'Engineering', 'Energy, Oil & Gas', 'Government & Public Sector',
    'Education & Training', 'Call Centre & Customer Service')
COMPANY_FOCUS = {
    'Safaricom': [ICT, BANK, MKT, CS, SALES], 'Equity Bank': [BANK, ACC, ICT, CS], 'KCB Group': [BANK, ACC, ICT, 'Legal'],
    'M-KOPA': [ICT, SALES, BANK, CS], 'Twiga Foods': [MFG, AGRI, SALES, ICT], 'Kenya Airways': [HOSP, ENG, CS, ACC],
    'Britam': ['Insurance', BANK, SALES, ACC], 'Jumia Kenya': [ICT, MFG, MKT, CS], 'Nation Media Group': ['Advertising, Arts & Media', MKT, SALES, ICT],
    'East African Breweries (EABL)': [MFG, SALES, MKT, ENG], 'Co-operative Bank of Kenya': [BANK, ACC, ICT, CS], 'Cellulant': [ICT, BANK, SALES],
    'Kenya Power (KPLC)': [ENERGY, ENG, 'Trades & Services', CS], 'Aga Khan University Hospital': [HEALTH, ADMIN, ACC],
    'Naivas Supermarkets': [RETAIL, MFG, 'Security & Protective Services', ACC], 'Carrefour Kenya (Majid Al Futtaim)': [RETAIL, MFG, MKT],
    'Bamburi Cement': [MFG, ENG, SALES, ENERGY], 'Kenya Ports Authority': [MFG, ENG, GOV, 'Security & Protective Services'],
    'Serena Hotels': [HOSP, SALES, ADMIN], 'Kisumu County Government': [GOV, HEALTH, EDU, ADMIN], 'James Finlay Kenya': [AGRI, MFG, ACC],
    'Kakuzi PLC': [AGRI, MFG, ACC], 'Oserian Development Company': [AGRI, MFG, ENG], 'Moi Teaching & Referral Hospital': [HEALTH, ADMIN, GOV],
    'Kenya Red Cross Society': [NGO, HEALTH, 'Community & Social Services', ADMIN], 'Amref Health Africa': [NGO, HEALTH, ACC, MKT],
    'BURN Manufacturing': [MFG, ENG, SALES, ENERGY], 'Sanergy': [NGO, MFG, ENG, AGRI], 'Andela': [ICT, 'Human Resources & Recruitment'], 'Ajua': [ICT, MKT, CS],
}

LOCATIONS = ['Nairobi CBD', 'Westlands, Nairobi', 'Upper Hill, Nairobi', 'Kilimani, Nairobi', 'Karen, Nairobi', 'Industrial Area, Nairobi',
             'Thika, Kiambu', 'Ruiru, Kiambu', 'Athi River, Machakos', 'Kitengela, Kajiado', 'Mombasa', 'Nyali, Mombasa', 'Malindi, Kilifi',
             'Diani, Kwale', 'Kisumu', 'Nakuru', 'Naivasha, Nakuru', 'Eldoret', 'Kericho', 'Nyeri', 'Meru', 'Kakamega', 'Kitale',
             'Nanyuki, Laikipia', 'Machakos', 'Garissa', 'Kakuma, Turkana', 'Remote', 'Remote - Kenya wide', 'Kampala, Uganda']

# classification -> [(title, subclassification, skills, monthly KES lo, hi)]
ROLES = {
    'Information & Communication Technology': [
        ('Senior Python Developer', 'Developers/Programmers', 'Python, Django, PostgreSQL, AWS, Docker', 250000, 400000),
        ('Full Stack Engineer (React/Node)', 'Engineering - Software', 'React, TypeScript, Node.js, GraphQL', 180000, 320000),
        ('Data Analyst', 'Data Science & Analytics', 'SQL, Power BI, Python, Excel, Dashboards', 90000, 160000),
        ('DevOps Engineer', 'Networks & Systems Administration', 'Kubernetes, Terraform, AWS, CI/CD, Linux', 200000, 350000),
        ('Cyber Security Analyst', 'Security', 'SIEM, Incident Response, ISO 27001, CEH', 150000, 280000),
        ('IT Support Technician', 'Help Desk & IT Support', 'Windows, Office 365, Active Directory, Networking', 45000, 80000),
        ('Product Manager', 'Product Management & Development', 'Roadmaps, Agile, Analytics, Stakeholder management', 220000, 400000),
        ('Mobile Money Integration Engineer', 'Mobile & Payments Development', 'M-Pesa Daraja API, REST, Java, Payments, USSD', 180000, 320000),
        ('Android Developer', 'Mobile & Payments Development', 'Kotlin, Android SDK, REST, Firebase', 150000, 280000),
        ('QA Engineer', 'Testing & Quality Assurance', 'Selenium, Postman, Test plans, JIRA', 90000, 170000),
        ('Business Analyst', 'Business/Systems Analysts', 'Requirements, UML, SQL, Jira, Agile', 120000, 220000),
        ('Machine Learning Engineer', 'Engineering - Software', 'Python, PyTorch, MLOps, LLMs, AWS', 250000, 450000),
    ],
    'Healthcare & Medical': [
        ('Registered Nurse (KRCHN)', 'Nursing', 'Nursing Council of Kenya licence, Triage, Patient care', 45000, 90000),
        ('Clinical Officer', 'Clinical Officers', 'COC registration, Outpatient care, Minor procedures', 50000, 95000),
        ('Medical Officer', 'Medical Officers & Doctors', 'KMPDC licence, Internship completed, Emergency care', 150000, 280000),
        ('Pharmaceutical Technologist', 'Pharmacy', 'PPB registration, Dispensing, Inventory', 40000, 75000),
        ('Laboratory Technologist', 'Laboratory & Diagnostics', 'KMLTTB registration, Haematology, Quality control', 45000, 85000),
        ('Community Health Officer', 'Community Health', 'Community mobilisation, Health education, Reporting', 40000, 70000),
        ('Medical Records Officer', 'Medical Administration', 'HMIS, Data entry, Filing, Confidentiality', 35000, 60000),
        ('Nutritionist', 'Nutrition & Dietetics', 'KNDI registration, Clinical nutrition, Counselling', 45000, 80000),
    ],
    'NGO, Development & Humanitarian': [
        ('Programme Manager', 'Programme/Project Management', 'Programme design, Donor reporting, Budgets, Logframes', 250000, 450000),
        ('Monitoring & Evaluation Officer', 'Monitoring, Evaluation & Learning (MEL)', 'M&E frameworks, Data collection, Kobo, Reporting', 120000, 220000),
        ('Grants & Partnerships Officer', 'Grants & Fundraising', 'Proposal writing, Donor compliance, USAID/EU rules', 130000, 230000),
        ('Field Officer - WASH', 'Humanitarian & Emergency Response', 'WASH, Community engagement, Field reporting', 70000, 120000),
        ('Protection Officer (Refugee Camp)', 'Refugee & Migration Services', 'Protection principles, Case management, Field work', 110000, 190000),
        ('Advocacy & Communications Officer', 'Advocacy & Policy', 'Policy briefs, Media relations, Campaigns', 120000, 200000),
    ],
    'Banking & Financial Services': [
        ('Relationship Manager - SME Banking', 'Banking - Retail', 'SME lending, Portfolio growth, Credit appraisal', 150000, 280000),
        ('Credit Analyst', 'Credit & Lending', 'Credit risk, Financial analysis, Excel', 90000, 160000),
        ('Mobile Money Product Lead', 'Mobile Money & Fintech', 'Mobile payments, Product strategy, Partnerships, Agent networks', 250000, 450000),
        ('Loan Officer (Microfinance)', 'Microfinance & SACCOs', 'Group lending, Field collections, Client onboarding', 40000, 80000),
        ('Compliance Officer', 'Compliance & Risk', 'AML/CFT, CBK prudential guidelines, Reporting', 120000, 220000),
        ('Bank Teller', 'Banking - Retail', 'Cash handling, Customer service, Core banking', 40000, 65000),
    ],
    'Trades & Services': [
        ('Electrician', 'Electricians', 'EPRA licence, Commercial wiring, Fault finding', 40000, 80000),
        ('Plumber', 'Plumbers', 'Plumbing certificate, Maintenance, Installations', 35000, 70000),
        ('Motor Vehicle Mechanic', 'Mechanics & Auto Technicians', 'Diagnostics, Toyota/Isuzu, Fleet servicing', 40000, 85000),
        ('Solar PV Installer', 'Solar & Electrical Installers', 'EPRA T3 licence, Solar design, Installation', 45000, 90000),
        ('Welder & Fabricator', 'Welders & Fabricators', 'Arc/MIG welding, Fabrication drawings, Safety', 35000, 70000),
        ('Housekeeper', 'Cleaning & Domestic Services', 'Cleaning, Laundry, Reliability, References', 18000, 30000),
    ],
    'Accounting': [
        ('Senior Accountant', 'Financial Accounting', 'CPA(K), IFRS, Month-end, QuickBooks/SAP', 120000, 220000),
        ('Accounts Assistant', 'Accounts Payable/Receivable', 'Reconciliations, Petty cash, ERP, CPA Part II', 40000, 70000),
        ('Payroll Officer', 'Payroll', 'Payroll, PAYE, NSSF, SHA/NHIF, iTax', 60000, 110000),
        ('Tax Accountant', 'Tax & KRA Compliance', 'CPA(K), iTax filing, VAT, Withholding tax', 90000, 180000),
        ('Internal Auditor', 'Audit & Assurance', 'CIA/CPA, Risk-based audit, Controls, Reporting', 120000, 220000),
    ],
    'Sales': [
        ('Business Development Manager', 'New Business Development', 'B2B sales, Pipeline, CRM, Negotiation', 120000, 250000),
        ('Key Account Manager', 'Account & Relationship Management', 'Client management, Renewals, Upselling', 100000, 200000),
        ('Field Sales Agent', 'Field Sales & Agents', 'Direct sales, Route planning, Targets, Commission', 25000, 60000),
        ('Telesales Executive', 'Telesales', 'Outbound calls, Lead conversion, CRM', 30000, 60000),
    ],
    'Marketing & Communications': [
        ('Digital Marketing Manager', 'Digital & Search Marketing', 'SEO, Google Ads, Meta Ads, Analytics, Email', 150000, 280000),
        ('Marketing Coordinator', 'Marketing Assistants/Coordinators', 'Content, Social media, Canva, Campaigns', 50000, 90000),
        ('Corporate Communications Officer', 'Public Relations & Corporate Affairs', 'Media relations, Press releases, Events', 90000, 170000),
        ('Content Creator', 'Marketing Communications', 'Copywriting, Video, TikTok/Instagram, Editing', 40000, 90000),
    ],
    'Administration & Office Support': [
        ('Executive Assistant', 'Personal & Executive Assistants', 'Diary management, Travel, Board papers, Discretion', 80000, 150000),
        ('Office Administrator', 'Office Management', 'Front office, MS Office, Procurement, Scheduling', 40000, 75000),
        ('Receptionist', 'Front Office & Receptionists', 'Switchboard, Visitor management, Customer service', 30000, 50000),
        ('Data Entry Clerk', 'Data Entry', 'Accuracy, Excel, Typing 50wpm', 25000, 40000),
    ],
    'Engineering': [
        ('Civil Engineer', 'Civil/Structural Engineering', 'EBK registration, Structural design, AutoCAD, Roads', 100000, 220000),
        ('Mechanical Engineer', 'Mechanical Engineering', 'SolidWorks, Plant maintenance, HVAC', 90000, 200000),
        ('Electrical Engineer', 'Electrical/Electronic Engineering', 'Power systems, PLC, Substation design, EBK', 100000, 220000),
        ('Water & Sanitation Engineer', 'Water & Sanitation Engineering', 'Hydraulic design, EPANET, Borehole projects', 90000, 180000),
        ('Telecoms Field Engineer', 'Telecommunications Engineering', 'Fibre, RF, Site surveys, Ericsson/Huawei', 80000, 160000),
    ],
    'Construction': [
        ('Site Supervisor', 'Foreperson/Supervisors', 'Residential construction, OSH, Scheduling', 60000, 120000),
        ('Quantity Surveyor', 'Estimating & Quantity Surveying', 'BOQs, Take-offs, Tendering, BORAQS', 90000, 180000),
        ('Construction Project Manager', 'Project Management', 'Commercial construction, Contracts, Procurement', 200000, 400000),
    ],
    'Hospitality & Tourism': [
        ('Head Chef', 'Chefs/Cooks', 'Menu design, Kitchen management, Food safety', 90000, 180000),
        ('Barista', 'Bar & Beverage Staff', 'Coffee, Customer service, Speed', 25000, 40000),
        ('Front Office Manager', 'Front Office & Guest Services', 'Opera PMS, Guest relations, Rostering', 70000, 130000),
        ('Safari Guide', 'Tour Guides & Safari', 'KPSGA silver/bronze, Driving licence, Wildlife knowledge', 40000, 90000),
        ('Cabin Crew', 'Airline & Cabin Crew', 'Customer service, Safety training, Swahili & English', 80000, 150000),
    ],
    'Education & Training': [
        ('Primary School Teacher (CBC)', 'Teaching - Primary (CBC)', 'TSC registration, CBC curriculum, Classroom management', 35000, 70000),
        ('Secondary Mathematics & Physics Teacher', 'Teaching - Secondary', 'TSC registration, Mathematics, Physics, KCSE prep', 40000, 90000),
        ('ECDE Teacher', 'Early Childhood (ECDE)', 'ECDE certificate/diploma, Play-based learning, First aid', 20000, 40000),
        ('TVET Instructor - Electrical', 'TVET & Vocational Training', 'TVETA licence, Curriculum delivery, Practicals', 45000, 85000),
        ('University Lecturer', 'University & Tertiary', 'PhD/Masters, Research, Publications, Supervision', 120000, 250000),
    ],
    'Agriculture, Animals & Conservation': [
        ('Farm Manager', 'Farm Management', 'Crop planning, Team supervision, Budgets, Irrigation', 70000, 150000),
        ('Agronomist', 'Agronomy & Farm Services', 'Soil science, Crop protection, Farmer training', 60000, 120000),
        ('Flower Farm Quality Supervisor', 'Horticulture & Floriculture', 'Post-harvest, Cold chain, GlobalGAP, Grading', 40000, 80000),
        ('Tea Estate Assistant Manager', 'Tea, Coffee & Sugar', 'Estate operations, Labour management, Yield reporting', 80000, 150000),
        ('Veterinary Officer', 'Veterinary Services', 'KVB registration, Livestock health, Extension', 60000, 120000),
        ('Dairy Extension Officer', 'Livestock & Dairy', 'Dairy husbandry, Cooperative engagement, Training', 40000, 80000),
    ],
    'Human Resources & Recruitment': [
        ('HR Business Partner', 'Consulting & Generalist HR', 'Employment Act, IHRM, Performance management', 150000, 280000),
        ('Recruitment Consultant', 'Recruitment - Agency', 'Sourcing, LinkedIn, Interviewing, Business development', 60000, 130000),
        ('HR Assistant', 'Consulting & Generalist HR', 'HRIS, Onboarding, Leave management, CHRP', 40000, 70000),
    ],
    'Retail & Consumer Products': [
        ('Branch Manager', 'Management - Store', 'Retail leadership, P&L, Shrinkage control, Merchandising', 80000, 160000),
        ('Cashier', 'Retail Assistants & Cashiers', 'POS, Cash handling, Customer service', 20000, 35000),
        ('FMCG Distribution Supervisor', 'FMCG Distribution', 'Route to market, Distributors, Sales targets, Van sales', 60000, 120000),
    ],
    'Manufacturing, Transport & Logistics': [
        ('Warehouse Assistant', 'Warehousing & Distribution', 'Stock counts, Forklift, Pick/pack, ERP', 25000, 45000),
        ('Truck Driver (Long Distance)', 'Boda Boda, Riders & Drivers', 'Class CE licence, Nairobi–Mombasa route, PSV/NTSA compliant', 40000, 70000),
        ('Delivery Rider', 'Boda Boda, Riders & Drivers', 'Motorbike licence, Smartphone, Nairobi routes, Customer service', 25000, 45000),
        ('Procurement Officer', 'Procurement & Supply Chain', 'Tendering, PPADA, Supplier management, KISM', 80000, 160000),
        ('Production Supervisor', 'Production & Machine Operators', 'Shift management, Line efficiency, ISO 22000', 60000, 120000),
        ('Clearing & Forwarding Agent', 'Freight, Clearing & Forwarding', 'KRA iCMS, Customs documentation, KPA processes', 45000, 90000),
    ],
    'Legal': [
        ('Corporate Lawyer', 'Corporate & Commercial Law', 'Advocate of the High Court, Contracts, M&A, LSK', 180000, 350000),
        ('Legal Officer', 'Advocates & Litigation', 'Litigation, Legal drafting, Compliance, Advocate', 100000, 200000),
        ('Paralegal', 'Law Clerks & Paralegals', 'Legal research, Court filing, Document management', 40000, 80000),
    ],
    'Design & Architecture': [
        ('UX/UI Designer', 'UX/UI Design', 'Figma, Design systems, User research, Prototyping', 120000, 250000),
        ('Architect', 'Architecture', 'BORAQS registration, Revit, ArchiCAD, Residential/Commercial', 100000, 220000),
        ('Graphic Designer', 'Graphic Design', 'Adobe CC, Branding, Print & digital, Social media', 45000, 90000),
    ],
    'Energy, Oil & Gas': [
        ('Solar Project Engineer', 'Renewable & Solar Energy', 'PV design, PVsyst, Mini-grids, EPRA', 120000, 250000),
        ('Power Line Technician', 'Power Generation & Distribution', 'HV/LV lines, Live-line, Safety, Field work', 45000, 90000),
        ('HSE Officer', 'Health, Safety & Environment', 'NEBOSH, DOSH registration, Audits, Incident investigation', 80000, 160000),
    ],
    'Call Centre & Customer Service': [
        ('Customer Care Representative', 'Customer Service - Call Centre', 'Inbound calls, CRM, Swahili & English, Problem solving', 30000, 55000),
        ('Team Leader - Contact Centre', 'Supervisors/Team Leaders', 'Coaching, KPIs, Workforce planning', 70000, 120000),
        ('BPO Chat Support Agent (Night Shift)', 'BPO & Outsourcing', 'Written English, Zendesk, Typing speed, US hours', 35000, 60000),
    ],
    'Community & Social Services': [
        ('Social Worker', 'Social Work', 'Case management, Child protection, Counselling, Reporting', 50000, 100000),
        ('Youth Programme Coordinator', 'Youth Development', 'Youth engagement, Life skills, Facilitation, M&E', 60000, 110000),
    ],
    'Government & Public Sector': [
        ('County Revenue Officer', 'County Government', 'Revenue collection, Public finance, Reporting, Integrity', 50000, 90000),
        ('Policy Analyst', 'Policy, Planning & Regulation', 'Policy analysis, Briefs, Stakeholder engagement, Research', 100000, 180000),
        ('Public Health Officer', 'County Government', 'Public health inspections, Health promotion, Reporting', 45000, 85000),
    ],
    'Security & Protective Services': [
        ('Security Guard', 'Security Guards', 'PSRA registration, Certificate of good conduct, Access control', 15000, 25000),
        ('Security Supervisor', 'Security Supervisors & Managers', 'Team supervision, Incident reporting, CCTV, Patrols', 30000, 55000),
        ('Loss Prevention Officer', 'Investigations & Loss Prevention', 'Investigations, Stock audits, CCTV review, Reporting', 40000, 75000),
    ],
    'Advertising, Arts & Media': [
        ('Multimedia Journalist', 'Journalism & Broadcasting', 'News writing, Video, Social media, MCK accreditation', 60000, 120000),
        ('Digital Content Producer', 'Content Creation & Social Media', 'Video editing, TikTok/YouTube, Analytics, Storytelling', 50000, 100000),
        ('Sub-Editor', 'Editing & Publishing', 'Copy editing, Headlines, CMS, Deadlines', 70000, 130000),
    ],
    'Insurance': [
        ('Underwriter', 'Underwriting', 'Motor & medical underwriting, Risk assessment, IRA compliance', 70000, 140000),
        ('Claims Officer', 'Claims', 'Claims assessment, Customer service, Documentation', 50000, 95000),
        ('Insurance Sales Agent', 'Brokerage & Agents', 'COP certificate, Prospecting, Commission, Life & general', 25000, 80000),
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
PERKS = ['Flexible / hybrid working arrangements', 'Comprehensive medical cover for you and your dependants', 'Pension scheme above statutory NSSF',
         'Paid maternity/paternity leave above the statutory minimum', 'Annual performance bonus', 'Staff transport / commuter allowance',
         'Airtime and data allowance', 'Modern office in Westlands/Upper Hill close to matatu routes', 'Lunch provided on site', 'Learning & certification sponsorship']
EXTRAS = ['Valid Certificate of Good Conduct', 'Relevant degree/diploma or equivalent experience', 'Valid driving licence',
          'KRA PIN, NSSF and SHA registration (or willingness to register)', 'Fluency in English and Kiswahili', 'Experience in a fast-paced environment']
TEAMS = ['Technology', 'Operations', 'Customer', 'People & Culture', 'Finance', 'Growth', 'Delivery', 'Clinical', 'Projects']

REVIEWS = [
    (5, 'Great culture and genuine flexibility', 'Supportive leaders, real hybrid working and interesting problems to solve.', 'Can be a lot going on at once during peak periods.'),
    (4, 'Good place to grow your career', 'Plenty of internal mobility and training budget. Pay is fair for the market.', 'Some legacy systems slow things down.'),
    (3, 'Solid but very corporate', 'Stable, good medical cover, nice offices.', 'Decisions take time and there are many layers of approval.'),
    (4, 'Friendly team, decent pay', 'The people are the best part. Managers listen and salaries are paid on time.', 'Nairobi traffic makes the commute long; limited parking.'),
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
            company, hq = random.choice(COMPANIES)
            focus = [c for c in COMPANY_FOCUS.get(company, []) if c in ROLES]
            if focus and random.random() < 0.8:
                cls = random.choice(focus)
                title, sub, skills, lo, hi = random.choice(ROLES[cls])
            else:
                cls, (title, sub, skills, lo, hi) = random.choice(pool)
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
            salary_text = (f"KSh {salary_min:,} – {salary_max:,} per month" if salary_min else 'Competitive, commensurate with experience')
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
                (title, company, location, derive_state(location), description, salary_text if salary_min else '', salary_min, salary_max, 'KES',
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
               VALUES (?, 'Python jobs in Nairobi', 'python', 'Nairobi', 'daily', 1, ?)""", (seeker_id, now.isoformat()))
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
    print(f"[seed] demo logins (password {DEMO_PASSWORD}): seeker@demo.openjobs.local, employer.safaricom@demo.openjobs.local, ...")
