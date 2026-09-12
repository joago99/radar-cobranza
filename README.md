# Radar de Cobranza

Convierte un listado de facturas en un tablero de cobranza: cuanto te deben, cuanto
esta vencido, quien te debe y que hacer con cada cliente.

Pensado para gerencia y control de gestion: el dato que ya tienes en un Excel se
transforma en una pantalla que dice donde esta el problema y cual es el proximo paso.

## Que entrega

- **Tablero HTML** (`salida/radar.html`): KPIs, aging de cartera, ranking de deudores
  y detalle de facturas con semaforo de atraso.
- **CSV de recordatorios** (`salida/recordatorios.csv`): accion sugerida por cliente.
- **Borradores de correo** (`salida/correos/`): un texto por cliente moroso, listo para copiar.

## KPIs que calcula

| Indicador | Definicion |
|---|---|
| Por cobrar | Saldo pendiente total (monto - pagado) |
| Vencido | Saldo de facturas con fecha de vencimiento pasada |
| % vencido | Vencido / por cobrar |
| DSO | Dias de venta en cartera: cartera / facturacion diaria del periodo |
| Atraso promedio | Promedio de dias de atraso de las facturas vencidas |
| Top deudor | Cliente con mayor monto vencido |

Aging: Corriente / 0-30 / 31-60 / 61-90 / +90 dias.

Regla de accion sugerida: hasta 30 dias recordatorio por correo, 31-60 llamada de
cobranza, 61-90 llamada gerencial, sobre 90 dias cobranza judicial.

## Uso

Requiere solo Python 3 (sin dependencias externas).

```bash
python scripts/generar_demo.py          # crea datos/facturas_demo.csv (sintetico)
python radar.py --input datos/facturas_demo.csv --out salida --titulo "Mi Empresa"
```

Abre `salida/radar.html` en el navegador.

Opciones:

```bash
python radar.py --hoy 2026-09-11        # fecha de corte (reproducible)
python radar.py --titulo "Cartera Norte"
```

## Formato de entrada

CSV delimitado por coma, punto y coma, tabulacion o pipe. Los nombres de columna se
reconocen por alias (sin distinguir mayusculas, tildes ni espacios):

| Campo | Alias aceptados | Obligatorio |
|---|---|---|
| Cliente | cliente, nombre, razon_social | Si |
| RUT | rut, rut_cliente, documento | No |
| Email | email, correo, mail | No |
| Folio | folio, numero, numero_factura, factura | No |
| Emision | emision, fecha_emision, fecha | No |
| Vencimiento | vencimiento, fecha_vencimiento, vence | Si |
| Monto | monto, total, valor, importe | Si |
| Pagado | pagado, abono, pagos | No |

Montos en formato chileno (`1.234.567` o `1.234,56`) o simple (`1234567.50`).
Fechas `YYYY-MM-DD`, `DD-MM-YYYY` o `DD/MM/YYYY`.

```csv
cliente,rut,email,numero,emision,vencimiento,monto,pagado
Constructora Alerce SpA,76.412.330-5,pagos@alerce.cl,F-10401,2026-05-02,2026-06-01,4820000,0
```

## Privacidad

Todo corre local. No hay llamadas a servicios externos ni envio de datos a ningun
lado. Chart.js se sirve desde `vendor/` (sin CDN).

## Estado

v0.1 - alcance cerrado: aging, ranking, recordatorios. Fuera de alcance por ahora:
multimoneda, envio automatico de correos, conexion directa a ERP.

## Licencia

MIT
