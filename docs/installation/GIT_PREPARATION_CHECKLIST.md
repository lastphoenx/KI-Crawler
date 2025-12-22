# 🔧 Git-Vorbereitung Checkliste

Folge dieser Checkliste, um das Projekt git-ready zu machen.

## ✅ Abgeschlossen (Automatisch)

- [x] `.gitignore` erstellt
- [x] `README.md` mit detaillierter Installation aktualisiert

## 🔄 Manuell durchführen

### 1. Root-Verzeichnis aufräumen (optional aber empfohlen)

```bash
# Alte Version archivieren
mv docx_generator.py _archive/docx_generator_v1.py

# Sketch/Experimentelle Datei archivieren  
mv main_ui.py _archive/main_ui_sketch.py

# Redundant - wird in scripts/ verschoben (nächster Schritt)
```

### 2. Scripts-Verzeichnis erstellen und Hilfsdateien verschieben

```bash
mkdir -p scripts

# Test/CLI-Skripte
mv run_full_crawl.py scripts/
mv sidebar_parser.py scripts/
mv categorizer.py scripts/
mv method_extractor.py scripts/
```

### 3. Dokumentation in docs/ organisieren (optional)

```bash
mkdir -p docs

# Prozess-Dokumentation
mv CRAWL_TROUBLESHOOTING.md docs/troubleshooting.md
mv TESTING_GUIDE.md docs/testing.md
mv DEPLOYMENT_OVERVIEW.md docs/deployment.md
mv REAL_CRAWLER_INTEGRATION.md docs/integration.md
mv MEMORY_PROFILING.md docs/performance.md

# Archivieren (Sprint-Notizen)
mv WEEK3_SUMMARY.md _archive/
mv QUICK_WINS_SUMMARY.md _archive/
mv DEPLOYMENT_CHECKLIST.md _archive/
mv CSS_DOWNLOAD_FEATURE.md _archive/
mv DEDUPLICATION_AND_LINKS.md _archive/
mv DEEP_REVIEW.md _archive/
```

### 4. Redundante md-Dateien prüfen

Diese sind teilweise redundant oder veraltet:
- `QUICKSTART.md` - Duplikat zu `QUICK_START_DEBIAN.md` → entfernen oder mergen
- `INSTALLATION_DEBIAN_DOCKER.md` - Spezialfall, wenn Docker wichtig → in `docs/` verschieben
- `QUICK_START_DEBIAN.md` - Wenn Debian-spezifisch, in `docs/` → `docs/installation-debian.md`

```bash
# Beispiel
rm QUICKSTART.md  # oder in README integrieren
mv INSTALLATION_DEBIAN_DOCKER.md docs/installation-docker.md
mv QUICK_START_DEBIAN.md docs/quickstart-debian.md
```

## 📊 Vorher/Nachher Vergleich

### VORHER (chaotisch)
```
KI-Crawler/
├── 15 *.md Dateien im Root
├── venv/ (338 MB - NICHT in .gitignore!)
├── __pycache__/ (NICHT in .gitignore!)
├── cache/, logs/, output/ (Runtime-Daten)
├── docx_generator.py (redundant)
├── main_ui.py (Sketch)
├── run_full_crawl.py (sollte in scripts/)
└── sidebar_parser.py (sollte in scripts/)
```

### NACHHER (sauber)
```
KI-Crawler/
├── README.md (Hauptdoku)
├── requirements.txt
├── config.yaml
├── .gitignore ✅
│
├── src/ (Core Logic)
├── app/ (Web UI)
├── models/ (Data)
├── services/ (Business Logic)
│
├── scripts/ (CLI-Hilfsskripte)
├── docs/ (Dokumentation)
├── _archive/ (Alte Dateien)
│
├── venv/ 🚫 (in .gitignore)
├── cache/ 🚫 (in .gitignore)
├── logs/ 🚫 (in .gitignore)
└── output/ 🚫 (in .gitignore)
```

## 🚀 Git initialisieren

Nachdem du die obigen Schritte durchgeführt hast:

```bash
# Git repo initialisieren
git init

# Alle Dateien hinzufügen (ignoriert .gitignore)
git add .

# Überprüfen was committet wird
git status

# Commitmeldung
git commit -m "Initial commit: Web Documentation Crawler"

# Remote hinzufügen
git remote add origin https://github.com/username/KI-Crawler.git

# Pushen
git push -u origin main
```

## ⚠️ Wichtig: Venv nicht committen!

Stelle sicher, dass `venv/` Verzeichnis **nicht** in git ist:

```bash
# Sollte NICHT angezeigt werden:
git status venv

# Wenn es doch angezeigt wird:
git rm --cached -r venv
git commit -m "Remove venv from tracking"
```

## 📋 Struktur-Umbenennungsidee

Optional: Wenn mehrere zusammenhängende Module sind, in `src/` verschieben:

```bash
mkdir -p src
mv crawler.py src/
mv parser.py src/
mv navigation_strategy.py src/
mv api_parser.py src/
# ... etc
```

Dann in Skripten aktualisieren:
```python
from src.crawler import Crawler
from src.parser import Parser
```

---

**Nach Abschluss:** Projekt ist produktionsbereit für GitHub/GitLab! 🚀
