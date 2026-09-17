import importlib
import sys

from memory.db import Memory


def load_memory_skill(monkeypatch, tmp_path):
    database_path = tmp_path / "memory.db"
    monkeypatch.setenv("CLAWBOT_DB_PATH", str(database_path))
    sys.modules.pop("skills.memory_skill", None)
    memory_skill = importlib.import_module("skills.memory_skill")
    memory_skill._memory = Memory(str(database_path))
    return memory_skill


def test_remember_and_recall_round_trip(monkeypatch, tmp_path):
    memory_skill = load_memory_skill(monkeypatch, tmp_path)

    assert memory_skill.remember("color", "blue") == "Remembered 'color'."
    assert memory_skill.recall("color") == "blue"


def test_recall_missing_key_returns_nothing_remembered_message(monkeypatch, tmp_path):
    memory_skill = load_memory_skill(monkeypatch, tmp_path)

    assert memory_skill.recall("missing") == "Nothing remembered under 'missing'."
