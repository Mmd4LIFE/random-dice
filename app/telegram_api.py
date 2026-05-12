import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)
BASE = f"https://api.telegram.org/bot{settings.bot_token}"


async def send_message(chat_id: int, text: str) -> dict[str, Any] | None:
    url = f"{BASE}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, json=payload)
        data = r.json()
        if not data.get("ok"):
            logger.error(
                "telegram_send_message_failed",
                extra={
                    "chat_id": chat_id,
                    "status_code": r.status_code,
                    "response": data,
                },
            )
            return None
        return data.get("result")


async def set_webhook(url: str, secret_token: str | None = None) -> bool:
    payload: dict[str, Any] = {"url": url}
    if secret_token:
        payload["secret_token"] = secret_token
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{BASE}/setWebhook", json=payload)
        data = r.json()
        ok = bool(data.get("ok"))
        if not ok:
            logger.error("set_webhook_failed", extra={"response": data})
        return ok
