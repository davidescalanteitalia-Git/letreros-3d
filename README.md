# Letreros 3D Studio

Aplicación propia para diseño y futura fabricación de letreros corpóreos impresos en 3D.

## Estado actual (v0.9)
**Web + motor en un solo contenedor.** `letreros.d4digitalstudio.it` sirve el editor (`index.html`) y la API del motor (`servidor/app.py`, FastAPI):
- Diseñar: texto, fuente, medidas, estructura; guardar/abrir proyecto JSON; boceto SVG.
- **Fabricar STL**: comprobar el diseño (medidas reales, peso PETG, metros de LED, avisos por letra), **visor 3D de la geometría real** (vista explotada, corte, luz encendida), descargar todas las piezas en ZIP (STL por pieza + `LEEME.txt` con montaje + `ficha.json`) y la probeta de holguras.
- **10 fuentes fabricables** (OFL): Montserrat, Poppins, Roboto, Oswald, Bebas Neue, Playfair Display, Lobster, Pacifico, Dancing Script y Great Vibes. Composición con **HarfBuzz**: kerning, ligaduras y enlaces de las manuscritas.
- **Construcción del conjunto**: letras sueltas · **unidas** (una pieza por palabra con puentes automáticos y barra inferior opcional) · **sobre placa común** (rectangular o silueta, siluetas grabadas para pegar cada letra, agujeros de fijación y de cable).
- **División automática por cama**: lo que no cabe se corta en vertical por los puntos más estrechos; macizas con cola de milano, huecas con placa de empalme interior; partes A, B, C….
- **Varias líneas** (hasta 4, alineación izquierda/centro/derecha e interlineado).
- **División en rejilla**: también en horizontal cuando la pieza es más alta que la cama (partes A1, B1, A2…; empalmes A1A2…).
- **Camas listas para Bambu Studio**: el ZIP trae `camas/cama-NN-opaco.3mf` y `…-difusor.3mf` con las piezas ya colocadas y separadas por filamento; el visor 3D tiene «Ver camas de impresión».
- **Contornos DXF 1:1** (`contornos.dxf`, mm) para cortar a láser el frente de metacrilato de la caja, vinilo o plantillas.
- **Plantilla de montaje 1:1** (`plantilla-montaje.svg`) y **presupuesto** de filamento y LED.
- **Vista 3D en vivo** (v0.9) en la pantalla de diseño: al cambiar texto, fuente, medidas, estructura o logo, la geometría real se actualiza sola (con pausa de ~1 s; interruptor «3D en vivo»).
- **Logotipos SVG o DXF** (v0.9): sube el logo del negocio y se fabrica con la misma estructura que las letras (hueco con luz, neón, maciza…). Alto, posición (izquierda, derecha, encima, debajo) y separación; también logo solo, sin texto. El proyecto JSON guarda el logo.
- **Tiempo de impresión estimado** por cama y total, y **ajustes recomendados de Bambu Studio** (A2L + PETG) en el LEEME.
- **Letras unidas por piezas** (v0.8): elige cuántas letras lleva cada pieza (p. ej. «aperto» → ap · er · to). Las piezas se unen con cola de milano (macizas) o placa de empalme interior + **tapas desplazadas** que cruzan la junta (huecas); el cable pasa por dentro de los puentes y sale por **un solo agujero** al principio o al final.
- **8 estructuras**: frontal (frente a presión), halo (separadores), caja, maciza, **lateral iluminado** (frente opaco, cuerpo translúcido), **doble luz** (frente y trasera translúcidos, separadores metálicos), **neón flex** (base o placa común con canal a la medida del neón) y **caja de luz** (caja con galce, guías de tira, colgadores; difusor con letras en relieve + máscara calada a ras).
- **Luz e instalación**: filas de LED según la distancia a la cara, metros por letra, consumo, amperios, fuente con 20 % de margen y puntos de alimentación (con los W/m de tu tira).
- **Fijaciones**: torretas para inserto roscado M4, agujeros pasantes avellanados o colgadores, marcados en la plantilla de taladro.

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
- Probar en pieza física la cola de milano, la placa de empalme y la rejilla; abrir las camas 3MF en Bambu Studio.
- Probar en pieza física: neón en su canal, caja de luz (encaje máscara/difusor), torretas de inserto.
- Logotipos SVG.
