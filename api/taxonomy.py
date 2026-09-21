#!/usr/bin/env python3
"""
Job taxonomy shared by the API, alerts, seeding and the frontend.

Kenya-first (launch market):
- CLASSIFICATIONS: industry classifications with sub-classifications, shaped for the Kenyan
  market (NGO/development, agribusiness, mobile money, clinical officers, security services...).
- REGIONS: the 47 counties. Jobs store the county in the `state` column (kept for schema
  stability); the UI labels it "County".
- Salaries are quoted in KES per month, which is how Kenyan employers and candidates talk.
"""
import re

COUNTRY = 'Kenya'
COUNTRY_CODE = 'KE'
CURRENCY = 'KES'
CURRENCY_SYMBOL = 'KSh'
SALARY_PERIOD = 'month'      # salary_min / salary_max are monthly figures
REGION_LABEL = 'County'

CLASSIFICATIONS = {
    'Accounting': ['Accounts Payable/Receivable', 'Audit & Assurance', 'Bookkeeping', 'Financial Accounting', 'Management Accounting', 'Payroll', 'Tax & KRA Compliance'],
    'Administration & Office Support': ['Administrative Assistants', 'Data Entry', 'Front Office & Receptionists', 'Office Management', 'Personal & Executive Assistants', 'Records Management'],
    'Advertising, Arts & Media': ['Agency Account Management', 'Content Creation & Social Media', 'Editing & Publishing', 'Journalism & Broadcasting', 'Performing Arts', 'Photography & Videography'],
    'Agriculture, Animals & Conservation': ['Agribusiness & Value Chains', 'Agronomy & Farm Services', 'Conservation, Parks & Wildlife', 'Farm Management', 'Horticulture & Floriculture', 'Livestock & Dairy', 'Tea, Coffee & Sugar', 'Veterinary Services'],
    'Banking & Financial Services': ['Analysis & Reporting', 'Banking - Retail', 'Compliance & Risk', 'Credit & Lending', 'Investment & Treasury', 'Microfinance & SACCOs', 'Mobile Money & Fintech'],
    'Call Centre & Customer Service': ['BPO & Outsourcing', 'Collections', 'Customer Service - Call Centre', 'Customer Service - Customer Facing', 'Sales - Inbound', 'Sales - Outbound', 'Supervisors/Team Leaders'],
    'CEO & General Management': ['Board Appointments', 'CEO & Country Director', 'COO & MD', 'General/Business Unit Manager'],
    'Community & Social Services': ['Child Protection', 'Community Development', 'Counselling & Psychosocial Support', 'Gender & Inclusion', 'Social Work', 'Youth Development'],
    'Construction': ['Estimating & Quantity Surveying', 'Foreperson/Supervisors', 'Health, Safety & Environment', 'Project Management', 'Quality Assurance', 'Site Engineering', 'Surveying'],
    'Consulting & Strategy': ['Analysts', 'Corporate Development', 'Environment & Sustainability', 'Management & Change Consulting', 'Strategy & Planning'],
    'Design & Architecture': ['Architecture', 'Graphic Design', 'Industrial Design', 'Interior Design', 'UX/UI Design', 'Web & Interaction Design'],
    'Education & Training': ['Early Childhood (ECDE)', 'Library Services', 'Special Needs Education', 'Teaching - Primary (CBC)', 'Teaching - Secondary', 'Tutoring & Coaching', 'TVET & Vocational Training', 'University & Tertiary'],
    'Energy, Oil & Gas': ['Health, Safety & Environment', 'Mining & Quarrying', 'Oil & Gas Operations', 'Power Generation & Distribution', 'Renewable & Solar Energy'],
    'Engineering': ['Chemical Engineering', 'Civil/Structural Engineering', 'Electrical/Electronic Engineering', 'Environmental Engineering', 'Mechanical Engineering', 'Project Engineering', 'Telecommunications Engineering', 'Water & Sanitation Engineering'],
    'Government & Public Sector': ['County Government', 'Defence & Security Services', 'Judiciary & Legal Services', 'National Government & Parastatals', 'Policy, Planning & Regulation'],
    'Healthcare & Medical': ['Clinical Officers', 'Community Health', 'Dental', 'Laboratory & Diagnostics', 'Medical Administration', 'Medical Officers & Doctors', 'Nursing', 'Nutrition & Dietetics', 'Pharmacy', 'Physiotherapy & Rehabilitation', 'Psychology & Counselling', 'Public Health'],
    'Hospitality & Tourism': ['Airline & Cabin Crew', 'Bar & Beverage Staff', 'Chefs/Cooks', 'Front Office & Guest Services', 'Housekeeping', 'Management', 'Tour Guides & Safari', 'Travel Agents/Consultants', 'Waiting Staff'],
    'Human Resources & Recruitment': ['Consulting & Generalist HR', 'Industrial & Employee Relations', 'Occupational Health & Safety', 'Recruitment - Agency', 'Recruitment - Internal', 'Remuneration & Benefits', 'Training & Development'],
    'Information & Communication Technology': ['Architects', 'Business/Systems Analysts', 'Data Science & Analytics', 'Database Development & Administration', 'Developers/Programmers', 'Engineering - Network', 'Engineering - Software', 'Help Desk & IT Support', 'Management', 'Mobile & Payments Development', 'Networks & Systems Administration', 'Product Management & Development', 'Programme & Project Management', 'Security', 'Testing & Quality Assurance', 'Web Development & Production'],
    'Insurance': ['Actuarial', 'Assessment', 'Brokerage & Agents', 'Claims', 'Underwriting'],
    'Legal': ['Advocates & Litigation', 'Corporate & Commercial Law', 'Family Law', 'Law Clerks & Paralegals', 'Legal Practice Management', 'Legal Secretaries'],
    'Manufacturing, Transport & Logistics': ['Boda Boda, Riders & Drivers', 'Fleet Management', 'Freight, Clearing & Forwarding', 'Procurement & Supply Chain', 'Production & Machine Operators', 'Quality Control', 'Warehousing & Distribution'],
    'Marketing & Communications': ['Brand Management', 'Digital & Search Marketing', 'Event Management', 'Market Research & Analysis', 'Marketing Assistants/Coordinators', 'Marketing Communications', 'Product Marketing', 'Public Relations & Corporate Affairs'],
    'NGO, Development & Humanitarian': ['Advocacy & Policy', 'Community Mobilisation', 'Grants & Fundraising', 'Humanitarian & Emergency Response', 'Monitoring, Evaluation & Learning (MEL)', 'Programme/Project Management', 'Public Health Programmes', 'Refugee & Migration Services'],
    'Real Estate & Property': ['Administration', 'Facilities Management', 'Commercial Sales & Leasing', 'Residential Sales & Letting', 'Property Management', 'Valuation'],
    'Retail & Consumer Products': ['Buying & Merchandising', 'FMCG Distribution', 'Management - Area/Multi-site', 'Management - Store', 'Retail Assistants & Cashiers', 'Planning'],
    'Sales': ['Account & Relationship Management', 'Analysis & Reporting', 'Field Sales & Agents', 'Management', 'New Business Development', 'Sales Coordinators', 'Telesales'],
    'Science & Technology': ['Biotechnology & Genetics', 'Chemistry & Physics', 'Environmental, Earth & Geosciences', 'Laboratory & Technical Services', 'Mathematics, Statistics & Information Sciences'],
    'Security & Protective Services': ['Investigations & Loss Prevention', 'Security Guards', 'Security Operations & Control Rooms', 'Security Supervisors & Managers'],
    'Sport & Recreation': ['Coaching & Instruction', 'Fitness & Personal Training', 'Management'],
    'Trades & Services': ['Beauty, Hair & Wellness', 'Carpenters & Joiners', 'Cleaning & Domestic Services', 'Electricians', 'Masons & Construction Workers', 'Mechanics & Auto Technicians', 'Plumbers', 'Solar & Electrical Installers', 'Tailoring & Textiles', 'Welders & Fabricators'],
}

