"""Match score labels for seeker-facing UI."""


def match_tier(score: int | float | None) -> str | None:
    """Return ELITE / STRONG / WATCHLIST tier for display, or None below threshold."""
    if score is None:
        return None
    value = int(score)
    if value >= 80:
        return 'ELITE'
    if value >= 70:
        return 'STRONG'
    if value >= 50:
        return 'WATCHLIST'
    return None


def match_tier_label(score: int | float | None) -> str:
    tier = match_tier(score)
    if not tier:
        return ''
    return tier
