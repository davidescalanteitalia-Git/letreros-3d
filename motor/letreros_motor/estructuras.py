"""Construcción de las piezas de cada estructura.

Todas las piezas salen en la orientación de impresión (z=0 apoyado en la cama):
- cuerpo de caja/frontal: fondo sobre la cama, paredes hacia arriba;
- frente de frontal: cara visible sobre la cama, faldón hacia arriba;
- cuerpo de halo: cara visible sobre la cama, separadores hacia arriba.

Diseños propios de Letreros 3D Studio; no reproducen geometría de terceros.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import manifold3d as m3d
import trimesh
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import polylabel, split

from .diseno import BOQUILLA_MM, DENSIDAD_PETG, Diseno
from .errores import ErrorEntrada, ErrorGeometria
from .geometria import a_trimesh, cilindro, multipoligono, poligonos, prisma, unir
from .texto import Letra

UNION = {"join_style": 2, "mitre_limit": 3.0}  # esquinas vivas en los offsets
AREA_HUECO_MIN = 4.0  # mm²: por debajo, la parte se hace maciza
LARGO_DOBLE_SEPARADOR = 150.0  # mm: partes más largas llevan dos separadores
R_SEPARADOR = 5.0
DRENAJE_MM = 3.0


@dataclass
class Pieza:
    letra: Letra
    rol: str  # cuerpo | frente | empalme | placa
    malla: trimesh.Trimesh
    huella: MultiPolygon  # contorno apoyado en la cama, para comprobar el tamaño
    parte: str = ""  # A, B, C… si la pieza se dividió; AB, BC… en los empalmes

    @property
    def archivo(self) -> str:
        sufijo = f"-{self.parte}" if self.parte else ""
        return f"{self.letra.codigo}{sufijo}-{self.rol}.stl"

    @property
    def volumen_cm3(self) -> float:
        return float(self.malla.volume) / 1000.0

    @property
    def peso_g(self) -> float:
        return self.volumen_cm3 * DENSIDAD_PETG


@dataclass
class ResultadoLetra:
    letra: Letra
    piezas: list[Pieza] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    metros_led: float = 0.0
    hueca: bool = False
    cortes: list = field(default_factory=list)
    puntos_cable: list = field(default_factory=list)
    puntos_separadores: list = field(default_factory=list)


# --------------------------------------------------------------------------- utilidades 2D

def _interior(parte: Polygon, pared: float):
    """Hueco de una parte de la letra tras restar la pared, o vacío si no cabe."""
    hueco = multipoligono(parte.buffer(-pared, **UNION))
    hueco = multipoligono(MultiPolygon([p for p in hueco.geoms if p.area >= AREA_HUECO_MIN]))
    return hueco


def _punto_mas_holgado(region: Polygon):
    """Centro del mayor círculo inscrito (polo de inaccesibilidad) y su radio."""
    p = polylabel(region, tolerance=0.05)
    return p, region.boundary.distance(p)


def _mitades(region: Polygon) -> list[Polygon]:
    minx, miny, maxx, maxy = region.bounds
    if max(maxx - minx, maxy - miny) <= LARGO_DOBLE_SEPARADOR:
        return [region]
    c = region.centroid
    corte = (LineString([(c.x, miny - 1), (c.x, maxy + 1)]) if maxx - minx >= maxy - miny
             else LineString([(minx - 1, c.y), (maxx + 1, c.y)]))
    partes = [g for g in split(region, corte).geoms if isinstance(g, Polygon)]
    return partes if len(partes) >= 2 else [region]


def _cabe_en_cama(huella: MultiPolygon, cama) -> tuple[bool, bool, tuple[float, float]]:
    """(cabe, solo_girada, (ancho, alto) mínimos). Usa el rectángulo mínimo girado."""
    cx, cy, _ = cama
    minx, miny, maxx, maxy = huella.bounds
    w, h = maxx - minx, maxy - miny
    if w <= cx and h <= cy:
        return True, False, (w, h)
    if w <= cy and h <= cx:  # cabe girada 90°
        return True, True, (w, h)
    rect = huella.minimum_rotated_rectangle
    xs, ys = rect.exterior.coords.xy
    lados = sorted(math.dist((xs[i], ys[i]), (xs[i + 1], ys[i + 1])) for i in range(2))
    a, b = lados
    if (a <= cx and b <= cy) or (a <= cy and b <= cx):
        return True, True, (a, b)
    return False, False, (w, h)


def comprobar_trazos(forma: MultiPolygon) -> bool:
    """True si alguna parte es más fina que la boquilla (desaparece al erosionar B/2)."""
    erosion = forma.buffer(-BOQUILLA_MM / 2)
    return len(poligonos(erosion)) < len(forma.geoms) or erosion.area < 0.3 * forma.area


# --------------------------------------------------------------------------- estructuras

def _agujero_cable(huecos: list[Polygon], d: Diseno, z_fondo: float, avisos: list[str], c: str):
    if d.cable <= 0 or not huecos:
        return m3d.Manifold()
    mayor = max(huecos, key=lambda p: p.area)
    p, r = _punto_mas_holgado(mayor)
    if r < d.cable / 2 + 0.8:
        avisos.append(f"'{c}': no cabe el agujero de cable de Ø{d.cable:g} mm en el fondo.")
        return m3d.Manifold()
    return cilindro(p.x, p.y, d.cable / 2, -1, z_fondo + 1)


def _agujero_drenaje(huecos: list[Polygon], d: Diseno, z_fondo: float, avisos: list[str], c: str):
    if not d.drenaje or not huecos:
        return m3d.Manifold()
    margen = DRENAJE_MM / 2 + 0.8
    zona = multipoligono(MultiPolygon(huecos).buffer(-margen))
    if zona.is_empty:
        avisos.append(f"'{c}': interior demasiado estrecho para el drenaje de Ø{DRENAJE_MM:g} mm.")
        return m3d.Manifold()
    x, y = min((pt for g in zona.geoms for pt in g.exterior.coords), key=lambda q: (q[1], q[0]))
    return cilindro(x, y, DRENAJE_MM / 2, -1, z_fondo + 1)


def _separadores(huecos: list[Polygon], d: Diseno, avisos: list[str], c: str):
    solidos, colocados, z0, z1 = [], [], d.frente, d.profundidad + d.separacion
    for hueco in huecos:
        for region in _mitades(hueco):
            p, r = _punto_mas_holgado(region)
            r_ext = min(R_SEPARADOR, r - 0.2)
            if r_ext < d.tornillo / 2 + 1.2:
                avisos.append(f"'{c}': una zona interior es demasiado estrecha para un separador; fíjala con adhesivo.")
                continue
            solidos.append(cilindro(p.x, p.y, r_ext, z0 - 0.01, z1))
            solidos.append(cilindro(p.x, p.y, d.tornillo / 2, z0 + 1.0, z1 + 1))
            colocados.append((p.x, p.y))
    return solidos[0::2], solidos[1::2], colocados


def _comprobar_led(huecos: list[Polygon], d: Diseno, avisos: list[str], c: str) -> float:
    ancho = d.ancho_tira
    if ancho <= 0 or not huecos:
        return 0.0
    estrechas = []
    for h in huecos:
        if h.buffer(-(ancho / 2 + 0.3)).is_empty:
            _, r = _punto_mas_holgado(h)
            estrechas.append(2 * r)
    if estrechas:
        rango = f"~{min(estrechas):.1f} mm" if len(estrechas) == 1 else f"~{min(estrechas):.1f}–{max(estrechas):.1f} mm"
        avisos.append(f"'{c}': {len(estrechas)} zona(s) interior(es) de {rango} de ancho; no cabe la tira de {ancho:g} mm "
                      "(usa tira más estrecha, más altura o estructura maciza).")
    # Para trazos alargados, la línea central ≈ perímetro interior / 2.
    return sum(h.length for h in huecos) / 2 / 1000.0


def construir_letra(letra: Letra, d: Diseno, retoques: dict | None = None) -> ResultadoLetra:
    """Genera las piezas de una letra. `retoques` = {rol: función(sólido) -> sólido} antes de mallar."""
    res = ResultadoLetra(letra)
    solidos: list[tuple[str, m3d.Manifold]] = []
    c, av = letra.caracter, res.avisos
    forma = letra.forma
    if d.comp_xy > 0:
        forma = multipoligono(forma.buffer(-d.comp_xy, **UNION))
        if forma.is_empty:
            raise ErrorEntrada(f"La compensación XY borra por completo la letra '{c}'.")
    if comprobar_trazos(forma):
        av.append(f"'{c}': hay trazos más finos que la boquilla de {BOQUILLA_MM} mm.")

    huecos: list[Polygon] = []
    if d.estructura != "maciza":
        for parte in forma.geoms:
            h = _interior(parte, d.pared)
            if h.is_empty:
                av.append(f"'{c}': una parte pequeña (tilde, punto o trazo fino) queda maciza: no cabe una pared de {d.pared:g} mm.")
            huecos.extend(h.geoms)
        res.hueca = bool(huecos)
    hueco = MultiPolygon(huecos)
    if d.estructura in ("caja", "frontal") and d.cable > 0 and huecos:
        pc, rc = _punto_mas_holgado(max(huecos, key=lambda q: q.area))
        if rc >= d.cable / 2 + 0.8:
            res.puntos_cable = [(pc.x, pc.y)]
    p = d.profundidad

    if d.estructura == "maciza":
        solidos.append(("cuerpo", prisma(forma, 0, p)))

    elif d.estructura == "caja":
        cuerpo = prisma(forma, 0, p) - prisma(hueco, d.fondo, p + 1)
        cuerpo -= unir([_agujero_cable(huecos, d, d.fondo, av, c), _agujero_drenaje(huecos, d, d.fondo, av, c)])
        solidos.append(("cuerpo", cuerpo))
        res.metros_led = _comprobar_led(huecos, d, av, c)

    elif d.estructura == "frontal":
        alto_cuerpo = p - d.frente
        cuerpo = prisma(forma, 0, alto_cuerpo) - prisma(hueco, d.fondo, alto_cuerpo + 1)
        cuerpo -= unir([_agujero_cable(huecos, d, d.fondo, av, c), _agujero_drenaje(huecos, d, d.fondo, av, c)])
        solidos.append(("cuerpo", cuerpo))
        frente = prisma(forma, 0, d.frente)
        faldon = []
        for h in huecos:
            exterior = h.buffer(-d.holgura, **UNION)
            anillo = multipoligono(exterior.difference(h.buffer(-(d.holgura + d.pared_encaje), **UNION)))
            if anillo.is_empty or anillo.area < 1.0:
                av.append(f"'{c}': una parte es demasiado estrecha para el faldón; ese tramo del frente va pegado.")
                continue
            faldon.append(prisma(anillo, d.frente - 0.01, d.frente + d.encaje))
        solidos.append(("frente", unir([frente, *faldon])))
        res.metros_led = _comprobar_led(huecos, d, av, c)

    elif d.estructura == "halo":
        cuerpo = prisma(forma, 0, p) - prisma(hueco, d.frente, p + 1)
        macizos, agujeros, res.puntos_separadores = _separadores(huecos, d, av, c)
        cuerpo = unir([cuerpo, *macizos]) - unir(agujeros)
        solidos.append(("cuerpo", cuerpo))
        res.metros_led = _comprobar_led(huecos, d, av, c)

    if retoques:
        solidos = [(rol, retoques[rol](sol) if rol in retoques else sol) for rol, sol in solidos]

    cabe, _, (w, h) = _cabe_en_cama(forma, d.cama)
    if cabe:
        for rol, solido in solidos:
            res.piezas.append(_pieza(letra, rol, solido, forma))
    else:
        if not getattr(d, "dividir", True):
            raise ErrorEntrada(
                f"'{c}' mide {w:.0f} × {h:.0f} mm y no cabe en la cama {d.cama[0]:g} × {d.cama[1]:g} mm. "
                "Activa la división automática o reduce la altura."
            )
        _dividir(res, letra, d, forma, hueco, solidos, puntos_clave(huecos, d))

    for pieza in res.piezas:
        cabe, girada, (w, h) = _cabe_en_cama(pieza.huella, d.cama)
        if not cabe:
            raise ErrorEntrada(
                f"La pieza {pieza.archivo} mide {w:.0f} × {h:.0f} mm y no cabe en la cama "
                f"{d.cama[0]:g} × {d.cama[1]:g} mm; reduce la altura."
            )
        if girada:
            av.append(f"{pieza.archivo}: solo cabe girada en la cama; en Bambu Studio usa 'Orientar automáticamente'.")
    return res


def puntos_clave(huecos: list[Polygon], d: Diseno) -> list[tuple[float, float]]:
    """Dónde van el agujero de cable y los separadores (para no cortar por ahí)."""
    pts = []
    if huecos and d.estructura in ("caja", "frontal") and d.cable > 0:
        p, _ = _punto_mas_holgado(max(huecos, key=lambda q: q.area))
        pts.append((p.x, p.y))
    if d.estructura == "halo":
        for h in huecos:
            for region in _mitades(h):
                p, _ = _punto_mas_holgado(region)
                pts.append((p.x, p.y))
    return pts


EMPALME_GROSOR = 2.4


def _dividir(res, letra, d, forma, hueco, solidos, puntos):
    from shapely.geometry import Point

    from .division import empalmes, planificar
    macizo = d.estructura == "maciza" or not res.hueca
    plan = planificar(forma, d.cama, macizo, d.holgura, [x for x, _ in puntos])
    alto = d.profundidad + d.separacion + 60
    for i, (nombre, region) in enumerate(zip(plan.nombres, plan.regiones_hembra)):
        corte = prisma(region, -30, alto)
        for rol, solido in solidos:
            parte = solido ^ corte
            if parte.is_empty() or parte.volume() < 1.0:
                continue
            huella = multipoligono(forma.intersection(region))
            res.piezas.append(_pieza(letra, rol, parte, huella, nombre))
    if not macizo:
        libres = [Point(x, y).buffer(max(d.cable / 2, R_SEPARADOR) + 1.5) for x, y in puntos]
        for k, zona in enumerate(empalmes(hueco, plan.cortes, d.holgura)):
            for q in libres:
                zona = multipoligono(zona.difference(q))
            if zona.is_empty:
                res.avisos.append(f"'{letra.caracter}': el corte {plan.nombres[k]}|{plan.nombres[k + 1]} no tiene sitio para empalme; pégalo con refuerzo.")
                continue
            res.piezas.append(_pieza(letra, "empalme", prisma(zona, 0, EMPALME_GROSOR), zona,
                                     plan.nombres[k] + plan.nombres[k + 1]))
    res.cortes = plan.cortes
    tipo = "cola de milano" if macizo else "corte recto + placa de empalme interior"
    res.avisos.append(f"'{letra.caracter}': dividida en {len(plan.regiones)} partes ({tipo}) en x = "
                      + ", ".join(f"{x:.0f}" for x in plan.cortes) + " mm.")


def _pieza(letra: Letra, rol: str, solido: m3d.Manifold, huella: MultiPolygon, parte: str = "") -> Pieza:
    if solido.is_empty():
        raise ErrorGeometria(f"La pieza {rol} de '{letra.caracter}' quedó vacía.")
    malla = a_trimesh(solido)
    if not (malla.is_watertight and malla.is_winding_consistent and malla.is_volume):
        raise ErrorGeometria(f"La pieza {rol} de '{letra.caracter}' no es un sólido cerrado.")
    return Pieza(letra, rol, malla, huella, parte)
