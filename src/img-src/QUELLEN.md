# Bilder der Website

Bildschirmfotos der App sind vorläufig nicht enthalten: Die Oberfläche der App ändert sich noch (Stand 26.10.2026).
Neue Aufnahmen hier als PNG ablegen, ihre Herkunft in dieser Datei festhalten und `python3 tools/bilder.py` laufen
lassen; danach die Bildstellen in `src/content/*` wieder einsetzen.

Die Strukturformeln in `src/assets/formel-*.svg` stammen aus den Daten der App (`Importdaten/Pharmakologie/drug_*.svg`,
RDKit-Zeichnungen aus PubChem-Strukturdaten) und sind für die Website nur einfarbig schwarz (#000000) umgefärbt, wie die App sie im
Design Reinform zeichnet. Das Vorschaubild für Links (`og-*.jpg`) zeigt Atorvastatin auf einer solchen Tafel. Das App-Symbol
(`src/icon-src/app-icon-1024.png`) ist eine Kopie aus `Assets.xcassets/AppIcon.appiconset` des App-Projekts; daraus
entstehen Favicon, Home-Bildschirm-Symbol und die Marke im Seitenkopf.
