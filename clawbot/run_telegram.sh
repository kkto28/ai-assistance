#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ -f "$SCRIPT_DIR/set_env.sh" ]; then
    . "$SCRIPT_DIR/set_env.sh"
fi

LOG_FILE="$SCRIPT_DIR/../telegram.log"
PID_FILE="$SCRIPT_DIR/../telegram.pid"
PYTHON="${PYTHON:-$SCRIPT_DIR/../venv/bin/python}"

if [ ! -x "$PYTHON" ]; then
    PYTHON="${PYTHON_FALLBACK:-python3}"
fi

if ! "$PYTHON" -c 'import openai' >/dev/null 2>&1; then
    echo "Error: OpenAI is not installed for $PYTHON." >&2
    echo "Run: $PYTHON -m pip install -r \"$SCRIPT_DIR/../requirements.txt\"" >&2
    exit 1
fi

if [ -f "$PID_FILE" ]; then
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        echo "Telegram bot is already running with PID $pid."
        exit 0
    fi
    rm -f "$PID_FILE"
fi

cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"
nohup "$PYTHON" main.py telegram >>"$LOG_FILE" 2>&1 </dev/null &
pid=$!
echo "$pid" >"$PID_FILE"

echo "Telegram bot started with PID $pid."
echo "Log: $LOG_FILE"
