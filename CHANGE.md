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
- Google Calendar troubleshooting guide with ordered OAuth token checks,
  refresh-token recovery steps, and links to Google documentation
- Google Mail skill for read-only Spam, Promotions, and Social review plus
  explicit-ID, approval-gated moves to recoverable Trash
- Google Calendar skill with OAuth authentication, event listing, creation,
  updates, deletion, UK date/time resolution, and relative weekday handling
- LaunchDaemon setup instructions for keeping Ollama running after logout
- Reusable APScheduler interval jobs, including hourly scheduling support
- Read-only web search skill with `open_web_page` and `search_web` tools,
  including DuckDuckGo text, news, image, and video search; page results now
  include an LLM-generated concise `TL;DR` with an extractive fallback and
  chat-friendly point-form formatting
- Rose approval controls for dangerous tools in the sidebar
- React Rose desktop UI with a Python agent API and native macOS wrapper
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
- Read-only browser skill for navigation, page text, links, and screenshots
- Wednesday bin collection reminder with optional Telegram screenshot delivery

### Changed
- Root README now focuses on the project description and run modes, with
  detailed Clawbot setup and integration guidance in `clawbot/README.md`
- Root, Clawbot, and Rose README files now provide clearer setup, launcher,
  configuration, integration, safety, and architecture guidance
- Rose and Clawbot launchers now source the local environment file before
  starting services, so Google Calendar and Mail credentials are available
- Google Mail inspection is read-only and does not require approval; only
  explicit message cleanup remains approval-gated
- Calendar mutation tools now run without the dangerous-tool approval prompt
- Calendar event times and relative date resolution default to `Europe/London`
- Rose and CLI agent prompts now explicitly route current or online-information
  requests through `search_web` and `open_web_page`
- Agent prompts now direct web searches when the agent lacks knowledge or
  needs broader, up-to-date context before answering
- Telegram proactive messages no longer require Rose approval; shell and file
  mutation tools remain protected by the dangerous-tool gate
- Rose keeps its sidebar and avatar visible during long chats and uses a
  compact native window layout
- Rose uses the source photo for a rounded, white-bordered macOS Dock icon
- Ollama action requests explicitly disable thinking and require actual tool
  calls when a matching skill is available
- Rose keeps Approve/Deny controls out of the conversation column
- Ollama is the default model provider and `qwen3:8b` is the default model
- Scheduler and launcher documentation in `clawbot/README.md`
- Launcher scripts now use environment-provided credentials and validate the
  configured Python environment before starting
- Memory APIs now support deleting a single channel or all conversation
  history, and the scheduler clears all history daily at 01:00
- Morning briefings now run daily at 09:00
- Morning briefings now focus on Glasgow weather
- The commit-message skill now requires updating and verifying `CHANGE.md`
  before creating commits
- Git now ignores untracked `run_*.sh` launcher scripts
- Scheduler cron jobs now use `Europe/London` explicitly

### Fixed
- Google Calendar and Mail API requests now send the loaded OAuth bearer token
- Calendar appointment listings now use exact UK-local day bounds for relative
  and explicit dates, report the authoritative weekday/date, and reject
  ambiguous date requests; coverage is in
  `tests/test_google_calendar_skill.py` and `tests/test_agent_loop.py`
- Telegram proactive messages now always use the configured
  `TELEGRAM_CHAT_ID` instead of accepting a model-supplied destination
- Ollama refusal responses are retried with an explicit tool-call instruction
- Rose handles duplicate server starts without an address-in-use traceback
- Rose startup waits for the Python API before loading WebKit, avoiding an
  intermittent blank native app window
- Scheduler startup now runs as a module with the correct `PYTHONPATH`,
  avoiding package import failures

### Tests
- Ollama refusal recovery coverage in `tests/test_agent_loop.py`
- Ollama agent-loop coverage in `tests/test_agent_loop.py`
- Phase 1 registry tests: 4 passing
- Phase 2 skill tests: 8 passing
- Weather skill and scheduler tests: 35 passing, 2 opt-in live weather tests
  skipped by default
- Added memory deletion and scheduled cleanup coverage
- Browser skill behavior coverage in `tests/test_browser_skill.py` (12 tests)
- Scheduler screenshot and timing coverage in `tests/test_scheduler_jobs.py`

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
