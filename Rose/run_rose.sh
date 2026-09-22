#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR/.."

if [ -f clawbot/set_env.sh ]; then
  # Load local credentials before Python imports config.py.
  . clawbot/set_env.sh
fi

if [ -x venv/bin/python ]; then
  exec venv/bin/python Rose/server.py
fi
exec python3 Rose/server.py
