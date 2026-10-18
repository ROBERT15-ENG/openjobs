"""
Guest-only ad catalog for OpenJobs job feed (pre-login).
Each entry is sized to match a standard job card in templates/index.html.
"""

from typing import Any, Dict, List

# kind: "promoted" (premium placements) | "standard" (display ads)
GUEST_ADS: List[Dict[str, Any]] = [
    {
        "id": "promo-visa-premium",
        "kind": "promoted",
        "theme": "visa_premium",
        "title": "Premium — Visa sponsorship roles",
        "advertiser": "OpenJobs Premium",
        "location": "Australia-wide · All skilled occupations",
        "summary": (
            "See employer-sponsored roles matched to MLTSSL/STSOL-style occupation lists — "
            "not just teaching. Daily alerts, 482/TSS filters, and early access before free users."
        ),
        "features": [
            "Skilled list–matched sponsors",
            "482 / TSS & relocation filters",
            "Email + Telegram alerts",
        ],
        "price_hint": "$9/mo",
        "cta_label": "Start Premium",
        "cta_url": "/register?plan=visa_premium",
        "logo_letter": "V",
        "tags": ["Visa", "Premium", "MLTSSL"],
    },
    {
        "id": "promo-employer-premium",
        "kind": "promoted",
        "title": "Feature your role at the top of search",
        "advertiser": "OpenJobs for Employers",
        "location": "Australia-wide",
        "summary": "Premium listings get more views, highlighted placement, and AI-matched candidates. First post from $99 AUD.",
        "cta_label": "Post a promoted job",
        "cta_url": "/employer",
        "logo_letter": "O",
        "tags": ["Employers", "Premium"],
    },
    {
        "id": "promo-cloud-skills",
        "kind": "promoted",
        "title": "AWS & Azure certifications — cohort starts soon",
        "advertiser": "CloudCareer Academy",
        "location": "Online · Self-paced",
        "summary": "Structured paths for solutions architects and DevOps engineers. Alumni placed at top AU tech employers.",
        "cta_label": "View programs",
        "cta_url": "https://example.com/cloud-career",
        "logo_letter": "C",
        "tags": ["Learning", "Cloud"],
    },
    {
        "id": "std-resume-review",
        "kind": "standard",
        "title": "Free ATS resume scan",
        "advertiser": "ResumeLift",
        "location": "Remote",
        "summary": "See how recruiters' systems read your CV before you apply. Keyword gaps and formatting tips in minutes.",
        "cta_label": "Scan my resume",
        "cta_url": "https://example.com/resume-scan",
        "logo_letter": "R",
        "tags": ["Tools"],
    },
    {
        "id": "std-interview-prep",
        "kind": "standard",
        "title": "Mock interviews with industry mentors",
        "advertiser": "PrepHire",
        "location": "Video call",
        "summary": "Practice behavioural and technical rounds with engineers and hiring managers from Australian startups.",
        "cta_label": "Book a session",
        "cta_url": "https://example.com/interview-prep",
        "logo_letter": "P",
        "tags": ["Career"],
    },
]


def ads_for_page(page: int = 1, per_kind: int = 2) -> List[Dict[str, Any]]:
    """Rotate catalog ads by page; return promoted first, then standard."""
    promoted = [a for a in GUEST_ADS if a.get("kind") == "promoted"]
    standard = [a for a in GUEST_ADS if a.get("kind") == "standard"]
    if not promoted and not standard:
        return []

    page = max(1, page)
    offset_p = ((page - 1) * per_kind) % len(promoted) if promoted else 0
    offset_s = ((page - 1) * per_kind) % len(standard) if standard else 0

    out: List[Dict[str, Any]] = []
    for i in range(per_kind):
        if promoted:
            out.append(promoted[(offset_p + i) % len(promoted)])
        if standard:
            out.append(standard[(offset_s + i) % len(standard)])
    return out
