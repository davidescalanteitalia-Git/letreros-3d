"""Letrero completo: maquetar, construir todas las letras y exportar el paquete."""
from __future__ import annotations

import json
import math
import zipfile
from dataclasses import dataclass, field, replace
from pathlib import Path

import trimesh

from . import __version__
from .diseno import DENSIDAD_PETG, ESTRUCTURAS, Diseno, validar
from .errores import ErrorEntrada
from .estructuras import Pieza, ResultadoLetra, construir_letra
from .conjunto import agrupar, placa
from .fuentes import obtener_fuente
from .texto import maquetar

INSTRUCCIONES = {
    ("lateral", "cuerpo"): "Fondo sobre la cama, paredes hacia arriba. PETG translúcido (la luz sale por los laterales). Sin soportes.",
    ("lateral", "frente"): "Cara visible sobre la cama, faldón hacia arriba. Color opaco.",
    ("doble", "cuerpo"): "Anillo de paredes, apoyado en cualquiera de sus bordes. Color opaco. Sin soportes.",
    ("doble", "frente"): "Cara visible sobre la cama, faldón hacia arriba. PETG translúcido.",
    ("doble", "trasera"): "Plana sobre la cama, faldón hacia arriba. PETG translúcido; agujeros para separadores metálicos.",
    ("neon", "base"): "Plana sobre la cama, canal hacia arriba. Color opaco (negro o blanco según la pared). Sin soportes.",
    ("caja_luz", "cuerpo"): "Fondo sobre la cama, paredes hacia arriba. Opaco. Los colgadores y las guías no necesitan soportes.",
    ("caja_luz", "difusor"): "Plana sobre la cama, letras en relieve hacia arriba. PETG translúcido blanco o natural.",
    ("caja_luz", "mascara"): "Plana sobre la cama. Color opaco. Los ojos de las letras (O, A, B…) se pegan sobre el difusor.",
    ("maciza", "cuerpo"): "Cara visible hacia arriba. Relleno 10-15 %.",
    ("caja", "cuerpo"): "Fondo sobre la cama, paredes hacia arriba. Sin soportes.",
    ("frontal", "cuerpo"): "Fondo sobre la cama, paredes hacia arriba. Color opaco. Sin soportes.",
    ("frontal", "frente"): "Cara visible sobre la cama, faldón hacia arriba. PETG blanco o natural para difundir la luz.",
    ("halo", "cuerpo"): "Cara visible sobre la cama, separadores hacia arriba. Color opaco. Sin soportes.",
}
INSTRUCCIONES_ROL = {
    "empalme": "Plana sobre la cama (en «doble», de pie). Se pega por dentro cruzando la junta de las dos partes.",
    "placa": "Plana, ranuras de posición hacia arriba. Relleno 15-20 %. Pega cada letra sobre su silueta grabada.",
}


def instrucciones(estructura: str, rol: str) -> str:
    return INSTRUCCIONES.get((estructura, rol)) or INSTRUCCIONES_ROL.get(rol, "")


