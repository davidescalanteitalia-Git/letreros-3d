"""Maquetación de un texto (una o varias líneas) con medidas reales.

Convención del oficio: la altura del letrero es la de la MAYÚSCULA (A, H, M).
Todas las letras comparten escala: la O y la C sobresalen lo que dicta la
fuente, las minúsculas, acentos y descendentes miden lo que les corresponde.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from shapely import affinity
from shapely.geometry import MultiPolygon

from pathlib import Path

from .contornos import _tt, altura_mayuscula_unidades, glifo_por_nombre_mm
from .errores import ErrorEntrada

LONGITUD_MAX = 40  # caracteres por línea
LINEAS_MAX = 4
ALINEACIONES = {"izquierda": 0.0, "centro": 0.5, "derecha": 1.0}


@dataclass
class Letra:
    indice: int  # 1, 2, 3… solo letras con contorno (los espacios no cuentan)
    caracter: str
    forma: MultiPolygon  # en mm, posición final en el letrero, línea base y=0
    origen_x: float  # x del origen tipográfico, para el mapa de montaje
    palabra: int = 0  # 0, 1, 2… según los espacios y saltos de línea del texto
    linea: int = 0  # 0 = primera línea (arriba)

    @property
    def codigo(self) -> str:
        return f"{self.indice:02d}-{nombre_seguro(self.caracter)}"


def nombre_seguro(c: str) -> str:
    base = "".join(ch for ch in unicodedata.normalize("NFD", c) if not unicodedata.combining(ch))
    base = "".join(ch for ch in base if ch.isascii() and ch.isalnum())
    return base or "".join(f"u{ord(ch):04X}" for ch in c)


def normalizar_texto(texto: str) -> str:
    """Texto limpio. Admite hasta LINEAS_MAX líneas separadas por saltos de línea."""
    if not isinstance(texto, str):
        raise ErrorEntrada("El texto debe ser una cadena.")
    t = unicodedata.normalize("NFC", texto).replace("\r\n", "\n").replace("\r", "\n")
    lineas = [" ".join(l.split(" ")).strip() for l in t.split("\n")]
    lineas = [l for l in lineas if l]
    if not lineas:
        raise ErrorEntrada("El texto está vacío.")
    if len(lineas) > LINEAS_MAX:
        raise ErrorEntrada(f"Máximo {LINEAS_MAX} líneas por letrero (recibidas {len(lineas)}).")
    for l in lineas:
        if "\t" in l:
            raise ErrorEntrada("El texto no admite tabuladores.")
        if len(l) > LONGITUD_MAX:
            raise ErrorEntrada(f"Máximo {LONGITUD_MAX} caracteres por línea (la línea «{l[:12]}…» tiene {len(l)}).")
        for ch in l:
            if ch != " " and (ch.isspace() or unicodedata.category(ch).startswith("C")):
                raise ErrorEntrada(f"Carácter no imprimible en el texto: U+{ord(ch):04X}.")
    return "\n".join(lineas)


def _datos_fuente(fuente) -> bytes:
    from .fuentes import FUENTES, binario
    if isinstance(fuente, str) and fuente in FUENTES:
        return binario(fuente)
    return Path(fuente).read_bytes()


def _componer_linea(t: str, fuente, escala: float, espaciado_mm: float, tolerancia_mm: float):
    """Glifos de una línea con HarfBuzz: [(caracteres, forma, origen_x, es_espacio)] con la base en y=0."""
    import uharfbuzz as hb

    tt = _tt(fuente)
    orden = tt.getGlyphOrder()
    buf = hb.Buffer()
    buf.add_str(t)
    buf.guess_segment_properties()
    hb.shape(hb.Font(hb.Face(hb.Blob(_datos_fuente(fuente)))), buf, {"kern": True, "liga": True, "calt": True})
    clusters = sorted({i.cluster for i in buf.glyph_infos}) + [len(t)]
    glifos, x = [], 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        siguiente = clusters[clusters.index(info.cluster) + 1]
        caracteres = t[info.cluster:siguiente]
        if info.codepoint == 0:
            raise ErrorEntrada(f"La fuente no contiene el carácter '{caracteres}'.")
        forma = glifo_por_nombre_mm(fuente, orden[info.codepoint], escala, tolerancia_mm)
        colocada = None
        if not forma.is_empty:
            colocada = affinity.translate(forma, xoff=x + pos.x_offset * escala, yoff=pos.y_offset * escala)
        glifos.append((caracteres, colocada, x))
        x += pos.x_advance * escala + espaciado_mm
    return glifos


def maquetar(texto: str, fuente, altura_mayuscula_mm: float, espaciado_mm: float = 0.0,
             tolerancia_mm: float = 0.05, interlineado: float = 1.4, alineacion: str = "centro") -> list[Letra]:
    """Compone el texto con HarfBuzz (kerning, ligaduras y formas contextuales
    de las manuscritas) y devuelve una Letra por glifo con contorno, ya colocada.

    `fuente` es la clave de una fuente registrada o la ruta a un .ttf estático.
    `espaciado_mm` se suma al avance de cada glifo (0 = espaciado de la fuente).
    Varias líneas: la base de cada línea baja `interlineado` × altura de mayúscula;
    `alineacion` (izquierda | centro | derecha) se aplica al ancho visible de cada línea.
    Con una sola línea el resultado es idéntico al de versiones anteriores.
    """
    if alineacion not in ALINEACIONES:
        raise ErrorEntrada(f"Alineación '{alineacion}' desconocida. Opciones: {', '.join(ALINEACIONES)}.")
    t = normalizar_texto(texto)
    escala = altura_mayuscula_mm / altura_mayuscula_unidades(fuente)
    lineas = [_componer_linea(l, fuente, escala, espaciado_mm, tolerancia_mm) for l in t.split("\n")]

    def tinta(glifos):
        formas = [f for _, f, _ in glifos if f is not None]
        if not formas:
            return None
        return min(f.bounds[0] for f in formas), max(f.bounds[2] for f in formas)

    limites = [tinta(g) for g in lineas]
    validos = [b for b in limites if b]
    if not validos:
        raise ErrorEntrada("El texto no contiene ningún carácter con contorno imprimible.")
    izquierda = min(b[0] for b in validos)
    mas_ancha = max(b[1] - b[0] for b in validos)
    f = ALINEACIONES[alineacion]

    letras: list[Letra] = []
    palabra = 0
    for n, (glifos, lim) in enumerate(zip(lineas, limites)):
        if lim is None:
            continue
        dx = izquierda + (mas_ancha - (lim[1] - lim[0])) * f - lim[0] if len(lineas) > 1 else 0.0
        dy = -n * interlineado * altura_mayuscula_mm
        if letras and letras[-1].palabra == palabra:
            palabra += 1  # cada línea empieza palabra nueva
        for caracteres, forma, x in glifos:
            if caracteres.isspace():
                palabra += 1 if letras and letras[-1].palabra == palabra else 0
            if forma is None:
                continue
            colocada = affinity.translate(forma, xoff=dx, yoff=dy) if (dx or dy) else forma
            letras.append(Letra(len(letras) + 1, caracteres, MultiPolygon(list(colocada.geoms)), x + dx, palabra, n))
    return letras
