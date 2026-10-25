# Informe de auditoría — implementado vs. planificado
Fecha: 25-10-2026 · Rama: `feat/motor-stl-una-letra` · Base: `main` @ 942202d (14 commits)

## 1. Estado real
| Área | Planificado (docs) | Implementado en `main` | Tras este PR |
|---|---|---|---|
| Editor web | React + TS + Three.js | `index.html` único v0.3, JS sin dependencias, vista SVG decorativa | sin cambios |
| Contornos tipográficos | Fuentes con licencia, curvas en mm | Google Fonts por CSS (solo visual) | Montserrat Bold OFL versionada, contornos → mm |
| Sólido / STL | CadQuery/OCC, STL manifold | No existe | Letra maciza extruida, STL validado |
| Contornos interiores | Preservar A, B, O, P | No aplica | Sí, con pruebas de topología |
| Caja hueca, tapa, fondo | M2 | No | No |
| División, conectores | M4 | Solo texto en la UI | No |
| Iluminación (frontal, halo, neón) | M4 | Selector visual | No |
| Backend / API | FastAPI | No | No (CLI + librería, lista para envolver en API) |
| Pruebas / CI | Unitarias, lint, CI | Ninguna | 79 pruebas pytest + workflow en PR |
| Datos | JSON → Supabase opcional | JSON local `schema_version: 1` | sin cambios |
| Despliegue | Docker frontend + backend separado | nginx con `index.html` | sin cambios (el motor no entra en la imagen) |

## 2. Discrepancias encontradas
1. **Versiones desalineadas:** `README.md` dice "Prototipo visual v0.1", `03_HOJA_DE_RUTA.md` habla de v0.2 e `index.html` es v0.3. Este PR actualiza el README.
2. **"Altura" sin definición** en la UI y el JSON. El motor fija la convención: altura = contorno real del glifo (de su punto más bajo al más alto). La vista SVG usa `font-size`, que no equivale; habrá que alinearla cuando la UI consuma el motor.
3. **Fuentes:** la UI ofrece 10 familias, el motor solo 1 versionada. Hay que añadir las otras 9 con su OFL y SHA-256 antes de permitir STL con ellas. Las manuscritas (Great Vibes, Dancing Script) tienen trazos finos: el aviso de boquilla 0,4 mm lo detectará a alturas pequeñas.
4. **Materiales:** la UI ofrece ASA y PLA, pero el único perfil existente es PETG.
5. **Rangos de la UI vs. la máquina:** la UI acepta 1500 mm de altura y holgura 0; sin división, el motor rechaza lo que no cabe en 320 × 310 × 325 mm.
6. **Arquitectura:** el plan prevé CadQuery/OpenCascade. Para extruir contornos planos y hacer offsets de pared bastan shapely + trimesh, mucho más ligeros. Se propone posponer OCC hasta necesitar chaflanes, redondeos o booleanas 3D complejas.
7. **Historial:** varios commits duplicados con el mismo mensaje (`docs: preparar traspaso…`, `feat: añadir prototipo web…`). Es cosmético.

## 3. Seguridad
- **Sin secretos en el historial git** (búsqueda en todos los commits de patrones de token, bearer, api_key, password, ghp_ y sk-).
- **Claves compartidas antes por chat (Coolify, Hetzner):** este informe no puede comprobar si se revocaron. Si no se ha hecho, hay que revocarlas.
- **Repositorio público con datos de infraestructura:** `GUIA_TRASPASO_CLAUDE_CODE.md` publica la URL del panel Coolify y la IP del servidor. Recomendación: hacer privado el repo (antes, configurar el acceso de Coolify) o mover esos datos fuera del repo; poner el panel de Coolify detrás de Cloudflare Access o una lista de IPs.
- **Workflow `verificar-coolify.yml`:** correcto (manual, `contents: read`, token solo en env). Usar un token de solo lectura.
- **`index.html`:** no hay XSS (usa `textContent`, el SVG se exporta escapado y el JSON se limita a 20 kB). Pero los valores del JSON no se validan contra las opciones: una fuente desconocida deja el selector vacío.
- **Google Fonts remoto:** envía la IP del visitante a Google. En Italia/UE hay precedente (LG München, 2022) de que eso exige consentimiento. Recomendación: servir las fuentes desde el propio sitio.
- **nginx:** sin cabeceras de seguridad (CSP, X-Content-Type-Options, Referrer-Policy). Mejora pequeña y sin riesgo para un PR aparte.

## 4. Arquitectura mínima propuesta
```
index.html (estático, nginx)  ──fase 2──►  API FastAPI (contenedor separado en Coolify)
                                                   │
                                           motor/letreros_motor  (librería Python pura)
                                             fuentes.py   registro de fuentes con licencia + SHA-256
                                             contornos.py glifo → polígonos en mm (shapely)
                                             generador.py validación → extrusión → malla → STL (trimesh)
```
Orden: (1) este PR, una letra maciza; (2) caja hueca = contorno − offset de pared, más fondo separado; (3) probeta de holguras PETG; (4) palabra completa con kerning y una pieza por letra; (5) API FastAPI con límites de tamaño y tiempo; (6) conectar el botón "Fabricar STL" de la UI.

## 5. Pendiente de verificación humana
- Abrir `A.stl` en Bambu Studio: medidas 134,57 × 120,00 × 35,00 mm, sin aviso de reparación.
- Imprimir una muestra pequeña (`--altura 40 --profundidad 5`) y medirla con calibre.
- Confirmar si la versión publicada en letreros.d4digitalstudio.it es la v0.3 (no se ha comprobado).
