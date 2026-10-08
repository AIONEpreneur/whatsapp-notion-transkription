# WhatsApp-Sprachnachrichten → Notion (vollautomatisch, lokal)

Legt eine Sprachnachricht in einen Ordner — und bekommt Sekunden später eine
fertig aufbereitete Notion-Seite: **lokal transkribiert**, von Claude
zusammengefasst, mit erkannten Fragen und markiertem Testimonial-Potenzial,
dem richtigen Kunden zugeordnet und optional per Slack gemeldet.

Die Aufnahme **verlässt den Rechner nicht** — transkribiert wird offline mit
[whisper.cpp](https://github.com/ggerganov/whisper.cpp). Nach extern (z. B.
Adobe Podcast) muss nichts mehr hochgeladen werden.

## Was passiert

```
Audiodatei in den Ordner legen
        │
        ▼
 [1] transkribieren.sh   → mp3-Archiv + lokale Whisper-Transkription (.txt)
        │                   + Eigennamen-Korrektur (korrekturen.txt)
        ▼
 [2] transkript_zu_notion.py --auto
        │   • Kunde aus Dateiname erkannt (sonst "unbekannt")
        │   • Claude: Zusammenfassung, Fragen, Testimonial
        │   • Notion-Seite in der Transkript-DB angelegt
        │   • optional Slack-Benachrichtigung
        ▼
 Datei nach Transkripte/Verarbeitet/ archiviert
```

Zwei Betriebsarten:

- **Vollautomatik** — ein Ordner-Wächter (macOS LaunchAgent) startet den Lauf
  bei jeder neuen Datei von selbst. Nichts klicken.
- **Manuell** — `bash verarbeiten.sh` von Hand (oder nur `transkribieren.sh`,
  wenn du den Kunden lieber im Dialog wählst: `python3 transkript_zu_notion.py`).

## Voraussetzungen

- macOS mit [Homebrew](https://brew.sh)
- `ffmpeg` und `whisper-cpp` (`brew install ffmpeg whisper-cpp`)
- Whisper-Modell `ggml-large-v3-turbo.bin` (~1,6 GB, siehe EINRICHTUNG.md)
- Notion-Account mit zwei Datenbanken (CRM + Transkripte) und einer Integration
- optional: Anthropic-API-Key (Analyse), Slack-Webhook (Benachrichtigung)

## Einrichtung

Siehe **[EINRICHTUNG.md](EINRICHTUNG.md)** — einmalig, Schritt für Schritt.

Kurzfassung:

```bash
cp konfiguration.beispiel.json konfiguration.json   # Pfade + DB-IDs eintragen
cp korrekturen.beispiel.txt   korrekturen.txt        # eigene Marken-/Namen
cp .env.beispiel ~/.config/whatsapp-workflow/.env    # Tokens eintragen
bash watcher/installieren.sh                         # Vollautomatik aktivieren
```

## Kunde aus Dateiname

Der Auto-Modus liest den Kundennamen aus dem Dateinamen (Datum/Zahlen werden
ignoriert). `Kerstin Wenzel 071026.opus` → Kunde **Kerstin Wenzel**, sofern er
in der CRM-Datenbank existiert. Kein Treffer → Seite wird als „unbekannt"
angelegt; die Zuordnung lässt sich in Notion in zwei Sekunden nachziehen.

## Dateien

| Datei | Zweck |
|-------|-------|
| `transkribieren.sh` | Audio → mp3-Archiv + lokale Whisper-Transkription |
| `transkript_zu_notion.py` | Transkript → Notion (interaktiv oder `--auto`) |
| `verarbeiten.sh` | Komplettlauf (1 + 2), vom Wächter aufgerufen |
| `korrigiere.py` / `korrekturen.txt` | Eigennamen nach dem Transkribieren richtigstellen |
| `watcher/` | Ordner-Wächter (LaunchAgent) installieren/entfernen |
| `konfiguration.json` | Pfade + Notion-DB-IDs (nicht im Git) |

## Datenschutz

Transkription läuft vollständig offline. An externe Dienste gehen nur die Texte,
die du selbst anbindest: Notion (Ablage), Anthropic (Analyse, optional), Slack
(Benachrichtigung, optional). Ohne Anthropic-Key bleibt die Analyse aus, der
Rest funktioniert weiter.
