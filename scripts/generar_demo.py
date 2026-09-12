# -*- coding: utf-8 -*-
"""
Genera un set de facturas sinteticas para probar Radar de Cobranza.
Datos ficticios: empresas, montos y fechas inventados.
"""
import csv
import os
import random
from datetime import date, timedelta

random.seed(7)

CLIENTES = [
    ("Constructora Alerce SpA", "76.412.330-5", "pagos@alerce.cl"),
    ("Transportes Vinamar Ltda", "78.990.221-K", "contabilidad@vinamar.cl"),
    ("Agroindustrial Maipo SA", "96.551.740-2", "tesoreria@agromaipo.cl"),
    ("Servicios Electricos Coya", "77.201.559-8", "admin@electricacoya.cl"),
    ("Comercial Delta Norte", "79.334.881-0", "cobranza@deltanorte.cl"),
    ("Minera Andacollo SpA", "76.883.112-4", "cuentas@mineraandacollo.cl"),
    ("Supermercados Buin Ltda", "77.445.223-1", "finanzas@supbuin.cl"),
    ("Retail Sur Global SA", "96.770.114-9", "pagos@retailsurglobal.cl"),
    ("Clínica Los Robles", "78.112.667-3", "administracion@clinrobles.cl"),
    ("Inmobiliaria Pehuen", "76.998.441-7", "gerencia@pehuen.cl"),
    ("Distribuidora Bahia Azul", "79.554.012-6", "cobranzas@bahiaazul.cl"),
    ("Frigorifico Osorno SpA", "77.667.889-2", "pagos@friosorno.cl"),
]

# perfil de pago por cliente: 0 = excelente, 1 = regular, 2 = malo
PERFIL = [0, 1, 2, 0, 2, 1, 0, 2, 1, 0, 1, 2]

# clientes que facturan en dolares (para probar multimoneda)
EN_USD = {"Retail Sur Global SA", "Minera Andacollo SpA"}

HOY = date.today()
MESES = 7
filas = []
folio = 10400

for cliente, rut, email in CLIENTES:
    perfil = PERFIL[CLIENTES.index((cliente, rut, email))]
    n = random.randint(3, 9)
    for _ in range(n):
        emision = HOY - timedelta(days=random.randint(10, 30 * MESES))
        plazo = random.choice([30, 30, 45, 60, 90])
        vencimiento = emision + timedelta(days=plazo)
        moneda = "USD" if cliente in EN_USD else "CLP"
        if moneda == "USD":
            monto = round(random.uniform(4_000, 120_000), 0)
        else:
            monto = round(random.uniform(280_000, 9_800_000), -3)
        folio += random.randint(1, 7)

        antiguedad = (HOY - vencimiento).days
        if perfil == 0:
            p_pago = 0.95 if antiguedad < 15 else 0.75
        elif perfil == 1:
            p_pago = 0.7 if antiguedad < 20 else 0.35
        else:
            p_pago = 0.4 if antiguedad < 10 else 0.08

        pagado = monto if random.random() < p_pago else 0
        if pagado == 0 and random.random() < 0.18:
            pagado = round(monto * random.uniform(0.2, 0.7), 0)

        filas.append({
            "cliente": cliente, "rut": rut, "email": email,
            "numero": f"F-{folio}", "emision": emision.isoformat(),
            "vencimiento": vencimiento.isoformat(), "moneda": moneda,
            "monto": int(monto), "pagado": int(pagado),
        })

filas.sort(key=lambda f: f["vencimiento"])
destino = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "datos")
os.makedirs(destino, exist_ok=True)
ruta = os.path.join(destino, "facturas_demo.csv")
with open(ruta, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["cliente", "rut", "email", "numero",
                                       "emision", "vencimiento", "moneda",
                                       "monto", "pagado"])
    w.writeheader()
    w.writerows(filas)

pendiente_clp = sum((f["monto"] - f["pagado"]) * (950 if f["moneda"] == "USD" else 1)
                     for f in filas)
print(f"{len(filas)} facturas -> {ruta}")
print(f"Saldo pendiente total (a CLP, USD=950): ${pendiente_clp:,.0f}".replace(",", "."))
