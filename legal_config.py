"""Legal document versions and entity placeholders (AU + Kenya)."""
import os

PRIVACY_POLICY_VERSION = os.environ.get("PRIVACY_POLICY_VERSION", "2026-10-01-au-ke")
TERMS_VERSION = os.environ.get("TERMS_VERSION", "2026-10-01-au-ke")


def legal_substitutions() -> dict:
    app_url = os.environ.get("APP_URL", "http://localhost:5700").rstrip("/")
    return {
        "ENTITY_NAME": os.environ.get("LEGAL_ENTITY_NAME", "OpenJobs"),
        "ENTITY_AU": os.environ.get(
            "LEGAL_ENTITY_AU", "OpenJobs Australia (operated by the entity named in your service agreement)"
        ),
        "ENTITY_KE": os.environ.get(
            "LEGAL_ENTITY_KE", "OpenJobs Kenya (local contact for Kenya data subjects)"
        ),
        "CONTACT_EMAIL": os.environ.get("LEGAL_PRIVACY_EMAIL", "privacy@openjobs.com"),
        "SUPPORT_EMAIL": os.environ.get("LEGAL_SUPPORT_EMAIL", "support@openjobs.com"),
        "AU_ADDRESS": os.environ.get("LEGAL_AU_ADDRESS", "Australia (contact us for postal details)"),
        "KE_ADDRESS": os.environ.get("LEGAL_KE_ADDRESS", "Nairobi, Kenya (contact us for postal details)"),
        "EFFECTIVE_DATE": os.environ.get("LEGAL_EFFECTIVE_DATE", "17 October 2026"),
        "PRIVACY_VERSION": PRIVACY_POLICY_VERSION,
        "TERMS_VERSION": TERMS_VERSION,
        "APP_URL": app_url,
    }
