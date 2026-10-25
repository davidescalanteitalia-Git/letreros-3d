"""Reparto de las piezas en camas de impresión y exportación 3MF / DXF.

- Cada pieza se gira sobre la cama para ocupar su rectángulo mínimo y se
  coloca por estantes (de mayor a menor alto) dejando SEPARACION mm entre piezas.
- Las camas se separan por material: «opaco» (cuerpos, empalmes, placa) y
  «difusor» (frentes translúcidos de la frontal), porque cada cama se imprime
  con un solo filamento.
- El 3MF se escribe a mano (3MF Core 1.x, unidades mm): un objeto con nombre por
  pieza, ya colocado; Bambu Studio lo abre como proyecto de una placa.
- El DXF (R2010, mm) tiene los contornos 1:1 en posición de montaje, para cortar
  frentes de metacrilato, vinilo o plantillas.

Diseño propio de Letreros 3D Studio.
"""
from __future__ import annotations

import io
import math
import zipfile
from dataclasses import dataclass, field
from xml.sax.saxutils import quoteattr

import numpy as np
from shapely.geometry import MultiPoint

SEPARACION = 6.0  # mm entre piezas en la cama
MARGEN_REAL = 5.0  # la cama útil (320 × 310) está centrada en la física (330 × 320)
MATERIAL_POR_ROL = {"frente": "difusor"}
NOMBRE_MATERIAL = {"opaco": "opaco (cuerpos, empalmes, placa)", "difusor": "difusor (frentes translúcidos)"}


@dataclass
class Colocacion:
    pieza: object  # estructuras.Pieza
    matriz: np.ndarray  # 4×4, de la pieza tal cual a su sitio en la cama
    ancho: float
    alto: float
    x: float
    y: float
    girada: bool = False


@dataclass
class Cama:
    numero: int
    material: str
    colocaciones: list[Colocacion] = field(default_factory=list)

    @property
    def archivo(self) -> str:
        return f"cama-{self.numero:02d}-{self.material}.3mf"

    @property
    def peso_g(self) -> float:
        return sum(c.pieza.peso_g for c in self.colocaciones)


def material(pieza) -> str:
    return MATERIAL_POR_ROL.get(pieza.rol, "opaco")


def _rot_z(angulo: float) -> np.ndarray:
    c, s = math.cos(angulo), math.sin(angulo)
    m = np.eye(4)
    m[:2, :2] = [[c, -s], [s, c]]
    return m


def _tras(x: float, y: float) -> np.ndarray:
    m = np.eye(4)
    m[0, 3], m[1, 3] = x, y
    return m


