# KI-Crawler: Deployment Überblick

## 📋 Dateien für Deployment

Diese 5 neue Dateien wurden für das Debian-Docker-Deployment erstellt:

| Datei | Zweck |
|-------|-------|
| `Dockerfile` | Blueprint für Docker Image |
| `docker-compose.yml` | Container-Orchestrierung & Volumes |
| `.dockerignore` | Dateien ausschließen von Docker Build |
| `deploy.sh` | Automatisiertes Deployment-Skript für Debian |
| `INSTALLATION_DEBIAN_DOCKER.md` | Detaillierte Anleitung (für Proxmox VM) |
| `QUICK_START_DEBIAN.md` | Schnelle 5-Minuten-Anleitung |
| `DEPLOYMENT_CHECKLIST.md` | Schritt-für-Schritt Checklist |
| `DEPLOYMENT_OVERVIEW.md` | Dieses Dokument |

---

## 🎯 Deployment-Pfade

### Pfad A: Schnellstart (Empfohlen)
**Zeit**: ~10 Minuten
```bash
# 1. Auf Debian VM
git clone <your-repo>
cd ki-crawler
chmod +x deploy.sh
./deploy.sh

# 2. Browser
http://DEBIAN_IP:8080
```

### Pfad B: Manuelles Deployment (Mit Kontrolle)
**Zeit**: ~20 Minuten
```bash
# 1. Manuell durcharbeiten: INSTALLATION_DEBIAN_DOCKER.md
# 2. Dateien per SFTP/SCP kopieren
# 3. docker-compose up -d
```

---

## 📂 Zu kopiende Dateien (Windows → Debian)

### ✅ MUSS kopiert werden:

**Verzeichnisse:**
```
app/
components/
models/
pages/
services/
templates/
```

**Python-Hauptdateien:**
```
main_ui.py              (Web-UI Entry Point)
crawler.py              (Core Crawler)
parser.py               (HTML Parser - FIXED für RAG)
html_generator.py       (HTML Output)
markdown_generator.py   (Markdown Output - NEU!)
docx_generator.py       (DOCX Output)
docx_generator_v2.py    (Alternative DOCX)
pdf_converter.py        (PDF Conversion)
rate_limiter.py
sitemap_parser.py
image_handler.py
api_parser.py
openapi_detector.py
navigation_strategy.py
rendering_strategy.py
syntax_highlighter.py
sidebar_parser.py
template_manager.py
categorizer.py
method_extractor.py
full_pipeline.py
```

**Konfigurationsdateien:**
```
config.yaml
requirements.txt
Dockerfile
docker-compose.yml
.dockerignore
```

### ❌ NICHT kopieren:

```
__pycache__/              (Python Cache)
cache/                    (Browser Cache)
output/                   (Crawl-Results)
*.log                     (Log-Dateien)
test_*.py                 (Tests)
debug_*.py                (Debug-Skripte)
check_*.py                (Check-Skripte)
analyze_*.py              (Analyze-Skripte)
verify_*.py               (Verify-Skripte)
*.docx                    (Alte Dokumente)
*.md (außer README)       (Dokumentation)
webseiten-crawler.docx
```

---

## 🐳 Docker Images & Layers

Der Docker Build erstellt ein Image mit:

```
FROM python:3.11-slim (166 MB)
  ├─ System packages (git, curl, wget, libxml2, etc.)
  ├─ LibreOffice (für PDF-Export) (~300 MB)
  ├─ Python Dependencies (pip install -r requirements.txt)
  └─ Source Code (app/, config.yaml, etc.)

Total Image Size: ~800 MB - 1 GB
```

### Optimierungen:
- Nutzt `slim` Image (nicht full Python)
- Multi-stage Build möglich (für Zukunft)
- Layer-Caching für schnelle Rebuilds

---

## 📊 Deployment Vergleich

