"""Línea de comandos de Letreros 3D Studio.

  python -m letreros_motor letrero "LUCY" --estructura frontal --altura 120 -o salida/LUCY
  python -m letreros_motor probeta -o salida/probeta
  python -m letreros_motor A --altura 120 --profundidad 35 -o salida/A.stl   (M1, una letra maciza)
"""
from __future__ import annotations

import argparse
import sys

from . import ESTRUCTURAS, Diseno, ErrorEntrada, ErrorGeometria
from . import Parametros, exportar, exportar_stl, generar_letra, generar_letrero, generar_probeta
from .fuentes import FUENTE_POR_DEFECTO, FUENTES
from .proyecto import Proyecto, ResultadoLetra

SUBCOMANDOS = {"letrero", "probeta", "desde-web"}


def _parametros_comunes(ap: argparse.ArgumentParser) -> None:
    g = ap.add_argument_group("medidas (mm)")
    g.add_argument("--altura", type=float, default=120, help="altura de la MAYÚSCULA (20–1000). Def. 120")
    g.add_argument("--profundidad", type=float, default=40, help="grosor total montado (5–250). Def. 40")
    g.add_argument("--pared", type=float, default=1.6, help="pared lateral; múltiplo de 0,4. Def. 1.6")
    g.add_argument("--frente", type=float, default=2.0, help="grosor del frente. Def. 2")
    g.add_argument("--fondo", type=float, default=2.0, help="grosor del fondo. Def. 2")
    g.add_argument("--holgura", type=float, default=0.25, help="juego del frente a presión. Def. 0.25")
    g.add_argument("--encaje", type=float, default=4.0, help="altura del faldón del frente. Def. 4")
    g.add_argument("--pared-encaje", type=float, default=1.2, help="grosor del faldón. Def. 1.2")
    g.add_argument("--comp-xy", type=float, default=0.0, help="compensación XY (0–0,5). Def. 0")
    g.add_argument("--fuente", default=FUENTE_POR_DEFECTO, choices=sorted(FUENTES))


