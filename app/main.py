import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db, init_db
from app.poller import polling_worker
from app.telegram_api import delete_webhook
from app.update_processor import process_telegram_update

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    poll_stop: asyncio.Event | None = None
    poll_task: asyncio.Task | None = None

    if settings.use_polling:
        del_body = await delete_webhook(drop_pending_updates=True)
        logger.info(
            "USE_POLLING=true — webhook cleared for long polling; deleteWebhook ok=%s",
            del_body.get("ok"),
        )
        poll_stop = asyncio.Event()
        poll_task = asyncio.create_task(polling_worker(poll_stop))
        logger.info("telegram_transport=getUpdates polling (no public HTTPS required)")
    else:
        logger.info(
            "telegram_transport=webhook POST /webhook — "
            "needs HTTPS URL registered + firewall open; webhook_secret=%s",
            "configured" if settings.webhook_secret else "disabled",
        )

    yield

    if poll_stop is not None:
        poll_stop.set()
    if poll_task is not None:
        poll_task.cancel()
        try:
            await poll_task
        except asyncio.CancelledError:
            pass

    engine.dispose()


app = FastAPI(title="Telegram Dice Bot", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "polling": settings.use_polling}


def verify_webhook_secret(x_telegram_bot_api_secret_token: str | None = Header(None)) -> None:
    if settings.use_polling:
        return
    if not settings.webhook_secret:
        return
    if x_telegram_bot_api_secret_token != settings.webhook_secret:
        if x_telegram_bot_api_secret_token is None:
            logger.warning(
                "webhook_rejected_missing_secret_header "
                "(set WEBHOOK_SECRET empty or re-register webhook with the same secret_token)"
            )
        else:
            logger.warning("webhook_rejected_bad_secret")
        raise HTTPException(status_code=403, detail="Invalid secret")


@app.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(verify_webhook_secret),
):
    if settings.use_polling:
        raise HTTPException(status_code=503, detail="Bot uses polling; webhook disabled")

    update: dict[str, Any] = await request.json()
    await process_telegram_update(db, update, source="webhook")
    return {"ok": True}
