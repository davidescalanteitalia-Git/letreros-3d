# CLAUDE.md — Instrucciones para Claude Code

## Identidad del proyecto
Letreros 3D Studio, software independiente de rotulación y producción FDM. Usuario final de habla española. Repositorio: davidescalanteitalia-Git/letreros-3d, rama main. Sitio publicado: https://letreros.d4digitalstudio.it. Infraestructura: Coolify alojado en Hetzner; DNS mediante Cloudflare. No asumir que Claude tenga acceso a esos servicios o sus tokens.

## REALIDAD VERIFICADA (2026-10-25)
- `index.html` v0.4: editor en español + pestaña Fabricar STL conectada a la API (comprobar, visor 3D three.js con geometría real, ZIP de piezas, probeta). Vista SVG sigue siendo ilustrativa.
- `servidor/`: FastAPI que sirve index.html y la API (/api/salud, /api/opciones, /api/comprobar, /api/modelo, /api/letrero, /api/probeta); clave opcional LETREROS_CLAVE, límites de tamaño/tiempo/IP, CSP. three.js 0.170 local en servidor/estaticos/vendor (MIT).
- `Dockerfile`: python:3.13-slim, usuario no root, uvicorn en puerto 80, healthcheck /api/salud. Misma configuración de Coolify que antes.
- `docs/`: análisis comparativo y roadmaps; no equivale a código desarrollado.
- `config/PERFIL_A2L_PETG.md`: Bambu Lab A2L, boquilla 0.4 mm, PETG; medidas nominales 330×320×325 mm; corroborar antes de generar.
- `.github/workflows/verificar-coolify.yml`: prueba manual de conexión API solo lectura, con secreto COOLIFY_API_TOKEN; no despliega.
- Se observó despliegue de la v0.1 healthy en Coolify y una captura del sitio online; no afirmar que la v0.3 esté en producción sin comprobar versión publicada.
- `motor/` (M2, 2026-10-25): motor Python local (fontTools + shapely + manifold3d + trimesh). Texto de una línea con altura de mayúscula; estructuras maciza/caja/frontal (frente a presión)/halo (separadores); validaciones; probeta de holguras; STL por pieza + ficha.json + LEEME. 125 pruebas pytest + CI. M1 STL verificado abriendo en Bambu Studio (A 120×35 y 40×5).
- No existe aún: división por cama, 3MF, DXF de acrílico, otras fuentes para CAD, neón/doble luz, base de datos ni cuentas.

## Trabajo esperado
1. Inspeccionar árbol, código y commits antes de cambiar nada; correr tests cuando existan.
2. Hacer auditoría de seguridad y arquitectura; priorizar prototipo real que cree STL verificable de UNA letra.
3. Separar vista previa decorativa de geometría CAD auténtica. Añadir controles de entradas y errores.
4. Implementar progresivamente: contornos tipográficos en mm → sólido extruido manifold → STL → caja hueca → tapa/fondo → pruebas PETG → conjuntos multi-letra/SVG → conectores y división → luz frontal/halo/doble/neón → costes y gestión.
5. Para cada función, definir pruebas automatizadas, muestras imprimibles, límites y documentación de uso. No declarar compatibilidad sin verificar en Bambu Studio.
6. Trabajar en rama nueva feat/*; hacer cambios pequeños, commits claros y PR. No sobrescribir main sin revisión del propietario.
7. Nunca activar despliegues automáticos, editar infraestructura, DNS, permisos o configuraciones de producción sin autorización explícita.
8. Nunca solicitar ni volcar claves API en chat, GitHub, logs, capturas o código. Usar secretos del proveedor con permisos mínimos. Claves expuestas anteriormente deben revocarse.

## Arquitectura futura propuesta, NO implementada
React + TypeScript + Three.js (editor real); FastAPI + Python + CadQuery/OpenCascade (motor sólido); generador STL, validación trimesh; modelos tipográficos vectorizados con licencias revisadas; backend separado en Coolify. Opcional: Supabase para cuentas e histórico, Cloudflare Access para privacidad, GitHub Actions CI. Diseñar antes de añadir servicios.

## Modalidades deseadas
Frontal iluminada; halo posterior; doble frontal + posterior; neonflex; caja hueca sin luz; corpórea maciza; frente opaco con cuerpo iluminado; conjuntos unidos; placa común; logotipos SVG. Deben parametrizarse sin prometer fabricación hasta tener motor CAD.

## Fuentes UI actuales
Montserrat, Poppins, Roboto, Oswald, Bebas Neue, Playfair Display, Lobster, Pacifico, Dancing Script, Great Vibes. La carga de Google Fonts en el navegador no suministra contornos deterministas para CAD. Revisar OFL/licencia y capacidad de trazos mínimos antes de implementar exportación.

## Impresora y prototipado
Bambu Lab A2L; boquilla 0.4 mm; PETG; cama nominal 330×320×325 mm. Margen XY 5 mm/lado y 0.25 mm holgura son HIPÓTESIS a calibrar. Probar una letra y diferentes holguras; evitar ajustes eléctricos y cálculos LED no fundamentados.

## Criterios mínimos de calidad
- Dimensiones reales, coherencia mm, STL manifold, contornos interiores preservados, pruebas unitarias, tests de extracción y slicer.
- Para letras largas: orientación, segmentación, uniones, mapa de montaje y cada pieza dentro del volumen real.
- Para exterior/LED: temperatura, UV, agua, disipación, fuente/alimentación y fijaciones verificadas.
- No copiar código, diseño UI exacto ni algoritmos de LetraMaker/otros productos propietarios.

## Documentación de referencia en el repo
Leer: `docs/GUIA_TRASPASO_CLAUDE_CODE.md`, `docs/01_ANALISIS_COMPETITIVO.md`, `docs/02_ESPECIFICACION_PROFESIONAL.md`, `docs/03_HOJA_DE_RUTA.md`, `docs/04_CATALOGO_FUNCIONAL.md`, `config/PERFIL_A2L_PETG.md`.

## Primera solicitud sugerida al agente
“Examina el repositorio completo y presenta un informe de discrepancias entre lo implementado y lo planificado. Propón arquitectura mínima y un PR pequeño para generar STL auténtico de una letra con pruebas. No despliegues en producción ni modifiques secrets, DNS o infraestructura.”
