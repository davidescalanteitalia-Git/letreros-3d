"""Logotipos en SVG o DXF → silueta 2D en mm, lista para las mismas estructuras que las letras.

- SVG: cada elemento con relleno aporta sus contornos (regla par-impar dentro del elemento:
  los agujeros de una «O» o de un anillo se respetan); los elementos se suman. Se aplican
  las transformaciones del archivo. Los trazos sin relleno se ignoran (avisando).
- DXF: polilíneas, círculos, elipses, arcos, splines y líneas. Se buscan las regiones
  cerradas y se rellenan por niveles (contorno exterior lleno, agujero vacío, isla llena…).
- El resultado se normaliza a 1 de alto con la esquina inferior izquierda en (0, 0);
  el letrero lo escala a la altura que elijas.

Seguridad: tamaño limitado, sin DOCTYPE/ENTITY en SVG y número de puntos acotado.
"""
from __future__ import annotations

import io
import math

from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import polygonize, unary_union
from shapely.validation import make_valid

from .errores import ErrorEntrada
from .geometria import multipoligono, poligonos

TAMANO_MAX = 600_000  # bytes del archivo
PUNTOS_MAX = 250_000
PASO_CURVA = 0.004  # fracción del tamaño del dibujo entre puntos al aplanar curvas


def _limpiar(geom) -> MultiPolygon:
    geom = make_valid(geom)
    mp = multipoligono(geom)
    if mp.is_empty:
        return mp
    area = mp.area
    return MultiPolygon([p for p in mp.geoms if p.area > area * 1e-5])


def normalizar(forma: MultiPolygon) -> MultiPolygon:
    minx, miny, maxx, maxy = forma.bounds
    alto = maxy - miny
    if alto <= 0 or (maxx - minx) <= 0:
        raise ErrorEntrada("El logo no tiene tamaño.")
    f = affinity.translate(forma, -minx, -miny)
    return multipoligono(affinity.scale(f, 1 / alto, 1 / alto, origin=(0, 0)))


def _par_impar(anillos: list[Polygon]):
    r = Polygon()
    for p in anillos:
        if p.is_valid and p.area > 0:
            r = r.symmetric_difference(p)
        else:
            r = r.symmetric_difference(make_valid(p))
    return r


# --------------------------------------------------------------------------- SVG

def leer_svg(texto: str) -> tuple[MultiPolygon, list[str]]:
    from svgelements import SVG, Shape

    if len(texto.encode("utf-8")) > TAMANO_MAX:
        raise ErrorEntrada("El logo pesa demasiado (máximo 600 kB). Simplifícalo o guárdalo como SVG optimizado.")
    cabecera = texto[:4000].upper()
    if "<!DOCTYPE" in cabecera or "<!ENTITY" in texto.upper():
        raise ErrorEntrada("SVG no admitido: contiene DOCTYPE o entidades. Expórtalo como SVG simple.")
    try:
        svg = SVG.parse(io.StringIO(texto), reify=True)
    except Exception as e:  # noqa: BLE001 - cualquier fallo del analizador es un archivo no válido
        raise ErrorEntrada(f"No se pudo leer el SVG: {e}") from None
    avisos, piezas, sin_relleno, puntos = [], [], 0, 0
    formas = [e for e in svg.elements() if isinstance(e, Shape)]
    if not formas:
        raise ErrorEntrada("El SVG no contiene formas.")
    caja = None
    for e in formas:
        try:
            bb = e.bbox()
        except Exception:  # noqa: BLE001
            bb = None
        if bb:
            caja = bb if caja is None else (min(caja[0], bb[0]), min(caja[1], bb[1]), max(caja[2], bb[2]), max(caja[3], bb[3]))
    tam = max(caja[2] - caja[0], caja[3] - caja[1]) if caja else 100.0
    paso = max(tam * PASO_CURVA, 1e-6)
    for e in formas:
        if e.fill is None or e.fill.value is None or getattr(e.fill, "alpha", 255) == 0:
            sin_relleno += 1
            continue
        from svgelements import Path
        camino = Path(e)
        anillos = []
        for sub in camino.as_subpaths():
            sub = Path(sub)
            try:
                largo = sub.length(error=1e-3)
            except Exception:  # noqa: BLE001
                continue
            if not largo or largo <= 0:
                continue
            n = max(8, min(4000, int(largo / paso)))
            pts = [sub.point(i / n) for i in range(n + 1)]
            pts = [(float(p.x), -float(p.y)) for p in pts if p is not None]
            puntos += len(pts)
            if puntos > PUNTOS_MAX:
                raise ErrorEntrada("El logo tiene demasiado detalle; simplifícalo antes de subirlo.")
            if len(pts) >= 3:
                anillos.append(Polygon(pts))
        if anillos:
            piezas.append(_par_impar(anillos))
    if sin_relleno:
        avisos.append(f"Logo: {sin_relleno} elemento(s) sin relleno (solo trazo) se han ignorado; "
                      "conviértelos a trazados rellenos si deben imprimirse.")
    forma = _limpiar(unary_union(piezas)) if piezas else MultiPolygon()
    if forma.is_empty:
        raise ErrorEntrada("El logo no tiene zonas rellenas: conviértelo a formas rellenas (trazo → contorno).")
    return forma, avisos


