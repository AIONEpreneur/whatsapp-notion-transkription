#!/usr/bin/env python3
"""
Transkript -> Notion.

Liest .txt/.vtt-Dateien aus dem Transkripte-Ordner, laesst Claude das
Transkript analysieren (Zusammenfassung, offene Fragen, Testimonial-Potenzial),
legt eine Notion-Seite in der Transkript-Datenbank an, benachrichtigt optional
Slack und archiviert die Datei nach Verarbeitet/.

Zwei Betriebsarten:
  python3 transkript_zu_notion.py          interaktiv (fragt Kunde + Titel)
  python3 transkript_zu_notion.py --auto    vollautomatisch (fuer den Watcher):
                                            Kunde wird aus dem Dateinamen erkannt,
                                            kein Terminal-Dialog, kein Warten.

Keine externen Abhaengigkeiten - nur Python-Stdlib.
Konfiguration: konfiguration.json (DB-IDs, Pfade) + .env (Tokens).
"""
import json
import os
import re
import sys
import datetime
import shutil
import urllib.request
import urllib.error
from pathlib import Path

# --- Pfade / Konfiguration ---
SCRIPT_DIR = Path(__file__).parent.resolve()
AUTO = "--auto" in sys.argv

def load_config():
    cfg_file = SCRIPT_DIR / "konfiguration.json"
    if not cfg_file.exists():
        sys.exit("[Fehler] konfiguration.json fehlt. Kopiere konfiguration.beispiel.json "
                 "nach konfiguration.json und trage deine Werte ein.")
    return json.loads(cfg_file.read_text(encoding="utf-8"))

CFG = load_config()
TRANSKRIPTE_DIR = Path(os.path.expanduser(CFG["transkripte_ordner"])).resolve()
ARCHIV_DIR = TRANSKRIPTE_DIR / "Verarbeitet"
ENV_FILE = Path(os.path.expanduser(CFG.get("env_datei", "~/.config/whatsapp-workflow/.env")))
CRM_DB_ID = CFG["crm_db_id"]
TRANSCRIPT_DB_ID = CFG["transkript_db_id"]
ANTHROPIC_MODEL = CFG.get("anthropic_model", "claude-sonnet-4-5")
NOTION_VERSION = "2022-06-28"

# --- .env laden ---
def load_env(key, required=True):
    if not ENV_FILE.exists():
        if required:
            sys.exit(f"[Fehler] Token-Datei fehlt: {ENV_FILE}")
        return None
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    if required:
        sys.exit(f"[Fehler] {key} nicht in .env gefunden")
    return None

TOKEN = load_env("NOTION_TOKEN")
SLACK_WEBHOOK = load_env("SLACK_WEBHOOK_URL", required=False)
ANTHROPIC_API_KEY = load_env("ANTHROPIC_API_KEY", required=False)
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

# --- Notion API ---
def notion_request(method, path, body=None):
    url = f"https://api.notion.com/v1{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        sys.exit(f"[Fehler] Notion API ({e.code}):\n{err}\n\n"
                 f"Tipp: Sind die Datenbanken mit der Integration geteilt?")

def fetch_customers():
    result = notion_request("POST", f"/databases/{CRM_DB_ID}/query", {"page_size": 100})
    customers = []
    for page in result.get("results", []):
        title_prop = page["properties"].get("Name", {}).get("title", [])
        name = title_prop[0]["plain_text"] if title_prop else "(ohne Name)"
        customers.append({"id": page["id"], "name": name})
    customers.sort(key=lambda c: c["name"].lower())
    return customers

# --- Kunde aus Dateiname erkennen (Auto-Modus) ---
def kunde_aus_dateiname(dateiname, customers):
    """Versucht, aus 'Kerstin Wenzel 071026.txt' den Kunden 'Kerstin Wenzel' zu finden.
    Gibt (customer_id, customer_name) oder (None, None) zurueck."""
    stem = Path(dateiname).stem
    # Datums-/Zahl-Tokens und WhatsApp-Standardpraefixe entfernen
    bereinigt = re.sub(r'\b\d[\d.\-: ]*\b', ' ', stem)
    bereinigt = re.sub(r'(?i)whatsapp|audio|ptt|at|voice|sprachnachricht', ' ', bereinigt)
    bereinigt = re.sub(r'\s+', ' ', bereinigt).strip().lower()
    if not bereinigt:
        return (None, None)
    # Bester Treffer: Kundenname kommt im bereinigten Dateinamen vor (oder umgekehrt)
    treffer = []
    for c in customers:
        cl = c["name"].lower()
        if cl and (cl in bereinigt or bereinigt in cl):
            treffer.append((len(cl), c))
    if treffer:
        treffer.sort(reverse=True)  # laengster/spezifischster Name zuerst
        c = treffer[0][1]
        return (c["id"], c["name"])
    return (None, None)

