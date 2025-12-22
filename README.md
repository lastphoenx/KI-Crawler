# Web Documentation Crawler

Ein intelligentes **Web-Crawling-System**, das HTML-Dokumentationen vollautomatisiert crawlt und in strukturierte **DOCX/PDF-Dokumente** konvertiert.

## Features

✅ **Intelligentes 2-Level Crawling**
- Extrahiert automatisch Top-Level Navigation
- Folgt Kategorie-Links und Detail-Seiten
- Duplicate-Detection & Error-Handling

✅ **Umfassender Content Parser**
- Headings (h1-h4), Paragraphen, Code-Blöcke
- Listen (ul/ol), Tabellen, Definition-Lists
- Info-Boxen, Blockquotes, nested Content
- 331+ Elemente aus 37 Seiten in Test

✅ **Professionelle DOCX-Generierung**
- Strukturierte Überschriften & Inhaltsverzeichnis
- Tabellen mit Styling
- Code-Blöcke mit Syntax-Hervorhebung
- Fehler-Log & Fehler-Behandlung

✅ **Retry & Error Handling**
- 3x Retry mit exponential backoff
- Detaillierte Fehlerprotokolle
- Graceful degradation bei Fehlern

## Installation

### 🚀 Option A: Automatisches Setup (empfohlen)

```bash
# Repository klonen
git clone https://github.com/lastphoenx/KI-Crawler.git
cd KI-Crawler

# Setup-Script ausführen (installiert alles automatisch)
chmod +x setup.sh
./setup.sh
```

Das Script installiert automatisch:
- ✅ System-Bibliotheken (Linux/WSL: libxml2, libxslt, etc.)
- ✅ Python Virtual Environment
- ✅ Alle Python-Dependencies aus requirements.txt
- ✅ Playwright-Browser (Chromium ~280 MB für JavaScript-Rendering)

Nach dem Setup:
```bash
source venv/bin/activate  # Virtual Environment aktivieren
python main_ui.py         # Web-UI starten
```

---

### 🔧 Option B: Manuelle Installation

### Voraussetzungen
- **Python 3.10+** (getestet mit Python 3.13)
- **pip** (Python Package Manager)
- **Git** (für Repository-Klonen)

### Schritt 1: Repository klonen
```bash
git clone https://github.com/lastphoenx/KI-Crawler.git
cd KI-Crawler
```

### Schritt 2: Virtual Environment erstellen
```bash
# Linux/macOS/WSL
python3 -m venv venv
source venv/bin/activate

# Windows (CMD)
python -m venv venv
venv\Scripts\activate.bat

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

### Schritt 3: Dependencies installieren

**Linux/WSL - Erst System-Bibliotheken:**
```bash
# Für lxml und andere C-Extensions
sudo apt install -y libxml2-dev libxslt1-dev python3-dev zlib1g-dev

# Dann Python-Pakete
pip install --upgrade pip
pip install -r requirements.txt

# Playwright-Browser installieren (für JavaScript-Rendering)
playwright install chromium
```

**macOS:**
```bash
# System-Bibliotheken (falls nötig)
brew install libxml2 libxslt

# Python-Pakete
pip install --upgrade pip
pip install -r requirements.txt

# Playwright-Browser installieren (für JavaScript-Rendering)
playwright install chromium
```

**Windows:**
```bash
# Direkt installieren (keine System-Libs nötig)
pip install --upgrade pip
pip install -r requirements.txt

# Playwright-Browser installieren (für JavaScript-Rendering)
playwright install chromium
```

### Schritt 4: Konfiguration (Optional)
```bash
# Falls du API Keys oder Secrets benötigst
cp .env.example .env
nano .env  # Bearbeiten nach Bedarf
```

**Wichtig:** Die Ordner `output/`, `cache/`, `logs/` werden **automatisch erstellt** beim ersten Start.

### Schritt 5: Optional - LibreOffice für PDF-Export
```bash
# Ubuntu/Debian/WSL
sudo apt install -y libreoffice

# macOS
brew install libreoffice

# Windows
# Download: https://www.libreoffice.org/download/
```

**Core Abhängigkeiten:**
- `requests` - HTTP-Requests
- `beautifulsoup4` - HTML-Parsing
- `python-docx` - DOCX-Generierung (v1.2.0+)
- `pyyaml` - Konfiguration (v6.0.2+)
- `lxml` - XML-Parsing (v5.0+)
- `fastapi` / `nicegui` - Web UI
- `playwright` - JavaScript-Rendering für SPAs

**System-Kompatibilität:**
- ✅ Linux (Ubuntu, Debian, Arch, etc.)
- ✅ macOS (Intel & Apple Silicon)
- ✅ Windows 10/11
- ✅ WSL (Windows Subsystem for Linux)
- ✅ Docker (siehe Dockerfile)

**Hinweise:**
- Alle **Pfade in config.yaml sind relativ** (./output, ./cache) → funktioniert auf allen Systemen
- **Keine Datenbank** erforderlich (File-basiertes System)
- **Ordner werden automatisch erstellt** beim ersten Start

## Verwendung

### Schnellstart (5 Minuten)

```bash
python scripts/run_full_crawl.py
```

Dies crawlt die **pCloud API-Dokumentation** (konfiguriert in `config.yaml`) und erzeugt:
- `output/documentation.docx` - strukturiertes Word-Dokument
- `output/documentation.pdf` - (optional mit LibreOffice)

### Für andere Websites

Bearbeite `config.yaml`:

```yaml
crawler:
  entry_url: "https://your-docs.example.com/"  # Start-URL
  max_retries: 3                                 # Retry-Versuche
  timeout_seconds: 10                            # Request-Timeout

