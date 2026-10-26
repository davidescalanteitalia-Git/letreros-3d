"""Caja de luz: una caja para todo el texto, con la cara en dos piezas.

Diseño propio de Letreros 3D Studio:
- cuerpo: bandeja con fondo, paredes y galce superior donde apoya la cara;
  guías dobles en el fondo para pegar la tira LED en filas, paso de cable abajo
  y dos colgadores tipo ojo de cerradura en la trasera (cuelga de dos tornillos);
- difusor (translúcido): placa que apoya en el galce, con las letras en relieve;
- máscara (opaca): placa con las letras caladas; encaja sobre el difusor y las
  letras quedan a ras, iluminadas. Los «ojos» de letras como la O salen sueltos
  dentro del mismo archivo: se pegan en su sitio sobre el difusor.
Pose de impresión: cuerpo con el fondo en la cama; difusor con las letras hacia
arriba; máscara plana.
"""
from __future__ import annotations

import math

import manifold3d as m3d
from shapely.geometry import MultiPolygon, box
from shapely.ops import unary_union

from .diseno import Diseno
from .estructuras import (ResultadoLetra, UNION, finalizar, separacion_filas, subir)
from .geometria import cilindro, multipoligono, poligonos, prisma, unir
from .texto import Letra

RIEL_ANCHO, RIEL_ALTO = 1.2, 1.5
OJO_CABEZA, OJO_CUELLO, OJO_RECORRIDO = 9.0, 4.6, 10.0


def _rieles(interior: MultiPolygon, d: Diseno, z: float):
    """Filas de tira: dos rieles por fila, a lo largo de X, separadas `separacion_filas`."""
    sep = separacion_filas(d)
    zona = multipoligono(interior.buffer(-4.0, **UNION))
    if zona.is_empty or d.ancho_tira <= 0:
        return [], 0, 0.0, 0.0
    minx, miny, maxx, maxy = zona.bounds
    alto = maxy - miny
    n = max(1, math.ceil(alto / sep - 1e-9))
    paso = alto / n
    rieles, metros = [], 0.0
    for k in range(n):
        y = miny + paso * (k + 0.5)
        fila = zona.intersection(box(minx - 1, y - d.ancho_tira / 2, maxx + 1, y + d.ancho_tira / 2))
        metros += sum(g.bounds[2] - g.bounds[0] for g in poligonos(fila))
        for lado in (-1, 1):
            yc = y + lado * (d.ancho_tira / 2 + 0.4 + RIEL_ANCHO / 2)
            riel = zona.intersection(box(minx, yc - RIEL_ANCHO / 2, maxx, yc + RIEL_ANCHO / 2))
            rieles.append(prisma(riel, z - 0.3, z + RIEL_ALTO))
    return rieles, n, metros / 1000.0, paso


def _ojo_cerradura(x: float, y: float, fondo: float):
    """(refuerzo, vaciado): agujero de cabeza Ø9, ranura Ø4,6 hacia arriba y cámara para la cabeza."""
    alto_pad = fondo + 4.0
    pad = unir([cilindro(x, y + OJO_RECORRIDO * t, OJO_CABEZA / 2 + 4, 0, alto_pad) for t in (0, 0.5, 1)])
    from shapely.geometry import Point
    cabeza = Point(x, y).buffer(OJO_CABEZA / 2, 48)
    cuello = unary_union([box(x - OJO_CUELLO / 2, y, x + OJO_CUELLO / 2, y + OJO_RECORRIDO),
                          Point(x, y + OJO_RECORRIDO).buffer(OJO_CUELLO / 2, 48), cabeza])
    camara = unary_union([box(x - OJO_CABEZA / 2, y, x + OJO_CABEZA / 2, y + OJO_RECORRIDO),
                          Point(x, y + OJO_RECORRIDO).buffer(OJO_CABEZA / 2, 48), cabeza])
    vacio = unir([prisma(cuello, -1, fondo - 0.4), prisma(camara, fondo - 0.5, fondo + 3.0)])
    return pad, vacio


def construir_caja_luz(unidades: list[Letra], d: Diseno) -> ResultadoLetra:
    from .conjunto import contorno_placa

    letras = multipoligono(unary_union([u.forma for u in unidades]))
    contorno = contorno_placa(letras, d)
    caja = Letra(1, "caja", contorno, contorno.bounds[0])
    res = ResultadoLetra(caja, hueca=True)
    av = res.avisos
    p, t_cara = d.profundidad, d.frente + d.mascara
    galce = multipoligono(contorno.buffer(-d.pared, **UNION))
    interior = multipoligono(contorno.buffer(-(d.pared + d.repisa), **UNION))
    if not letras.within(galce.buffer(-(d.holgura + 1.0))):
        av.append("Caja de luz: hay letras muy cerca del borde; sube el margen de la placa.")

    cuerpo = prisma(contorno, 0, p) - prisma(interior, d.fondo, p + 1) - prisma(galce, p - t_cara, p + 1)
    rieles, filas, metros, paso = _rieles(interior, d, d.fondo)
    minx, miny, maxx, maxy = interior.bounds
    ojos = []
    if maxx - minx > 60 and maxy - miny > 50:
        y_ojo = maxy - 12 - OJO_RECORRIDO
        for x in (minx + (maxx - minx) * 0.25, minx + (maxx - minx) * 0.75):
            ojos.append(_ojo_cerradura(x, y_ojo, d.fondo))
            res.puntos_fijacion.append((x, y_ojo + OJO_RECORRIDO))
    else:
        av.append("Caja de luz pequeña: sin colgadores; fíjala con adhesivo o tornillos pasantes.")
    quitar = [v for _, v in ojos]
    if d.cable > 0:
        xc, yc = (minx + maxx) / 2, miny + max(8.0, d.cable)
        quitar.append(cilindro(xc, yc, d.cable / 2, -1, d.fondo + RIEL_ALTO + 1))
        res.puntos_cable = [(xc, yc)]
    cuerpo = unir([cuerpo, *rieles, *[pad for pad, _ in ojos]]) - unir(quitar)

    placa_cara = multipoligono(galce.buffer(-d.holgura, **UNION))
    relieve = multipoligono(letras.buffer(-d.holgura, **UNION))
    difusor = unir([prisma(placa_cara, 0, d.frente), prisma(relieve, d.frente - 0.01, d.frente + d.mascara)])
    mascara = prisma(multipoligono(placa_cara.difference(letras)), 0, d.mascara)

    res.led = {"metros": round(metros, 3), "filas": filas, "separacion_mm": round(paso, 1) if filas else 0.0,
               "montaje": "filas en el fondo, entre las guías"}
    res.metros_led = res.led["metros"]
    solidos = [("cuerpo", cuerpo), ("difusor", difusor), ("mascara", mascara)]
    materiales = {"difusor": "difusor"}
    montajes = {"difusor": subir(p - t_cara), "mascara": subir(p - d.mascara)}
    finalizar(res, caja, d, contorno, interior, solidos, res.puntos_cable + res.puntos_fijacion, materiales, montajes)
    return res
