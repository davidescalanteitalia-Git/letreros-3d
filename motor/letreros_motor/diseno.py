"""Parámetros de un letrero, con rangos y validación cruzada.

Todas las medidas en milímetros. Los valores por defecto son hipótesis de
partida para PETG con boquilla 0,4 mm en Bambu Lab A2L; se afinan con la
probeta de holguras (`python -m letreros_motor probeta`).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace

from .errores import ErrorEntrada
from .fuentes import FUENTE_POR_DEFECTO

ESTRUCTURAS = {
    "maciza": "Letra corpórea maciza (sin luz).",
    "caja": "Caja hueca con fondo y frente abierto (neón, acrílico pegado o decorativa).",
    "frontal": "Frontal iluminada: cuerpo con fondo + frente impreso translúcido que encaja a presión.",
    "halo": "Retroiluminada (halo): frente cerrado, trasera abierta y separadores para tornillo a pared.",
}

BOQUILLA_MM = 0.4
# Bambu Lab A2L: 330 × 320 × 325 mm nominales, margen hipotético de 5 mm por lado en XY.
CAMA_A2L_MM = (320.0, 310.0, 325.0)
DENSIDAD_PETG = 1.27  # g/cm³


@dataclass(frozen=True)
class Diseno:
    texto: str
    estructura: str = "frontal"
    altura: float = 120.0          # altura de la MAYÚSCULA
    profundidad: float = 40.0      # grosor total del letrero montado (eje Z)
    pared: float = 1.6             # lateral de la letra (4 líneas de 0,4)
    frente: float = 2.0            # grosor del frente (frontal/halo)
    fondo: float = 2.0             # grosor del fondo (caja/frontal)
    holgura: float = 0.25          # juego entre faldón del frente y pared interior
    encaje: float = 4.0            # altura del faldón que entra en el cuerpo
    pared_encaje: float = 1.2      # grosor del faldón
    espaciado: float = 0.0         # separación extra entre letras (mm reales)
    comp_xy: float = 0.0           # compensación XY: se resta del contorno exterior
    tira_led: float | None = None  # ancho de la tira LED; None = 8 mm en frontal/halo, 0 = sin comprobar
    w_por_metro: float = 0.0       # consumo de la tira (W/m) si se conoce
    cable: float = 6.0             # Ø agujero de cable en el fondo (0 = sin agujero)
    drenaje: bool = False          # agujero Ø3 en la parte baja del fondo (exterior)
    separacion: float = 20.0       # halo: distancia del letrero a la pared
    tornillo: float = 3.2          # halo: Ø del agujero del separador
    fuente: str = FUENTE_POR_DEFECTO
    tolerancia: float = 0.05       # desviación máx. de las curvas
    cama: tuple[float, float, float] = field(default=CAMA_A2L_MM)

    @property
    def ancho_tira(self) -> float:
        if self.tira_led is None:
            return 8.0 if self.estructura in ("frontal", "halo") else 0.0
        return self.tira_led

    def como_dict(self) -> dict:
        d = asdict(self)
        d["tira_led"] = self.ancho_tira
        d["cama"] = list(self.cama)
        return d


_RANGOS = {
    "altura": (20, 1000),
    "profundidad": (5, 250),
    "pared": (0.8, 6),
    "frente": (0.8, 6),
    "fondo": (0.8, 6),
    "holgura": (0, 1),
    "encaje": (1, 15),
    "pared_encaje": (0.8, 4),
    "espaciado": (-20, 200),
    "comp_xy": (0, 0.5),
    "w_por_metro": (0, 50),
    "separacion": (5, 80),
    "tornillo": (2, 6),
    "tolerancia": (0.005, 0.5),
}

_NOMBRES = {
    "altura": "Altura de mayúscula", "profundidad": "Profundidad", "pared": "Pared",
    "frente": "Frente", "fondo": "Fondo", "holgura": "Holgura", "encaje": "Encaje",
    "pared_encaje": "Pared del faldón", "espaciado": "Espaciado", "comp_xy": "Compensación XY",
    "w_por_metro": "Consumo W/m", "separacion": "Separación a pared", "tornillo": "Ø tornillo",
    "tolerancia": "Tolerancia de curvas",
}


def _num(nombre: str, valor) -> float:
    try:
        v = float(valor)
    except (TypeError, ValueError):
        raise ErrorEntrada(f"{_NOMBRES.get(nombre, nombre)} debe ser un número en mm.") from None
    if not math.isfinite(v):
        raise ErrorEntrada(f"{_NOMBRES.get(nombre, nombre)} no es un número válido.")
    return v


def validar(d: Diseno) -> tuple[Diseno, list[str]]:
    """Devuelve el diseño normalizado y la lista de avisos. Lanza ErrorEntrada si es imposible."""
    if d.estructura not in ESTRUCTURAS:
        raise ErrorEntrada(f"Estructura '{d.estructura}' desconocida. Opciones: {', '.join(ESTRUCTURAS)}.")
    cambios = {}
    for campo, (mn, mx) in _RANGOS.items():
        v = _num(campo, getattr(d, campo))
        if not mn <= v <= mx:
            raise ErrorEntrada(
                f"{_NOMBRES[campo]} debe estar entre {mn:g} y {mx:g} mm (recibido {getattr(d, campo)})."
            )
        cambios[campo] = v
    tira = d.tira_led if d.tira_led is None else _num("tira_led", d.tira_led)
    if tira is not None and tira != 0 and not 3 <= tira <= 20:
        raise ErrorEntrada("Ancho de tira LED entre 3 y 20 mm (o 0 para no comprobar).")
    cable = _num("cable", d.cable)
    if cable != 0 and not 2 <= cable <= 15:
        raise ErrorEntrada("Ø del agujero de cable entre 2 y 15 mm (o 0 para no hacerlo).")
    d = replace(d, tira_led=tira, cable=cable, drenaje=bool(d.drenaje), **cambios)

    p, avisos = d.profundidad, []
    if d.estructura == "frontal":
        minimo = d.fondo + d.frente + d.encaje + 2
        if p < minimo:
            raise ErrorEntrada(
                f"Profundidad {p:g} mm insuficiente para frontal: fondo {d.fondo:g} + frente {d.frente:g} "
                f"+ encaje {d.encaje:g} + 2 mm libres = {minimo:g} mm mínimo."
            )
        if p - d.fondo - d.frente < 15:
            avisos.append("Menos de 15 mm entre fondo y frente: la luz puede verse a puntos; usa tira COB o más profundidad.")
    elif d.estructura == "caja" and p < d.fondo + 2:
        raise ErrorEntrada(f"Profundidad {p:g} mm insuficiente para caja con fondo {d.fondo:g} mm.")
    elif d.estructura == "halo" and p < d.frente + 5:
        raise ErrorEntrada(f"Profundidad {p:g} mm insuficiente para halo con frente {d.frente:g} mm.")

    if d.estructura != "maciza":
        lineas = d.pared / BOQUILLA_MM
        if abs(lineas - round(lineas)) > 0.05:
            avisos.append(
                f"Pared {d.pared:g} mm no es múltiplo de la boquilla {BOQUILLA_MM} mm: "
                "el laminador puede dejar huecos. Recomendado 1,2 · 1,6 · 2,0."
            )
    if d.estructura == "frontal" and d.pared_encaje < 2 * BOQUILLA_MM:
        avisos.append("Faldón de menos de 2 líneas de boquilla: puede romperse al encajar.")
    cx, cy, cz = d.cama
    if not (cx > 0 and cy > 0 and cz > 0):
        raise ErrorEntrada("La cama debe tener medidas positivas.")
    alto_pieza = p + (d.separacion if d.estructura == "halo" else 0)
    if alto_pieza > cz:
        raise ErrorEntrada(f"La pieza mide {alto_pieza:g} mm de alto y la cama admite {cz:g} mm en Z.")
    return d, avisos