# --- Textaufbereitung ---
def split_by_sentences(text, max_sentences=3, max_chars=400):
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZAEOEUE])', text)
    paragraphs, current, char_count = [], [], 0
    for s in sentences:
        current.append(s)
        char_count += len(s)
        if len(current) >= max_sentences or char_count >= max_chars:
            paragraphs.append(" ".join(current))
            current, char_count = [], 0
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs

def format_for_notion(text):
    text = text.strip()
    if not text:
        return [""]
    text = re.sub(r'^\d{2}:\d{2}:\d{2}\s+Speaker:\s*', '', text)
    if "\n\n" in text:
        rough = [p.strip() for p in text.split("\n\n") if p.strip()]
        raw_paragraphs = []
        for block in rough:
            block = re.sub(r'^\d{2}:\d{2}:\d{2}\s+Speaker:\s*', '', block)
            if len(block) > 250:
                raw_paragraphs.extend(split_by_sentences(block))
            else:
                raw_paragraphs.append(block)
    else:
        raw_paragraphs = split_by_sentences(text)
    final = []
    for p in raw_paragraphs:
        while len(p) > 1900:
            final.append(p[:1900])
            p = p[1900:]
        final.append(p)
    return final

# --- Claude-Analyse ---
ANALYSIS_PROMPT = """Du bekommst gleich ein Transkript einer Sprachnachricht eines Kunden.

Analysiere es und gib EXAKT ein JSON-Objekt zurueck (keine Markdown-Code-Bloecke, kein Text drumherum):

{
  "zusammenfassung": "2-3 Saetze, was der Kunde sagt (auf Deutsch)",
  "fragen": ["Frage 1 (originalgetreu rekonstruiert, ggf. korrigiert)", "Frage 2", ...],
  "ist_testimonial": true/false,
  "testimonial_zitate": ["zitatfaehige Stelle 1", "Stelle 2", ...],
  "testimonial_begruendung": "Kurze Erklaerung (1 Satz), warum (nicht) Testimonial"
}

- "fragen": leeres Array [], wenn keine Fragen gestellt werden.
- "ist_testimonial": true wenn der Kunde lobt, Erfolge schildert, dankt - Stellen, die als Social Proof taugen.
- "testimonial_zitate": leeres Array [] wenn ist_testimonial false.
- Bei offensichtlichen Whisper-Hoerfehlern dezent korrigieren.

Transkript:
---
"""

def analyze_with_claude(text):
    if not ANTHROPIC_API_KEY:
        if not AUTO:
            print("   [Hinweis] ANTHROPIC_API_KEY fehlt in .env - Analyse uebersprungen")
        return None
    full_prompt = ANALYSIS_PROMPT + text + "\n---"
    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": full_prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            response = json.loads(r.read())
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"   [Hinweis] Anthropic-API-Fehler: {e}")
        return None
    output = response["content"][0]["text"].strip()
    m = re.search(r'\{[\s\S]*\}', output)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None

# --- Slack ---
def send_slack(kunde, zusammenfassung, fragen, testimonial, notion_url):
    if not SLACK_WEBHOOK:
        return False
    payload = {
        "kunde": kunde or "Unbekannt",
        "zusammenfassung": zusammenfassung or "(keine)",
        "fragen": "\n- " + "\n- ".join(fragen) if fragen else "(keine)",
        "testimonial": testimonial or "(kein Testimonial)",
        "notion_url": notion_url,
    }
    req = urllib.request.Request(SLACK_WEBHOOK, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status < 300
    except urllib.error.URLError:
        return False

# --- Notion-Seite anlegen ---
def create_transcript_page(title, customer_id, transcript_text, original_filename, analysis=None):
    today = datetime.date.today().isoformat()
    paragraphs = format_for_notion(transcript_text)
    properties = {
        "Titel": {"title": [{"text": {"content": title[:200]}}]},
        "Datum": {"date": {"start": today}},
        "Status": {"select": {"name": "Neu"}},
        "Quelle": {"select": {"name": "WhatsApp"}},
        "Transkript": {"rich_text": [{"text": {"content": transcript_text[:1900]}}]},
        "Originaldatei": {"rich_text": [{"text": {"content": original_filename}}]},
    }
    if customer_id:
        properties["Kunde"] = {"relation": [{"id": customer_id}]}

    def heading(text, level=2):
        key = f"heading_{level}"
        return {"object": "block", "type": key, key: {"rich_text": [{"text": {"content": text}}]}}
    def paragraph(text):
        return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": text}}]}}
    def bullet(text):
        return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"text": {"content": text}}]}}
    def callout(text, icon="💡", color="blue_background"):
        return {"object": "block", "type": "callout", "callout": {
            "rich_text": [{"text": {"content": text}}], "icon": {"type": "emoji", "emoji": icon}, "color": color}}

    children = []
    if analysis:
        if analysis.get("zusammenfassung"):
            children.append(heading("Zusammenfassung"))
            children.append(callout(analysis["zusammenfassung"], "📌", "gray_background"))
        if analysis.get("fragen"):
            children.append(heading("Offene Fragen"))
            for f in analysis["fragen"]:
                children.append(bullet(f))
        if analysis.get("ist_testimonial"):
            children.append(heading("Testimonial-Potenzial"))
            children.append(callout(analysis.get("testimonial_begruendung", ""), "⭐", "yellow_background"))
            for q in analysis.get("testimonial_zitate", []):
                children.append({"object": "block", "type": "quote",
                                 "quote": {"rich_text": [{"text": {"content": q}}]}})
    children.append(heading("Transkript"))
    for p in paragraphs:
        children.append(paragraph(p))

    body = {"parent": {"database_id": TRANSCRIPT_DB_ID}, "properties": properties, "children": children}
    return notion_request("POST", "/pages", body)

