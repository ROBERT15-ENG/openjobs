"""Jinja rendering and site-wide template variables."""

import os

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def site_config() -> dict:
    base = os.environ.get("APP_URL", "http://localhost:5700").rstrip("/")
    return {
        "site_url": base,
        "site_name": "OpenJobs",
        "contact_email": os.environ.get("CONTACT_EMAIL", "hello@openjobs.com.au"),
        "contact_address": os.environ.get(
            "CONTACT_ADDRESS", "Level 1, 1 Market Street, Sydney NSW 2000, Australia"
        ),
        "ga_measurement_id": os.environ.get("GA_MEASUREMENT_ID", "").strip(),
    }


def render_page(template_name: str, **context) -> str:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    merged = {**site_config(), **context}
    return env.get_template(template_name).render(**merged)
