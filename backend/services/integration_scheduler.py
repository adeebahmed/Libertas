from __future__ import annotations

import asyncio
import logging

from ..database import SessionLocal
from .ofx_sync import sync_all_ofx
from .plaid_sync import sync_all_plaid
from .sheets_sync import sync_all_sheets

logger = logging.getLogger(__name__)


async def run_daily_sync_once(trigger: str = "scheduled") -> dict:
    db = SessionLocal()
    try:
        plaid = await sync_all_plaid(db, trigger=trigger)
        sheets = await sync_all_sheets(db, trigger=trigger)
        ofx = await sync_all_ofx(db, trigger=trigger)
        return {"plaid": plaid, "sheets": sheets, "ofx": ofx}
    finally:
        db.close()


async def daily_sync_loop(interval_seconds: int = 60 * 60 * 24):
    # Delay first scheduled run so startup remains fast.
    await asyncio.sleep(30)
    while True:
        try:
            result = await run_daily_sync_once(trigger="scheduled")
            logger.info("Daily integrations sync completed: %s", result)
        except Exception as exc:
            logger.warning("Daily integrations sync failed: %s", exc)
        await asyncio.sleep(interval_seconds)
