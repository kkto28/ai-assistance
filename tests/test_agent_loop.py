from types import SimpleNamespace

import pytest

from config import config
from core.agent import Agent
from skills import ToolSpec, registry


@pytest.fixture
def agent(monkeypatch):
    monkeypatch.setattr(config, "model_provider", "ollama")
    monkeypatch.setattr(config, "model_name", "test-model")
    monkeypatch.setattr(config, "name", "Test Agent")
    monkeypatch.setattr(
        registry,
        "_tools",
        {
            "add_note": ToolSpec(
                name="add_note",
                description="Add a note.",
                dangerous=False,
                func=lambda note: f"saved: {note}",
            )
        },
    )
    instance = Agent.__new__(Agent)
    instance._client = SimpleNamespace()
    return instance


def test_ollama_loop_executes_tool_calls_until_final_response(agent):
    tool_call_message = SimpleNamespace(
        content="",
        tool_calls=[
            SimpleNamespace(
                function=SimpleNamespace(
                    name="add_note",
                    arguments={"note": "remember this"},
                )
            )
        ],
    )
    final_message = SimpleNamespace(content="Done", tool_calls=[])
    responses = iter(
        [
            SimpleNamespace(message=tool_call_message),
            SimpleNamespace(message=final_message),
        ]
    )
    requests = []

    def chat(**request):
        requests.append(request)
        return next(responses)

    agent._client.chat = chat

    result = agent._run_loop(
        [{"role": "user", "content": "Save this"}],
        lambda *_: True,
    )

    assert result == "Done"
    assert requests[0]["tools"][0]["function"]["name"] == "add_note"
    assert requests[1]["messages"][-1] == {
        "role": "tool",
        "content": "saved: remember this",
        "tool_name": "add_note",
    }


def test_ollama_loop_stops_after_max_tool_call_turns(agent):
    response = SimpleNamespace(
        message=SimpleNamespace(
            content="",
            tool_calls=[
                SimpleNamespace(
                    function=SimpleNamespace(
                        name="add_note",
                        arguments={"note": "again"},
                    )
                )
            ],
        )
    )
    agent._client.chat = lambda **_: response

    result = agent._run_loop([], lambda *_: True)

    assert result == "Stopped after reaching the max tool-call turns for this message."


def test_ollama_loop_repairs_refusal_for_action_request(agent):
    refusal = SimpleNamespace(
        content="I cannot execute commands.",
        tool_calls=[],
    )
    tool_call = SimpleNamespace(
        content="",
        tool_calls=[
            SimpleNamespace(
                function=SimpleNamespace(
                    name="add_note",
                    arguments={"note": "saved after retry"},
                )
            )
        ],
    )
    final = SimpleNamespace(content="Done", tool_calls=[])
    responses = iter(
        [
            SimpleNamespace(message=refusal),
            SimpleNamespace(message=tool_call),
            SimpleNamespace(message=final),
        ]
    )
    requests = []
    agent._client.chat = lambda **request: (
        requests.append(request) or next(responses)
    )

    result = agent._run_loop(
        [{"role": "user", "content": "Run the requested action"}],
        lambda *_: True,
    )

    assert result == "Done"
    assert any(
        message["content"].startswith("You must execute")
        for message in requests[1]["messages"]
        if message["role"] == "user"
    )
