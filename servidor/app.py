"""Servidor de Letreros 3D Studio: la web (index.html) + la API del motor en el mismo puerto.

Variables de entorno (todas opcionales, se configuran en Coolify):
- LETREROS_CLAVE: si existe, la API exige la cabecera `X-Clave` con este valor.
- LETREROS_CONCURRENCIA: trabajos de geometría simultáneos (def. 2).
- LETREROS_PETICIONES_MIN: peticiones de generación por IP y minuto (def. 30).
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import secrets
import tempfile
import time
import unicodedata
from collections import defaultdict, deque
from dataclasses import replace
from pathlib import Path

import numpy as np

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

import letreros_motor as lm
from letreros_motor.diseno import _RANGOS, ESTRUCTURAS, Diseno
from letreros_motor.estructuras import ResultadoLetra
from letreros_motor.web import ESTILO_A_ESTRUCTURA, FUENTES_WEB, diseno_desde_web

RAIZ = Path(__file__).resolve().parent.parent
INDEX = RAIZ / "index.html"
MAX_CUERPO = 20_000  # bytes de JSON por petición
TIEMPO_MAX = 90  # s por trabajo
TRIANGULOS_VISOR_MAX = 600_000
VENDOR = Path(__file__).resolve().parent / "estaticos" / "vendor"

CLAVE = os.getenv("LETREROS_CLAVE", "")
SEMAFORO = asyncio.Semaphore(max(1, int(os.getenv("LETREROS_CONCURRENCIA", "2"))))
LIMITE_MIN = max(1, int(os.getenv("LETREROS_PETICIONES_MIN", "30")))
_historial: dict[str, deque] = defaultdict(deque)

CABECERAS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' "
        "https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data: blob:; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    ),
}

app = FastAPI(title="Letreros 3D Studio", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/vendor", StaticFiles(directory=VENDOR), name="vendor")


class ErrorPeticion(Exception):
    def __init__(self, estado: int, mensaje: str):
        self.estado, self.mensaje = estado, mensaje


@app.exception_handler(ErrorPeticion)
async def _manejar(_: Request, e: ErrorPeticion):
    return JSONResponse({"error": e.mensaje}, status_code=e.estado)


@app.middleware("http")
async def _cabeceras(request: Request, siguiente):
    respuesta = await siguiente(request)
    for k, v in CABECERAS.items():
        respuesta.headers.setdefault(k, v)
    return respuesta


def _ip(request: Request) -> str:
    # Detrás del proxy de Coolify, la última entrada de X-Forwarded-For la añade el proxy.
    xff = request.headers.get("x-forwarded-for", "")
    return xff.split(",")[-1].strip() if xff else (request.client.host if request.client else "?")


async def _leer_proyecto(request: Request) -> dict:
    if CLAVE and not secrets.compare_digest(request.headers.get("x-clave", ""), CLAVE):
        raise ErrorPeticion(401, "Clave incorrecta o ausente.")
    ip, ahora = _ip(request), time.monotonic()
    marcas = _historial[ip]
    while marcas and ahora - marcas[0] > 60:
        marcas.popleft()
    if len(marcas) >= LIMITE_MIN:
        raise ErrorPeticion(429, "Demasiadas peticiones; espera un minuto.")
    marcas.append(ahora)
    cuerpo = await request.body()
    if len(cuerpo) > MAX_CUERPO:
        raise ErrorPeticion(413, "Proyecto demasiado grande.")
    try:
        datos = json.loads(cuerpo or b"{}")
    except ValueError:
        raise ErrorPeticion(400, "El cuerpo no es JSON válido.") from None
    if not isinstance(datos, dict):
        raise ErrorPeticion(400, "Se esperaba un objeto JSON.")
    return datos


async def _trabajo(funcion, *args):
    async with SEMAFORO:
        try:
            return await asyncio.wait_for(run_in_threadpool(funcion, *args), TIEMPO_MAX)
        except asyncio.TimeoutError:
            raise ErrorPeticion(503, "La generación tardó demasiado; reduce el texto o la precisión.") from None
        except (lm.ErrorEntrada, ValueError) as e:
            raise ErrorPeticion(422, str(e)) from None
        except lm.ErrorGeometria as e:
            raise ErrorPeticion(500, f"Error de geometría: {e}") from None


def _slug(texto: str) -> str:
    base = unicodedata.normalize("NFD", texto)
    base = "".join(c for c in base if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9]+", "-", base).strip("-")[:40] or "letrero"


def _zip(proyecto: lm.Proyecto, nombre: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        ruta = lm.exportar(proyecto, Path(tmp) / nombre, comprimir=True)
        return Path(ruta).read_bytes()


def _cama_de(proyecto: lm.Proyecto) -> dict:
    return {id(col.pieza): (c, col) for c in proyecto.camas() for col in c.colocaciones}


def _informe(proyecto: lm.Proyecto) -> dict:
    camas = _cama_de(proyecto)
    return {
        "resumen": proyecto.resumen(),
        "avisos": proyecto.avisos,
        "piezas": [
            {"archivo": p.archivo, "rol": p.rol, "caracter": p.letra.caracter, "cama": camas[id(p)][0].numero,
             "medidas_mm": [round(float(v), 1) for v in p.malla.extents], "peso_g": round(p.peso_g, 1)}
            for p in proyecto.piezas
        ],
        "camas": [{"numero": c.numero, "material": c.material, "piezas": len(c.colocaciones),
                   "peso_g": round(c.peso_g, 1), "archivo": c.archivo} for c in proyecto.camas()],
        "peso_g": round(proyecto.peso_g, 1),
        "metros_led": round(proyecto.metros_led, 2),
        "estructura": proyecto.diseno.estructura,
        "costes": proyecto.costes(),
    }


# Piezas que se imprimen boca abajo: para verlas montadas se reflejan en Z.
_VOLTEAR = {("frontal", "frente"), ("halo", "cuerpo")}


def _modelo(datos: dict) -> dict:
    d = diseno_desde_web(datos)
    d = replace(d, tolerancia=max(d.tolerancia, 0.12))  # vista algo más ligera que la fabricación
    proyecto = lm.generar_letrero(d)
    if sum(len(p.malla.faces) for p in proyecto.piezas) > TRIANGULOS_VISOR_MAX:
        raise lm.ErrorEntrada("Demasiado detalle para el visor; reduce el texto.")
    piezas, minimo, maximo = [], np.full(3, np.inf), np.full(3, -np.inf)
    camas = _cama_de(proyecto)
    for p in proyecto.piezas:
        v = np.asarray(p.malla.vertices, dtype=np.float32).copy()
        f = np.asarray(p.malla.faces, dtype=np.uint32).copy()
        montaje = np.eye(4)  # de la pose de impresión a la pose montada
        if (d.estructura, p.rol) in _VOLTEAR:
            v[:, 2] = d.profundidad - v[:, 2]
            f = f[:, [0, 2, 1]].copy()
            montaje[2, 2], montaje[2, 3] = -1.0, d.profundidad
        elif p.rol == "empalme":  # va pegado por dentro: sobre el fondo, o detrás del frente en halo
            dz = (d.profundidad - d.frente - float(v[:, 2].max())) if d.estructura == "halo" else d.fondo
            v[:, 2] += dz
            montaje[2, 3] = dz
        elif p.rol == "placa":  # detrás de las letras
            v[:, 2] -= d.placa_grosor
            montaje[2, 3] = -d.placa_grosor
        cama, col = camas[id(p)]
        a_cama = col.matriz @ np.linalg.inv(montaje)  # de la pose montada a su sitio en la cama
        minimo, maximo = np.minimum(minimo, v.min(0)), np.maximum(maximo, v.max(0))
        piezas.append({
            "archivo": p.archivo, "rol": p.rol, "caracter": p.letra.caracter, "parte": p.parte,
            "unidad": p.letra.indice, "cama": cama.numero, "m_cama": [round(float(x), 5) for x in a_cama.T.ravel()],
            "v": base64.b64encode(v.tobytes()).decode(), "i": base64.b64encode(f.tobytes()).decode(),
        })
    return {
        "estructura": d.estructura, "profundidad": d.profundidad, "separacion": d.separacion,
        "cama": list(d.cama), "costes": proyecto.costes(),
        "minimo": [round(float(x), 2) for x in minimo], "maximo": [round(float(x), 2) for x in maximo],
        "piezas": piezas, **{k: v for k, v in _informe(proyecto).items() if k != "piezas"},
    }


def _descarga(contenido: bytes, nombre: str) -> Response:
    return Response(contenido, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}.zip"', "Cache-Control": "no-store"})


# --------------------------------------------------------------------------- rutas

@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
def inicio():
    return FileResponse(INDEX, media_type="text/html", headers={"Cache-Control": "no-cache"})


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/api/salud")
def salud():
    return {"ok": True, "motor": lm.__version__}


@app.get("/api/opciones")
def opciones():
    return {
        "motor": lm.__version__,
        "protegido": bool(CLAVE),
        "estructuras": ESTRUCTURAS,
        "estilos_fabricables": {k: v for k, v in ESTILO_A_ESTRUCTURA.items() if v},
        "fuentes_fabricables": list(FUENTES_WEB),
        "rangos": {k: list(v) for k, v in _RANGOS.items()},
        "defecto": Diseno("A").como_dict(),
    }


@app.post("/api/comprobar")
async def comprobar(request: Request):
    datos = await _leer_proyecto(request)
    proyecto = await _trabajo(lambda: lm.generar_letrero(diseno_desde_web(datos)))
    return _informe(proyecto)


@app.post("/api/modelo")
async def modelo(request: Request):
    datos = await _leer_proyecto(request)
    return await _trabajo(_modelo, datos)


@app.post("/api/letrero")
async def letrero(request: Request):
    datos = await _leer_proyecto(request)

    def tarea():
        d = diseno_desde_web(datos)
        nombre = f"{_slug(d.texto)}-{d.estructura}"
        return _zip(lm.generar_letrero(d), nombre), nombre

    contenido, nombre = await _trabajo(tarea)
    return _descarga(contenido, nombre)


@app.post("/api/probeta")
async def probeta(request: Request):
    datos = await _leer_proyecto(request)

    def tarea():
        base = diseno_desde_web({**datos, "style": "front", "font": "Montserrat", "letters": "P"})
        piezas, avisos, d = lm.generar_probeta(base)
        proyecto = lm.Proyecto(d, [ResultadoLetra(piezas[0].letra, piezas)], avisos)
        return _zip(proyecto, "probeta-holguras")

    return _descarga(await _trabajo(tarea), "probeta-holguras")
