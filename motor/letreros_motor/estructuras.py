"""Construcción de las piezas de cada estructura.

Todas las piezas salen en la orientación de impresión (z=0 apoyado en la cama):
- cuerpo de caja/frontal/lateral: fondo sobre la cama, paredes hacia arriba;
- frente de frontal/lateral/doble: cara visible sobre la cama, faldón hacia arriba;
- cuerpo de halo: cara visible sobre la cama, separadores hacia arriba;
- doble: cuerpo = anillo de paredes; trasera translúcida con faldón hacia arriba;
- neón: base plana con el canal hacia arriba.
Cada pieza lleva su material (opaco / difusor) y la matriz que la lleva de la
pose de impresión a la pose montada (para el visor y la plantilla).

Diseños propios de Letreros 3D Studio; no reproducen geometría de terceros.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import manifold3d as m3d
import numpy as np
import trimesh
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import polylabel, split, unary_union

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
    material: str = "opaco"  # opaco | difusor (cada cama de impresión lleva un solo filamento)
    montaje: np.ndarray | None = None  # 4×4: pose de impresión → pose montada (None = igual)

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
    cortes: list = field(default_factory=list)  # x de los cortes verticales
    cortes_y: list = field(default_factory=list)  # y de los cortes horizontales
    juntas: list = field(default_factory=list)  # [((x0, y0), (x1, y1))] tramos de corte, para la plantilla
    puntos_cable: list = field(default_factory=list)
    puntos_separadores: list = field(default_factory=list)
    puntos_fijacion: list = field(default_factory=list)  # torretas/agujeros de fijación (x, y)
    led: dict = field(default_factory=dict)  # plan de LED de la letra (filas, separación, metros)
    visual: list = field(default_factory=list)  # [(rol, trimesh)] solo para el visor (p. ej. el neón)


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

def huecos_cable(huecos: list[Polygon], letra: Letra, d: Diseno) -> list[Polygon]:
    """Hueco donde va el agujero de cable: el mayor, o el primero/último si hay una sola salida."""
    if not huecos or getattr(letra, "salida", "") == "no":
        return []
    salida = getattr(letra, "salida", "")
    if salida in ("inicio", "fin"):
        from shapely.geometry import box as _box
        todo = unary_union(huecos)
        minx, miny, maxx, maxy = todo.bounds
        for f in (0.3, 0.5, 0.8, 1.2, 3.0):
            w = f * d.altura
            franja = _box(minx - 1, miny - 1, minx + w, maxy + 1) if salida == "inicio" else _box(maxx - w, miny - 1, maxx + 1, maxy + 1)
            trozos = poligonos(todo.intersection(franja))
            if trozos:
                mayor = max(trozos, key=lambda q: q.area)
                if _punto_mas_holgado(mayor)[1] >= d.cable / 2 + 0.8:
                    return [mayor]
        return [max(huecos, key=lambda q: q.area)]
    return [max(huecos, key=lambda q: q.area)]


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
    """Avisa de zonas donde no cabe la tira. Devuelve los metros de tira del plan profesional."""
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
    return 0.0


def distancia_luz(d: Diseno) -> float:
    """Distancia de la tira a la superficie que difunde (mm): marca la separación entre filas."""
    if d.estructura in ("frontal", "lateral"):
        return d.profundidad - d.fondo - d.frente
    if d.estructura == "caja":
        return d.profundidad - d.fondo
    if d.estructura == "halo":
        return d.separacion
    if d.estructura == "caja_luz":
        return d.profundidad - d.fondo - d.frente - d.mascara
    return d.profundidad


def separacion_filas(d: Diseno) -> float:
    """Regla de taller: filas de LED separadas como mucho lo que mide la distancia a la cara
    (luz uniforme sin puntos). `paso_led` > 0 la fija a mano."""
    if d.paso_led > 0:
        return d.paso_led
    return min(max(distancia_luz(d), 15.0), 100.0)


def plan_led(huecos: list[Polygon], d: Diseno) -> dict:
    """Filas y metros de tira por letra.

    - frontal / lateral / caja / halo / caja de luz: cada trazo interior lleva
      max(1, redondeo(ancho / separación)) filas a lo largo de su línea central
      (largo ≈ área / ancho medio, ancho medio ≈ 2·área / perímetro).
    - doble: tira lateral pegada a la pared interior: una vuelta por hueco.
    """
    if not huecos or d.ancho_tira <= 0 and d.estructura != "doble":
        return {"metros": 0.0, "filas": 0, "separacion_mm": 0.0}
    sep = separacion_filas(d)
    if d.estructura == "doble":
        metros = sum(h.length for h in huecos) / 1000.0
        return {"metros": round(metros, 3), "filas": len(huecos), "separacion_mm": 0.0, "montaje": "lateral (pared interior)"}
    total, filas = 0.0, 0
    for h in huecos:
        if h.area <= 0 or h.length <= 0:
            continue
        ancho = 2 * h.area / h.length
        largo = h.area / max(ancho, 1e-6)
        n = max(1, round(ancho / sep))
        total += largo * n
        filas = max(filas, n)
    return {"metros": round(total / 1000.0, 3), "filas": filas, "separacion_mm": round(sep, 1),
            "montaje": "fondo" if d.estructura != "halo" else "trasera del frente, hacia la pared"}


# --------------------------------------------------------------------------- fijaciones

INSERTO_D, INSERTO_PROF = 5.6, 8.0  # inserto térmico M4 (Ø5,6 × 8)
TORRETA_R_MAX = 5.5
PASANTE_D, AVELLANADO_D = 4.5, 8.5


def _puntos_fijacion(huecos: list[Polygon], radio_min: float) -> list[tuple[float, float, float]]:
    pts = []
    for hueco in huecos:
        for region in _mitades(hueco):
            p, r = _punto_mas_holgado(region)
            if r >= radio_min:
                pts.append((p.x, p.y, r))
    return pts


def _fijaciones(huecos: list[Polygon], d: Diseno, z_fondo: float, alto_libre: float, av: list[str], c: str, evitar=()):
    """(sólidos que se suman, sólidos que se restan, puntos) según d.fijacion."""
    from shapely.geometry import Point
    if d.fijacion == "ninguna" or not huecos:
        return [], [], []
    libres = [Point(x, y).buffer(d.cable / 2 + 2) for x, y in evitar]
    huecos = [h for hh in huecos for h in poligonos(hh.difference(unary_union(libres)) if libres else hh)]
    suma, resta, pts = [], [], []
    if d.fijacion == "insertos":
        r_min = INSERTO_D / 2 + 1.6 + 0.3
        alto = min(10.0, alto_libre - 1.0)
        if alto < INSERTO_PROF + 0.5:
            av.append(f"'{c}': no hay altura para torretas de inserto M4; usa agujeros pasantes.")
            return [], [], []
        for x, y, r in _puntos_fijacion(huecos, r_min):
            re = min(TORRETA_R_MAX, r - 0.3)
            suma.append(cilindro(x, y, re, z_fondo - 0.01, z_fondo + alto))
            resta.append(cilindro(x, y, INSERTO_D / 2, z_fondo + alto - INSERTO_PROF, z_fondo + alto + 1))
            pts.append((x, y))
    else:  # pasantes con avellanado por dentro (cabeza del tornillo dentro de la letra)
        r_min = AVELLANADO_D / 2 + 0.6
        for x, y, _ in _puntos_fijacion(huecos, r_min):
            resta.append(cilindro(x, y, PASANTE_D / 2, -1, z_fondo + 1))
            h = min(z_fondo, (AVELLANADO_D - PASANTE_D) / 2)
            resta.append(m3d.Manifold.cylinder(h + 0.01, PASANTE_D / 2, AVELLANADO_D / 2, 48).translate([x, y, z_fondo - h]))
            pts.append((x, y))
    if not pts:
        av.append(f"'{c}': interior demasiado estrecho para fijaciones; pégala o usa placa común.")
    return suma, resta, pts


# --------------------------------------------------------------------------- matrices de montaje

def voltear(p: float) -> np.ndarray:
    """Refleja en Z: la pieza impresa boca abajo queda con la cara en z = p."""
    m = np.eye(4)
    m[2, 2], m[2, 3] = -1.0, p
    return m


def subir(dz: float) -> np.ndarray:
    m = np.eye(4)
    m[2, 3] = dz
    return m


# --------------------------------------------------------------------------- estructuras

def _faldon(huecos, d, av, c, z0):
    """Faldón que entra en el cuerpo (frente/trasera a presión)."""
    faldon = []
    for h in huecos:
        exterior = h.buffer(-d.holgura, **UNION)
        anillo = multipoligono(exterior.difference(h.buffer(-(d.holgura + d.pared_encaje), **UNION)))
        if anillo.is_empty or anillo.area < 1.0:
            av.append(f"'{c}': una parte es demasiado estrecha para el faldón; ese tramo va pegado.")
            continue
        faldon.append(prisma(anillo, z0 - 0.01, z0 + d.encaje))
    return faldon


def ranura_neon(forma: MultiPolygon, d: Diseno) -> MultiPolygon:
    """Canal del neón: sigue el contorno de la letra (rincones suavizados) con el ancho del neón + juego."""
    w = d.neon_ancho + 2 * max(d.holgura, 0.2)
    camino = forma.buffer(d.neon_ancho, join_style=1).buffer(-d.neon_ancho, join_style=1)
    return multipoligono(camino.boundary.buffer(w / 2, join_style=1, cap_style=1))


def profundidad_ranura_neon(d: Diseno) -> float:
    return min(d.neon_alto * 0.6, d.profundidad - 2.0)


def construir_letra(letra: Letra, d: Diseno, retoques: dict | None = None) -> ResultadoLetra:
    """Genera las piezas de una letra. `retoques` = {rol: función(sólido) -> sólido} antes de mallar."""
    res = ResultadoLetra(letra)
    solidos: list[tuple[str, m3d.Manifold]] = []
    materiales: dict[str, str] = {}
    montajes: dict[str, np.ndarray] = {}
    c, av = letra.caracter, res.avisos
    forma = letra.forma
    if d.comp_xy > 0:
        forma = multipoligono(forma.buffer(-d.comp_xy, **UNION))
        if forma.is_empty:
            raise ErrorEntrada(f"La compensación XY borra por completo la letra '{c}'.")
    if comprobar_trazos(forma):
        av.append(f"'{c}': hay trazos más finos que la boquilla de {BOQUILLA_MM} mm.")

    huecos: list[Polygon] = []
    if d.estructura not in ("maciza", "neon"):
        for parte in forma.geoms:
            h = _interior(parte, d.pared)
            if h.is_empty:
                av.append(f"'{c}': una parte pequeña (tilde, punto o trazo fino) queda maciza: no cabe una pared de {d.pared:g} mm.")
            huecos.extend(h.geoms)
        res.hueca = bool(huecos)
    hueco = MultiPolygon(huecos)
    hc = huecos_cable(huecos, letra, d)
    if d.estructura in ("caja", "frontal", "lateral") and d.cable > 0 and hc:
        pc, rc = _punto_mas_holgado(hc[0])
        if rc >= d.cable / 2 + 0.8:
            res.puntos_cable = [(pc.x, pc.y)]
    p = d.profundidad
    plantilla_forma = forma

    if d.estructura == "maciza":
        cuerpo = prisma(forma, 0, p)
        if d.fijacion != "ninguna":  # macizas: agujeros ciegos por detrás para espárrago/inserto
            pts = _puntos_fijacion([g for g in forma.geoms], INSERTO_D / 2 + 2.5)
            cuerpo -= unir([cilindro(x, y, INSERTO_D / 2, -1, min(INSERTO_PROF, p - 2)) for x, y, _ in pts])
            res.puntos_fijacion = [(x, y) for x, y, _ in pts]
        solidos.append(("cuerpo", cuerpo))

    elif d.estructura == "caja":
        cuerpo = prisma(forma, 0, p) - prisma(hueco, d.fondo, p + 1)
        suma, resta, res.puntos_fijacion = _fijaciones(huecos, d, d.fondo, p - d.fondo, av, c, res.puntos_cable)
        cuerpo = unir([cuerpo, *suma])
        cuerpo -= unir([_agujero_cable(hc, d, d.fondo, av, c), _agujero_drenaje(huecos, d, d.fondo, av, c), *resta])
        solidos.append(("cuerpo", cuerpo))
        _comprobar_led(huecos, d, av, c)

    elif d.estructura in ("frontal", "lateral"):
        alto_cuerpo = p - d.frente
        cuerpo = prisma(forma, 0, alto_cuerpo) - prisma(hueco, d.fondo, alto_cuerpo + 1)
        libre = alto_cuerpo - d.fondo - d.encaje
        suma, resta, res.puntos_fijacion = _fijaciones(huecos, d, d.fondo, libre, av, c, res.puntos_cable)
        cuerpo = unir([cuerpo, *suma])
        cuerpo -= unir([_agujero_cable(hc, d, d.fondo, av, c), _agujero_drenaje(huecos, d, d.fondo, av, c), *resta])
        solidos.append(("cuerpo", cuerpo))
        solidos.append(("frente", unir([prisma(forma, 0, d.frente), *_faldon(huecos, d, av, c, d.frente)])))
        montajes["frente"] = voltear(p)
        if d.estructura == "lateral":
            materiales.update(cuerpo="difusor", frente="opaco")
        else:
            materiales["frente"] = "difusor"
        _comprobar_led(huecos, d, av, c)

    elif d.estructura == "doble":
        # Anillo de paredes + frente y trasera translúcidos a presión; la trasera lleva los
        # agujeros para separadores metálicos de pared y el paso de cable.
        alto = p - d.frente - d.fondo
        solidos.append(("cuerpo", prisma(forma, 0, alto) - prisma(hueco, -1, alto + 1)))
        montajes["cuerpo"] = subir(d.fondo)
        solidos.append(("frente", unir([prisma(forma, 0, d.frente), *_faldon(huecos, d, av, c, d.frente)])))
        montajes["frente"] = voltear(p)
        materiales["frente"] = "difusor"
        trasera = unir([prisma(forma, 0, d.fondo), *_faldon(huecos, d, av, c, d.fondo)])
        pts = _puntos_fijacion(huecos, max(d.tornillo / 2 + 4.0, d.encaje))
        res.puntos_separadores = [(x, y) for x, y, _ in pts]
        quitar = [cilindro(x, y, d.tornillo / 2, -1, d.fondo + d.encaje + 1) for x, y in res.puntos_separadores]
        if d.cable > 0 and hc:
            pc, rc = _punto_mas_holgado(hc[0])
            if rc >= d.cable / 2 + 0.8 and all((pc.x - x) ** 2 + (pc.y - y) ** 2 > (d.cable + d.tornillo) ** 2
                                               for x, y in res.puntos_separadores):
                quitar.append(cilindro(pc.x, pc.y, d.cable / 2, -1, d.fondo + 1))
                res.puntos_cable = [(pc.x, pc.y)]
        if not res.puntos_separadores and huecos:
            av.append(f"'{c}': no hay sitio para separadores en la trasera; fíjala con varilla roscada o adhesivo.")
        solidos.append(("trasera", trasera - unir(quitar)))
        materiales["trasera"] = "difusor"
        if p - d.frente - d.fondo < 2 * d.encaje + 2:
            raise ErrorEntrada(f"'{c}': profundidad insuficiente para frente y trasera con faldón.")

    elif d.estructura == "halo":
        cuerpo = prisma(forma, 0, p) - prisma(hueco, d.frente, p + 1)
        macizos, agujeros, res.puntos_separadores = _separadores(huecos, d, av, c)
        cuerpo = unir([cuerpo, *macizos]) - unir(agujeros)
        solidos.append(("cuerpo", cuerpo))
        montajes["cuerpo"] = voltear(p)
        _comprobar_led(huecos, d, av, c)

    elif d.estructura == "neon":
        ranura = ranura_neon(forma, d)
        g = profundidad_ranura_neon(d)
        base_forma = multipoligono(unary_union([forma, ranura]).buffer(d.neon_borde, join_style=1))
        base = prisma(base_forma, 0, p) - prisma(ranura, p - g, p + 1)
        # Paso de cable por el punto más bajo del canal (donde empieza el neón).
        from shapely.geometry import Point
        clave = (lambda q: (-q[0] + 0.0 * q[1])) if getattr(letra, "salida", "") == "fin" else (lambda q: (q[1], q[0]))
        if getattr(letra, "salida", "") == "inicio":
            clave = lambda q: q[0]  # noqa: E731
        borde = min((pt for g_ in ranura.geoms for pt in g_.exterior.coords), key=clave)
        punto = _mas_cercano(multipoligono(ranura.buffer(-0.5)), Point(borde))
        if d.cable > 0 and getattr(letra, "salida", "") != "no":
            base -= cilindro(punto.x, punto.y, min(d.cable, d.neon_ancho) / 2, -1, p)
            res.puntos_cable = [(punto.x, punto.y)]
        libres = multipoligono(base_forma.difference(ranura.buffer(4.0)))
        if d.fijacion != "ninguna":
            pts = [(x, y) for x, y, _ in _puntos_fijacion(poligonos(libres), AVELLANADO_D / 2 + 1.0)]
            quitar = []
            for x, y in pts:
                quitar.append(cilindro(x, y, PASANTE_D / 2, -1, p + 1))
                h = min(p - 1.0, (AVELLANADO_D - PASANTE_D) / 2)
                quitar.append(m3d.Manifold.cylinder(h + 0.01, PASANTE_D / 2, AVELLANADO_D / 2, 48).translate([x, y, p - h]))
            base -= unir(quitar)
            res.puntos_fijacion = pts
        solidos.append(("base", base))
        largo = ranura.boundary.length / 2 / 1000.0  # el canal tiene dos bordes: su línea central ≈ mitad
        res.led = {"metros": round(largo, 3), "filas": 1, "separacion_mm": 0.0, "montaje": "neón flex en el canal"}
        res.metros_led = res.led["metros"]
        tubo = prisma(multipoligono(ranura.buffer(-max(d.holgura, 0.2))), p - g, p - g + d.neon_alto)
        res.visual.append(("neon", a_trimesh(tubo)))
        plantilla_forma = base_forma
        if g < d.neon_alto * 0.5:
            av.append(f"'{c}': canal de {g:.1f} mm para un neón de {d.neon_alto:g} mm de alto: sujétalo con silicona "
                      "o sube la profundidad de la base.")

    if d.estructura in ("caja", "frontal", "lateral", "halo", "doble"):
        res.led = plan_led(huecos, d)
        res.metros_led = res.led.get("metros", 0.0)

    if retoques:
        solidos = [(rol, retoques[rol](sol) if rol in retoques else sol) for rol, sol in solidos]
    finalizar(res, letra, d, plantilla_forma, hueco, solidos, puntos_clave(huecos, d) + res.puntos_fijacion,
              materiales, montajes)
    return res


def _mas_cercano(geom, punto):
    from shapely.ops import nearest_points
    return nearest_points(geom, punto)[0]


def finalizar(res: ResultadoLetra, letra: Letra, d: Diseno, forma: MultiPolygon, hueco: MultiPolygon,
              solidos: list, puntos: list, materiales: dict | None = None, montajes: dict | None = None) -> None:
    """Malla los sólidos, divide lo que no cabe en la cama y comprueba cada pieza."""
    materiales, montajes = materiales or {}, montajes or {}
    c, av = letra.caracter, res.avisos
    inicio = len(res.piezas)
    cabe, _, (w, h) = _cabe_en_cama(forma, d.cama)
    if getattr(letra, "cortes", ()):
        _dividir(res, letra, d, forma, hueco, solidos, puntos, forzado=True)
    elif cabe:
        for rol, solido in solidos:
            res.piezas.append(_pieza(letra, rol, solido, forma))
    else:
        if not getattr(d, "dividir", True):
            raise ErrorEntrada(
                f"'{c}' mide {w:.0f} × {h:.0f} mm y no cabe en la cama {d.cama[0]:g} × {d.cama[1]:g} mm. "
                "Activa la división automática o reduce la altura."
            )
        _dividir(res, letra, d, forma, hueco, solidos, puntos)

    for pieza in res.piezas[inicio:]:
        pieza.material = materiales.get(pieza.rol, pieza.material)
        if pieza.rol == "empalme":
            pieza.material = "opaco"
            pieza.montaje = _montaje_empalme(d)
        elif pieza.rol in montajes:
            pieza.montaje = montajes[pieza.rol]
        cabe, girada, (w, h) = _cabe_en_cama(pieza.huella, d.cama)
        if not cabe and getattr(letra, "cortes", ()):
            raise ErrorEntrada(
                f"La pieza «{pieza.parte}» mide {w:.0f} × {h:.0f} mm y no cabe en la cama "
                f"{d.cama[0]:g} × {d.cama[1]:g} mm: pon menos letras por pieza o reduce la altura."
            )
        if not cabe:
            raise ErrorEntrada(
                f"La pieza {pieza.archivo} mide {w:.0f} × {h:.0f} mm y no cabe en la cama "
                f"{d.cama[0]:g} × {d.cama[1]:g} mm; reduce la altura."
            )
        if girada:
            av.append(f"{pieza.archivo}: solo cabe girada en la cama; en Bambu Studio usa 'Orientar automáticamente'.")


def _montaje_empalme(d: Diseno) -> np.ndarray:
    if d.estructura == "halo":
        return subir(d.profundidad - d.frente - EMPALME_GROSOR)
    if d.estructura == "doble":
        return subir(d.fondo + d.encaje + 0.5)
    return subir(d.fondo)


def puntos_clave(huecos: list[Polygon], d: Diseno) -> list[tuple[float, float]]:
    """Dónde van el agujero de cable y los separadores (para no cortar por ahí)."""
    pts = []
    if huecos and d.estructura in ("caja", "frontal", "lateral", "doble") and d.cable > 0:
        p, _ = _punto_mas_holgado(max(huecos, key=lambda q: q.area))
        pts.append((p.x, p.y))
    if d.estructura in ("halo", "doble"):
        for h in huecos:
            for region in _mitades(h):
                p, _ = _punto_mas_holgado(region)
                pts.append((p.x, p.y))
    return pts


EMPALME_GROSOR = 2.4
BANDA_GROSOR = 2.0  # doble: el empalme es una banda pegada a la pared interior (no hay fondo)


TAPAS = ("frente", "trasera", "difusor", "mascara")


def _plan_tapas(forma, plan, d):
    """Cortes de las tapas desplazados respecto a los del cuerpo: cada tapa cruza la junta y
    traba las dos piezas (si las tapas siguen cabiendo en la cama)."""
    from .division import corte_estrecho, plan_forzado
    xs = plan.cortes
    nuevos = []
    for k, x in enumerate(xs):
        limite = xs[k + 1] - 15 if k + 1 < len(xs) else forma.bounds[2] - 15
        if limite - x < 20:
            return None
        nuevos.append(corte_estrecho(forma, x + 12, min(x + 45, limite)))
    tapas = plan_forzado(forma, nuevos, plan.nombres, False, d.holgura)
    for region in tapas.regiones:
        if not _cabe_en_cama(multipoligono(forma.intersection(region)), d.cama)[0]:
            return None
    return tapas


def _dividir(res, letra, d, forma, hueco, solidos, puntos, forzado=False):
    from shapely.geometry import Point

    from .division import empalmes, plan_forzado, planificar
    macizo = d.estructura in ("maciza", "neon") or not res.hueca
    if forzado:
        plan = plan_forzado(forma, list(letra.cortes), list(letra.partes), macizo, d.holgura)
    else:
        plan = planificar(forma, d.cama, macizo, d.holgura, puntos)
    tapas = _plan_tapas(forma, plan, d) if forzado and not macizo else None
    alto = d.profundidad + d.separacion + 60
    for rol, solido in solidos:
        p_rol = tapas if (tapas is not None and rol in TAPAS) else plan
        for nombre, region in zip(p_rol.nombres, p_rol.regiones_hembra):
            corte = prisma(region, -30, alto)
            parte = solido ^ corte
            if parte.is_empty() or parte.volume() < 1.0:
                continue
            huella = multipoligono(forma.intersection(region))
            res.piezas.append(_pieza(letra, rol, parte, huella, nombre))
    if tapas is not None:
        res.avisos.append(f"'{letra.caracter}': las tapas van desplazadas respecto a las juntas del cuerpo "
                          "(cada tapa cruza la junta y traba las dos piezas).")
    if not macizo:
        libres = [Point(x, y).buffer(max(d.cable / 2, R_SEPARADOR) + 1.5) for x, y in puntos]
        for (union, _), zona in zip(plan.juntas, empalmes(hueco, plan.juntas, d.holgura)):
            for q in libres:
                zona = multipoligono(zona.difference(q))
            if d.estructura == "doble":  # banda pegada a la pared interior, entre los dos faldones
                zona = multipoligono(zona.difference(hueco.buffer(-(BANDA_GROSOR + d.holgura), **UNION)))
                zona = MultiPolygon([q for q in poligonos(zona) if q.area > 8])
                alto_banda = d.profundidad - d.frente - d.fondo - 2 * d.encaje - 1.0
                solido = prisma(zona, 0, alto_banda) if alto_banda > 3 else m3d.Manifold()
            else:
                solido = prisma(zona, 0, EMPALME_GROSOR)
            if zona.is_empty or solido.is_empty():
                res.avisos.append(f"'{letra.caracter}': la junta {union} no tiene sitio para empalme; pégala con refuerzo.")
                continue
            res.piezas.append(_pieza(letra, "empalme", solido, zona, union))
    res.cortes = plan.cortes
    res.cortes_y = plan.cortes_y
    res.juntas = [tuple(map(tuple, seg.coords)) for _, seg in plan.juntas]
    tipo = "cola de milano" if macizo else "corte recto + placa de empalme interior"
    if forzado:
        res.avisos.append(f"'{letra.caracter}': {len(plan.nombres)} piezas ({', '.join(plan.nombres)}) unidas con {tipo}.")
        return
    donde = []
    if plan.cortes:
        donde.append("x = " + ", ".join(f"{x:.0f}" for x in plan.cortes))
    if plan.cortes_y:
        donde.append("y = " + ", ".join(f"{y:.0f}" for y in plan.cortes_y))
    res.avisos.append(f"'{letra.caracter}': dividida en {len(plan.nombres)} partes ({tipo}) en " + " · ".join(donde) + " mm.")


def _pieza(letra: Letra, rol: str, solido: m3d.Manifold, huella: MultiPolygon, parte: str = "") -> Pieza:
    if solido.is_empty():
        raise ErrorGeometria(f"La pieza {rol} de '{letra.caracter}' quedó vacía.")
    malla = a_trimesh(solido)
    if not (malla.is_watertight and malla.is_winding_consistent and malla.is_volume):
        raise ErrorGeometria(f"La pieza {rol} de '{letra.caracter}' no es un sólido cerrado.")
    return Pieza(letra, rol, malla, huella, parte)
