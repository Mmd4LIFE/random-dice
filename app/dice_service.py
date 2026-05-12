import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models import DiceRollLog, User

logger = logging.getLogger(__name__)


def upsert_user(db: Session, from_user: dict[str, Any]) -> User:
    tid = int(from_user["id"])
    user = db.query(User).filter(User.telegram_user_id == tid).one_or_none()
    if user is None:
        user = User(
            telegram_user_id=tid,
            username=from_user.get("username"),
            first_name=from_user.get("first_name"),
            last_name=from_user.get("last_name"),
            language_code=from_user.get("language_code"),
        )
        db.add(user)
        db.flush()
        logger.info(
            "user_created telegram_user_id=%s username=%s db_user_id=%s",
            tid,
            user.username,
            user.id,
        )
    else:
        user.username = from_user.get("username")
        user.first_name = from_user.get("first_name")
        user.last_name = from_user.get("last_name")
        user.language_code = from_user.get("language_code")
        logger.debug("user_touch telegram_user_id=%s db_user_id=%s", tid, user.id)
    return user


def log_dice_roll(
    db: Session,
    *,
    user: User,
    dice_emoji: str,
    dice_value: int,
    chat_id: int,
    message_id: int,
) -> DiceRollLog:
    row = DiceRollLog(
        user_id=user.id,
        dice_emoji=dice_emoji,
        dice_value=dice_value,
        telegram_chat_id=chat_id,
        telegram_message_id=message_id,
    )
    db.add(row)
    db.flush()
    logger.info(
        "dice_roll_logged telegram_user_id=%s db_user_id=%s log_id=%s emoji=%r value=%s chat_id=%s message_id=%s",
        user.telegram_user_id,
        user.id,
        row.id,
        dice_emoji,
        dice_value,
        chat_id,
        message_id,
    )
    return row


def reply_text_for_dice(emoji: str, value: int) -> str:
    return f"Your roll: {value}\nDice type: {emoji}"
