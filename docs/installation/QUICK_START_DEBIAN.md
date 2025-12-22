# KI-Crawler Quick Start - Debian Docker

## TL;DR (5 Minuten Setup)

### Schritt 1: Grundlagen vorbereiten
```bash
sudo apt-get update && sudo apt-get install -y curl git

# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Schritt 2: KI-Crawler herunterladen und aufsetzen
```bash
# Entweder clone (wenn Git verfügbar):
git clone https://github.com/YOUR_REPO/ki-crawler.git
cd ki-crawler

# Oder manuell: Dateien per SCP/SFTP kopieren
# Siehe INSTALLATION_DEBIAN_DOCKER.md
```

### Schritt 3: Deploy-Skript ausführen
```bash
chmod +x deploy.sh
./deploy.sh
```

### Schritt 4: Zugreifen
```
Browser: http://DEINE_VM_IP:8080
```

---

## Detailliert

### Was wird installiert?
- ✅ Docker & Docker Compose (Schritt 1)
- ✅ Python 3.11 + Abhängigkeiten (via Docker)
- ✅ BeautifulSoup4, requests, python-docx, etc.
- ✅ LibreOffice (für PDF-Export)
- ✅ Playwright (für JS-Heavy Websites)

### Wo sind meine Daten?
```
~/ki-crawler/
├── output/          # Hier landen alle Crawl-Ergebnisse
├── cache/           # Browser-Cache
├── config.yaml      # Konfiguration
└── Dockerfile       # Docker Blueprint
```

### Befehle nach Setup
```bash
cd ~/ki-crawler

# Logs anschauen
docker-compose logs -f

# Status prüfen
docker-compose ps

# Neustarten
docker-compose restart

# Neu bauen (nach Code-Updates)
docker-compose up --build -d

# Stoppen
docker-compose down
```

### Firewall öffnen (falls nötig)
```bash
sudo ufw allow 8080
sudo ufw enable
```

---

## Wenn etwas schiefgeht

### Container startet nicht?
```bash
docker-compose logs | head -50
```

### Port 8080 belegt?
Ändere in `docker-compose.yml`:
```yaml
ports:
  - "8888:8080"  # Statt 8080:8080
```

### Docker-User-Fehler?
```bash
sudo usermod -aG docker $USER
# Dann abmelden/anmelden oder:
newgrp docker
```

---

## Nächste Schritte

1. Öffne `http://localhost:8080`
2. Starte erste Crawl
3. Warte auf Completion
4. Download Markdown/DOCX/HTML
5. Profit! 🚀

**Vollständige Anleitung**: Siehe `INSTALLATION_DEBIAN_DOCKER.md`

**Troubleshooting**: Siehe `DEPLOYMENT_CHECKLIST.md`
