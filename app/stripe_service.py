import logging
from typing import Optional
from fastapi import Request
import stripe
from app.config import settings
from app.database import User

logger = logging.getLogger("fitbuddy.billing")

if settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY

def create_stripe_checkout_session(user: User, success_url: str, cancel_url: str) -> Optional[dict]:
    """
    Creates a Stripe Checkout Session for upgrading to FitBuddy Pro.
    Returns session dict containing 'url' and 'id'.
    """
    if not settings.STRIPE_SECRET_KEY:
        logger.warning("STRIPE_SECRET_KEY not set. Operating in simulation mode.")
        # Simulated Checkout Session for testing/offline environments
        return {
            "url": f"{success_url}?session_id=sim_session_{user.id}",
            "id": f"sim_session_{user.id}"
        }

    try:
        # Create or reuse customer
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.username,
                metadata={"user_id": user.user_id, "id": str(user.id)}
            )
            customer_id = customer.id

        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": settings.STRIPE_PRO_PRICE_ID,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=user.user_id,
            metadata={"user_id": user.user_id}
        )
        return {"url": checkout_session.url, "id": checkout_session.id}
    except Exception as e:
        logger.error(f"Error creating Stripe checkout session: {e}")
        return None

def verify_and_construct_webhook_event(payload: bytes, sig_header: str) -> Optional[dict]:
    """Validates incoming Stripe webhook signature."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        # In simulation mode, parse payload directly
        try:
            import json
            return json.loads(payload.decode("utf-8"))
        except Exception:
            return None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return event
    except Exception as e:
        logger.error(f"Invalid Stripe webhook signature: {e}")
        return None
