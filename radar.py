# -*- coding: utf-8 -*-
"""
Radar de Cobranza v0.2
Convierte un listado de facturas (CSV o XLSX) en un tablero de cobranza:
- KPIs: total por cobrar, vencido, % vencido, DSO, atraso promedio, top deudor
- Aging de cartera (corriente / 0-30 / 31-60 / 61-90 / +90)
- Ranking de clientes por deuda vencida
- Tabla con semaforo de atraso
- Multimoneda: convierte la cartera a CLP con tipos de cambio configurables
- CSV de recordatorios + texto de correo por cliente
- Export a PDF (si hay Chrome o Edge instalado)

Sin dependencias externas: solo libreria estandar de Python 3 (XLSX incluido).
"""
import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import unicodedata
import zipfile
from datetime import date, datetime, timedelta
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------- utilidades

ALIAS = {
    "cliente": ["cliente", "nombre", "razon_social", "razon social", "nombre_cliente"],
    "rut": ["rut", "rut_cliente", "documento", "id_cliente"],
    "folio": ["folio", "numero", "n_factura", "numero_factura", "factura", "num"],
    "emision": ["emision", "fecha_emision", "fecha emision", "fecha"],
    "vencimiento": ["vencimiento", "fecha_vencimiento", "fecha vencimiento", "vence"],
    "monto": ["monto", "total", "valor", "importe", "monto_total"],
    "pagado": ["pagado", "abono", "pagos", "monto_pagado"],
    "email": ["email", "correo", "e_mail", "mail"],
    "moneda": ["moneda", "currency", "divisa", "mon"],
    "tc": ["tipo_cambio", "tc", "cambio", "valor_cambio"],
}

# Tipos de cambio por defecto a CLP. Se pueden pisar con --tc "USD=980,EUR=1060".
TASAS = {"CLP": 1.0, "USD": 950.0, "EUR": 1030.0, "UF": 39000.0}

SIMBOLO = {"CLP": "$", "USD": "US$", "EUR": "EUR ", "UF": "UF "}


def a_moneda(v):
    """Normaliza el nombre de la moneda."""
    s = norm(v).upper()
    if s in ("", "CLP", "PESO", "PESOS", "P"):
        return "CLP"
    if s in ("USD", "US$", "DOLAR", "DOLARES", "DOLAR_USD"):
        return "USD"
    if s in ("EUR", "EURO", "EUROS"):
        return "EUR"
    if s in ("UF",):
        return "UF"
    return s[:6] or "CLP"


def fmt(monto, moneda="CLP"):
    """Formatea un monto en su moneda."""
    if moneda == "CLP":
        return "$" + f"{round(monto):,}".replace(",", ".")
    return SIMBOLO.get(moneda, moneda + " ") + f"{round(monto):,}".replace(",", ".")


def norm(s):
    """Normaliza un encabezado: minusculas, sin tildes, sin espacios raros."""
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", "_", s)


def mapear_columnas(headers):
    """Devuelve dict campo_logico -> indice de columna real."""
    nh = [norm(h) for h in headers]
    mapa = {}
    for campo, opciones in ALIAS.items():
        for op in opciones:
            if op in nh:
                mapa[campo] = nh.index(op)
                break
    return mapa


