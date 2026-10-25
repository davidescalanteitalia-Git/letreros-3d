"""Letrero completo: maquetar, construir todas las letras y exportar el paquete."""
from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
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
    ("maciza", "cuerpo"): "Cara visible hacia arriba. Relleno 10-15 %.",
    ("caja", "cuerpo"): "Fondo sobre la cama, paredes hacia arriba. Sin soportes.",
    ("frontal", "cuerpo"): "Fondo sobre la cama, paredes hacia arriba. Color opaco. Sin soportes.",
    ("frontal", "frente"): "Cara visible sobre la cama, faldón hacia arriba. PETG blanco o natural para difundir la luz.",
    ("halo", "cuerpo"): "Cara visible sobre la cama, separadores hacia arriba. Color opaco. Sin soportes.",
}
INSTRUCCIONES_ROL = {
    "empalme": "Plana sobre la cama. Se pega por dentro cruzando la junta de las dos partes (fondo o frente).",
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

    def costes(self) -> dict:
        d = self.diseno
        material = self.peso_g / 1000 * d.precio_kg
        led = self.metros_led * d.precio_led_m
        return {"material_eur": round(material, 2), "led_eur": round(led, 2), "total_eur": round(material + led, 2)}

    def medidas(self) -> tuple[float, float, float, float]:
        fs = [r.letra.forma for r in self.letras]
        return (min(f.bounds[0] for f in fs), min(f.bounds[1] for f in fs),
                max(f.bounds[2] for f in fs), max(f.bounds[3] for f in fs))

    def resumen(self) -> str:
        d = self.diseno
        minx, miny, maxx, maxy = self.medidas()
        from .conjunto import CONJUNTOS
        lineas = [
            f"Letrero «{d.texto}» · {d.estructura} ({ESTRUCTURAS[d.estructura]})",
            f"Fuente {obtener_fuente(d.fuente).nombre} · conjunto {d.conjunto} ({CONJUNTOS[d.conjunto]})",
            f"Mayúscula {d.altura:g} mm · conjunto {maxx - minx:.1f} × {maxy - miny:.1f} × {d.profundidad:g} mm",
            f"Piezas: {len(self.piezas)} · material ≈ {self.peso_g:.0f} g de PETG (sólido al 100 %; el laminador dará el dato real)",
        ]
        if self.metros_led:
            led = f"Tira LED {d.ancho_tira:g} mm: ≈ {self.metros_led:.2f} m (estimación por perímetro interior / 2)"
            if d.w_por_metro:
                led += f" · consumo nominal ≈ {self.metros_led * d.w_por_metro:.1f} W"
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
    letras = maquetar(d.texto, d.fuente, d.altura, d.espaciado, d.tolerancia)
    unidades, avisos_conjunto = agrupar(letras, d)
    avisos += avisos_conjunto
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


def _medidas(malla: trimesh.Trimesh) -> list[float]:
    return [round(float(v), 2) for v in malla.extents]


def exportar(proyecto: Proyecto, carpeta: str | Path, comprimir: bool = False) -> Path:
    """Escribe un STL por pieza, ficha.json y LEEME.txt. Devuelve la carpeta (o el .zip)."""
    carpeta = Path(carpeta)
    if carpeta.exists() and any(carpeta.iterdir()):
        existentes = {p.name for p in carpeta.iterdir()}
        if not existentes <= {p.archivo for p in proyecto.piezas} | {"ficha.json", "LEEME.txt", "plantilla-montaje.svg"}:
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
        },
        "montaje": [
            {"orden": r.letra.indice, "caracter": r.letra.caracter,
             "x_mm": round(r.letra.forma.bounds[0], 2), "y_mm": round(r.letra.forma.bounds[1], 2),
             "ancho_mm": round(r.letra.forma.bounds[2] - r.letra.forma.bounds[0], 2),
             "alto_mm": round(r.letra.forma.bounds[3] - r.letra.forma.bounds[1], 2),
             "hueca": r.hueca, "cortes_x_mm": [round(x, 1) for x in r.cortes]}
            for r in proyecto.letras
        ],
        "piezas": [
            {"archivo": p.archivo, "caracter": p.letra.caracter, "rol": p.rol,
             "medidas_mm": _medidas(p.malla), "volumen_cm3": round(p.volumen_cm3, 2),
             "peso_g": round(p.peso_g, 1), "triangulos": int(len(p.malla.faces)),
             "parte": p.parte, "impresion": instrucciones(d.estructura, p.rol)}
            for p in proyecto.piezas
        ],
        "avisos": proyecto.avisos,
    }
    (carpeta / "ficha.json").write_text(json.dumps(ficha, ensure_ascii=False, indent=2), encoding="utf-8")
    (carpeta / "LEEME.txt").write_text(_leeme(proyecto, ficha), encoding="utf-8")
    (carpeta / "plantilla-montaje.svg").write_text(plantilla_svg(proyecto), encoding="utf-8")

    if comprimir:
        zip_path = carpeta.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(carpeta.iterdir()):
                z.write(f, f"{carpeta.name}/{f.name}")
        return zip_path
    return carpeta


