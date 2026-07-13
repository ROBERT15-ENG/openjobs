"""Skill extraction utilities."""

import sqlite3

from db import get_db_path


def extract_skills_fast(text: str) -> list[str]:
    try:
        db = sqlite3.connect(get_db_path())
        rows = db.execute('SELECT name, aliases FROM skills_taxonomy').fetchall()
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
        print(f'[extract_skills_fast] {exc}')
        return []
