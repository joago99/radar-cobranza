# -*- coding: utf-8 -*-
"""Verifica contraste WCAG de una paleta. Sirve cuando no hay acceso a vision.

Compara cada par texto/fondo y avisa cual queda bajo el minimo. Regla practica:
4.5:1 para texto de cuerpo y etiquetas pequenas, 3:1 para texto grande (>= 24px).

Uso: editar la lista PARES y ejecutar `python scripts/contraste.py`.
"""

MIN_CUERPO = 4.5
MIN_GRANDE = 3.0

# (nombre, color de texto, color de fondo, es_texto_grande)
PARES = [
    ("cuerpo / fondo pagina", "#2b2724", "#f6f4f1", False),
    ("cuerpo / tarjeta", "#2b2724", "#fffdfb", False),
    ("KPI valor / tarjeta", "#3d3833", "#fffdfb", False),
    ("etiqueta secundaria / tarjeta", "#776d64", "#fffdfb", False),
    ("KPI alerta / tarjeta", "#7a4331", "#fffdfb", False),
    ("nota / fondo nota", "#6b5330", "#f3ece4", False),
    ("pill corriente", "#5c554d", "#ece7e1", False),
    ("pill 0-30", "#6b5330", "#e8d9c5", False),
    ("pill 31-60", "#6f4b25", "#dcc3a3", False),
    ("pill 61-90", "#41260f", "#c99a72", False),
    ("pill +90", "#fdf8f4", "#8d5a41", False),
]


def luminancia(color):
    """Luminancia relativa segun WCAG 2.x."""
    h = color.lstrip("#")
    canales = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    canales = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
               for c in canales]
    return 0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2]


def contraste(a, b):
    la, lb = luminancia(a), luminancia(b)
    alto, bajo = max(la, lb), min(la, lb)
    return round((alto + 0.05) / (bajo + 0.05), 2)


def main():
    fallas = 0
    print(f"{'par':32} {'ratio':>6}  minimo  estado")
    for nombre, texto, fondo, grande in PARES:
        ratio = contraste(texto, fondo)
        minimo = MIN_GRANDE if grande else MIN_CUERPO
        ok = ratio >= minimo
        fallas += 0 if ok else 1
        print(f"{nombre:32} {ratio:6}  {minimo:6}  {'OK' if ok else 'BAJO'}")
    print()
    if fallas:
        print(f"{fallas} par(es) bajo el minimo: oscurecer el texto o aclarar el fondo.")
    else:
        print("Todos los pares cumplen el minimo de contraste.")


if __name__ == "__main__":
    main()
