"""Maquetación de un texto en una línea con medidas reales.

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

LONGITUD_MAX = 40


@dataclass
class Letra:
    indice: int  # 1, 2, 3… solo letras con contorno (los espacios no cuentan)
    caracter: str
    forma: MultiPolygon  # en mm, posición final en el letrero, línea base y=0
    origen_x: float  # x del origen tipográfico, para el mapa de montaje
    palabra: int = 0  # 0, 1, 2… según los espacios del texto

    @property
    def codigo(self) -> str:
        return f"{self.indice:02d}-{nombre_seguro(self.caracter)}"


def nombre_seguro(c: str) -> str:
    base = "".join(ch for ch in unicodedata.normalize("NFD", c) if not unicodedata.combining(ch))
    base = "".join(ch for ch in base if ch.isascii() and ch.isalnum())
    return base or "".join(f"u{ord(ch):04X}" for ch in c)


def normalizar_texto(texto: str) -> str:
    if not isinstance(texto, str):
        raise ErrorEntrada("El texto debe ser una cadena.")
    t = unicodedata.normalize("NFC", texto).strip()
    if not t:
        raise ErrorEntrada("El texto está vacío.")
    if any(ch in "\r\n\t" for ch in t):
        raise ErrorEntrada("Por ahora el letrero es de una sola línea (sin saltos ni tabuladores).")
    if len(t) > LONGITUD_MAX:
        raise ErrorEntrada(f"Máximo {LONGITUD_MAX} caracteres por letrero (recibidos {len(t)}).")
    for ch in t:
        if ch != " " and (ch.isspace() or unicodedata.category(ch).startswith("C")):
            raise ErrorEntrada(f"Carácter no imprimible en el texto: U+{ord(ch):04X}.")
    return t


def _datos_fuente(fuente) -> bytes:
    from .fuentes import FUENTES, binario
    if isinstance(fuente, str) and fuente in FUENTES:
        return binario(fuente)
    return Path(fuente).read_bytes()


def maquetar(texto: str, fuente, altura_mayuscula_mm: float, espaciado_mm: float = 0.0,
             tolerancia_mm: float = 0.05) -> list[Letra]:
    """Compone el texto con HarfBuzz (kerning, ligaduras y formas contextuales
    de las manuscritas) y devuelve una Letra por glifo con contorno, ya colocada.

    `fuente` es la clave de una fuente registrada o la ruta a un .ttf estático.
    `espaciado_mm` se suma al avance de cada glifo (0 = espaciado de la fuente).
    """
    import uharfbuzz as hb

    t = normalizar_texto(texto)
    escala = altura_mayuscula_mm / altura_mayuscula_unidades(fuente)
    tt = _tt(fuente)
    orden = tt.getGlyphOrder()
    buf = hb.Buffer()
    buf.add_str(t)
    buf.guess_segment_properties()
    hb.shape(hb.Font(hb.Face(hb.Blob(_datos_fuente(fuente)))), buf, {"kern": True, "liga": True, "calt": True})
    infos, posiciones = buf.glyph_infos, buf.glyph_positions
    clusters = sorted({i.cluster for i in infos}) + [len(t)]

    letras: list[Letra] = []
    x, palabra = 0.0, 0
    for info, pos in zip(infos, posiciones):
        siguiente = clusters[clusters.index(info.cluster) + 1]
        caracteres = t[info.cluster:siguiente]
        if caracteres.isspace():
            palabra += 1 if letras and letras[-1].palabra == palabra else 0
        if info.codepoint == 0:
            raise ErrorEntrada(f"La fuente no contiene el carácter '{caracteres}'.")
        forma = glifo_por_nombre_mm(fuente, orden[info.codepoint], escala, tolerancia_mm)
        if not forma.is_empty:
            colocada = affinity.translate(forma, xoff=x + pos.x_offset * escala, yoff=pos.y_offset * escala)
            letras.append(Letra(len(letras) + 1, caracteres, MultiPolygon(list(colocada.geoms)), x, palabra))
        x += pos.x_advance * escala + espaciado_mm
    if not letras:
        raise ErrorEntrada("El texto no contiene ningún carácter con contorno imprimible.")
    return letras
