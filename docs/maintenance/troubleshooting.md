# Crawl Troubleshooting Guide

## Problem: Nur ein Teilbereich wird gecrawlt (z.B. nur /methods/)

### Ursache
Der Crawler kann **NUR** Seiten finden, die von der Start-URL aus verlinkt sind!

Wenn du bei `https://docs.pcloud.com/methods/` startest:
- Crawler findet nur Links UNTER `/methods/` 
- Andere Bereiche wie `/api/`, `/guides/` etc. werden NICHT gefunden
- Ergebnis: Nur 22-31 Seiten statt der ganzen Domain

### Lösung 1: Richtige Start-URL wählen

**Statt:**  
❌ `https://docs.pcloud.com/methods/`

**Verwende:**  
✅ `https://docs.pcloud.com` (ohne Pfad)  
✅ `https://docs.pcloud.com/` (mit Slash am Ende)

Der Crawler startet dann auf der Hauptseite und folgt ALLEN Links.

### Lösung 2: Max Pages & Depth erhöhen

Wenn du die ganze Domain crawlen willst:
- **Max Pages**: 500-1000 (Standard: 100)
- **Crawl Depth**: 3-4 (Standard: 2)

Depth 2 bedeutet: Startseite → 1. Ebene → 2. Ebene → STOP

### Lösung 3: URL Patterns verwenden

Wenn du gezielt mehrere Bereiche willst:

**Include Patterns** (nur diese):
```
.*/methods/.*
.*/api/.*
.*/guides/.*
```

**Exclude Patterns** (diese ausschließen):
```
.*/login.*
.*/admin.*
```

## Problem: Filename wird ignoriert

### Debug Schritte

1. Prüfe ob `output_name` im Log erscheint:
   ```
   Using user-specified filename: mein-test
   ```

2. Wenn nicht, prüfe ob das Input-Feld ausgefüllt ist

3. Wenn "documentation" erscheint, ist der Standardwert aktiv

### Häufige Ursachen

- Input-Feld nicht geändert (Standard: "documentation.docx")
- Wert nicht gespeichert (onChange Event nicht gefeuert)
- Config nicht korrekt übergeben

## Beispiel: Ganze pCloud Docs crawlen

```yaml
Start URL: https://docs.pcloud.com
Output Filename: pcloud-complete-docs.docx
Max Pages: 500
Crawl Depth: 3
Strategy: Auto-Detect
```

Ergebnis: Alle Bereiche (methods, protocols, structures, sdks, etc.)

## Navigation Strategy Erklärung

### Auto-Detect (Empfohlen)
1. Versucht Sitemap.xml zu finden
2. Falls nicht vorhanden: Folgt Navigation-Links
3. Findet automatisch Kategorien und Unterseiten

### Sitemap.xml
- Nutzt XML-Sitemap falls vorhanden
- Schnellster Weg alle URLs zu finden
- Nicht alle Sites haben eine

### CSS Selectors
- Nur Links die dem CSS-Selektor entsprechen
- Beispiel: `nav.sidebar a` für Sidebar-Links
- Für sehr spezifische Crawls

### Follow All Links
- Folgt ALLEN Links auf der Seite
- Kann zu sehr vielen Seiten führen
- Vorsicht bei großen Sites!

## Typische Crawl-Größen

| Site-Typ | Pages | Depth | Dauer |
|----------|-------|-------|-------|
| Kleine Docs | 50 | 2 | 30s |
| Mittlere API Docs | 200 | 3 | 2min |
| Große Dokumentation | 500+ | 3-4 | 5-10min |

## Logs interpretieren

Wichtige Log-Zeilen:

```
Building crawl queue from https://docs.pcloud.com/methods/
```
→ Start-URL (hier ist /methods/ das Problem!)

```
Found 6 top-level navigation links
```
→ Kategorien gefunden

```
Queue has 22 detailed pages to crawl
```
→ Anzahl der zu crawlenden Detail-Seiten

```
Parallel crawl: 22/22 pages fetched
```
→ Alle Seiten erfolgreich

```
Crawl complete. Visited 31 pages. Errors: 0
```
→ Gesamt-Ergebnis (31 = 22 Detail + 9 Kategorie-Seiten)