# Legacy free-text categories (older employer form, imports) -> classification
CATEGORY_TO_CLASSIFICATION = {
    'software development': 'Information & Communication Technology',
    'technology': 'Information & Communication Technology',
    'devops / sysadmin': 'Information & Communication Technology',
    'devops': 'Information & Communication Technology',
    'data science': 'Information & Communication Technology',
    'ai/ml': 'Information & Communication Technology',
    'development': 'Information & Communication Technology',
    'product': 'Information & Communication Technology',
    'fintech': 'Banking & Financial Services',
    'banking': 'Banking & Financial Services',
    'engineering': 'Engineering',
    'design': 'Design & Architecture',
    'sales': 'Sales',
    'marketing': 'Marketing & Communications',
    'ngo': 'NGO, Development & Humanitarian',
    'healthcare': 'Healthcare & Medical',
    'education': 'Education & Training',
    'agriculture': 'Agriculture, Animals & Conservation',
    'general': None,
}

WORK_TYPES = {
    'full_time': 'Full time',
    'part_time': 'Part time',
    'contract': 'Contract',
    'casual': 'Casual',
    'internship': 'Internship / Attachment',
}

WORK_ARRANGEMENTS = {
    'remote': 'Remote',
    'hybrid': 'Hybrid',
    'onsite': 'On-site',
}

