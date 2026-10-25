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
from .fuentes import obtener_fuente
from .texto import maquetar

INSTRUCCIONES = {
    ("maciza", "cuerpo"): "Cara visible hacia arriba. Relleno 10-15 %.",
    ("caja", "cuerpo"): "Fondo sobre la cama, paredes hacia arriba. Sin soportes.",
    ("frontal", "cuerpo"): "Fondo sobre la cama, paredes hacia arriba. Color opaco. Sin soportes.",
    ("frontal", "frente"): "Cara visible sobre la cama, faldón hacia arriba. PETG blanco o natural para difundir la luz.",
    ("halo", "cuerpo"): "Cara visible sobre la cama, separadores hacia arriba. Color opaco. Sin soportes.",
}


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

    def resumen(self) -> str:
        d = self.diseno
        minx = min(r.letra.forma.bounds[0] for r in self.letras)
        maxx = max(r.letra.forma.bounds[2] for r in self.letras)
        miny = min(r.letra.forma.bounds[1] for r in self.letras)
        maxy = max(r.letra.forma.bounds[3] for r in self.letras)
        lineas = [
            f"Letrero «{d.texto}» · {d.estructura} ({ESTRUCTURAS[d.estructura]})",
            f"Mayúscula {d.altura:g} mm · conjunto {maxx - minx:.1f} × {maxy - miny:.1f} × {d.profundidad:g} mm",
            f"Piezas: {len(self.piezas)} · material ≈ {self.peso_g:.0f} g de PETG (sólido al 100 %; el laminador dará el dato real)",
        ]
        if self.metros_led:
            led = f"Tira LED {d.ancho_tira:g} mm: ≈ {self.metros_led:.2f} m (estimación por perímetro interior / 2)"
            if d.w_por_metro:
                led += f" · consumo nominal ≈ {self.metros_led * d.w_por_metro:.1f} W"
            lineas.append(led)
        lineas += [f"AVISO: {a}" for a in self.avisos]
        return "\n".join(lineas)


def generar_letrero(diseno: Diseno) -> Proyecto:
    d, avisos = validar(diseno)
    fuente = obtener_fuente(d.fuente)
    letras = maquetar(d.texto, fuente.ruta, d.altura, d.espaciado, d.tolerancia)
    resultados = [construir_letra(l, d) for l in letras]
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
        if not existentes <= {p.archivo for p in proyecto.piezas} | {"ficha.json", "LEEME.txt"}:
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
        },
        "montaje": [
            {"orden": r.letra.indice, "caracter": r.letra.caracter,
             "x_mm": round(r.letra.forma.bounds[0], 2), "y_mm": round(r.letra.forma.bounds[1], 2),
             "ancho_mm": round(r.letra.forma.bounds[2] - r.letra.forma.bounds[0], 2),
             "alto_mm": round(r.letra.forma.bounds[3] - r.letra.forma.bounds[1], 2),
             "hueca": r.hueca}
            for r in proyecto.letras
        ],
        "piezas": [
            {"archivo": p.archivo, "caracter": p.letra.caracter, "rol": p.rol,
             "medidas_mm": _medidas(p.malla), "volumen_cm3": round(p.volumen_cm3, 2),
             "peso_g": round(p.peso_g, 1), "triangulos": int(len(p.malla.faces)),
             "impresion": INSTRUCCIONES.get((d.estructura, p.rol), "")}
            for p in proyecto.piezas
        ],
        "avisos": proyecto.avisos,
    }
    (carpeta / "ficha.json").write_text(json.dumps(ficha, ensure_ascii=False, indent=2), encoding="utf-8")
    (carpeta / "LEEME.txt").write_text(_leeme(proyecto, ficha), encoding="utf-8")

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
        partes.append(f"  {rol}: {INSTRUCCIONES.get((d.estructura, rol), '')}")
    partes += ["", "MONTAJE (izquierda → derecha, medido desde el borde izquierdo de la primera letra)"]
    x0 = min(m["x_mm"] for m in ficha["montaje"])
    for m in ficha["montaje"]:
        partes.append(f"  {m['orden']:02d} «{m['caracter']}»  x = {m['x_mm'] - x0:7.1f} mm  ancho {m['ancho_mm']:6.1f} mm")
    if d.estructura == "frontal":
        partes += ["", f"Frente a presión con holgura {d.holgura:g} mm: calibrar antes con `python -m letreros_motor probeta`."]
    if d.estructura == "halo":
        partes += ["", f"Separadores de {d.separacion:g} mm con agujero Ø{d.tornillo:g} mm para taco/tornillo a pared."]
    partes += ["", "Medidas verificadas como sólidos cerrados (manifold). Comprobar en Bambu Studio antes de imprimir."]
    return "\n".join(partes) + "\n"
