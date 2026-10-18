"""
Match scraped job text to Australian skilled occupation list keywords (ANZSCO).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "au_skilled_occupations.json"

_WORD = re.compile(r"[a-z0-9]+", re.I)


def _norm(text: str) -> str:
    return " ".join(_WORD.findall((text or "").lower()))


def _phrase_hits(phrase: str, text: str) -> bool:
    if not phrase or not text:
        return False
    if len(phrase) <= 3:
        return bool(re.search(rf"\b{re.escape(phrase)}\b", text))
    return phrase in text


@lru_cache(maxsize=1)
def load_occupations() -> List[Dict[str, Any]]:
    if not DATA_FILE.is_file():
        return []
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return list(raw.get("occupations") or [])


def _job_blob(job: Dict[str, Any]) -> str:
    parts = [
        str(job.get("title") or ""),
        str(job.get("company") or ""),
        str(job.get("description") or ""),
        str(job.get("teaser") or ""),
        str(job.get("search_summary") or ""),
    ]
    bullets = job.get("bulletPoints") or []
    if isinstance(bullets, list):
        parts.extend(str(b) for b in bullets)
    return _norm(" ".join(parts))


def match_occupation(
    job: Dict[str, Any],
    min_score: int = 3,
) -> Optional[Dict[str, Any]]:
    """
    Return best occupation match or None.
    Title keyword hit scores higher than body-only hits.
    """
    title = _norm(str(job.get("title") or ""))
    blob = _job_blob(job)
    if not blob:
        return None

    best: Optional[Tuple[int, Dict[str, Any]]] = None
    for occ in load_occupations():
        score = 0
        for kw in occ.get("keywords") or []:
            phrase = _norm(kw)
            if not phrase:
                continue
            if _phrase_hits(phrase, title):
                score += 5
            elif _phrase_hits(phrase, blob):
                score += 2
        if score <= 0:
            continue
        if best is None or score > best[0]:
            best = (score, occ)

    if best is None or best[0] < min_score:
        return None
    occ = dict(best[1])
    occ["match_score"] = best[0]
    return occ


def annotate_job_occupation(job: Dict[str, Any], match: Dict[str, Any]) -> None:
    job["anzsco"] = match.get("anzsco")
    job["occupation_title"] = match.get("title")
    job["skilled_lists"] = match.get("lists") or []
    job["occupation_match_score"] = match.get("match_score")
    lists = ",".join(job["skilled_lists"])
    tag = f"anzsco:{match.get('anzsco')} lists:{lists}"
    summary = job.get("search_summary") or ""
    if tag not in summary:
        job["search_summary"] = f"{tag} {summary}".strip()


def occupation_list_version() -> str:
    if not DATA_FILE.is_file():
        return "missing"
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return str(raw.get("version") or "unknown")
    except Exception:
        return "invalid"
