# KI-Crawler: Installation auf Debian (Docker)

## Überblick

Diese Anleitung zeigt die **Schritt-für-Schritt Installation** deiner KI-Crawler App auf einer **Debian VM in Proxmox**.

---

## Phase 1: Debian VM vorbereiten

### 1.1 System aktualisieren
```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 1.2 Docker installieren
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

Validieren:
```bash
docker --version
docker run hello-world
```

### 1.3 Docker Compose installieren
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

---

## Phase 2: KI-Crawler Dateien zur Debian VM übertragen

### Welche Dateien du kopieren musst

**Schritt 1: Auf Windows - Diese Ordner/Dateien kopieren:**

```
C:\Users\santinel\Documents\Apps\KI-Crawler\
├── app/                          ✅ KOPIEREN
├── components/                   ✅ KOPIEREN
├── models/                       ✅ KOPIEREN
├── pages/                        ✅ KOPIEREN
├── services/                     ✅ KOPIEREN
├── templates/                    ✅ KOPIEREN
├── *.py (Hauptdateien):
│   ├── main_ui.py               ✅ KOPIEREN
│   ├── crawler.py               ✅ KOPIEREN
│   ├── parser.py                ✅ KOPIEREN
│   ├── html_generator.py        ✅ KOPIEREN
│   ├── markdown_generator.py    ✅ KOPIEREN
│   ├── docx_generator.py        ✅ KOPIEREN
│   ├── docx_generator_v2.py     ✅ KOPIEREN
│   ├── pdf_converter.py         ✅ KOPIEREN
│   ├── rate_limiter.py          ✅ KOPIEREN
│   ├── sitemap_parser.py        ✅ KOPIEREN
│   ├── image_handler.py         ✅ KOPIEREN
│   ├── api_parser.py            ✅ KOPIEREN
│   ├── openapi_detector.py      ✅ KOPIEREN
│   ├── navigation_strategy.py   ✅ KOPIEREN
│   ├── rendering_strategy.py    ✅ KOPIEREN
│   ├── syntax_highlighter.py    ✅ KOPIEREN
│   ├── sidebar_parser.py        ✅ KOPIEREN
│   ├── template_manager.py      ✅ KOPIEREN
│   ├── categorizer.py           ✅ KOPIEREN
│   ├── method_extractor.py      ✅ KOPIEREN
│   └── full_pipeline.py         ✅ KOPIEREN
├── config.yaml                  ✅ KOPIEREN
├── requirements.txt             ✅ KOPIEREN
├── Dockerfile                   ✅ KOPIEREN
├── docker-compose.yml           ✅ KOPIEREN
├── .dockerignore                ✅ KOPIEREN
└── README.md                    ✅ KOPIEREN (optional)
```

**NICHT kopieren** (nicht nötig für Docker):
```
__pycache__/                     ❌ Wird durch Docker neu generiert
cache/                           ❌ Cache-Verzeichnis (wird neu erstellt)
output/                          ❌ Output-Verzeichnis (wird neu erstellt)
*.log                            ❌ Log-Dateien (nicht nötig)
test_*.py                        ❌ Test-Dateien (nicht nötig)
debug_*.py                       ❌ Debug-Skripte
check_*.py                       ❌ Check-Skripte
analyze_*.py                     ❌ Analyze-Skripte
verify_*.py                      ❌ Verify-Skripte
*.docx                           ❌ Alte DOCX-Dateien
*.md (außer README)              ❌ Dokumentation (optional)
run_full_crawl.py               ❌ Legacy-Skript (wir nutzen main_ui.py)
```

### Schritt 2: Dateien übertragen

**Option A: SCP (von Windows PowerShell oder WSL)**
```powershell
# Alle Dateien mit SCP kopieren
scp -r "C:\Users\santinel\Documents\Apps\KI-Crawler\*" debian_user@debian_ip:/home/debian_user/ki-crawler/