def _imprimir_piezas(proyecto: Proyecto, destino) -> None:
    print(proyecto.resumen())
    print(f"Archivos en {destino}")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] not in SUBCOMANDOS and not argv[0].startswith("-"):
        return _main_m1(argv)

    ap = argparse.ArgumentParser(prog="letreros_motor", description="Letreros 3D Studio · motor de geometría")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("letrero", help="generar todas las piezas de un letrero",
                        description="Estructuras: " + " | ".join(f"{k}: {v}" for k, v in ESTRUCTURAS.items()))
    pl.add_argument("texto", help='texto, p. ej. "LUCY"; varias líneas con \\n: "LUCY\\nHAIR"')
    pl.add_argument("--alineacion", choices=["centro", "izquierda", "derecha"], default="centro",
                    help="varias líneas: alineación. Def. centro")
    pl.add_argument("--interlineado", type=float, default=1.4,
                    help="varias líneas: distancia entre bases × altura (1–3). Def. 1.4")
    pl.add_argument("--estructura", choices=list(ESTRUCTURAS), default="frontal")
    _parametros_comunes(pl)
    pl.add_argument("--espaciado", type=float, default=0.0, help="mm extra entre letras. Def. 0")
    pl.add_argument("--tira-led", type=float, default=None, help="ancho de la tira LED (0 = no comprobar). Def. 8 en frontal/halo")
    pl.add_argument("--w-por-metro", type=float, default=0.0, help="consumo de la tira en W/m (opcional)")
    pl.add_argument("--cable", type=float, default=6.0, help="Ø agujero de cable en el fondo (0 = no). Def. 6")
    pl.add_argument("--drenaje", action="store_true", help="agujero de drenaje Ø3 para exterior")
    pl.add_argument("--separacion", type=float, default=20.0, help="halo: distancia a la pared. Def. 20")
    pl.add_argument("--tornillo", type=float, default=3.2, help="halo: Ø agujero del separador. Def. 3.2")
    pl.add_argument("--conjunto", choices=["individual", "unidas", "placa"], default="individual",
                    help="letras sueltas, unidas en una pieza por palabra, o sobre placa común")
    pl.add_argument("--puente", type=float, default=0.0, help="unidas: suavizado de rincones entre letras (mm)")
    pl.add_argument("--barra", type=float, default=0.0, help="unidas: barra inferior de esta altura (mm)")
    pl.add_argument("--placa-forma", choices=["rect", "silueta"], default="rect")
    pl.add_argument("--placa-margen", type=float, default=15.0)
    pl.add_argument("--placa-grosor", type=float, default=4.0)
    pl.add_argument("--placa-agujero", type=float, default=5.0, help="Ø agujeros de fijación de la placa (0 = no)")
    pl.add_argument("--no-dividir", action="store_true", help="error en vez de dividir lo que no cabe en la cama")
    pl.add_argument("--precio-kg", type=float, default=25.0, help="€/kg de filamento para el presupuesto")
    pl.add_argument("--precio-led-m", type=float, default=0.0, help="€/m de tira LED para el presupuesto")
    pl.add_argument("--zip", action="store_true", help="además, comprimir la carpeta en .zip")
    pl.add_argument("-o", "--salida", required=True, help="carpeta de salida (nueva o vacía)")

    pp = sub.add_parser("probeta", help="probeta de holguras del frente a presión")
    _parametros_comunes(pp)
    pp.add_argument("--holguras", type=float, nargs="+", default=[0.15, 0.25, 0.35, 0.45])
    pp.add_argument("-o", "--salida", required=True, help="carpeta de salida")

    pw = sub.add_parser("desde-web", help="fabricar el proyecto JSON guardado en el editor web")
    pw.add_argument("proyecto", help="archivo .json de 'Guardar proyecto JSON'")
    pw.add_argument("--zip", action="store_true")
    pw.add_argument("-o", "--salida", required=True, help="carpeta de salida (nueva o vacía)")

    a = ap.parse_args(argv)
    if a.cmd == "desde-web":
        return _desde_web(a)
    comunes = dict(altura=a.altura, profundidad=a.profundidad, pared=a.pared, frente=a.frente, fondo=a.fondo,
                   holgura=a.holgura, encaje=a.encaje, pared_encaje=a.pared_encaje, comp_xy=a.comp_xy,
                   fuente=a.fuente)
    try:
        if a.cmd == "letrero":
            d = Diseno(a.texto.replace("\\n", "\n"), estructura=a.estructura,
                       alineacion=a.alineacion, interlineado=a.interlineado, espaciado=a.espaciado, tira_led=a.tira_led,
                       w_por_metro=a.w_por_metro, cable=a.cable, drenaje=a.drenaje,
                       separacion=a.separacion, tornillo=a.tornillo, conjunto=a.conjunto, puente=a.puente,
                       barra=a.barra, placa_forma=a.placa_forma, placa_margen=a.placa_margen,
                       placa_grosor=a.placa_grosor, placa_agujero=a.placa_agujero, dividir=not a.no_dividir,
                       precio_kg=a.precio_kg, precio_led_m=a.precio_led_m, **comunes)
            proyecto = generar_letrero(d)
            destino = exportar(proyecto, a.salida, comprimir=a.zip)
            _imprimir_piezas(proyecto, destino)
        else:
            piezas, avisos, d = generar_probeta(Diseno("P", **comunes), a.holguras)
            res = ResultadoLetra(piezas[0].letra, piezas)
            proyecto = Proyecto(d, [res], avisos)
            destino = exportar(proyecto, a.salida)
            print(f"Probeta de holguras {', '.join(f'{h:g}' for h in sorted(a.holguras))} mm · {len(piezas)} piezas")
            for av in avisos:
                print(f"AVISO: {av}")
            print(f"Archivos en {destino}")
    except (ErrorEntrada, ErrorGeometria, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    return 0


def _desde_web(a) -> int:
    import json
    from pathlib import Path

    from .web import diseno_desde_web
    try:
        ruta = Path(a.proyecto)
        if ruta.stat().st_size > 20_000:
            raise ErrorEntrada("El proyecto JSON es demasiado grande.")
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        proyecto = generar_letrero(diseno_desde_web(datos))
        destino = exportar(proyecto, a.salida, comprimir=a.zip)
    except FileNotFoundError:
        print(f"Error: no existe el archivo {a.proyecto}", file=sys.stderr)
        return 2
    except json.JSONDecodeError:
        print("Error: el archivo no es un JSON válido.", file=sys.stderr)
        return 2
    except (ErrorEntrada, ErrorGeometria) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    _imprimir_piezas(proyecto, destino)
    return 0


def _main_m1(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="letreros_motor", description="(M1) STL de UNA letra maciza.")
    ap.add_argument("letra")
    ap.add_argument("--altura", type=float, required=True, help="altura real del contorno en mm")
    ap.add_argument("--profundidad", type=float, required=True)
    ap.add_argument("--fuente", default=FUENTE_POR_DEFECTO, choices=sorted(FUENTES))
    ap.add_argument("--tolerancia", type=float, default=0.05)
    ap.add_argument("-o", "--salida", required=True)
    a = ap.parse_args(argv)
    try:
        malla, informe = generar_letra(Parametros(a.letra, a.altura, a.profundidad, a.fuente, a.tolerancia))
        ruta = exportar_stl(malla, a.salida)
    except (ErrorEntrada, ErrorGeometria) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    print(informe.como_texto())
    print(f"STL escrito en {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
