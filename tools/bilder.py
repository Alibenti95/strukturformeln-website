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

PAPER = (244, 240, 232)
SURFACE = (252, 250, 245)
INK = (29, 27, 24)
SECONDARY = (98, 91, 82)
PETROL = (24, 76, 85)
RULE = (212, 201, 182)

WIDTHS = (402, 804)

OG_TEXT = {
    "de": ("Über 500 Strukturformeln", "Wirkstoffe lernen, nachschlagen und wiedererkennen – mit Lernplan und fünf Chemie-Spielen."),
    "en": ("Over 500 structural formulas", "Learn, look up and recognise drug structures – with a study plan and five chemistry games."),
}


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = {
        "serif": ["/System/Library/Fonts/NewYork.ttf", "/System/Library/Fonts/Supplemental/Georgia.ttf"],
        "sans": ["/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"],
    }[name]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
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


def rounded_device(screen: Image.Image, height: int) -> Image.Image:
    """Ein Bildschirmfoto in einem schlichten dunklen Rahmen mit runden Ecken – kein Produktbild."""
    scale = height / screen.height
    screen = screen.resize((round(screen.width * scale), height), Image.LANCZOS)
    border = max(8, round(height * 0.012))
    radius = round(height * 0.085)
    frame = Image.new("RGBA", (screen.width + 2 * border, screen.height + 2 * border), (0, 0, 0, 0))
    mask = Image.new("L", frame.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, frame.width - 1, frame.height - 1], radius=radius, fill=255)
    body = Image.new("RGBA", frame.size, (29, 27, 24, 255))
    frame.paste(body, (0, 0), mask)
    inner_mask = Image.new("L", screen.size, 0)
    ImageDraw.Draw(inner_mask).rounded_rectangle([0, 0, screen.width - 1, screen.height - 1],
                                                 radius=radius - border, fill=255)
    frame.paste(screen, (border, border), inner_mask)
    return frame


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
    formula = formula_image("atorvastatin", 400)
    for lang, (title, subtitle) in OG_TEXT.items():
        canvas = Image.new("RGB", (1200, 630), PAPER)
        draw = ImageDraw.Draw(canvas)
        # feine Linien wie das Raster eines Laborjournals
        for y in range(0, 630, 42):
            draw.line([(0, y), (1200, y)], fill=(236, 230, 219), width=1)
        draw.rectangle([0, 0, 1199, 629], outline=RULE, width=2)

        # Tafel wie auf der Website: weiße Zeichenfläche, Kante, darauf die Formel
        plate_w, plate_h = 460, formula.height + 80
        px, py = 1200 - plate_w - 70, (630 - plate_h) // 2
        draw.rounded_rectangle([px + 4, py + 8, px + plate_w + 4, py + plate_h + 8], radius=22, fill=(226, 219, 205))
        draw.rounded_rectangle([px, py, px + plate_w, py + plate_h], radius=22, fill=(255, 255, 255), outline=(207, 195, 174), width=2)
        canvas.paste(formula, (px + (plate_w - formula.width) // 2, py + 40))

        x, y = 80, 110
        draw.text((x, y), CONFIG["app_name"], font=font("serif", 30), fill=PETROL)
        y += 70
        title_font = font("serif", 64)
        for line in wrap(draw, title, title_font, 660):
            draw.text((x, y), line, font=title_font, fill=INK)
            y += 76
        y += 14
        draw.line([(x, y), (x + 56, y)], fill=RULE, width=2)
        y += 30
        sub_font = font("sans", 28)
        for line in wrap(draw, subtitle, sub_font, 640):
            draw.text((x, y), line, font=sub_font, fill=SECONDARY)
            y += 38
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
    size = 180
    icon = Image.new("RGB", (size, size), PAPER)
    draw = ImageDraw.Draw(icon)
    import math
    cx, cy, r = size / 2, size / 2, size * 0.32
    points = [(cx + r * math.cos(math.radians(60 * i - 90)), cy + r * math.sin(math.radians(60 * i - 90)))
              for i in range(6)]
    draw.polygon(points, outline=PETROL, width=9)
    draw.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=PETROL)
    target = OUT / "apple-touch-icon.png"
    icon.save(target, "PNG", optimize=True)
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
