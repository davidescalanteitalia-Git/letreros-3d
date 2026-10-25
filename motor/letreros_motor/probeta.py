"""Probeta de holguras para el frente a presión de la estructura frontal.

Un cuerpo rectangular con la misma pared, fondo y faldón que el letrero real,
y un frente por cada holgura. Cada frente lleva grabados tantos puntos como su
posición (1 punto = la holgura más pequeña), en el lado del faldón. Se imprime
todo, se prueba cuál encaja firme sin forzar y ese valor se usa en `--holgura`.
"""
from __future__ import annotations

from dataclasses import replace

from shapely.geometry import MultiPolygon, box

from .diseno import Diseno, validar
from .estructuras import Pieza, construir_letra
from .geometria import cilindro, unir
from .texto import Letra

HOLGURAS_PROBETA = (0.15, 0.25, 0.35, 0.45)
ANCHO, ALTO = 40.0, 24.0


def generar_probeta(base: Diseno | None = None, holguras=HOLGURAS_PROBETA) -> tuple[list[Pieza], list[str], Diseno]:
    base = base or Diseno("I")
    holguras = sorted(float(h) for h in holguras)
    if not 1 <= len(holguras) <= 6:
        raise ValueError("Entre 1 y 6 holguras por probeta.")
    d, avisos = validar(replace(base, texto="P", estructura="frontal",
                                profundidad=base.fondo + base.frente + base.encaje + 4,
                                cable=0, tira_led=0, drenaje=False))
    avisos = [a for a in avisos if "entre fondo y frente" not in a]  # la probeta no lleva luz
    rect = MultiPolygon([box(0, 0, ANCHO, ALTO)])
    piezas: list[Pieza] = []
    for i, h in enumerate(holguras, start=1):
        dh, _ = validar(replace(d, holgura=h))

        def grabar(solido, n=i, z=dh.frente):
            puntos = [cilindro(ANCHO / 2 + (k - (n - 1) / 2) * 4.0, ALTO / 2, 0.9, z - 0.6, z + 1) for k in range(n)]
            return solido - unir(puntos)

        res = construir_letra(Letra(i, f"h{int(round(h * 100)):03d}", rect, 0.0), dh, retoques={"frente": grabar})
        cuerpo, frente = res.piezas
        if i == 1:
            cuerpo.letra = Letra(0, "probeta", rect, 0.0)
            piezas.append(cuerpo)
        piezas.append(frente)
    avisos.append(
        f"Imprime el cuerpo y los {len(holguras)} frentes; elige el que entra firme sin forzar "
        f"(1 punto = {holguras[0]:g} mm … {len(holguras)} puntos = {holguras[-1]:g} mm) y úsalo en --holgura."
    )
    return piezas, avisos, d
