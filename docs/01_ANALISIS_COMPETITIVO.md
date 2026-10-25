# Análisis de plataformas de referencia — Letreros 3D Studio
Versión 2 · 25-10-2026 · Revisión directa de las webs públicas de cada plataforma (sin cuenta ni pago).
Sustituye la versión del 22-10-2026, que era documental.

**Regla de propiedad intelectual:** se estudian funciones, parámetros publicados y precios para diseñar una solución propia. No se copia interfaz, textos, imágenes, marcas, fuentes ni código de terceros.

## 1. Ficha de cada plataforma

### LetraMaker — letramaker.comunicacao3d.com (Brasil, portugués)
- **Entrada:** texto con fuentes integradas o SVG del logo; detecta contornos y huecos automáticamente.
- **12 estilos de construcción:** Face Acrílico (fondo impreso, fondo calado, apoyo doble, apoyo único, back fit, encaje), Face impresa con encaje, Retroiluminado (halo, con pernos separadores), LED doble, Letra curva (letras sobre base curvada), Neón LED 2.ª generación, Orgánico.
- **Partes:** frente, cuerpo y trasera generados a la vez. Pared paramétrica (profundidad y espesor), grosor de acrílico y holgura de encaje configurables.
- **Producción:** STL por letra o pieza única; DXF alineado para cortar acrílico/PVC; ficha técnica PDF con peso, filamento, coste por pieza, logo del cliente y checklist; herramienta Cortar para letras más grandes que la cama; *mesas de impresión* que reparten las piezas en camas y exportan un STL por cama; agujeros para cable LED y pernos espaciadores internos; historial con numeración automática de pedidos; aprovechamiento de acrílico (anunciado como "en breve").
- **Precio:** Explorer gratis (2 estilos), Maker R$ 22/mes (12 estilos, STL/DXF ilimitado, presets), Empresa R$ 42/mes (ficha técnica, cortar, mesas, historial). Pago con Stripe.

### PROLED3D — proled3d.com (8 idiomas, incluido español e italiano)
- **Entrada:** texto, SVG, DXF (las líneas centrales de DXF solo para neón).
- **Herramientas:** generador de cuerpos/tapas/bases; *Guillotina* que divide bases y tapas por cama con unión recta o en cola de milano; *nesting* automático de piezas de acrílico/PVC en planchas DXF; cotizador (medidas, material, tiempo de impresión, componentes eléctricos, merma, margen e impuestos); editor de nodos y perforaciones; optimizador de curvas; neón flex; exportación ZIP organizada.
- **Plugins** para CorelDRAW e Illustrator.
- **Precio:** gratis funcional; Premium 10 USD/mes.
- No publica valores por defecto: "verificar el ajuste con tu impresora".

### LumiSign 3D — lumisign3d.com (web + escritorio Mac/Windows, 11 idiomas)
- **Entrada:** DXF en mm o pulgadas; tolerancia de curva hasta 0,05 mm.
- **Validador DXF:** contornos abiertos, micro-segmentos, etc., con niveles de error/aviso/info.
- **Tipos:** canal con frente de acrílico en rebaje, frente sólido (pintado), modo pared hacia dentro.
- **Valores por defecto publicados:** pared 2 mm · profundidad de caja 25 mm · acrílico 3 mm · ancho de rebaje 2 mm · holgura del acrílico 0,2 mm.
- **6 sistemas de fondo:** abierto, macizo, *snap-in*, ranura, inserto, rebaje; con labio, profundidad de rebaje, separación a pared y grosor de fondo ajustables. Fondo exportable como tercer STL.
- **Vista:** se regenera al cambiar cualquier parámetro, sin botón "Generar"; cubo de orientación; deslizador de vista explotada; opacidad para simular iluminación; contador de triángulos.
- **Precio:** 5 €/mes, prueba de 14 días sin exportar STL. Licencia atada al hardware.

### Cartelito — cartelito.app (Buenos Aires; español, inglés y portugués)
- **Entrada:** texto (Anton, Archivo Black, Poppins Bold, Bebas Neue, Righteous), TTF/OTF propia, SVG, PNG vectorizado automáticamente.
- **6 estructuras:** frente macizo difusor (ejemplo pared 2,0 / frente 2,0); puntos de luz tipo marquesina (Ø 4,0 cada 8,0); acrílico enrasado (holgura 0,20); acrílico insertado (labio 2,0 / repisa 2,0) o a media pared; halo con acrílico trasero; placa trasera con la silueta completa (margen 10).
- **Estimación en vivo:** gramos de filamento, horas de impresión, metros de tira LED.
- **ZIP:** `piece-01..n.stl` (una por letra), `base-01..n.stl` (tapas snap-in con agujeros de ventilación), `base.dxf` (PVC), `acrylic.dxf` (con holgura ya restada) y estimación.
- **Precio:** editor gratuito (no publica planes).

