#!/usr/bin/env python3
"""Erzeugt die Bilder der Website aus den Quellbildern in src/img-src/ nach src/assets/.

Braucht Pillow (python3 -m pip install pillow). Aufruf: python3 tools/bilder.py

- Bildschirmfotos: zwei Breiten als WebP (402 px für 1x, 804 px für 2x), Qualität 82.
- Open-Graph-Bild je Sprache (1200 × 630, JPEG): Papiergrund, Titel, ein Bildschirm der App.
- apple-touch-icon.png (180 × 180) aus dem Website-Zeichen (ein Sechseck in Petrol, vorläufig).

Die Bildschirmfotos stammen aus der Dokumentation des App-Projekts (nur gelesen, nicht verändert);
welche Datei woher kommt, steht in src/img-src/QUELLEN.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    sys.exit("Pillow fehlt: python3 -m pip install pillow")

ROOT = Path(__file__).resolve().parent.parent
SRC_IMG = ROOT / "src" / "img-src"
OUT = ROOT / "src" / "assets"
CONFIG = json.loads((ROOT / "site.config.json").read_text(encoding="utf-8"))

# Reinform (AppDesign.reinform): Weiß, Schwarz, Grau für Nebentext – keine Rundungen, keine Schatten
WHITE = (255, 255, 255)
INK = (0, 0, 0)
SECONDARY = (92, 92, 92)
ICON_SRC = ROOT / "src" / "icon-src" / "app-icon-1024.png"

WIDTHS = (402, 804)

OG_TEXT = {
    "de": ("Über 500 Strukturformeln", "Wirkstoffe lernen, nachschlagen und wiedererkennen – mit Lernplan und fünf Chemie-Spielen."),
    "en": ("Over 500 structural formulas", "Learn, look up and recognise drug structures – with a study plan and five chemistry games."),
}


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = {
        "sans": ["/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"],
        "sans-bold": ["/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"],
    }[name]
    for path in candidates:
        if Path(path).exists():
            # Helvetica.ttc: Schnitt 1 = Bold
            index = 1 if name == "sans-bold" and path.endswith("Helvetica.ttc") else 0
            return ImageFont.truetype(path, size, index=index)
    return ImageFont.load_default()


def screenshots() -> None:
    for path in sorted(SRC_IMG.glob("*.png")):
        image = Image.open(path).convert("RGB")
        for width in WIDTHS:
            target = OUT / f"{path.stem}-{width}.webp"
            if image.width < width:
                # Kein Hochrechnen: die 2x-Datei bekommt die native Breite der Quelle.
                scaled = image.copy()
            else:
                height = round(image.height * width / image.width)
                scaled = image.resize((width, height), Image.LANCZOS)
            scaled.save(target, "WEBP", quality=82, method=6)
            print(f"  {target.name}: {scaled.width}×{scaled.height}, {target.stat().st_size // 1024} KB")


def formula_image(name: str, width: int) -> Image.Image:
    """Eine Strukturformel aus src/assets (SVG aus den App-Daten) als Bitmap – über die Schnellansicht von macOS
    (qlmanage), ohne zusätzliche Abhängigkeit. Weißer Rand wird abgeschnitten."""
    import subprocess, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        svg = OUT / f"formel-{name}.svg"
        subprocess.run(["qlmanage", "-t", "-s", "1600", "-o", tmp, str(svg)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        image = Image.open(Path(tmp) / f"{svg.name}.png").convert("RGB")
    from PIL import ImageOps
    box = ImageOps.invert(image).getbbox()
    image = image.crop(box)
    return image.resize((width, round(image.height * width / image.width)), Image.LANCZOS)


def og_images() -> None:
    formula = formula_image("atorvastatin", 420)
    icon = Image.open(ICON_SRC).convert("RGB").resize((76, 76), Image.LANCZOS)
    for lang, (title, subtitle) in OG_TEXT.items():
        canvas = Image.new("RGB", (1200, 630), WHITE)
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([0, 0, 1199, 629], outline=INK, width=2)

        # Tafel wie auf der Website: weiße Zeichenfläche mit schwarzer Linie, darauf die Formel
        plate_w, plate_h = 480, formula.height + 80
        px, py = 1200 - plate_w - 70, (630 - plate_h) // 2
        draw.rectangle([px, py, px + plate_w, py + plate_h], fill=WHITE, outline=INK, width=2)
        canvas.paste(formula, (px + (plate_w - formula.width) // 2, py + 40))

        x, y = 80, 96
        canvas.paste(icon, (x, y))
        draw.rectangle([x, y, x + 75, y + 75], outline=INK, width=2)
        draw.text((x + 96, y + 22), CONFIG["app_name"], font=font("sans-bold", 30), fill=INK)
        y += 124
        title_font = font("sans-bold", 60)
        for line in wrap(draw, title, title_font, 600):
            draw.text((x, y), line, font=title_font, fill=INK)
            y += 72
        y += 18
        draw.line([(x, y), (x + 56, y)], fill=INK, width=2)
        y += 30
        sub_font = font("sans", 27)
        for line in wrap(draw, subtitle, sub_font, 560):
            draw.text((x, y), line, font=sub_font, fill=SECONDARY)
            y += 37
        target = OUT / f"og-{lang}.jpg"
        canvas.save(target, "JPEG", quality=88, optimize=True)
        print(f"  {target.name}: {target.stat().st_size // 1024} KB")


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words, lines, line = text.split(), [], ""
    for word in words:
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def touch_icon() -> None:
    """Symbole aus dem App-Symbol: Home-Bildschirm (180), Favicon (48), Marke im Seitenkopf (64 = 32 pt @2x)."""
    icon = Image.open(ICON_SRC).convert("RGB")
    for name, size in (("apple-touch-icon.png", 180), ("favicon-48.png", 48), ("app-icon-64.png", 64)):
        target = OUT / name
        icon.resize((size, size), Image.LANCZOS).save(target, "PNG", optimize=True)
        print(f"  {target.name}")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    if any(SRC_IMG.glob("*.png")):
        print("Bildschirmfotos:")
        screenshots()
    print("Open-Graph-Bilder:")
    og_images()
    print("Symbol:")
    touch_icon()
