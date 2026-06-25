"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """Service liveness probe."""
    return {"status": "ok", "service": "arc-fintech"}


@router.get("/health/blockchain")
def blockchain_health():
    """Verify Arc RPC connectivity via arc_devkit."""
    from arc_devkit.core.connection import check_connection
    connected = check_connection()
    return {
        "blockchain": "connected" if connected else "disconnected",
        "network": "arc-testnet",
    }
