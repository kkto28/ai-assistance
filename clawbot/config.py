"""
Central configuration for Clawbot.
Loads settings from environment variables so the same code runs
locally, on a VPS, or in a container without changes.
"""
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # --- Agent identity ---
    name: str = os.getenv("CLAWBOT_NAME", "Rose")

    # --- Model backend ---
    # "anthropic" | "openai" | "ollama"
    model_provider: str = os.getenv("CLAWBOT_MODEL_PROVIDER", "ollama")
    # "gpt-5-nano" | "qwen3:8b"
    model_name: str = os.getenv("CLAWBOT_MODEL_NAME", "qwen3:8b")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # --- Storage ---
    db_path: str = os.getenv("CLAWBOT_DB_PATH", "clawbot.db")

    # --- Safety ---
    # If False, every tool call that mutates the system (shell, file write)
    # requires interactive approval before it runs.
    auto_approve: bool = os.getenv("CLAWBOT_AUTO_APPROVE", "false").lower() == "true"

    # --- Channels ---
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    discord_token: str = os.getenv("DISCORD_BOT_TOKEN", "")

    # --- Skills ---
    # Skill modules to load at startup. Add your own module names here.
    enabled_skills: list = field(default_factory=lambda: [
        "skills.shell_skill",
        "skills.file_skill",
        "skills.memory_skill",
        "skills.weather_skill",
        "skills.telegram_skill",
    ])


config = Config()
