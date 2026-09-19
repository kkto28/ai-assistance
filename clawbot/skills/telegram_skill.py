"""Send proactive messages through the configured Telegram bot."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import config
from skills import tool

_TELEGRAM_MESSAGE_LIMIT = 4096


def _telegram_request(message: str, chat_id: str) -> dict:
    url = f"https://api.telegram.org/bot{config.telegram_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Clawbot Telegram skill",
        },
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        body = json.loads(response.read().decode("utf-8"))
    if not body.get("ok"):
        description = body.get("description", "Telegram rejected the message")
        raise RuntimeError(description)
    return body


@tool(
    name="send_telegram_message",
    description=(
        "Send a message to the configured Telegram chat. Use this when the "
        "user asks you to notify or message them on Telegram."
    ),
    dangerous=True,
)
def send_telegram_message(message: str) -> str:
    """Send a message to the configured TELEGRAM_CHAT_ID."""
    if not config.telegram_token:
        return "Error: TELEGRAM_BOT_TOKEN is not configured."
    target_chat_id = str(config.telegram_chat_id).strip()
    if not target_chat_id:
        return "Error: TELEGRAM_CHAT_ID is not configured."
    if not isinstance(message, str) or not message.strip():
        return "Error: message must not be empty."
    if len(message) > _TELEGRAM_MESSAGE_LIMIT:
        return (
            f"Error: message exceeds Telegram's "
            f"{_TELEGRAM_MESSAGE_LIMIT}-character limit."
        )

    try:
        _telegram_request(message, target_chat_id)
    except HTTPError as exc:
        try:
            details = json.loads(exc.read().decode("utf-8"))
            message = details.get("description", str(exc))
        except (OSError, ValueError, UnicodeDecodeError):
            message = str(exc)
        return f"Error: could not send Telegram message: {message}"
    except (URLError, TimeoutError, OSError, RuntimeError, ValueError) as exc:
        if isinstance(exc, URLError) and getattr(exc, "reason", None):
            exc = exc.reason
        return f"Error: could not send Telegram message: {exc}"
    return f"Telegram message sent to chat {target_chat_id}."
