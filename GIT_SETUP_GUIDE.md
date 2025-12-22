# 🔧 Git Setup Guide - KI-Crawler

## 📊 Status Check

✅ Git installiert (Version 2.47.3)
❌ Git nicht konfiguriert (user.name/email fehlt)
❌ Kein Git Repository initialisiert
❌ Keine SSH Keys vorhanden

---

## 🎯 Setup-Schritte

### Schritt 1: Git Benutzer konfigurieren

**Du musst entscheiden:**
- Welchen **Namen** soll Git für deine Commits verwenden?
- Welche **E-Mail** (sollte mit deinem GitHub Account übereinstimmen)?

```bash
# Ersetze mit deinen echten Daten!
git config --global user.name "Dein Name"
git config --global user.email "deine.email@example.com"

# Verifizieren:
git config --global --list
```

**Empfehlung:** Verwende die gleiche E-Mail wie bei GitHub!

---

### Schritt 2: GitHub Authentication wählen

Du hast **2 Optionen** für GitHub-Authentifizierung:

#### Option A: SSH Keys (Empfohlen) 🔐

**Vorteile:**
- ✅ Sicherer
- ✅ Keine Passwort-Eingabe mehr nötig
- ✅ Standard bei Entwicklern

**Setup:**
```bash
# 1. SSH Key generieren (ED25519 - moderner Standard)
ssh-keygen -t ed25519 -C "deine.email@example.com"

# Drücke Enter für Standard-Pfad: /home/thomas/.ssh/id_ed25519
# Optional: Passphrase eingeben (für extra Sicherheit)

# 2. Public Key anzeigen und kopieren
cat ~/.ssh/id_ed25519.pub

# 3. Zu GitHub hinzufügen:
# → Gehe zu: https://github.com/settings/keys
# → Klicke "New SSH Key"
# → Titel: "WSL-Debian-KI-Crawler"
# → Key: Füge den Inhalt von id_ed25519.pub ein
# → "Add SSH Key"

# 4. Testen
ssh -T git@github.com
# Erwartete Ausgabe: "Hi USERNAME! You've successfully authenticated..."
```

#### Option B: Personal Access Token (PAT) 🎫

**Vorteile:**
- ✅ Einfach einzurichten
- ✅ Funktioniert ohne SSH
- ❌ Muss gespeichert/verwaltet werden

**Setup:**
```bash
# 1. Token erstellen:
# → Gehe zu: https://github.com/settings/tokens
# → "Generate new token (classic)"
# → Scopes wählen: repo (full control)
# → Token kopieren (SOFORT! Wird nur einmal angezeigt!)

# 2. Bei git push verwenden:
# Username: dein-github-username
# Password: ghp_xxxxx... (dein Token)

# 3. Credentials speichern (optional):
git config --global credential.helper store
# Dann beim ersten push: Token eingeben, wird gespeichert
```

**Meine Empfehlung:** SSH Keys (Option A)

---

### Schritt 3: Git Repository initialisieren

```bash
cd /home/thomas/projects/KI-Crawler

# Repository initialisieren
git init

# Branch zu 'main' umbenennen (moderner Standard)
git branch -M main

# .gitignore prüfen (sollte bereits existieren)
cat .gitignore

# Alle Dateien stagen
git add .

# Status prüfen (WICHTIG: venv/ sollte NICHT gelistet sein!)
git status

# Initial Commit
git commit -m "Initial commit: Web Documentation Crawler

- Complete project structure
- Python crawler with BeautifulSoup
- DOCX/PDF generation
- NiceGUI web interface
- Docker support
- Comprehensive documentation"
```

**Wichtig:** Verifiziere mit `git status`, dass `venv/` (338 MB) NICHT committed wird!

---

### Schritt 4: GitHub Repository erstellen

Du hast **2 Optionen:**

#### Option A: Neues Repository auf GitHub erstellen

1. Gehe zu: https://github.com/new
2. **Repository Name:** `KI-Crawler` (oder dein Wunschname)
3. **Beschreibung:** "Intelligent web documentation crawler with DOCX/PDF export"
4. **Visibility:** Private oder Public (deine Wahl)
5. **NICHT** initialisieren mit README, .gitignore, oder License
6. **Create Repository**

#### Option B: Bestehendes Repository verwenden

