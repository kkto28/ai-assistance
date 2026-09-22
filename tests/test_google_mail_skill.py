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

    assert "Promotions: 1 message(s)" in result
    assert "ID: message-1 | Sale | shop@example.com" in result
    assert "No messages were changed." in result
    assert "CATEGORY_PROMOTIONS" in requests[0].full_url


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
