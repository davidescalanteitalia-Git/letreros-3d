"""Parámetros de un letrero, con rangos y validación cruzada.

Todas las medidas en milímetros. Los valores por defecto son hipótesis de
partida para PETG con boquilla 0,4 mm en Bambu Lab A2L; se afinan con la
probeta de holguras (`python -m letreros_motor probeta`).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace

from .errores import ErrorEntrada
from .fuentes import FUENTE_POR_DEFECTO

ESTRUCTURAS = {
    "maciza": "Letra corpórea maciza (sin luz).",
    "caja": "Caja hueca con fondo y frente abierto (neón, acrílico pegado o decorativa).",
    "frontal": "Frontal iluminada: cuerpo con fondo + frente impreso translúcido que encaja a presión.",
    "halo": "Retroiluminada (halo): frente cerrado, trasera abierta y separadores para tornillo a pared.",
    "lateral": "Frente opaco y cuerpo translúcido: la luz sale por los laterales de la letra.",
    "doble": "Doble iluminación: frente y trasera translúcidos a presión, agujeros para separadores metálicos.",
    "neon": "Neón flex: base con canal que sigue el contorno de la letra (o placa común con canales).",
    "caja_luz": "Caja de luz: caja con guías de tira LED, máscara opaca calada y difusor con letras en relieve.",
}
ILUMINADAS = ("frontal", "halo", "lateral", "doble", "caja_luz", "caja")
FIJACIONES = {"ninguna": "Sin fijación (adhesivo o placa)", "insertos": "Torretas para inserto roscado M4 (Ø5,6 × 8)",
              "pasantes": "Agujeros pasantes Ø4,5 avellanados para tornillo y taco"}
TENSIONES = (5.0, 12.0, 24.0)
POSICIONES_LOGO = ("izquierda", "derecha", "arriba", "abajo")
SALIDAS_CABLE = {"cada_pieza": "Un agujero de cable en cada pieza",
                 "inicio": "Una sola salida, en la primera letra (cable por dentro de los puentes)",
                 "fin": "Una sola salida, en la última letra (cable por dentro de los puentes)"}

BOQUILLA_MM = 0.4
# Bambu Lab A2L: 330 × 320 × 325 mm nominales, margen hipotético de 5 mm por lado en XY.
CAMA_A2L_MM = (320.0, 310.0, 325.0)
DENSIDAD_PETG = 1.27  # g/cm³


@dataclass(frozen=True)
class Diseno:
    texto: str
    estructura: str = "frontal"
    altura: float = 120.0          # altura de la MAYÚSCULA
    profundidad: float = 40.0      # grosor total del letrero montado (eje Z)
    pared: float = 1.6             # lateral de la letra (4 líneas de 0,4)
    frente: float = 2.0            # grosor del frente (frontal/halo)
    fondo: float = 2.0             # grosor del fondo (caja/frontal)
    holgura: float = 0.25          # juego entre faldón del frente y pared interior
    encaje: float = 4.0            # altura del faldón que entra en el cuerpo
    pared_encaje: float = 1.2      # grosor del faldón
    espaciado: float = 0.0         # separación extra entre letras (mm reales)
    comp_xy: float = 0.0           # compensación XY: se resta del contorno exterior
    tira_led: float | None = None  # ancho de la tira LED; None = 8 mm en frontal/halo, 0 = sin comprobar
    w_por_metro: float = 0.0       # consumo de la tira (W/m) si se conoce
    cable: float = 6.0             # Ø agujero de cable en el fondo (0 = sin agujero)
    drenaje: bool = False          # agujero Ø3 en la parte baja del fondo (exterior)
    separacion: float = 20.0       # halo: distancia del letrero a la pared
    tornillo: float = 3.2          # halo: Ø del agujero del separador
    conjunto: str = "individual"   # individual | unidas | placa
    puente: float = 0.0            # unidas: cierra huecos entre letras de hasta este ancho
    barra: float = 0.0             # unidas: barra inferior de esta altura (0 = sin barra)
    placa_forma: str = "rect"      # placa: rect | silueta
    placa_margen: float = 15.0     # placa: margen alrededor de las letras
    placa_grosor: float = 4.0      # placa: grosor
    placa_agujero: float = 5.0     # placa: Ø agujeros de fijación (0 = sin agujeros)
    dividir: bool = True           # dividir automáticamente lo que no cabe en la cama
    precio_kg: float = 25.0        # €/kg de filamento (presupuesto)
    precio_led_m: float = 0.0      # €/m de tira LED (presupuesto)
    logo_altura: float = 0.0       # alto del logo en mm (0 = sin logo)
    logo_posicion: str = "izquierda"  # izquierda | derecha | arriba | abajo (respecto al texto)
    logo_separacion: float = 15.0  # distancia del logo al texto
    letras_por_pieza: int = 0      # unidas: piezas de N letras con uniones entre ellas (0 = una pieza por palabra)
    salida_cable: str = "cada_pieza"  # cada_pieza | inicio | fin (unidas: una sola salida de cable)
    fijacion: str = "ninguna"      # ninguna | insertos | pasantes
    tension: float = 12.0          # V de la tira (5, 12, 24): amperios y fuente recomendada
    paso_led: float = 0.0          # separación entre filas de LED (0 = automática: ≈ distancia a la cara)
    neon_ancho: float = 6.0        # neón flex: ancho del perfil
    neon_alto: float = 12.0        # neón flex: alto del perfil
    neon_borde: float = 6.0        # neón: base alrededor del canal
    mascara: float = 1.2           # caja de luz: grosor de la máscara opaca (= relieve de las letras del difusor)
    repisa: float = 3.0            # caja de luz: galce donde apoya la cara
    interlineado: float = 1.4      # varias líneas: distancia entre bases = interlineado × altura
    alineacion: str = "centro"     # varias líneas: izquierda | centro | derecha
    fuente: str = FUENTE_POR_DEFECTO
    tolerancia: float = 0.05       # desviación máx. de las curvas
    cama: tuple[float, float, float] = field(default=CAMA_A2L_MM)

    @property
    def ancho_tira(self) -> float:
        if self.tira_led is None:
            return 8.0 if self.estructura in ("frontal", "halo", "lateral", "doble", "caja_luz") else 0.0
        return self.tira_led

    def como_dict(self) -> dict:
        d = asdict(self)
        d["tira_led"] = self.ancho_tira
        d["cama"] = list(self.cama)
        return d


_RANGOS = {
    "altura": (20, 1000),
    "profundidad": (5, 250),
    "pared": (0.8, 6),
    "frente": (0.8, 6),
    "fondo": (0.8, 6),
    "holgura": (0, 1),
    "encaje": (1, 15),
    "pared_encaje": (0.8, 4),
    "espaciado": (-20, 200),
    "comp_xy": (0, 0.5),
    "w_por_metro": (0, 50),
    "separacion": (5, 80),
    "tornillo": (2, 6),
    "tolerancia": (0.005, 0.5),
    "puente": (0, 20),
    "barra": (0, 80),
    "placa_margen": (3, 100),
    "placa_grosor": (2, 10),
    "precio_kg": (0, 500),
    "precio_led_m": (0, 500),
    "paso_led": (0, 150),
    "neon_ancho": (4, 20),
    "neon_alto": (4, 25),
    "neon_borde": (2, 30),
    "mascara": (0.8, 4),
    "repisa": (1.5, 10),
    "logo_altura": (0, 1000),
    "logo_separacion": (-50, 300),
}

_NOMBRES = {
    "altura": "Altura de mayúscula", "profundidad": "Profundidad", "pared": "Pared",
    "frente": "Frente", "fondo": "Fondo", "holgura": "Holgura", "encaje": "Encaje",
    "pared_encaje": "Pared del faldón", "espaciado": "Espaciado", "comp_xy": "Compensación XY",
    "w_por_metro": "Consumo W/m", "separacion": "Separación a pared", "tornillo": "Ø tornillo",
    "tolerancia": "Tolerancia de curvas", "puente": "Puente entre letras", "barra": "Barra inferior",
    "placa_margen": "Margen de la placa", "placa_grosor": "Grosor de la placa",
    "precio_kg": "Precio del filamento", "precio_led_m": "Precio de la tira LED",
    "paso_led": "Separación entre filas de LED", "neon_ancho": "Ancho del neón", "neon_alto": "Alto del neón",
    "neon_borde": "Borde de la base del neón", "mascara": "Grosor de la máscara", "repisa": "Galce de la caja",
    "logo_altura": "Altura del logo", "logo_separacion": "Separación del logo",
}


def _num(nombre: str, valor) -> float:
    try:
        v = float(valor)
    except (TypeError, ValueError):
        raise ErrorEntrada(f"{_NOMBRES.get(nombre, nombre)} debe ser un número en mm.") from None
    if not math.isfinite(v):
        raise ErrorEntrada(f"{_NOMBRES.get(nombre, nombre)} no es un número válido.")
    return v


def validar(d: Diseno) -> tuple[Diseno, list[str]]:
    """Devuelve el diseño normalizado y la lista de avisos. Lanza ErrorEntrada si es imposible."""
    if d.estructura not in ESTRUCTURAS:
        raise ErrorEntrada(f"Estructura '{d.estructura}' desconocida. Opciones: {', '.join(ESTRUCTURAS)}.")
    cambios = {}
    for campo, (mn, mx) in _RANGOS.items():
        v = _num(campo, getattr(d, campo))
        if not mn <= v <= mx:
            raise ErrorEntrada(
                f"{_NOMBRES[campo]} debe estar entre {mn:g} y {mx:g} mm (recibido {v:g})."
            )
        cambios[campo] = v
    tira = d.tira_led if d.tira_led is None else _num("tira_led", d.tira_led)
    if tira is not None and tira != 0 and not 3 <= tira <= 20:
        raise ErrorEntrada("Ancho de tira LED entre 3 y 20 mm (o 0 para no comprobar).")
    cable = _num("cable", d.cable)
    if cable != 0 and not 2 <= cable <= 15:
        raise ErrorEntrada("Ø del agujero de cable entre 2 y 15 mm (o 0 para no hacerlo).")
    agujero = _num("placa_agujero", d.placa_agujero)
    if agujero != 0 and not 3 <= agujero <= 10:
        raise ErrorEntrada("Ø de los agujeros de la placa entre 3 y 10 mm (o 0 para no hacerlos).")
    from .conjunto import CONJUNTOS
    if d.conjunto not in CONJUNTOS:
        raise ErrorEntrada(f"Conjunto '{d.conjunto}' desconocido. Opciones: {', '.join(CONJUNTOS)}.")
    interlineado = _num("interlineado", d.interlineado)
    if not 1.0 <= interlineado <= 3.0:
        raise ErrorEntrada(f"Interlineado entre 1 y 3 veces la altura (recibido {interlineado:g}).")
    from .texto import ALINEACIONES
    if d.alineacion not in ALINEACIONES:
        raise ErrorEntrada(f"Alineación '{d.alineacion}' desconocida. Opciones: {', '.join(ALINEACIONES)}.")
    try:
        lpp = int(float(d.letras_por_pieza))
    except (TypeError, ValueError):
        raise ErrorEntrada("Letras por pieza debe ser un número entero.") from None
    if not 0 <= lpp <= 10:
        raise ErrorEntrada("Letras por pieza entre 0 (una pieza por palabra) y 10.")
    if d.logo_posicion not in POSICIONES_LOGO:
        raise ErrorEntrada(f"Posición del logo '{d.logo_posicion}' desconocida. Opciones: {', '.join(POSICIONES_LOGO)}.")
    if d.salida_cable not in SALIDAS_CABLE:
        raise ErrorEntrada(f"Salida de cable '{d.salida_cable}' desconocida. Opciones: {', '.join(SALIDAS_CABLE)}.")
    if d.fijacion not in FIJACIONES:
        raise ErrorEntrada(f"Fijación '{d.fijacion}' desconocida. Opciones: {', '.join(FIJACIONES)}.")
    tension = _num("tension", d.tension)
    if tension not in TENSIONES:
        raise ErrorEntrada("Tensión de la tira: 5, 12 o 24 V.")
    if d.placa_forma not in ("rect", "silueta"):
        raise ErrorEntrada("La forma de la placa es 'rect' o 'silueta'.")
    from .fuentes import obtener_fuente
    obtener_fuente(d.fuente)
    d = replace(d, letras_por_pieza=lpp, tension=tension, interlineado=interlineado, tira_led=tira, cable=cable, drenaje=bool(d.drenaje), dividir=bool(d.dividir),
                placa_agujero=agujero, **cambios)
    if d.conjunto == "placa" and d.estructura in ("halo", "doble"):
        raise ErrorEntrada("La placa común no se combina con halo ni doble: van separados de la pared.")
    if d.barra > d.altura * 0.6:
        raise ErrorEntrada(f"La barra inferior ({d.barra:g} mm) no debe superar el 60 % de la altura.")

    p, avisos = d.profundidad, []
    if d.estructura == "caja_luz" and d.conjunto != "individual":
        avisos.append("Caja de luz: la construcción del conjunto no se usa (todas las letras van en la cara de la caja).")
    if d.estructura in ("frontal", "lateral"):
        minimo = d.fondo + d.frente + d.encaje + 2
        if p < minimo:
            raise ErrorEntrada(
                f"Profundidad {p:g} mm insuficiente para frontal: fondo {d.fondo:g} + frente {d.frente:g} "
                f"+ encaje {d.encaje:g} + 2 mm libres = {minimo:g} mm mínimo."
            )
        if p - d.fondo - d.frente < 15:
            avisos.append("Menos de 15 mm entre fondo y frente: la luz puede verse a puntos; usa tira COB o más profundidad.")
    elif d.estructura == "doble":
        minimo = d.fondo + d.frente + 2 * d.encaje + 4
        if p < minimo:
            raise ErrorEntrada(f"Profundidad {p:g} mm insuficiente para doble: fondo + frente + 2 faldones + 4 mm = {minimo:g} mm mínimo.")
    elif d.estructura == "neon":
        if not 4 <= p <= 30:
            raise ErrorEntrada("Neón: la profundidad es el grosor de la base, entre 4 y 30 mm.")
        if min(d.neon_alto * 0.6, p - 2) < 3:
            raise ErrorEntrada(f"Base de {p:g} mm demasiado fina para el canal del neón: sube la profundidad.")
    elif d.estructura == "caja_luz":
        minimo = d.fondo + d.frente + d.mascara + 15
        if p < minimo:
            raise ErrorEntrada(f"Profundidad {p:g} mm insuficiente para caja de luz: fondo + difusor + máscara + 15 mm = {minimo:g} mm.")
        if p - d.fondo - d.frente - d.mascara < 30:
            avisos.append("Caja de luz con menos de 30 mm de cámara: la luz puede verse a puntos; usa tira COB o más profundidad.")
    elif d.estructura == "caja" and p < d.fondo + 2:
        raise ErrorEntrada(f"Profundidad {p:g} mm insuficiente para caja con fondo {d.fondo:g} mm.")
    elif d.estructura == "halo" and p < d.frente + 5:
        raise ErrorEntrada(f"Profundidad {p:g} mm insuficiente para halo con frente {d.frente:g} mm.")

    if d.estructura not in ("maciza", "neon"):
        lineas = d.pared / BOQUILLA_MM
        if abs(lineas - round(lineas)) > 0.05:
            avisos.append(
                f"Pared {d.pared:g} mm no es múltiplo de la boquilla {BOQUILLA_MM} mm: "
                "el laminador puede dejar huecos. Recomendado 1,2 · 1,6 · 2,0."
            )
    if d.estructura in ("frontal", "lateral", "doble") and d.pared_encaje < 2 * BOQUILLA_MM:
        avisos.append("Faldón de menos de 2 líneas de boquilla: puede romperse al encajar.")
    cx, cy, cz = d.cama
    if not (cx > 0 and cy > 0 and cz > 0):
        raise ErrorEntrada("La cama debe tener medidas positivas.")
    alto_pieza = p + (d.separacion if d.estructura == "halo" else 0)
    if alto_pieza > cz:
        raise ErrorEntrada(f"La pieza mide {alto_pieza:g} mm de alto y la cama admite {cz:g} mm en Z.")
    return d, avisos