@dataclass
class Proyecto:
    diseno: Diseno
    letras: list[ResultadoLetra]
    avisos: list[str] = field(default_factory=list)

    @property
    def piezas(self) -> list[Pieza]:
        return [p for r in self.letras for p in r.piezas]

    @property
    def metros_led(self) -> float:
        return sum(r.metros_led for r in self.letras)

    @property
    def peso_g(self) -> float:
        return sum(p.peso_g for p in self.piezas)

    @property
    def unidades(self) -> list[ResultadoLetra]:
        return [r for r in self.letras if r.letra.caracter != "base" or r.letra.indice != 0]

    def camas(self):
        """Reparto de las piezas en camas de impresión (por material)."""
        if getattr(self, "_camas", None) is None:
            from .camas import distribuir
            self._camas = distribuir(self.piezas, self.diseno.cama)
        return self._camas

    def costes(self) -> dict:
        d = self.diseno
        material = self.peso_g / 1000 * d.precio_kg
        led = self.metros_led * d.precio_led_m
        material, led = round(material, 2), round(led, 2)
        return {"material_eur": material, "led_eur": led, "total_eur": round(material + led, 2)}

    def medidas(self) -> tuple[float, float, float, float]:
        fs = [r.letra.forma for r in self.letras]
        return (min(f.bounds[0] for f in fs), min(f.bounds[1] for f in fs),
                max(f.bounds[2] for f in fs), max(f.bounds[3] for f in fs))

    def resumen(self) -> str:
        d = self.diseno
        minx, miny, maxx, maxy = self.medidas()
        from .conjunto import CONJUNTOS
        lineas = [
            f"Letrero «{d.texto.replace(chr(10), ' / ')}» · {d.estructura} ({ESTRUCTURAS[d.estructura]})",
            f"Fuente {obtener_fuente(d.fuente).nombre} · conjunto {d.conjunto} ({CONJUNTOS[d.conjunto]})",
            f"Mayúscula {d.altura:g} mm · conjunto {maxx - minx:.1f} × {maxy - miny:.1f} × {d.profundidad:g} mm",
            f"Piezas: {len(self.piezas)} en {len(self.camas())} cama(s) de impresión · material ≈ {self.peso_g:.0f} g de PETG (sólido al 100 %; el laminador dará el dato real)",
        ]
        if self.metros_led:
            if d.estructura == "neon":
                led = f"Neón flex {d.neon_ancho:g} × {d.neon_alto:g} mm: ≈ {self.metros_led:.2f} m de canal"
            else:
                from .estructuras import separacion_filas
                led = (f"Tira LED {d.ancho_tira:g} mm: ≈ {self.metros_led:.2f} m"
                       + (f" (filas cada ≤ {separacion_filas(d):.0f} mm)" if d.estructura != "doble" else " (pegada a la pared interior)"))
            e = plan_electrico(self)
            if "vatios" in e:
                led += (f" · {e['vatios']:.1f} W a {d.tension:g} V = {e['amperios']:.2f} A"
                        + (f" · fuente ≥ {e['fuente_w']} W" if e["fuente_w"] else " · varias fuentes")
                        + (f" · {e['alimentaciones']} puntos de alimentación" if e["alimentaciones"] > 1 else ""))
            lineas.append(led)
        c = self.costes()
        if d.precio_kg or d.precio_led_m:
            lineas.append(f"Coste de materiales ≈ {c['total_eur']:.2f} € (filamento {c['material_eur']:.2f} € "
                          f"a {d.precio_kg:g} €/kg" + (f" + LED {c['led_eur']:.2f} €" if d.precio_led_m else "") + ")")
        lineas += [f"AVISO: {a}" for a in self.avisos]
        return "\n".join(lineas)


def generar_letrero(diseno: Diseno) -> Proyecto:
    d, avisos = validar(diseno)
    obtener_fuente(d.fuente)
    letras = maquetar(d.texto, d.fuente, d.altura, d.espaciado, d.tolerancia, d.interlineado, d.alineacion)
    unidades, avisos_conjunto = agrupar(letras, d)
    avisos += avisos_conjunto
    if d.estructura == "caja_luz":
        from .caja_luz import construir_caja_luz
        resultados = [construir_caja_luz(unidades, d)]
    elif d.estructura == "neon" and d.conjunto == "placa":
        # Placa de neón: las letras no son piezas; la placa lleva sus canales.
        resultados = [_datos_neon(u, d) for u in unidades]
        resultados.append(placa(unidades, resultados, d))
    else:
        resultados = [construir_letra(u, d) for u in unidades]
        if d.conjunto == "placa":
            resultados.append(placa(unidades, resultados, d))
    vistos = set(avisos)
    for r in resultados:
        for a in r.avisos:
            if a not in vistos:
                vistos.add(a)
                avisos.append(a)
    return Proyecto(d, resultados, avisos)


ARCHIVOS_FIJOS = {"ficha.json", "LEEME.txt", "plantilla-montaje.svg", "contornos.dxf", "camas"}


