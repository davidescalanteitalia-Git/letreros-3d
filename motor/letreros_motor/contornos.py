"""Contornos tipográficos reales → polígonos en milímetros.

Las curvas cuadráticas (TrueType) y cúbicas (CFF) se aproximan con segmentos
rectos cuya desviación máxima respecto a la curva es `tolerancia_mm`.
"""
from __future__ import annotations

import math
from functools import lru_cache

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from shapely import affinity
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely.validation import make_valid

from .errores import ErrorEntrada, ErrorGeometria


class _PlumaPoligonos(BasePen):
    """Recoge los contornos del glifo como listas de puntos (unidades de fuente)."""

    def __init__(self, glyphset, paso_unidades: float):
        super().__init__(glyphset)
        self.paso = paso_unidades
        self.anillos: list[list[tuple[float, float]]] = []
        self._actual: list[tuple[float, float]] = []

    def _segmentos(self, largo: float) -> int:
        return max(2, min(64, math.ceil(largo / self.paso)))

    def _moveTo(self, p):
        self._cerrar()
        self._actual = [p]

    def _lineTo(self, p):
        self._actual.append(p)

    def _qCurveToOne(self, p1, p2):
        p0 = self._getCurrentPoint()
        n = self._segmentos(_dist(p0, p1) + _dist(p1, p2))
        for i in range(1, n + 1):
            t = i / n
            a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
            self._actual.append((a * p0[0] + b * p1[0] + c * p2[0], a * p0[1] + b * p1[1] + c * p2[1]))

    def _curveToOne(self, p1, p2, p3):
        p0 = self._getCurrentPoint()
        n = self._segmentos(_dist(p0, p1) + _dist(p1, p2) + _dist(p2, p3))
        for i in range(1, n + 1):
            t = i / n
            a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
            self._actual.append(
                (
                    a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                    a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1],
                )
            )

    def _closePath(self):
        self._cerrar()

    def _endPath(self):
        self._cerrar()

    def _cerrar(self):
        if len(self._actual) >= 3:
            self.anillos.append(self._actual)
        self._actual = []


def _dist(a, b) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _area_firmada(puntos) -> float:
    return 0.5 * sum(
        puntos[i][0] * puntos[(i + 1) % len(puntos)][1] - puntos[(i + 1) % len(puntos)][0] * puntos[i][1]
        for i in range(len(puntos))
    )


def contorno_letra(ruta_fuente, letra: str, altura_mm: float, tolerancia_mm: float = 0.05) -> MultiPolygon:
    """Devuelve la silueta de `letra` como MultiPolygon en mm.

    Convención de medida: `altura_mm` es la altura del contorno real del glifo
    (de su punto más bajo al más alto), no el cuerpo tipográfico. La esquina
    inferior izquierda queda en (0, 0).
    """
    fuente = TTFont(str(ruta_fuente))
    cmap = fuente.getBestCmap()
    if ord(letra) not in cmap:
        raise ErrorEntrada(f"La fuente no contiene el carácter '{letra}'.")
    glyphset = fuente.getGlyphSet()
    nombre = cmap[ord(letra)]

    # Primera pasada sin precisión para conocer la escala.
    pluma = _PlumaPoligonos(glyphset, paso_unidades=1e9)
    glyphset[nombre].draw(pluma)
    if not pluma.anillos:
        raise ErrorEntrada(f"El carácter '{letra}' no tiene contorno imprimible.")
    ys = [p[1] for anillo in pluma.anillos for p in anillo]
    alto_unidades = max(ys) - min(ys)
    if alto_unidades <= 0:
        raise ErrorEntrada(f"El carácter '{letra}' no tiene altura.")
    escala = altura_mm / alto_unidades

    forma = _forma_glifo(glyphset, nombre, escala, tolerancia_mm)
    minx, miny, _, _ = forma.bounds
    forma = affinity.translate(forma, xoff=-minx, yoff=-miny)
    return _a_multipoligono(forma, letra)