# Dann: Nur die folgenden Ordner beibehalten:
# app/, components/, models/, pages/, services/, templates/
# Alle *.py-Dateien außer test_*, debug_*, etc.
```

**Option B: Per Hand (sichere Variante)**

1. Auf Debian VM:
```bash
mkdir -p ~/ki-crawler
cd ~/ki-crawler
```

2. Auf Windows: Kopiere manuell per SFTP-Client (z.B. WinSCP, Filezilla):
   - Quelle: `C:\Users\santinel\Documents\Apps\KI-Crawler\`
   - Ziel: `/home/debian_user/ki-crawler/`

3. Dann auf Debian alle **nicht benötigten Dateien löschen**:
```bash
cd ~/ki-crawler
rm -rf __pycache__ cache output
rm -f test_*.py debug_*.py check_*.py analyze_*.py verify_*.py
rm -f *.log *.docx run_full_crawl.py
```

---

## Phase 3: Docker Build & Run

### 3.1 Image bauen
```bash
cd ~/ki-crawler
docker build -t ki-crawler:latest .
```

**Wartezeit**: ~3-5 Minuten (abhängig von Internet-Geschwindigkeit)

Output sollte enden mit:
```
Successfully tagged ki-crawler:latest
```

### 3.2 Container starten

**Option A: Mit docker-compose (empfohlen)**
```bash
docker-compose up -d
```

**Option B: Mit docker run**
```bash
docker run -d \
  --name ki-crawler \
  -p 8080:8080 \
  -v ~/ki-crawler/output:/app/output \
  -v ~/ki-crawler/cache:/app/cache \
  -v ~/ki-crawler/config.yaml:/app/config.yaml \
  ki-crawler:latest
```

### 3.3 Logs prüfen
```bash
docker-compose logs -f
# oder
docker logs -f ki-crawler
```

Erfolgreiches Startup sieht so aus:
```
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### 3.4 Auf App zugreifen
```
http://debian_vm_ip:8080
```

---

## Phase 4: Persistente Speicherung & Backups

### 4.1 Output-Verzeichnis überprüfen
```bash
ls -la ~/ki-crawler/output/
```

### 4.2 Regelmäßig Backup machen
```bash
# Täglich backup ins Archiv
tar -czf ~/backups/ki-crawler-$(date +%Y%m%d).tar.gz ~/ki-crawler/output/
```

### 4.3 config.yaml anpassen (optional)
```bash
nano ~/ki-crawler/config.yaml
```

Nach Änderungen Container neustarten:
```bash
docker-compose restart
```

---

## Troubleshooting

### Container startet nicht
```bash
# Logs prüfen
docker logs ki-crawler

# Container rekonstruieren
docker-compose down
docker-compose up --build -d
```

### Port 8080 schon in Benutzung
```bash
# Anderer Port in docker-compose.yml:
# Ändere "8080:8080" zu "8888:8080"

docker-compose down
docker-compose up -d
```

### Performance langsam
```bash
# Container-Ressourcen erhöhen (docker-compose.yml):
services:
  ki-crawler:
    # ... andere config ...
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
```

### Playwright-Installation fehlgeschlagen
Ist bereits im Dockerfile enthalten - sollte automatisch funktionieren.

---

## Zusammenfassung der Befehle

```bash
# Setup einmalig:
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo usermod -aG docker $USER && newgrp docker

# KI-Crawler starten:
cd ~/ki-crawler
docker-compose up -d

# Status prüfen:
docker-compose ps
docker logs -f ki-crawler

# Stoppen:
docker-compose down

# Update durchführen:
git pull origin main
docker-compose up --build -d
```

---

## Nächste Schritte

Nach dem Start:
1. ✅ Öffne `http://debian_ip:8080`
2. ✅ Neuer Crawl: Gib URL ein (z.B. `https://www.unibas.ch`)
3. ✅ Output-Dateien: `~/ki-crawler/output/`

Viel Erfolg! 🚀
