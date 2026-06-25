"""Central application configuration — loaded before any arc_devkit import."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env before arc_devkit config singleton is instantiated
load_dotenv()


class Settings(BaseSettings):
    # Arc / blockchain
    arc_rpc_url: str = Field(..., alias="ARC_RPC_URL")
    arc_chain_id: int = Field(5042002, alias="ARC_CHAIN_ID")
    arc_private_key: str | None = Field(None, alias="ARC_PRIVATE_KEY")
    usdc_contract_address: str = Field(
        "0x0000000000000000000000000000000000000000",
        alias="USDC_CONTRACT_ADDRESS",
    )
    platform_wallet_address: str = Field("", alias="PLATFORM_WALLET_ADDRESS")

    # Arc DevKit / Anthropic (required by arc_devkit.config)
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field("claude-sonnet-4-6", alias="ANTHROPIC_MODEL")

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    # Redis
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    # Security
    key_encryption_secret: str = Field(..., alias="KEY_ENCRYPTION_SECRET")
    webhook_secret: str = Field(..., alias="WEBHOOK_SECRET")
    jwt_secret: str = Field("dev_jwt_secret_change_in_prod", alias="JWT_SECRET")

    # App
    app_env: str = Field("development", alias="APP_ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    api_prefix: str = Field("/api/v1", alias="API_PREFIX")
    idempotency_ttl: int = Field(86400, alias="IDEMPOTENCY_TTL")
    payment_timeout: int = Field(120, alias="PAYMENT_TIMEOUT")
    subscription_max_retries: int = Field(3, alias="SUBSCRIPTION_MAX_RETRIES")
    webhook_timeout: int = Field(10, alias="WEBHOOK_TIMEOUT")

    model_config = {"populate_by_name": True, "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
