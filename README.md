# Letreros 3D Studio

Aplicación propia para diseño y futura fabricación de letreros corpóreos impresos en 3D.

## Estado actual (v0.4)
**Web + motor en un solo contenedor.** `letreros.d4digitalstudio.it` sirve el editor (`index.html`) y la API del motor (`servidor/app.py`, FastAPI):
- Diseñar: texto, fuente, medidas, estructura; guardar/abrir proyecto JSON; boceto SVG.
- **Fabricar STL**: comprobar el diseño (medidas reales, peso PETG, metros de LED, avisos por letra), **visor 3D de la geometría real** (vista explotada, corte, luz encendida), descargar todas las piezas en ZIP (STL por pieza + `LEEME.txt` con montaje + `ficha.json`) y la probeta de holguras.
- Fabricable hoy: Montserrat Bold en frontal (frente a presión), halo (separadores), caja y maciza. Neón, doble luz, frente opaco, otras fuentes y división de letras grandes: próximas versiones.

El motor también se usa sin web desde PowerShell: ver `motor/README.md`.

## Usar en local
```powershell
cd motor; python -m venv .venv; .venv\Scripts\activate; cd ..
pip install -r motor/requirements.txt -r servidor/requirements.txt
$env:PYTHONPATH="motor"; uvicorn servidor.app:app --port 8000
```
Abre http://localhost:8000. Pruebas: `python -m pytest -q motor/tests servidor/tests`.

## Producción (Coolify)
La configuración de Coolify **no cambia**: build pack Dockerfile, `/Dockerfile`, rama `main`, puerto interno **80**. El nuevo `Dockerfile` (Python 3.13 slim, usuario sin privilegios, healthcheck contra `/api/salud`) sustituye al nginx anterior. Tras fusionar en `main`, pulsar **Redeploy** si el despliegue automático no está activo.

Variables de entorno opcionales (Coolify → Environment Variables):
| Variable | Def. | Uso |
|---|---|---|
| `LETREROS_CLAVE` | vacío | Si se define, la API pide esta clave (la web la solicita una vez por sesión). Recomendado mientras el sitio sea público. |
| `LETREROS_CONCURRENCIA` | 2 | Trabajos de geometría simultáneos. |
| `LETREROS_PETICIONES_MIN` | 30 | Peticiones de generación por IP y minuto. |

Seguridad incluida: cabeceras CSP/nosniff/frame-deny, límite de tamaño de petición (20 kB) y de tiempo (90 s), límite por IP, sin documentación de API pública, three.js servido localmente (sin CDN). Para que solo tú accedas, la opción más sólida sigue siendo Cloudflare Access delante del dominio.

## Arquitectura futura
React + TypeScript + Three.js en frontend; FastAPI + motor CAD para export STL, bajo pruebas de medidas y validación de malla. Véase `docs/02_ESPECIFICACION_PROFESIONAL.md`.

## Pendiente
- Imprimir la probeta de holguras en PETG y fijar el valor por defecto real.
- Verificar en Bambu Studio y en pieza física las estructuras frontal y halo.
- División de letras más grandes que la cama (colas de milano), más fuentes con licencia, kerning y varias líneas.
- Acrílico + DXF, neón flex y doble luz.
