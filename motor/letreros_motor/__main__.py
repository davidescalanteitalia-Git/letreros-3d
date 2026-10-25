"""Uso: python -m letreros_motor A --altura 120 --profundidad 35 -o salida/A.stl"""
from __future__ import annotations

import argparse
import sys

from . import ErrorEntrada, ErrorGeometria, Parametros, exportar_stl, generar_letra
from .fuentes import FUENTE_POR_DEFECTO, FUENTES


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="letreros_motor",
        description="Genera el STL de UNA letra corpórea maciza (prototipo, sin caja hueca ni LED).",
    )
    ap.add_argument("letra", help="Un solo carácter, p. ej. A, Ñ, 8")
    ap.add_argument("--altura", type=float, required=True, help="Altura real del contorno en mm (20–1500)")
    ap.add_argument("--profundidad", type=float, required=True, help="Grosor/extrusión en mm (5–250)")
    ap.add_argument("--fuente", default=FUENTE_POR_DEFECTO, choices=sorted(FUENTES))
    ap.add_argument("--tolerancia", type=float, default=0.05, help="Desviación máx. de curvas en mm")
    ap.add_argument("-o", "--salida", required=True, help="Ruta del .stl")
    a = ap.parse_args(argv)

    try:
        malla, informe = generar_letra(
            Parametros(a.letra, a.altura, a.profundidad, a.fuente, a.tolerancia)
        )
        ruta = exportar_stl(malla, a.salida)
    except (ErrorEntrada, ErrorGeometria) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    print(informe.como_texto())
    print(f"STL escrito en {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
