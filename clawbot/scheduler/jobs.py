"""
Scheduled / proactive tasks (Clawbot's "reaches out when something
matters" behavior). Each job just calls the agent like any other message
source -- scheduling is transport, same as channels/ are transport.

Requires: pip install apscheduler
"""
from apscheduler.schedulers.background import BackgroundScheduler
from core.agent import Agent

agent = Agent()
scheduler = BackgroundScheduler()


def morning_briefing():
    reply = agent.handle_message(
        channel="scheduled",
        user_text="Give me a short briefing: anything I should know this morning?",
        approve_fn=lambda name, inp: True,
    )
    print(f"[scheduled] {reply}")
    # Wire this up to a channel.send(reply) call once you have a channel
    # that supports proactive (not just reply-to) messages, e.g. Telegram's
    # bot.send_message(chat_id, reply).


def start():
    scheduler.add_job(morning_briefing, "cron", hour=8, minute=0)
    scheduler.start()
    print("Scheduler started. Jobs: morning_briefing @ 08:00")


if __name__ == "__main__":
    start()
    import time
    while True:
        time.sleep(60)
