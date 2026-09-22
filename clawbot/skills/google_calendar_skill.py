"""Google Calendar skill using Google's Calendar REST API."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from config import config
from skills import tool

_CALENDAR_API = "https://www.googleapis.com/calendar/v3"
_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
_DEFAULT_TIMEZONE = "Europe/London"
_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _request(
    method: str,
    path: str,
    *,
    payload: dict | None = None,
    access_token: str,
) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{_CALENDAR_API}{path}",
        data=data,
        headers={
            "Accept": "application/json",
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/json",
            "User-Agent": "Clawbot Google Calendar skill",
        },
        method=method,
    )
    with urlopen(request, timeout=20) as response:
        body = response.read()
    if not body:
        return {}
    return json.loads(body.decode("utf-8"))


def _access_token() -> str:
    if config.google_calendar_access_token:
        return config.google_calendar_access_token
    if not (
        config.google_calendar_refresh_token
        and config.google_calendar_client_id
        and config.google_calendar_client_secret
    ):
        raise ValueError(
            "Google Calendar credentials are not configured. Set "
            "GOOGLE_CALENDAR_ACCESS_TOKEN or the refresh-token settings."
        )

    payload = urlencode(
        {
            "client_id": config.google_calendar_client_id,
            "client_secret": config.google_calendar_client_secret,
            "refresh_token": config.google_calendar_refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    request = Request(
        _OAUTH_TOKEN_URL,
        data=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Clawbot Google Calendar skill",
        },
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))
    token = body.get("access_token")
    if not token:
        raise ValueError("Google OAuth token response did not include an access token")
    return token


def _calendar_id(calendar_id: str) -> str:
    value = calendar_id.strip() if isinstance(calendar_id, str) else ""
    return quote(value or config.google_calendar_default_calendar, safe="")


def _event_id(event_id: str) -> str:
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("event_id must not be empty")
    return quote(event_id.strip(), safe="")


def _parse_datetime(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must not be empty")
    normalized = value.strip()
    try:
        datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"{name} must be an ISO 8601 date-time, for example "
            "'2026-09-20T14:00:00' or '2026-09-20T14:00:00+01:00'"
        ) from exc
    return normalized


def _now_in_default_timezone() -> str:
    return datetime.now(ZoneInfo(_DEFAULT_TIMEZONE)).isoformat()


def _parse_calendar_date_phrase(date_phrase: str) -> date:
    phrase = " ".join(date_phrase.lower().split())
    now = datetime.fromisoformat(_now_in_default_timezone())
    if phrase in {"yesterday", "today", "tomorrow", "day after tomorrow"}:
        offset = {
            "yesterday": -1,
            "today": 0,
            "tomorrow": 1,
            "day after tomorrow": 2,
        }[phrase]
        return now.date() + timedelta(days=offset)

    for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(phrase, date_format).date()
        except ValueError:
            continue
    raise ValueError(
        "date_phrase must be today, tomorrow, yesterday, day after tomorrow, "
        "an ISO date such as 2026-09-21, or a UK date such as 21/09/2026"
    )


def _listing_day_bounds(date_phrase: str) -> tuple[str, str]:
    target_date = _parse_calendar_date_phrase(date_phrase)

    start = datetime.combine(
        target_date, datetime.min.time(), tzinfo=ZoneInfo(_DEFAULT_TIMEZONE)
    )
    end = datetime.combine(
        target_date + timedelta(days=1),
        datetime.min.time(),
        tzinfo=ZoneInfo(_DEFAULT_TIMEZONE),
    )
    return start.isoformat(), end.isoformat()


def _listing_date_label(time_min: str) -> str:
    parsed = datetime.fromisoformat(time_min.replace("Z", "+00:00"))
    local_date = parsed.astimezone(ZoneInfo(_DEFAULT_TIMEZONE))
    return (
        f"{local_date.strftime('%A')} {local_date.date().isoformat()} "
        f"({_DEFAULT_TIMEZONE})"
    )


@tool(
    name="get_current_uk_datetime",
    description=(
        "Get the authoritative current date, time, weekday, and timezone in "
        "the UK (Europe/London). Always use this before interpreting today, "
        "tomorrow, next week, or other relative dates."
    ),
)
def get_current_uk_datetime() -> str:
    current = datetime.now(ZoneInfo(_DEFAULT_TIMEZONE))
    return (
        f"Current UK date and time: {current.isoformat()} "
        f"({current.strftime('%A')}, timezone {current.tzname()}). "
        f"Date: {current.date().isoformat()}."
    )


@tool(
    name="resolve_uk_weekday",
    description=(
        "Resolve a weekday phrase such as 'coming Wednesday' or 'next "
        "Monday' to an exact UK calendar date. Use this before creating or "
        "updating an event when the user gives a relative weekday."
    ),
)
def resolve_uk_weekday(weekday: str, occurrence: str = "coming") -> str:
    if not isinstance(weekday, str):
        return "Error: weekday must be a weekday name."
    weekday_name = weekday.strip().lower()
    if weekday_name not in _WEEKDAYS:
        return (
            "Error: weekday must be one of Monday, Tuesday, Wednesday, "
            "Thursday, Friday, Saturday, or Sunday."
        )
    occurrence_name = occurrence.strip().lower() if isinstance(occurrence, str) else ""
    if occurrence_name not in {"coming", "next"}:
        return "Error: occurrence must be 'coming' or 'next'."

    current = datetime.now(ZoneInfo(_DEFAULT_TIMEZONE))
    days_ahead = (_WEEKDAYS[weekday_name] - current.weekday()) % 7
    if occurrence_name in {"coming", "next"} and days_ahead == 0:
        days_ahead = 7
    resolved = current.date() + timedelta(days=days_ahead)
    return (
        f"{occurrence.title()} {weekday_name.title()} is "
        f"{resolved.isoformat()} ({resolved.strftime('%A')}) in "
        f"{_DEFAULT_TIMEZONE}. Current UK date is {current.date().isoformat()}."
    )


@tool(
    name="resolve_uk_relative_date",
    description=(
        "Resolve a relative date phrase to an exact UK calendar date. "
        "Supported phrases include today, tomorrow, day after tomorrow, "
        "yesterday, coming Saturday, next Monday, and weekday names. "
        "Always use this before writing a calendar event when its date is "
        "not already an explicit ISO date. If the phrase is unsupported or "
        "ambiguous, return an error and ask the user for an exact date."
    ),
)
def resolve_uk_relative_date(date_phrase: str) -> str:
    if not isinstance(date_phrase, str) or not date_phrase.strip():
        return "Error: date_phrase must not be empty."

    phrase = " ".join(date_phrase.lower().split())
    current = datetime.now(ZoneInfo(_DEFAULT_TIMEZONE))
    if phrase in {
        "yesterday",
        "today",
        "tomorrow",
        "day after tomorrow",
    } or any(
        separator in phrase for separator in ("/", "-")
    ):
        try:
            resolved = _parse_calendar_date_phrase(phrase)
        except ValueError as exc:
            return f"Error: {exc}"
        return (
            f"'{date_phrase}' is {resolved.isoformat()} "
            f"({resolved.strftime('%A')}) in {_DEFAULT_TIMEZONE}. "
            f"Current UK date is {current.date().isoformat()}."
        )

    parts = phrase.split()
    if len(parts) == 2 and parts[0] in {"coming", "next"}:
        occurrence, weekday_name = parts
    elif len(parts) == 1:
        occurrence, weekday_name = "coming", parts[0]
    else:
        return (
            "Error: unsupported relative date. Use today, tomorrow, "
            "yesterday, day after tomorrow, or a weekday such as "
            "'coming Saturday'. Ask the user for an exact date when the "
            "requested date is ambiguous."
        )
    if weekday_name in {"week", "month"}:
        return (
            f"Error: '{date_phrase}' is ambiguous. Ask the user for an "
            "exact date or date range."
        )
    if weekday_name not in _WEEKDAYS:
        return f"Error: unsupported weekday '{weekday_name}'."

    days_ahead = (_WEEKDAYS[weekday_name] - current.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    resolved = current.date() + timedelta(days=days_ahead)
    return (
        f"'{date_phrase}' is {resolved.isoformat()} "
        f"({resolved.strftime('%A')}) in {_DEFAULT_TIMEZONE}. "
        f"Current UK date is {current.date().isoformat()}."
    )


def _listing_time(value: str, name: str, default_now: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        if default_now:
            return _now_in_default_timezone()
        return ""
    normalized = _parse_datetime(value, name)
    parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(_DEFAULT_TIMEZONE))
    return parsed.isoformat()


def _event_body(
    summary: str,
    start_time: str,
    end_time: str,
    timezone: str,
    description: str,
    location: str,
) -> dict:
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("summary must not be empty")
    timezone = timezone.strip() or _DEFAULT_TIMEZONE
    start = {"dateTime": _parse_datetime(start_time, "start_time")}
    end = {"dateTime": _parse_datetime(end_time, "end_time")}
    start["timeZone"] = timezone
    end["timeZone"] = timezone
    body = {
        "summary": summary.strip(),
        "start": start,
        "end": end,
    }
    if description.strip():
        body["description"] = description.strip()
    if location.strip():
        body["location"] = location.strip()
    return body


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


@tool(
    name="create_google_calendar_event",
    description=(
        "Create an event in Google Calendar. Times must be ISO 8601 date-times "
        "without a timezone are interpreted as Europe/London by default."
    ),
)
def create_google_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    timezone: str = _DEFAULT_TIMEZONE,
    description: str = "",
    location: str = "",
    calendar_id: str = "",
) -> str:
    try:
        event = _request(
            "POST",
            f"/calendars/{_calendar_id(calendar_id)}/events",
            payload=_event_body(
                summary, start_time, end_time, timezone, description, location
            ),
            access_token=_access_token(),
        )
        return (
            f"Created Google Calendar event '{event.get('summary', summary)}' "
            f"(ID: {event.get('id', 'unknown')})."
        )
    except (HTTPError, URLError, OSError, ValueError, TimeoutError) as exc:
        return _format_error("create Google Calendar event", exc)


@tool(
    name="update_google_calendar_event",
    description=(
        "Update an existing Google Calendar event. Provide the event ID and "
        "the complete replacement summary and time range."
    ),
)
def update_google_calendar_event(
    event_id: str,
    summary: str,
    start_time: str,
    end_time: str,
    timezone: str = _DEFAULT_TIMEZONE,
    description: str = "",
    location: str = "",
    calendar_id: str = "",
) -> str:
    try:
        event = _request(
            "PUT",
            f"/calendars/{_calendar_id(calendar_id)}/events/{_event_id(event_id)}",
            payload=_event_body(
                summary, start_time, end_time, timezone, description, location
            ),
            access_token=_access_token(),
        )
        return f"Updated Google Calendar event '{event.get('summary', summary)}'."
    except (HTTPError, URLError, OSError, ValueError, TimeoutError) as exc:
        return _format_error("update Google Calendar event", exc)


@tool(
    name="delete_google_calendar_event",
    description="Delete an existing Google Calendar event by its event ID.",
)
def delete_google_calendar_event(event_id: str, calendar_id: str = "") -> str:
    try:
        _request(
            "DELETE",
            f"/calendars/{_calendar_id(calendar_id)}/events/{_event_id(event_id)}",
            access_token=_access_token(),
        )
        return f"Deleted Google Calendar event '{event_id.strip()}'."
    except (HTTPError, URLError, OSError, ValueError, TimeoutError) as exc:
        return _format_error("delete Google Calendar event", exc)


@tool(
    name="list_google_calendar_events",
    description=(
        "List Google Calendar events. Use date_phrase='today' (or another "
        "supported day or explicit date such as '21/09/2026') when the user "
        "asks for events on a specific day; "
        "results are then limited to that UK calendar day. Use this to find "
        "event IDs before updating or deleting an event. Do not use an "
        "ambiguous phrase such as 'coming week'; ask for an exact date or "
        "date range instead."
    ),
)
def list_google_calendar_events(
    max_results: str = "10",
    calendar_id: str = "",
    time_min: str = "",
    time_max: str = "",
    date_phrase: str = "",
) -> str:
    try:
        count = int(max_results)
        if count < 1 or count > 250:
            raise ValueError("max_results must be between 1 and 250")
        if date_phrase.strip() and (time_min.strip() or time_max.strip()):
            raise ValueError("date_phrase cannot be combined with time_min or time_max")
        if date_phrase.strip():
            time_min, time_max = _listing_day_bounds(date_phrase)
        start_time = _listing_time(time_min, "time_min", default_now=True)
        end_time = _listing_time(time_max, "time_max")
        parameters = {
            "maxResults": count,
            "singleEvents": "true",
            "orderBy": "startTime",
            "timeMin": start_time,
        }
        if end_time:
            parameters["timeMax"] = end_time
        query = urlencode(parameters)
        response = _request(
            "GET",
            f"/calendars/{_calendar_id(calendar_id)}/events?{query}",
            access_token=_access_token(),
        )
        events = response.get("items", [])
        date_label = _listing_date_label(start_time)
        if not events:
            return f"No Google Calendar events found for {date_label}."
        lines = [f"Google Calendar events for {date_label}:"]
        for event in events:
            start = event.get("start", {}).get(
                "dateTime", event.get("start", {}).get("date", "unknown")
            )
            lines.append(
                f"- {event.get('summary', '(untitled)')} | {start} | "
                f"ID: {event.get('id')}"
            )
        return "\n".join(lines)
    except (HTTPError, URLError, OSError, ValueError, TimeoutError) as exc:
        return _format_error("list Google Calendar events", exc)