### Volucore — volucore.net (beta, navegador)
- 13 herramientas; las relevantes son **LED Letters** (31 fuentes; texto, SVG o imagen; paredes, tapa y tira LED ajustables; STL/DXF/SVG) y **Neon Sign** (21 fuentes, 6 de trazo único; canales para LED; conectores ocultos; piezas numeradas y dimensionadas según la impresora).
- **Trace:** convierte PNG/JPG/WEBP a SVG.
- Vista 3D en vivo con tamaño real en mm; 3MF multicolor; exporta STL, 3MF, DXF, SVG y SCAD.
- Compatible declarado con Bambu Studio, OrcaSlicer, PrusaSlicer, Cura y Creality Print.
- **Precio por descargas:** Free 3/mes, Standard 30, Business 50 (comercial), Business Pro 80.
- Guías de solución de problemas de impresión con capturas del laminador.

### SignFlex3D — signflex3d.com (especialista en neón flex, español)
- **Entrada:** SVG de trazo abierto (monotrazo), calcado de foto (beta), biblioteca de diseños.
- **Canales:** 1.ª gen. (silicona maciza) 6,2 × 10 mm, pared 1,5 mm; 2.ª gen. (tira en S con funda) 8 × 6,5 mm, pared 1,5 mm, labio de 0,7 mm. Raíles en el suelo del canal que centran la tira; se cambia de sistema con un clic.
- Pasos de cable, túneles internos, cableado oculto; anclajes de bocallave u orejas para tornillo colocados arrastrando.
- **División:** 15 impresoras en lista; plano de corte arrastrable con uniones ocultas; puentes que unen partes sueltas.
- Difusor interior/exterior; SVG del difusor para láser; lista de materiales (metros de neón, tornillos, gramos, dónde cortar la tira).
- **Precio:** Básico 15 USD/mes, Experto 29 USD/mes; 5 diseños sueltos por 12 USD.

### Modelador 3D — modelador3d.com.br (vía SkipTheCAD; portugués, gratis)
- Tipos: macizas, caja hueca, frontal LED, relieve sobre placa.
- ~15 fuentes, SVG; altura 20–1000 mm; profundidad, pared y fondo; acabado frontal plano, chaflán o redondeado; **opción que engrosa trazos finos para que se impriman**.
- STL de un color, una pieza por letra; **no divide** letras más grandes que la cama.
- Descarga gratis dejando nombre y email.

### Código abierto
| Proyecto | Licencia | Qué aporta | Uso permitido para nosotros |
|---|---|---|---|
| ashirley/neon-generator | Apache-2.0 | SVG → canal STL para neón, Python, perfiles (`-p noodle`), longitud | Se puede estudiar y reutilizar con atribución y aviso de licencia. Proyecto pequeño (20 commits). |
| AlfredoSequeida/hello-world | GPL-3.0 | Letras OpenSCAD con difusor-inserto a 0,5 mm de holgura; LED WS2812B + ESP8266 | Solo como referencia de ideas. Incorporar código obligaría a publicar nuestro software como GPL. |

## 2. Lo que TODAS hacen (mínimo para competir)
1. Texto con fuentes integradas + SVG del logo, con huecos interiores correctos.
2. Vista 3D en vivo con medidas reales en mm.
3. Cuerpo + frente/tapa + fondo como piezas separadas, con pared, profundidad y holgura configurables.
4. Un STL por letra, empaquetado en ZIP.
5. DXF para cortar acrílico/PVC con la holgura ya aplicada.
6. Funcionar en el navegador, sin instalar nada.

## 3. Lo que diferencia a los mejores
| Función | Quién | Valor para un taller |
|---|---|---|
| División por cama con uniones (cola de milano, ocultas) | PROLED3D, LetraMaker, Volucore, SignFlex3D | Imprescindible para rótulos > 31 cm |
| Mesas/camas: reparto automático de piezas y un STL por cama | LetraMaker | Ahorra mucho tiempo en producción |
| Ficha técnica PDF con marca del taller y checklist | LetraMaker | Entregable profesional para el cliente |
| Cotizador con merma, margen e impuestos | PROLED3D | Presupuestos rápidos |
| Estimación en vivo de filamento, horas y LED | Cartelito | Decide el precio mientras diseñas |
| Validador de contornos con niveles de gravedad | LumiSign | Evita fallos antes de imprimir |
| Engrosar trazos finos automáticamente | Modelador 3D | Hace imprimibles las fuentes script |
| Puentes para partes sueltas (punto de la i, tilde de la Ñ) | SignFlex3D | Clave en español (Ñ, tildes) |
| Historial con numeración de pedidos | LetraMaker | Gestión del taller |
| Nesting de acrílico | PROLED3D | Ahorro de material |

