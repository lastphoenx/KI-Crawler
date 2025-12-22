#!/bin/bash
# KI-Crawler Setup Script - Automatische Installation
# Erstellt von: lastphoenx
# Datum: 2025-12-22

set -e  # Beende bei Fehlern

echo "🚀 KI-Crawler Setup wird gestartet..."
echo ""

# Prüfe Python Version
echo "📋 Prüfe Python-Installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 ist nicht installiert!"
    echo "   Installiere Python 3.10 oder höher und führe das Script erneut aus."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python $PYTHON_VERSION gefunden"
echo ""

# Prüfe System-Bibliotheken (nur Linux/WSL)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🔧 Prüfe System-Bibliotheken..."
    
    # Prüfe ob apt verfügbar ist
    if command -v apt &> /dev/null; then
        echo "   Installiere benötigte System-Bibliotheken..."
        sudo apt update
        sudo apt install -y libxml2-dev libxslt1-dev python3-dev zlib1g-dev
        echo "✅ System-Bibliotheken installiert"
    else
        echo "⚠️  apt nicht gefunden - überspringe System-Libs (evtl. manuell installieren)"
    fi
    echo ""
fi

# Virtual Environment erstellen
echo "🐍 Erstelle Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual Environment erstellt"
else
    echo "✅ Virtual Environment existiert bereits"
fi
echo ""

# Virtual Environment aktivieren
echo "⚡ Aktiviere Virtual Environment..."
source venv/bin/activate
echo "✅ Virtual Environment aktiv"
echo ""

# Upgrade pip
echo "📦 Aktualisiere pip..."
pip install --upgrade pip --quiet
echo "✅ pip aktualisiert"
echo ""

# Installiere Python-Dependencies
echo "📦 Installiere Python-Pakete (das kann einige Minuten dauern)..."
pip install -r requirements.txt --quiet
echo "✅ Python-Pakete installiert"
echo ""

# Installiere Playwright-Browser
echo "🌐 Installiere Playwright-Browser (Chromium)..."
echo "   Hinweis: Download ist ~280 MB und kann einige Minuten dauern..."
playwright install chromium
echo "✅ Playwright-Browser installiert"
echo ""

# Erstelle .env falls nicht vorhanden
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "🔑 Erstelle .env aus Template..."
        cp .env.example .env
        echo "✅ .env erstellt - bitte anpassen falls nötig"
        echo ""
    fi
fi

# Prüfe config.yaml
if [ -f "config.yaml" ]; then
    echo "✅ config.yaml gefunden"
else
    echo "⚠️  config.yaml nicht gefunden - bitte erstellen!"
fi
echo ""

# Zusammenfassung
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Setup erfolgreich abgeschlossen!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Nächste Schritte:"
echo "   1. Konfiguration anpassen: nano config.yaml"
echo "   2. Optional .env bearbeiten: nano .env"
echo "   3. CLI starten: python main.py"
echo "   4. Web-UI starten: python main_ui.py"
echo ""
echo "💡 Virtual Environment aktivieren:"
echo "   source venv/bin/activate"
echo ""
echo "📚 Weitere Infos: README.md"
echo ""
