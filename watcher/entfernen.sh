#!/bin/bash
# Entfernt den Ordner-Waechter wieder. Der manuelle Weg (verarbeiten.sh) bleibt nutzbar.
set -euo pipefail
LABEL="${1:-com.local.whatsapp-transkription}"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST"
echo "Waechter entfernt: $LABEL"
