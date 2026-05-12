import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db, init_db
from app.dice_service import log_dice_roll, reply_text_for_dice, upsert_user
from app.telegram_api import send_message

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    engine.dispose()


app = FastAPI(title="Telegram Dice Bot", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


def verify_webhook_secret(x_telegram_bot_api_secret_token: str | None = Header(None)) -> None:
    if not settings.webhook_secret:
        return
    if x_telegram_bot_api_secret_token != settings.webhook_secret:
        logger.warning("webhook_rejected_bad_secret")
        raise HTTPException(status_code=403, detail="Invalid secret")


@app.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(verify_webhook_secret),
):
    update: dict[str, Any] = await request.json()
    logger.debug("webhook_update_received update_id=%s", update.get("update_id"))

    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"ok": True}

    chat = message.get("chat") or {}
    chat_id = chat.get("id")

    text = (message.get("text") or "").strip()
    if text.startswith("/start"):
        if chat_id:
            await send_message(
                int(chat_id),
                "Hi! Send an animated dice sticker (🎲 🎯 🏀 ⚽ 🎳 🎰). "
                "When Telegram delivers the result, I'll reply with the number and save it.",
            )
        return {"ok": True}

    dice = message.get("dice")
    if not dice:
        return {"ok": True}

    from_user = message.get("from")
    if not from_user or chat_id is None:
        logger.warning("dice_message_missing_from_or_chat", extra={"update_id": update.get("update_id")})
        return {"ok": True}

    dice_emoji = dice.get("emoji") or "🎲"
    dice_value = int(dice["value"])
    chat_id = int(chat_id)
    message_id = int(message["message_id"])

    user = upsert_user(db, from_user)
    log_dice_roll(
        db,
        user=user,
        dice_emoji=dice_emoji,
        dice_value=dice_value,
        chat_id=chat_id,
        message_id=message_id,
    )
    db.commit()

    text = reply_text_for_dice(dice_emoji, dice_value)
    await send_message(chat_id, text)
    return {"ok": True}
