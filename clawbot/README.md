# Clawbot (Python scaffold)

A modular, from-scratch personal agent: one reasoning loop, a pluggable
skill system, thin channel adapters, and local SQLite memory.

## Structure

```
clawbot/
  core/agent.py          # the reasoning loop (LLM <-> tool calling)
  skills/                # one file per capability, auto-discovered
    __init__.py           # registry + @tool decorator
    shell_skill.py         # run_shell
    file_skill.py          # read_file, write_file, list_files (sandboxed)
    memory_skill.py        # remember, recall
  channels/               # transport only -- no agent logic
    cli_channel.py
    telegram_channel.py
  memory/db.py            # SQLite: conversation history + notes
  scheduler/jobs.py       # APScheduler: proactive/scheduled messages
  config.py               # all settings, via environment variables
  main.py                 # entry point
```

**Why it's modular:** `core/agent.py` only knows about `skills.registry`
and `memory.db.Memory` -- it never imports a specific skill or channel.
Adding a capability = adding a file to `skills/` with an `@tool(...)`
decorated function. Adding a platform = adding a file to `channels/`
that calls `Agent.handle_message()`. Nothing else changes.

## Quickstart

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...
python main.py cli
```

Dangerous tools (`run_shell`, `write_file`) will ask for approval in the
terminal before running, unless you set `CLAWBOT_AUTO_APPROVE=true`.

To use a local Ollama model with the same tool-calling loop:

```bash
brew install ollama
brew services start ollama
ollama pull qwen3:8b
export CLAWBOT_MODEL_PROVIDER=ollama
export CLAWBOT_MODEL_NAME=qwen3:8b
export OLLAMA_HOST=http://localhost:11434
python main.py cli
```

The Ollama model must support tool calling. The agent sends tool results
back to Ollama and continues the loop until the model returns final text.

Manage the Ollama service with Homebrew:

```bash
brew services start ollama    # start Ollama in the background
brew services stop ollama     # stop Ollama
brew services restart ollama  # restart Ollama
brew services list             # check service status
tail -f /opt/homebrew/var/log/ollama.log  # follow Ollama logs
```

If you installed Ollama without Homebrew, run it directly instead:

```bash
ollama serve
```

## Running scheduled jobs

The scheduler currently runs `morning_briefing` every day at **08:00** in
the machine's local timezone. Run it from the `clawbot/` directory:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m scheduler.jobs
```

To send the briefing to Telegram as well as printing it locally, configure
the bot token and destination chat ID before starting the scheduler:

```bash
export TELEGRAM_BOT_TOKEN=123456:your-bot-token
export TELEGRAM_CHAT_ID=123456789
python -m scheduler.jobs
```

`TELEGRAM_CHAT_ID` is the chat or group where scheduled messages should be
delivered. If either Telegram variable is missing, the job remains
local-only. Keep the process running for APScheduler to trigger the job.

The agent can also send a proactive Telegram message with the
`send_telegram_message` skill. Configure the same variables, then ask Rose
to send a message. The skill always uses the configured `TELEGRAM_CHAT_ID`:
Telegram delivery does not require the dangerous-tool approval prompt; shell
and file mutation tools remain protected.

```text
Send me a Telegram message saying "The backup finished."
```

The web search skill provides read-only internet access and DuckDuckGo text, news,
image, and video search:

```text
Search the web for the latest Ollama tool-calling documentation.
Open https://ollama.com/blog/tool-support and summarize it.
```

Use `search_type` as `text` (default), `news`, `images`, or `videos` when a
specific result type is needed.
`open_web_page` includes a short `TL;DR` followed by the extracted page text.
The TL;DR uses the configured model provider and falls back to a local
extractive summary if the model is unavailable.

To run the scheduler in the background:

```bash
./run_job.sh
```

The launcher writes the process ID to `../scheduler.pid` and output to
`../scheduler.log`. To stop the background scheduler:

```bash
kill "$(cat ../scheduler.pid)"
rm ../scheduler.pid
```

## Adding a skill

Create `skills/your_skill.py`:

```python
from skills import tool

@tool(name="your_tool", description="What it does, for the LLM.")
def your_tool(some_arg: str) -> str:
    return f"did something with {some_arg}"
```

Then add `"skills.your_skill"` to `enabled_skills` in `config.py`.
That's the whole integration -- no registry wiring, no changes to
`core/agent.py`.

## Adding a channel

Copy `channels/cli_channel.py` as a template. A channel's only job is:
receive a platform message -> call `agent.handle_message(channel, text)`
-> send the reply back on that platform.

## Where to go from here

- **Approval UI per channel**: `telegram_channel.py` currently
  auto-approves dangerous tools. Wire up an inline Approve/Deny keyboard
  instead of the CLI's `input()` prompt.
- **Swap the reasoning loop for LangGraph** if you need branching logic,
  multi-step plans with checkpointing, or parallel sub-agents. Only
  `core/agent.py` would change -- skills and channels are untouched.
- **Multi-agent**: if one skill library gets unwieldy (e.g. "research"
  vs "scheduling" vs "coding" all fighting for context), split into
  role-based agents (see CrewAI) that hand off to each other.
- **Harden the sandbox**: `file_skill.py`'s workspace jail and
  `run_shell`'s 30s timeout are minimal. For anything beyond personal,
  trusted use, run the whole process in a container/VM and add a
  command allowlist.

## Security note

This gives an LLM the ability to run real shell commands and write real
files. Keep approval mode on until you trust your setup, and don't
point `CLAWBOT_WORKSPACE` at anything you're not willing to lose.
