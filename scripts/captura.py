# -*- coding: utf-8 -*-
"""Captura una imagen completa del tablero generado (para revisar/reportar).

Requiere: pip install playwright  (y Chrome instalado).
Uso: python scripts/captura.py [archivo.html] [salida.png]
"""
import os
import sys

from playwright.sync_api import sync_playwright

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
origen = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "salida", "radar.html")
destino = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RAIZ, "salida", "radar-preview.png")
url = "file:///" + os.path.abspath(origen).replace("\\", "/")

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1420, "height": 1900})
    pg.goto(url, wait_until="load")
    pg.wait_for_timeout(2500)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    pg.screenshot(path=destino, full_page=True)
    b.close()
print("captura ->", destino)
