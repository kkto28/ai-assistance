"""
Clawbot skill system.

A "skill" is a Python module that registers one or more tools using the
@tool decorator below. Skills are auto-discovered from config.enabled_skills
at startup, so adding a new capability never requires touching core/.

This is a deliberately lightweight plugin registry (no external dependency).
If you outgrow it -- e.g. you want skill versioning, hot-reload, or
third-party skill packages -- swap it for `pluggy` without changing how
individual skills are written; only registry.py's internals would change.
"""
from __future__ import annotations
import importlib
import inspect
from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class ToolSpec:
    name: str
    description: str
    func: Callable[..., Any]
    dangerous: bool = False  # requires approval unless auto_approve is set

    def to_schema(self) -> dict:
        """Produce an LLM-tool-call schema (Anthropic/OpenAI style) from
        the wrapped function's signature."""
        sig = inspect.signature(self.func)
        properties = {}
        required = []
        for pname, param in sig.parameters.items():
            properties[pname] = {"type": "string"}
            if param.default is inspect.Parameter.empty:
                required.append(pname)
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


class SkillRegistry:
    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}

    def register(self, name: str, description: str, dangerous: bool = False):
        """Decorator: turns a plain function into a registered tool."""
        def wrapper(func: Callable):
            self._tools[name] = ToolSpec(name, description, func, dangerous)
            return func
        return wrapper

    def get(self, name: str) -> ToolSpec:
        return self._tools[name]

    def all(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def schemas(self) -> list[dict]:
        return [t.to_schema() for t in self._tools.values()]

    def load(self, module_names: list[str]):
        """Import each skill module so its @tool registrations run."""
        for name in module_names:
            importlib.import_module(name)


registry = SkillRegistry()
tool = registry.register  # nicer alias: @tool("name", "description")
