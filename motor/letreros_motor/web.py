"""Traducción del proyecto JSON de la web (index.html) a un `Diseno` del motor.

El editor web guarda {schema_version: 1, letters, height, depth, wall, clearance,
style, font, …} con valores en texto. Aquí se valida el formato, se convierten
los números y se traducen las estructuras. Lo que el motor aún no fabrica se
rechaza con un mensaje claro en vez de generar algo distinto a lo pedido.
"""
from __future__ import annotations

from .diseno import Diseno
from .errores import ErrorEntrada

# style de index.html → estructura del motor (None = todavía no fabricable)
ESTILO_A_ESTRUCTURA = {
    "front": "frontal",
    "halo": "halo",
    "box": "caja",
    "solid": "maciza",
    "neon": None,
    "dual": None,
    "frontsolid": None,
}
NOMBRES_ESTILO = {
    "neon": "Neón flex", "dual": "Doble iluminación", "frontsolid": "Frente opaco con cuerpo iluminado",
}
# Fuentes del editor con contornos verificados para fabricar (las 10 del selector).
from .fuentes import POR_FAMILIA_WEB as FUENTES_WEB  # noqa: E402

# layout de index.html → conjunto del motor
LAYOUT_A_CONJUNTO = {"individual": "individual", "connected": "unidas", "base": "placa"}

# Campos numéricos opcionales que la pestaña Fabricar añade (nombre web → campo Diseno)
CAMPOS_EXTRA = {
    "frente": "frente", "fondo": "fondo", "encaje": "encaje", "pared_encaje": "pared_encaje",
    "espaciado": "espaciado", "comp_xy": "comp_xy", "tira_led": "tira_led", "w_por_metro": "w_por_metro",
    "cable": "cable", "separacion": "separacion", "tornillo": "tornillo",
    "puente": "puente", "barra": "barra", "placa_margen": "placa_margen", "placa_grosor": "placa_grosor",
    "placa_agujero": "placa_agujero", "precio_kg": "precio_kg", "precio_led_m": "precio_led_m",
}
LIMITE_TEXTO_CAMPO = 100


def _texto(datos: dict, clave: str, defecto: str = "") -> str:
    v = datos.get(clave, defecto)
    if v is None:
        return defecto
    if not isinstance(v, (str, int, float, bool)):
        raise ErrorEntrada(f"Campo '{clave}' con formato no válido.")
    return str(v)[:LIMITE_TEXTO_CAMPO]


def _numero(datos: dict, clave: str, nombre: str):
    crudo = _texto(datos, clave).strip().replace(",", ".")
    if crudo == "":
        return None
    try:
        return float(crudo)
    except ValueError:
        raise ErrorEntrada(f"{nombre}: '{crudo}' no es un número.") from None


def diseno_desde_web(datos: dict) -> Diseno:
    if not isinstance(datos, dict):
        raise ErrorEntrada("El proyecto debe ser un objeto JSON.")
    if datos.get("schema_version") != 1:
        raise ErrorEntrada("Proyecto de otra versión del editor (se esperaba schema_version 1).")

    estilo = _texto(datos, "style", "front")
    if estilo not in ESTILO_A_ESTRUCTURA:
        raise ErrorEntrada(f"Estructura '{estilo}' desconocida.")
    estructura = ESTILO_A_ESTRUCTURA[estilo]
    if estructura is None:
        raise ErrorEntrada(
            f"«{NOMBRES_ESTILO[estilo]}» aún no se fabrica. Disponibles: frontal iluminada, halo, caja hueca y maciza."
        )

    fuente_web = _texto(datos, "font", "Montserrat")
    if fuente_web not in FUENTES_WEB:
        raise ErrorEntrada(
            f"La fuente «{fuente_web}» no está entre las fuentes fabricables: {', '.join(FUENTES_WEB)}."
        )

    kwargs: dict = {}
    for clave, campo, nombre in (("height", "altura", "Altura"), ("depth", "profundidad", "Profundidad"),
                                 ("wall", "pared", "Pared"), ("clearance", "holgura", "Holgura")):
        v = _numero(datos, clave, nombre)
        if v is not None:
            kwargs[campo] = v
    for clave, campo in CAMPOS_EXTRA.items():
        v = _numero(datos, clave, campo)
        if v is not None:
            kwargs[campo] = v
    layout = _texto(datos, "layout", "individual")
    if layout not in LAYOUT_A_CONJUNTO:
        raise ErrorEntrada(f"Construcción del conjunto '{layout}' desconocida.")
    kwargs["conjunto"] = LAYOUT_A_CONJUNTO[layout]
    forma_placa = _texto(datos, "placa_forma", "rect")
    if forma_placa:
        kwargs["placa_forma"] = forma_placa
    if datos.get("dividir") is not None:
        kwargs["dividir"] = datos.get("dividir") in (True, "true", "1", "on", 1)
    drenaje = datos.get("drenaje")
    if drenaje is not None:
        kwargs["drenaje"] = drenaje in (True, "true", "1", "on", 1)

    bedx, bedy = _numero(datos, "bedx", "Cama X"), _numero(datos, "bedy", "Cama Y")
    if bedx is not None and bedy is not None:
        if not (50 <= bedx <= 600 and 50 <= bedy <= 600):
            raise ErrorEntrada("La cama útil debe medir entre 50 y 600 mm en X e Y.")
        kwargs["cama"] = (bedx, bedy, 325.0)

    return Diseno(_texto(datos, "letters"), estructura=estructura, fuente=FUENTES_WEB[fuente_web], **kwargs)
