"""Shared constants for OpenJobs."""

APPLICATION_STATUSES = (
    'applied',
    'screening',
    'interview',
    'offer',
    'hired',
    'rejected',
    'withdrawn',
)

KANBAN_STAGES = (
    'applied',
    'screening',
    'interview',
    'offer',
    'hired',
    'rejected',
)

STATUS_ALIASES = {
    'pending': 'applied',
    'reviewing': 'screening',
}

SEEKER_ROLES = ('user', 'seeker')

JWT_ALGORITHM = 'HS256'
JWT_EXPIRY_DAYS = 7
