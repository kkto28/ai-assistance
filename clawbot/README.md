# Clawbot

Clawbot is Rose's Python agent runtime. It combines:

- one tool-calling reasoning loop;
- pluggable skills registered with `@tool`;
- CLI, Telegram, scheduler, and Rose channels;
- local SQLite conversation history and notes.

## Quickstart

From the repository root:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set a model provider:

```bash
# OpenAI
export CLAWBOT_MODEL_PROVIDER=openai
export OPENAI_API_KEY=your-key

# Or Ollama
brew install ollama
brew services start ollama
ollama pull qwen3:8b
export CLAWBOT_MODEL_PROVIDER=ollama
export CLAWBOT_MODEL_NAME=qwen3:8b
export OLLAMA_HOST=http://localhost:11434
```

Start a terminal session:

```bash
./clawbot/run_cli.sh
```

The launcher uses the repository virtual environment when available and
automatically sources `clawbot/set_env.sh` if present.

## Launchers

Run these from the repository root:

| Launcher | Purpose | Logs / state |
| --- | --- | --- |
| `./clawbot/run_cli.sh` | Interactive terminal chat | — |
| `./clawbot/run_job.sh` | Background scheduled jobs | `scheduler.log`, `scheduler.pid` |
| `./clawbot/run_telegram.sh` | Background Telegram bot | `telegram.log`, `telegram.pid` |
| `./Rose/run_rose.sh` | Browser UI backend | Port `8765` |
| `./Rose/run_rose_app.sh` | Native macOS UI | Port `8765` |

Stop a background job with its PID file:

```bash
kill "$(cat scheduler.pid)"
rm scheduler.pid
```

Use the equivalent `telegram.pid` file for the Telegram bot. Stop Rose with:

```bash
kill "$(lsof -tiTCP:8765 -sTCP:LISTEN)"
```

## Environment variables

The launchers source `clawbot/set_env.sh` automatically. This file is ignored
by Git and should contain local secrets only. Do not commit or paste its
contents.

Common settings:

| Variable | Purpose |
| --- | --- |
| `CLAWBOT_MODEL_PROVIDER` | `ollama`, `openai`, or `anthropic` |
| `CLAWBOT_MODEL_NAME` | Model name, such as `qwen3:8b` |
| `OLLAMA_HOST` | Ollama server URL |
| `OPENAI_API_KEY` | OpenAI credential |
| `ANTHROPIC_API_KEY` | Anthropic credential |
| `CLAWBOT_AUTO_APPROVE` | Set to `true` to bypass dangerous-tool approval |
| `CLAWBOT_WORKSPACE` | Root directory used by file tools |
| `CLAWBOT_DB_PATH` | SQLite database path |

Configuration is loaded when the process starts. Restart the relevant launcher
after changing environment variables.

## Google Calendar

The Calendar skill can list, create, update, and delete events. Configure a
Google OAuth desktop application with the Calendar scope
`https://www.googleapis.com/auth/calendar`:

```bash
export GOOGLE_CALENDAR_CLIENT_ID=your-client-id
export GOOGLE_CALENDAR_CLIENT_SECRET=your-client-secret
export GOOGLE_CALENDAR_REFRESH_TOKEN=your-refresh-token
export GOOGLE_CALENDAR_DEFAULT_CALENDAR=primary
```

The refresh token is preferred because it can obtain new access tokens
automatically. `GOOGLE_CALENDAR_ACCESS_TOKEN` is available for short-lived
testing. Event times default to `Europe/London`.

Example requests:

```text
List my calendar events for today.
Create a dentist appointment on 2026-09-25 from 10:00 to 11:00.
Update event EVENT_ID on 2026-09-25 to run from 11:00 to 12:00.
Delete event EVENT_ID.
```

## Google Mail

The Mail skill can inspect Spam, Promotions, and Social without changing
anything. Inspection returns up to 20 messages per category by default,
grouped with sender, date, subject, and exact Message ID fields so candidates
are easy to review. Cleanup moves only selected messages to recoverable Gmail
Trash.
Configure OAuth with the Gmail scope
`https://www.googleapis.com/auth/gmail.modify`:

