#!/bin/sh
# Nimbus uninstaller — removes the LaunchAgent and app state.
# Offers (but never forces) deletion of the Keychain item.
set -e
PLIST="$HOME/Library/LaunchAgents/com.pier.nimbus.plist"

launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST"
rm -rf "$HOME/Library/Application Support/Nimbus"
echo "LaunchAgent and app state removed."

printf "Also delete the Nimbus sessionKey from the Keychain (if present)? [y/N] "
read -r answer
if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
  security delete-generic-password -s Nimbus 2>/dev/null && echo "Keychain item deleted." \
    || echo "No Nimbus Keychain item found."
else
  echo "Keychain item kept."
fi
echo "Done. (This folder and its venv are yours to delete manually.)"
