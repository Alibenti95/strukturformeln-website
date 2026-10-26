#!/usr/bin/env python3
"""Baut die Website aus src/ nach docs/ (GitHub Pages).

Ohne Abhängigkeiten: Python 3 aus macOS reicht. Aufruf: python3 build.py

Was passiert:
  1. site.config.json lesen (Name, Adresse, Sprachen, Kontakt).
  2. Für jede aktive Sprache jede Seite aus src/content/<sprache>/*.html in die Vorlage
     src/templates/base.html setzen – mit Titel, Beschreibung, Canonical, hreflang, Open Graph.
  3. CSS, Bilder (src/assets, von tools/bilder.py erzeugt) und statische Dateien kopieren.
  4. sitemap.xml, robots.txt, 404.html, Startseite mit Sprachweiche, .nojekyll, ggf. CNAME schreiben.
  5. Verbliebene Platzhalter [[...]] melden – solange welche da sind, nicht veröffentlichen.
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.parse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = ROOT / "docs"

CONFIG = json.loads((ROOT / "site.config.json").read_text(encoding="utf-8"))
STRINGS = json.loads((SRC / "strings.json").read_text(encoding="utf-8"))

PLACEHOLDER = re.compile(r"\[\[([^\]]+)\]\]")
VARIABLE = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")
FRONT_MATTER = re.compile(r"^<!--\s*(.*?)\s*-->\s*", re.DOTALL)


def site_url() -> str:
    domain = CONFIG.get("custom_domain", "").strip()
    if domain:
        return f"https://{domain}"
    return CONFIG["site_url"].rstrip("/")


def base_path() -> str:
    if CONFIG.get("custom_domain", "").strip():
        return ""
    return CONFIG.get("base_path", "").rstrip("/")


def tag(code: str) -> str:
    """Sprach-Tag für hreflang und lang-Attribute (z. B. es-MX); der Schlüssel selbst ist Ordner und URL-Pfad."""
    return CONFIG["languages"][code].get("hreflang", code)


def active_languages() -> list[str]:
    return [code for code, lang in CONFIG["languages"].items() if lang.get("active")]


def read_page(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONT_MATTER.match(text)
    if not match:
        sys.exit(f"Kopfblock fehlt: {path}")
    meta = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    for required in ("key", "slug", "title", "description"):
        if required not in meta:
            sys.exit(f"{path}: '{required}' fehlt im Kopfblock")
    return meta, text[match.end():]


def page_path(lang: str, slug: str) -> str:
    """Der Pfad einer Seite unterhalb der Basis: /de/ oder /de/funktionen/."""
    return f"/{lang}/" if slug == "" else f"/{lang}/{slug}/"


def render(template: str, variables: dict) -> str:
    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name not in variables:
            print(f"  Warnung: unbekannte Variable {{{{{name}}}}}")
            return match.group(0)
        return str(variables[name])
    return VARIABLE.sub(replace, template)


def mark_placeholders(html: str) -> str:
    """[[Text]] wird sichtbar als Platzhalter gesetzt, damit er in der Vorschau auffällt."""
    return PLACEHOLDER.sub(lambda m: f'<mark class="platzhalter">{m.group(1)}</mark>', html)


def main() -> None:
    langs = active_languages()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    template = (SRC / "templates" / "base.html").read_text(encoding="utf-8")
    base = base_path()
    url = site_url()
    today = dt.date.today().isoformat()

    # Seiten einlesen: pages[lang][key] = (meta, body)
    pages: dict[str, dict[str, tuple[dict, str]]] = {}
    for lang in langs:
        pages[lang] = {}
        for path in sorted((SRC / "content" / lang).glob("*.html")):
            meta, body = read_page(path)
            pages[lang][meta["key"]] = (meta, body)

    keys = set()
    for lang in langs:
        keys |= set(pages[lang])

    sitemap_entries: list[str] = []
    placeholders: dict[str, int] = {}

    for lang in langs:
        strings = STRINGS[lang]
        for key in sorted(keys):
            if key not in pages[lang]:
                print(f"  Warnung: Seite '{key}' fehlt in {lang}")
                continue
            meta, body = pages[lang][key]
            path = page_path(lang, meta["slug"])
            canonical = url + base + path

            # hreflang: jede Sprache, in der es die Seite gibt, plus x-default auf dieselbe Seite in der
            # Standardsprache (nicht auf die Sprachweiche, die noindex ist).
            default_lang = CONFIG["default_language"]
            x_default_key = default_lang if key in pages.get(default_lang, {}) else lang
            x_default = url + base + page_path(x_default_key, pages[x_default_key][key][0]["slug"])
            alternates = []
            for other in langs:
                if key in pages[other]:
                    other_path = page_path(other, pages[other][key][0]["slug"])
                    alternates.append(
                        f'<link rel="alternate" hreflang="{tag(other)}" href="{url}{base}{other_path}">'
                    )
            alternates.append(f'<link rel="alternate" hreflang="x-default" href="{x_default}">')

            # Sprachumschalter: dieselbe Seite in den anderen Sprachen (sonst deren Startseite).
            switcher = []
            for other in langs:
                if other == lang:
                    continue
                other_slug = pages[other][key][0]["slug"] if key in pages[other] else ""
                switcher.append(
                    f'<a href="{base}{page_path(other, other_slug)}" lang="{tag(other)}" hreflang="{tag(other)}">'
                    f'{CONFIG["languages"][other]["name"]}</a>'
                )

            variables = {
                "lang": tag(lang),
                "locale": CONFIG["languages"][lang]["locale"],
                "base": base,
                "site_url": url,
                "canonical": canonical,
                "page_title": render(meta["title"], {"app_name": CONFIG["app_name"]}),
                "page_description": render(meta["description"], {"app_name": CONFIG["app_name"]}),
                "og_type": meta.get("og_type", "website"),
                "og_image": f"{url}{base}/assets/og-{lang}.jpg",
                "alternates": "\n    ".join(alternates),
                "language_switcher": " · ".join(switcher),
                "app_name": CONFIG["app_name"],
                "support_email": CONFIG["support_email"],
                "support_mailto": "mailto:" + CONFIG["support_email"] + "?subject="
                                  + urllib.parse.quote(f"Support {CONFIG['app_name']}"),
                "ios_minimum": CONFIG["ios_minimum"],
                "appstore_url": CONFIG["appstore_url"],
                "appstore_state": "ready" if CONFIG["appstore_url"] else "pending",
                "year": str(dt.date.today().year),
                "privacy_date": privacy_date(lang),
                "structured_data": "",
                "body_class": meta.get("body_class", ""),
                "verification": (f'<meta name="google-site-verification" content="{CONFIG["google_site_verification"]}">'
                                 if CONFIG.get("google_site_verification") else ""),
            }
            for page_key, (page_meta, _) in pages[lang].items():
                variables[f"url_{page_key}"] = base + page_path(lang, page_meta["slug"])
            for name, value in strings.items():
                variables[f"s_{name}"] = value

            if key == "home":
                variables["structured_data"] = structured_data(lang, variables)

            html = render(body, variables)
            html = render(template, {**variables, "content": html})
            html = mark_placeholders(html)

            for found in PLACEHOLDER.findall(render(body, variables)):
                number = re.match(r"Angabe (\d+)", found)
                group = int(number.group(1)) if number else 0
                placeholders.setdefault(group, set()).add(f"{lang}/{meta['slug'] or 'index'}")

            target = OUT / path.strip("/") / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(html, encoding="utf-8")

            sitemap_entries.append(sitemap_entry(canonical, today, [
                (other, f"{url}{base}{page_path(other, pages[other][key][0]['slug'])}")
                for other in langs if key in pages[other]
            ], x_default))

    # Statisches: CSS, Bilder, Favicon.
    shutil.copytree(SRC / "css", OUT / "css")
    if (SRC / "assets").exists():
        shutil.copytree(SRC / "assets", OUT / "assets")
    for static in (SRC / "static").glob("*"):
        shutil.copy(static, OUT / static.name)

    # Links zu Impressum und Datenschutz für Sprachweiche und 404 – jede Seite der Website erreicht sie.
    legal_links = " · ".join(
        f'<a href="{base}{page_path(l, pages[l][k][0]["slug"])}" lang="{tag(l)}">{STRINGS[l][s]}</a>'
        for l in langs for k, s in (("legal", "nav_legal"), ("privacy", "nav_privacy")) if k in pages[l])

    # Sprachweiche an der Wurzel, 404, robots, sitemap, .nojekyll, CNAME.
    (OUT / "index.html").write_text(
        render((SRC / "templates" / "root.html").read_text(encoding="utf-8"),
               {"base": base, "site_url": url, "app_name": CONFIG["app_name"],
                "default_language": CONFIG["default_language"],
                "language_links": "\n      ".join(
                    f'<li><a href="{base}/{l}/" lang="{tag(l)}" hreflang="{tag(l)}">{CONFIG["languages"][l]["name"]}</a></li>'
                    for l in langs),
                "language_codes": json.dumps(langs), "legal_links": legal_links}),
        encoding="utf-8")
    (OUT / "404.html").write_text(
        render((SRC / "templates" / "404.html").read_text(encoding="utf-8"),
               {"base": base, "app_name": CONFIG["app_name"],
                "language_links": " · ".join(
                    f'<a href="{base}/{l}/" lang="{tag(l)}">{CONFIG["languages"][l]["name"]}</a>' for l in langs),
                "legal_links": legal_links}),
        encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {url}{base}/sitemap.xml\n", encoding="utf-8")
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(sitemap_entries) + "\n</urlset>\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    domain = CONFIG.get("custom_domain", "").strip()
    if domain:
        (OUT / "CNAME").write_text(domain + "\n", encoding="utf-8")

    print(f"Gebaut: {sum(1 for _ in OUT.rglob('index.html'))} Seiten in {OUT.relative_to(ROOT)}/ "
          f"({', '.join(langs)}), Adresse {url}{base}/")
    if CONFIG.get("app_name_ist_arbeitstitel"):
        print(f"Hinweis: „{CONFIG['app_name']}“ ist ein Arbeitstitel (site.config.json → app_name).")
    if not CONFIG["appstore_url"]:
        print("Hinweis: appstore_url ist leer – die Seiten zeigen „bald im App Store“.")
    if placeholders:
        print("Offene Angaben [[...]] – vor der Veröffentlichung ausfüllen (Fragen: OFFENE_FRAGEN.md):")
        for group, where in sorted(placeholders.items()):
            label = f"Angabe {group}" if group else "ohne Nummer"
            print(f"  {label}: {', '.join(sorted(where))}")
    else:
        print("Keine Platzhalter mehr offen.")


MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
             "October", "November", "December"]


def privacy_date(lang: str) -> str:
    """Stand der Datenschutzerklärung aus site.config.json (datenschutz_stand, JJJJ-MM-TT); leer = offene Angabe 13."""
    value = CONFIG.get("datenschutz_stand", "").strip()
    if not value:
        return "[[Angabe 13: Datum der Veröffentlichung]]" if lang == "de" else "[[Angabe 13: date of publication]]"
    day = dt.date.fromisoformat(value)
    if lang == "de":
        return day.strftime("%d.%m.%Y")
    return f"{day.day} {MONTHS_EN[day.month - 1]} {day.year}"


def sitemap_entry(loc: str, lastmod: str, alternates: list[tuple[str, str]], x_default: str) -> str:
    links = "".join(
        f'\n    <xhtml:link rel="alternate" hreflang="{tag(lang)}" href="{href}"/>' for lang, href in alternates)
    links += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{x_default}"/>'
    return f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{lastmod}</lastmod>{links}\n  </url>"


def structured_data(lang: str, v: dict) -> str:
    """Schema.org für die Startseite: die App und die Website. Keine Bewertungen, kein Preis –
    nur, was belegt ist. Der App-Store-Link kommt dazu, sobald er in der Konfiguration steht."""
    app = {
        "@context": "https://schema.org",
        "@type": "MobileApplication",
        "name": v["app_name"],
        "operatingSystem": f"iOS {v['ios_minimum']}+",
        "applicationCategory": "EducationalApplication",
        "applicationSubCategory": "Medicinal chemistry learning app",
        "inLanguage": ["de", "en", "es", "pt", "ja", "ko"],
        "description": v["page_description"],
        "url": v["canonical"],
        "image": v["og_image"],
    }
    if v["appstore_url"]:
        app["installUrl"] = v["appstore_url"]
        app["downloadUrl"] = v["appstore_url"]
    website = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": v["app_name"],
        "url": f"{v['site_url']}{v['base']}/",
        "inLanguage": lang,
    }
    return "\n".join(
        f'<script type="application/ld+json">{json.dumps(d, ensure_ascii=False)}</script>'
        for d in (app, website))


if __name__ == "__main__":
    main()
