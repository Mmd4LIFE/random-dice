import asyncio
import logging

from app.database import SessionLocal
from app.telegram_api import get_updates
from app.update_processor import process_telegram_update

logger = logging.getLogger(__name__)


async def polling_worker(stop: asyncio.Event) -> None:
    offset: int | None = None
    logger.info("polling_started long_poll_timeout=50s")

    while not stop.is_set():
        try:
            updates = await get_updates(offset=offset, timeout=50)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("polling_get_updates_failed")
            await asyncio.sleep(5)
            continue

        for update in updates:
            uid = update.get("update_id")
            if uid is not None:
                offset = int(uid) + 1

            db = SessionLocal()
            try:
                await process_telegram_update(db, update, source="poll")
            except Exception:
                logger.exception("poll_process_update_failed update_id=%s", uid)
                db.rollback()
            finally:
                db.close()

    logger.info("polling_stopped")
