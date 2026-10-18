"""Australian states and territories for regional job search."""

from typing import List, Tuple

# (code, SEEK where string, display name)
AU_STATES: List[Tuple[str, str, str]] = [
    ("NSW", "New South Wales", "New South Wales"),
    ("VIC", "Victoria", "Victoria"),
    ("QLD", "Queensland", "Queensland"),
    ("WA", "Western Australia", "Western Australia"),
    ("SA", "South Australia", "South Australia"),
    ("TAS", "Tasmania", "Tasmania"),
    ("NT", "Northern Territory", "Northern Territory"),
    ("ACT", "Australian Capital Territory", "Australian Capital Territory"),
]

STATE_CODES = {code for code, _, _ in AU_STATES}


def infer_state_code(location: str) -> str:
    loc = (location or "").upper()
    for code, _, name in AU_STATES:
        if f" {code}" in loc or loc.endswith(code) or name.upper() in loc:
            return code
    # City hints
    hints = {
        "SYDNEY": "NSW",
        "MELBOURNE": "VIC",
        "BRISBANE": "QLD",
        "PERTH": "WA",
        "ADELAIDE": "SA",
        "HOBART": "TAS",
        "DARWIN": "NT",
        "CANBERRA": "ACT",
        "TAMWORTH": "NSW",
        "GEELONG": "VIC",
        "PILBARA": "WA",
        "KARRATHA": "WA",
    }
    for city, code in hints.items():
        if city in loc:
            return code
    return "AU"
