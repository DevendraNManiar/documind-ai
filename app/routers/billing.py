import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/billing", tags=["billing"])
stripe.api_key = settings.stripe_secret_key


@router.post("/checkout")
async def create_checkout(user: User = Depends(get_current_user)) -> dict:
    """Create a Stripe Checkout session for the Pro plan."""
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": settings.stripe_price_pro, "quantity": 1}],
        client_reference_id=str(user.id),
        customer_email=user.email,
        success_url="https://documind-ai.example.com/billing/success",
        cancel_url="https://documind-ai.example.com/billing/cancel",
    )
    return {"checkout_url": session.url}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("client_reference_id")
        if user_id:
            user = await db.scalar(select(User).where(User.id == user_id))
            if user:
                user.plan = "pro"
                user.stripe_customer_id = session.get("customer")
                await db.commit()

    return {"received": True}
