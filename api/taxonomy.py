#!/usr/bin/env python3
"""
Job taxonomy shared by the API, alerts, seeding and the frontend.

- CLASSIFICATIONS: Seek-style industry classifications with sub-classifications.
- CATEGORY_TO_CLASSIFICATION: maps the legacy free-text `category` values to a classification.
- Location helpers: derive an Australian state (or "Remote"/"International") from a free-text location.
"""
import re

CLASSIFICATIONS = {
    'Accounting': ['Accounts Payable/Receivable', 'Audit', 'Bookkeeping', 'Financial Accounting', 'Management Accounting', 'Payroll', 'Taxation'],
    'Administration & Office Support': ['Administrative Assistants', 'Data Entry', 'Office Management', 'Personal Assistants', 'Receptionists'],
    'Advertising, Arts & Media': ['Agency Account Management', 'Editing & Publishing', 'Journalism', 'Performing Arts', 'Photography'],
    'Banking & Financial Services': ['Analysis & Reporting', 'Banking - Retail', 'Compliance & Risk', 'Financial Planning', 'Funds Management', 'Mortgages'],
    'Call Centre & Customer Service': ['Collections', 'Customer Service - Call Centre', 'Customer Service - Customer Facing', 'Sales - Inbound', 'Sales - Outbound', 'Supervisors/Team Leaders'],
    'CEO & General Management': ['Board Appointments', 'CEO', 'COO & MD', 'General/Business Unit Manager'],
    'Community Services & Development': ['Aged & Disability Support', 'Child Welfare', 'Community Development', 'Housing & Homelessness', 'Volunteer Coordination'],
    'Construction': ['Estimating', 'Foreperson/Supervisors', 'Health, Safety & Environment', 'Project Management', 'Quality Assurance', 'Surveying'],
    'Consulting & Strategy': ['Analysts', 'Corporate Development', 'Environment & Sustainability', 'Management & Change Consulting', 'Strategy & Planning'],
    'Design & Architecture': ['Architecture', 'Graphic Design', 'Industrial Design', 'Interior Design', 'UX/UI Design', 'Web & Interaction Design'],
    'Education & Training': ['Childcare & Outside School Hours Care', 'Library Services', 'Teaching - Early Childhood', 'Teaching - Primary', 'Teaching - Secondary', 'Tutoring', 'Vocational Training'],
    'Engineering': ['Chemical Engineering', 'Civil/Structural Engineering', 'Electrical/Electronic Engineering', 'Environmental Engineering', 'Mechanical Engineering', 'Project Engineering', 'Systems Engineering'],
    'Farming, Animals & Conservation': ['Agronomy & Farm Services', 'Conservation, Parks & Wildlife', 'Farm Management', 'Veterinary Services'],
    'Government & Defence': ['Air Force', 'Army', 'Emergency Services', 'Government - Federal', 'Government - Local', 'Government - State', 'Policy, Planning & Regulation'],
    'Healthcare & Medical': ['Aged Care Nursing', 'Dental', 'General Practitioners', 'Medical Administration', 'Nursing - General', 'Pharmacy', 'Physiotherapy', 'Psychology & Counselling'],
    'Hospitality & Tourism': ['Bar & Beverage Staff', 'Chefs/Cooks', 'Front Office & Guest Services', 'Kitchen & Sandwich Hands', 'Management', 'Travel Agents/Consultants', 'Waiting Staff'],
    'Human Resources & Recruitment': ['Consulting & Generalist HR', 'Industrial & Employee Relations', 'Occupational Health & Safety', 'Recruitment - Agency', 'Recruitment - Internal', 'Remuneration & Benefits', 'Training & Development'],
    'Information & Communication Technology': ['Architects', 'Business/Systems Analysts', 'Computer Operators', 'Database Development & Administration', 'Developers/Programmers', 'Engineering - Network', 'Engineering - Software', 'Help Desk & IT Support', 'Management', 'Networks & Systems Administration', 'Product Management & Development', 'Programme & Project Management', 'Security', 'Testing & Quality Assurance', 'Web Development & Production'],
    'Insurance & Superannuation': ['Assessment', 'Brokerage', 'Claims', 'Superannuation', 'Underwriting'],
    'Legal': ['Corporate & Commercial Law', 'Criminal & Civil Law', 'Family Law', 'Law Clerks & Paralegals', 'Legal Practice Management', 'Legal Secretaries'],
    'Manufacturing, Transport & Logistics': ['Assembly & Process Work', 'Couriers, Drivers & Postal Services', 'Fleet Management', 'Import/Export & Customs', 'Machine Operators', 'Purchasing, Procurement & Inventory', 'Road Transport', 'Warehousing, Storage & Distribution'],
    'Marketing & Communications': ['Brand Management', 'Digital & Search Marketing', 'Event Management', 'Market Research & Analysis', 'Marketing Assistants/Coordinators', 'Marketing Communications', 'Product Management & Development', 'Public Relations & Corporate Affairs'],
    'Mining, Resources & Energy': ['Analysis & Reporting', 'Health, Safety & Environment', 'Mining - Engineering & Maintenance', 'Mining - Operations', 'Oil & Gas - Operations', 'Power Generation & Distribution'],
    'Real Estate & Property': ['Administration', 'Body Corporate & Facilities Management', 'Commercial Sales, Leasing & Property Mgmt', 'Residential Leasing & Property Management', 'Residential Sales', 'Valuation'],
    'Retail & Consumer Products': ['Buying', 'Management - Area/Multi-site', 'Management - Store', 'Merchandisers', 'Retail Assistants', 'Planning'],
    'Sales': ['Account & Relationship Management', 'Analysis & Reporting', 'Management', 'New Business Development', 'Sales Coordinators', 'Sales Representatives/Consultants'],
    'Science & Technology': ['Biotechnology & Genetics', 'Chemistry & Physics', 'Environmental, Earth & Geosciences', 'Laboratory & Technical Services', 'Materials Sciences', 'Mathematics, Statistics & Information Sciences'],
    'Self Employment': ['Self Employment'],
    'Sport & Recreation': ['Coaching & Instruction', 'Fitness & Personal Training', 'Management'],
    'Trades & Services': ['Air Conditioning & Refrigeration', 'Automotive Trades', 'Carpentry & Cabinet Making', 'Cleaning Services', 'Electricians', 'Fitters, Turners & Machinists', 'Labourers', 'Plumbers', 'Security Services', 'Welders & Boilermakers'],
}