## 4. Valores iniciales a adoptar (hipótesis, se calibran con probetas PETG en la A2L)
| Parámetro | Valor inicial | Fuente de referencia |
|---|---|---|
| Pared | 2,0 mm | LumiSign, Cartelito |
| Frente impreso difusor | 2,0 mm | Cartelito |
| Profundidad de caja | 25–35 mm (35 en nuestro primer ensayo) | LumiSign / perfil A2L |
| Acrílico | 3 mm | LumiSign |
| Rebaje / labio / repisa | 2,0 mm | LumiSign, Cartelito |
| Holgura del acrílico | 0,20 mm | LumiSign, Cartelito |
| Holgura de tapa PETG | 0,25 mm (probar 0,15–0,45) | Nuestro perfil |
| Puntos de luz | Ø 4,0 mm cada 8,0 mm | Cartelito |
| Margen de placa trasera | 10 mm | Cartelito |
| Neón 1.ª gen. | canal 6,2 × 10 mm, pared 1,5 mm | SignFlex3D |
| Neón 2.ª gen. | canal 8 × 6,5 mm, pared 1,5 mm, labio 0,7 mm | SignFlex3D |

## 5. Precios del mercado
| Plataforma | Precio |
|---|---|
| Cartelito, Modelador 3D | Gratis |
| LetraMaker | R$ 22 / R$ 42 al mes (≈ 3,5 € / 7 €) |
| LumiSign | 5 €/mes |
| PROLED3D | 10 USD/mes |
| Volucore | Gratis 3 descargas/mes; planes por número de descargas |
| SignFlex3D | 15 / 29 USD al mes |

Conclusión: el mercado es barato. Vender el software como suscripción compite con precios de 3 a 10 €. El valor diferencial está en usarlo como **herramienta de producción propia de D4** (encargos de rótulos) o en ofrecer algo que nadie tiene (ver punto 6).

## 6. Huecos que nadie cubre bien (nuestra oportunidad)
1. **Calibración real:** nadie entrega probetas de holgura ni guarda la holgura medida por material e impresora. Podemos generar una probeta (0,15/0,25/0,35/0,45 mm) y guardar el valor ganador en el perfil.
2. **Perfil A2L + PETG verificado:** todos dicen "verifica con tu impresora". Nosotros podemos publicar valores probados.
3. **Español + italiano nativos y pensados para el taller:** Ñ, tildes y ¿¡ con puentes automáticos; unidades y textos de oficio.
4. **Del diseño a la factura:** ninguno conecta con la gestión. Con el stack de D4 (Odoo, n8n) el presupuesto puede convertirse en pedido y factura.
5. **Validación honesta:** ningún STL sale sin comprobar que la malla es cerrada, cabe en la cama y no tiene trazos menores que la boquilla (ya implementado en el motor M1).

## 7. Plan de funciones priorizado
| Fase | Funciones | Referencia | Estado |
|---|---|---|---|
| **M1** | Una letra maciza → STL validado | Modelador 3D | ✅ hecho (rama `feat/motor-stl-una-letra`) |
| **M2** | Caja hueca + frente impreso 2 mm + fondo snap-in con ventilación · probeta de holguras | Cartelito, LumiSign | siguiente |
| **M3** | Palabra completa con espaciado real · ZIP con una pieza por letra · puentes para Ñ/i/tildes · engrosar trazos finos | Cartelito, SignFlex3D, Modelador 3D | |
| **M4** | Frente de acrílico (enrasado, rebaje, insertado) + DXF con holgura · halo con separadores · agujeros para cable LED | LumiSign, Cartelito, LetraMaker | |
| **M5** | API + vista 3D real en la web (regenera al cambiar parámetros, vista explotada) | LumiSign | |
| **M6** | División por cama con uniones · mesas de impresión · numeración de piezas y mapa de montaje | LetraMaker, PROLED3D, SignFlex3D | |
| **M7** | Estimación de filamento/horas/LED · cotizador · ficha técnica PDF con marca D4 · historial de pedidos | Cartelito, PROLED3D, LetraMaker | |
| **M8** | SVG/PNG del logo con validador · neón flex 1.ª/2.ª gen. · puntos de luz | LumiSign, Volucore, SignFlex3D | |

## 8. Fuentes consultadas (25-10-2026)
- https://letramaker.comunicacao3d.com/home
- https://proled3d.com/
- https://www.lumisign3d.com/
- https://cartelito.app/en · https://cartelito.app/editor
- https://volucore.net/
- https://signflex3d.com/
- https://skipthecad.com/generators/modelador3d-channel-letters/
- https://github.com/ashirley/neon-generator
- https://github.com/AlfredoSequeida/hello-world
