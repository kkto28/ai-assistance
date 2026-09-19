"""
Scheduled / proactive tasks (Clawbot's "reaches out when something
matters" behavior). Each job just calls the agent like any other message
source -- scheduling is transport, same as channels/ are transport.

Requires: pip install apscheduler
"""
import asyncio
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from core.agent import Agent
from config import config
from telegram import Bot

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


def morning_briefing() -> str:
    reply = _get_agent().handle_message(
        channel="scheduled",
        user_text="Just tell me the weather today in Glasgow 2648579",
        approve_fn=lambda name, inp: True,
    )
    print(f"[scheduled] {reply}")
    if config.telegram_token and config.telegram_chat_id:
        send_telegram_message(reply)
    return reply


def clear_all_history() -> str:
    count = _get_agent().memory.clear_all_history()
    result = f"Cleared {count} messages from all history."
    print(f"[scheduled] {result}")
    return result


def start():
    scheduler.add_job(morning_briefing, "cron", hour=00, minute=40)
    scheduler.add_job(clear_all_history, "cron", hour=1, minute=10)
    scheduler.start()
    print(
        "Scheduler started. Jobs: morning_briefing @ 00:40, "
        "clear_all_history @ 01:10"
    )


if __name__ == "__main__":
    start()
    import time
    while True:
        time.sleep(60)
