"""Application status normalization."""

from constants import APPLICATION_STATUSES, KANBAN_STAGES, STATUS_ALIASES


def normalize_status(status: str | None) -> str:
    if not status:
        return 'applied'
    normalized = status.strip().lower()
    return STATUS_ALIASES.get(normalized, normalized)


def is_valid_status(status: str, allowed: tuple[str, ...] = APPLICATION_STATUSES) -> bool:
    return normalize_status(status) in allowed


def is_valid_kanban_stage(stage: str) -> bool:
    return normalize_status(stage) in KANBAN_STAGES


def kanban_stage_for(status: str | None) -> str:
    stage = normalize_status(status)
    return stage if stage in KANBAN_STAGES else 'applied'
