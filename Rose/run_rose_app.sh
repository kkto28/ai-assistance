#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_PATH="$SCRIPT_DIR/Rose.app"

if [ -f "$SCRIPT_DIR/../clawbot/set_env.sh" ]; then
  # Load local credentials before the native app starts its Python backend.
  . "$SCRIPT_DIR/../clawbot/set_env.sh"
fi

rm -rf "$APP_PATH"
mkdir -p "$APP_PATH/Contents/MacOS"

cat >"$APP_PATH/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>Rose</string>
  <key>CFBundleDisplayName</key>
  <string>Rose Personal AI</string>
  <key>CFBundleIdentifier</key>
  <string>local.rose.personal-ai</string>
  <key>CFBundleExecutable</key>
  <string>Rose</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSMinimumSystemVersion</key>
  <string>13.0</string>
</dict>
</plist>
PLIST

swiftc \
  -framework AppKit \
  -framework WebKit \
  "$SCRIPT_DIR/RoseApp.swift" \
  -o "$APP_PATH/Contents/MacOS/Rose"

ROSE_ROOT="$SCRIPT_DIR/.." exec "$APP_PATH/Contents/MacOS/Rose"
