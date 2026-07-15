"""Active hiring regions and country codes (from ekip)."""

REGIONS = {
    'au-syd': {'name': 'Sydney', 'country': 'AU', 'status': 'active'},
    'au-mel': {'name': 'Melbourne', 'country': 'AU', 'status': 'active'},
    'au-bne': {'name': 'Brisbane', 'country': 'AU', 'status': 'active'},
    'au-per': {'name': 'Perth', 'country': 'AU', 'status': 'active'},
    'sg': {'name': 'Singapore', 'country': 'SG', 'status': 'active'},
    'remote': {'name': 'Remote / Worldwide', 'country': 'XX', 'status': 'active'},
}

COUNTRY_ALIASES = {
    'au': 'AU',
    'australia': 'AU',
    'sg': 'SG',
    'singapore': 'SG',
    'nz': 'NZ',
    'new zealand': 'NZ',
}


def normalize_country(value: str | None) -> str | None:
    if not value:
        return None
    key = value.strip().lower()
    if key in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[key]
    if len(value.strip()) == 2:
        return value.strip().upper()
    return value.strip()


def infer_country_region(location: str | None) -> tuple[str | None, str | None]:
    """Best-effort country/region from a free-text location."""
    if not location:
        return None, None
    loc = location.lower()
    if 'remote' in loc or 'worldwide' in loc:
        return 'XX', 'remote'
    if 'singapore' in loc or loc.strip() in ('sg',):
        return 'SG', 'sg'
    if any(x in loc for x in ('sydney', 'nsw')):
        return 'AU', 'au-syd'
    if any(x in loc for x in ('melbourne', 'vic')):
        return 'AU', 'au-mel'
    if any(x in loc for x in ('brisbane', 'qld')):
        return 'AU', 'au-bne'
    if any(x in loc for x in ('perth', 'wa')):
        return 'AU', 'au-per'
    if 'australia' in loc or ' aus' in f' {loc}' or loc.endswith(' au'):
        return 'AU', None
    return None, None
