# Motor de geometría — Letreros 3D Studio

Herramienta de producción local: escribe un texto y obtén todas las piezas del letrero en STL, listas para Bambu Studio (Bambu Lab A2L, boquilla 0,4 mm, PETG). No toca la web publicada.

## Instalar (una vez)
```powershell
cd motor
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q             # deben pasar todas
```
En sesiones siguientes basta con `cd motor` y `.venv\Scripts\activate`.

## 1 · Calibrar la holgura (antes del primer letrero frontal)
```powershell
python -m letreros_motor probeta -o salida\probeta
```
Genera 1 cuerpo + 4 frentes con holgura 0,15 / 0,25 / 0,35 / 0,45 mm (1 a 4 puntos grabados en el lado del faldón). Imprime todo en PETG, prueba cuál entra **firme sin forzar** y usa ese valor en `--holgura`. Acepta los mismos `--pared`, `--frente`, `--fondo`, `--encaje` que el letrero, y otras holguras con `--holguras 0.2 0.3`.

## 2 · Generar un letrero
```powershell
python -m letreros_motor letrero "LUCY" --estructura frontal --altura 120 --profundidad 40 -o salida\LUCY
```
Resultado en `salida\LUCY\`:
- `01-L-cuerpo.stl`, `01-L-frente.stl`, `02-U-cuerpo.stl`… una pieza por archivo, ya orientadas para imprimir;
- `LEEME.txt`: resumen, medidas y peso de cada pieza, cómo imprimir y **mapa de montaje** (posición X de cada letra);
- `ficha.json`: lo mismo en datos (parámetros, piezas, camas, avisos, metros de LED);
- `camas/cama-01-opaco.3mf`, `cama-02-difusor.3mf`…: las piezas ya colocadas en la cama de la A2L, separadas por filamento (opaco: cuerpos, empalmes, placa · difusor: frentes). Ábrelas en Bambu Studio;
- `contornos.dxf`: contornos 1:1 en mm y en posición de montaje (capas LETRAS, PLACA, CORTES, CABLE) para láser o vinilo;
- `plantilla-montaje.svg`: plantilla 1:1 para marcar en la pared.
Añade `--zip` para obtener además `salida\LUCY.zip`.

### Estructuras (`--estructura`)
| Valor | Piezas | Uso |
|---|---|---|
| `maciza` | cuerpo | Letra corpórea sin luz. |
| `caja` | cuerpo (fondo + paredes, frente abierto) | Neón flex, acrílico pegado o decorativa. |
| `frontal` | cuerpo (fondo + paredes) + **frente impreso a presión** | Frontal iluminada: tira LED en el fondo, frente en PETG blanco/natural. |
| `halo` | cuerpo (frente cerrado + paredes, trasera abierta) con **separadores** | Retroiluminada: la luz sale hacia la pared. |

### Parámetros (todos en mm)
| Opción | Def. | Rango | Qué es |
|---|---|---|---|
| `--altura` | 120 | 20–1000 | Altura de la **mayúscula** (A, H, M). La O, acentos y descendentes miden lo que dicta la fuente. |
| `--profundidad` | 40 | 5–250 | Grosor total del letrero montado. |
| `--pared` | 1,6 | 0,8–6 | Lateral. Usa múltiplos de 0,4 (1,2 · 1,6 · 2,0). |
| `--frente` | 2 | 0,8–6 | Grosor del frente (frontal/halo). |
| `--fondo` | 2 | 0,8–6 | Grosor del fondo (caja/frontal). |
| `--holgura` | 0,25 | 0–1 | Juego del frente a presión (sale de la probeta). |
| `--encaje` | 4 | 1–15 | Altura del faldón que entra en el cuerpo. |
| `--pared-encaje` | 1,2 | 0,8–4 | Grosor del faldón. |
| `--espaciado` | 0 | −20–200 | Separación extra entre letras. |
| `--comp-xy` | 0 | 0–0,5 | Resta al contorno exterior (pata de elefante). |
| `--tira-led` | 8* | 0 / 3–20 | Ancho de la tira: avisa de zonas donde no cabe. *0 en maciza/caja salvo que lo indiques. |
| `--w-por-metro` | — | 0–50 | Consumo de tu tira; calcula el consumo nominal. |
| `--cable` | 6 | 0 / 2–15 | Ø del agujero de cable en el fondo, en el punto más holgado. |
| `--drenaje` | no | — | Agujero Ø3 en la parte baja del fondo (exterior). |
| `--separacion` | 20 | 5–80 | Halo: distancia de la letra a la pared. |
| `--tornillo` | 3,2 | 2–6 | Halo: Ø del agujero de cada separador. |

### Varias líneas (v0.6)
Escribe `\n` donde quieras el salto: `python -m letreros_motor letrero "LUCY\nHAIR" --alineacion izquierda --interlineado 1.3 -o salida\LUCY`.
Hasta 4 líneas de 40 caracteres. `--alineacion` centro | izquierda | derecha (sobre el ancho visible de cada línea); `--interlineado` 1–3 × altura (def. 1,4). Con letras unidas, cada línea es una pieza aparte.

### Fuente, conjunto, división y presupuesto (v0.5)
| Opción | Def. | Qué es |
|---|---|---|
| `--fuente` | montserrat-bold | `montserrat-bold`, `poppins-bold`, `roboto-bold`, `oswald-bold`, `bebas-neue`, `playfair-bold`, `lobster`, `pacifico`, `dancing-script-bold`, `great-vibes`. |
| `--conjunto` | individual | `individual` (sueltas), `unidas` (una pieza por palabra, puentes automáticos), `placa` (sobre placa común). |
| `--barra` | 0 | Unidas: barra inferior de esta altura que une las letras de palo. |
| `--puente` | 0 | Unidas: suaviza los rincones entre letras. |
| `--placa-forma` / `--placa-margen` / `--placa-grosor` / `--placa-agujero` | rect / 15 / 4 / 5 | Placa común. Lleva grabada la silueta de cada letra (0,6 mm) y agujeros de cable alineados. |
| `--no-dividir` | — | Error en vez de dividir lo que no cabe en la cama. |
| `--precio-kg` / `--precio-led-m` | 25 / 0 | Presupuesto de materiales en €. |

Ejemplo: `python -m letreros_motor letrero "aperto" --fuente pacifico --conjunto unidas --altura 100 -o salida\aperto`

El paquete incluye además `plantilla-montaje.svg` a escala 1:1 (posición de cada pieza, cable +, separadores o, cortes --).

### Lo que comprueba antes de exportar
- Valores fuera de rango, profundidad insuficiente para fondo + frente + encaje, piezas más altas que la cama.
- Cada pieza: sólido cerrado (manifold), apoyada en z = 0, cabe en la cama A2L (320 × 310 × 325) recta o girada.
- Avisos con la letra afectada: trazos más finos que la boquilla, partes que se hacen macizas (tildes pequeñas), zonas donde no cabe la tira LED, cable/drenaje/separadores que no caben, pared no múltiplo de 0,4.
- No sobrescribe una carpeta que tenga otros archivos.

## Una sola letra maciza (M1)
```powershell
python -m letreros_motor A --altura 120 --profundidad 35 -o salida\A.stl
```
Aquí `--altura` es la del contorno de esa letra (convención M1, se conserva por compatibilidad).

## Límites actuales
- División: vertical por los puntos más estrechos y, si la pieza es más alta que la cama, también horizontal (rejilla A1, B1, A2…).
- El reparto en camas usa rectángulos (estantes); Bambu Studio puede reordenar con «Organizar» si quieres aprovechar más la cama.
- Metros de LED: estimación (perímetro interior / 2). El peso es el del sólido al 100 %; el laminador da el real.
- Sin acrílico/DXF todavía (fase M4).

## Diseño técnico
`texto.py` maqueta con la altura de mayúscula → `estructuras.py` construye cada pieza con sólidos de **manifold3d** (uniones y restas que siempre dan mallas cerradas) a partir de offsets de **shapely** → `proyecto.py` valida, exporta STL binario reproducible, ficha y LEEME. `diseno.py` concentra parámetros, rangos y validación cruzada.
