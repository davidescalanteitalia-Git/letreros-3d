"""Puente entre polígonos 2D (shapely) y sólidos 3D (manifold3d).

manifold3d garantiza que toda unión o resta produce un sólido cerrado y
orientable (manifold), condición necesaria para que el laminador no tenga que
reparar nada.
"""
from __future__ import annotations

import manifold3d as m3d
import numpy as np
import trimesh
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

SEGMENTOS_CIRCULO = 48


def poligonos(geom: BaseGeometry) -> list[Polygon]:
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    return [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon) and not g.is_empty]


def multipoligono(geom: BaseGeometry) -> MultiPolygon:
    return MultiPolygon(poligonos(geom))


def _anillo(coords) -> np.ndarray:
    pts = np.asarray(coords, dtype=float)[:, :2]
    return pts[:-1] if len(pts) > 1 and np.allclose(pts[0], pts[-1]) else pts


def seccion(geom: BaseGeometry) -> m3d.CrossSection:
    contornos = []
    for p in poligonos(geom):
        contornos.append(_anillo(p.exterior.coords))
        contornos.extend(_anillo(i.coords) for i in p.interiors)
    if not contornos:
        return m3d.CrossSection()
    return m3d.CrossSection(contornos, m3d.FillRule.EvenOdd)


def prisma(geom: BaseGeometry, z0: float, z1: float) -> m3d.Manifold:
    """Extruye la silueta entre las alturas z0 y z1 (mm)."""
    if z1 <= z0 or geom is None or geom.is_empty:
        return m3d.Manifold()
    return seccion(geom).extrude(z1 - z0).translate([0.0, 0.0, z0])


def cilindro(x: float, y: float, radio: float, z0: float, z1: float) -> m3d.Manifold:
    if z1 <= z0 or radio <= 0:
        return m3d.Manifold()
    return m3d.Manifold.cylinder(z1 - z0, radio, radio, SEGMENTOS_CIRCULO).translate([x, y, z0])


def unir(solidos) -> m3d.Manifold:
    solidos = [s for s in solidos if not s.is_empty()]
    if not solidos:
        return m3d.Manifold()
    return m3d.Manifold.batch_boolean(solidos, m3d.OpType.Add) if len(solidos) > 1 else solidos[0]


def a_trimesh(solido: m3d.Manifold) -> trimesh.Trimesh:
    malla = solido.to_mesh()
    return trimesh.Trimesh(
        vertices=np.asarray(malla.vert_properties)[:, :3].astype(float),
        faces=np.asarray(malla.tri_verts).astype(np.int64),
        process=True,
    )
