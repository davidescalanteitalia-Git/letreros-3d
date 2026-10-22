# Letreros 3D — Plan inicial

## Objetivo
Desarrollar una aplicación web privada en español para diseñar letras corpóreas, generar componentes imprimibles y exportar STL para preparación en Bambu Studio.

## Etapas
1. Editor de texto: fuente, altura, profundidad y vista previa.
2. Geometría: extrusión, cuerpo hueco, fondo y tapa, con tolerancias configurables.
3. Exportación: archivos STL separados por componente y validación de mallas.
4. Prototipo físico: imprimir una letra de prueba, verificar medidas y encajes.
5. Opcional: SVG, canales LED, división automática de piezas grandes, costes y despliegue en Coolify.

## Stack propuesto
- Frontend: React, TypeScript y Three.js.
- Motor CAD: Python con CadQuery/OpenCascade (evaluar licencias y compatibilidad al implementarlo).
- API: FastAPI.
- Despliegue: contenedores Docker mediante Coolify.
- Almacenamiento posterior: Supabase, si es necesario.

## Criterios iniciales de calidad
- Unidades expresadas en milímetros.
- Mallas STL cerradas, sin autointersecciones.
- Separación entre cuerpo, tapa y fondo.
- Tolerancias comprobadas mediante impresión física.
- Preparación final de la impresión en Bambu Studio.

## Pendientes por confirmar
- Modelo exacto y volumen de impresión útil de la impresora Bambu Lab (no asumir medidas por la denominación A2L).
- Material de impresión y dimensiones deseadas de la primera letra.
- Preferencia de iluminación frontal, halo o neón flexible.

## Seguridad
- Mantener claves/API fuera de GitHub.
- Usar un repositorio privado para desarrollo propio.
- No copiar código propietario de programas comerciales.
