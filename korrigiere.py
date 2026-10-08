#!/usr/bin/env python3
"""
Wendet die Regeln aus korrekturen.txt auf eine Transkript-Datei an.

    python3 korrigiere.py "Transkripte/Datei.txt"

Hintergrund: Whisper hoert Eigennamen oft falsch (z. B. Markennamen). Der Weg
ueber whisper's --prompt hilft unzuverlaessig, deshalb wird hier nach der
Transkription deterministisch ersetzt. korrekturen.txt ist frei editierbar.
Fehlt die Datei, passiert nichts (kein Fehler).
"""
import re
import sys
from pathlib import Path

REGEL_DATEI = Path(__file__).resolve().parent / "korrekturen.txt"

def lies_regeln(pfad=REGEL_DATEI):
    regeln = []
    if not pfad.exists():
        return regeln
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=>" not in zeile:
            continue
        falsch, richtig = zeile.split("=>", 1)
        falsch, richtig = falsch.strip(), richtig.strip()
        if falsch:
            regeln.append((falsch, richtig))
    return sorted(regeln, key=lambda r: len(r[0]), reverse=True)

def korrigiere(text, regeln):
    gesamt = 0
    for falsch, richtig in regeln:
        muster = re.compile(r"\b" + re.escape(falsch) + r"\b", re.IGNORECASE)
        text, anzahl = muster.subn(richtig, text)
        gesamt += anzahl
    return text, gesamt

def main():
    if len(sys.argv) < 2:
        raise SystemExit("Aufruf: python3 korrigiere.py <transkript.txt>")
    datei = Path(sys.argv[1])
    if not datei.exists():
        raise SystemExit(f"[Fehler] Datei nicht gefunden: {datei}")
    regeln = lies_regeln()
    if not regeln:
        return 0
    original = datei.read_text(encoding="utf-8")
    neu, anzahl = korrigiere(original, regeln)
    if anzahl:
        datei.write_text(neu, encoding="utf-8")
        print(f"   {anzahl} Eigenname(n) korrigiert")
    return 0

if __name__ == "__main__":
    sys.exit(main())
