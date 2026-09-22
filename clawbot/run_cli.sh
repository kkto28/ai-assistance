#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ -f "$SCRIPT_DIR/set_env.sh" ]; then
    . "$SCRIPT_DIR/set_env.sh"
fi

PYTHON="${PYTHON:-$SCRIPT_DIR/../venv/bin/python}"

if [ ! -x "$PYTHON" ]; then
    PYTHON="${PYTHON_FALLBACK:-python3}"
fi

if ! "$PYTHON" -c 'import openai' >/dev/null 2>&1; then
    echo "Error: OpenAI is not installed for $PYTHON." >&2
    echo "Run: $PYTHON -m pip install -r \"$SCRIPT_DIR/../requirements.txt\"" >&2
    exit 1
fi

cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON" main.py cli