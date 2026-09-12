# -*- coding: utf-8 -*-
"""Diagnostico: abre el tablero y reporta errores de consola y estado del DOM."""
import sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "file:///C:/Users/joaqu/radar-cobranza/salida/radar.html"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1400, "height": 1700})
    errores, consola = [], []
    pg.on("console", lambda m: consola.append(f"{m.type}: {m.text}"))
    pg.on("pageerror", lambda e: errores.append(str(e)))
    resp_fallidas = []
    pg.on("requestfailed", lambda r: resp_fallidas.append(f"{r.url} -> {r.failure}"))
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(2500)

    print("URL:", URL)
    print("errores de pagina:", errores or "ninguno")
    print("consola:", consola or "vacia")
    print("peticiones fallidas:", resp_fallidas or "ninguna")
    print("Chart definido:", pg.evaluate("typeof Chart !== 'undefined'"))
    if pg.evaluate("typeof Chart !== 'undefined'"):
        print("versión Chart:", pg.evaluate("Chart.version"))
        print("instancias:", pg.evaluate("Object.keys(Chart.instances||{}).length"))
    print("canvas:", pg.evaluate("document.querySelectorAll('canvas').length"))
    print("KPIs:", pg.evaluate("[...document.querySelectorAll('.kpi .v')].map(e=>e.textContent)"))
    print("filas clientes:", pg.evaluate("document.querySelectorAll('#tCli tbody tr').length"))
    print("filas facturas:", pg.evaluate("document.querySelectorAll('#tFac tbody tr').length"))
    print("canvas[0] tamano:", pg.evaluate("(()=>{const c=document.querySelectorAll('canvas')[0];return c?`${c.width}x${c.height}`:'no hay'})()"))
    print("canvas[0] con pixeles:", pg.evaluate(
        "(()=>{const c=document.querySelectorAll('canvas')[0];if(!c)return 'n/a';"
        "const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;"
        "for(let i=3;i<d.length;i+=4){if(d[i]!==0)return true}return false})()"))
    print("aviso multimoneda:", pg.evaluate(
        "(()=>{const e=document.getElementById('nota');"
        "return e && e.style.display!=='none' ? e.textContent : 'no aplica'})()"))
    b.close()
