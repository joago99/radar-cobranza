# Radar de Cobranza

Convierte un listado de facturas en un tablero de cobranza: cuanto te deben, cuanto
esta vencido, quien te debe y que hacer con cada cliente.

Pensado para gerencia y control de gestion: el dato que ya tienes en un Excel se
transforma en una pantalla que dice donde esta el problema y cual es el proximo paso.

## Que entrega

- **Tablero HTML** (`salida/radar.html`): KPIs, aging de cartera, ranking de deudores
  y detalle de facturas con semaforo de atraso.
- **PDF** (`salida/radar.pdf`, opcional con `--pdf`): el mismo tablero listo para
  circular por correo.
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

Requiere solo Python 3. Sin dependencias externas (ni pandas, ni openpyxl).

```bash
python scripts/generar_demo.py          # crea datos/facturas_demo.csv (sintetico)
python radar.py --input datos/facturas_demo.csv --out salida --titulo "Mi Empresa"
```

Abre `salida/radar.html` en el navegador.

Opciones:

```bash
# Excel en vez de CSV
python radar.py -i cartera.xlsx

# fecha de corte reproducible
python radar.py --hoy 2026-09-11

# tipos de cambio propios para cartera multimoneda
python radar.py --tc "USD=962,EUR=1055,UF=39500"

# exportar tambien a PDF (usa Chrome o Edge del sistema)
python radar.py --pdf
```

## Demo

- Tablero de ejemplo: [`demo/index.html`](demo/index.html)
- Vista previa: [`demo/preview.png`](demo/preview.png)
- PDF de ejemplo: [`demo/radar.pdf`](demo/radar.pdf)

La demo se genera con 72 facturas sinteticas de 12 empresas ficticias, incluidos dos
clientes que facturan en dolares.

## Formato de entrada

CSV (delimitado por coma, punto y coma, tabulacion o pipe) o XLSX/XLSM.
Los nombres de columna se reconocen por alias, sin distinguir mayusculas, tildes ni
espacios:

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
| Moneda | moneda, currency, divisa | No (por defecto CLP) |
| Tipo de cambio | tipo_cambio, tc, cambio | No (por defecto tabla interna) |

- Montos en formato chileno (`1.234.567` o `1.234,56`) o simple (`1234567.50`).
- Fechas `YYYY-MM-DD`, `DD-MM-YYYY`, `DD/MM/YYYY`, o fecha nativa de Excel.
- En XLSX se lee la primera hoja.

```csv
cliente,rut,email,numero,emision,vencimiento,moneda,monto,pagado
Constructora Alerce SpA,76.412.330-5,pagos@alerce.cl,F-10401,2026-05-02,2026-06-01,CLP,4820000,0
```

## Multimoneda

Si la cartera mezcla monedas, cada factura conserva su moneda original en el detalle y
todos los agregados se convierten a CLP. La tasa de cada factura se toma, en orden de
prioridad, de la columna `tipo_cambio`, de `--tc`, o de la tabla interna
(USD 950, EUR 1030, UF 39000). El tablero muestra un aviso con las tasas aplicadas.

## Estructura

```
radar.py                       programa principal
datos/                         archivos de entrada (demo sintetica incluida)
demo/                          salida de ejemplo versionada (tablero, PDF, preview)
scripts/generar_demo.py        genera facturas sinteticas
scripts/captura.py             captura el tablero a PNG (requiere playwright + Chrome)
scripts/diagnostico.py         revisa errores de consola y estado del render
vendor/chart.umd.min.js        Chart.js local (sin CDN, funciona offline)
salida/                        salidas generadas (no versionado)
```

## Como verificar que el tablero esta bien generado

`scripts/diagnostico.py` abre el tablero con Chrome, reporta errores de consola,
cuenta los graficos instanciados y confirma que los canvas tienen pixeles dibujados.
Sirve para no confundir un "no se ve nada" con un problema de datos:

```bash
python scripts/diagnostico.py            # por defecto salida/radar.html
```

Salida esperada: `errores de pagina: ninguno`, `instancias: 2`, `canvas[0] con pixeles: True`.

## Privacidad

Todo corre local. No hay llamadas a servicios externos ni envio de datos a ningun
lado. Chart.js se sirve desde `vendor/` (sin CDN).

## Estado

v0.2 - incluye lectura XLSX, multimoneda y export a PDF. Fuera de alcance por ahora:
envio automatico de correos, conexion directa a ERP/sistema de facturacion,
proyeccion de flujo de caja.

## Licencia

MIT
