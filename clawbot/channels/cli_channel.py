"""
Terminal channel. Simplest possible adapter -- good for local dev and
as a template for the next channel you add.
"""
from core.agent import Agent
from config import config


def run():
    agent = Agent()
    print(f"{config.name} CLI — type 'exit' to quit.\n")
    while True:
        user_text = input("you> ").strip()
        if user_text.lower() in ("exit", "quit"):
            break
        if not user_text:
            continue
        reply = agent.handle_message(channel="cli", user_text=user_text)
        print(f"{config.name.lower()}> {reply}\n")


if __name__ == "__main__":
    run()
