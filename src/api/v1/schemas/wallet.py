"""Wallet API schemas."""

from pydantic import BaseModel, Field


class CreateWalletRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="Your platform user ID")


class WalletResponse(BaseModel):
    wallet_id: str
    user_id: str
    address: str
    status: str


class BalanceResponse(BaseModel):
    address: str
    native_balance: str
    usdc_balance: str
