from io import BytesIO
import json

from skills import google_mail_skill


def test_inspect_mail_reports_selected_categories_and_message_metadata(monkeypatch):
    requests = []
    monkeypatch.setattr(google_mail_skill, "_access_token", lambda: "token")

    def fake_urlopen(request, timeout):
        requests.append(request)
        if "/messages?" in request.full_url:
            return BytesIO(b'{"messages": [{"id": "message-1"}]}')
        return BytesIO(
            json.dumps(
                {
                    "threadId": "thread-1",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Sale"},
                            {"name": "From", "value": "shop@example.com"},
                            {"name": "Date", "value": "Tue, 22 Sep 2026 10:00:00 +0000"},
                        ]
                    },
                }
            ).encode()
        )

    monkeypatch.setattr(google_mail_skill, "urlopen", fake_urlopen)

    result = google_mail_skill.inspect_google_mail("promotions", "5")

    assert "Promotions: 1 found" in result
    assert "Promotions 1. Sale" in result
    assert "From: shop@example.com" in result
    assert "Message ID: message-1" in result
    assert "No messages were changed." in result
    assert "CATEGORY_PROMOTIONS" in requests[0].full_url


def test_inspect_mail_defaults_to_twenty_results(monkeypatch):
    requests = []
    monkeypatch.setattr(google_mail_skill, "_access_token", lambda: "token")
    monkeypatch.setattr(
        google_mail_skill,
        "_list_messages",
        lambda label_id, max_results, access_token: (
            requests.append((label_id, max_results, access_token)) or []
        ),
    )

    result = google_mail_skill.inspect_google_mail("spam")

    assert "Limit: 20 messages per category" in result
    assert requests == [("SPAM", 20, "token")]


def test_cleanup_requires_explicit_confirmation(monkeypatch):
    monkeypatch.setattr(
        google_mail_skill,
        "_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("request should not be made")
        ),
    )

    result = google_mail_skill.cleanup_google_mail("message-1", "yes")

    assert result == "Cleanup not performed: confirmation must be exactly 'APPROVE'."


def test_cleanup_moves_only_selected_messages_to_trash(monkeypatch):
    requests = []
    monkeypatch.setattr(google_mail_skill, "_access_token", lambda: "token")
    monkeypatch.setattr(
        google_mail_skill,
        "_request",
        lambda method, path, **kwargs: requests.append((method, path, kwargs)) or {},
    )

    result = google_mail_skill.cleanup_google_mail(
        "message-1, message-2", "APPROVE"
    )

    assert result.startswith("Moved 2 Google Mail message(s) to Trash.")
    assert [path for _, path, _ in requests] == [
        "/messages/message-1/trash",
        "/messages/message-2/trash",
    ]
    assert all(method == "POST" for method, _, _ in requests)


def test_cleanup_is_registered_as_dangerous():
    from skills import registry

    assert registry.get("cleanup_google_mail").dangerous is True


def test_inspection_is_not_registered_as_dangerous():
    from skills import registry

    assert registry.get("inspect_google_mail").dangerous is False


def test_access_token_is_only_used_when_refresh_credentials_are_unavailable(
    monkeypatch,
):
    monkeypatch.setattr(google_mail_skill.config, "google_mail_access_token", "access")
    monkeypatch.setattr(google_mail_skill.config, "google_mail_refresh_token", "")
    monkeypatch.setattr(google_mail_skill.config, "google_mail_client_id", "")
    monkeypatch.setattr(google_mail_skill.config, "google_mail_client_secret", "")

    assert google_mail_skill._access_token() == "access"


def test_refresh_credentials_take_precedence_over_stale_access_token(
    monkeypatch,
):
    requests = []
    monkeypatch.setattr(google_mail_skill.config, "google_mail_access_token", "stale")
    monkeypatch.setattr(
        google_mail_skill.config, "google_mail_refresh_token", "refresh"
    )
    monkeypatch.setattr(google_mail_skill.config, "google_mail_client_id", "client")
    monkeypatch.setattr(
        google_mail_skill.config, "google_mail_client_secret", "secret"
    )

    def fake_urlopen(request, timeout):
        requests.append(request)
        return BytesIO(b'{"access_token": "fresh"}')

    monkeypatch.setattr(google_mail_skill, "urlopen", fake_urlopen)

    assert google_mail_skill._access_token() == "fresh"
    assert requests[0].full_url == "https://oauth2.googleapis.com/token"
