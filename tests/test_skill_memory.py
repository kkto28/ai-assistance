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


def test_forget_removes_remembered_key(monkeypatch, tmp_path):
    memory_skill = load_memory_skill(monkeypatch, tmp_path)
    memory_skill.remember("color", "blue")

    assert memory_skill.forget("color") == "Forgot 'color'."
    assert memory_skill.recall("color") == "Nothing remembered under 'color'."


def test_forget_missing_key_returns_nothing_remembered_message(monkeypatch, tmp_path):
    memory_skill = load_memory_skill(monkeypatch, tmp_path)

    assert memory_skill.forget("missing") == "Nothing remembered under 'missing'."


def test_clear_channel_history_removes_only_requested_channel(monkeypatch, tmp_path):
    memory_skill = load_memory_skill(monkeypatch, tmp_path)
    memory_skill._memory.add_message("telegram:1", "user", "hello")
    memory_skill._memory.add_message("telegram:1", "assistant", "hi")
    memory_skill._memory.add_message("telegram:2", "user", "keep this")

    assert (
        memory_skill.clear_channel_history("telegram:1")
        == "Cleared 2 messages from channel 'telegram:1'."
    )
    assert memory_skill._memory.recent_history("telegram:1") == []
    assert memory_skill._memory.recent_history("telegram:2") == [
        {"role": "user", "content": "keep this"}
    ]


def test_memory_clear_history_returns_deleted_count(tmp_path):
    memory = Memory(str(tmp_path / "memory.db"))
    memory.add_message("cli", "user", "one")
    memory.add_message("cli", "assistant", "two")

    assert memory.clear_channel_history("cli") == 2
    assert memory.clear_channel_history("cli") == 0


def test_memory_clear_all_history_removes_messages_from_every_channel(tmp_path):
    memory = Memory(str(tmp_path / "memory.db"))
    memory.add_message("cli", "user", "one")
    memory.add_message("telegram:1", "assistant", "two")
    memory.remember("keep", "this note")

    assert memory.clear_all_history() == 2
    assert memory.recent_history("cli") == []
    assert memory.recent_history("telegram:1") == []
    assert memory.recall("keep") == "this note"
    assert memory.clear_all_history() == 0


def test_memory_forget_returns_whether_key_was_deleted(tmp_path):
    memory = Memory(str(tmp_path / "memory.db"))
    memory.remember("color", "blue")

    assert memory.forget("color") is True
    assert memory.forget("color") is False
