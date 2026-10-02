import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.insert(0, "clawbot")

from scheduler import jobs


def test_send_telegram_message_requires_token_and_chat_id(monkeypatch):
    monkeypatch.setattr(
        jobs,
        "config",
        SimpleNamespace(telegram_token="", telegram_chat_id=""),
    )

    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        jobs.send_telegram_message("hello")


def test_send_telegram_message_uses_configured_bot(monkeypatch):
    bot = Mock()
    bot.send_message = AsyncMock()
    bot_context = Mock()
    bot_context.__aenter__ = AsyncMock(return_value=bot)
    bot_context.__aexit__ = AsyncMock(return_value=False)
    bot_factory = Mock(return_value=bot_context)
    monkeypatch.setattr(jobs, "Bot", bot_factory)
    monkeypatch.setattr(
        jobs,
        "config",
        SimpleNamespace(telegram_token="token", telegram_chat_id="123"),
    )

    jobs.send_telegram_message("hello")

    bot_factory.assert_called_once_with(token="token")
    bot.send_message.assert_called_once_with(chat_id="123", text="hello")


def test_send_telegram_image_uses_configured_bot_and_file(monkeypatch, tmp_path):
    image = tmp_path / "calendar.png"
    image.write_bytes(b"png-data")
    sent_photo = {}
    bot = Mock()

    async def send_photo(**kwargs):
        sent_photo["contents"] = kwargs["photo"].read()

    bot.send_photo = AsyncMock(side_effect=send_photo)
    bot_context = Mock()
    bot_context.__aenter__ = AsyncMock(return_value=bot)
    bot_context.__aexit__ = AsyncMock(return_value=False)
    bot_factory = Mock(return_value=bot_context)
    monkeypatch.setattr(jobs, "Bot", bot_factory)
    monkeypatch.setattr(
        jobs,
        "config",
        SimpleNamespace(telegram_token="token", telegram_chat_id="123"),
    )

    jobs.send_telegram_image(str(image), caption="Calendar")

    bot_factory.assert_called_once_with(token="token")
    bot.send_photo.assert_called_once()
    kwargs = bot.send_photo.call_args.kwargs
    assert kwargs["chat_id"] == "123"
    assert kwargs["caption"] == "Calendar"
    assert sent_photo["contents"] == b"png-data"


def test_send_telegram_image_reports_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(
        jobs,
        "config",
        SimpleNamespace(telegram_token="token", telegram_chat_id="123"),
    )

    with pytest.raises(FileNotFoundError, match="No image"):
        jobs.send_telegram_image(str(tmp_path / "missing.png"))


def test_send_telegram_image_rejects_partial_telegram_configuration(
    monkeypatch, tmp_path
):
    image = tmp_path / "calendar.png"
    image.write_bytes(b"png-data")
    monkeypatch.setattr(
        jobs,
        "config",
        SimpleNamespace(telegram_token="token", telegram_chat_id=""),
    )

    with pytest.raises(RuntimeError, match="TELEGRAM_CHAT_ID"):
        jobs.send_telegram_image(str(image))


def test_morning_briefing_sends_reply_to_telegram_when_configured(monkeypatch):
    agent = Mock()
    agent.handle_message.return_value = "Good morning."
    send_message = Mock()
    monkeypatch.setattr(jobs, "agent", agent)
    monkeypatch.setattr(jobs, "send_telegram_message", send_message)
    monkeypatch.setattr(
        jobs,
        "config",
        SimpleNamespace(telegram_token="token", telegram_chat_id="123"),
    )

    result = jobs.morning_briefing()

    assert result == "Good morning."
    send_message.assert_called_once_with("Good morning.")


def test_bin_collection_reminder_captures_and_sends_calendar_screenshot(
    monkeypatch, tmp_path
):
    screenshot_path = tmp_path / "calendar.png"
    screenshot_path.write_bytes(b"png-data")
    monkeypatch.setattr(jobs, "WORKSPACE", tmp_path)
    monkeypatch.setattr(
        jobs,
        "screenshot",
        Mock(return_value="Saved screenshot to workspace/calendar.png"),
    )
    send_image = Mock()
    monkeypatch.setattr(jobs, "send_telegram_image", send_image)
    monkeypatch.setattr(
        jobs,
        "config",
        SimpleNamespace(
            bin_collection_url="https://example.com/calendar",
            telegram_token="token",
            telegram_chat_id="123",
        ),
    )

    result = jobs.bin_collection_reminder()

    jobs.screenshot.assert_called_once_with("https://example.com/calendar")
    send_image.assert_called_once_with(
        str(screenshot_path), caption="Bin Collection Reminder"
    )
    assert result == f"Saved bin collection calendar screenshot to {screenshot_path}"


def test_bin_collection_reminder_requires_calendar_url(monkeypatch):
    monkeypatch.setattr(jobs, "config", SimpleNamespace(bin_collection_url=""))

    with pytest.raises(RuntimeError, match="CLAWBOT_BIN_COLLECTION_URL"):
        jobs.bin_collection_reminder()


def test_bin_collection_reminder_reports_screenshot_failure(monkeypatch):
    monkeypatch.setattr(
        jobs, "screenshot", Mock(return_value="Error: Chrome unavailable")
    )
    monkeypatch.setattr(
        jobs,
        "config",
        SimpleNamespace(
            bin_collection_url="https://example.com/calendar",
            telegram_token="",
            telegram_chat_id="",
        ),
    )

    with pytest.raises(RuntimeError, match="Chrome unavailable"):
        jobs.bin_collection_reminder()


def test_clear_all_history_removes_messages_from_all_channels(monkeypatch):
    agent = Mock()
    agent.memory.clear_all_history.return_value = 4
    monkeypatch.setattr(jobs, "agent", agent)

    result = jobs.clear_all_history()

    assert result == "Cleared 4 messages from all history."
    agent.memory.clear_all_history.assert_called_once_with()


def test_schedule_interval_job_supports_hourly_jobs(monkeypatch):
    scheduler = Mock()
    monkeypatch.setattr(jobs, "scheduler", scheduler)
    task = Mock()

    jobs.schedule_interval_job(task, hours=1, job_id="hourly-task")

    scheduler.add_job.assert_called_once_with(
        task,
        "interval",
        hours=1,
        minutes=0,
        seconds=0,
        id="hourly-task",
    )


@pytest.mark.parametrize(
    "interval",
    [
        {"hours": -1},
        {"minutes": -1},
        {"seconds": -1},
        {},
    ],
)
def test_schedule_interval_job_rejects_invalid_intervals(monkeypatch, interval):
    monkeypatch.setattr(jobs, "scheduler", Mock())

    with pytest.raises(ValueError):
        jobs.schedule_interval_job(Mock(), **interval)


def test_start_schedules_history_cleanup_at_one_am(monkeypatch):
    scheduler = Mock()
    monkeypatch.setattr(jobs, "scheduler", scheduler)

    jobs.start()

    scheduler.add_job.assert_any_call(
        jobs.clear_all_history,
        "cron",
        hour=1,
        minute=0,
        timezone="Europe/London",
    )
    scheduler.add_job.assert_any_call(
        jobs.morning_briefing,
        "cron",
        hour=9,
        minute=0,
        timezone="Europe/London",
    )
    scheduler.add_job.assert_any_call(
        jobs.bin_collection_reminder,
        "cron",
        day_of_week="wed",
        hour=8,
        minute=30,
        timezone="Europe/London",
    )
    scheduler.start.assert_called_once_with()
