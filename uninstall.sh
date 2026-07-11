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
  deleted=0
  while security delete-generic-password -s Nimbus >/dev/null 2>&1; do deleted=$((deleted+1)); done
  [ "$deleted" -gt 0 ] && echo "Deleted $deleted Nimbus Keychain item(s)." \
    || echo "No Nimbus Keychain items found."
else
  echo "Keychain item kept."
fi
echo "Done. (This folder and its venv are yours to delete manually.)"
