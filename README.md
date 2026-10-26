# Website „Wirkstoffe Chemie Trainer“

Statische Produktwebsite der iOS-App „Wirkstoffe Chemie Trainer“ mit Funktionsübersicht, Support, Datenschutzerklärung
und Impressum, auf Deutsch und Englisch. Ausgeliefert über GitHub Pages aus dem Ordner `docs/`.

Die Website setzt keine Cookies, nutzt keine Analyse-Dienste und lädt keine Schriften, Skripte oder Inhalte von
Drittanbietern.

## Aufbau

```
site.config.json        Name, Adresse der Website, Kontaktadresse, Stand der Datenschutzerklärung, Sprachen
build.py                erzeugt docs/ aus src/ (nur Python 3, keine Abhängigkeiten)
tools/bilder.py         erzeugt Vorschaubilder und Symbol (Pillow, macOS-Schnellansicht für SVG)
src/templates/          Seitenrahmen, Sprachweiche, 404
src/content/<sprache>/  Inhalte je Sprache; der Kopfblock jeder Datei nennt key, slug, title, description
src/strings.json        Texte des Seitenrahmens je Sprache
src/css/style.css       Gestaltung
src/assets/             Bilder (Strukturformeln aus den App-Daten, Vorschaubilder)
docs/                   fertige Website – wird bei jedem Build neu erzeugt, nicht von Hand ändern
```

## Ändern und bauen

```bash
python3 build.py
```

Der Build meldet verbliebene Platzhalter `[[…]]`. Solange er welche meldet, nicht veröffentlichen. Nach einer
inhaltlichen Änderung der Datenschutzerklärung `datenschutz_stand` in `site.config.json` auf das Veröffentlichungsdatum
setzen. Vorschaubilder neu erzeugen: `python3 tools/bilder.py`.

Lokale Vorschau – die Seiten liegen unter dem Repository-Pfad:

```bash
mkdir -p /tmp/vorschau && ln -sfn "$PWD/docs" /tmp/vorschau/strukturformeln-website && (cd /tmp/vorschau && python3 -m http.server 8765)
```

## Sprachen

Aktiv sind Deutsch (`/de/`, Standard) und Englisch (`/en/`). Vorbereitet, aber inaktiv: `es-es`, `es-mx`, `pt-pt`,
`pt-br`, `ja`, `ko`. Inaktive Sprachen erscheinen nirgends, auch nicht in hreflang oder der Sitemap. Eine Sprache
aktivieren: Ordner `src/content/<code>/` mit denselben `key`-Seiten anlegen, Block in `src/strings.json` und Text für
das Vorschaubild in `tools/bilder.py` ergänzen, in `site.config.json` auf `"active": true` setzen, bauen.

## Veröffentlichung

GitHub Pages: Branch `main`, Ordner `/docs`. `docs/.nojekyll` lässt GitHub die Dateien unverändert ausliefern.
Adresse: `https://alibenti95.github.io/strukturformeln-website/`. Ein anderer Repository-Name braucht einen anderen
`base_path`, eine eigene Domain `custom_domain` in `site.config.json` – danach neu bauen. Für die eigene Domain erzeugt der
Build `docs/CNAME`.

Suchmaschinen: Unter einer github.io-Projektadresse wird `robots.txt` nicht ausgewertet; die Sitemap
`…/strukturformeln-website/sitemap.xml` in der Google Search Console (URL-Präfix-Property, Bestätigung per HTML-Tag über
`google_site_verification`) einreichen.
