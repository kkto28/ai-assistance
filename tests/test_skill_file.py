import importlib
import sys


def load_file_skill(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAWBOT_WORKSPACE", str(tmp_path))
    sys.modules.pop("skills.file_skill", None)
    return importlib.import_module("skills.file_skill")


def test_write_then_read_round_trip(monkeypatch, tmp_path):
    file_skill = load_file_skill(monkeypatch, tmp_path)

    assert file_skill.write_file("notes/greeting.txt", "hello") == "Wrote 5 chars to notes/greeting.txt"
    assert file_skill.read_file("notes/greeting.txt") == "hello"


def test_path_traversal_returns_error_without_escaping_workspace(monkeypatch, tmp_path):
    file_skill = load_file_skill(monkeypatch, tmp_path)
    outside_path = tmp_path.parent / "escaped.txt"

    result = file_skill.write_file("../escaped.txt", "must not escape")

    assert result.startswith("Error: Path '../escaped.txt' escapes the workspace sandbox.")
    assert not outside_path.exists()


def test_list_files_on_empty_directory_returns_empty_marker(monkeypatch, tmp_path):
    file_skill = load_file_skill(monkeypatch, tmp_path)

    assert file_skill.list_files() == "(empty)"
