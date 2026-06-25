"""
Background worker — processes due subscriptions on a schedule.

Runs as a separate process (Docker service: worker).
Uses arc_devkit PaymentAgent for actual USDC transfers.
"""

import logging
import os
import time

# Load env before arc_devkit
from src.config import settings  # noqa: F401

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = int(os.getenv("WORKER_INTERVAL", "60"))


def run_cycle() -> None:
    from src.api.dependencies import subscription_renew_uc
    from src.infrastructure.database.session import SessionLocal

    db = SessionLocal()
    try:
        uc = subscription_renew_uc(db)
        results = uc.process_due()
        logger.info("Subscription cycle complete: %s", results)
    except Exception as exc:
        logger.error("Worker cycle error: %s", exc)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Subscription worker started — interval=%ds", INTERVAL_SECONDS)
    while True:
        run_cycle()
        time.sleep(INTERVAL_SECONDS)