def _leeme(proyecto: Proyecto, ficha: dict) -> str:
    d = proyecto.diseno
    partes = [proyecto.resumen(), "", "PIEZAS"]
    for p in ficha["piezas"]:
        x, y, z = p["medidas_mm"]
        partes.append(f"  {p['archivo']:<28} {x:>7.1f} × {y:>6.1f} × {z:>5.1f} mm  {p['peso_g']:>6.1f} g")
    partes += ["", "CÓMO IMPRIMIR"]
    for rol in sorted({p.rol for p in proyecto.piezas}):
        partes.append(f"  {rol}: {instrucciones(d.estructura, rol)}")
    partes += ["", "MONTAJE (izquierda → derecha, medido desde el borde izquierdo de la primera letra)"]
    x0 = min(m["x_mm"] for m in ficha["montaje"])
    for m in ficha["montaje"]:
        partes.append(f"  {m['orden']:02d} «{m['caracter']}»  x = {m['x_mm'] - x0:7.1f} mm  ancho {m['ancho_mm']:6.1f} mm")
    divididas = [m for m in ficha["montaje"] if m["cortes_x_mm"]]
    if divididas:
        partes += ["", "PIEZAS DIVIDIDAS (la cama no admite la pieza entera)"]
        for m in divididas:
            partes.append(f"  «{m['caracter']}»: cortes en x = {', '.join(f'{x - x0:.0f}' for x in m['cortes_x_mm'])} mm "
                          "(partes A, B, C… de izquierda a derecha; empalmes AB, BC… o colas de milano)")
    partes += ["", "PLANTILLA: plantilla-montaje.svg está a escala 1:1 (mm). Imprímela al 100 % para marcar en la pared "
               "la posición de cada pieza, los agujeros de cable (+) y los separadores (o)."]
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
          f'<title>Plantilla de montaje 1:1 · {escape(proyecto.diseno.texto)}</title>',
          '<rect width="100%" height="100%" fill="#fff"/>']
    for r in proyecto.letras:
        es_placa = r.letra.indice == 0 and r.letra.caracter == "base"
        el.append(f'<path d="{camino(r.letra.forma)}" fill="{"none" if es_placa else "#eef3fb"}" '
                  f'stroke="{"#999" if es_placa else "#1f4e8c"}" stroke-width="0.4" fill-rule="evenodd"/>')
        for x in r.cortes:
            el.append(f'<line x1="{x - minx + m:.2f}" y1="{m / 2:.2f}" x2="{x - minx + m:.2f}" y2="{alto - m / 2:.2f}" '
                      'stroke="#c0392b" stroke-width="0.4" stroke-dasharray="3 2"/>')
        for x, y in r.puntos_cable:
            a, b = pt(x, y).split(",")
            el.append(f'<path d="M{float(a) - 4:.2f},{b} h8 M{a},{float(b) - 4:.2f} v8" stroke="#000" stroke-width="0.4"/>')
        for x, y in r.puntos_separadores:
            a, b = pt(x, y).split(",")
            el.append(f'<circle cx="{a}" cy="{b}" r="{proyecto.diseno.tornillo / 2:.2f}" fill="none" stroke="#000" stroke-width="0.4"/>'
                      f'<path d="M{float(a) - 5:.2f},{b} h10 M{a},{float(b) - 5:.2f} v10" stroke="#000" stroke-width="0.2"/>')
        if not es_placa:
            c = r.letra.forma.representative_point()
            a, b = pt(c.x, c.y).split(",")
            el.append(f'<text x="{a}" y="{b}" font-size="6" text-anchor="middle" fill="#1f4e8c">{escape(r.letra.codigo)}</text>')
    el.append(f'<text x="{m / 2:.1f}" y="{alto - 4:.1f}" font-size="4" fill="#555">Escala 1:1 · medidas en mm · '
              f'{ancho - 2 * m:.0f} × {alto - 2 * m:.0f} mm · + cable · o separador · -- corte</text>')
    el.append("</svg>")
    return "\n".join(el) + "\n"