def _datos_neon(letra, d: Diseno) -> ResultadoLetra:
    """Metros, punto de cable y tubo de vista de una letra de neón que va en placa común."""
    res = construir_letra(letra, replace(d, conjunto="individual", dividir=True, fijacion="ninguna"))
    res.piezas = []
    return res


def plan_electrico(proyecto: "Proyecto") -> dict:
    """Consumo y fuente a partir de los metros y de los datos de TU tira (W/m y tensión).
    Sin W/m no se inventa consumo: solo metros. Fuente con un 20 % de margen, a tamaño comercial."""
    d = proyecto.diseno
    metros = proyecto.metros_led
    res = {"metros": round(metros, 2), "tension_v": d.tension}
    if not metros or not d.w_por_metro:
        return res
    vatios = metros * d.w_por_metro
    necesaria = vatios * 1.2
    fuente = next((f for f in FUENTES_COMERCIALES_W if f >= necesaria), None)
    tramo_max = TRAMO_MAX_M.get(d.tension, 5.0)
    res.update({"vatios": round(vatios, 1), "amperios": round(vatios / d.tension, 2),
                "fuente_w": fuente, "alimentaciones": max(1, math.ceil(metros / tramo_max)),
                "tramo_max_m": tramo_max})
    return res


FUENTES_COMERCIALES_W = (15, 25, 35, 50, 60, 75, 100, 150, 200, 240, 320, 480, 600)
TRAMO_MAX_M = {5.0: 2.0, 12.0: 5.0, 24.0: 10.0}  # longitud orientativa por punto de alimentación


def _medidas(malla: trimesh.Trimesh) -> list[float]:
    return [round(float(v), 2) for v in malla.extents]


def exportar(proyecto: Proyecto, carpeta: str | Path, comprimir: bool = False) -> Path:
    """Escribe un STL por pieza, ficha.json y LEEME.txt. Devuelve la carpeta (o el .zip)."""
    carpeta = Path(carpeta)
    if carpeta.exists() and any(carpeta.iterdir()):
        existentes = {p.name for p in carpeta.iterdir()}
        if not existentes <= {p.archivo for p in proyecto.piezas} | ARCHIVOS_FIJOS:
            raise ErrorEntrada(f"La carpeta {carpeta} ya contiene otros archivos; elige una carpeta nueva o vacía.")
    carpeta.mkdir(parents=True, exist_ok=True)
    d = proyecto.diseno
    for p in proyecto.piezas:
        (carpeta / p.archivo).write_bytes(trimesh.exchange.stl.export_stl(p.malla))

    ficha = {
        "motor": f"letreros_motor {__version__}",
        "fuente": obtener_fuente(d.fuente).nombre,
        "diseno": d.como_dict(),
        "resumen": {
            "piezas": len(proyecto.piezas),
            "peso_petg_g": round(proyecto.peso_g, 1),
            "densidad_petg": DENSIDAD_PETG,
            "metros_led": round(proyecto.metros_led, 3),
            "consumo_w": round(proyecto.metros_led * d.w_por_metro, 1) if d.w_por_metro else None,
            "costes": proyecto.costes(),
            "electrico": plan_electrico(proyecto),
        },
        "montaje": [
            {"orden": r.letra.indice, "caracter": r.letra.caracter,
             "x_mm": round(r.letra.forma.bounds[0], 2), "y_mm": round(r.letra.forma.bounds[1], 2),
             "ancho_mm": round(r.letra.forma.bounds[2] - r.letra.forma.bounds[0], 2),
             "alto_mm": round(r.letra.forma.bounds[3] - r.letra.forma.bounds[1], 2),
             "hueca": r.hueca, "cortes_x_mm": [round(x, 1) for x in r.cortes],
             "cortes_y_mm": [round(y, 1) for y in r.cortes_y], "linea": r.letra.linea,
             "led": r.led, "fijaciones": [[round(x, 1), round(y, 1)] for x, y in r.puntos_fijacion],
             "separadores": [[round(x, 1), round(y, 1)] for x, y in r.puntos_separadores],
             "cable": [[round(x, 1), round(y, 1)] for x, y in r.puntos_cable]}
            for r in proyecto.letras
        ],
        "piezas": [
            {"archivo": p.archivo, "caracter": p.letra.caracter, "rol": p.rol,
             "medidas_mm": _medidas(p.malla), "volumen_cm3": round(p.volumen_cm3, 2),
             "peso_g": round(p.peso_g, 1), "triangulos": int(len(p.malla.faces)),
             "parte": p.parte, "material": p.material, "impresion": instrucciones(d.estructura, p.rol)}
            for p in proyecto.piezas
        ],
        "camas": [
            {"archivo": f"camas/{c.archivo}", "numero": c.numero, "material": c.material,
             "peso_g": round(c.peso_g, 1),
             "piezas": [{"archivo": col.pieza.archivo, "x_mm": round(col.x, 1), "y_mm": round(col.y, 1),
                         "ancho_mm": round(col.ancho, 1), "alto_mm": round(col.alto, 1)} for col in c.colocaciones]}
            for c in proyecto.camas()
        ],
        "avisos": proyecto.avisos,
    }
    (carpeta / "ficha.json").write_text(json.dumps(ficha, ensure_ascii=False, indent=2), encoding="utf-8")
    (carpeta / "LEEME.txt").write_text(_leeme(proyecto, ficha), encoding="utf-8")
    (carpeta / "plantilla-montaje.svg").write_text(plantilla_svg(proyecto), encoding="utf-8")
    from .camas import cama_3mf, contornos_dxf
    (carpeta / "contornos.dxf").write_bytes(contornos_dxf(proyecto))
    (carpeta / "camas").mkdir(exist_ok=True)
    for c in proyecto.camas():
        (carpeta / "camas" / c.archivo).write_bytes(cama_3mf(c, f"{d.texto.replace(chr(10), ' / ')} · cama {c.numero}"))

    if comprimir:
        zip_path = carpeta.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(carpeta.rglob("*")):
                if f.is_file():
                    z.write(f, f"{carpeta.name}/{f.relative_to(carpeta).as_posix()}")
        return zip_path
    return carpeta


