import sys

import pytest

from skills import SkillRegistry, registry


@pytest.fixture
def skill_registry():
    return SkillRegistry()


def test_registering_a_tool_makes_it_retrievable_by_name(skill_registry):
    @skill_registry.register("greet", "Greet a person.")
    def greet(name: str) -> str:
        return f"Hello, {name}"

    tool = skill_registry.get("greet")

    assert tool.name == "greet"
    assert tool.description == "Greet a person."
    assert tool.func is greet


def test_to_schema_marks_only_parameters_without_defaults_as_required(skill_registry):
    @skill_registry.register("search", "Search for a phrase.")
    def search(query: str, limit: int = 10) -> str:
        return query

    schema = skill_registry.get("search").to_schema()

    assert schema == {
        "name": "search",
        "description": "Search for a phrase.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "string"},
            },
            "required": ["query"],
        },
    }


def test_schemas_returns_one_schema_per_registered_tool(skill_registry):
    @skill_registry.register("first", "First tool.")
    def first(value: str) -> str:
        return value

    @skill_registry.register("second", "Second tool.")
    def second(value: str) -> str:
        return value

    schemas = skill_registry.schemas()

    assert len(schemas) == 2
    assert {schema["name"] for schema in schemas} == {"first", "second"}


def test_load_imports_a_module_and_registers_its_tools(tmp_path, monkeypatch):
    module_name = "temporary_skill_for_registry_test"
    module_path = tmp_path / f"{module_name}.py"
    module_path.write_text(
        "from skills import tool\n\n"
        '@tool(name="loaded_tool", description="Loaded from a module.")\n'
        "def loaded_tool(value: str) -> str:\n"
        "    return value\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    try:
        registry.load([module_name])
        loaded = registry.get("loaded_tool")

        assert loaded.description == "Loaded from a module."
        assert loaded.func("value") == "value"
    finally:
        registry._tools.pop("loaded_tool", None)
        sys.modules.pop(module_name, None)
