from unittest.mock import Mock

import skills.shell_skill as shell_skill


def test_run_shell_passes_command_to_subprocess(monkeypatch):
    completed = Mock(stdout="output\n", stderr="")
    run = Mock(return_value=completed)
    monkeypatch.setattr(shell_skill.subprocess, "run", run)

    result = shell_skill.run_shell("printf hello")

    assert result == "output"
    run.assert_called_once_with(
        "printf hello",
        shell=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_run_shell_timeout_returns_expected_error(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise shell_skill.subprocess.TimeoutExpired("sleep 31", 30)

    monkeypatch.setattr(shell_skill.subprocess, "run", raise_timeout)

    assert shell_skill.run_shell("sleep 31") == "Error: command timed out after 30s"


def test_run_shell_appends_stderr_when_present(monkeypatch):
    monkeypatch.setattr(
        shell_skill.subprocess,
        "run",
        Mock(return_value=Mock(stdout="output\n", stderr="warning\n")),
    )

    assert shell_skill.run_shell("command") == "output\n[stderr]\nwarning"
