# Análisis de los editores en funcionamiento — qué hacen, qué no y cómo superarlos
Fecha: 25-10-2026 · Pruebas hechas a mano en Chrome, sin crear cuentas ni pagar.
Caso de prueba común: palabra **"LUCY"** (y "LUCY ÑÁ" cuando se podía escribir texto), 120 mm, 35 mm de profundidad, impresora Bambu Lab A2L. Para las plataformas que solo aceptan SVG se usó un SVG de "LUCY" en curvas generado con nuestra fuente Montserrat Bold.

| Plataforma | ¿Probado el editor? | Límite de la prueba |
|---|---|---|
| Cartelito | Sí, completo | Sin descargar el ZIP (no se bajaron archivos) |
| SignFlex3D | Sí, con el SVG de prueba | Descarga de STL requiere cuenta |
| PROLED3D | Sí, configurador de estructuras | Generar texto y exportar requieren login con Google |
| LumiSign 3D | Sí, panel completo | Solo acepta DXF; exportar requiere licencia |
| Modelador 3D | Sí, panel completo | Descarga pide nombre y email |
| Volucore | No: el editor exige cuenta | Analizado por su web y guías |
| LetraMaker | No: el editor exige cuenta | Analizado por su web (estilos, funciones, precios) |

---

## 1. Ficha de cada editor

### Cartelito (cartelito.app/editor)
**Cómo funciona:** panel único a la izquierda, vista 3D a la derecha; todo se recalcula al momento.
- Entrada: Texto · SVG · Imagen (PNG vectorizado). 5 fuentes (Anton, Archivo Black, Poppins Bold, Bebas Neue, Righteous) + subir TTF/OTF propia.
- 6 estructuras con parámetros propios:
  - Frente sólido: pared 2 · frente 2 (paso 0,4 = múltiplos de boquilla).
  - Acrílico desde adentro / a media pared / al ras / atrás (halo): labio 2 · acrílico 3 · holgura 0,2 · apoyo interno 2 · (media pared: retroceso 15).
  - Placa de respaldo: acrílico 3 · margen 10.
- Frente perforado: patrón contorno o rejilla, punto Ø 4 cada 8.
- Base trasera encastrable: con borde (bandeja) / plana / solo anillo · piso 2 · borde 1,6 · altura 8 · ventilación Ø 6 cada 15.
- Presupuesto en vivo: gramos, horas, metros de LED, coste por precio del kg.
- Salida: ZIP por pieza o STL completo.

**Lo que hace bien:** muy simple; presupuesto inmediato; avisa cuando los agujeros de ventilación no caben ("bajá alguno de los dos valores").

**Lo que NO hace / fallos observados:**
- ❌ Acepta **letra de 2000 mm** sin aviso: calcula 17,9 kg y 1192 h como si fuera normal.
- ❌ Acepta **pared de 0 mm** (todos los campos con mínimo 0) y sigue dando presupuesto.
- ❌ No muestra medidas del letrero ni de cada letra.
- ❌ No conoce la impresora ni la cama: no avisa si no cabe, no divide.
- ❌ Tilde de la Ñ y acento de la Á salen como piezas flotantes sueltas, sin puente ni aviso.
- ❌ Sin guardar proyecto, sin historial, sin vista de sección.

### SignFlex3D (signflex3d.com — neón y letras corpóreas)
**Cómo funciona:** el cálculo se hace en el navegador (respuesta en ~0,5 s). Vista "Sencilla/Completa", herramientas en iconos, vista Modelo / Cama de impresión, cubo de vistas (SUP, FRE, IZQ, DER, POS, INF), deslizador "Separar piezas" (vista explotada).
- Entrada: SVG (monotrazo para neón, relleno para corpóreas), calcado de foto (beta), JSON de proyecto, TTF/OTF.
- **Perfil de corte acotado** siempre visible (ej. "pared 2,5 · acrílico 3 · 35 mm").
- Cabecera con datos: medida total, modelo, piezas, gramos, tiempo, triángulos, ms de cálculo.
- Corpóreas: cara de acrílico o cara impresa; 7 modelos (acrílico con muesca, fondo hueco, apoyo doble, ajuste trasero, pared continua, canal en el fondo, acrílico al ras). SVG de la cara de acrílico para láser.
- **Cama:** 15 impresoras (incluida **Bambu Lab A2L 330×320×325**), personalizada, "Buscar el giro en que cabe", **Partir** y **Repartir** (coloca las letras giradas en el mínimo de camas: LUCY entró en 1 cama A2L), "Descargar las camas (ZIP)".
- **Corte:** planos arrastrables y girables, "Sugerir cortes", cortar solo una letra, colas de milano (de abajo arriba o solo en la base), holgura de junta ajustada según boquilla (0,2/0,4/0,6/0,8), conectores macho-hembra en paredes.
- Neón: canal 1.ª gen. 6,2×10 / 2.ª gen. 8×6,5, pared 1,5, base 3, margen 8; anclajes, puentes, pasacables, túneles, separadores, tapa difusora.
- "Escalar accesorios con el letrero": los accesorios se mueven en proporción; grosores y agujeros no.
- Muestra la versión del motor ("motor vcorp-17oct").

