"""Wallet domain entity."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class WalletStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


@dataclass
class Wallet:
    user_id: str
    address: str
    encrypted_private_key: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: WalletStatus = WalletStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_active(self) -> bool:
        return self.status == WalletStatus.ACTIVE