Wenn du bereits ein Repository hast:
```bash
# Notiere die URL:
# SSH: git@github.com:username/KI-Crawler.git
# HTTPS: https://github.com/username/KI-Crawler.git
```

---

### Schritt 5: Remote hinzufügen und pushen

**Bei SSH (empfohlen):**
```bash
# Remote hinzufügen (ersetze USERNAME!)
git remote add origin git@github.com:USERNAME/KI-Crawler.git

# Push
git push -u origin main

# Bei Fehler "Permission denied":
# → Prüfe SSH Key: ssh -T git@github.com
# → Key zu GitHub hinzugefügt?
```

**Bei HTTPS mit Token:**
```bash
# Remote hinzufügen (ersetze USERNAME!)
git remote add origin https://github.com/USERNAME/KI-Crawler.git

# Push (wird nach Credentials fragen)
git push -u origin main
# Username: dein-github-username
# Password: ghp_xxxxx... (dein Personal Access Token)
```

---

## ✅ Verifizierung

Nach erfolgreichem Push:

```bash
# 1. Remote prüfen
git remote -v

# 2. Branch prüfen
git branch -a

# 3. Letzten Commit anzeigen
git log --oneline -1

# 4. GitHub aufrufen und prüfen
# → https://github.com/USERNAME/KI-Crawler
```

---

## 🔄 Täglicher Workflow (nach Setup)

```bash
# 1. Status prüfen
git status

# 2. Änderungen stagen
git add .
# oder spezifisch:
git add main.py parser.py

# 3. Commit
git commit -m "Beschreibung der Änderungen"

# 4. Push
git push origin main

# 5. Pull (wenn auf anderem Rechner gearbeitet wurde)
git pull origin main
```

---

## 🆘 Troubleshooting

### "Permission denied (publickey)"
```bash
# SSH Key prüfen
ssh -T git@github.com

# Neuen Key generieren falls nötig
ssh-keygen -t ed25519 -C "deine.email@example.com"

# Public Key anzeigen und zu GitHub hinzufügen
cat ~/.ssh/id_ed25519.pub
```

### "Authentication failed" bei HTTPS
```bash
# Stelle sicher, dass du Personal Access Token verwendest
# NICHT dein GitHub-Passwort!

# Token erstellen: https://github.com/settings/tokens
# Scopes: repo (full control)
```

### "The current branch main has no upstream branch"
```bash
# Bei erstem Push:
git push -u origin main

# Danach reicht:
git push
```

### "venv/ wird trotz .gitignore committed"
```bash
# .gitignore prüfen
cat .gitignore | grep venv

# Cache leeren und neu stagen
git rm -r --cached venv/
git add .gitignore
git commit -m "Fix: Remove venv/ from tracking"
```

### Falscher Remote URL
```bash
# Remote ändern
git remote set-url origin git@github.com:USERNAME/REPO.git

# Oder entfernen und neu hinzufügen
git remote remove origin
git remote add origin git@github.com:USERNAME/REPO.git
```

---

## 📚 Nützliche Git Commands

```bash
# Status anzeigen
git status

# Änderungen ansehen
git diff

# Commit History
git log --oneline --graph --all

# Letzten Commit rückgängig (aber Änderungen behalten)
git reset --soft HEAD~1

# Dateien unstagen
git restore --staged filename

# Alle lokalen Änderungen verwerfen
git reset --hard HEAD

# Branch erstellen
git checkout -b feature/neue-funktion

# Branch wechseln
git checkout main

# Branches anzeigen
git branch -a
```

---

## 🎯 Nächste Schritte

**Jetzt:**
1. ❓ **Frage:** Welche E-Mail verwendest du bei GitHub?
2. 🔑 **Entscheide:** SSH Keys oder Personal Access Token?
3. 📝 **Konfiguriere:** Git user.name und user.email
4. 🚀 **Setup:** SSH Keys ODER Token
5. 📦 **GitHub:** Repository erstellen/wählen
6. ⬆️ **Push:** Code hochladen

**Danach:**
- Andere Projekte (SlitProjektHub, etc.) ebenfalls migrieren
- CI/CD Pipeline einrichten (optional)
- Branch Protection Rules (optional)

---

**Fragen? Bereit für die nächsten Schritte?**

Sag mir:
1. Deine GitHub E-Mail
2. SSH Keys oder Token?
3. Neues oder bestehendes Repository?

Dann führe ich dich durch die Befehle! 🚀
