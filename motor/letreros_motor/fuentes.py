"""Registro de fuentes autorizadas para generar geometría.

Solo se usan archivos versionados en el repositorio, sin modificar, con
licencia SIL OFL 1.1 y suma SHA-256 fija: el mismo texto produce siempre la
misma geometría. Las fuentes variables se fijan al peso de la vista previa
(p. ej. wght=700) en memoria, solo para calcular contornos; el archivo de
fuente no se modifica ni se redistribuye modificado (los nombres reservados
de la OFL se respetan).
"""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

from .errores import ErrorEntrada

DIR_FUENTES = Path(__file__).resolve().parent.parent / "fuentes"
GOOGLE = "https://github.com/google/fonts (commit e7db6ca, 2026-10-23)"


@dataclass(frozen=True)
class Fuente:
    clave: str
    nombre: str
    familia_web: str  # nombre en el selector de index.html
    archivo: str
    archivo_licencia: str
    origen: str
    sha256: str
    variaciones: dict = field(default_factory=dict, hash=False, compare=False)
    estilo: str = "rotulo"  # rotulo | manuscrita (se une sola)
    licencia: str = "SIL Open Font License 1.1"

    @property
    def ruta(self) -> Path:
        return DIR_FUENTES / self.archivo


_LISTA = [
    Fuente("montserrat-bold", "Montserrat Bold", "Montserrat", "Montserrat-Bold.ttf", "OFL-Montserrat.txt",
           "https://github.com/JulietaUla/Montserrat (commit 555facf)",
           "bc6e854971cea46b463be6f9eef4d9cd52f51cfc1fc0dd90c9d3e6483dc0ec61"),
    Fuente("poppins-bold", "Poppins Bold", "Poppins", "Poppins-Bold.ttf", "OFL-Poppins.txt", GOOGLE,
           "983676516167748b74de6f4771fb384c664fd913acb8b471122ecacf5da5ea6c"),
    Fuente("roboto-bold", "Roboto Bold", "Roboto", "Roboto[wdth,wght].ttf", "OFL-Roboto.txt", GOOGLE,
           "d7598e12c5dbef095ff8272cfc55da0250bd07fbdecbac8a530b9b277872a134", {"wght": 700, "wdth": 100}),
    Fuente("oswald-bold", "Oswald Bold", "Oswald", "Oswald[wght].ttf", "OFL-Oswald.txt", GOOGLE,
           "5b38c246e255a12f5712d640d56bcced0472466fc68983d2d0410ec0457c2817", {"wght": 700}),
    Fuente("bebas-neue", "Bebas Neue", "Bebas Neue", "BebasNeue-Regular.ttf", "OFL-BebasNeue.txt", GOOGLE,
           "08e4623805102d819f58601e46e345648846075e363b2ceb23313c2d1c83ec73"),
    Fuente("playfair-bold", "Playfair Display Bold", "Playfair Display", "PlayfairDisplay[wght].ttf",
           "OFL-PlayfairDisplay.txt", GOOGLE,
           "c40f2293766a503bc70cce9e512ef844a4ccb7cbcde792fe2ea31d191917d8d6", {"wght": 700}),
    Fuente("lobster", "Lobster", "Lobster", "Lobster-Regular.ttf", "OFL-Lobster.txt", GOOGLE,
           "d6568e697fd50cedc0be04d8aae4127fe95add607e7bff954ca88604be80c205", estilo="manuscrita"),
    Fuente("pacifico", "Pacifico", "Pacifico", "Pacifico-Regular.ttf", "OFL-Pacifico.txt", GOOGLE,
           "5b6c0d5334a7bf77dea52b975c5a0c408878c0f7115ed5b6fb151f634b7bf701", estilo="manuscrita"),
    Fuente("dancing-script-bold", "Dancing Script Bold", "Dancing Script", "DancingScript[wght].ttf",
           "OFL-DancingScript.txt", GOOGLE,
           "21808625578fe8d8cd10cb684be546dca077b27cd03a53a2f1ec11dc743c924c", {"wght": 700}, estilo="manuscrita"),
    Fuente("great-vibes", "Great Vibes", "Great Vibes", "GreatVibes-Regular.ttf", "OFL-GreatVibes.txt", GOOGLE,
           "8d509802186f1b51572531ecf313e8098f9a5bfdfaca93f0c9b34467f9982d15", estilo="manuscrita"),
]
FUENTES: dict[str, Fuente] = {f.clave: f for f in _LISTA}
POR_FAMILIA_WEB: dict[str, str] = {f.familia_web: f.clave for f in _LISTA}
FUENTE_POR_DEFECTO = "montserrat-bold"


def obtener_fuente(clave: str) -> Fuente:
    if clave not in FUENTES:
        disponibles = ", ".join(sorted(FUENTES))
        raise ErrorEntrada(f"Fuente '{clave}' no autorizada. Disponibles: {disponibles}.")
    fuente = FUENTES[clave]
    _verificar(clave)
    return fuente


@lru_cache(maxsize=None)
def _verificar(clave: str) -> None:
    fuente = FUENTES[clave]
    if not fuente.ruta.is_file():
        raise ErrorEntrada(f"Falta el archivo de fuente {fuente.ruta}.")
    if hashlib.sha256(fuente.ruta.read_bytes()).hexdigest() != fuente.sha256:
        raise ErrorEntrada(f"El archivo {fuente.archivo} no coincide con la versión revisada (SHA-256 distinto).")


@lru_cache(maxsize=16)
def _datos(clave: str) -> tuple[TTFont, bytes]:
    fuente = obtener_fuente(clave)
    tt = TTFont(str(fuente.ruta))
    if fuente.variaciones:
        tt = instancer.instantiateVariableFont(tt, dict(fuente.variaciones))
    flujo = io.BytesIO()
    tt.save(flujo)
    datos = flujo.getvalue()
    return TTFont(io.BytesIO(datos)), datos


def ttfont(clave: str) -> TTFont:
    """TTFont estático (variables ya fijadas) para dibujar contornos."""
    return _datos(clave)[0]


def binario(clave: str) -> bytes:
    """Bytes de la fuente estática, para HarfBuzz."""
    return _datos(clave)[1]
