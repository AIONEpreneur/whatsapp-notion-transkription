# Projektnotizen für Claude

Shareable Vorlage: WhatsApp-Sprachnachrichten lokal transkribieren und nach
Notion ablegen. Abgeleitet aus Kirstens Live-System in `~/Desktop/WhatsApp-Audio`.

## Grundsätze
- **Lokal zuerst**: Transkription läuft offline mit whisper.cpp. Nie wieder
  Audio zu einem externen Dienst hochladen (der alte Adobe-Podcast-Weg ist tot).
- **Generisch halten**: keine echten Tokens, DB-IDs, Kunden- oder Markennamen
  im Repo. Alles Persönliche lebt in `konfiguration.json`, `korrekturen.txt`,
  `.env` — alle drei sind per `.gitignore` ausgeschlossen.
- Deutschsprachige Doku und Meldungen (Zielgruppe: Solopreneure im DACH-Raum).

## Architektur
- `transkribieren.sh` — Schritt 1 (Audio → mp3 + Whisper-.txt + Eigennamen).
- `transkript_zu_notion.py` — Schritt 2, zwei Modi: interaktiv / `--auto`.
  Auto erkennt den Kunden aus dem Dateinamen gegen die CRM-DB.
- `verarbeiten.sh` — 1 + 2, vom LaunchAgent (`watcher/`) aufgerufen.

## Beim Erweitern beachten
- Keine Fremd-Abhängigkeiten in Python (nur Stdlib) — hält die Vorlage leicht.
- Notion-Eigenschaftsnamen (Titel/Datum/Status/Quelle/Transkript/Originaldatei/
  Kunde) müssen zur Transkript-DB passen; bei Änderung EINRICHTUNG.md angleichen.
