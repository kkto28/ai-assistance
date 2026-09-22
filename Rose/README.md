# Rose desktop interface

Rose is a small React/WebKit chat interface backed by `Rose/server.py`.
The backend uses the same Clawbot configuration, skills, model provider, and
approval rules as the terminal client.

## Start Rose

From the repository root:

```bash
# Browser version
./Rose/run_rose.sh
open http://127.0.0.1:8765

# Native macOS window
./Rose/run_rose_app.sh
```

Both launchers load `clawbot/set_env.sh` automatically when that file exists.
The browser/server launcher prefers `venv/bin/python`.

Rose serves the local API and UI at `127.0.0.1:8765`. Check whether it is
ready with:

```bash
curl http://127.0.0.1:8765/api/health
```

To stop the server:

```bash
kill "$(lsof -tiTCP:8765 -sTCP:LISTEN)"
```

If the port is already in use, inspect the process before stopping it:

```bash
lsof -nP -iTCP:8765 -sTCP:LISTEN
```

## Configuration

Set the model provider before starting Rose:

```bash
export CLAWBOT_MODEL_PROVIDER=ollama
export CLAWBOT_MODEL_NAME=qwen3:8b
export OLLAMA_HOST=http://localhost:11434
```

For OpenAI, use `CLAWBOT_MODEL_PROVIDER=openai` and set `OPENAI_API_KEY`.
The backend reads configuration when it starts, so restart Rose after changing
environment variables, enabled skills, or dependencies.

## Safety and permissions

Dangerous tools are controlled by `CLAWBOT_AUTO_APPROVE`, which defaults to
`false`. Rose shows an approval control before running shell commands, writing
files, or moving selected Gmail messages to Trash.

Read-only operations such as listing calendar events and inspecting Gmail do
not require approval. Gmail cleanup still requires explicit message IDs and
the literal confirmation `APPROVE`.

## Implementation notes

- `Rose/server.py` provides the HTTP API and serves the web interface.
- `Rose/RoseApp.swift` wraps the interface in a native macOS window.
- The frontend uses React and Babel from a CDN; no Node or npm build is
  required.
- An internet connection is required for the CDN-hosted frontend scripts.
- Replace `Rose/assets/Rose.png` to change the Dock icon.
