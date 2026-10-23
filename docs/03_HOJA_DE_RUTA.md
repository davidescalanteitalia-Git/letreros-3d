# Hoja de ruta profesional — Letreros 3D Studio

Actualizado 2026-10-23. El sitio v0.2 es un prototipo visual funcional. Todavía no genera piezas CAD ni STL.

## Referencias públicas
- PROLED3D: TEXT/SVG -> STL/DXF/ZIP, cuerpos, tapas, bases y división. https://proled3d.com/
- LumiSign 3D: DXF, vista 3D y STL por componente. https://www.lumisign3d.com/
- Volucore: diseño paramétrico, segmentación para cama de impresión y uniones. https://volucore.net/
- Más plataformas y comparaciones: docs/01_ANALISIS_COMPETITIVO.md

## Funciones ya implementadas en v0.2
- Campos de proyecto, texto, medidas en mm, grosor de pared, holgura, material y color.
- Vista preliminar ilustrativa de estructuras frontal/halo/neón/maciza.
- Guardar y cargar proyectos como JSON local.
- Exportar boceto SVG con texto editable. No son contornos de corte ni geometría lista para imprimir.

## Próximos entregables y aceptación
### M1 — Motor CAD real
- API FastAPI y motor CAD (CadQuery/OpenCascade o alternativa).
- Entrada texto o vector autorizado, dimensiones en mm.
- Extrusión de sólido para una letra, exportación STL.
- Pruebas: malla cerrada y medidas válidas al cargar STL en Bambu Studio.

### M2 — Canal y tapa
- Contornos exteriores e interiores; sustracciones y offsets robustos.
- Cuerpo hueco, tapa y fondo como sólidos separados.
- Probetas para determinar ajuste por material y boquilla.
- Pruebas de impresión y medición con calibre.

### M3 — Editor profesional
- Importación SVG, tipografías autorizadas, vistas 3D con geometría CAD real.
- Mensajes de contornos inválidos y paredes demasiado delgadas.
- Historial de proyecto y export ZIP con metadatos.

### M4 — Producción
- Perfiles reales de impresora, segmentación, conectores y piezas numeradas.
- Frontal iluminado, efecto halo y neonflex con canal compatible.
- DXF para corte y costes reales a partir de slicer y materiales.

## Principios
- No copiar código propietario ni marcas comerciales de terceros.
- Repositorio privado, no incluir credenciales.
- No asumir el volumen de impresión de la máquina identificada por el usuario como A2L sin comprobar el modelo.
- Una vista bonita no certifica que el modelo pueda fabricarse.
- Los cambios de GitHub requieren un nuevo deploy de Coolify o configurar autodeploy.
