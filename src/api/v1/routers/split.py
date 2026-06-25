"""Split payment endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import split_uc
from src.api.v1.schemas.split import CreateSplitRequest, SplitResponse
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/split", tags=["split"])


@router.post("", response_model=SplitResponse, status_code=201)
def execute_split(body: CreateSplitRequest, db: Session = Depends(get_db)):
    """
    Execute a split payment.

    Example: 100 USDC → Platform 10% (10 USDC) + Merchant 90% (90 USDC)

    Uses arc_devkit PaymentAgent.execute_batch() for atomic batch transfer.
    """
    uc = split_uc(db)
    rule = uc.build_from_config(
        name=body.name,
        recipients_config=[r.model_dump() for r in body.recipients],
    )

    try:
        execution = uc.execute(
            split_rule=rule,
            total_amount=body.total_amount_usdc,
            invoice_id=body.invoice_id,
            broadcast=body.broadcast,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SplitResponse(
        split_rule_id=rule.id,
        name=rule.name,
        status=execution.status.value,
        tx_hashes=execution.tx_hashes,
        breakdown=rule.breakdown(body.total_amount_usdc),
    )
