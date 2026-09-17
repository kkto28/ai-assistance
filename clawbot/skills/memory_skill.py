"""
Memory skill: lets the agent save and retrieve durable notes about the
user across sessions (preferences, ongoing tasks, facts to remember).
"""
from config import config
from memory.db import Memory
from skills import tool

_memory = Memory(config.db_path)


@tool(name="remember", description="Save a fact or preference for later, under a short key.")
def remember(key: str, value: str) -> str:
    _memory.remember(key, value)
    return f"Remembered '{key}'."


@tool(name="recall", description="Look up a previously remembered fact by key.")
def recall(key: str) -> str:
    value = _memory.recall(key)
    return value if value is not None else f"Nothing remembered under '{key}'."