# Legacy free-text categories (employer.html select, seed data) -> classification
CATEGORY_TO_CLASSIFICATION = {
    'software development': 'Information & Communication Technology',
    'technology': 'Information & Communication Technology',
    'devops / sysadmin': 'Information & Communication Technology',
    'devops': 'Information & Communication Technology',
    'data science': 'Information & Communication Technology',
    'ai/ml': 'Information & Communication Technology',
    'development': 'Information & Communication Technology',
    'fintech': 'Banking & Financial Services',
    'engineering': 'Engineering',
    'design': 'Design & Architecture',
    'sales': 'Sales',
    'marketing': 'Marketing & Communications',
    'product': 'Information & Communication Technology',
    'general': None,
}

WORK_TYPES = {
    'full_time': 'Full time',
    'part_time': 'Part time',
    'contract': 'Contract/Temp',
    'casual': 'Casual/Vacation',
    'internship': 'Internship',
}

WORK_ARRANGEMENTS = {
    'remote': 'Remote',
    'hybrid': 'Hybrid',
    'onsite': 'On-site',
}

DATE_LISTED_OPTIONS = [(1, 'Today'), (3, 'Last 3 days'), (7, 'Last 7 days'), (14, 'Last 14 days'), (30, 'Last 30 days')]

SALARY_BANDS = [
    (0, 50000, 'Under $50k'),
    (50000, 70000, '$50k – $70k'),
    (70000, 90000, '$70k – $90k'),
    (90000, 120000, '$90k – $120k'),
    (120000, 150000, '$120k – $150k'),
    (150000, 200000, '$150k – $200k'),
    (200000, None, '$200k+'),
]