DATE_LISTED_OPTIONS = [(1, 'Today'), (3, 'Last 3 days'), (7, 'Last 7 days'), (14, 'Last 14 days'), (30, 'Last 30 days')]

# KES per month
SALARY_BANDS = [
    (0, 30000, 'Under KSh 30k'),
    (30000, 50000, 'KSh 30k – 50k'),
    (50000, 80000, 'KSh 50k – 80k'),
    (80000, 120000, 'KSh 80k – 120k'),
    (120000, 200000, 'KSh 120k – 200k'),
    (200000, 350000, 'KSh 200k – 350k'),
    (350000, None, 'KSh 350k+'),
]

# ── Location normalisation ────────────────────────────────────────────────────

# The 47 counties. Key = value stored in jobs.state; display adds "County".
REGIONS = {name: name for name in [
    'Baringo', 'Bomet', 'Bungoma', 'Busia', 'Elgeyo-Marakwet', 'Embu', 'Garissa', 'Homa Bay', 'Isiolo', 'Kajiado',
    'Kakamega', 'Kericho', 'Kiambu', 'Kilifi', 'Kirinyaga', 'Kisii', 'Kisumu', 'Kitui', 'Kwale', 'Laikipia', 'Lamu',
    'Machakos', 'Makueni', 'Mandera', 'Marsabit', 'Meru', 'Migori', 'Mombasa', "Murang'a", 'Nairobi', 'Nakuru',
    'Nandi', 'Narok', 'Nyamira', 'Nyandarua', 'Nyeri', 'Samburu', 'Siaya', 'Taita-Taveta', 'Tana River',
    'Tharaka-Nithi', 'Trans Nzoia', 'Turkana', 'Uasin Gishu', 'Vihiga', 'Wajir', 'West Pokot',
]}

# Towns / estates / business districts -> county (lower-case keys, longest names first when matching)
TOWN_TO_REGION = {
    # Nairobi
    'nairobi': 'Nairobi', 'westlands': 'Nairobi', 'upper hill': 'Nairobi', 'upperhill': 'Nairobi', 'kilimani': 'Nairobi',
    'karen': 'Nairobi', 'parklands': 'Nairobi', 'industrial area': 'Nairobi', 'ruaraka': 'Nairobi', 'embakasi': 'Nairobi',
    "lang'ata": 'Nairobi', 'langata': 'Nairobi', 'gigiri': 'Nairobi', 'lavington': 'Nairobi', 'kasarani': 'Nairobi',
    'south b': 'Nairobi', 'south c': 'Nairobi', 'nairobi cbd': 'Nairobi', 'hurlingham': 'Nairobi', 'ngara': 'Nairobi',
    'mombasa road': 'Nairobi', 'thika road': 'Nairobi', 'ngong road': 'Nairobi', 'waiyaki way': 'Nairobi', 'mukuru': 'Nairobi',
    # Coast
    'mombasa': 'Mombasa', 'nyali': 'Mombasa', 'likoni': 'Mombasa', 'bamburi': 'Mombasa', 'changamwe': 'Mombasa', 'mtwapa': 'Kilifi',
    'kilifi': 'Kilifi', 'malindi': 'Kilifi', 'watamu': 'Kilifi', 'diani': 'Kwale', 'ukunda': 'Kwale', 'kwale': 'Kwale',
    'lamu': 'Lamu', 'voi': 'Taita-Taveta', 'taveta': 'Taita-Taveta', 'hola': 'Tana River',
    # Central / Rift
    'kiambu': 'Kiambu', 'thika': 'Kiambu', 'ruiru': 'Kiambu', 'juja': 'Kiambu', 'kikuyu': 'Kiambu', 'limuru': 'Kiambu', 'ruaka': 'Kiambu',
    'nakuru': 'Nakuru', 'naivasha': 'Nakuru', 'gilgil': 'Nakuru', 'molo': 'Nakuru', 'eldoret': 'Uasin Gishu',
    'kitengela': 'Kajiado', 'ngong': 'Kajiado', 'ongata rongai': 'Kajiado', 'rongai': 'Kajiado', 'kajiado': 'Kajiado',
    'nyeri': 'Nyeri', 'karatina': 'Nyeri', 'nanyuki': 'Laikipia', 'nyahururu': 'Laikipia', "murang'a": "Murang'a", 'muranga': "Murang'a",
    'kerugoya': 'Kirinyaga', 'ol kalou': 'Nyandarua', 'kericho': 'Kericho', 'bomet': 'Bomet', 'narok': 'Narok',
    'kapsabet': 'Nandi', 'kabarnet': 'Baringo', 'iten': 'Elgeyo-Marakwet', 'kitale': 'Trans Nzoia', 'kapenguria': 'West Pokot',
    'lodwar': 'Turkana', 'kakuma': 'Turkana', 'maralal': 'Samburu',
    # Eastern / North Eastern
    'machakos': 'Machakos', 'athi river': 'Machakos', 'syokimau': 'Machakos', 'mlolongo': 'Machakos', 'wote': 'Makueni', 'makueni': 'Makueni',
    'kitui': 'Kitui', 'mwingi': 'Kitui', 'embu': 'Embu', 'meru': 'Meru', 'chuka': 'Tharaka-Nithi', 'isiolo': 'Isiolo',
    'marsabit': 'Marsabit', 'garissa': 'Garissa', 'dadaab': 'Garissa', 'wajir': 'Wajir', 'mandera': 'Mandera',
    # Western / Nyanza
    'kisumu': 'Kisumu', 'kakamega': 'Kakamega', 'bungoma': 'Bungoma', 'busia': 'Busia', 'vihiga': 'Vihiga', 'mbale': 'Vihiga',
    'siaya': 'Siaya', 'homa bay': 'Homa Bay', 'migori': 'Migori', 'kisii': 'Kisii', 'nyamira': 'Nyamira',
}
_TOWNS_BY_LENGTH = sorted(TOWN_TO_REGION, key=len, reverse=True)

