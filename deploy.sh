#!/bin/bash

set -e

echo "================================"
echo "KI-Crawler Docker Deployment"
echo "================================"

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funktionen
log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check: Docker installiert?
log_info "Prüfe Docker Installation..."
if ! command -v docker &> /dev/null; then
    log_warn "Docker nicht gefunden. Installiere Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    log_success "Docker installiert"
else
    log_success "Docker vorhanden: $(docker --version)"
fi

# Check: Docker Compose installiert?
log_info "Prüfe Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    log_warn "Docker Compose nicht gefunden. Installiere..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    log_success "Docker Compose installiert"
else
    log_success "Docker Compose vorhanden: $(docker-compose --version)"
fi

# Check: Docker Daemon läuft?
log_info "Starte Docker Daemon..."
if ! docker ps &> /dev/null; then
    log_warn "Docker Daemon läuft nicht. Starte..."
    sudo systemctl start docker
    sleep 2
fi
log_success "Docker läuft"

# Überprüfe: Wir sind im richtigen Verzeichnis?
if [ ! -f "Dockerfile" ]; then
    echo "❌ Fehler: Dockerfile nicht gefunden!"
    echo "Stelle sicher, dass du im KI-Crawler Verzeichnis bist:"
    echo "  cd ~/ki-crawler"
    exit 1
fi
log_success "Im korrekten Verzeichnis"

# Räume auf: Nicht benötigte Dateien löschen
log_info "Räume nicht benötigte Dateien auf..."
rm -rf __pycache__ .pytest_cache .mypy_cache .cache/
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "*~" -delete
log_success "Cleanup abgeschlossen"

# Build Docker Image
log_info "Baue Docker Image..."
docker build -t ki-crawler:latest .
log_success "Docker Image gebaut"

# Erstelle Verzeichnisse
log_info "Erstelle Output/Cache Verzeichnisse..."
mkdir -p output cache
log_success "Verzeichnisse erstellt"

# Starte Container
log_info "Starte Container..."
docker-compose down 2>/dev/null || true
docker-compose up -d
log_success "Container gestartet"

# Warte auf Startup
log_info "Warte auf Startup (10 Sekunden)..."
sleep 10

# Check: Container läuft?
if docker-compose ps | grep -q "Up"; then
    log_success "Container läuft ✓"
else
    log_warn "Container scheint nicht zu laufen!"
    log_info "Logs:"
    docker-compose logs --tail 20
    exit 1
fi

# Zeige Logs
log_info "Letzte 20 Log-Zeilen:"
docker-compose logs --tail 20

# Zusammenfassung
echo ""
echo "================================"
echo "✅ DEPLOYMENT ERFOLGREICH"
echo "================================"
echo ""
echo "🌐 Web-UI verfügbar unter:"
echo "   http://localhost:8080"
echo "   (oder http://$(hostname -I | awk '{print $1}'):8080 von außen)"
echo ""
echo "📁 Output-Verzeichnis: ./output/"
echo "💾 Cache-Verzeichnis: ./cache/"
echo ""
echo "Nützliche Befehle:"
echo "  docker-compose logs -f          # Logs anschauen"
echo "  docker-compose ps               # Status prüfen"
echo "  docker-compose down             # Stoppen"
echo "  docker-compose restart          # Neustarten"
echo ""
echo "Viel Erfolg! 🚀"
