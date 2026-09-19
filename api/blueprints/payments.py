"""Payment and Stripe webhook routes."""

import logging
import os

import requests
from auth_utils import require_employer
from db import get_db
from flask import Blueprint, current_app, jsonify, request
from org_util import employer_can_access_job

log = logging.getLogger(__name__)
payments_bp = Blueprint('payments', __name__)

PLAN_PRICES_CENTS = {'standard': 9900, 'premium': 19900}


@payments_bp.route('/api/pricing', methods=['GET'])
def get_pricing():
    return jsonify({
        'currency': 'AUD',
        'plans': [
            {
                'id': 'standard',
                'name': 'Standard Job Post',
                'price': 99,
                'description': 'Post your job listing for 30 days',
                'features': ['30-day listing', 'AI-matched candidates', 'Email applications'],
                'featured': False,
            },
            {
                'id': 'premium',
                'name': 'Premium Job Post',
                'price': 199,
                'description': 'Top placement + featured badge + email to matched seekers',
                'features': ['Top of search results', 'Featured badge', 'Email to matched seekers', 'Priority support'],
                'featured': True,
            },
        ],
        'stripe_configured': bool(os.environ.get('STRIPE_SECRET_KEY')),
        'paypal_configured': bool(os.environ.get('PAYPAL_CLIENT_ID')),
    })


@payments_bp.route('/api/payment/checkout', methods=['POST'])
@require_employer
def create_checkout():
    if not os.environ.get('STRIPE_SECRET_KEY'):
        return jsonify({
            'error': 'Payment not configured',
            'demo': True,
            'message': 'Add STRIPE_SECRET_KEY to .env to enable payments',
        }), 503

    data = request.json or {}
    plan = (data.get('plan') or 'standard').strip().lower()
    if plan not in PLAN_PRICES_CENTS:
        return jsonify({'error': f'plan must be one of: {sorted(PLAN_PRICES_CENTS)}'}), 400
    try:
        job_id = int(data.get('job_id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'job_id is required'}), 400

    db = get_db()
    job = db.execute('SELECT id, employer_id FROM jobs WHERE id = ?', (job_id,)).fetchone()
    if not job or not employer_can_access_job(db, request.user_id, request.user_role, dict(job)):
        return jsonify({'error': 'Job not found'}), 404
    base_url = current_app.config['BASE_URL']

    session_data = {
        'payment_method_types': ['card'],
        'line_items': [{
            'price_data': {
                'currency': 'aud',
                'product_data': {'name': f'OpenJobs {plan.title()} Posting'},
                'unit_amount': PLAN_PRICES_CENTS[plan],
            },
            'quantity': 1,
        }],
        'mode': 'payment',
        'success_url': f'{base_url}/employer?payment=success&job_id={job_id}',
        'cancel_url': f'{base_url}/employer',
        'metadata': {
            'job_id': str(job_id),
            'user_id': str(request.user_id),
            'plan': plan,
        },
    }
    try:
        resp = requests.post(
            'https://api.stripe.com/v1/checkout/sessions',
            auth=(os.environ['STRIPE_SECRET_KEY'], ''),
            data=session_data,
            timeout=15,
        )
        if resp.status_code == 200:
            session = resp.json()
            return jsonify({'success': True, 'checkout_url': session['url'], 'session_id': session['id']})
        log.warning('stripe checkout failed: %s %s', resp.status_code, resp.text[:300])
        return jsonify({'error': 'Stripe checkout failed'}), 502
    except requests.RequestException:
        log.exception('stripe checkout request failed')
        return jsonify({'error': 'Payment service unavailable'}), 502


@payments_bp.route('/api/payment/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature', '')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

    if not webhook_secret:
        return jsonify({'error': 'Webhook secret not configured'}), 503

    try:
        import stripe
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except Exception:
        return jsonify({'error': 'Webhook signature verification failed'}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata') or {}
        job_id = metadata.get('job_id')
        user_id = metadata.get('user_id')
        plan = (metadata.get('plan') or 'standard').lower()
        if job_id and user_id:
            db = get_db()
            job = db.execute(
                'SELECT id, employer_id, moderation_status FROM jobs WHERE id = ?', (int(job_id),)
            ).fetchone()
            if job and employer_can_access_job(db, int(user_id), 'employer', dict(job)):
                if job['moderation_status'] == 'removed':
                    log.warning('paid job %s is moderation-removed; not reactivating', job_id)
                else:
                    db.execute(
                        'UPDATE jobs SET is_active = 1, is_featured = ? WHERE id = ?',
                        (1 if plan == 'premium' else 0, int(job_id)),
                    )
                    db.commit()

    return jsonify({'received': True})
