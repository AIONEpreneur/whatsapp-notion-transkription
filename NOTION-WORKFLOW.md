# WhatsApp-Sprachnachrichten automatisch transkribieren

> Aktualisierter Workflow (lokal + automatisch). Löst den alten Weg über Adobe
> Podcast ab — es wird nichts mehr nach extern hochgeladen.

## So funktioniert es jetzt

1. **Sprachnachricht in den Ordner legen** — auf dem Schreibtisch liegt der
   Ordner **WhatsApp-Audio** (ein Alias; der echte Ordner ist
   `~/WhatsApp-Audio-Eingang`, außerhalb des geschützten Desktop-Bereichs).
2. **Der Rest passiert von selbst** (Ordner-Wächter im Hintergrund):
   - lokale Transkription mit Whisper (`ggml-large-v3-turbo`), offline
   - Eigennamen-Korrektur (ShEO Club, PageFix, ActiveCampaign … via `korrekturen.txt`)
   - Claude analysiert: Zusammenfassung, offene Fragen, Testimonial-Potenzial
   - Notion-Seite in **📞 Kunden-Sprachnachrichten** wird angelegt
   - Kunde wird **aus dem Dateinamen** erkannt (z. B. „Kerstin Wenzel 071026")
     und zugeordnet; kein Treffer → „unbekannt" (in Notion in 2 Sek. nachziehen)
   - optionale Slack-Benachrichtigung
   - Audio wandert ins Archiv, Transkript nach `Transkripte/Verarbeitet/`

## Kein Hochladen mehr

Früher: mp3 erzeugen → bei Adobe Podcast hochladen → warten → Transkript
herunterladen. **Entfällt komplett.** Transkribiert wird lokal; die Aufnahme
verlässt den Rechner nicht.

## Dateiname = Kundenzuordnung

Benenne die Datei mit dem Kundennamen, dann landet sie automatisch beim
richtigen Kunden: `Kerstin Wenzel 071026.opus`. Datum/Zahlen sind egal.

## Falls mal nichts passiert

- Liegt die Datei wirklich im Ordner (Alias auf dem Schreibtisch)?
- Endung `.opus`/`.m4a`/`.ogg`/`.wav`? (Eine fertige `.mp3` wird bewusst ignoriert.)
- Log ansehen: `~/Library/Logs/com.local.whatsapp-transkription.log`
- Manueller Start als Rückfallebene: `bash ~/WhatsApp-Audio-Eingang/.engine/verarbeiten.sh`

## Technik / Quelle

Repo (teilbare Vorlage): `Code/whatsapp-notion-transkription`.
Live-Engine: `~/WhatsApp-Audio-Eingang/.engine/`.