def _alinear(malla, cx: float, cy: float) -> tuple[np.ndarray, float, float]:
    """Deja la huella apoyada en (0, 0), recta (0° o 90°). Solo si así no cabe en la
    cama, la gira al ángulo de su rectángulo mínimo."""
    xy = malla.vertices[:, :2]
    angulo = 0.0
    w0, h0 = np.ptp(xy[:, 0]), np.ptp(xy[:, 1])
    if not ((w0 <= cx and h0 <= cy) or (h0 <= cx and w0 <= cy)):
        rect = MultiPoint(xy[::max(1, len(xy) // 4000)]).convex_hull.minimum_rotated_rectangle
        if rect.geom_type == "Polygon":
            cs = list(rect.exterior.coords)
            angulo = -math.atan2(cs[1][1] - cs[0][1], cs[1][0] - cs[0][0])
    m = _rot_z(angulo)
    q = xy @ m[:2, :2].T
    m = _tras(-q[:, 0].min(), -q[:, 1].min()) @ m
    w, h = float(np.ptp(q[:, 0])), float(np.ptp(q[:, 1]))
    if h > w and h <= cx:  # estantes: mejor piezas apaisadas
        m = _tras(h, 0) @ _rot_z(math.pi / 2) @ m
        w, h = h, w
    return m, w, h


def distribuir(piezas, cama, separacion: float = SEPARACION) -> list[Cama]:
    """Reparte las piezas en camas por material. `cama` = (x, y, z) útil en mm."""
    cx, cy = float(cama[0]), float(cama[1])
    camas: list[Cama] = []
    for mat in ("opaco", "difusor"):
        items = []
        for p in piezas:
            if material(p) != mat:
                continue
            m, w, h = _alinear(p.malla, cx, cy)
            girada = False
            if w > cx + 1e-6 or h > cy + 1e-6:  # solo cabe de pie
                m = _tras(h, 0) @ _rot_z(math.pi / 2) @ m
                w, h, girada = h, w, True
            items.append((p, m, w, h, girada))
        items.sort(key=lambda it: (-it[3], -it[2], it[0].archivo))
        abiertas: list[tuple[Cama, list[list[float]]]] = []  # (cama, estantes [y, alto, x_libre])
        for p, m, w, h, girada in items:
            sitio = None
            for c, estantes in abiertas:
                for e in estantes:
                    if h <= e[1] + 1e-6 and e[2] + w <= cx + 1e-6:
                        sitio = (c, e[2], e[0])
                        e[2] += w + separacion
                        break
                if sitio:
                    break
                y_libre = estantes[-1][0] + estantes[-1][1] + separacion
                if y_libre + h <= cy + 1e-6:
                    estantes.append([y_libre, h, w + separacion])
                    sitio = (c, 0.0, y_libre)
                    break
            if sitio is None:
                c = Cama(0, mat)
                abiertas.append((c, [[0.0, h, w + separacion]]))
                sitio = (c, 0.0, 0.0)
            c, x, y = sitio
            matriz = _tras(x + MARGEN_REAL, y + MARGEN_REAL) @ m
            c.colocaciones.append(Colocacion(p, matriz, w, h, x, y, girada))
        camas += [c for c, _ in abiertas]
    for i, c in enumerate(camas, start=1):
        c.numero = i
    return camas


# --------------------------------------------------------------------------- 3MF

_TIPOS = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          '</Types>')
_RELS = ('<?xml version="1.0" encoding="UTF-8"?>\n'
         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
         'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')


def modelo_3mf(objetos: list[tuple[str, np.ndarray, np.ndarray]], titulo: str = "") -> bytes:
    """3MF con un objeto por (nombre, vértices N×3, caras M×3) ya colocados, en mm."""
    partes = ['<?xml version="1.0" encoding="UTF-8"?>\n'
              '<model unit="millimeter" xml:lang="es-ES" '
              'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
              '<metadata name="Application">Letreros 3D Studio</metadata>']
    if titulo:
        partes.append(f"<metadata name=\"Title\">{titulo.replace('&', '&amp;').replace('<', '&lt;')}</metadata>")
    partes.append("<resources>")
    for i, (nombre, v, f) in enumerate(objetos, start=1):
        partes.append(f'<object id="{i}" type="model" name={quoteattr(nombre)}><mesh><vertices>')
        partes.append("".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in v))
        partes.append("</vertices><triangles>")
        partes.append("".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in f))
        partes.append("</triangles></mesh></object>")
    partes.append("</resources><build>")
    partes += [f'<item objectid="{i}"/>' for i in range(1, len(objetos) + 1)]
    partes.append("</build></model>")
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, datos in (("[Content_Types].xml", _TIPOS), ("_rels/.rels", _RELS),
                              ("3D/3dmodel.model", "".join(partes))):
            info = zipfile.ZipInfo(nombre, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, datos.encode("utf-8"))
    return salida.getvalue()


def cama_3mf(c: Cama, titulo: str = "") -> bytes:
    objetos = []
    for col in c.colocaciones:
        malla = col.pieza.malla
        v = np.c_[malla.vertices, np.ones(len(malla.vertices))] @ col.matriz.T
        objetos.append((col.pieza.archivo[:-4], v[:, :3], np.asarray(malla.faces)))
    return modelo_3mf(objetos, titulo)


def leer_3mf(datos: bytes) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """Lector mínimo (para pruebas): [(nombre, vértices, caras)]."""
    import xml.etree.ElementTree as ET
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        raiz = ET.fromstring(z.read("3D/3dmodel.model"))
    res = []
    for o in raiz.iterfind(".//m:object", ns):
        v = np.array([[float(e.get(k)) for k in "xyz"] for e in o.iterfind(".//m:vertex", ns)])
        f = np.array([[int(e.get(k)) for k in ("v1", "v2", "v3")] for e in o.iterfind(".//m:triangle", ns)])
        res.append((o.get("name"), v, f))
    return res


# --------------------------------------------------------------------------- DXF

def contornos_dxf(proyecto) -> bytes:
    """DXF 1:1 en mm con los contornos en posición de montaje (capas LETRAS, PLACA, CORTES, CABLE)."""
    import ezdxf

    doc = ezdxf.new("R2010", setup=False)
    doc.units = ezdxf.units.MM
    doc.header["$MEASUREMENT"] = 1
    for nombre, color in (("LETRAS", 5), ("PLACA", 8), ("CORTES", 1), ("CABLE", 3)):
        doc.layers.add(nombre, color=color)
    msp = doc.modelspace()
    minx, miny, _, _ = proyecto.medidas()
    for r in proyecto.letras:
        capa = "PLACA" if (r.letra.indice == 0 and r.letra.caracter == "base") else "LETRAS"
        for poly in r.letra.forma.geoms:
            for anillo in (poly.exterior, *poly.interiors):
                pts = [(x - minx, y - miny) for x, y in list(anillo.coords)[:-1]]
                msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": capa})
        for (xa, ya), (xb, yb) in r.juntas:
            msp.add_line((xa - minx, ya - miny), (xb - minx, yb - miny), dxfattribs={"layer": "CORTES"})
        for x, y in r.puntos_cable:
            msp.add_circle((x - minx, y - miny), proyecto.diseno.cable / 2, dxfattribs={"layer": "CABLE"})
    texto = io.StringIO()
    doc.write(texto)
    return texto.getvalue().encode("utf-8")
