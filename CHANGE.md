# Changes

All notable changes to Clawbot are tracked here, newest first. Each
entry corresponds to one phase/slice from `PLAN.md`. Keep entries short
— point to the test file that pins new behavior instead of re-explaining
it in prose.

## [Unreleased]

### Latest commit
- `dd16d4f` (`feat(scheduler): send scheduled briefings to Telegram`)
- `4010669` (`feat(weather): add BBC weather location tools`)

### Added
- Ollama provider support with iterative tool-call execution
- Ollama setup, Homebrew service management, and log-tail documentation
- `tests/test_skills_registry.py`: registry registration, schema generation,
  schema enumeration, and module loading coverage
- `tests/test_skill_file.py`, `tests/test_skill_shell.py`, and
  `tests/test_skill_memory.py`: isolated skill behavior coverage
- BBC Weather skill with generic location resolution and weather lookup by
  numeric location ID (`skills/weather_skill.py`)
- Telegram delivery for scheduled briefings with configurable chat ID
- Background launchers: `clawbot/run_cli.sh`, `clawbot/run_job.sh`, and
  `clawbot/run_telegram.sh`

### Changed
- Ollama is the default model provider and `qwen3:8b` is the default model
- Scheduler and launcher documentation in `clawbot/README.md`
- Launcher scripts now use environment-provided credentials and validate the
  configured Python environment before starting
- Memory APIs now support deleting a single channel or all conversation
  history, and the scheduler clears all history daily at 01:00
- Morning briefings now run daily at 09:00
- The commit-message skill now requires updating and verifying `CHANGE.md`
  before creating commits
- Git now ignores untracked `run_*.sh` launcher scripts

### Fixed
- Scheduler startup now runs as a module with the correct `PYTHONPATH`,
  avoiding package import failures

### Tests
- Ollama agent-loop coverage in `tests/test_agent_loop.py`
- Phase 1 registry tests: 4 passing
- Phase 2 skill tests: 8 passing
- Weather skill and scheduler tests: 35 passing, 2 opt-in live weather tests
  skipped by default
- Added memory deletion and scheduled cleanup coverage

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