def _leeme(proyecto: Proyecto, ficha: dict) -> str:
    d = proyecto.diseno
    partes = [proyecto.resumen(), "", "PIEZAS"]
    for p in ficha["piezas"]:
        x, y, z = p["medidas_mm"]
        partes.append(f"  {p['archivo']:<28} {x:>7.1f} × {y:>6.1f} × {z:>5.1f} mm  {p['peso_g']:>6.1f} g")
    partes += ["", "CAMAS DE IMPRESIÓN (carpeta camas/: ábrelas en Bambu Studio, ya vienen colocadas)"]
    from .camas import NOMBRE_MATERIAL
    for c in ficha["camas"]:
        partes.append(f"  {c['archivo']:<30} {len(c['piezas'])} pieza(s) · {c['peso_g']:.0f} g · {NOMBRE_MATERIAL[c['material']]}")
    partes += ["", "CÓMO IMPRIMIR"]
    for rol in sorted({p.rol for p in proyecto.piezas}):
        partes.append(f"  {rol}: {instrucciones(d.estructura, rol)}")
    partes += ["", "MONTAJE (medido desde la esquina inferior izquierda del letrero; y hacia arriba)"]
    x0 = min(m["x_mm"] for m in ficha["montaje"])
    y0 = min(m["y_mm"] for m in ficha["montaje"])
    for m in ficha["montaje"]:
        partes.append(f"  {m['orden']:02d} «{m['caracter']}»  x = {m['x_mm'] - x0:7.1f} mm  y = {m['y_mm'] - y0:7.1f} mm  "
                      f"ancho {m['ancho_mm']:6.1f} × alto {m['alto_mm']:6.1f} mm")
    divididas = [m for m in ficha["montaje"] if m["cortes_x_mm"] or m["cortes_y_mm"]]
    if divididas:
        partes += ["", "PIEZAS DIVIDIDAS (la cama no admite la pieza entera)"]
        for m in divididas:
            donde = []
            if m["cortes_x_mm"]:
                donde.append("x = " + ", ".join(f"{x - x0:.0f}" for x in m["cortes_x_mm"]))
            if m["cortes_y_mm"]:
                donde.append("y = " + ", ".join(f"{y - y0:.0f}" for y in m["cortes_y_mm"]))
            partes.append(f"  «{m['caracter']}»: cortes en {' · '.join(donde)} mm")
        partes.append("  Partes: letras A, B, C… de izquierda a derecha; números 1, 2… de abajo arriba (A1, B1, A2…).")
        partes.append("  Uniones: colas de milano en macizas; en huecas, placa de empalme con el nombre de las dos partes (AB, 12, A1A2…).")
    partes += ["", "PLANTILLA: plantilla-montaje.svg está a escala 1:1 (mm). Imprímela al 100 % para marcar en la pared "
               "la posición de cada pieza, los agujeros de cable (+) y los separadores (o)."]
    e = ficha["resumen"]["electrico"]
    if e.get("metros"):
        partes += ["", "LUZ E INSTALACIÓN (orientativo: confirma con la ficha de tu tira y de la fuente)"]
        for m in ficha["montaje"]:
            led = m.get("led") or {}
            if led.get("metros"):
                filas = f"{led['filas']} fila(s)" + (f" cada {led['separacion_mm']:.0f} mm" if led.get("separacion_mm") else "")
                partes.append(f"  «{m['caracter']}»: {led['metros']:.2f} m · {filas} · {led.get('montaje', '')}")
        partes.append(f"  Total: {e['metros']:.2f} m a {e['tension_v']:g} V.")
        if "vatios" in e:
            partes.append(f"  Consumo {e['vatios']:.1f} W → {e['amperios']:.2f} A. Fuente recomendada ≥ "
                          f"{e['fuente_w'] or 'varias'} W (20 % de margen). Alimenta como mucho {e['tramo_max_m']:g} m por punto "
                          f"({e['alimentaciones']} punto(s)) para evitar caída de tensión.")
        else:
            partes.append("  Indica los W/m de tu tira para calcular consumo, amperios y fuente.")
        partes.append("  Exterior: fuente IP67, conexiones selladas y drenaje abajo.")
    if d.fijacion != "ninguna" or d.estructura in ("doble", "caja_luz", "halo"):
        partes += ["", "FIJACIÓN"]
        partes.append({"insertos": "  Torretas para inserto térmico M4 (Ø5,6 × 8): mételo con el soldador a 220-240 °C. "
                                   "Atornilla a la pared con varilla M4 o tornillo + taco.",
                       "pasantes": "  Agujeros Ø4,5 avellanados por dentro: tornillo de cabeza avellanada 4 mm + taco.",
                       "ninguna": ""}[d.fijacion] if d.estructura not in ("doble", "caja_luz", "halo") else
                      {"doble": f"  Trasera con agujeros Ø{d.tornillo:g} para separadores metálicos (inox) a pared.",
                       "caja_luz": "  Dos colgadores tipo ojo de cerradura: tornillos a pared con la cabeza 5 mm fuera, "
                                   "a la distancia de la plantilla; cuelga la caja y bájala.",
                       "halo": f"  Separadores impresos de {d.separacion:g} mm con agujero Ø{d.tornillo:g}."}[d.estructura])
        partes.append("  Las posiciones están en plantilla-montaje.svg (o = fijación/separador, + = cable).")
    if d.estructura == "neon":
        partes += ["", f"NEÓN: canal de {d.neon_ancho:g} mm siguiendo el contorno. Respeta el radio mínimo de curvatura de tu "
                   "neón en las esquinas; si no entra, calienta el neón suavemente o usa uno más fino. Sella con silicona neutra."]
    partes += ["", "CONTORNOS: contornos.dxf (mm, 1:1, en posición de montaje). Capa LETRAS para cortar a láser "
               "el frente de metacrilato (estructura caja) o vinilo; CORTES y CABLE como referencia."]
    if d.estructura == "frontal":
        partes += ["", f"Frente a presión con holgura {d.holgura:g} mm: calibrar antes con `python -m letreros_motor probeta`."]
    if d.estructura == "halo":
        partes += ["", f"Separadores de {d.separacion:g} mm con agujero Ø{d.tornillo:g} mm para taco/tornillo a pared."]
    partes += ["", "Medidas verificadas como sólidos cerrados (manifold). Comprobar en Bambu Studio antes de imprimir."]
    return "\n".join(partes) + "\n"


