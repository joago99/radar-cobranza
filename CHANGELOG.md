# Changelog

Formato basado en Keep a Changelog. Versionado semantico.

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
