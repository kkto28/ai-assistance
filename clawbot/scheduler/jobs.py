"""
Scheduled / proactive tasks (Clawbot's "reaches out when something
matters" behavior). Each job just calls the agent like any other message
source -- scheduling is transport, same as channels/ are transport.

Requires: pip install apscheduler
"""
import asyncio
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from config import config
from core.agent import Agent
from skills.browser_skill import screenshot
from skills.file_skill import WORKSPACE
from telegram import Bot

SLEEP_INTERVAL = 60 * 60

agent: Optional[Agent] = None
scheduler = BackgroundScheduler()


def _get_agent() -> Agent:
    global agent
    if agent is None:
        agent = Agent()
    return agent


def send_telegram_message(message: str) -> None:
    if not config.telegram_token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN to send scheduled Telegram messages.")
    if not config.telegram_chat_id:
        raise RuntimeError(
            "Set TELEGRAM_CHAT_ID to send scheduled Telegram messages."
        )

    async def send() -> None:
        async with Bot(token=config.telegram_token) as bot:
            await bot.send_message(chat_id=config.telegram_chat_id, text=message)

    asyncio.run(send())


def send_telegram_image(image_path: str, caption: str = "") -> None:
    if not config.telegram_token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN to send scheduled Telegram messages.")
    if not config.telegram_chat_id:
        raise RuntimeError(
            "Set TELEGRAM_CHAT_ID to send scheduled Telegram messages."
        )

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"No image at {image_path}")

    async def send() -> None:
        async with Bot(token=config.telegram_token) as bot:
            with path.open("rb") as photo:
                await bot.send_photo(
                    chat_id=config.telegram_chat_id, photo=photo, caption=caption
                )

    asyncio.run(send())


def morning_briefing() -> str:
    reply = _get_agent().handle_message(
        channel="scheduled",
        user_text="Tell me the weather today in Glasgow 2648579",
        approve_fn=lambda name, inp: True,
    )
    print(f"[scheduled] {reply}")
    if config.telegram_token and config.telegram_chat_id:
        send_telegram_message(reply)
    return reply


def bin_collection_reminder() -> str:
    if not config.bin_collection_url:
        raise RuntimeError(
            "Set CLAWBOT_BIN_COLLECTION_URL to the collection calendar URL."
        )

    result = screenshot(config.bin_collection_url)
    prefix = "Saved screenshot to workspace/"
    if not result.startswith(prefix):
        raise RuntimeError(f"Could not capture bin collection calendar: {result}")

    image_path = WORKSPACE / result.removeprefix(prefix)
    if config.telegram_token or config.telegram_chat_id:
        send_telegram_image(str(image_path), caption="Bin Collection Reminder")
    result = f"Saved bin collection calendar screenshot to {image_path}"
    print(f"[scheduled] {result}")
    return result


def clear_all_history() -> str:
    count = _get_agent().memory.clear_all_history()
    result = f"Cleared {count} messages from all history."
    print(f"[scheduled] {result}")
    return result


def schedule_interval_job(
    job,
    *,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
    job_id: Optional[str] = None,
) -> None:
    """Schedule a callable on a repeating interval before starting the scheduler."""
    if hours < 0 or minutes < 0 or seconds < 0:
        raise ValueError("Interval values cannot be negative.")
    if hours == 0 and minutes == 0 and seconds == 0:
        raise ValueError("At least one interval value must be greater than zero.")

    options = {"hours": hours, "minutes": minutes, "seconds": seconds}
    if job_id:
        options["id"] = job_id
    scheduler.add_job(job, "interval", **options)


def start():
    scheduler.add_job(
        morning_briefing, "cron", hour=9, minute=0, timezone="Europe/London"
    )
    scheduler.add_job(
        clear_all_history, "cron", hour=1, minute=0, timezone="Europe/London"
    )
    scheduler.add_job(
        bin_collection_reminder,
        "cron",
        day_of_week="wed",
        hour=8,
        minute=30,
        timezone="Europe/London",
    )
    scheduler.start()
    print(
        "Scheduler started. Jobs: morning_briefing @ 09:00, "
        "clear_all_history @ 01:00, "
        "bin collection reminder @ 08:30 on Wednesdays. "
        "Use schedule_interval_job(..., hours=1) for hourly jobs."
    )


if __name__ == "__main__":
    start()
    import time

    while True:
        time.sleep(SLEEP_INTERVAL)
