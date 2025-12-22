# HTML Generierung - Neue Features

## Übersicht der Verbesserungen

Basierend auf der Analyse der generierten `index.html` wurden drei wichtige Verbesserungen implementiert:

---

## 1. 🔄 Intelligente Deduplizierung (SHA256-basiert)

### Problem
- **11x "Weitere Informationen"** - identische Seiten mehrfach in der Navigation
- **4x "Über HERMES"** - komplett identische Inhalte
- Führt zu Verwirrung und aufgeblähter Navigation

### Lösung
```python
def _deduplicate_pages(self, pages: List[Dict]) -> Tuple[List[Dict], Dict[str, List[str]]]:
    """Remove duplicate pages based on content hash"""
```

**Funktionsweise:**
1. Berechnet SHA256-Hash des Seiteninhalts
2. Vergleicht Hash-Werte aller Seiten
3. Behält nur erste Instanz jeder einzigartigen Seite
4. Protokolliert gefundene Duplikate

**Log-Ausgabe:**
```
🔄 Removed 14 duplicate pages
  📋 'Weitere Informationen' had 10 duplicate(s)
  📋 'Über HERMES' had 3 duplicate(s)
```

**Vorteile:**
- Übersichtlichere Navigation
- Schnellere Seite (weniger Daten)
- Keine redundanten Inhalte mehr

---

## 2. 📥 Automatisches Download von Dokumenten

### Problem (Bild 3)
- Links zu externen Dokumenten (`.pdf`, `.docx`, `.xlsx`, etc.)
- Dokumente nicht lokal verfügbar
- Link funktioniert nur mit Internet

**Beispiel:** `rechtsgrundlagenanalyse.docx | 97.56 KB`

### Lösung
```python
async def _process_download_links(self, pages: List[Dict], downloads_dir: Path):
    """Find and download external files, update links"""
```

**Funktionsweise:**
1. Scannt alle Seiten nach Download-Links
2. Erkennt Dateitypen: `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.zip`, etc.
3. Lädt Dateien automatisch in `downloads/` Ordner herunter
4. Aktualisiert Links auf lokale Pfade

**Vorher:**
```html
<a href="https://example.com/docs/rechtsgrundlagenanalyse.docx">
    rechtsgrundlagenanalyse.docx
</a>
```

**Nachher:**
```html
<a href="downloads/rechtsgrundlagenanalyse.docx">
    rechtsgrundlagenanalyse.docx
</a>
```

**Vorteile:**
- Vollständig offline nutzbar
- Alle Dokumente lokal gespeichert
- Keine toten Links bei Server-Änderungen

---

## 3. 🔗 Intelligente Interne Verlinkung

### Problem (Bild 4)
- Querverweise zu anderen Seiten als externe Links
- Navigation zwischen verwandten Inhalten umständlich
- Keine automatische Verlinkung zwischen Seiten

**Beispiel Links:**
- "Projektmanagementplan"
- "Projektstausbericht"
- "Änderungsstatusliste"
- "Projekterfahrungen"

### Lösung
```python
def _link_internal_references(self, pages: List[Dict]):
    """Process internal cross-references and link pages together"""
```

**Funktionsweise:**
1. Erstellt Index aller Seitentitel → IDs
2. Erstellt Index aller URL-Slugs → IDs
3. Findet Links die auf andere Seiten verweisen
4. Konvertiert zu internen JavaScript-Navigation

**Matching-Strategien:**
- **Titel-Match:** Link-Text = Seitentitel
- **Slug-Match:** URL-Pfad enthält Seitennamen
- **Case-insensitive:** Groß-/Kleinschreibung egal

**Vorher:**
```html
<a href="https://example.com/projektmanagementplan.html">
    Projektmanagementplan
</a>
```

**Nachher:**
```html
<a href="#page-15" onclick="showPage('page-15'); return false;">
    Projektmanagementplan
</a>
```

**Vorteile:**
- Sofortige Navigation ohne Seitenneuladung
- Keine externen Requests
- Bessere User Experience

---

## Technische Details

### Hash-Algorithmus
- **SHA256** für Content-Deduplizierung
- Robust gegen kleine Formatierungsänderungen
- Schnelle Vergleiche bei großen Datenmengen

### Download-Verarbeitung
- **Async/Await** für parallele Downloads
- **Timeout:** 30 Sekunden pro Datei
- **Sanitization:** Bereinigt Dateinamen
- **Skip-Logic:** Überspringt bereits heruntergeladene Dateien

