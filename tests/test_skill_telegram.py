import json
from io import BytesIO
from urllib.error import HTTPError, URLError

from config import config
from skills import registry
from skills import telegram_skill


def test_send_telegram_message_uses_configured_chat(monkeypatch):
    monkeypatch.setattr(config, "telegram_token", "bot-token")
    monkeypatch.setattr(config, "telegram_chat_id", "12345")
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return BytesIO(json.dumps({"ok": True}).encode())

    monkeypatch.setattr(telegram_skill, "urlopen", fake_urlopen)

    result = telegram_skill.send_telegram_message("Hello from Rose")

    assert result == "Telegram message sent to chat 12345."
    request, timeout = requests[0]
    assert timeout == 15
    assert request.full_url.endswith("/botbot-token/sendMessage")
    assert json.loads(request.data) == {
        "chat_id": "12345",
        "text": "Hello from Rose",
    }


def test_send_telegram_message_validates_configuration(monkeypatch):
    monkeypatch.setattr(config, "telegram_token", "")
    monkeypatch.setattr(config, "telegram_chat_id", "")

    assert (
        telegram_skill.send_telegram_message("Hello")
        == "Error: TELEGRAM_BOT_TOKEN is not configured."
    )


def test_send_telegram_message_reports_network_errors(monkeypatch):
    monkeypatch.setattr(config, "telegram_token", "bot-token")
    monkeypatch.setattr(config, "telegram_chat_id", "12345")
    monkeypatch.setattr(
        telegram_skill,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("offline")),
    )

    assert telegram_skill.send_telegram_message("Hello") == (
        "Error: could not send Telegram message: offline"
    )


def test_send_telegram_message_uses_only_configured_chat(monkeypatch):
    monkeypatch.setattr(config, "telegram_token", "bot-token")
    monkeypatch.setattr(config, "telegram_chat_id", "12345")
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return BytesIO(b'{"ok": true}')

    monkeypatch.setattr(
        telegram_skill,
        "urlopen", fake_urlopen
    )

    assert telegram_skill.send_telegram_message("Hello") == (
        "Telegram message sent to chat 12345."
    )
    assert json.loads(requests[0][0].data) == {
        "chat_id": "12345",
        "text": "Hello",
    }


def test_send_telegram_message_reports_telegram_api_errors(monkeypatch):
    monkeypatch.setattr(config, "telegram_token", "bot-token")
    monkeypatch.setattr(config, "telegram_chat_id", "12345")
    error = HTTPError(
        "https://api.telegram.org",
        400,
        "Bad Request",
        {},
        BytesIO(b'{"ok": false, "description": "Bad Request: chat not found"}'),
    )
    monkeypatch.setattr(
        telegram_skill,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(error),
    )

    assert telegram_skill.send_telegram_message("Hello") == (
        "Error: could not send Telegram message: Bad Request: chat not found"
    )


def test_send_telegram_message_registers_as_a_skill():
    spec = registry.get("send_telegram_message")
    assert spec.func is telegram_skill.send_telegram_message
    assert spec.dangerous is False
    assert "chat_id" not in spec.to_schema()["input_schema"]["properties"]
