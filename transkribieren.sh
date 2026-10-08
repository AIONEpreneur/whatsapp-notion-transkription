#!/bin/bash
# WhatsApp-Audio -> Transkript. Alles lokal auf diesem Rechner.
# Konvertiert jede neue Sprachnachricht (opus/ogg/m4a/aac/wav/oga) nach mp3 (Archiv),
# transkribiert sie lokal mit whisper.cpp und legt das .txt im Transkripte-Ordner ab.
# Die Aufnahme verlaesst den Rechner nicht.
#
# Werte kommen aus konfiguration.json (neben diesem Skript).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG="$SCRIPT_DIR/konfiguration.json"
[ -f "$CFG" ] || { echo "[Fehler] konfiguration.json fehlt. Kopiere konfiguration.beispiel.json."; exit 1; }

# JSON-Werte dependency-frei ueber Python lesen
jget() { python3 -c "import json,os,sys;print(os.path.expanduser(json.load(open('$CFG')).get('$1','')))"; }

WATCH_DIR="$(jget audio_ordner)"
TXT_DIR="$(jget transkripte_ordner)"
MODELL="$(jget whisper_modell)"
OUT_DIR="$WATCH_DIR/converted"
WORK_DIR="$WATCH_DIR/.arbeit"
LOG="$WATCH_DIR/.logs/convert.log"

WHISPER="$(command -v whisper-cli || command -v whisper-cpp || true)"
# Homebrew-Pfad fuer LaunchAgents (eingeschraenktes PATH) ergaenzen
[ -z "$WHISPER" ] && [ -x /opt/homebrew/bin/whisper-cli ] && WHISPER=/opt/homebrew/bin/whisper-cli
FFMPEG="$(command -v ffmpeg || echo /opt/homebrew/bin/ffmpeg)"

mkdir -p "$OUT_DIR" "$TXT_DIR" "$WORK_DIR" "$WATCH_DIR/.logs"

[ -n "$WHISPER" ] || { echo "[Fehler] whisper.cpp fehlt. Beheben mit: brew install whisper-cpp"; exit 1; }
[ -f "$MODELL" ] || { echo "[Fehler] Modelldatei fehlt: $MODELL (siehe EINRICHTUNG.md)"; exit 1; }

shopt -s nullglob nocaseglob
gefunden=0
fehler=0

for f in "$WATCH_DIR"/*.{opus,ogg,m4a,aac,wav,oga}; do
    [ -e "$f" ] || continue
    gefunden=1
    base=$(basename "$f")
    name="${base%.*}"

    out="$OUT_DIR/${name}.mp3"
    [ -f "$out" ] && out="$OUT_DIR/${name}-$(date +%H%M%S).mp3"
    echo "[$(date '+%F %T')] Konvertiere: $base" >> "$LOG"
    if ! "$FFMPEG" -y -i "$f" -acodec libmp3lame -ab 128k "$out" 2>> "$LOG"; then
        echo "[Fehler] $base - ffmpeg fehlgeschlagen, Datei bleibt liegen"; fehler=1; continue
    fi

    wav="$WORK_DIR/${name}.wav"
    if ! "$FFMPEG" -y -i "$f" -ar 16000 -ac 1 -c:a pcm_s16le "$wav" 2>> "$LOG"; then
        echo "[Fehler] $base - WAV-Umwandlung fehlgeschlagen, Datei bleibt liegen"; fehler=1; continue
    fi

    echo "Transkribiere: $base"
    ziel="$TXT_DIR/${name}"
    [ -f "$ziel.txt" ] && ziel="$TXT_DIR/${name}-$(date +%H%M%S)"
    if ! "$WHISPER" -m "$MODELL" -l de -otxt -of "$ziel" -np "$wav" >> "$LOG" 2>&1; then
        echo "[Fehler] $base - Transkription fehlgeschlagen, Datei bleibt liegen"; rm -f "$wav"; fehler=1; continue
    fi
    rm -f "$wav"

    # Eigennamen richtigstellen
    python3 "$SCRIPT_DIR/korrigiere.py" "$ziel.txt" || true

    mv "$f" "$WATCH_DIR/.logs/"
    zeichen=$(wc -c < "$ziel.txt" | tr -d ' ')
    echo "OK: $base -> $(basename "$ziel.txt") (${zeichen} Zeichen)"
done

if [ $gefunden -eq 0 ]; then
    echo "Keine neuen Sprachnachrichten im Ordner."
    exit 2
fi
exit $fehler
