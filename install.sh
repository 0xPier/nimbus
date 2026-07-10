#!/bin/sh
# Nimbus installer — venv + LaunchAgent. Everything stays in this folder,
# ~/Library/LaunchAgents, and ~/Library/Application Support/Nimbus.
set -e
cd "$(dirname "$0")"
NIMBUS_DIR="$(pwd)"
PLIST="$HOME/Library/LaunchAgents/com.pier.nimbus.plist"
LABEL="com.pier.nimbus"

if [ ! -x .venv/bin/python ]; then
  echo "creating venv..."
  python3 -m venv .venv
  .venv/bin/pip -q install requests keyring rumps
fi

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$NIMBUS_DIR/.venv/bin/python</string>
    <string>-m</string>
    <string>nimbus.app</string>
  </array>
  <key>WorkingDirectory</key><string>$NIMBUS_DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string></dict>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Nimbus installed and started — look for the cloud in your menu bar."