**Lo que hace bien:** es el más completo y el más rápido; perfil acotado; reparto de camas; corte profesional.

**Lo que NO hace / fallos observados:**
- ❌ El tamaño se fija por **ancho total del diseño**; la altura de letra sale "≈ 124 mm" (aproximada). Un rotulista pide altura de letra exacta.
- ❌ Al subir un SVG declarado de 120 mm de alto lo convirtió en 129,4 mm (midió el sobrante de la C, no la altura de mayúscula).
- ❌ Fallo de coherencia: tras elegir la A2L, el panel de corte seguía diciendo "Todo cabe en tu cama (Bambu Lab A1… 256×256)".
- ❌ Para texto hay que preparar un SVG fuera (CorelDRAW); no hay editor de texto con fuentes en el modo corpóreas.
- ❌ Las funciones útiles (difusor, cableado oculto, lista de materiales) son del plan de 29 USD/mes.

### PROLED3D (app.proled3d.com, v2.498)
**Cómo funciona:** asistente de 5 pasos (01 Forma → 02 Estructura → 03 Configurar → 04 Herramientas → 05 Verificar y exportar) con una **consola** de mensajes abajo y un tour guiado de 8 pasos.
- Modos: Letras caja/Logo · Neón Flex · **Rótulo de bandera (BETA, cajón de doble cara)**.
- Entrada: SVG/DXF (mm o pulgadas) o Texto: 14 fuentes (Montserrat Black, Poppins Black, Roboto Black, Oswald Bold, Bebas Neue, Anton, Barlow Condensed Black, Archivo Black, Rajdhani Bold, Orbitron Black, Exo 2 ExtraBold, Teko Bold, Russo One, Noto Sans Black); **altura de texto en mm** (200 por defecto) y espaciado.
- **Configurador de estructuras** (lo mejor que se ha visto):
  - Paso 1, Tapa: encaje interno (L), apoyo a media pared (F), frente lleno (C), retroiluminada (C8R, PRO), frente perforado (P, PRO), acrílico (PRO).
  - Paso 2, Base compatible con esa tapa: 1, 1B (soporte PVC), 2 (sin borde), 3 (a ras), 3R (encaje elevado), 4 (anillo para PVC), 4R, 5 (PVC a presión), 6 (doble canal), 6B, 7.
  - Paso 3, Verificación: código de la combinación (ej. **F6**), **sección exacta A-A del montaje** con plano de corte móvil (X-Z / Y-Z, posición en mm), cotas, colores por pieza (base, tapa, acrílico) y tabla de componentes (tapa, base, frente, acrílico, PVC, cierre).
- Herramientas: Guillotina con cola de milano, nesting de acrílico/PVC, cotizador, editor de nodos, optimizador de curvas, ZIP, documentación PRO, "Compartir 3D", vista "RayX" (rayos X).

**Lo que hace bien:** sistema modular tapa × base con compatibilidades; dibujo técnico de sección real; 8 idiomas incluido italiano.

**Lo que NO hace / fallos observados:**
- ❌ El tour guiado bloquea el uso: reabre el configurador en bucle y hubo que recargar.
- ❌ Para generar el texto pide **login con Google** (aunque dice "seguir explorando").
- ❌ Las mejores tapas (retroiluminada, perforada, acrílico) y bases son PRO.
- ❌ No hay perfil de impresora visible en el flujo inicial; los valores por defecto (pared 1,5, profundidad 40…) no se explican.

