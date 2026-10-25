# Motor de geometría — prototipo M1

Genera el **STL auténtico de UNA letra corpórea maciza** a partir de los contornos reales de una fuente con licencia revisada. Es la primera pieza del motor CAD; no toca la web publicada (el `Dockerfile` sigue copiando solo `index.html`).

## Qué hace
1. Lee el glifo de `fuentes/Montserrat-Bold.ttf` (OFL 1.1, archivo versionado con SHA-256 comprobado).
2. Aproxima curvas con desviación ≤ 0,05 mm (ajustable) y aplica la regla de relleno TrueType, preservando huecos interiores (A, B, O, 8…) y piezas separadas (punto de la i, tilde de la Ñ).
3. Escala a milímetros: **la altura es la del contorno real del glifo**, de su punto más bajo al más alto.
4. Extruye la profundidad en Z. Cara en XY, apoyada en la cama.
5. Comprueba malla cerrada, orientación coherente, volumen = área × profundidad, cama útil A2L (320 × 310 × 325 mm, admite giro de 90°) y trazos más finos que la boquilla de 0,4 mm.
6. Escribe STL binario reproducible (mismos parámetros → mismos bytes).

## Instalar y usar (Windows o Linux)
```bash
cd motor
python -m venv .venv
.venv\Scripts\activate        # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
python -m letreros_motor A --altura 120 --profundidad 35 -o salida/A.stl
python -m pytest -q
```
Salida de ejemplo:
```
Letra: A  ·  Fuente: Montserrat Bold 9.000 (SIL Open Font License 1.1)
Medidas: 134.57 × 120.00 × 35.00 mm (X × Y × Z)
Volumen: 249.87 cm³  ·  Cara: 7139.2 mm²
Cuerpos: 1  ·  Agujeros interiores: 1  ·  Triángulos: 44
Malla cerrada (manifold): sí
```

## Límites (honestos)
- Solo letra **maciza**: sin caja hueca, tapa, fondo, canal LED, conectores ni división.
- Un carácter por ejecución; una fuente (Montserrat Bold). Las otras nueve de la interfaz no están aún versionadas para CAD.
- Altura 20–1500 mm y profundidad 5–250 mm (como en la interfaz), pero rechaza lo que no cabe en la cama.
- **Sin verificar todavía en Bambu Studio ni impresa.** Las pruebas automáticas validan la malla; la compatibilidad con el laminador y la pieza física deben confirmarse a mano.

## Prueba manual en Bambu Studio (muestra imprimible)
1. `python -m letreros_motor A --altura 120 --profundidad 35 -o salida/A.stl`
2. Importar en Bambu Studio → comprobar que muestra 134,57 × 120,00 × 35,00 mm y que no pide reparar la malla.
3. Para ahorrar material en la primera prueba: `--altura 40 --profundidad 5`.
4. Medir con calibre altura y hueco interior; anotar resultados en `config/PERFIL_A2L_PETG.md`.

## Por qué trimesh + shapely y no CadQuery (por ahora)
Para extruir contornos planos bastan polígonos exactos y una malla validada; CadQuery/OpenCascade añade una dependencia pesada para el servidor. El *offset* de shapely cubre la siguiente etapa (caja hueca: contorno − pared). Se reevaluará CadQuery cuando hagan falta chaflanes, redondeos o uniones sólidas complejas.