parser:
  content_selectors:
    - "div.main-content"  # CSS-Selektoren für Content-Area
    - "main"
    - "article"
  title_selectors:
    - "h1"
    - ".page-title"

document:
  title: "Your Documentation"
  author: "Your Name"
```

Dann ausführen:

```bash
python full_pipeline.py
```

## Architektur

```
crawler.py           (37 Seiten, 0 Fehler)
    ↓
parser.py            (331 Elemente extrahiert)
    ↓
docx_generator.py    (49 KB DOCX)
    ↓
pdf_converter.py     (optional PDF)
```

### Crawler
- **2-Level Navigation**: Top-Level Links → Submenu-Links
- **Queue-basiert**: Intelligente URL-Verwaltung
- **Robustheit**: Retry-Logik, Duplicate-Check

### Parser
- **Rekursive Extraktion**: Alle verschachtelten Elemente
- **Element-Typen**: 15+ verschiedene Content-Typen
- **Intelligente Deduplication**: Duplikate entfernen

### DOCX-Generator
- **Hierarchische Struktur**: h1-h4 korrekt formatiert
- **Styling**: Farben, Fonts, Abstände
- **Tabellen**: Mit Alt-Row-Farben
- **Error-Handling**: Fehlerseiten mit Placeholders

## Ergebnisse (pCloud API-Test)

| Metrik | Wert |
|--------|------|
| **Seiten gecrawlt** | 37 |
| **Listing-Seiten gefiltert** | 13 |
| **Detail-Seiten im DOCX** | 24 |
| **Crawl-Fehler** | 0 |
| **Elemente extrahiert** | 331 |
| **Durchschnitt/Seite** | 8.9 |
| **DOCX-Größe** | 50 KB |
| **Runtime** | ~9 Sekunden |

### Smart Listing-Filter

Das System erkennt automatisch **Listing/Index-Seiten** (die nur Links enthalten) und filtert sie aus dem Output. Nur echte Detail-Seiten mit vollständigem Content gehen ins DOCX.

## CLI-Skripte

| Skript | Beschreibung |
|--------|-------------|
| `full_pipeline.py` | Komplette Pipeline (Crawl → Parse → DOCX) |
| `run_full_crawl.py` | Nur Crawl + Parsing, ohne DOCX |
| `test_quick.py` | Test mit 5 Seiten |
| `sidebar_parser.py` | Test der Navigation-Extraktion |

## Konfiguration

### config.yaml - Haupt-Parameter

```yaml
crawler:
  entry_url: "https://..."        # Startseite
  max_retries: 3                  # Fehler-Versuche
  retry_backoff_factor: 2         # Exponential backoff
  timeout_seconds: 10             # Request-Timeout
  user_agent: "Mozilla/..."       # User-Agent Header

parser:
  content_selectors: [...]        # CSS für Content-Area
  title_selectors: [...]          # CSS für Titel
  code_block_selector: "..."      # CSS für Code-Blöcke
  table_selector: "table"         # CSS für Tabellen
  note_box_selector: "..."        # CSS für Info-Boxen

document:
  title: "..."                    # Dokument-Titel
  author: "..."                   # Autor
  style: "professional"           # Design-Stil
  include_toc: true               # Inhaltsverzeichnis
  include_error_log: true         # Fehler-Anhang

output:
  docx_filename: "..."            # DOCX-Name
  pdf_filename: "..."             # PDF-Name
  cache_dir: "./cache"            # Cache-Verzeichnis
  output_dir: "./output"          # Output-Verzeichnis
```

## Troubleshooting

**Problem:** "Max retries exceeded"
- **Lösung**: `timeout_seconds` erhöhen, `max_retries` erhöhen

**Problem:** Parser findet wenig Content
- **Lösung**: `content_selectors` in `config.yaml` anpassen (inspect mit Browser)

**Problem:** PDF-Konvertierung fehlgeschlagen
- **Lösung**: LibreOffice installieren oder optional überspringen
  ```bash
  # Ubuntu
  sudo apt-get install libreoffice
  # macOS
  brew install libreoffice
  # Windows: https://www.libreoffice.org/download/
  ```

**Problem:** Netzwerkfehler beim Crawlen
- **Lösung**: VPN prüfen, `timeout_seconds` erhöhen, URLs whitelisten

## Performance

- **Crawl-Zeit**: ~0.3s pro Seite
- **Parse-Zeit**: ~0.1s pro Seite
- **DOCX-Gen**: ~0.8s
- **Total**: ~8-15s für ~40 Seiten

## Erweiterungen

Mögliche Verbesserungen:
- [ ] Sitemap.xml automatisch parsen
- [ ] JavaScript-gerenderte Seiten (Selenium)
- [ ] Multilingual-Support
- [ ] Custom CSS → DOCX Styling
- [ ] Export zu Markdown, PDF, HTML
- [ ] Web UI für Konfiguration

## Lizenz

MIT

## Support

Probleme? Fehlermeldungen prüfen in `*.log` oder Ausgabe.

---

**Happy Crawling!**