def a_numero(v):
    """Parsea montos en formato chileno (1.234.567 / 1.234,56) o simple."""
    if v is None:
        return 0.0
    s = str(v).strip().replace("$", "").replace("\xa0", "").replace(" ", "")
    if s in ("", "-", "nan", "None"):
        return 0.0
    s = s.replace("%", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        entero, _, dec = s.partition(",")
        s = entero.replace(".", "") + "." + dec
    elif re.match(r"^-?\d{1,3}(\.\d{3})+$", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


FORMATOS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%y", "%d/%m/%y")


def a_fecha(v):
    if isinstance(v, date):
        return v
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none"):
        return None
    s = s.split(" ")[0].split("T")[0]
    for f in FORMATOS:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            continue
    # Excel guarda fechas como numero de serie (dias desde 1899-12-30)
    if re.fullmatch(r"\d{5}(\.\d+)?", s):
        try:
            return (datetime(1899, 12, 30) + timedelta(days=float(s))).date()
        except (ValueError, OverflowError):
            return None
    return None


def clp(x):
    return "$" + f"{round(x):,}".replace(",", ".")


# ---------------------------------------------------------------- calculo


def leer_xlsx(path):
    """Lee la primera hoja de un XLSX usando solo la libreria estandar."""
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(path) as z:
        nombres = z.namelist()
        compartidas = []
        if "xl/sharedStrings.xml" in nombres:
            raiz = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in raiz.findall(f"{ns}si"):
                compartidas.append("".join(t.text or "" for t in si.iter(f"{ns}t")))
        hoja = "xl/worksheets/sheet1.xml"
        if hoja not in nombres:
            hojas = sorted(n for n in nombres
                           if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
            if not hojas:
                raise SystemExit(f"El XLSX no tiene hojas legibles: {path}")
            hoja = hojas[0]
        raiz = ET.fromstring(z.read(hoja))

    crudas = {}
    for fila in raiz.iter(f"{ns}row"):
        celdas = {}
        for c in fila.findall(f"{ns}c"):
            ref = c.get("r") or ""
            m = re.match(r"([A-Z]+)", ref)
            if not m:
                continue
            col = 0
            for ch in m.group(1):
                col = col * 26 + (ord(ch) - 64)
            tipo = c.get("t")
            if tipo == "s":
                v = c.find(f"{ns}v")
                idx = int(v.text) if v is not None and v.text else -1
                texto = compartidas[idx] if 0 <= idx < len(compartidas) else ""
            elif tipo == "inlineStr":
                nodo = c.find(f"{ns}is")
                texto = "".join(t.text or "" for t in nodo.iter(f"{ns}t")) if nodo is not None else ""
            else:
                v = c.find(f"{ns}v")
                texto = (v.text or "") if v is not None else ""
            celdas[col - 1] = (texto or "").strip()
        if celdas:
            ancho = max(celdas) + 1
            crudas[int(fila.get("r") or 0)] = [celdas.get(i, "") for i in range(ancho)]
    return [crudas[k] for k in sorted(crudas)]


def leer_filas(path):
    """Devuelve la matriz de celdas desde CSV (cualquier delimitador) o XLSX."""
    if path.lower().endswith((".xlsx", ".xlsm")):
        return leer_xlsx(path)
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        muestra = fh.read(4096)
        fh.seek(0)
        try:
            dialecto = csv.Sniffer().sniff(muestra, delimiters=",;\t|")
        except csv.Error:
            dialecto = csv.excel
        return list(csv.reader(fh, dialecto))


def leer_facturas(path):
    filas = leer_filas(path)
    if not filas:
        raise SystemExit("El archivo no tiene filas.")
    mapa = mapear_columnas(filas[0])
    for obligatorio in ("cliente", "vencimiento", "monto"):
        if obligatorio not in mapa:
            raise SystemExit(
                f"Falta una columna obligatoria: '{obligatorio}'. "
                f"Encontradas: {filas[0]}"
            )
    facturas = []
    for n, fila in enumerate(filas[1:], start=2):
        if not any(c.strip() for c in fila):
            continue

        def val(campo, default=""):
            i = mapa.get(campo)
            if i is None or i >= len(fila):
                return default
            return fila[i]

        monto = a_numero(val("monto"))
        pagado = a_numero(val("pagado"))
        venc = a_fecha(val("vencimiento"))
        if venc is None or monto <= 0:
            print(f"  fila {n} omitida (sin vencimiento o monto invalido)")
            continue
        facturas.append({
            "cliente": (val("cliente") or "SIN NOMBRE").strip(),
            "rut": (val("rut") or "").strip(),
            "email": (val("email") or "").strip(),
            "folio": (val("folio") or str(n)).strip(),
            "emision": a_fecha(val("emision")),
            "vencimiento": venc,
            "monto": monto,
            "pagado": pagado,
            "moneda": a_moneda(val("moneda")),
            "tc": a_numero(val("tc")),
            "saldo": max(monto - pagado, 0.0),
        })
    return facturas


def analizar(facturas, hoy):
    """Devuelve estructura lista para el tablero. Todos los agregados en CLP."""
    for f in facturas:
        f["tasa"] = f.get("tc", 0.0) if f.get("tc", 0.0) > 0 else TASAS.get(f["moneda"], 1.0)
        if f["moneda"] == "CLP":
            f["tasa"] = 1.0
        f["saldo_clp"] = f["saldo"] * f["tasa"]
        f["monto_clp"] = f["monto"] * f["tasa"]
    pendientes = [f for f in facturas if f["saldo_clp"] > 0.5]
    for f in pendientes:
        f["atraso"] = (hoy - f["vencimiento"]).days
        f["corriente"] = f["atraso"] <= 0

    def tramo(d):
        if d <= 0:
            return "Corriente"
        if d <= 30:
            return "0-30 dias"
        if d <= 60:
            return "31-60 dias"
        if d <= 90:
            return "61-90 dias"
        return "+90 dias"

    for f in pendientes:
        f["tramo"] = tramo(f["atraso"])

    vencidas = [f for f in pendientes if f["atraso"] > 0]

    # DSO: cartera / facturacion diaria del periodo observado
    fechas = [f["emision"] for f in facturas if f["emision"]]
    if fechas:
        dias = max((hoy - min(fechas)).days, 1)
    else:
        dias = 365
    facturado = sum(f["monto_clp"] for f in facturas)
    dso = (sum(f["saldo_clp"] for f in pendientes) / (facturado / dias)) if facturado else 0.0

    # ranking por cliente
    por_cliente = {}
    for f in vencidas:
        c = por_cliente.setdefault(f["cliente"], {
            "cliente": f["cliente"], "rut": f["rut"], "email": f["email"],
            "saldo": 0.0, "vencido": 0.0, "facturas": 0,
            "max_atraso": 0, "facturas_detalle": [],
        })
        c["saldo"] += f["saldo_clp"]
        c["vencido"] += f["saldo_clp"]
        c["facturas"] += 1
        c["max_atraso"] = max(c["max_atraso"], f["atraso"])
        c["facturas_detalle"].append(f)

    for f in pendientes:
        if f["atraso"] <= 0:
            c = por_cliente.setdefault(f["cliente"], {
                "cliente": f["cliente"], "rut": f["rut"], "email": f["email"],
                "saldo": 0.0, "vencido": 0.0, "facturas": 0,
                "max_atraso": 0, "facturas_detalle": [],
            })
            c["saldo"] += f["saldo_clp"]
            c["facturas"] += 1

    ranking = sorted(por_cliente.values(), key=lambda c: (-c["vencido"], -c["saldo"]))

    tramos = ["Corriente", "0-30 dias", "31-60 dias", "61-90 dias", "+90 dias"]
    aging = [{"tramo": t, "monto": round(sum(f["saldo_clp"] for f in pendientes if f["tramo"] == t))}
             for t in tramos]

    total = sum(f["saldo_clp"] for f in pendientes)
    vencido = sum(f["saldo_clp"] for f in vencidas)
    atraso_prom = (sum(f["atraso"] for f in vencidas) / len(vencidas)) if vencidas else 0.0

    monedas = sorted({f["moneda"] for f in pendientes})
    return {
        "hoy": hoy.isoformat(),
        "multimoneda": len([m for m in monedas if m != "CLP"]) > 0,
        "kpis": {
            "por_cobrar": round(total),
            "vencido": round(vencido),
            "pct_vencido": round((vencido / total * 100) if total else 0, 1),
            "dso": round(dso),
            "atraso_promedio": round(atraso_prom, 1),
            "top_deudor": ranking[0]["cliente"] if ranking and ranking[0]["vencido"] > 0 else "-",
            "n_clientes": len([c for c in ranking if c["saldo"] > 0]),
            "n_facturas": len(pendientes),
            "monedas": monedas,
            "tasas": {m: TASAS.get(m, 1.0) for m in monedas},
        },
        "aging": aging,
        "ranking": [
            {"cliente": c["cliente"], "rut": c["rut"], "email": c["email"],
             "saldo": round(c["saldo"]), "vencido": round(c["vencido"]),
             "facturas": c["facturas"], "max_atraso": c["max_atraso"]}
            for c in ranking if c["saldo"] > 0
        ],
        "facturas": [
            {"cliente": f["cliente"], "rut": f["rut"], "folio": f["folio"],
             "vencimiento": f["vencimiento"].isoformat(), "atraso": f["atraso"],
             "monto": round(f["monto"]), "pagado": round(f["pagado"]),
             "saldo": round(f["saldo"]), "tramo": f["tramo"],
             "moneda": f["moneda"], "tasa": f["tasa"],
             "saldo_clp": round(f["saldo_clp"])}
            for f in sorted(pendientes, key=lambda x: -x["atraso"])
        ],
    }


# ---------------------------------------------------------------- salidas


def escribir_recordatorios(datos, carpeta):
    ruta = os.path.join(carpeta, "recordatorios.csv")
    with open(ruta, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cliente", "email", "facturas_vencidas", "monto_vencido",
                    "max_atraso_dias", "accion_sugerida"])
        for c in datos["ranking"]:
            if c["vencido"] <= 0:
                continue
            if c["max_atraso"] > 90:
                accion = "Cobranza judicial / carta certificada"
            elif c["max_atraso"] > 60:
                accion = "Llamada gerencial + acuerdo de pago"
            elif c["max_atraso"] > 30:
                accion = "Llamada de cobranza"
            else:
                accion = "Recordatorio por correo"
            w.writerow([c["cliente"], c["email"], c["facturas"], c["vencido"],
                        c["max_atraso"], accion])
    return ruta


PLANTILLA_CORREO = """Estimado(a) {cliente}:

Le escribimos respecto de {n} factura(s) pendiente(s) de pago por un total de {monto}.

Detalle:
{detalle}

La deuda presenta {max_atraso} dia(s) de atraso. Agradeceremos regularizar el pago
o bien responder este correo para acordar una fecha.

Quedamos atentos.

--
Area de Cobranza
"""


def escribir_correos(datos, carpeta):
    destino = os.path.join(carpeta, "correos")
    os.makedirs(destino, exist_ok=True)
    generados = 0
    for c in datos["ranking"]:
        if c["vencido"] <= 0:
            continue
        detalle = "\n".join(
            f"  - Factura {f['folio']} vence {f['vencimiento']}: {fmt(f['saldo'], f['moneda'])} "
            f"({f['atraso']} dias)"
            for f in sorted(
                [x for x in datos["facturas"]
                 if x["cliente"] == c["cliente"] and x["atraso"] > 0],
                key=lambda x: -x["atraso"])
        )
        cuerpo = PLANTILLA_CORREO.format(
            cliente=c["cliente"], n=c["facturas"], monto=clp(c["vencido"]),
            detalle=detalle, max_atraso=c["max_atraso"])
        nombre = re.sub(r"[^A-Za-z0-9]+", "_", c["cliente"])[:40] + ".txt"
        with open(os.path.join(destino, nombre), "w", encoding="utf-8") as fh:
            fh.write(cuerpo)
        generados += 1
    return destino, generados


PLANTILLA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Radar de Cobranza - __TITULO__</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='5' fill='%232b2724'/%3E%3Crect x='6' y='18' width='5' height='8' fill='%239c8f80'/%3E%3Crect x='13.5' y='13' width='5' height='13' fill='%23b3805a'/%3E%3Crect x='21' y='7' width='5' height='19' fill='%238d5a41'/%3E%3C/svg%3E">
<script src="../vendor/chart.umd.min.js"></script>
<style>
  :root{
    --bg:#f6f4f1; --card:#fffdfb; --borde:#e7e1da; --linea:#efeae4;
    --texto:#2b2724; --suave:#776d64; --tinta:#3d3833; --alerta:#7a4331;
    --nude-1:#9c8f80; --nude-2:#c9a883; --nude-3:#b3805a; --nude-4:#8d5a41; --nude-5:#653f2f;
    --serif:Georgia,'Palatino Linotype','Book Antiqua','Times New Roman',serif;
    --sans:'Segoe UI',system-ui,-apple-system,'Helvetica Neue',Arial,sans-serif
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--texto);font-family:var(--sans);
       font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
  header{background:var(--card);border-bottom:1px solid var(--borde);padding:20px 30px;
         display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px}
  h1{margin:0;font-family:var(--serif);font-weight:600;font-size:1.45rem;letter-spacing:.01em}
  header .meta{color:var(--suave);font-size:.8rem;letter-spacing:.02em}
  main{padding:24px 30px;max-width:1400px;margin:0 auto}
  .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:22px}
  .kpi{background:var(--card);border:1px solid var(--borde);border-radius:6px;padding:16px 18px}
  .kpi .l{color:var(--suave);font-size:.72rem;text-transform:uppercase;letter-spacing:.09em}
  .kpi .v{font-size:1.55rem;font-weight:600;margin-top:8px;letter-spacing:-.01em;
          color:var(--tinta);font-variant-numeric:tabular-nums}
  .kpi .s{color:var(--suave);font-size:.76rem;margin-top:3px}
  .kpi.alerta .v{color:var(--alerta)}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:22px}
  @media(max-width:900px){.grid{grid-template-columns:1fr}}
  .card{background:var(--card);border:1px solid var(--borde);border-radius:6px;padding:20px}
  .card h2{margin:0 0 16px;font-family:var(--serif);font-weight:600;font-size:1.02rem;
           letter-spacing:.01em;color:var(--tinta)}
  .chart{height:280px}
  table{width:100%;border-collapse:collapse;font-size:.85rem}
  th{text-align:left;color:var(--suave);font-weight:600;font-size:.7rem;
     text-transform:uppercase;letter-spacing:.09em;padding:9px 10px;border-bottom:1px solid var(--borde)}
  td{padding:10px;border-bottom:1px solid var(--linea);font-variant-numeric:tabular-nums}
  tr:hover td{background:#faf7f4}
  .num{text-align:right}
  .pill{display:inline-block;padding:3px 8px;border-radius:3px;font-size:.7rem;font-weight:600;
        letter-spacing:.05em;text-transform:uppercase}
  .c-corriente{background:#ece7e1;color:#5c554d}
  .c-0-30-dias{background:#e8d9c5;color:#6b5330}
  .c-31-60-dias{background:#dcc3a3;color:#6f4b25}
  .c-61-90-dias{background:#c99a72;color:#41260f}
  .c-90-dias{background:#8d5a41;color:#fdf8f4}
  .doc{color:var(--suave);font-size:.76rem;margin-top:6px;letter-spacing:.01em}
  .nota{background:#f3ece4;border:1px solid #e3d5c6;color:#6b5330;border-radius:6px;
        padding:11px 15px;font-size:.82rem;margin-bottom:20px}
  footer{padding:18px 30px;color:var(--suave);font-size:.76rem;text-align:center;
         letter-spacing:.02em;border-top:1px solid var(--borde);margin-top:26px}
</style>
</head>
<body>
<header>
  <h1>Radar de Cobranza</h1>
  <div class="meta">Corte al __FECHA__ &middot; __NFACT__ facturas pendientes &middot; __NCLI__ clientes</div>
</header>
<main>
  <section class="kpis" id="kpis"></section>
  <div id="nota" class="nota" style="display:none"></div>
  <section class="grid">
    <div class="card"><h2>Aging de cartera</h2><div class="chart"><canvas id="cAging"></canvas></div></div>
    <div class="card"><h2>Top deudores (vencido)</h2><div class="chart"><canvas id="cTop"></canvas></div></div>
  </section>
  <div class="card" style="margin-bottom:22px">
    <h2>Clientes por deuda</h2>
    <table id="tCli">
      <thead><tr><th>Cliente</th><th>RUT</th><th class="num">Facturas</th>
      <th class="num">Saldo</th><th class="num">Vencido</th><th class="num">Atraso max.</th>
      <th>Accion</th></tr></thead><tbody></tbody>
    </table>
  </div>
  <div class="card">
    <h2>Facturas pendientes</h2>
    <table id="tFac">
      <thead><tr><th>Cliente</th><th>Factura</th><th>Vencimiento</th>
      <th class="num">Atraso</th><th>Tramo</th><th>Mon.</th><th class="num">Monto</th>
      <th class="num">Saldo</th><th class="num">Saldo CLP</th></tr></thead><tbody></tbody>
    </table>
    <div class="doc">Atraso en dias corridos respecto de la fecha de vencimiento. Saldo = monto - pagado.</div>
  </div>
</main>
<footer>Generado por Radar de Cobranza v0.1 &middot; datos locales, sin servicios externos</footer>
<script>
const D = __DATA__;
const clp = n => '$' + n.toLocaleString('es-CL');
const fmt = (n,m) => m === 'CLP' ? clp(n)
  : (m === 'USD' ? 'US$' : m + ' ') + n.toLocaleString('es-CL');
// Ojo: el '+' de "+90 dias" genera guion doble si no se limpia el borde
const clase = t => 'c-' + t.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'');

// Nota de multimoneda
if (D.multimoneda) {
  const t = D.kpis.tasas;
  const pares = Object.keys(t).filter(m=>m!=='CLP').map(m=>m+'='+t[m].toLocaleString('es-CL')).join('  ');
  const el = document.getElementById('nota');
  el.style.display = 'block';
  el.innerHTML = 'Cartera en varias monedas (' + D.kpis.monedas.join(', ') +
    '). Los totales estan convertidos a CLP con: ' + pares +
    ' por unidad. Ajustable con la opcion --tc.';
}

// KPIs
const k = D.kpis;
document.getElementById('kpis').innerHTML = [
  {l:'Por cobrar', v:clp(k.por_cobrar), s:'saldo pendiente total'},
  {l:'Vencido', v:clp(k.vencido), s:k.pct_vencido+'% de la cartera', a:k.pct_vencido>30},
  {l:'DSO', v:k.dso+' dias', s:'dias de venta en cartera'},
  {l:'Atraso promedio', v:k.atraso_promedio+' dias', s:'solo facturas vencidas', a:k.atraso_promedio>30},
  {l:'Top deudor', v:k.top_deudor, s:'mayor monto vencido'}
].map(x=>`<div class="kpi${x.a?' alerta':''}"><div class="l">${x.l}</div>
  <div class="v">${x.v}</div><div class="s">${x.s}</div></div>`).join('');

// Aging
new Chart(document.getElementById('cAging'), {
  type:'bar',
  data:{ labels:D.aging.map(a=>a.tramo),
    datasets:[{ data:D.aging.map(a=>a.monto), backgroundColor:D.aging.map((a,i)=>
      ['#9c8f80','#c9a883','#b3805a','#8d5a41','#653f2f'][i]), borderRadius:3, maxBarThickness:70 }]},
  options:{ responsive:true, maintainAspectRatio:false,
    plugins:{ legend:{display:false},
      tooltip:{callbacks:{label:c=>clp(c.parsed.y)}} },
    scales:{ y:{beginAtZero:true, ticks:{callback:v=>(v/1000000).toFixed(1)+' M', color:'#776d64'},
      grid:{color:'#efeae4'}}, x:{grid:{display:false}, ticks:{color:'#776d64'}} } }
});

// Top deudores (ojo: NO usar 'top' como nombre de variable: colisiona con window.top)
const topDeu = D.ranking.filter(c=>c.vencido>0).slice(0,10);
new Chart(document.getElementById('cTop'), {
  type:'bar',
  data:{ labels:topDeu.map(c=>c.cliente.length>22?c.cliente.slice(0,21)+'...':c.cliente),
    datasets:[{ data:topDeu.map(c=>c.vencido), backgroundColor:'#8d5a41',
      borderRadius:3, maxBarThickness:26 }]},
  options:{ indexAxis:'y', responsive:true, maintainAspectRatio:false,
    plugins:{ legend:{display:false}, tooltip:{callbacks:{label:c=>clp(c.parsed.x)}} },
    scales:{ x:{beginAtZero:true, ticks:{callback:v=>(v/1000000).toFixed(1)+' M', color:'#776d64'},
      grid:{color:'#efeae4'}}, y:{grid:{display:false}, ticks:{color:'#776d64'}} } }
});

// Tabla clientes
const accion = c => c.max_atraso>90 ? 'Cobranza judicial'
  : c.max_atraso>60 ? 'Llamada gerencial'
  : c.max_atraso>30 ? 'Llamada de cobranza'
  : c.vencido>0 ? 'Recordatorio por correo' : '-';
document.querySelector('#tCli tbody').innerHTML = D.ranking.map(c=>
  `<tr><td>${c.cliente}${c.email?'<div class="doc">'+c.email+'</div>':''}</td>
   <td>${c.rut||'-'}</td><td class="num">${c.facturas}</td>
   <td class="num">${clp(c.saldo)}</td>
   <td class="num">${c.vencido?clp(c.vencido):'-'}</td>
   <td class="num">${c.max_atraso>0?c.max_atraso+' d':'-'}</td>
   <td>${accion(c)}</td></tr>`).join('');

// Tabla facturas
document.querySelector('#tFac tbody').innerHTML = D.facturas.map(f=>
  `<tr><td>${f.cliente}</td><td>${f.folio}</td><td>${f.vencimiento}</td>
   <td class="num">${f.atraso<=0?'-':f.atraso}</td>
   <td><span class="pill ${clase(f.tramo)}">${f.tramo}</span></td>
   <td>${f.moneda}</td>
   <td class="num">${fmt(f.monto, f.moneda)}</td>
   <td class="num">${fmt(f.saldo, f.moneda)}</td>
   <td class="num">${D.multimoneda ? clp(f.saldo_clp) : '-'}</td></tr>`).join('');
</script>
</body>
</html>
"""


def escribir_dashboard(datos, carpeta, titulo):
    html = (PLANTILLA_HTML
            .replace("__DATA__", json.dumps(datos, ensure_ascii=False))
            .replace("__FECHA__", datos["hoy"])
            .replace("__TITULO__", titulo)
            .replace("__NFACT__", str(datos["kpis"]["n_facturas"]))
            .replace("__NCLI__", str(datos["kpis"]["n_clientes"])))
    ruta = os.path.join(carpeta, "radar.html")
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(html)
    return ruta


def exportar_pdf(html_path, carpeta):
    """Exporta el tablero a PDF usando Chrome/Edge en modo headless.

    No agrega dependencias de Python: reutiliza el navegador ya instalado.
    """
    candidatos = [
        os.environ.get("CHROME_PATH"),
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
    ]
    exe = next((c for c in candidatos if c and os.path.exists(c)), None)
    if not exe:
        print("  PDF: no encontre Chrome ni Edge en el sistema.")
        print("       Alternativa: abre el tablero y usa Imprimir > Guardar como PDF.")
        return None
    destino = os.path.abspath(os.path.join(carpeta, "radar.pdf"))
    url = "file:///" + os.path.abspath(html_path).replace("\\", "/")
    cmd = [exe, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
           "--virtual-time-budget=6000", f"--print-to-pdf={destino}", url]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=180)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
        print(f"  PDF: fallo la exportacion ({type(e).__name__})")
        return None
    if os.path.exists(destino) and os.path.getsize(destino) > 0:
        return destino
    print("  PDF: el navegador no genero el archivo")
    return None


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description="Radar de Cobranza v0.2")
    ap.add_argument("--input", "-i", default="datos/facturas_demo.csv",
                    help="CSV o XLSX de facturas")
    ap.add_argument("--out", "-o", default="salida", help="carpeta de salida")
    ap.add_argument("--hoy", help="fecha de corte YYYY-MM-DD (por defecto hoy)")
    ap.add_argument("--titulo", default="Cartera", help="nombre de la cartera/empresa")
    ap.add_argument("--tc", help='tipos de cambio a CLP, ej: "USD=980,EUR=1060,UF=39500"')
    ap.add_argument("--pdf", action="store_true", help="exportar tambien el tablero a PDF")
    args = ap.parse_args()

    if args.tc:
        for par in args.tc.split(","):
            if "=" in par:
                moneda, valor = par.split("=", 1)
                TASAS[a_moneda(moneda)] = a_numero(valor)
        print("Tipos de cambio:", ", ".join(f"{m}={v:g}" for m, v in TASAS.items()))

    hoy = a_fecha(args.hoy) if args.hoy else date.today()
    os.makedirs(args.out, exist_ok=True)

    print(f"Leyendo {args.input}")
    facturas = leer_facturas(args.input)
    print(f"  {len(facturas)} facturas leidas")
    datos = analizar(facturas, hoy)

    r1 = escribir_dashboard(datos, args.out, args.titulo)
    r2 = escribir_recordatorios(datos, args.out)
    carpeta_correos, n = escribir_correos(datos, args.out)

    k = datos["kpis"]
    print("\n--- RESUMEN ---")
    print(f"  Por cobrar      : {clp(k['por_cobrar'])}")
    print(f"  Vencido         : {clp(k['vencido'])} ({k['pct_vencido']}%)")
    print(f"  DSO             : {k['dso']} dias")
    print(f"  Atraso promedio : {k['atraso_promedio']} dias")
    print(f"  Top deudor      : {k['top_deudor']}")
    print("\n--- ARCHIVOS ---")
    print(f"  Tablero   : {r1}")
    print(f"  Recordatorios: {r2}")
    print(f"  Correos   : {carpeta_correos} ({n} borradores)")
    if args.pdf:
        pdf = exportar_pdf(r1, args.out)
        if pdf:
            print(f"  PDF       : {pdf}")


if __name__ == "__main__":
    main()
