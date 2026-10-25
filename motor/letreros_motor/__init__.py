"""Motor de geometría de Letreros 3D Studio (prototipo M1: una letra maciza → STL)."""
from .errores import ErrorEntrada, ErrorGeometria
from .generador import Informe, Parametros, exportar_stl, generar_letra

__version__ = "0.1.0"
__all__ = ["ErrorEntrada", "ErrorGeometria", "Informe", "Parametros", "exportar_stl", "generar_letra"]
