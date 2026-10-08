#!/bin/bash
# Komplettlauf: transkribieren + nach Notion ablegen.
# Wird vom Ordner-Waechter (LaunchAgent) aufgerufen und kann auch von Hand
# gestartet werden. Im Auto-Modus stellt das Python-Skript keine Rueckfragen:
# der Kunde wird aus dem Dateinamen erkannt (sonst "unbekannt").
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

bash "$SCRIPT_DIR/transkribieren.sh"
ergebnis=$?

# 2 = nichts zu transkribieren. Trotzdem Notion-Schritt laufen lassen,
# falls noch unverarbeitete .txt liegen (z. B. nach einem frueheren Abbruch).
if [ $ergebnis -ne 0 ] && [ $ergebnis -ne 2 ]; then
    echo "[Fehler] Transkription meldete Code $ergebnis - Notion-Schritt wird trotzdem versucht."
fi

python3 "$SCRIPT_DIR/transkript_zu_notion.py" --auto
