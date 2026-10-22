# Especificación profesional — plataforma de letreros 3D
Versión 0.1 · 22-10-2026 · Documento de planificación, no aplicación finalizada.

## Visión
Aplicación privada, en español, para convertir textos y logotipos propios en componentes físicos de letreros corpóreos fabricables con impresora FDM y, posteriormente, corte de acrílico. Objetivo: archivos dimensionalmente precisos y fabricación repetible, no solo renders atractivos.

## Usuario y trabajos
Usuario: propietario de un taller con impresora Bambu Lab (modelo exacto pendiente de confirmación). Uso inicial personal. Casos: letrero de negocio, letras separadas, letreros LED frontales/halo, neonflex, placas y logotipos. Piezas más grandes que la cama requieren división validada.

## Recorrido del producto
1. Nuevo proyecto → tipo de letrero.
2. Texto + fuente o SVG validado.
3. Unidades mm, altura, profundidad, grosor de pared, material, tapa y holgura.
4. Vista frontal, lateral, perspectiva, corte y vista explotada.
5. Motor geométrico genera componentes independientes.
6. Validación automática y alertas de geometría/fabricación.
7. Exportar STL en ZIP y manifiesto JSON con medidas, material y parámetros.
8. Abrir en Bambu Studio para laminar; imprimir una muestra de tolerancia.
9. Registrar prueba, ajustes y versión del proyecto.

## Arquitectura propuesta
- Frontend: React + TypeScript + Three.js para editor 2D/3D, entrada y revisión.
- Backend: FastAPI, trabajos de generación asíncronos y cola de tareas solo cuando el volumen lo requiera.
- Geometría: CadQuery/OpenCascade para sólidos B-Rep, booleans, offsets y triangulación; evaluar bibliotecas para tipografía y SVG respetando licencias.
- Validación: controles de contorno cerrado, autointersección, espesor mínimo, conectividad, malla manifold, caras invertidas, unidades y caja envolvente.
- Salida: STL por componente y ZIP con metadatos; DXF/3MF después de validar necesidades.
- Datos: archivos y parámetros locales al principio; Supabase opcional al añadir cuentas/histórico.
- Despliegue: Docker con Coolify en servidor propio; Cloudflare + subdominio + autenticación.
- Código: GitHub; ramas de funciones y revisiones antes de desplegar.

## Modelo de datos propuesto
Project(id, name, type, created_at, updated_at, revision)
SourceAsset(id, project_id, type[text/svg], checksum, original_name)
DesignParams(project_id, revision, text, font_id, height_mm, depth_mm, wall_mm, clearance_mm, back_mm, preset_id)
PrinterProfile(id, name, bed_x_mm, bed_y_mm, bed_z_mm, nozzle_mm, safety_margin_mm)
GeometryJob(id, revision, state, progress, error_code, duration_ms)
Part(id, job_id, letter_index, role[body/face/back/connector], bounds_mm, volume_mm, mesh_valid)
Export(id, job_id, format, file_path, checksum)

## Módulos funcionales
### A. Editor
- Texto editable con preservación de contornos interiores (A, B, O, P).
- Escala basada en altura real de geometría, no tamaño arbitrario de fuente.
- Conjuntos de piezas editables por estilo; controles con unidades y valores permitidos.
- Vista explotada, medidas y avisos.

### B. Motor CAD
- Curvas 2D cerradas y orientación de anillos exterior/interior.
- Offsets robustos, uniones y sustracciones booleanas.
- Generación de cuerpo, tapa y fondo independientes.
- Tolerancias positivas / negativas según proceso; no asumir valores universales.
- Un modelo determinista: mismos parámetros y versión de motor → misma geometría.

### C. Iluminación (posterior)
- Frente difusor y fondo opaco; halo trasero; canal para neonflex monotrazo.
- Entradas de cable, ventilación según diseño y fijaciones.
- Advertencias sobre disipación térmica, alimentación y protección exterior.
- No automatizar recomendaciones eléctricas sin conocer tira, tensión, potencia y fuente.