### LumiSign 3D (app.lumisign3d.com, v1.0.98)
**Cómo funciona:** panel por secciones (Origen, Paredes, Acrílico, Fondo, División, Colores) + visor con cubo de orientación y panel de "Display" (paredes/acrílico/base, explosión, intensidad y ángulo de luz, brillo de material, vista retroiluminada).
- Entrada: **solo DXF**, mm o cm, tolerancia de curva 0,05 (0,01–2).
- Paredes: 4 presets; pared exterior 3 (0,4–50) · profundidad 25 (5–500) · pared hacia dentro · labio frontal sobre el acrílico.
- Acrílico: grosor 3 (1–20) · rebaje 2 · holgura 0,2 (0–2) · hundido bajo el borde · frente sólido.
- Fondo: 6 tipos (W abierto, I macizo, S a presión, G ranura, V inserto, F rebaje).
- **División en piezas:** cama (300×300 por defecto, 50–2000), dientes de unión (paso 10, profundidad 0,15… holgura de junta), lengüeta en pared o corte recto, **cortes automáticos en los puntos más estrechos**, edición de cortes (doble clic divide, Mayús+doble clic horizontal, clic derecho borra), pieza mínima.
- Salidas: STL pared/fondo/base, STL por objeto, **STL dividido, plan de montaje en PDF, DXF del acrílico dividido y colocado en planchas (900×600)**.

**Lo que hace bien:** la división más inteligente (corta donde es más estrecho) y el **plan de montaje PDF**; rangos con mínimos y máximos en todos los campos.

**Lo que NO hace:**
- ❌ **No admite texto ni fuentes**: hay que traer un DXF hecho en otro programa.
- ❌ Sin presupuesto, sin gramos ni horas.
- ❌ Licencia atada al hardware, pago manual mensual, Windows sin firmar.

### Modelador 3D (modelador3d.com.br/personalizador/letreiro)
**Cómo funciona:** formulario en 7 bloques numerados con vista 3D y medidas encima (ej. "306 × 124 × 25,0 mm").
1. Qué crear: texto o logo SVG; **21 estilos de fuente agrupados** (clásicas, display, temáticas, manuscritas); espacio entre letras en mm reales.
2. Tipo: maciza, caja hueca, front-lit LED, relieve en placa (con descripción de cada uno).
3. Tamaño: **altura de la mayúscula (A, M, H)**, válida igual para minúsculas, acentos y varias líneas (20–1000 mm); profundidad 3–120; tabla "Medidas de la pieza": montado L×A×P, cada letra, piezas en el archivo, filamento estimado; selector de mesa (180, 220, 256, 300, 350, 500+); **dividir solo lo que no cabe**, con cola de milano.
4. Paredes 2 (1–8) y fondo 1,6 (0,8–8).
5. Acabado del frente: plano, chaflán, redondeado.
6. Cierre: tapa frontal a presión, agujero de cable (uno por letra, en el punto más central), **agujero de drenaje para exterior**.
7. Impresión: **reforzar trazos finos** (mínimo 1,2 mm ≈ 2× boquilla) y **compensación XY** 0–0,4 mm (pata de elefante).
- Venta de la pieza impresa desde R$ 203 + envío; botón de presupuesto para modelado a medida.

**Lo que hace bien:** la definición de altura más correcta, ayudas de texto en cada campo, drenaje, compensación XY, refuerzo de trazos. Es el que mejor piensa en quien imprime.

**Lo que NO hace:** sin acrílico ni halo, sin DXF, sin LED más allá de "front-lit", sin perfil de corte, sin guardar proyecto; un solo color.

### Volucore (LED Letters) — sin acceso al editor
Según su web: 31 fuentes (incluye árabe); texto, SVG o imagen trazada en el navegador (umbral, suavizado, detalle); 4 tapas (enrasada, frente hundido, envolvente con halo, canal abierto); **elige la tira LED y marca las zonas demasiado estrechas para ella; estima potencia, peso y coste**; agujeros de cable y fijación; salidas STL cuerpo y tapa, DXF de frente y fondo, SVG, PNG. **No divide** una letra que no cabe: solo avisa.

