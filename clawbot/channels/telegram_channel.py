"""
Telegram channel adapter.

Notice this file knows nothing about tools, skills, or the LLM -- it only
translates Telegram messages into Agent.handle_message() calls and sends
the reply back. This is the pattern for every new channel you add
(discord_channel.py, slack_channel.py, ...): keep the transport dumb.

Requires: pip install python-telegram-bot
"""
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

from config import config
from core.agent import Agent

agent = Agent()


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = str(update.effective_chat.id)

    # Dangerous tool calls fall back to auto-approve on Telegram for now --
    # wiring up an inline "Approve/Deny" button pair is the natural next
    # step (see Application docs for InlineKeyboardMarkup).
    reply = agent.handle_message(
        channel=f"telegram:{chat_id}",
        user_text=user_text,
        approve_fn=lambda name, inp: True,
    )
    print(f"Telegram chat {chat_id} reply: {reply}")
    await update.message.reply_text(reply)


def run():
    if not config.telegram_token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN in your environment first.")
    app = Application.builder().token(config.telegram_token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    print(f"{config.name} Telegram channel running...")
    app.run_polling()


if __name__ == "__main__":
    run()
