"""Tiempo de impresión estimado y ajustes recomendados para Bambu Lab A2L con PETG.

Estimación propia, orientativa (±30 %): el tiempo exacto lo calcula Bambu Studio al laminar.
Modelo: volumen impreso = carcasa (paredes, techos y suelos) + relleno al 15 % del resto;
tiempo = volumen / caudal medio + cambios de capa + calentamiento por cama.
"""
from __future__ import annotations

CAPA_MM = 0.20
CAUDAL_MM3_S = 9.0  # caudal medio efectivo PETG (paredes exteriores más lentas)
SEG_POR_CAPA = 3.0  # cambio de capa, desplazamientos, limpieza
CARCASA_MM = 0.6  # grosor medio de carcasa por unidad de superficie
RELLENO = 0.15
PREPARACION_MIN = 6.0  # calentamiento, nivelado y purga por cama

AJUSTES_A2L_PETG = [
    ("Impresora", "Bambu Lab A2L · boquilla 0,4 mm"),
    ("Filamento", "PETG (Bambu PETG HF / Basic o genérico) · cama texturizada PEI"),
    ("Altura de capa", "0,20 mm (0,16 mm para frentes y letras pequeñas)"),
    ("Paredes", "3 perímetros (las paredes de 1,6 mm salen macizas)"),
    ("Capas superiores / inferiores", "4 / 4"),
    ("Relleno", "15 % giroide (macizas y placas)"),
    ("Soportes", "No (todas las piezas salen orientadas para imprimir sin soportes)"),
    ("Borde (brim)", "5 mm solo en piezas altas y estrechas (cuerpos de letras finas)"),
    ("Velocidad", "Perfil estándar de PETG; paredes exteriores lentas para mejor acabado"),
    ("Refrigeración", "Ventilador 30–50 % (PETG); sin ventilador en la primera capa"),
]


def segundos_pieza(malla) -> float:
    v = float(abs(malla.volume))
    a = float(malla.area)
    alto = float(malla.extents[2])
    carcasa = min(v, a * CARCASA_MM)
    impreso = carcasa + (v - carcasa) * RELLENO
    capas = max(1.0, alto / CAPA_MM)
    return impreso / CAUDAL_MM3_S + capas * SEG_POR_CAPA


def segundos_cama(cama) -> float:
    """Piezas de la misma cama comparten capas: los cambios de capa cuentan una vez (la más alta)."""
    if not cama.colocaciones:
        return 0.0
    vol = 0.0
    alto = 0.0
    for col in cama.colocaciones:
        m = col.pieza.malla
        v, a = float(abs(m.volume)), float(m.area)
        carcasa = min(v, a * CARCASA_MM)
        vol += carcasa + (v - carcasa) * RELLENO
        alto = max(alto, float(m.extents[2]))
    capas = max(1.0, alto / CAPA_MM)
    extra = SEG_POR_CAPA * 0.4 * (len(cama.colocaciones) - 1) * capas  # saltos entre piezas
    return vol / CAUDAL_MM3_S + capas * SEG_POR_CAPA + extra + PREPARACION_MIN * 60


def formato(segundos: float) -> str:
    m = int(round(segundos / 60))
    h, m = divmod(m, 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"
