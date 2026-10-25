"""Letra maciza extruida → malla cerrada → STL.

Orientación: la cara de la letra queda en el plano XY (apoyada en la cama) y
la profundidad crece en Z. Unidades: milímetros (Bambu Studio interpreta STL en mm).
"""
from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import trimesh
from shapely.geometry import MultiPolygon

from .contornos import contorno_letra
from .errores import ErrorEntrada, ErrorGeometria
from .fuentes import FUENTE_POR_DEFECTO, obtener_fuente

# Límites alineados con los campos de index.html.
ALTURA_MIN, ALTURA_MAX = 20.0, 1500.0
PROFUNDIDAD_MIN, PROFUNDIDAD_MAX = 5.0, 250.0

# Bambu Lab A2L: 330 × 320 × 325 mm nominales. XY con margen hipotético de
# 5 mm por lado (config/PERFIL_A2L_PETG.md). Pendiente de calibrar.
CAMA_UTIL_MM = (320.0, 310.0, 325.0)
BOQUILLA_MM = 0.4


@dataclass(frozen=True)
class Parametros:
    letra: str
    altura_mm: float
    profundidad_mm: float
    fuente: str = FUENTE_POR_DEFECTO
    tolerancia_mm: float = 0.05
    cama_mm: tuple[float, float, float] = CAMA_UTIL_MM


@dataclass
class Informe:
    letra: str
    fuente: str
    licencia_fuente: str
    ancho_mm: float
    alto_mm: float
    profundidad_mm: float
    volumen_mm3: float
    area_cara_mm2: float
    cuerpos: int
    agujeros: int
    triangulos: int
    estanca: bool
    advertencias: list[str] = field(default_factory=list)

    def como_texto(self) -> str:
        lineas = [
            f"Letra: {self.letra}  ·  Fuente: {self.fuente} ({self.licencia_fuente})",
            f"Medidas: {self.ancho_mm:.2f} × {self.alto_mm:.2f} × {self.profundidad_mm:.2f} mm (X × Y × Z)",
            f"Volumen: {self.volumen_mm3 / 1000:.2f} cm³  ·  Cara: {self.area_cara_mm2:.1f} mm²",
            f"Cuerpos: {self.cuerpos}  ·  Agujeros interiores: {self.agujeros}  ·  Triángulos: {self.triangulos}",
            f"Malla cerrada (manifold): {'sí' if self.estanca else 'NO'}",
        ]
        lineas += [f"AVISO: {a}" for a in self.advertencias]
        return "\n".join(lineas)


def _numero(nombre: str, valor, minimo: float, maximo: float) -> float:
    try:
        v = float(valor)
    except (TypeError, ValueError):
        raise ErrorEntrada(f"{nombre} debe ser un número en mm.") from None
    if not math.isfinite(v) or not (minimo <= v <= maximo):
        raise ErrorEntrada(f"{nombre} debe estar entre {minimo:g} y {maximo:g} mm (recibido {valor}).")
    return v


def validar(p: Parametros) -> Parametros:
    if not isinstance(p.letra, str):
        raise ErrorEntrada("La letra debe ser texto.")
    letra = unicodedata.normalize("NFC", p.letra)
    if len(letra) != 1:
        raise ErrorEntrada("Este prototipo genera exactamente UN carácter por pieza.")
    if letra.isspace() or unicodedata.category(letra).startswith("C"):
        raise ErrorEntrada("El carácter no es imprimible.")
    altura = _numero("Altura", p.altura_mm, ALTURA_MIN, ALTURA_MAX)
    profundidad = _numero("Profundidad", p.profundidad_mm, PROFUNDIDAD_MIN, PROFUNDIDAD_MAX)
    tolerancia = _numero("Tolerancia de curvas", p.tolerancia_mm, 0.005, 0.5)
    return Parametros(letra, altura, profundidad, p.fuente, tolerancia, p.cama_mm)


def _comprobar_trazos(cara: MultiPolygon) -> list[str]:
    """Detecta partes más finas que la boquilla (desaparecen al erosionar BOQUILLA/2)."""
    erosion = cara.buffer(-BOQUILLA_MM / 2)
    restante = len(getattr(erosion, "geoms", [erosion])) if not erosion.is_empty else 0
    perdida = 1 - (erosion.area / cara.area if cara.area else 0)
    avisos = []
    if restante < len(cara.geoms):
        avisos.append(f"Hay trazos más finos que la boquilla de {BOQUILLA_MM} mm; no se imprimirán.")
    elif perdida > 0.5:
        avisos.append("Trazos muy finos para la altura elegida; revisar en Bambu Studio.")
    return avisos


def generar_letra(params: Parametros) -> tuple[trimesh.Trimesh, Informe]:
    p = validar(params)
    fuente = obtener_fuente(p.fuente)
    cara = contorno_letra(fuente.ruta, p.letra, p.altura_mm, p.tolerancia_mm)

    ancho, alto = cara.bounds[2], cara.bounds[3]
    cx, cy, cz = p.cama_mm
    cabe = (ancho <= cx and alto <= cy) or (ancho <= cy and alto <= cx)
    if not cabe or p.profundidad_mm > cz:
        raise ErrorEntrada(
            f"La letra mide {ancho:.1f} × {alto:.1f} × {p.profundidad_mm:.1f} mm y no cabe en la cama útil "
            f"{cx:g} × {cy:g} × {cz:g} mm. La división en piezas aún no está implementada."
        )

    piezas = [trimesh.creation.extrude_polygon(poly, height=p.profundidad_mm) for poly in cara.geoms]
    malla = trimesh.util.concatenate(piezas)
    malla.merge_vertices()
    malla.fix_normals()

    if not (malla.is_watertight and malla.is_winding_consistent and malla.is_volume):
        raise ErrorGeometria("La malla generada no es cerrada/manifold; no se exporta.")
    esperado = cara.area * p.profundidad_mm
    if not math.isclose(malla.volume, esperado, rel_tol=1e-6):
        raise ErrorGeometria(f"Volumen {malla.volume:.3f} ≠ área·profundidad {esperado:.3f}.")

    avisos = _comprobar_trazos(cara)
    if not ancho <= cx or not alto <= cy:
        avisos.append("Cabe solo girada 90° en la cama.")

    extension = malla.extents
    informe = Informe(
        letra=p.letra,
        fuente=fuente.nombre,
        licencia_fuente=fuente.licencia,
        ancho_mm=float(extension[0]),
        alto_mm=float(extension[1]),
        profundidad_mm=float(extension[2]),
        volumen_mm3=float(malla.volume),
        area_cara_mm2=float(cara.area),
        cuerpos=len(cara.geoms),
        agujeros=sum(len(poly.interiors) for poly in cara.geoms),
        triangulos=len(malla.faces),
        estanca=bool(malla.is_watertight),
        advertencias=avisos,
    )
    return malla, informe


def exportar_stl(malla: trimesh.Trimesh, destino: str | Path) -> Path:
    destino = Path(destino)
    if destino.suffix.lower() != ".stl":
        raise ErrorEntrada("El archivo de salida debe terminar en .stl")
    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = trimesh.exchange.stl.export_stl(malla)  # binario, sin marca de tiempo → reproducible
    destino.write_bytes(datos)
    return destino


__all__ = ["Parametros", "Informe", "generar_letra", "exportar_stl", "validar"]
