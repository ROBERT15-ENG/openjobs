"""UTC time helpers.

All timestamps persisted by the app are UTC ISO-8601 strings with a ``Z``
suffix (e.g. ``2026-09-19T12:00:00.123456Z``). Lexicographic ordering of these
strings matches chronological ordering, which is what the SQL comparisons rely
on, and SQLite's date functions understand the format directly.
"""

import datetime as _dt

UTC = _dt.timezone.utc


def utcnow() -> _dt.datetime:
    return _dt.datetime.now(UTC)


def to_iso(dt: _dt.datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat().replace('+00:00', 'Z')


def utcnow_iso() -> str:
    return to_iso(utcnow())


def iso_after(**delta) -> str:
    """ISO timestamp ``timedelta(**delta)`` from now (e.g. ``iso_after(hours=24)``)."""
    return to_iso(utcnow() + _dt.timedelta(**delta))


def iso_before(**delta) -> str:
    return to_iso(utcnow() - _dt.timedelta(**delta))


def today_iso() -> str:
    return utcnow().date().isoformat()


def from_timestamp(ts: float) -> _dt.datetime:
    return _dt.datetime.fromtimestamp(ts, UTC)
