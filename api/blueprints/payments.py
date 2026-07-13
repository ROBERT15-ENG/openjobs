"""Payment and Stripe webhook routes."""

import os

import requests
from auth_utils import require_auth
from flask import Blueprint, current_app, jsonify, request

payments_bp = Blueprint('payments', __name__)


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
@require_auth
def create_checkout():
    if not os.environ.get('STRIPE_SECRET_KEY'):
        return jsonify({
            'error': 'Payment not configured',
            'demo': True,
            'message': 'Add STRIPE_SECRET_KEY to .env to enable payments',
        }), 503

    data = request.json or {}
    job_id = data.get('job_id')
    plan = data.get('plan', 'standard')
    prices = {'standard': 9900, 'premium': 19900}
    base_url = current_app.config['BASE_URL']

    session_data = {
        'payment_method_types': ['card'],
        'line_items': [{
            'price_data': {
                'currency': 'aud',
                'product_data': {'name': f'OpenJobs {plan.title()} Posting'},
                'unit_amount': prices.get(plan, 9900),
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
        return jsonify({'error': 'Stripe error', 'detail': resp.text}), 502
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


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
    except Exception as exc:
        return jsonify({'error': f'Signature verification failed: {exc}'}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata') or {}
        job_id = metadata.get('job_id')
        if job_id:
            from db import get_db
            db = get_db()
            db.execute('UPDATE jobs SET is_active = 1 WHERE id = ?', (int(job_id),))
            db.commit()

    return jsonify({'received': True})
