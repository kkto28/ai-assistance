from io import BytesIO
import json

from skills import google_calendar_skill


def test_resolve_relative_date_handles_tomorrow(monkeypatch):
    monkeypatch.setattr(
        google_calendar_skill,
        "_now_in_default_timezone",
        lambda: "2026-09-21T20:50:00+01:00",
    )

    result = google_calendar_skill.resolve_uk_relative_date("tomorrow")

    assert "'tomorrow' is 2026-09-22" in result


def test_resolve_relative_date_rejects_ambiguous_coming_week():
    result = google_calendar_skill.resolve_uk_relative_date("coming week")

    assert result.startswith("Error: 'coming week' is ambiguous.")
    assert "exact date" in result


def test_resolve_relative_date_accepts_uk_explicit_date():
    result = google_calendar_skill.resolve_uk_relative_date("21/09/2026")

    assert "'21/09/2026' is 2026-09-21" in result


def test_list_events_with_date_phrase_limits_results_to_that_uk_day(monkeypatch):
    requests = []
    monkeypatch.setattr(
        google_calendar_skill,
        "_now_in_default_timezone",
        lambda: "2026-09-21T20:50:00+01:00",
    )
    monkeypatch.setattr(google_calendar_skill, "_access_token", lambda: "token")

    def fake_urlopen(request, timeout):
        requests.append(request)
        return BytesIO(
            json.dumps(
                {
                    "items": [
                        {
                            "summary": "Today appointment",
                            "start": {"dateTime": "2026-09-21T10:00:00+01:00"},
                            "id": "today-id",
                        }
                    ]
                }
            ).encode()
        )

    monkeypatch.setattr(google_calendar_skill, "urlopen", fake_urlopen)

    result = google_calendar_skill.list_google_calendar_events(
        max_results="25", date_phrase="today"
    )

    assert result.startswith(
        "Google Calendar events for Monday 2026-09-21 (Europe/London):"
    )
    assert "Today appointment" in result
    assert "today-id" in result
    assert "timeMin=2026-09-21T00%3A00%3A00%2B01%3A00" in requests[0].full_url
    assert "timeMax=2026-09-22T00%3A00%3A00%2B01%3A00" in requests[0].full_url


def test_list_events_with_uk_date_uses_that_exact_day(monkeypatch):
    requests = []
    monkeypatch.setattr(google_calendar_skill, "_access_token", lambda: "token")
    monkeypatch.setattr(
        google_calendar_skill,
        "urlopen",
        lambda request, timeout: requests.append(request)
        or BytesIO(b'{"items": []}'),
    )

    result = google_calendar_skill.list_google_calendar_events(
        date_phrase="21/09/2026"
    )

    assert result == (
        "No Google Calendar events found for Monday 2026-09-21 "
        "(Europe/London)."
    )
    assert "timeMin=2026-09-21T00%3A00%3A00%2B01%3A00" in requests[0].full_url
    assert "timeMax=2026-09-22T00%3A00%3A00%2B01%3A00" in requests[0].full_url


def test_list_events_rejects_conflicting_date_filters():
    result = google_calendar_skill.list_google_calendar_events(
        time_min="2026-09-21T00:00:00+01:00", date_phrase="today"
    )

    assert result == (
        "Error: could not list Google Calendar events: "
        "date_phrase cannot be combined with time_min or time_max"
    )