```bash
export GOOGLE_MAIL_CLIENT_ID=your-client-id
export GOOGLE_MAIL_CLIENT_SECRET=your-client-secret
export GOOGLE_MAIL_REFRESH_TOKEN=your-refresh-token
```

`GOOGLE_MAIL_ACCESS_TOKEN` can be used for short-lived testing. Ask Rose to
inspect mail first. Inspection is read-only and does not require approval.
Cleanup requires:

1. a review of the messages and their exact IDs;
2. explicit selection of the IDs to move;
3. the normal dangerous-tool approval; and
4. the literal confirmation `APPROVE`.

Messages are moved to Trash, not permanently deleted.

## Scheduler and Telegram

The scheduler runs the morning briefing daily at 09:00 and clears conversation
history daily at 01:00, both in `Europe/London` time:

```bash
./clawbot/run_job.sh
```

Telegram delivery also requires:

```bash
export TELEGRAM_BOT_TOKEN=your-bot-token
export TELEGRAM_CHAT_ID=your-chat-id
./clawbot/run_telegram.sh
```

The scheduled bin collection reminder runs Wednesdays at 08:30 London time.
Set `CLAWBOT_BIN_COLLECTION_URL` to the calendar URL in `clawbot/set_env.sh`,
and configure Playwright and Chrome remote debugging as described in the
Browser skill section. When Telegram credentials are configured, the reminder
sends its screenshot to `TELEGRAM_CHAT_ID`.

The scheduler can also run interval jobs from Python:

```python
from scheduler import jobs

jobs.schedule_interval_job(
    jobs.morning_briefing,
    hours=1,
    job_id="hourly-briefing",
)
jobs.start()
```

## Web search

The web skill provides read-only DuckDuckGo text, news, image, and video
search, plus page extraction:

```text
Search the web for the latest Ollama tool-calling documentation.
Open https://ollama.com/blog/tool-support and summarize it.
```

Use `search_type` values `text`, `news`, `images`, or `videos` when calling the
search tool directly.

## Browser skill

`skills/browser_skill.py` provides read-only web browsing, using the
shared Chrome-over-CDP connector in `core/browser.py`:

- `navigate(url)` — opens a URL in a new tab, leaves it open for you to see
- `get_page_text(url)` — fetches a page's visible text content
- `get_links(url)` — lists links found on a page
- `screenshot(url)` — saves a PNG to `workspace/`

These tools do not click page controls or submit forms. They are currently
registered as non-dangerous tools; `screenshot` writes a PNG into the
configured workspace. Interactive actions (such as clicking or filling
forms) should be separate tools and marked `dangerous=True`.

The skill is enabled by default in `config.py`. Playwright is installed with
the project requirements. To use it, start Chrome with the
`--remote-debugging-port=9222` flag, or set `CHROME_CDP_PORT` to your chosen
port. Confirm the debugging endpoint is available at
`http://localhost:9222/json/version` (replace `9222` if using another port).
Remove `"skills.browser_skill"` from `enabled_skills` if you do not want to
load the skill.

## Project structure

```text
clawbot/
  core/agent.py       Agent loop, prompts, tool execution, approvals
  skills/             Registered tools and integrations
  channels/           CLI and Telegram adapters
  memory/db.py        SQLite history and notes
  scheduler/jobs.py   Scheduled and interval jobs
  config.py           Environment-backed configuration
  main.py             CLI entry point
```

Adding a skill means creating a module under `skills/` with an `@tool`
function, then adding its module path to `enabled_skills` in `config.py`.
Adding a channel means calling `Agent.handle_message()` from a transport
adapter.

## Security

Clawbot can run shell commands, write files, access Google services, and send
Telegram messages. Keep approval mode enabled until the setup is trusted.
Use a workspace directory that can safely be modified, rotate credentials if
they are exposed, and never commit `set_env.sh`.
