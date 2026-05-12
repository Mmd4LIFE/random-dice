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


async def delete_webhook(drop_pending_updates: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if drop_pending_updates:
        payload["drop_pending_updates"] = True
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{BASE}/deleteWebhook", json=payload)
        data = r.json()
        if not data.get("ok"):
            logger.error("delete_webhook_failed response=%s", data)
        return data


async def get_updates(*, offset: int | None = None, timeout: int = 50) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    async with httpx.AsyncClient(timeout=timeout + 10.0) as client:
        r = await client.get(f"{BASE}/getUpdates", params=params)
        data = r.json()
        if not data.get("ok"):
            logger.error("get_updates_failed status=%s body=%s", r.status_code, data)
            return []
        return list(data.get("result") or [])


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