### LetraMaker — sin acceso al editor
Según su web: 12 estilos (Face acrílico con fondo impreso, fondo calado, apoyo doble, apoyo único, back fit, encaje; face impresa con encaje; retroiluminado con pernos; LED doble; letra curva; neón LED 2.ª gen.; orgánico). Ficha técnica PDF con marca, cortar letras grandes, **mesas de impresión (un STL por cama)**, agujeros de cable y pernos separadores, historial con numeración. Planes: gratis (2 estilos), R$ 22/mes, R$ 42/mes.

---

## 2. Comparativa de capacidades
✅ = sí · ◐ = parcial · ❌ = no · ? = no verificable sin cuenta

| Capacidad | Cartelito | SignFlex3D | PROLED3D | LumiSign | Modelador 3D | Volucore | LetraMaker |
|---|---|---|---|---|---|---|---|
| Texto con fuentes en el editor | ✅ 5 | ◐ (neón) | ✅ 14 | ❌ | ✅ 21 | ✅ 31 | ✅ |
| SVG / DXF / imagen | SVG, PNG | SVG, foto | SVG, DXF | DXF | SVG | SVG, imagen | SVG |
| Altura exacta de mayúscula en mm | ◐ | ❌ (por ancho) | ✅ | ❌ (del DXF) | ✅ | ? | ? |
| Validación de valores imposibles | ❌ | ◐ | ? | ✅ rangos | ✅ rangos | ✅ tira LED | ? |
| Medidas visibles del letrero | ❌ | ✅ | ✅ | ◐ | ✅ | ✅ | ? |
| Perfil / sección acotada | ❌ | ✅ | ✅ sección real | ❌ | ❌ | ❌ | ? |
| Sistema tapa × base | ◐ | ✅ 7 | ✅ 6×11 | ✅ 6 fondos | ◐ | ✅ 4 tapas | ✅ 12 |
| Acrílico + DXF | ✅ | ✅ SVG | ✅ | ✅ | ❌ | ✅ | ✅ |
| Perfil de impresora / cama | ❌ | ✅ 15 (A2L) | ? | ◐ manual | ✅ 6 tamaños | ❌ | ✅ |
| División con uniones | ❌ | ✅ | ✅ | ✅ la mejor | ✅ | ❌ | ✅ |
| Reparto en camas | ❌ | ✅ | ? | ❌ | ❌ | ❌ | ✅ |
| Plan de montaje | ❌ | ❌ | ? | ✅ PDF | ❌ | ❌ | ◐ ficha |
| Refuerzo de trazos finos | ❌ | ❌ | ❌ | ❌ | ✅ | ◐ aviso | ? |
| Compensación XY / holgura por boquilla | ❌ | ✅ boquilla | ◐ tolerancia | ◐ | ✅ | ? | ✅ |
| Drenaje exterior | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| LED: tira, potencia, consumo | ◐ metros | ◐ metros | ◐ cotizador | ❌ | ❌ | ✅ | ❌ |
| Presupuesto | ✅ básico | ◐ | ✅ completo | ❌ | ◐ gramos | ✅ | ✅ PDF |
| Guardar proyecto / historial | ❌ | ✅ | ✅ PRO | ❌ | ❌ | ✅ | ✅ |
| Ñ y tildes resueltas | ❌ sueltas | ? | ? | — | ✅ (altura) | ? | ? |
| Sin cuenta para probar | ✅ | ✅ | ◐ | ◐ | ✅ | ❌ | ❌ |

---

## 3. Lo mejor de cada uno → cómo lo hacemos mejor en Letreros 3D Studio

