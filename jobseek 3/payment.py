"""Payment integration for JobSeek - Stripe/PayPal ready"""
import os
import json
import hashlib
import time

# Payment Config
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
PAYPAL_SECRET = os.environ.get('PAYPAL_SECRET', '')

# Pricing
PREMIUM_JOB_POSTING_PRICE = 19.99  # USD
FEATURED_JOB_PRICE = 9.99
RESUME_ACCESS_PRICE = 4.99

def is_stripe_configured():
    return bool(STRIPE_SECRET_KEY)

def is_paypal_configured():
    return bool(PAYPAL_CLIENT_ID and PAYPAL_SECRET)

def create_stripe_checkout(job_id: int, user_id: int, plan: str = 'premium') -> dict:
    """Create Stripe checkout session"""
    if not is_stripe_configured():
        return {"success": False, "error": "Stripe not configured"}
    
    try:
        import requests
        
        prices = {
            'premium': PREMIUM_JOB_POSTING_PRICE,
            'featured': FEATURED_JOB_PRICE,
            'resume_access': RESUME_ACCESS_PRICE
        }
        
        amount = prices.get(plan, PREMIUM_JOB_POSTING_PRICE)
        
        session = {
            'payment_method_types': ['card'],
            'line_items': [{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'JobSeek {plan.title()} Posting'
                    },
                    'unit_amount': int(amount * 100)
                },
                'quantity': 1
            }],
            'mode': 'payment',
            'success_url': f'http://localhost:5700/payment-success.html?job_id={job_id}&session_id={{CHECKOUT_SESSION_ID}}',
            'cancel_url': 'http://localhost:5700/employer.html',
            'metadata': {
                'job_id': str(job_id),
                'user_id': str(user_id),
                'plan': plan
            }
        }
        
        # In production, call Stripe API:
        # resp = requests.post('https://api.stripe.com/v1/checkout/sessions', 
        #    auth=(STRIPE_SECRET_KEY, ''), json=session, timeout=10)
        
        return {
            "success": True,
            "message": "Stripe checkout would be created here",
            "demo_url": f"http://localhost:5700/payment-success.html?job_id={job_id}&demo=true"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def verify_stripe_webhook(payload: bytes, signature: str) -> dict:
    """Verify Stripe webhook signature"""
    if not STRIPE_WEBHOOK_SECRET:
        return {"success": False, "error": "Webhook secret not configured"}
    
    try:
        import hmac
        import hashlib
        
        expected = hmac.new(
            STRIPE_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        if hmac.compare_digest(expected, signature):
            return {"success": True, "verified": True}
        return {"success": False, "verified": False}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_pricing() -> dict:
    """Return pricing information"""
    return {
        "currency": "USD",
        "plans": {
            "premium_job": {
                "name": "Premium Job Posting",
                "price": PREMIUM_JOB_POSTING_PRICE,
                "features": ["Top of listings", "Featured badge", "30 days exposure"]
            },
            "featured": {
                "name": "Featured Job",
                "price": FEATURED_JOB_PRICE,
                "features": ["Highlighted in search", "Email blast"]
            },
            "resume_access": {
                "name": "Resume Access Pack",
                "price": RESUME_ACCESS_PRICE,
                "features": ["View 10 candidate resumes", "Direct contact"]
            }
        },
        "stripe_configured": is_stripe_configured(),
        "paypal_configured": is_paypal_configured()
    }

if __name__ == "__main__":
    print("Stripe configured:", is_stripe_configured())
    print("PayPal configured:", is_paypal_configured())
    print("Pricing:", json.dumps(get_pricing(), indent=2))