#!/bin/bash
# Installiert den Ordner-Waechter als LaunchAgent. Danach laeuft der Workflow
# vollautomatisch: Audiodatei in den Ordner legen -> Rest passiert von selbst.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFG="$REPO/konfiguration.json"
[ -f "$CFG" ] || { echo "[Fehler] konfiguration.json fehlt - erst EINRICHTUNG.md durcharbeiten."; exit 1; }

WATCH_DIR="$(python3 -c "import json,os;print(os.path.expanduser(json.load(open('$CFG'))['audio_ordner']))")"
LABEL="${1:-com.local.whatsapp-transkription}"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"

mkdir -p "$HOME/Library/LaunchAgents" "$WATCH_DIR/.logs"

sed -e "s|__LABEL__|${LABEL}|g" \
    -e "s|__REPO__|${REPO}|g" \
    -e "s|__WATCH_DIR__|${WATCH_DIR}|g" \
    "$REPO/watcher/waechter.plist.vorlage" > "$PLIST"

# Neu laden (falls schon aktiv)
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "Waechter installiert: $PLIST"
echo "Beobachteter Ordner:  $WATCH_DIR"
echo ""
echo "Test: eine Audiodatei (.opus/.m4a/...) in den Ordner legen."
echo "Log:  tail -f \"$WATCH_DIR/.logs/waechter.log\""
echo "Stoppen: bash \"$REPO/watcher/entfernen.sh\""
