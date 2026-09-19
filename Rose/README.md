# Rose React desktop interface

Rose is a React chat interface served by a small Python server. This is the
only Rose desktop interface; its Python backend imports and calls the agent
under `clawbot/` and uses the same Ollama/provider configuration as the rest
of the project.

## Run

From the repository root:

```bash
python Rose/server.py
```

Open <http://127.0.0.1:8765> in your browser. The server prints the URL and
stops with `Ctrl+C`.

If you start Rose again while it is already running, the second process now
detects the existing Rose server and exits cleanly. To find and stop a
different process using the port:

```bash
lsof -nP -iTCP:8765 -sTCP:LISTEN
kill <PID>
```

For a native macOS window instead of a browser tab:

```bash
./Rose/run_rose_app.sh
```

This compiles and launches a small AppKit/WebKit wrapper. It starts
`Rose/server.py` in the background, displays the React interface in the app
window, and stops the backend when the window closes.

The native app sets its Dock icon from `Rose/assets/Rose.png` when it starts,
so replacing that image also updates the app icon.

For Ollama:

```bash
export CLAWBOT_MODEL_PROVIDER=ollama
export CLAWBOT_MODEL_NAME=qwen3:8b
export OLLAMA_HOST=http://localhost:11434
python Rose/server.py
```

The frontend uses React and Babel from a CDN, so the current zero-build setup
does not require Node or npm. An internet connection is needed to load the
React browser scripts. The Python backend itself uses only the standard
library plus the project's existing Clawbot dependencies.

Replace the Rose photo by replacing `Rose/assets/Rose.png`. The dashboard is
an extension area for future widgets, notes, metrics, and shortcuts.

Dangerous Clawbot tools remain protected by `CLAWBOT_AUTO_APPROVE`. With the
default `false` setting, Rose pauses the chat and shows an Approve/Deny card
in the sidebar and above the conversation.

Ollama tool-capable models are configured to use actual tool calls for action
requests rather than only describing what they would do.
