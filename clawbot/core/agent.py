"""
The agent's reasoning loop.

This is a hand-rolled tool-calling loop rather than LangGraph, kept
intentionally simple so the control flow is easy to read end to end:

    user message -> LLM -> (tool call? -> run tool -> feed result back) -> repeat
                         -> (final text? -> return to caller)

Swap this file for a LangGraph StateGraph later if you need branching,
persistence-across-crashes, or human-approval nodes baked into the graph
itself -- nothing outside core/agent.py needs to change, since channels/
and skills/ only depend on Agent.handle_message().
"""
from __future__ import annotations
import json
import re

from config import config
from memory.db import Memory
from skills import registry


class Agent:
    def __init__(self):
        registry.load(config.enabled_skills)
        self.memory = Memory(config.db_path)
        self._client = self._build_client()

    def _build_client(self):
        if config.model_provider == "anthropic":
            import anthropic
            return anthropic.Anthropic(api_key=config.anthropic_api_key)
        elif config.model_provider == "openai":
            import openai
            return openai.OpenAI(api_key=config.openai_api_key)
        elif config.model_provider == "ollama":
            import ollama
            return ollama.Client(host=config.ollama_host)
        raise ValueError(f"Unknown model_provider: {config.model_provider}")

    def handle_message(self, channel: str, user_text: str, approve_fn=None) -> str:
        """
        approve_fn: optional callable(tool_name, tool_input) -> bool.
        Used to gate dangerous tools when config.auto_approve is False.
        Channels can pass their own (e.g. ask on Telegram); the CLI
        default just prompts in the terminal.
        """
        self.memory.add_message(channel, "user", user_text)
        history = self.memory.recent_history(channel)
        messages = [{"role": m["role"], "content": m["content"]} for m in history]

        final_text = self._run_loop(messages, approve_fn or self._cli_approve)
        self.memory.add_message(channel, "assistant", final_text)
        return final_text

    def _run_loop(self, messages: list[dict], approve_fn) -> str:
        if config.model_provider == "openai":
            return self._run_openai_loop(messages, approve_fn)
        if config.model_provider == "ollama":
            return self._run_ollama_loop(messages, approve_fn)
        return self._run_anthropic_loop(messages, approve_fn)

    def _run_anthropic_loop(self, messages: list[dict], approve_fn) -> str:
        max_turns = 8
        for _ in range(max_turns):
            response = self._client.messages.create(
                model=config.model_name,
                max_tokens=1024,
                system=self._system_prompt(),
                tools=registry.schemas(),
                messages=messages,
            )

            tool_calls = [b for b in response.content if b.type == "tool_use"]
            text_blocks = [b.text for b in response.content if b.type == "text"]

            if not tool_calls:
                return "\n".join(text_blocks) or "(no response)"

            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for call in tool_calls:
                tool_results.append(self._execute_tool(call, approve_fn))
            messages.append({"role": "user", "content": tool_results})

        return "Stopped after reaching the max tool-call turns for this message."

    def _run_openai_loop(self, messages: list[dict], approve_fn) -> str:
        request_messages = [
            {"role": "system", "content": self._system_prompt()},
            *messages,
        ]
        tools = self._openai_tools()

        for _ in range(8):
            request = {
                "model": config.model_name,
                "messages": request_messages,
            }
            if tools:
                request["tools"] = tools

            response = self._client.chat.completions.create(**request)
            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            if not tool_calls:
                return message.content or "(no response)"

            request_messages.append(self._openai_assistant_message(message))
            for call in tool_calls:
                request_messages.append(self._execute_openai_tool(call, approve_fn))

        return "Stopped after reaching the max tool-call turns for this message."

    def _run_ollama_loop(self, messages: list[dict], approve_fn) -> str:
        request_messages = [
            {"role": "system", "content": self._system_prompt()},
            *messages,
        ]
        tools = self._openai_tools()

        repair_attempted = False
        for _ in range(8):
            request = {
                "model": config.model_name,
                "messages": request_messages,
                "think": False,
            }
            if tools:
                request["tools"] = tools

            response = self._client.chat(**request)
            message = response.message
            tool_calls = message.tool_calls or []

            if not tool_calls:
                if (
                    not repair_attempted
                    and self._looks_like_action_request(request_messages)
                ):
                    repair_attempted = True
                    request_messages.append(
                        {
                            "role": "user",
                            "content": (
                                "You must execute the requested action now. "
                                "Do not say you cannot execute it. Emit the "
                                "actual matching tool call, especially "
                                "run_shell for a shell command."
                            ),
                        }
                    )
                    continue
                return message.content or "(no response)"

            request_messages.append(self._ollama_assistant_message(message))
            for call in tool_calls:
                request_messages.append(
                    self._execute_ollama_tool(call, approve_fn)
                )

        return "Stopped after reaching the max tool-call turns for this message."

    @staticmethod
    def _looks_like_action_request(messages: list[dict]) -> bool:
        if not messages:
            return False
        latest = messages[-1]
        if latest.get("role") != "user":
            return False
        text = str(latest.get("content", "")).lower()
        return bool(
            re.search(
                r"\b(run|execute|launch|start|stop|restart|create|write|"
                r"delete|remove|save|change|modify|update)\b",
                text,
            )
        )

    @staticmethod
    def _system_prompt() -> str:
        return f"""You are {config.name}, a personal AI agent with real tools:
you can run shell commands, read/write files in your workspace, and
remember facts across sessions.

When the user asks you to perform an action, you MUST call the matching
tool instead of claiming that you cannot perform it. In particular:
- use run_shell for shell commands;
- use read_file, write_file, or list_files for workspace files;
- use remember or recall for saved facts.
- use search_web for internet searches, including news, images, or videos;
- use open_web_page to read a specific public URL and summarize it.
- use get_current_uk_datetime for the authoritative current UK date and time;
- use resolve_uk_weekday to convert phrases such as "coming Wednesday" to an
  exact UK date before creating or updating a calendar event;
- use list_google_calendar_events to find calendar event IDs;
- use create_google_calendar_event, update_google_calendar_event, or
  delete_google_calendar_event for Google Calendar changes.
When the user asks for current or online information, use the web tools
instead of answering from memory.
When the user asks about today's date, the current time, tomorrow, next week,
or another relative date, call get_current_uk_datetime first. Do not guess
the date from model knowledge. Interpret calendar event times in
Europe/London unless the user specifies another timezone.
For phrases such as "coming Wednesday", also call resolve_uk_weekday and use
the exact returned date in the calendar tool call. Never calculate that date
yourself or substitute the previous day.
For calendar operations, use the Calendar tools directly; do not claim that
you lack calendar access. List events before updating or deleting when an
event ID is not already known.
If you do not know something, or need broader context or up-to-date
information, use search_web to broaden your knowledge before answering.
Do not describe a tool call in plain text. Emit the actual tool call.
Be direct and only use a tool when it is actually needed."""

    @staticmethod
    def _openai_tools() -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            }
            for tool in registry.schemas()
        ]

    @staticmethod
    def _openai_assistant_message(message) -> dict:
        return {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in message.tool_calls
            ],
        }

    @staticmethod
    def _ollama_assistant_message(message) -> dict:
        return {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "function": {
                        "name": call.function.name,
                        "arguments": dict(call.function.arguments),
                    }
                }
                for call in (message.tool_calls or [])
            ],
        }

    def _execute_openai_tool(self, call, approve_fn) -> dict:
        try:
            tool_input = json.loads(call.function.arguments)
        except (TypeError, json.JSONDecodeError) as e:
            return {
                "role": "tool",
                "tool_call_id": call.id,
                "content": f"Tool error: invalid arguments: {e}",
            }

        spec = registry.get(call.function.name)
        result = self._execute_tool_call(
            spec, call.function.name, tool_input, approve_fn
        )
        return {
            "role": "tool",
            "tool_call_id": call.id,
            "content": str(result),
        }

    def _execute_ollama_tool(self, call, approve_fn) -> dict:
        tool_name = call.function.name
        tool_input = call.function.arguments
        spec = registry.get(tool_name)
        result = self._execute_tool_call(
            spec, tool_name, tool_input, approve_fn
        )
        return {
            "role": "tool",
            "content": str(result),
            "tool_name": tool_name,
        }

    def _execute_tool(self, call, approve_fn) -> dict:
        spec = registry.get(call.name)
        result = self._execute_tool_call(spec, call.name, call.input, approve_fn)
        return {
            "type": "tool_result",
            "tool_use_id": call.id,
            "content": str(result),
        }

    def _execute_tool_call(self, spec, tool_name, tool_input, approve_fn):
        if spec.dangerous and not config.auto_approve:
            if not approve_fn(tool_name, tool_input):
                return "User declined to approve this action."
        try:
            return spec.func(**tool_input)
        except Exception as e:
            return f"Tool error: {e}"

    @staticmethod
    def _cli_approve(tool_name: str, tool_input: dict) -> bool:
        print(f"\n⚠️  {config.name} wants to run: {tool_name}({tool_input})")
        return input("Approve? [y/N] ").strip().lower() == "y"