# ── Location normalisation ────────────────────────────────────────────────────

AU_STATES = {
    'NSW': 'New South Wales', 'VIC': 'Victoria', 'QLD': 'Queensland', 'WA': 'Western Australia',
    'SA': 'South Australia', 'TAS': 'Tasmania', 'ACT': 'Australian Capital Territory', 'NT': 'Northern Territory',
}

# major localities -> state (lower-case keys)
CITY_TO_STATE = {
    'sydney': 'NSW', 'newcastle': 'NSW', 'wollongong': 'NSW', 'parramatta': 'NSW', 'central coast': 'NSW', 'north sydney': 'NSW', 'chatswood': 'NSW',
    'melbourne': 'VIC', 'geelong': 'VIC', 'ballarat': 'VIC', 'bendigo': 'VIC', 'docklands': 'VIC', 'richmond': 'VIC',
    'brisbane': 'QLD', 'gold coast': 'QLD', 'sunshine coast': 'QLD', 'cairns': 'QLD', 'townsville': 'QLD', 'toowoomba': 'QLD', 'fortitude valley': 'QLD',
    'perth': 'WA', 'fremantle': 'WA', 'bunbury': 'WA', 'karratha': 'WA', 'port hedland': 'WA',
    'adelaide': 'SA', 'mount gambier': 'SA',
    'hobart': 'TAS', 'launceston': 'TAS',
    'canberra': 'ACT',
    'darwin': 'NT', 'alice springs': 'NT',
}

_STATE_RE = re.compile(r'\b(' + '|'.join(AU_STATES) + r')\b', re.IGNORECASE)
_STATE_NAME_RE = re.compile(r'\b(' + '|'.join(re.escape(v) for v in AU_STATES.values()) + r')\b', re.IGNORECASE)
_REMOTE_RE = re.compile(r'\b(remote|work from home|wfh|anywhere)\b', re.IGNORECASE)


def derive_state(location: str) -> str:
    """'Sydney NSW' -> 'NSW'; 'Melbourne' -> 'VIC'; 'Remote' -> 'Remote'; unknown -> 'Other'."""
    if not location:
        return 'Other'
    loc = location.strip()
    if _REMOTE_RE.search(loc):
        return 'Remote'
    m = _STATE_RE.search(loc)
    if m:
        return m.group(1).upper()
    m = _STATE_NAME_RE.search(loc)
    if m:
        for abbr, name in AU_STATES.items():
            if name.lower() == m.group(1).lower():
                return abbr
    low = loc.lower()
    for city, state in CITY_TO_STATE.items():
        if city in low:
            return state
    if 'australia' in low:
        return 'Other'
    return 'International'


def state_label(state: str) -> str:
    if state in AU_STATES:
        return AU_STATES[state]
    return state or 'Other'


def normalize_classification(value):
    """Case-insensitive lookup returning the canonical classification name or None."""
    if not value:
        return None
    v = value.strip().lower()
    for name in CLASSIFICATIONS:
        if name.lower() == v:
            return name
    return CATEGORY_TO_CLASSIFICATION.get(v)


def normalize_subclassification(classification, value):
    if not classification or not value:
        return None
    v = value.strip().lower()
    for sub in CLASSIFICATIONS.get(classification, []):
        if sub.lower() == v:
            return sub
    return None


def all_locations():
    """Suggestion pool for the location autocomplete."""
    out = ['Remote']
    for city, state in CITY_TO_STATE.items():
        out.append(f"{city.title()} {state}")
    out += [f"All {name}" for name in AU_STATES.values()]
    return out
