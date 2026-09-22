# Rose / Clawbot

Rose is a personal AI assistant with a Python backend, a lightweight skill
system, local SQLite memory, and an optional macOS desktop interface.

## Choose how to run it

| Use case | Command |
| --- | --- |
| Terminal chat | `./clawbot/run_cli.sh` |
| Browser UI | `./Rose/run_rose.sh`, then open <http://127.0.0.1:8765> |
| Native macOS window | `./Rose/run_rose_app.sh` |
| Scheduled briefing | `./clawbot/run_job.sh` |
| Telegram bot | `./clawbot/run_telegram.sh` |

Run commands from the repository root.

## First-time setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Choose a model provider:

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

The launch scripts automatically source `clawbot/set_env.sh` when it exists.
Use that file for local environment variables, but keep it out of Git and
never share its contents.

## Safety

Rose asks for approval before dangerous tools such as shell commands, file
writes, and Gmail cleanup. Gmail inspection and calendar listing are
read-only. Gmail cleanup moves only explicitly selected messages to Trash and
requires a separate `APPROVE` confirmation.

Keep `CLAWBOT_AUTO_APPROVE=false` unless you fully understand the risks.

## Documentation

- [Clawbot guide](clawbot/README.md) — setup, skills, channels, Google
  Calendar/Mail, scheduler, and security details
- [Rose guide](Rose/README.md) — browser and native macOS UI
- [Change log](CHANGE.md)
