"""Skill extraction utilities."""

import logging

from db import connect

log = logging.getLogger(__name__)


def extract_skills_fast(text: str) -> list[str]:
    try:
        db = connect()
        try:
            rows = db.execute('SELECT name, aliases FROM skills_taxonomy').fetchall()
        finally:
            db.close()
        text_lower = text.lower()
        matched = []
        for name, aliases in rows:
            if name.lower() in text_lower:
                matched.append(name)
            elif aliases:
                for alias in aliases.split(','):
                    if alias.strip().lower() in text_lower:
                        matched.append(name)
                        break
        return list(dict.fromkeys(matched))
    except Exception as exc:
        log.warning('[extract_skills_fast] %s', exc)
        return []
