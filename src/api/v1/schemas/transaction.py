"""Transaction API schemas."""

from pydantic import BaseModel


class TransactionResponse(BaseModel):
    id: str
    tx_hash: str
    from_address: str
    to_address: str
    amount_usdc: str
    type: str
    status: str
    created_at: str


class TransactionListResponse(BaseModel):
    address: str
    recorded: list[dict]
    onchain_scan: dict
