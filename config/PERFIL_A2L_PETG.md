# Perfil de impresora — Bambu Lab A2L

Estado: perfil base confirmado con datos del usuario y especificaciones de fabricante, 24 de octubre de 2026.

## Máquina
- Fabricante: Bambu Lab
- Modelo: A2L (no A1)
- Boquilla instalada: 0.4 mm (confirmada por el usuario)
- Filamento principal: PETG (confirmado por el usuario)
- Diámetro de filamento: 1.75 mm (especificación A2L)
- Volumen nominal de impresión: 330 × 320 × 325 mm (X × Y × Z)
- Temperatura máxima de cama: 80 °C (especificación A2L)
- Temperatura máxima del cabezal: 300 °C (especificación A2L)
- Laminador: Bambu Studio

Fuentes:
- https://blog.bambulab.com/bambu-lab-a2l-creative-playground-extra-large/
- https://uelectronics.com/wp-content/uploads/2026/06/Guia-de-Inicio-Bambu-Lab-A2L-Espanol-2.pdf

## Valores de ingeniería iniciales (hipótesis, no presets validados)
- Espesor de pared de diseño: 2.0 mm, equivalente a aproximadamente cinco líneas de 0.4 mm si el ancho configurado fuese 0.4 mm. El ancho de extrusión real depende de Bambu Studio.
- Holgura inicial entre piezas: 0.25 mm. Calibrar con probetas PETG de 0.15 / 0.25 / 0.35 / 0.45 mm.
- Altura de capa inicial para evaluación: 0.20 mm; seleccionar perfil oficial A2L/PETG en Bambu Studio y afinar con ensayos.
- Margen de cama provisional: 5 mm por lado; volumen XY de planificación conservador 320 × 310 mm, sujeto a clips, brim y orientación de pieza.
- No establecer temperaturas o velocidad concretas hasta conocer marca y tipo exacto de PETG y el perfil recomendado.
- No garantizar aptitud exterior ni comportamiento LED sin pruebas UV/térmicas y ensayos de montaje.

## Siguiente ensayo
Letra A de 120 mm de altura y 35 mm de profundidad, con cuerpo PETG, tapa separada y probeta de tolerancias.

## Pendiente
- Confirmar marca y variante de PETG.
- Tipo de acabado y lugar de instalación (interior/exterior).
- Primera letra maciza, hueca sin LED, frontal LED, halo o neón flexible.
