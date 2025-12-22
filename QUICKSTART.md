# Quick Start Guide

## 30-Sekunden-Setup

```bash
# 1. Dependencies installieren
pip install -r requirements.txt

# 2. Deine URL in config.yaml ändern (optional)
# Oder default pCloud-Docs verwenden

# 3. Crawl starten
python full_pipeline.py

# 4. Output im /output Ordner
```

**Fertig!** → `output/documentation.docx`

---

## Voreingestellte Beispiele

### pCloud API (Standard)
```bash
python full_pipeline.py
```
→ 37 Seiten, 331 Elemente, 49 KB DOCX, ~8s

### Eigene Website crawlen
**Schritt 1:** `config.yaml` bearbeiten
```yaml
crawler:
  entry_url: "https://docs.example.com/"
```

**Schritt 2:** Content-Selector anpassen (optional)
```yaml
parser:
  content_selectors:
    - "div.main-content"  # Für deine Website
    - "main"
```

**Schritt 3:** Crawl starten
```bash
python full_pipeline.py
```

---

## Kommandos

| Kommando | Was es macht | Wann nutzen |
|----------|-------------|-----------|
| `python full_pipeline.py` | Komplett: Crawl → Parse → DOCX | Produktion |
| `python run_full_crawl.py` | Nur Crawl + Parsing | Debug |
| `python test_quick.py` | Test mit 5 Seiten | Schnell testen |
| `python sidebar_parser.py` | Navigation extrahieren | Debug Navigation |

---

## Häufige Probleme

**❌ "Max retries exceeded"**
```yaml
# config.yaml → erhöhen:
crawler:
  timeout_seconds: 15  # statt 10
  max_retries: 5      # statt 3
```

**❌ "Keine Content gefunden"**
```bash
# Mit Browser Inspector CSS-Selektor finden:
parser:
  content_selectors:
    - "div.page-content"  # DEINE CSS anpassen
```

**❌ "PDF konvertierung fehlgeschlagen"**
- LibreOffice optional – DOCX funktioniert auch ohne
- Optional: LibreOffice installieren für PDF

---

## Output verstehen

```
output/
├── documentation.docx    ← Hauptdokument
├── documentation.pdf     ← Optional (LibreOffice)
└── cache/                ← HTML-Cache (lokal)
```

**DOCX enthält:**
- Titelseite
- Inhaltsverzeichnis (manuell)
- Alle Seiten mit Überschriften
- Fehler-Log am Ende

---

## Tipps & Tricks

### Nur spezifische Kategorien crawlen
Cache löschen + `config.yaml` anpassen:
```bash
rm -r cache output
# dann python full_pipeline.py
```

### Schneller testen
```bash
python test_quick.py  # Nur 5 Seiten → 3 Sekunden
```

### Debugging
Logs in `console` + Dateiname zeigt URL:
```
[  8/37] Binary API SDK                                     (45 elements)
        ↑ Seite 8 von 37, 45 Elemente extrahiert
```

### Cache nutzen
HTML wird lokal gecacht → schneller bei Wiederholung:
```bash
python full_pipeline.py  # 2. Mal: ohne Netzwerk-Delay
```

---

## Anforderungen

- Python 3.7+
- Internet (zum Crawlen)
- ~100 MB Disk (für Cache + Output)

Optional:
- LibreOffice (für PDF)

---

## Wo du anfangen kannst

1. **pCloud API testen** (vorkonfiguriert):
   ```bash
   python full_pipeline.py
   ```

2. **Eigene Dokumentation**:
   - URL in `config.yaml` eintragen
   - Evtl. CSS-Selektoren anpassen
   - `python full_pipeline.py` starten

3. **Erweitern**:
   - `parser.py` - mehr Element-Typen hinzufügen
   - `docx_generator.py` - eigenes Design
   - `config.yaml` - neue Parameter

---

## Support

Lese:
- `README.md` - Vollständige Dokumentation
- `config.yaml` - Alle Parameter
- Code-Kommentare in `crawler.py`, `parser.py`

Frag bei Problemen!