# --- Datei-Reader ---
def read_txt(path):
    return path.read_text(encoding="utf-8", errors="replace")
READERS = {".txt": read_txt, ".vtt": read_txt}
IGNORE_PREFIXES = ("SETUP", "README", "ANLEITUNG", "EINRICHTUNG", "VIDEO-SKRIPT")

# --- Interaktive Kundenauswahl ---
def choose_customer(customers):
    print("\nWelcher Kunde?\n")
    for i, c in enumerate(customers, 1):
        print(f"  [{i:2}] {c['name']}")
    print(f"  [ 0] (kein Kunde / unbekannt)")
    print(f"  [ n] (neuen Kunden anlegen)")
    while True:
        choice = input("\n-> Nummer: ").strip().lower()
        if choice == "0":
            return None
        if choice == "n":
            name = input("   Name des neuen Kunden: ").strip()
            if not name:
                continue
            new_page = notion_request("POST", "/pages", {
                "parent": {"database_id": CRM_DB_ID},
                "properties": {"Name": {"title": [{"text": {"content": name}}]},
                               "Status": {"select": {"name": "Lead"}}}})
            print(f"   Kunde '{name}' angelegt.")
            return new_page["id"]
        if choice.isdigit() and 1 <= int(choice) <= len(customers):
            return customers[int(choice) - 1]["id"]
        print("   Bitte gueltige Nummer eingeben.")

# --- Hauptlogik ---
def main():
    ARCHIV_DIR.mkdir(exist_ok=True)
    files = [f for f in TRANSKRIPTE_DIR.iterdir()
             if f.is_file() and f.suffix.lower() in READERS
             and not f.name.startswith(".")
             and not f.name.upper().startswith(IGNORE_PREFIXES)]
    if not files:
        if not AUTO:
            print(f"[Hinweis] Keine Transkript-Dateien (.txt/.vtt) in {TRANSKRIPTE_DIR}")
        return

    customers = fetch_customers()
    if not AUTO:
        print(f"{len(files)} Datei(en), {len(customers)} Kunden geladen.\n")

    for f in files:
        text = READERS[f.suffix.lower()](f)

        if AUTO:
            customer_id, cname = kunde_aus_dateiname(f.name, customers)
            label = cname or "WhatsApp-Nachricht"
            title_input = f"{label} - {datetime.date.today().isoformat()}"
            print(f"[auto] {f.name} -> Kunde: {cname or 'unbekannt'}")
        else:
            print(f"\n=== {f.name} ===")
            preview = (text[:200] + "...") if len(text) > 200 else text
            print(f"Vorschau:\n  {preview}\n")
            customer_id = choose_customer(customers)
            title_input = input("\n-> Titel (Enter = automatisch): ").strip()
            if not title_input:
                cname = next((c["name"] for c in customers if c["id"] == customer_id), None)
                label = cname if cname else "WhatsApp-Nachricht"
                title_input = f"{label} - {datetime.date.today().isoformat()}"
            cname = next((c["name"] for c in customers if c["id"] == customer_id), None)

        analysis = analyze_with_claude(text)
        page = create_transcript_page(title_input, customer_id, text, f.name, analysis)
        print(f"   -> Notion: {page['url']}")

        if analysis and SLACK_WEBHOOK:
            relevant = bool(analysis.get("fragen")) or analysis.get("ist_testimonial")
            if relevant:
                testimonial_text = ""
                if analysis.get("ist_testimonial"):
                    zitate = analysis.get("testimonial_zitate", [])
                    testimonial_text = (analysis.get("testimonial_begruendung", "") +
                                        ("\n\n" + "\n\n".join(zitate) if zitate else ""))
                send_slack(cname, analysis.get("zusammenfassung", ""),
                           analysis.get("fragen") or [], testimonial_text, page["url"])

        shutil.move(str(f), str(ARCHIV_DIR / f.name))
        print(f"   -> archiviert: Verarbeitet/{f.name}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        sys.exit(1)