def _paso_mm(tolerancia_mm: float) -> float:
    # Una cuerda c sobre un arco de radio R se separa de él c²/(8R). Con R de
    # referencia = 5 mm, c = sqrt(8·tolerancia·R) mantiene la desviación
    # ≤ tolerancia en curvas de radio ≥ 5 mm (las más cerradas de un rótulo).
    return max(0.3, math.sqrt(8 * tolerancia_mm * 5.0))


def _forma_glifo(glyphset, nombre: str, escala: float, tolerancia_mm: float):
    """Silueta del glifo en mm, en coordenadas de la fuente (línea base en y=0)."""
    pluma = _PlumaPoligonos(glyphset, paso_unidades=_paso_mm(tolerancia_mm) / escala)
    glyphset[nombre].draw(pluma)
    if not pluma.anillos:
        return Polygon()
    # TrueType rellena por regla de devanado distinto de cero; los contornos
    # exteriores van en sentido horario (área firmada negativa). Procesar de
    # mayor a menor área: exterior suma, agujero resta, isla interior vuelve a sumar.
    anillos = sorted(pluma.anillos, key=lambda a: abs(_area_firmada(a)), reverse=True)
    signo_exterior = math.copysign(1, _area_firmada(anillos[0]))
    forma = Polygon()
    for anillo in anillos:
        poligono = make_valid(Polygon(anillo))
        if math.copysign(1, _area_firmada(anillo)) == signo_exterior:
            forma = unary_union([forma, poligono])
        else:
            forma = forma.difference(poligono)
    forma = affinity.scale(forma, xfact=escala, yfact=escala, origin=(0, 0))
    return make_valid(forma)


def _a_multipoligono(forma, letra: str) -> MultiPolygon:
    poligonos = [g for g in getattr(forma, "geoms", [forma]) if isinstance(g, Polygon) and g.area > 1e-6]
    if not poligonos:
        raise ErrorGeometria(f"No se obtuvo superficie válida para '{letra}'.")
    return MultiPolygon([orient(p) for p in poligonos])


def _tt(fuente) -> TTFont:
    """Acepta la clave de una fuente registrada (variables ya fijadas) o una ruta a un .ttf estático."""
    from .fuentes import FUENTES, ttfont
    if isinstance(fuente, str) and fuente in FUENTES:
        return ttfont(fuente)
    return _cargar(str(fuente))


@lru_cache(maxsize=8)
def _cargar(ruta: str) -> TTFont:
    return TTFont(ruta)


def altura_mayuscula_unidades(fuente) -> float:
    """Altura de la mayúscula (A, H, M) en unidades de la fuente."""
    tt = _tt(fuente)
    cap = getattr(tt["OS/2"], "sCapHeight", 0) or 0
    if cap <= 0:  # fuentes antiguas sin sCapHeight: medir la H
        glyphset = tt.getGlyphSet()
        pluma = _PlumaPoligonos(glyphset, paso_unidades=1e9)
        glyphset[tt.getBestCmap()[ord("H")]].draw(pluma)
        cap = max(p[1] for a in pluma.anillos for p in a)
    return float(cap)


def glifo_por_nombre_mm(fuente, nombre: str, escala: float, tolerancia_mm: float = 0.05) -> MultiPolygon:
    tt = _tt(fuente)
    forma = _forma_glifo(tt.getGlyphSet(), nombre, escala, tolerancia_mm)
    if forma.is_empty:
        return MultiPolygon()
    return _a_multipoligono(forma, nombre)


def glifo_mm(fuente, caracter: str, escala: float, tolerancia_mm: float = 0.05):
    """(silueta en mm con línea base en y=0, avance horizontal en mm).

    La silueta puede estar vacía (espacio). No se desplaza: x=0 es el origen
    del glifo, así se respetan los márgenes laterales de la fuente.
    """
    tt = _tt(fuente)
    cmap = tt.getBestCmap()
    if ord(caracter) not in cmap:
        raise ErrorEntrada(f"La fuente no contiene el carácter '{caracter}'.")
    nombre = cmap[ord(caracter)]
    avance = tt["hmtx"][nombre][0] * escala
    return glifo_por_nombre_mm(fuente, nombre, escala, tolerancia_mm), avance
