"""
Indeed Australia — not implemented.

Indeed blocks most automated HTML scraping and does not expose a stable public API.
Use SEEK (seek_au) for Australian listings, or an official Indeed publisher integration.
"""

from typing import Any, Dict, List


def search_indeed_au(
    keywords: str,
    location: str = "Australia",
    max_pages: int = 1,
) -> List[Dict[str, Any]]:
    raise NotImplementedError(
        "Indeed AU scraping is disabled (bot protection). Use source=seek or teaching_au."
    )
