"""
LinkedIn — not implemented (requires authenticated API / partnership).
"""

from typing import Any, Dict, List


def search_linkedin_au(
    keywords: str,
    location: str = "Australia",
    max_pages: int = 1,
) -> List[Dict[str, Any]]:
    raise NotImplementedError(
        "LinkedIn scraping is not available. Use source=seek or teaching_au."
    )