_REMOTE_RE = re.compile(r'\b(remote|work from home|wfh|anywhere)\b', re.IGNORECASE)
_COUNTRY_RE = re.compile(r'\bkenya\b', re.IGNORECASE)
_FOREIGN_HINTS = re.compile(r'\b(uganda|tanzania|rwanda|ethiopia|nigeria|ghana|south africa|usa|united states|uk|united kingdom|'
                            r'london|dubai|uae|india|germany|canada|australia|kampala|dar es salaam|kigali|lagos|accra)\b', re.IGNORECASE)


def derive_state(location: str) -> str:
    """'Westlands, Nairobi' -> 'Nairobi'; 'Eldoret' -> 'Uasin Gishu'; 'Remote' -> 'Remote';
    unknown Kenyan -> 'Other'; obviously foreign -> 'International'."""
    if not location:
        return 'Other'
    loc = location.strip()
    if _REMOTE_RE.search(loc):
        return 'Remote'
    low = loc.lower().replace('’', "'")
    # Resolve from the least specific segment inwards ('Mombasa Road, Nairobi' -> Nairobi, not Mombasa),
    # preferring the longest town match so 'Nairobi CBD' / 'Thika Road' beat bare county names.
    segments = [s.strip() for s in re.split(r'[,/|]', low) if s.strip()] or [low]
    for segment in reversed(segments):
        for town in _TOWNS_BY_LENGTH:
            if re.search(r'\b' + re.escape(town) + r'\b', segment):
                return TOWN_TO_REGION[town]
        for county in REGIONS:
            if re.search(r'\b' + re.escape(county.lower()) + r'\b', segment):
                return county
    if _COUNTRY_RE.search(low):
        return 'Other'
    if _FOREIGN_HINTS.search(low):
        return 'International'
    return 'Other'


def state_label(state: str) -> str:
    if state in REGIONS:
        return f"{state} {REGION_LABEL}"
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


def format_salary(salary_min, salary_max, currency=None) -> str:
    """'KSh 80,000 – 120,000 /month'. Foreign currencies are shown as-is without a period."""
    cur = (currency or CURRENCY).upper()
    sym = CURRENCY_SYMBOL if cur == CURRENCY else cur
    suffix = f' /{SALARY_PERIOD}' if cur == CURRENCY else ''
    if salary_min and salary_max:
        if salary_min == salary_max:
            return f"{sym} {salary_min:,.0f}{suffix}"
        return f"{sym} {salary_min:,.0f} – {salary_max:,.0f}{suffix}"
    if salary_min:
        return f"{sym} {salary_min:,.0f}+{suffix}"
    if salary_max:
        return f"Up to {sym} {salary_max:,.0f}{suffix}"
    return ''


def all_locations():
    """Suggestion pool for the location autocomplete."""
    out = ['Remote', f'All {COUNTRY}']
    major = ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret', 'Thika', 'Kiambu', 'Machakos', 'Nyeri', 'Naivasha',
             'Malindi', 'Kitale', 'Kakamega', 'Kericho', 'Meru', 'Nanyuki', 'Kitengela', 'Ruiru', 'Athi River', 'Westlands']
    out += major
    out += [f"{name} County" for name in REGIONS]
    return out
