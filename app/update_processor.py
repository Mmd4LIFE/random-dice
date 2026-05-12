import logging
from typing import Any

from sqlalchemy.orm import Session

from app.dice_service import log_dice_roll, reply_text_for_dice, upsert_user
from app.telegram_api import send_message

logger = logging.getLogger(__name__)


async def process_telegram_update(db: Session, update: dict[str, Any], *, source: str) -> None:
    upd_id = update.get("update_id")
    logger.info("%s_received update_id=%s", source, upd_id)

    message = update.get("message") or update.get("edited_message")
    if not message:
        logger.info("%s_skip_no_message update_id=%s", source, upd_id)
        return

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
        logger.info("%s_handled_start update_id=%s chat_id=%s", source, upd_id, chat_id)
        return

    dice = message.get("dice")
    if not dice:
        logger.info("%s_skip_not_dice_or_start update_id=%s chat_id=%s", source, upd_id, chat_id)
        return

    from_user = message.get("from")
    if not from_user or chat_id is None:
        logger.warning(
            "%s_dice_missing_from_or_chat update_id=%s chat_id=%s",
            source,
            upd_id,
            chat_id,
        )
        return

    dice_emoji = dice.get("emoji") or "🎲"
    dice_value = int(dice["value"])

    # Animated dice often arrives first with value 0; final value comes in an edited_message.
    if dice_value == 0:
        logger.info(
            "%s_dice_pending_zero update_id=%s chat_id=%s emoji=%r — waiting for final edit",
            source,
            upd_id,
            chat_id,
            dice_emoji,
        )
        return

    chat_id_i = int(chat_id)
    message_id = int(message["message_id"])

    user = upsert_user(db, from_user)
    log_dice_roll(
        db,
        user=user,
        dice_emoji=dice_emoji,
        dice_value=dice_value,
        chat_id=chat_id_i,
        message_id=message_id,
    )
    db.commit()

    reply = reply_text_for_dice(dice_emoji, dice_value)
    await send_message(chat_id_i, reply)
    logger.info(
        "%s_replied_dice update_id=%s chat_id=%s emoji=%r value=%s",
        source,
        upd_id,
        chat_id_i,
        dice_emoji,
        dice_value,
    )