# --------------------------------------------------------------------------- DXF

def leer_dxf(texto: str) -> tuple[MultiPolygon, list[str]]:
    import ezdxf
    from ezdxf import path as epath

    if len(texto.encode("utf-8")) > TAMANO_MAX:
        raise ErrorEntrada("El logo pesa demasiado (máximo 600 kB).")
    try:
        doc = ezdxf.read(io.StringIO(texto))
    except Exception as e:  # noqa: BLE001
        raise ErrorEntrada(f"No se pudo leer el DXF: {e}") from None
    msp = doc.modelspace()
    tipos = ("LWPOLYLINE", "POLYLINE", "CIRCLE", "ARC", "ELLIPSE", "SPLINE", "LINE")
    entidades = [e for e in msp if e.dxftype() in tipos]
    if not entidades:
        raise ErrorEntrada("El DXF no contiene contornos (polilíneas, círculos, arcos, splines o líneas).")
    caminos = []
    for e in entidades:
        try:
            caminos.append(epath.make_path(e))
        except Exception:  # noqa: BLE001
            continue
    xs, ys = [], []
    for c in caminos:
        for v in c.control_vertices():
            xs.append(v.x)
            ys.append(v.y)
        xs.append(c.start.x)
        ys.append(c.start.y)
    tam = max(max(xs) - min(xs), max(ys) - min(ys)) if xs else 100.0
    distancia = max(tam * PASO_CURVA * 0.25, 1e-6)
    lineas, puntos = [], 0
    for c in caminos:
        pts = [(v.x, v.y) for v in c.flattening(distancia)]
        puntos += len(pts)
        if puntos > PUNTOS_MAX:
            raise ErrorEntrada("El logo tiene demasiado detalle; simplifícalo antes de subirlo.")
        if len(pts) >= 2:
            lineas.append(LineString(pts))
    caras = list(polygonize(unary_union(lineas)))
    if not caras:
        raise ErrorEntrada("El DXF no tiene contornos cerrados: cierra las polilíneas del logo.")
    # Relleno por niveles: una cara está llena si la contienen un número par de otras caras.
    exteriores = [Polygon(c.exterior) for c in caras]
    llenas = []
    for i, cara in enumerate(caras):
        p = cara.representative_point()
        nivel = sum(1 for j, ex in enumerate(exteriores) if j != i and ex.contains(p))
        if nivel % 2 == 0:
            llenas.append(cara)
    forma = _limpiar(unary_union(llenas))
    if forma.is_empty:
        raise ErrorEntrada("No se encontró ninguna zona rellena en el DXF.")
    return forma, []


def leer_logo(texto: str, nombre: str = "") -> tuple[MultiPolygon, list[str]]:
    """Lee un SVG o DXF (según el nombre o el contenido) y devuelve la silueta normalizada a 1 de alto."""
    if not isinstance(texto, str) or not texto.strip():
        raise ErrorEntrada("El archivo del logo está vacío.")
    es_dxf = nombre.lower().endswith(".dxf") or ("SECTION" in texto[:2000] and "<svg" not in texto[:2000].lower())
    forma, avisos = leer_dxf(texto) if es_dxf else leer_svg(texto)
    return normalizar(forma), avisos


def colocar(logo: MultiPolygon, letras_bounds, d) -> MultiPolygon:
    """Escala el logo normalizado a `d.logo_altura` y lo coloca respecto al texto."""
    f = affinity.scale(logo, d.logo_altura, d.logo_altura, origin=(0, 0))
    w = f.bounds[2]
    h = d.logo_altura
    if letras_bounds is None:
        return multipoligono(f)
    minx, miny, maxx, maxy = letras_bounds
    s = d.logo_separacion
    cy = d.altura / 2  # centro de la mayúscula de la primera línea
    pos = d.logo_posicion
    if pos == "izquierda":
        dx, dy = minx - s - w, cy - h / 2
    elif pos == "derecha":
        dx, dy = maxx + s, cy - h / 2
    elif pos == "arriba":
        dx, dy = (minx + maxx) / 2 - w / 2, maxy + s
    else:  # abajo
        dx, dy = (minx + maxx) / 2 - w / 2, miny - s - h
    return multipoligono(affinity.translate(f, dx, dy))


def logo_a_svg(logo: MultiPolygon) -> str:
    """Trazado SVG (viewBox 0 0 w 1, y hacia abajo) para la miniatura en la web."""
    partes = []
    for p in poligonos(logo):
        for anillo in (p.exterior, *p.interiors):
            cs = list(anillo.coords)
            partes.append("M" + " L".join(f"{x:.4f},{1 - y:.4f}" for x, y in cs) + " Z")
    return " ".join(partes)


def proporcion(logo: MultiPolygon) -> float:
    minx, miny, maxx, maxy = logo.bounds
    return (maxx - minx) / max(maxy - miny, 1e-9)


__all__ = ["leer_logo", "leer_svg", "leer_dxf", "normalizar", "colocar", "logo_a_svg", "proporcion", "math"]
