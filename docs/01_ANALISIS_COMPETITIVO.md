# Benchmark funcional de generadores de letreros 3D
Fecha: 22-10-2026. Estado: investigación documental pública; no se han hecho pruebas autenticadas ni impresiones comparativas.

## Objetivo y límites
Estudiar funcionalidades y flujos de producción de terceros para especificar una implementación independiente. Las afirmaciones proceden de información pública; no implican acceso al código ni reproducción de algoritmos comerciales. Validar características y licencias antes de utilizar cualquier material.

## Plataformas estudiadas
| Referencia | URL | Capacidades públicas más relevantes | Lección para nuestro producto | Limitación de verificación |
|---|---|---|---|---|
| LetraMaker | https://letramaker.comunicacao3d.com/home | Generación de letras caja a partir de diseños vectoriales; referencia inicial del proyecto | Orientación al oficio de rotulación | Acceso directo a su editor y funciones premium pendiente |
| PROLED3D | https://proled3d.com/ | Texto/SVG; vista 2D/3D; conjuntos STL/DXF/ZIP; paredes, tapa, base, acrílico, perforaciones | Flujo integral diseño→fabricación | No se verificó exportación desde sesión autenticada |
| LumiSign 3D | https://www.lumisign3d.com/ | DXF, validación de contornos, tolerancias, vista explotada, sistemas de base, STL por objeto, web/escritorio | Precisión dimensional y diagnósticos preventivos | No se probaron ajustes físicos |
| Cartelito | https://cartelito.app/en | Texto/TTF/SVG/PNG, estructuras frontales/halo/acrílico, STL/DXF, estimaciones de filamento/LED | Flujo sencillo y presupuesto integrado | Estimaciones comerciales no auditadas |
| Volucore | https://volucore.net/ | Letras LED, neón, modelos separados, piezas dimensionadas según impresora; STL/3MF/DXF | Segmentación y ecosistema modular | Plataforma beta; requieren pruebas reales |
| SignFlex3D | https://signflex3d.com/ | SVG monotrazo/foto trazada; canales de neonflex, pasos de cable, anclajes, división | Motor separado para trazos abiertos | No se ensayó compatibilidad con todas las tiras |
| Modelador 3D | https://skipthecad.com/generators/modelador3d-channel-letters/ | Letras macizas/huecas/LED, SVG, STL, medidas | Experiencia básica de generación | Ficha de terceros, no validación completa |
| Neon Generator | https://github.com/ashirley/neon-generator | SVG → canal imprimible para neón LED, Python, licencia Apache-2.0 | Referencia de código permisivo con obligaciones de licencia | Requiere auditoría de dependencias y calidad |
| Hello World LED Sign | https://github.com/AlfredoSequeida/hello-world | Letras y difusores con OpenSCAD, control ESP8266, licencia GPL-3.0 | Pruebas de ensamblaje y electrónica | GPL-3.0 exige evaluación antes de incorporar código |

## Matriz priorizada de capacidades
Leyenda P0 = primer prototipo; P1 = producto útil; P2 = profesional; P3 = futura ampliación.
| ID | Función | Prioridad | Referencia |
|---|---|---|---|
| F01 | Entrada texto y fuentes autorizadas | P0 | PROLED3D, Cartelito |
| F02 | Dimensiones reales en milímetros | P0 | LumiSign |
| F03 | Extrusión y visualización 3D | P0 | Todas |
| F04 | Exportar STL independiente por letra | P0 | LumiSign |
| F05 | Cuerpo hueco + tapa + base separables | P1 | PROLED3D, Cartelito |
| F06 | Holguras ajustables y probetas de ajuste | P1 | LumiSign |
| F07 | Importar y validar SVG | P1 | PROLED3D |
| F08 | Guardar versiones de proyectos | P1 | Práctica de gestión |
| F09 | Vista explotada y sección transversal | P2 | LumiSign |
| F10 | Sistemas de iluminación frontal y halo | P2 | Cartelito |
| F11 | Neón flexible con perfiles por tira | P2 | SignFlex3D |
| F12 | División automatizada y conectores | P2 | Volucore |
| F13 | Exportación DXF y corte de acrílico | P2 | PROLED3D |
| F14 | Cálculo de materiales y presupuesto | P2 | Cartelito |
| F15 | Ficha técnica, ZIP por proyecto | P2 | PROLED3D |
| F16 | Múltiples perfiles de impresora y 3MF | P3 | Volucore |
| F17 | Vectorización PNG, OCR de logo (no texto) | P3 | Cartelito |

## Reglas de propiedad intelectual
No copiar interfaz exacta, marcas, fuentes no licenciadas, recursos gráficos, código, ni intentar extraer algoritmos. Observar funcionalidades públicamente documentadas y crear diseños, pruebas e implementaciones propios. Licencias de repositorios abiertos deben leerse y preservarse; GPL-3.0 requiere especial atención si se integra código.

## Pruebas para evaluación comparativa posterior
1. Texto 'LUCY' en fuente reproducible; altura 120 mm, profundidad 35 mm.
2. Letra 'O' con isla interior y contornos complejos.
3. SVG con agujeros y curva Bézier; SVG roto con líneas abiertas.
4. Cuerpo con tapa de prueba a holguras 0.15, 0.25, 0.35 y 0.45 mm.
5. Prueba de segmentación cuando pieza excede área útil.
6. Verificar que los STL se abren en Bambu Studio y que las medidas coinciden.
7. Comparar experiencia de uso, archivos producidos, defectos y tiempos en tabla de laboratorio.

## Fuentes
- https://proled3d.com/
- https://www.lumisign3d.com/
- https://cartelito.app/en
- https://volucore.net/
- https://signflex3d.com/
- https://skipthecad.com/generators/modelador3d-channel-letters/
- https://github.com/ashirley/neon-generator
- https://github.com/AlfredoSequeida/hello-world