| Aspekt | Option: Host Install | Option: Docker |
|--------|----------------------|-----------------|
| Setup-Zeit | 30-60 Min | 5-10 Min |
| Abhängigkeiten | Manuell + Global | Isoliert + Reproducible |
| Python Versionen | Konflikt-Anfällig | Garantiert 3.11 |
| Port-Management | Konfiguration nötig | docker-compose.yml |
| Updates | Apt-get + Pip | Docker rebuild |
| Produktivität | Kompliziert | Professionell |
| Portabilität | VM-spezifisch | Läuft überall |

**Fazit**: Docker ist hier **deutlich überlegen**.

---

## 🔄 Workflow nach Deployment

### Neue Features pushen
```bash
# Windows (Development)
# ... Code ändern ...
git add .
git commit -m "Feature XYZ"
git push origin main

# Debian VM
cd ~/ki-crawler
git pull origin main
docker-compose up --build -d
```

### Konfiguration anpassen
```bash
# Debian VM
nano config.yaml
docker-compose restart
```

### Logs anschauen
```bash
docker-compose logs -f --tail 100
```

---

## 🛡️ Security & Best Practices

### 1. Firewall konfigurieren
```bash
# Nur lokal erlauben:
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp        # SSH
sudo ufw allow 8080/tcp      # KI-Crawler
sudo ufw enable
```

### 2. Reverse Proxy (nginx) - Optional
```bash
# Für https + Authentifizierung
sudo apt-get install nginx
# ... nginx Config ...
```

### 3. Backups
```bash
# Täglich backup
0 3 * * * tar -czf ~/backups/ki-crawler-$(date +\%Y\%m\%d).tar.gz ~/ki-crawler/output/
```

### 4. Resource Limits
```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
```

---

## 📈 Monitoring & Metrics

### CPU/Memory Check
```bash
docker stats ki-crawler
```

### Log Rotation (automatisch)
```yaml
# docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## 🆘 Quick Troubleshooting

| Problem | Lösung |
|---------|--------|
| Container startet nicht | `docker logs ki-crawler` |
| Port 8080 frei? | `netstat -an \| grep 8080` |
| DNS nicht erreichbar | `docker-compose up --build -d` |
| Playwright fehler | `pip install -U playwright` |
| Out of memory | RAM erhöhen oder Crawl-Size reduzieren |

---

## 📚 Dokumentation

- **Anfänger**: Lese `QUICK_START_DEBIAN.md`
- **Detail-Plan**: Lese `INSTALLATION_DEBIAN_DOCKER.md`
- **Checklist**: Nutze `DEPLOYMENT_CHECKLIST.md`
- **Dieser Überblick**: `DEPLOYMENT_OVERVIEW.md`

---

## ✅ Post-Deployment Validierung

```bash
# 1. Container läuft
docker-compose ps
# Output: ki-crawler  ...  Up

# 2. Web-UI erreichbar
curl http://localhost:8080
# Output: HTML Response (nicht error)

# 3. Output-Verzeichnis vorhanden
ls -la ~/ki-crawler/output/
# Output: (leer ok, wird beim Crawl gefüllt)

# 4. Cache-Verzeichnis vorhanden
ls -la ~/ki-crawler/cache/
# Output: (leer ok)

# 5. Test-Crawl durchführen
# - Öffne http://DEBIAN_IP:8080
# - Starte neue Crawl mit kleiner URL
# - Warte auf Completion
# - Prüfe output Verzeichnis
```

---

## 🚀 Production Ready?

Vor Produktivbetrieb:

- [ ] HTTPS/SSL Setup (Nginx Reverse Proxy)
- [ ] Firewall richtig konfiguriert
- [ ] Backup-Strategie implementiert
- [ ] Resource-Limits gesetzt
- [ ] Log-Rotation aktiviert
- [ ] Monitoring aktiviert (optional)
- [ ] Test-Crawl durchgeführt
- [ ] Team trainiert

---

## 📞 Support

Bei Problemen:
1. Checke DEPLOYMENT_CHECKLIST.md
2. Schaue in `docker logs ki-crawler`
3. Lies INSTALLATION_DEBIAN_DOCKER.md
4. Erstelle Issue mit Logs

---

**Deployment erstellt: 2025-12-21**
**Version: 1.0**
**Status: Production Ready** ✅
