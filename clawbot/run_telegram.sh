#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
LOG_FILE="$SCRIPT_DIR/../telegram.log"
PID_FILE="$SCRIPT_DIR/../telegram.pid"

cd "$SCRIPT_DIR"
nohup python3 main.py telegram >>"$LOG_FILE" 2>&1 </dev/null &
echo $! >"$PID_FILE"