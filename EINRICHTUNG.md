# Einrichtung (einmalig)

## 1. Werkzeuge installieren

```bash
brew install ffmpeg whisper-cpp
```

## 2. Whisper-Modell laden (~1,6 GB)

```bash
mkdir -p ~/whisper-modelle
curl -L -o ~/whisper-modelle/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```

Kleineres, schnelleres Modell (etwas geringere Qualität): `ggml-large-v3.bin`
oder `ggml-medium.bin` von derselben Quelle — dann den Pfad in
`konfiguration.json` anpassen.

## 3. Notion vorbereiten

Du brauchst zwei Datenbanken:

**CRM-Datenbank** (Kunden) mit mindestens:
- `Name` (Titel)
- `Status` (Auswahl)

**Transkript-Datenbank** mit den Eigenschaften:
- `Titel` (Titel)
- `Datum` (Datum)
- `Status` (Auswahl, u. a. „Neu")
- `Quelle` (Auswahl, u. a. „WhatsApp")
- `Transkript` (Text)
- `Originaldatei` (Text)
- `Kunde` (Relation → CRM-Datenbank)

Dann:
1. Integration anlegen: https://www.notion.so/my-integrations → Token kopieren.
2. **Beide Datenbanken** mit der Integration teilen
   (DB öffnen → „•••" → „Verbindungen" → Integration hinzufügen).
3. Die beiden Datenbank-IDs aus der URL kopieren (der 32-stellige Teil).

## 4. Konfiguration anlegen

```bash
cp konfiguration.beispiel.json konfiguration.json
cp korrekturen.beispiel.txt   korrekturen.txt
```

`konfiguration.json` ausfüllen: Ordner-Pfade, Modellpfad, die beiden DB-IDs.
`korrekturen.txt`: eigene Marken-, Produkt- und Personennamen, die Whisper
verhört (eine Regel pro Zeile, `falsch => richtig`).

## 5. Tokens hinterlegen

```bash
mkdir -p ~/.config/whatsapp-workflow
cp .env.beispiel ~/.config/whatsapp-workflow/.env
```

`~/.config/whatsapp-workflow/.env` ausfüllen:
- `NOTION_TOKEN` (Pflicht)
- `ANTHROPIC_API_KEY` (optional, für die Claude-Analyse)
- `SLACK_WEBHOOK_URL` (optional, für Benachrichtigungen)

## 6. Testlauf (manuell)

Lege eine Audiodatei in den Audio-Ordner und starte:

```bash
bash verarbeiten.sh
```

Prüfe: Transkript in `Transkripte/Verarbeitet/`, Seite in der Notion-DB.

## 7. Vollautomatik aktivieren

```bash
bash watcher/installieren.sh
```

Ab jetzt reicht es, eine Audiodatei in den Ordner zu legen. Log mitlesen:

```bash
tail -f ~/Desktop/WhatsApp-Audio/.logs/waechter.log
```

Wieder abschalten:

```bash
bash watcher/entfernen.sh
```

## Hinweise

- Der Wächter reagiert auf **neue Dateien im Audio-Ordner**. Dateien mit der
  Endung `.mp3` werden bewusst ignoriert (das ist das Archivformat). WhatsApp-
  Sprachnachrichten sind `.opus`/`.m4a` — die werden erkannt.
- Beim Kopieren großer Dateien kurz warten, bis der Kopiervorgang fertig ist,
  bevor der Lauf startet (der Wächter hat 10 s Debounce).
- Läuft etwas schief, bleibt die Audiodatei liegen und wird beim nächsten Lauf
  erneut versucht.
