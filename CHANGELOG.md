# Changelog

Formato basado en Keep a Changelog. Versionado semantico.

## [0.3.0] - 2026-09-11

### Cambiado
- Identidad visual sobria: paleta de grises calidos y tonos nude, en reemplazo de los
  acentos azul/amarillo/naranjo/rojo.
- Tipografia: titulos y encabezados de tarjeta en serif del sistema (Georgia /
  Palatino Linotype / Book Antiqua). Los numeros y tablas siguen en sans con cifras
  tabulares, porque las cifras de Georgia son no alineadas y ensucian las columnas.
- Escala de severidad del aging en tonos tierra progresivos: greige, arena, camel,
  terracota y marron profundo. Los pills pasan de forma de capsula a rectangulo suave
  con mayusculas y espaciado.
- Bordes mas rectos (radio 6px en tarjetas, 3px en pills) y mas aire en el encabezado.
- Favicon alineado a la nueva paleta.

### Corregido
- El tramo "+90 dias" generaba la clase CSS `c--90-dias` (guion doble por el signo `+`),
  que no coincidia con ningun selector: el pill quedaba sin fondo y con texto invisible.
  Ahora el nombre de clase se normaliza y se limpian los guiones del borde.
- Contraste de las etiquetas secundarias: el gris de apoyo subio de `#8b8279` a
  `#776d64` para superar 4.5:1 sobre los fondos claros (WCAG AA).

## [0.2.0] - 2026-09-11

### Agregado
- Lectura de XLSX/XLSM con libreria estandar (`zipfile` + XML), sin openpyxl:
  cadenas compartidas, cadenas en linea y conversion de fechas nativas de Excel.
- Soporte multimoneda: columna `moneda` (CLP, USD, EUR, UF), conversion de todos los
  agregados a CLP y aviso en el tablero con las tasas aplicadas.
- Columna `tipo_cambio` por factura y opcion `--tc "USD=962,EUR=1055"` para fijar
  tipos de cambio propios.
- Export a PDF con `--pdf`, usando Chrome o Edge en modo headless (sin dependencias
  de Python).
- Detalle de facturas con columna de moneda y saldo convertido a CLP.
- Demo versionada en `demo/` (tablero, PDF, vista previa).
- Script `scripts/captura.py` para capturar el tablero a PNG.
- Diagnostico ampliado: reporta el aviso de multimoneda.

### Cambiado
- Los agregados (KPIs, aging, ranking) se calculan siempre en CLP; el detalle de
  facturas mantiene la moneda original.
- Formato de la linea de tipos de cambio en consola, sin separador de miles.

## [0.1.0] - 2026-09-11

### Agregado
- Lectura de facturas desde CSV con deteccion de delimitador y alias de columnas.
- Parseo de montos en formato chileno y de fechas en 3 formatos.
- KPIs: por cobrar, vencido, % vencido, DSO, atraso promedio, top deudor.
- Aging de cartera en 5 tramos (corriente, 0-30, 31-60, 61-90, +90).
- Ranking de clientes por deuda vencida.
- Tabla de facturas pendientes con semaforo de atraso y regla de accion sugerida.
- Tablero HTML autocontenido con Chart.js servido localmente (sin CDN).
- Export de recordatorios a CSV y borradores de correo por cliente.
- Generador de datos sinteticos para demo (`scripts/generar_demo.py`).
- Script de diagnostico del tablero via Playwright (`scripts/diagnostico.py`).

### Corregido
- Colision de nombre con el global `window.top` en el script del tablero, que
  impedia el render de los graficos.
