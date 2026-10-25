"""División de una pieza que no cabe en la cama.

Diseño propio de Letreros 3D Studio:
- Solo cortes verticales (perpendiculares al texto), situados donde la sección
  de material es más corta, evitando astillas (< 6 mm) y los puntos donde van
  el agujero de cable o los separadores.
- Macizas y placas: cola de milano en cada tramo cortado (macho en la parte
  izquierda; la hembra se agranda con la holgura).
- Huecas: corte recto de cuerpo y frente + placa de empalme interior que se
  pega cruzando la junta (no se ve desde fuera y alinea las dos partes).
"""
from __future__ import annotations

import math
import string
from dataclasses import dataclass

from shapely.geometry import LineString, MultiPolygon, Polygon, box
from shapely.ops import unary_union

from .errores import ErrorEntrada
from .geometria import multipoligono, poligonos

MARGEN_CAMA = 2.0
ASTILLA = 6.0
EVITAR = 10.0  # mm alrededor de cable/separadores
COLA_PROF = 8.0  # profundidad de la cola de milano
EMPALME_ANCHO = 40.0  # ancho total de la placa de empalme (20 mm a cada lado)


@dataclass
class Plan:
    cortes: list[float]
    regiones: list[Polygon]  # una por parte, en orden de izquierda a derecha
    regiones_hembra: list[Polygon]  # misma región con la holgura aplicada a las colas ajenas
    nombres: list[str]


def _cruces(forma: MultiPolygon, x: float) -> list[float]:
    miny, maxy = forma.bounds[1] - 1, forma.bounds[3] + 1
    inter = forma.intersection(LineString([(x, miny), (x, maxy)]))
    return [g.length for g in getattr(inter, "geoms", [inter]) if not g.is_empty and g.length > 1e-6]


def _intervalos(forma: MultiPolygon, x: float) -> list[tuple[float, float]]:
    miny, maxy = forma.bounds[1] - 1, forma.bounds[3] + 1
    inter = forma.intersection(LineString([(x, miny), (x, maxy)]))
    res = []
    for g in getattr(inter, "geoms", [inter]):
        if g.is_empty or g.length < 1e-6:
            continue
        ys = [c[1] for c in g.coords]
        res.append((min(ys), max(ys)))
    return res


def limite_ancho(forma: MultiPolygon, cama, macizo: bool) -> float:
    cx, cy, _ = cama
    alto = forma.bounds[3] - forma.bounds[1]
    extra = COLA_PROF if macizo else 0.0
    if alto <= cy - MARGEN_CAMA:
        return cx - MARGEN_CAMA - extra
    if alto <= cx - MARGEN_CAMA:
        return cy - MARGEN_CAMA - extra
    raise ErrorEntrada(
        f"La pieza mide {alto:.0f} mm de alto y la cama {max(cx, cy):g} mm: "
        "solo se divide en vertical; reduce la altura."
    )


def planificar(forma: MultiPolygon, cama, macizo: bool, holgura: float, evitar_x: list[float]) -> Plan:
    minx, _, maxx, _ = forma.bounds
    ancho = maxx - minx
    lim = limite_ancho(forma, cama, macizo)
    n = max(2, math.ceil(ancho / lim))
    for _ in range(6):
        cortes = _elegir_cortes(forma, minx, maxx, lim, n, evitar_x)
        if cortes is not None:
            break
        n += 1
    else:
        raise ErrorEntrada("No se encontró una forma de dividir la pieza; reduce la altura.")
    bordes = [minx - 1, *cortes, maxx + 1]
    franjas = [box(bordes[i], forma.bounds[1] - 50, bordes[i + 1], forma.bounds[3] + 50) for i in range(len(bordes) - 1)]
    if not macizo:
        regiones = franjas
        hembras = franjas
    else:
        colas = [_colas(forma, x) for x in cortes]
        regiones, hembras = [], []
        for i, franja in enumerate(franjas):
            propia = colas[i] if i < len(colas) else Polygon()  # macho hacia la derecha
            ajena = colas[i - 1] if i > 0 else Polygon()  # hembra en el lado izquierdo
            regiones.append(unary_union([franja, propia]).difference(ajena))
            hembras.append(unary_union([franja, propia]).difference(ajena.buffer(holgura, join_style=2)))
    nombres = list(string.ascii_uppercase[: len(franjas)])
    return Plan(cortes, [multipoligono(r) for r in regiones], [multipoligono(h) for h in hembras], nombres)


def _elegir_cortes(forma, minx, maxx, lim, n, evitar_x):
    cortes, inicio = [], minx
    for k in range(1, n):
        lo = max(inicio + 0.3 * lim, maxx - (n - k) * lim)
        hi = min(inicio + lim, maxx - 0.3 * lim)
        if lo > hi:
            return None
        mejor, puntos = None, None
        x = lo
        while x <= hi + 1e-9:
            longitudes = _cruces(forma, x)
            p = sum(longitudes) + 60 * sum(1 for L in longitudes if L < ASTILLA)
            p += sum(80 for e in evitar_x if abs(e - x) < EVITAR)
            if puntos is None or p < puntos:
                mejor, puntos = x, p
            x += 1.0
        cortes.append(round(mejor, 2))
        inicio = mejor
    if maxx - inicio > lim + 1e-6:
        return None
    return cortes


def _colas(forma: MultiPolygon, x: float) -> Polygon:
    """Colas de milano macho que salen del corte x hacia la derecha, una por tramo cortado."""
    colas = []
    for y0, y1 in _intervalos(forma, x):
        largo = y1 - y0
        if largo < 12:
            continue
        cuello = min(largo * 0.35, 22.0)
        boca = cuello * 1.45
        prof = min(COLA_PROF, largo * 0.5)
        yc = (y0 + y1) / 2
        colas.append(Polygon([(x - 0.01, yc - cuello / 2), (x + prof, yc - boca / 2),
                              (x + prof, yc + boca / 2), (x - 0.01, yc + cuello / 2)]))
    return unary_union(colas) if colas else Polygon()


def empalmes(huecos: MultiPolygon, cortes: list[float], holgura: float) -> list[MultiPolygon]:
    """Placa interior por cada corte: la parte del hueco a ±20 mm del corte, encogida por la holgura."""
    res = []
    for x in cortes:
        zona = huecos.intersection(box(x - EMPALME_ANCHO / 2, huecos.bounds[1] - 1, x + EMPALME_ANCHO / 2, huecos.bounds[3] + 1))
        zona = multipoligono(zona.buffer(-max(holgura, 0.2), join_style=2))
        res.append(MultiPolygon([p for p in poligonos(zona) if p.area > 30]))
    return res
