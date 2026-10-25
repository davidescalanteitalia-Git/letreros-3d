"""Motor de geometría de Letreros 3D Studio.

M1: una letra maciza → STL (`generar_letra`, se conserva).
M2: letreros completos con estructuras huecas para LED (`Diseno`, `generar_letrero`, `exportar`)
    y probeta de holguras (`generar_probeta`).
v0.3: 10 fuentes OFL, maquetación HarfBuzz, letras unidas/placa común, división por cama,
      plantilla de montaje SVG 1:1 y presupuesto.
v0.4: varias líneas (alineación, interlineado), división horizontal en rejilla, reparto en
      camas por material con 3MF para Bambu Studio y contornos DXF 1:1.
"""
__version__ = "0.4.0"

from .diseno import ESTRUCTURAS, Diseno, validar  # noqa: E402
from .errores import ErrorEntrada, ErrorGeometria  # noqa: E402
from .generador import Informe, Parametros, exportar_stl, generar_letra  # noqa: E402
from .probeta import generar_probeta  # noqa: E402
from .proyecto import Proyecto, exportar, generar_letrero  # noqa: E402

__all__ = [
    "ESTRUCTURAS", "Diseno", "validar", "ErrorEntrada", "ErrorGeometria",
    "Informe", "Parametros", "exportar_stl", "generar_letra",
    "generar_probeta", "Proyecto", "exportar", "generar_letrero",
]
