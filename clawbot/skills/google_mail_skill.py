"""Google Mail inspection and approval-gated cleanup."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config import config
from skills import tool

_GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
_MAILBOX_LABELS = {
    "spam": "SPAM",
    "promotions": "CATEGORY_PROMOTIONS",
    "social": "CATEGORY_SOCIAL",
}


def _request(
    method: str,
    path: str,
    *,
    access_token: str,
    payload: dict | None = None,
) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{_GMAIL_API}{path}",
        data=data,
        headers={
            "Accept": "application/json",
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/json",
            "User-Agent": "Clawbot Google Mail skill",
        },
        method=method,
    )
    with urlopen(request, timeout=20) as response:
        body = response.read()
    return json.loads(body.decode("utf-8")) if body else {}


def _access_token() -> str:
    has_refresh_credentials = all(
        (
            config.google_mail_refresh_token,
            config.google_mail_client_id,
            config.google_mail_client_secret,
        )
    )
    if not has_refresh_credentials and config.google_mail_access_token:
        print("Using existing Google OAuth access token...")
        return config.google_mail_access_token
    if not has_refresh_credentials:
        raise ValueError(
            "Google Mail credentials are not configured. Set "
            "GOOGLE_MAIL_ACCESS_TOKEN or the refresh-token settings."
        )

    payload = urlencode(
        {
            "client_id": config.google_mail_client_id,
            "client_secret": config.google_mail_client_secret,
            "refresh_token": config.google_mail_refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    print("Requesting new Google OAuth access token...")
    request = Request(
        _OAUTH_TOKEN_URL,
        data=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Clawbot Google Mail skill",
        },
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))
    token = body.get("access_token")
    if not token:
        raise ValueError("Google OAuth token response did not include an access token")
    return token


def _format_error(action: str, exc: Exception) -> str:
    if isinstance(exc, HTTPError):
        try:
            details = json.loads(exc.read().decode("utf-8"))
            message = details.get("error", {}).get("message", str(exc))
        except (OSError, ValueError, UnicodeDecodeError):
            message = str(exc)
        return f"Error: could not {action}: {message}"
    if isinstance(exc, URLError) and getattr(exc, "reason", None):
        exc = exc.reason
    return f"Error: could not {action}: {exc}"


def _header(headers: list[dict], name: str) -> str:
    wanted = name.lower()
    for header in headers:
        if header.get("name", "").lower() == wanted:
            return header.get("value", "")
    return ""


def _parse_categories(categories: str) -> list[str]:
    requested = [part.strip().lower() for part in categories.split(",") if part.strip()]
    if not requested:
        requested = list(_MAILBOX_LABELS)
    invalid = [category for category in requested if category not in _MAILBOX_LABELS]
    if invalid:
        raise ValueError(
            "categories must contain only spam, promotions, and social"
        )
    return requested


def _list_messages(label_id: str, max_results: int, access_token: str) -> list[dict]:
    query = urlencode(
        {"labelIds": label_id, "maxResults": max_results, "includeSpamTrash": "true"}
    )
    response = _request("GET", f"/messages?{query}", access_token=access_token)
    return response.get("messages", [])


def _message_summary(message_id: str, access_token: str) -> dict:
    query = urlencode({"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]}, doseq=True)
    message = _request(
        "GET", f"/messages/{message_id}?{query}", access_token=access_token
    )
    headers = message.get("payload", {}).get("headers", [])
    return {
        "id": message_id,
        "thread_id": message.get("threadId", ""),
        "from": _header(headers, "From"),
        "subject": _header(headers, "Subject") or "(no subject)",
        "date": _header(headers, "Date"),
    }


@tool(
    name="inspect_google_mail",
    description=(
        "Inspect Google Mail messages in Spam, Promotions, and Social without "
        "changing anything. This is read-only and does not require approval. "
        "Return counts and message IDs for review before any separate cleanup."
    ),
)
def inspect_google_mail(categories: str = "spam,promotions,social", max_results: str = "20") -> str:
    try:
        count = int(max_results)
        if count < 1 or count > 100:
            raise ValueError("max_results must be between 1 and 100")
        selected = _parse_categories(categories)
        print(
            f"Inspecting Google Mail categories: {', '.join(selected)} "
            f"(max {count} messages each)..."
        )
        token = _access_token()
        category_counts = []
        review_items = []
        for category in selected:
            messages = _list_messages(_MAILBOX_LABELS[category], count, token)
            summaries = [
                _message_summary(message["id"], token)
                for message in messages
                if message.get("id")
            ]
            category_counts.append((category.title(), len(summaries)))
            for index, message in enumerate(summaries, start=1):
                review_items.append(
                    f"{category.title()} {index}. {message['subject']}\n"
                    f"   From: {message['from'] or '(unknown sender)'}\n"
                    f"   Date: {message['date'] or '(no date)'}\n"
                    f"   Message ID: {message['id']}"
                )

        total = sum(count for _, count in category_counts)
        lines = [
            "Google Mail review (read-only)",
            f"Categories: {', '.join(selected)}",
            f"Limit: {count} messages per category",
            "",
            "Summary:",
            *[
                f"- {category}: {message_count} found"
                for category, message_count in category_counts
            ],
            f"- Total: {total} message(s)",
            "",
            "Review candidates:",
        ]
        lines.extend(review_items or ["- No messages found in the selected categories."])
        lines.extend(
            [
                "",
                "Next actions:",
                "- No messages were changed.",
                "- To clean up, provide the exact Message ID values to move to "
                "Trash and confirm with APPROVE.",
            ]
        )
        return "\n".join(lines)
    except (HTTPError, URLError, OSError, ValueError, TimeoutError) as exc:
        return _format_error("inspect Google Mail", exc)


@tool(
    name="cleanup_google_mail",
    description=(
        "Move specific Google Mail messages to Trash. This is a destructive "
        "mailbox mutation and requires both the normal tool approval prompt "
        "and confirmation='APPROVE'. Only use IDs returned by a preceding "
        "inspect_google_mail review; never clean up an entire category."
    ),
    dangerous=True,
)
def cleanup_google_mail(message_ids: str, confirmation: str) -> str:
    try:
        if confirmation.strip().upper() != "APPROVE":
            return "Cleanup not performed: confirmation must be exactly 'APPROVE'."
        ids = [message_id.strip() for message_id in message_ids.split(",") if message_id.strip()]
        if not ids:
            raise ValueError("message_ids must contain at least one Gmail message ID")
        if len(ids) > 100:
            raise ValueError("cleanup_google_mail accepts at most 100 message IDs")
        token = _access_token()
        for message_id in ids:
            _request("POST", f"/messages/{message_id}/trash", access_token=token)
        return (
            f"Moved {len(ids)} Google Mail message(s) to Trash. "
            "They remain recoverable in Gmail until permanently deleted."
        )
    except (HTTPError, URLError, OSError, ValueError, TimeoutError) as exc:
        return _format_error("clean up Google Mail", exc)
