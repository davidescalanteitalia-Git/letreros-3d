"""Registro de fuentes autorizadas para generar geometría.

Solo se usan archivos versionados en el repositorio, con licencia revisada y
suma SHA-256 fija. Así el mismo texto produce siempre la misma geometría,
cosa que la carga de Google Fonts en el navegador no garantiza.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .errores import ErrorEntrada

DIR_FUENTES = Path(__file__).resolve().parent.parent / "fuentes"


@dataclass(frozen=True)
class Fuente:
    clave: str
    nombre: str
    archivo: str
    licencia: str
    archivo_licencia: str
    origen: str
    sha256: str

    @property
    def ruta(self) -> Path:
        return DIR_FUENTES / self.archivo


FUENTES: dict[str, Fuente] = {
    "montserrat-bold": Fuente(
        clave="montserrat-bold",
        nombre="Montserrat Bold 9.000",
        archivo="Montserrat-Bold.ttf",
        licencia="SIL Open Font License 1.1",
        archivo_licencia="OFL-Montserrat.txt",
        origen="https://github.com/JulietaUla/Montserrat (commit 555facf)",
        sha256="bc6e854971cea46b463be6f9eef4d9cd52f51cfc1fc0dd90c9d3e6483dc0ec61",
    ),
}

FUENTE_POR_DEFECTO = "montserrat-bold"


def obtener_fuente(clave: str) -> Fuente:
    if clave not in FUENTES:
        disponibles = ", ".join(sorted(FUENTES))
        raise ErrorEntrada(f"Fuente '{clave}' no autorizada. Disponibles: {disponibles}.")
    fuente = FUENTES[clave]
    if not fuente.ruta.is_file():
        raise ErrorEntrada(f"Falta el archivo de fuente {fuente.ruta}.")
    resumen = hashlib.sha256(fuente.ruta.read_bytes()).hexdigest()
    if resumen != fuente.sha256:
        raise ErrorEntrada(
            f"El archivo {fuente.archivo} no coincide con la versión revisada (SHA-256 distinto)."
        )
    return fuente
