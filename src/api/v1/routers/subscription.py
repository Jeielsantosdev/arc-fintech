"""Subscription endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import (
    subscription_cancel_uc,
    subscription_create_uc,
    subscription_renew_uc,
)
from src.api.v1.schemas.subscription import (
    CancelSubscriptionResponse,
    CreateSubscriptionRequest,
    SubscriptionResponse,
)
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.post("", response_model=SubscriptionResponse, status_code=201)
def create_subscription(body: CreateSubscriptionRequest, db: Session = Depends(get_db)):
    """Create a new recurring subscription."""
    uc = subscription_create_uc(db)
    return uc.execute(
        customer_address=body.customer_address,
        merchant_address=body.merchant_address,
        amount_usdc=body.amount_usdc,
        interval_days=body.interval_days,
        description=body.description,
        split_rule_id=body.split_rule_id,
        metadata=body.metadata,
    )


@router.delete("/{subscription_id}", response_model=CancelSubscriptionResponse)
def cancel_subscription(subscription_id: str, db: Session = Depends(get_db)):
    """Cancel a subscription immediately."""
    uc = subscription_cancel_uc(db)
    try:
        return uc.execute(subscription_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/process-due")
def process_due_subscriptions(
    webhook_url: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Trigger processing of all due subscriptions.

    Normally called by the background worker, but exposed for manual triggering.
    """
    uc = subscription_renew_uc(db)
    return uc.process_due(webhook_url=webhook_url)