def plantilla_svg(proyecto: Proyecto) -> str:
    """Plantilla de montaje a escala 1:1 en mm (vista frontal, como se ve en la pared)."""
    from html import escape

    minx, miny, maxx, maxy = proyecto.medidas()
    m = 20.0
    ancho, alto = maxx - minx + 2 * m, maxy - miny + 2 * m

    def pt(x, y):
        return f"{x - minx + m:.2f},{maxy - y + m:.2f}"

    def camino(forma):
        trozos = []
        for poly in getattr(forma, "geoms", [forma]):
            for anillo in [poly.exterior, *poly.interiors]:
                cs = list(anillo.coords)
                trozos.append("M" + " L".join(pt(x, y) for x, y in cs) + " Z")
        return " ".join(trozos)

    el = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho:.1f}mm" height="{alto:.1f}mm" '
          f'viewBox="0 0 {ancho:.2f} {alto:.2f}" font-family="Arial, sans-serif">',
          f'<title>Plantilla de montaje 1:1 · {escape(proyecto.diseno.texto.replace(chr(10), ' / '))}</title>',
          '<rect width="100%" height="100%" fill="#fff"/>']
    for r in proyecto.letras:
        es_placa = r.letra.indice == 0 and r.letra.caracter == "base"
        el.append(f'<path d="{camino(r.letra.forma)}" fill="{"none" if es_placa else "#eef3fb"}" '
                  f'stroke="{"#999" if es_placa else "#1f4e8c"}" stroke-width="0.4" fill-rule="evenodd"/>')
        for (xa, ya), (xb, yb) in r.juntas:
            a1, b1 = pt(xa, ya).split(",")
            a2, b2 = pt(xb, yb).split(",")
            el.append(f'<line x1="{a1}" y1="{b1}" x2="{a2}" y2="{b2}" '
                      'stroke="#c0392b" stroke-width="0.4" stroke-dasharray="3 2"/>')
        for x, y in r.puntos_cable:
            a, b = pt(x, y).split(",")
            el.append(f'<path d="M{float(a) - 4:.2f},{b} h8 M{a},{float(b) - 4:.2f} v8" stroke="#000" stroke-width="0.4"/>')
        for x, y in r.puntos_fijacion:
            a, b = pt(x, y).split(",")
            el.append(f'<circle cx="{a}" cy="{b}" r="3" fill="none" stroke="#7a3db8" stroke-width="0.4"/>'
                      f'<path d="M{float(a) - 5:.2f},{b} h10 M{a},{float(b) - 5:.2f} v10" stroke="#7a3db8" stroke-width="0.2"/>')
        for x, y in r.puntos_separadores:
            a, b = pt(x, y).split(",")
            el.append(f'<circle cx="{a}" cy="{b}" r="{proyecto.diseno.tornillo / 2:.2f}" fill="none" stroke="#000" stroke-width="0.4"/>'
                      f'<path d="M{float(a) - 5:.2f},{b} h10 M{a},{float(b) - 5:.2f} v10" stroke="#000" stroke-width="0.2"/>')
        if not es_placa:
            c = r.letra.forma.representative_point()
            a, b = pt(c.x, c.y).split(",")
            el.append(f'<text x="{a}" y="{b}" font-size="6" text-anchor="middle" fill="#1f4e8c">{escape(r.letra.codigo)}</text>')
    el.append(f'<text x="{m / 2:.1f}" y="{alto - 4:.1f}" font-size="4" fill="#555">Escala 1:1 · medidas en mm · '
              f'{ancho - 2 * m:.0f} × {alto - 2 * m:.0f} mm · + cable · o separador · o violeta fijación · -- corte</text>')
    el.append("</svg>")
    return "\n".join(el) + "\n"
