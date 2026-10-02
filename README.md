# Rose / Clawbot

Rose is a personal AI assistant powered by Clawbot, a Python agent runtime
with a pluggable skill system and local SQLite memory.

## Choose how to run it

Run commands from the repository root:

| Use case | Command |
| --- | --- |
| Terminal chat | `./clawbot/run_cli.sh` |
| Browser UI | `./Rose/run_rose.sh`, then open <http://127.0.0.1:8765> |
| Native macOS window | `./Rose/run_rose_app.sh` |
| Scheduled briefing | `./clawbot/run_job.sh` |
| Telegram bot | `./clawbot/run_telegram.sh` |

See the [Clawbot guide](clawbot/README.md) for setup, configuration, skills,
channels, integrations, and security. For details about the interfaces, see
the [Rose guide](Rose/README.md). See the [change log](CHANGE.md) for updates.