### D. Impresión
- Perfil exacto de impresora confirmado con ficha del fabricante/usuario.
- Orientación y cama útil con margen configurable.
- Segmentación con conectores y numeración; pruebas de resistencia y encaje.
- STL válido; 3MF más adelante, sin confundir modelos 3MF con proyectos de laminador completos.

### E. Presupuestos
- Volumen geométrico no es igual a consumo real de filamento.
- Estimaciones preliminares por longitud/material; consumo y tiempo final desde laminador cuando sea posible.
- Costes configurables: gramos, LED, acrílico, adhesivos, electricidad, desperdicio, tiempo humano y margen.

## Backlog por entregables con criterios de aceptación
### M0 — Fundaciones
Repo, README, Docker básico, lint, pruebas automáticas, ADR arquitectónicas.
Aceptación: ejecutar frontend/backend localmente y endpoint /health; sin secretos expuestos.

### M1 — Primera letra STL
Entrar una letra con tipografía de uso autorizado; extruir en mm; visualizar 3D; exportar STL.
Aceptación: malla cerrada, dimensiones dentro de tolerancia numérica configurada, apertura sin errores en Bambu Studio.

### M2 — Letra corpórea ensamblable
Cuerpo hueco, tapa y fondo; probeta de 3 o más holguras.
Aceptación: export separado; probado físicamente y documentado con material, boquilla y resultado de encaje.

### M3 — Editor de letreros
Texto multi-letra, importación SVG, proyectos guardados, vistas explotadas.
Aceptación: SVG válidos/erróneos generan mensajes claros; letras con agujeros internos conservadas.

### M4 — LED + segmentación
Canales, pasos de cables, division por perfil de cama, conectores y numeración.
Aceptación: pieza individual cabe en volumen útil, uniones comprobadas en impresión y prueba lumínica segura.

### M5 — Producción profesional
DXF, manifiesto, ZIP, estimaciones, fichas técnicas, catálogo de parámetros, integración opcional Supabase y despliegue protegido.
Aceptación: un proyecto completo reproducible con export y checklist de taller.

## Matriz de riesgos
- Fallos de booleanos/offset en tipografías complejas → pruebas con curvas difíciles + fallback controlado.
- Ajustes flojos/forzados → patrones físicos por material, boquilla, orientación y calibración.
- Impresión exterior falla por UV/temperatura → perfiles materiales y ensayos, no prometer aptitud automática.
- Letras demasiado grandes → segmentación y validación de ensamblaje.
- Consumo/tiempo mal calculado → indicar estimación y usar datos reales de Bambu Studio cuando se obtengan.
- Seguridad → GitHub privado, autenticación, secretos solo en variables de entorno, backups.
- Licencias → registrar origen de bibliotecas/fuentes y auditoría de compatibilidad.

## Decisiones pendientes del usuario
1. Modelo EXACTO de impresora (la denominación 'A2L' no está validada), volumen de cama y boquilla.
2. Primer producto: letra opaca, frontal iluminada, halo o neonflex.
3. Material disponible (PETG, ASA, PLA u otro) y aplicación interior/exterior.
4. Confirmar que el repositorio sea privado antes de introducir recursos de negocio o credenciales.
5. Subdominio destinado a la aplicación, sin pedir contraseñas ni tokens en el chat.

## Primer ensayo propuesto
Letra A de altura 120 mm, profundidad 30 mm, pared 2.0 mm, cuerpo opaco + tapa separada; números como valores INICIALES de ingeniería, sujetos a ensayo físico. Medir con calibre, registrar encaje y ajustar.

## Definición de terminado
No se declara 'listo para producir' por una vista 3D. Se requieren archivos legibles, validación geométrica, pruebas de impresión y montaje y parámetros reproducibles.
