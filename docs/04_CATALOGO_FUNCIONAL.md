# Catálogo profesional de funciones — Letreros 3D Studio

Fecha: 2026-10-24
Versión objetivo: 1.0, evolución por hitos a partir del prototipo visual v0.3.
No se ha implementado aún generación CAD de piezas, STL ni división real. Las referencias comerciales inspiran el alcance funcional sin reutilizar código propietario.

## Impresora base
Bambu Lab A2L, volumen nominal 330x320x325 mm, boquilla 0.4 mm, PETG; cama útil inicial de planificación 320x310 mm (margen hipotético, debe revisarse con Bambu Studio). Nunca enviar geometría a la impresora sin comprobar malla, encaje, temperatura y seguridad.

## Tipos de letrero seleccionables
T1. Caja hueca sin LED: paredes, tapa y respaldo.
T2. Corpóreas macizas: volumen macizo (la laminación determina relleno).
T3. Frontal iluminado: cuerpo opaco, difusor, fondo, pasos LED.
T4. Posterior halo: frente opaco, separación de pared y salida trasera de luz.
T5. Doble iluminación: difusor frontal + espacio trasero halo, cámaras ópticas y control de luz.
T6. Neón flex: trazos de centro, canales de ancho y profundidad configurables, radios mínimos y pasacables.
T7. Frente opaco con cuerpo iluminado: material o paredes translúcidas según especificación.
T8. Cuerpo sobre placa o base compartida.
T9. Letras unidas en un conjunto, con puente o fusión de trayectorias cuando sea viable.
T10. Logos e iconos por SVG: siluetas compuestas y contornos con huecos.

## Biblioteca inicial de diez fuentes
- Montserrat (moderna, alto contraste de grosor y lectura)
- Poppins (geométrica, comercial)
- Roboto (texto universal)
- Oswald (condensada)
- Bebas Neue (rótulos altos)
- Playfair Display (serif elegante)
- Lobster (escritura ligada)
- Pacifico (script decorativa)
- Dancing Script (script fluida)
- Great Vibes (caligrafía fina)

Vista navegador: usar Google Fonts CSS. Export CAD: el servidor debe tener una fuente autorizada con sus archivos y licencias revisadas; CSS del navegador por sí solo no sirve para generar contornos deterministas. No afirmar que sean las 10 más usadas del sector sin estadística específica. Las fuentes script finas requieren validación de mínimo de trazo y posible engrosamiento o puentes. Las letras unidas NO se consiguen solo aplicando una fuente script: deben unirse los contornos con operaciones robustas o añadir puentes.

## Modelo de interfaz
Panel Proyecto: nombre, cliente opcional, notas, etiquetas, guardar JSON y recuperar.
Panel Diseño: texto/SVG, tipografía, altura, ancho objetivo, espaciado, alineación, unión de letras, base.
Panel Geometría: pared, cuerpo, tapa, rebaje acrílico, fondo, pestaña, holgura, tornillos/imanes.
Panel Luz: frontal, halo, doble, neonflex, color, temperatura, canal, alojamiento, cable, calor y materiales difusores.
Panel Fábrica: impresora, boquilla, material, orientación, segmentación y conectores, piezas enumeradas.
Panel Control: diagnósticos de malla, espesores, trazos imposibles, zonas no imprimibles, volumen.
Panel Costes: filamento calculado por slicer, LED, acrílico, consumibles, energía, mano de obra y márgenes.
Panel Export: STL/3MF por pieza, DXF cuando haya contornos, ZIP, BOM y manual de montaje.

## División automática según cama
1. Calcular el AABB de cada sólido en mm en distintas orientaciones XY y márgenes.
2. Si cabe, exportar entero; si no, buscar planos de división que eviten zonas delgadas, recortes de LED y agujeros.
3. Generar segmentos y conectores, tolerancias por material, etiquetado A-01, A-02 etc.
4. Validar que CADA pieza cumple el volumen útil y su geometría es manifold.
5. Emitir mapa de montaje, puntos de unión, sentido y numeración.
6. Prueba física antes de declarar fiable la segmentación.

## Integración de estilos y LED
No mezclar técnicas: 'halo' requiere separadores y orientación a pared; 'frontal' necesita difusión; 'doble' exige diseñar ambas cámaras; 'neonflex' necesita especificaciones físicas de perfil. Fijar 12/24 V solo después de conocer el producto; nunca inventar cableado o dimensionado de fuente.

## Arquitectura de ejecución
Frontend visual con Three.js/React, motor CAD Python + OCC/CadQuery, FastAPI y cola controlada para trabajos. Perfil PETG A2L configurable. Guardar proyecto JSON con schema_version, fuente y versión de geometría. Contenedor de frontend + contenedor backend separados en Coolify. Validar consumo de RAM y CPU antes de subir a producción.

## Hitos de implementación
V0.3 = selector de 10 fuentes, 7 estructuras, modo independiente/unido/base, proyecto JSON y vista ilustrativa.
V0.4 = generador CAD real de letra maciza y mallas STL validadas.
V0.5 = caja hueca, frente/fondo, holguras y probetas PETG.
V0.6 = texto multiletra, fusión y SVG.
V0.7 = segmentación por cama A2L con conectores probados.
V0.8 = frontal/halo/doble/neonflex reales.
V0.9 = export ZIP/BOM, 3MF, presupuestos y pruebas con piezas reales.
V1.0 = control de usuarios, historial, suite de tests, copias de seguridad y manual de producción.

## Criterios de aceptación
- Precisión dimensional verificable en slicer y calibre físico.
- STL manifold, huecos interiores preservados, tapas desmontables.
- Ninguna pieza excede cama útil en orientación elegida.
- Interfaz diferencia vista ilustrativa de CAD real.
- Modos luminosos validados con LED y materiales reales.
- Privacidad, permisos y licencias en orden.

## Referencias públicas
- https://proled3d.com/
- https://www.lumisign3d.com/
- https://volucore.net/
- https://fonts.google.com/
