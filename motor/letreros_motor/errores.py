class ErrorEntrada(ValueError):
    """Parámetro inválido o fuera de los límites admitidos. El mensaje es para el usuario."""


class ErrorGeometria(RuntimeError):
    """La geometría generada no supera las comprobaciones de fabricación."""