### Link-Verarbeitung
- **BeautifulSoup4** für HTML-Parsing
- **Case-insensitive Matching** für Titel
- **URL-Slug Extraktion** für Pfad-basierte Links
- **JavaScript Integration** für Navigation

---

## Verwendung

Die Features sind automatisch aktiviert bei der HTML-Generierung:

```python
html_generator = HTMLGenerator(base_url="https://example.com")
output_path = html_generator.generate(
    pages=crawled_pages,
    output_dir=Path("./output"),
    enhanced_formatting=True
)
```

### Log-Ausgaben

**Deduplizierung:**
```
🔄 Removed 14 duplicate pages
  📋 'Weitere Informationen' had 10 duplicate(s)
  📋 'Über HERMES' had 3 duplicate(s)
```

**Downloads:**
```
📥 Downloaded: rechtsgrundlagenanalyse.docx
📥 Downloaded: projektmanagementplan.pdf
📥 Downloaded: checkliste.xlsx
```

**Interne Links:**
```
🔗 Linked: 'projektmanagementplan' → page-15
🔗 Linked: 'änderungsstatusliste' → page-23
🔗 Linked slug: 'projekterfahrungen' → page-31
```

---

## Ordnerstruktur

```
output/
├── hermes_2025-12-20_14-09-02/
│   ├── index.html                    # Hauptseite mit Navigation
│   ├── assets/
│   │   ├── Main.css                  # Extrahierte CSS
│   │   ├── Hermes.css
│   │   └── style.css
│   └── downloads/                     # NEU: Heruntergeladene Dokumente
│       ├── rechtsgrundlagenanalyse.docx
│       ├── projektmanagementplan.pdf
│       └── checkliste.xlsx
```

---

## Vorteile Zusammengefasst

### Deduplizierung
- ✅ Übersichtliche Navigation
- ✅ Kleinere Dateigröße
- ✅ Keine redundanten Inhalte

### Download-Verarbeitung
- ✅ Vollständig offline nutzbar
- ✅ Alle Dokumente lokal
- ✅ Keine toten Links

### Interne Verlinkung
- ✅ Sofortige Navigation
- ✅ Bessere UX
- ✅ Keine Seitenneuladungen

---

## Konfiguration

### Download-Erweiterungen anpassen
In `html_generator.py` Zeile ~934:
```python
download_extensions = {'.pdf', '.docx', '.xlsx', '.pptx', '.zip', '.doc', '.xls', '.ppt'}
```

### Deduplizierung deaktivieren
In `html_generator.py` Zeile ~88:
```python
# parsed_pages, duplicate_info = self._deduplicate_pages(parsed_pages)
```

### Interne Links deaktivieren
In `html_generator.py` Zeile ~103:
```python
# parsed_pages = self._link_internal_references(parsed_pages)
```

---

## Zukünftige Erweiterungen

Mögliche weitere Verbesserungen:

1. **Smart Merging:** Ähnliche Seiten zusammenführen statt löschen
2. **Download Progress:** UI-Feedback während Downloads
3. **Link Preview:** Tooltip mit Zielseiten-Vorschau
4. **Broken Link Detection:** Warnung bei ungültigen internen Links
5. **External Link Highlighting:** Kennzeichnung externer vs. interner Links
6. **Download Statistics:** Report über heruntergeladene Dateien

---

## Bekannte Einschränkungen

1. **Duplikat-Erkennung:**
   - Basiert auf exakter Content-Übereinstimmung
   - Kleine Unterschiede (z.B. Datum) = unterschiedliche Seiten

2. **Download-Limits:**
   - Keine Größenbeschränkung implementiert
   - Sehr große Dateien können timeout auslösen

3. **Link-Matching:**
   - Nur Text-basiertes Matching
   - Keine semantische Analyse

---

## Changelog

### v2.0 - 2025-12-20
- ✨ NEU: SHA256-basierte Deduplizierung
- ✨ NEU: Automatischer Download von Dokumenten
- ✨ NEU: Intelligente interne Verlinkung
- 🐛 FIX: CSS-Extraktion via Playwright Browser
- 🎨 IMPROVE: Jinja2 Template-System
- 🎨 IMPROVE: Kategorisierte Navigation

### v1.0 - 2025-12-19
- Initial Release
- Basis HTML-Generierung
- CSS-Extraktion (HTTP)
- Einfache Navigation
