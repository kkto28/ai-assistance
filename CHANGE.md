# Changes

All notable changes to Clawbot are tracked here, newest first. Each
entry corresponds to one phase/slice from `PLAN.md`. Keep entries short
— point to the test file that pins new behavior instead of re-explaining
it in prose.

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
- Project structure: `core/`, `skills/`, `channels/`, `memory/`, `scheduler/`
- Skill registry with `@tool` decorator (`skills/__init__.py`)
- Shell skill: `run_shell` (`skills/shell_skill.py`)
- File skill: `read_file`, `write_file`, `list_files`, sandboxed to `WORKSPACE` (`skills/file_skill.py`)
- Memory skill: `remember`, `recall` (`skills/memory_skill.py`)
- SQLite-backed conversation history + notes (`memory/db.py`)
- Agent reasoning loop with tool-calling and approval gate (`core/agent.py`)
- CLI channel (`channels/cli_channel.py`)
- Telegram channel stub, auto-approves dangerous tools for now (`channels/telegram_channel.py`)
- APScheduler job stub: `morning_briefing` (`scheduler/jobs.py`)
- `requirements.txt`, `README.md`

### Tests
- Manual smoke test only: registry loads all 6 tools, `write_file` →
  `read_file` round-trips, `remember` → `recall` round-trips.
- No automated test suite yet — Phase 1 in `PLAN.md` backfills this.

### Known gaps (tracked for Phase 1+)
- `to_schema()` may mark parameters with default values as required —
  needs a test to confirm/fix.
- Telegram channel bypasses the approval gate entirely
  (`approve_fn=lambda: True`) — needs a real approve/deny flow (Phase 5).
- `run_shell` has no command allowlist yet (Phase 7).
