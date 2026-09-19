"""Small, dependency-free request validation.

Each ``Field`` coerces and checks one JSON value; ``validate_payload`` applies a
mapping of field name -> Field to a request body, returning only the known keys
with coerced values. Unknown keys are ignored (so clients can send extra data),
invalid values raise ``ValidationError`` with a message safe to return to the
client.

Usage::

    JOB_FIELDS = {'title': Str(max_len=200, required=True), 'salary_min': Int(min=0)}
    try:
        data = validate_payload(request.json, JOB_FIELDS)
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
"""

from __future__ import annotations

import re
from typing import Any, Iterable

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
ISO_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}')


class ValidationError(ValueError):
    pass


class Field:
    def __init__(self, *, required: bool = False, nullable: bool = True):
        self.required = required
        self.nullable = nullable

    def coerce(self, name: str, value: Any) -> Any:  # pragma: no cover - overridden
        return value

    def __call__(self, name: str, value: Any) -> Any:
        if value is None:
            if self.required or not self.nullable:
                raise ValidationError(f'{name} is required')
            return None
        return self.coerce(name, value)


class Str(Field):
    def __init__(self, *, max_len: int = 10_000, min_len: int = 0, strip: bool = True,
                 choices: Iterable[str] | None = None, lower: bool = False, **kw):
        super().__init__(**kw)
        self.max_len, self.min_len, self.strip, self.lower = max_len, min_len, strip, lower
        self.choices = set(choices) if choices else None

    def coerce(self, name, value):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = str(value)
        if not isinstance(value, str):
            raise ValidationError(f'{name} must be a string')
        if self.strip:
            value = value.strip()
        if self.lower:
            value = value.lower()
        if self.required and not value:
            raise ValidationError(f'{name} is required')
        if len(value) < self.min_len:
            raise ValidationError(f'{name} must be at least {self.min_len} characters')
        if len(value) > self.max_len:
            raise ValidationError(f'{name} must be at most {self.max_len} characters')
        if self.choices is not None and value and value not in self.choices:
            raise ValidationError(f'{name} must be one of: {sorted(self.choices)}')
        return value


class Email(Str):
    def __init__(self, **kw):
        kw.setdefault('max_len', 254)
        super().__init__(lower=True, **kw)

    def coerce(self, name, value):
        value = super().coerce(name, value)
        if value and not EMAIL_RE.match(value):
            raise ValidationError('Invalid email format')
        return value


class Int(Field):
    def __init__(self, *, min: int | None = None, max: int | None = None, **kw):
        super().__init__(**kw)
        self.min, self.max = min, max

    def coerce(self, name, value):
        if isinstance(value, bool):
            raise ValidationError(f'{name} must be an integer')
        if isinstance(value, str):
            value = value.strip().replace(',', '')
            if value == '':
                return None if self.nullable else self._fail(name)
        try:
            number = int(float(value))
        except (TypeError, ValueError):
            raise ValidationError(f'{name} must be an integer') from None
        if self.min is not None and number < self.min:
            raise ValidationError(f'{name} must be >= {self.min}')
        if self.max is not None and number > self.max:
            raise ValidationError(f'{name} must be <= {self.max}')
        return number

    def _fail(self, name):
        raise ValidationError(f'{name} is required')


class Float(Field):
    def __init__(self, *, min: float | None = None, max: float | None = None, **kw):
        super().__init__(**kw)
        self.min, self.max = min, max

    def coerce(self, name, value):
        if isinstance(value, bool):
            raise ValidationError(f'{name} must be a number')
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValidationError(f'{name} must be a number') from None
        if self.min is not None and number < self.min:
            raise ValidationError(f'{name} must be >= {self.min}')
        if self.max is not None and number > self.max:
            raise ValidationError(f'{name} must be <= {self.max}')
        return number


class Bool(Field):
    TRUE = {'1', 'true', 'yes', 'on'}
    FALSE = {'0', 'false', 'no', 'off', ''}

    def coerce(self, name, value):
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, (int, float)):
            return 1 if value else 0
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in self.TRUE:
                return 1
            if lowered in self.FALSE:
                return 0
        raise ValidationError(f'{name} must be true or false')


class IsoDate(Str):
    """Loose ISO-8601 date/datetime string (``YYYY-MM-DD...``)."""

    def coerce(self, name, value):
        value = super().coerce(name, value)
        if value and not ISO_DATE_RE.match(value):
            raise ValidationError(f'{name} must be an ISO-8601 date')
        return value


class Url(Str):
    def __init__(self, **kw):
        kw.setdefault('max_len', 2048)
        super().__init__(**kw)

    def coerce(self, name, value):
        value = super().coerce(name, value)
        if value and not value.lower().startswith(('http://', 'https://')):
            raise ValidationError(f'{name} must start with http:// or https://')
        return value


class StrList(Field):
    """List of short strings; also accepts a comma-separated string."""

    def __init__(self, *, max_items: int = 50, max_len: int = 200, **kw):
        super().__init__(**kw)
        self.max_items, self.max_len = max_items, max_len

    def coerce(self, name, value):
        if isinstance(value, str):
            value = [part for part in value.split(',')]
        if not isinstance(value, list):
            raise ValidationError(f'{name} must be a list')
        items = []
        for item in value:
            if not isinstance(item, (str, int, float)) or isinstance(item, bool):
                raise ValidationError(f'{name} must contain only strings')
            text = str(item).strip()
            if text:
                items.append(text[: self.max_len])
        if len(items) > self.max_items:
            raise ValidationError(f'{name} may contain at most {self.max_items} items')
        return items


def validate_payload(data: Any, fields: dict[str, Field], *, partial: bool = False) -> dict:
    """Validate ``data`` against ``fields``.

    ``partial=True`` (PATCH semantics) only validates keys that are present.
    """
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValidationError('Request body must be a JSON object')
    out: dict[str, Any] = {}
    for name, field in fields.items():
        if name not in data:
            if field.required and not partial:
                raise ValidationError(f'{name} is required')
            continue
        out[name] = field(name, data[name])
    return out


def int_list(value: Any, name: str = 'ids', *, max_items: int = 500) -> list[int]:
    if not isinstance(value, list) or not value:
        raise ValidationError(f'{name} must be a non-empty array')
    if len(value) > max_items:
        raise ValidationError(f'{name} may contain at most {max_items} items')
    out = []
    for item in value:
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            raise ValidationError(f'{name} must contain integers') from None
    return out


def clamp_int(value: int | None, default: int, lo: int, hi: int) -> int:
    if value is None:
        return default
    return max(lo, min(hi, value))