| Función | La mejor referencia | Nuestra versión mejorada |
|---|---|---|
| Medida | Modelador 3D (altura de mayúscula) | Altura de mayúscula exacta **y** medida de cada letra y del conjunto, siempre visibles; acentos y Ñ fuera de la medida. |
| Validación | LumiSign (rangos) + Volucore (tira LED) | Ningún campo acepta valores imposibles; cada aviso dice el problema, la letra afectada y cómo arreglarlo; el STL no se descarga con errores graves. |
| Estructuras | PROLED3D (tapa × base con compatibilidad) | Catálogo modular tapa × base × iluminación con código (ej. "F6"), solo combinaciones compatibles, cada una **probada en PETG en la A2L** antes de publicarla. |
| Vista técnica | PROLED3D (sección A-A) + SignFlex (perfil acotado) | Sección real acotada con plano móvil + vista explotada + colores por pieza, también exportable en el PDF. |
| Cama y división | LumiSign (corte en lo más estrecho) + SignFlex (repartir, A2L) | Perfil A2L por defecto; repartir letras en el mínimo de camas; cortar solo lo que no cabe y por los puntos más estrechos; cola de milano con holgura según boquilla. |
| Montaje | LumiSign (plan PDF) + LetraMaker (ficha técnica) | Ficha PDF con marca D4: piezas numeradas (L-01, U-01…), mapa de montaje, materiales, horas, gramos, LED, coste y checklist. |
| Imprimibilidad | Modelador 3D | Refuerzo de trazos < 2× boquilla, compensación XY, puentes para tildes/puntos, drenaje para exterior. |
| LED | Volucore | Catálogo de tiras (ancho, V, W/m) que marca zonas demasiado estrechas y calcula metros, potencia y fuente recomendada **solo cuando la tira es conocida**. |
| Presupuesto | PROLED3D + Cartelito | Precio en vivo (filamento, horas de máquina, LED, acrílico, mano de obra, margen, IVA) → presupuesto que pasa a pedido y factura en Odoo. |
| Calibración | Nadie | Probeta de holguras generada por el programa; el valor medido se guarda en el perfil de impresora y material. |
| Idioma | PROLED3D (8) | Español e italiano nativos desde el inicio; portugués e inglés después. |
| Facilidad | Cartelito / Modelador 3D | Modo sencillo (5 decisiones) y modo experto; sin tour que bloquee; ayudas cortas en cada campo. |

## 4. Corrección para nuestro motor M1
Nuestro M1 mide **cada letra por su propio contorno**. Para un rótulo completo eso es incorrecto: la "O" y la "C" sobresalen de la línea base y saldrían más pequeñas que la "H". Se corregirá en la siguiente fase: **altura = altura de mayúscula de la fuente** (A, M, H), igual para todas las letras; acentos, tildes y descendentes quedan fuera de esa medida. Se mantendrá la opción "altura total del contorno" para logos.

## 5. Modelos de negocio observados
- **Suscripción barata** (3–10 €/mes): LetraMaker, LumiSign, PROLED3D.
- **Suscripción especializada** (15–29 USD/mes): SignFlex3D.
- **Gratis con email + venta de la pieza impresa**: Modelador 3D (desde R$ 203 + envío) y Cartelito (gratis).
- **Por descargas**: Volucore.

Para D4 encaja un modelo híbrido: herramienta interna de producción para los encargos de rótulos (prioridad), y más adelante un configurador público para clientes que piden presupuesto o compran la pieza.

## 6. Plan actualizado
| Fase | Contenido |
|---|---|
| M2 | Altura de mayúscula · caja hueca + frente impreso + fondo a presión · probeta de holguras PETG · validación con rangos |
| M3 | Palabra completa (espaciado real, Ñ y tildes con puentes o pieza aparte) · refuerzo de trazos · compensación XY · medidas por letra |
| M4 | Catálogo tapa × base (primeras 3 combinaciones probadas) · acrílico + DXF · halo con separadores · agujero de cable y drenaje |
| M5 | Editor web con vista 3D real, perfil/sección acotada, vista explotada, modo sencillo/experto |
| M6 | Perfil A2L · repartir en camas · división en puntos estrechos con cola de milano · numeración |
| M7 | Ficha PDF con marca D4 y plan de montaje · presupuesto en vivo · enlace con Odoo |
| M8 | Catálogo de tiras LED · neón flex · SVG/PNG con validador |

## Fuentes
- https://cartelito.app/editor
- https://signflex3d.com/generador.html y https://signflex3d.com/motor/index.html?modo=corporea
- https://app.proled3d.com/
- https://app.lumisign3d.com/app
- https://modelador3d.com.br/personalizador/letreiro
- https://volucore.net/tools/led-letters y https://volucore.net/guides/how-to-make-3d-printed-led-channel-letters
- https://letramaker.comunicacao3d.com/home
