"""Billing state shared by job creation, checkout and the pricing endpoint.

A listing posted by an employer is held as ``pending_payment`` (inactive, not
searchable, no alert emails) until Stripe confirms payment via webhook. When no
Stripe key is configured the site runs free: listings publish immediately and
the UI says so.
"""

import os

PLANS = ('standard', 'premium')
PLAN_PRICES_CENTS = {'standard': 9900, 'premium': 19900}
PENDING_PAYMENT = 'pending_payment'


def payments_enabled() -> bool:
    return bool(os.environ.get('STRIPE_SECRET_KEY'))


def normalise_plan(value) -> str:
    plan = (value or 'standard').strip().lower()
    return plan if plan in PLANS else 'standard'


def activate_paid_job(db, job_id: int, plan: str) -> None:
    db.execute(
        "UPDATE jobs SET is_active = 1, is_featured = ?, moderation_status = 'ok' WHERE id = ?",
        (1 if plan == 'premium' else 0, job_id),
    )
    db.commit()
