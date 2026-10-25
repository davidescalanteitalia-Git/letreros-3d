"""División de una pieza que no cabe en la cama.

Diseño propio de Letreros 3D Studio:
- Cortes verticales (perpendiculares al texto) situados donde la sección de
  material es más corta, evitando astillas (< 6 mm) y los puntos donde van el
  agujero de cable o los separadores.
- Si la pieza es más alta que la cama, primero se corta en franjas horizontales
  (filas 1, 2… de abajo arriba) con el mismo criterio, y cada franja se corta en
  vertical si hace falta (columnas A, B…). Una rejilla da partes A1, B1, A2…
- Macizas y placas: cola de milano en cada tramo cortado (macho hacia la
  derecha o hacia arriba; la hembra se agranda con la holgura).
- Huecas: corte recto + placa de empalme interior que se pega cruzando la junta
  (no se ve desde fuera y alinea las dos partes). Cada empalme se nombra con las
  dos partes que une (AB, 12, A1A2…).
"""
from __future__ import annotations

import math
import string
from dataclasses import dataclass, field

from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
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
    cortes: list[float]  # x de los cortes verticales (todas las filas)
    regiones: list[Polygon]  # una por parte
    regiones_hembra: list[Polygon]  # misma región con la holgura aplicada a las colas ajenas
    nombres: list[str]
    cortes_y: list[float] = field(default_factory=list)  # y de los cortes horizontales
    juntas: list[tuple[str, LineString]] = field(default_factory=list)  # (partes unidas, tramo del corte)


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


def _espejo(g):
    """Intercambia x e y: así los cortes horizontales se calculan como verticales."""
    return affinity.affine_transform(g, [0, 1, 1, 0, 0, 0])


def limite_ancho(forma: MultiPolygon, cama, macizo: bool) -> float:
    """Ancho máximo de cada parte cuando solo se corta en vertical."""
    cx, cy, _ = cama
    alto = forma.bounds[3] - forma.bounds[1]
    extra = COLA_PROF if macizo else 0.0
    if alto <= cy - MARGEN_CAMA:
        return cx - MARGEN_CAMA - extra
    if alto <= cx - MARGEN_CAMA:
        return cy - MARGEN_CAMA - extra
    return 0.0  # hace falta cortar también en horizontal


def _plan_1d(forma, lim, macizo, holgura, evitar):
    """Cortes verticales de `forma` en partes de ancho ≤ lim. Devuelve (cortes, regiones, hembras)."""
    minx, _, maxx, _ = forma.bounds
    if maxx - minx <= lim:
        franja = box(minx - 60, forma.bounds[1] - 60, maxx + 60, forma.bounds[3] + 60)
        return [], [franja], [franja]
    n = max(2, math.ceil((maxx - minx) / lim))
    for _ in range(6):
        cortes = _elegir_cortes(forma, minx, maxx, lim, n, evitar)
        if cortes is not None:
            break
        n += 1
    else:
        raise ErrorEntrada("No se encontró una forma de dividir la pieza; reduce la altura.")
    bordes = [minx - 60, *cortes, maxx + 60]
    franjas = [box(bordes[i], forma.bounds[1] - 60, bordes[i + 1], forma.bounds[3] + 60) for i in range(len(bordes) - 1)]
    if not macizo:
        return cortes, franjas, franjas
    colas = [_colas(forma, x) for x in cortes]
    regiones, hembras = [], []
    for i, franja in enumerate(franjas):
        propia = colas[i] if i < len(colas) else Polygon()  # macho hacia la derecha
        ajena = colas[i - 1] if i > 0 else Polygon()  # hembra en el lado izquierdo
        regiones.append(unary_union([franja, propia]).difference(ajena))
        hembras.append(unary_union([franja, propia]).difference(ajena.buffer(holgura, join_style=2)))
    return cortes, regiones, hembras


