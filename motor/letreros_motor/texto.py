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

from .contornos import altura_mayuscula_unidades, glifo_mm
from .errores import ErrorEntrada

LONGITUD_MAX = 40


@dataclass
class Letra:
    indice: int  # 1, 2, 3… solo letras con contorno (los espacios no cuentan)
    caracter: str
    forma: MultiPolygon  # en mm, posición final en el letrero, línea base y=0
    origen_x: float  # x del origen tipográfico, para el mapa de montaje

    @property
    def codigo(self) -> str:
        return f"{self.indice:02d}-{nombre_seguro(self.caracter)}"


def nombre_seguro(c: str) -> str:
    base = "".join(ch for ch in unicodedata.normalize("NFD", c) if not unicodedata.combining(ch))
    base = "".join(ch for ch in base if ch.isascii() and ch.isalnum())
    return base or f"u{ord(c):04X}"


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


def maquetar(texto: str, ruta_fuente, altura_mayuscula_mm: float, espaciado_mm: float = 0.0,
             tolerancia_mm: float = 0.05) -> list[Letra]:
    """Coloca cada carácter según el avance de la fuente + `espaciado_mm` extra.

    No aplica pares de kerning (Montserrat los guarda en GPOS); para letras
    corpóreas que se montan sueltas el espaciado final se decide al montar.
    """
    t = normalizar_texto(texto)
    escala = altura_mayuscula_mm / altura_mayuscula_unidades(ruta_fuente)
    letras: list[Letra] = []
    x = 0.0
    for ch in t:
        forma, avance = glifo_mm(ruta_fuente, ch, escala, tolerancia_mm)
        if not forma.is_empty:
            colocada = affinity.translate(forma, xoff=x)
            letras.append(Letra(len(letras) + 1, ch, MultiPolygon(list(colocada.geoms)), x))
        x += avance + espaciado_mm
    if not letras:
        raise ErrorEntrada("El texto no contiene ningún carácter con contorno imprimible.")
    return letras
