# Clawbot — Development Plan

A TDD, incrementally-shipped build plan for the scaffold. Each phase
produces a working, tested slice of the system — never a half-built
mess. Pair this with `CHANGES.md` (template included below) to track
what actually happened vs. what was planned.

## Principles

- **Red → Green → Refactor.** Write a failing test for the smallest
  next behavior, make it pass with the simplest code, then clean up.
- **Vertical slices, not layers.** Each phase should leave you with
  something runnable end-to-end, not "all models done, no logic yet."
- **One skill/channel per PR.** Keep diffs small enough to review and
  revert independently — this is the whole point of the modular
  scaffold.
- **No dangerous tool ships without a test that it refuses unapproved
  execution.** Safety behavior is tested, not assumed.

## Tooling

```bash
pip install pytest pytest-mock pytest-cov
```

Suggested layout — tests mirror source:
```
tests/
  test_skills_registry.py
  test_skill_shell.py
  test_skill_file.py
  test_skill_memory.py
  test_agent_loop.py
  test_memory_db.py
```

Run with `pytest -v --cov=clawbot` before every commit.

---

## Phase 0 — Project skeleton (done)

- [x] Folder structure, config, requirements
- [x] Skill registry with `@tool` decorator
- [x] Shell, file, memory skills
- [x] SQLite memory layer
- [x] Agent reasoning loop
- [x] CLI + Telegram channel stubs
- [x] Manual smoke test (registry loads, file/memory skills work)

**Next up:** backfill this phase with real tests before adding anything
new, so the baseline is covered.

---

## Phase 1 — Test the skill registry (TDD)

**Goal:** `skills/__init__.py`'s registry is the foundation everything
else calls — get it airtight first.

1. Write `tests/test_skills_registry.py`:
   - registering a tool makes it retrievable by name
   - `to_schema()` produces correct `required` list from function signature
   - `schemas()` returns one schema per registered tool
   - `load()` imports a module and its tools appear in the registry
2. Run — confirm failures (red).
3. Registry code already exists; adjust only if tests reveal a gap
   (e.g. default-value params should be optional in the schema — check
   this, it's a likely bug).
4. Refactor: extract schema-building into a testable pure function if
   it isn't already.

**Definition of done:** `pytest tests/test_skills_registry.py` green,
no changes needed to any skill file.

---

## Phase 2 — Test each skill in isolation

**Goal:** every skill is testable without hitting the LLM or a real
shell/filesystem where avoidable.

1. `test_skill_file.py`:
   - write then read round-trips correctly
   - path traversal (`../../etc/passwd`) raises/returns an error, never
     escapes `WORKSPACE`
   - `list_files` on empty dir returns `"(empty)"`
   - use `tmp_path` fixture to isolate from the real workspace
2. `test_skill_shell.py`:
   - mock `subprocess.run`; assert command is passed through correctly
   - timeout path returns the expected error string, doesn't raise
   - stderr gets appended to output when present
3. `test_skill_memory.py`:
   - `remember` + `recall` round-trip
   - `recall` on missing key returns the "nothing remembered" message
   - use an in-memory/tmp SQLite DB, never the real `clawbot.db`

**Definition of done:** all three files green, no test touches a real
file outside `tmp_path` or a real shell command.

---

## Phase 3 — Test the agent loop with a mocked LLM client

**Goal:** verify the tool-calling loop's control flow without spending
API calls or depending on model behavior.

1. `test_agent_loop.py`:
   - mock `Agent._client.messages.create` to return: (a) a text-only
     response → loop returns it immediately, (b) a tool-call response
     followed by a text response → loop calls the tool and returns the
     second response
   - dangerous tool + `auto_approve=False` + `approve_fn` returns
     `False` → tool is *not* executed, agent reports decline
   - dangerous tool + `auto_approve=True` → tool runs without calling
     `approve_fn`
   - loop hits `max_turns` → returns the "stopped after max turns"
     message rather than looping forever
2. This phase will likely surface the first real bug: confirm
   `approve_fn` is actually being bypassed correctly when
   `auto_approve=True` (current code checks `config.auto_approve`
   inside `_execute_tool` — trace it under test to be sure).

**Definition of done:** agent loop behavior is pinned by tests; you can
now refactor toward LangGraph later without fear, since these tests
define the contract.

---

## Phase 4 — First real end-to-end skill (incremental slice)

Pick **one** new capability (e.g. a `weather_skill.py` calling a public
API, or a `browser_skill.py` with Playwright) and build it test-first:

1. Write the test for the tool function against a mocked HTTP
   response/browser action.
2. Implement the skill.
3. Add it to `enabled_skills` in `config.py`.
4. Manually run `python main.py cli` and exercise it once for real —
   TDD covers logic, not "does the actual API key work."
5. Log the change in `CHANGES.md`.

Repeat this phase per skill — it's your template for all future
capabilities.

---

## Phase 5 — Channel hardening

1. Test `telegram_channel.py`'s `on_message` handler with a mocked
   `Update`/`context`, asserting it calls `agent.handle_message` with
   the right channel id and sends the reply back.
2. Replace the current `approve_fn=lambda: True` auto-approve shortcut
   with a real inline-keyboard approve/deny flow; test the callback
   handler the same way.
3. Add `discord_channel.py` following the same tested pattern.

---

## Phase 6 — Scheduler + proactive messaging

1. Test `morning_briefing()` calls `agent.handle_message` with expected
   args (mock the agent).
2. Wire a real `send_message` call once a channel supports proactive
   sends (not just reply-to) — extend the channel interface with a
   `send(channel_id, text)` method, test it, then use it here.

---

## Phase 7 — Sandbox hardening

1. Test that `run_shell` respects a command allowlist once you add one
   (currently unrestricted beyond the approval gate).
2. Test `file_skill`'s jail against more traversal patterns (symlinks,
   absolute paths, `..%2f` encoded variants if ever exposed over a
   network boundary).
3. Consider containerizing tool execution (Docker) for anything beyond
   personal, trusted use — write the test against the container
   interface before wiring the real container.

---

## Ongoing: every change follows this loop

1. Add/adjust a test that captures the desired behavior (red).
2. Write the minimum code to pass it (green).
3. Refactor for clarity, re-run tests.
4. Append an entry to `CHANGES.md`.
5. Commit.

---

## `CHANGES.md` template

Copy this into `CHANGES.md` at the repo root and add one entry per
change, newest first. Keep entries short — link to the test file that
pins the behavior rather than re-explaining it in prose.

```markdown
# Changes

## [Unreleased]

### Added
-

### Changed
-

### Fixed
-

### Tests
-

---

## 2026-09-17 — Phase 0: initial scaffold
### Added
- Project structure: core/, skills/, channels/, memory/, scheduler/
- Skill registry with @tool decorator (skills/__init__.py)
- Shell, file, and memory skills
- SQLite-backed conversation history + notes (memory/db.py)
- Agent reasoning loop with tool-calling and approval gate (core/agent.py)
- CLI and Telegram channel adapters
- requirements.txt, README.md

### Tests
- Manual smoke test only (registry load + file/memory skill round-trip).
  No automated test suite yet — Phase 1 backfills this.
```

Each future phase above should produce one `CHANGES.md` entry, e.g.:

```markdown
## 2026-09-20 — Phase 1: registry tests
### Tests
- tests/test_skills_registry.py: schema generation, tool registration,
  module loading (4 tests, all passing)
### Fixed
- to_schema() was marking params with defaults as required; fixed and
  covered by test_schema_optional_params
```