def planificar(forma: MultiPolygon, cama, macizo: bool, holgura: float, puntos) -> Plan:
    """Plan de corte. `puntos` = [(x, y)] de cable/separadores que no deben cortarse
    (por compatibilidad también acepta una lista de x)."""
    puntos = [(p, None) if isinstance(p, (int, float)) else tuple(p) for p in puntos]
    evitar_x = [x for x, _ in puntos]
    evitar_y = [y for _, y in puntos if y is not None]
    cx, cy, _ = cama
    extra = COLA_PROF if macizo else 0.0
    minx, miny, maxx, maxy = forma.bounds
    lim = limite_ancho(forma, cama, macizo)

    if lim > 0:  # una sola fila: partes A, B, C…
        cortes, regiones, hembras = _plan_1d(forma, lim, macizo, holgura, evitar_x)
        nombres = list(string.ascii_uppercase[: len(regiones)])
        juntas = [(nombres[k] + nombres[k + 1], LineString([(x, miny - 1), (x, maxy + 1)])) for k, x in enumerate(cortes)]
        return Plan(cortes, [multipoligono(r) for r in regiones], [multipoligono(h) for h in hembras], nombres,
                    [], juntas)

    # Varias filas: franjas horizontales de alto ≤ lado corto de la cama, y cada franja en vertical.
    lim_alto = min(cx, cy) - MARGEN_CAMA - extra - 1.0
    lim_ancho = max(cx, cy) - MARGEN_CAMA - extra
    espejada = multipoligono(_espejo(forma))
    cortes_y, filas, filas_h = _plan_1d(espejada, lim_alto, macizo, holgura, evitar_y)
    filas = [_espejo(f) for f in filas]
    filas_h = [_espejo(f) for f in filas_h]

    regiones, hembras, nombres, por_fila = [], [], [], []
    for n, (fila, fila_h) in enumerate(zip(filas, filas_h), start=1):
        trozo = multipoligono(forma.intersection(fila))
        if trozo.is_empty:
            por_fila.append([])
            continue
        cortes_x, cols, cols_h = _plan_1d(trozo, lim_ancho, macizo, holgura, evitar_x)
        una = len(cols) == 1
        propios = []
        for k, (col, col_h) in enumerate(zip(cols, cols_h)):
            nombre = str(n) if una else f"{string.ascii_uppercase[k]}{n}"
            regiones.append(multipoligono(fila.intersection(col)))
            hembras.append(multipoligono(fila_h.intersection(col_h)))
            nombres.append(nombre)
            propios.append(nombre)
        por_fila.append(cortes_x)
    juntas: list[tuple[str, LineString]] = []
    # juntas verticales dentro de cada fila
    for n, cortes_x in enumerate(por_fila, start=1):
        y0 = cortes_y[n - 2] if n > 1 else miny - 1
        y1 = cortes_y[n - 1] if n - 1 < len(cortes_y) else maxy + 1
        for x in cortes_x:
            juntas.append((_nombre_junta(regiones, nombres, (x - 1, (y0 + y1) / 2), (x + 1, (y0 + y1) / 2)),
                           LineString([(x, y0), (x, y1)])))
    # juntas horizontales, troceadas por los cortes verticales de las dos filas vecinas
    for n, y in enumerate(cortes_y, start=1):
        xs = sorted({minx - 1, maxx + 1, *por_fila[n - 1], *(por_fila[n] if n < len(por_fila) else [])})
        for a, b in zip(xs, xs[1:]):
            m = (a + b) / 2
            juntas.append((_nombre_junta(regiones, nombres, (m, y - 1), (m, y + 1)), LineString([(a, y), (b, y)])))
    # Fuera las celdas sin material y los tramos de junta que no cruzan la pieza.
    vivas = [i for i, r in enumerate(regiones) if forma.intersection(r).area > 1.0]
    regiones, hembras, nombres = [regiones[i] for i in vivas], [hembras[i] for i in vivas], [nombres[i] for i in vivas]
    juntas = [(n, s) for n, s in juntas if s.intersection(forma).length > 1.0]
    todos_x = sorted({x for c in por_fila for x in c})
    return Plan(todos_x, regiones, hembras, nombres, list(cortes_y), juntas)


def _nombre_junta(regiones, nombres, p1, p2) -> str:
    def parte(p):
        q = Point(p)
        for r, nom in zip(regiones, nombres):
            if r.contains(q):
                return nom
        return min(zip(regiones, nombres), key=lambda rn: rn[0].distance(q))[1]
    return parte(p1) + parte(p2)


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


def empalmes(huecos: MultiPolygon, juntas, holgura: float) -> list[MultiPolygon]:
    """Placa interior por cada junta: la parte del hueco a ±20 mm del tramo de corte, encogida por la holgura.

    `juntas` = [(nombre, LineString)] del plan; por compatibilidad admite una lista de x (cortes verticales).
    """
    res = []
    for j in juntas:
        if isinstance(j, (int, float)):
            j = ("", LineString([(j, huecos.bounds[1] - 1), (j, huecos.bounds[3] + 1)]))
        _, seg = j
        x0, y0, x1, y1 = seg.bounds
        r = EMPALME_ANCHO / 2
        zona_caja = box(x0 - r, y0, x1 + r, y1) if x1 - x0 < 1e-6 else box(x0, y0 - r, x1, y1 + r)
        zona = huecos.intersection(zona_caja)
        zona = multipoligono(zona.buffer(-max(holgura, 0.2), join_style=2))
        res.append(MultiPolygon([p for p in poligonos(zona) if p.area > 30]))
    return res
