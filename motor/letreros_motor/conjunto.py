"""Cómo se agrupan las letras: sueltas, unidas en una pieza o sobre una placa común."""
from __future__ import annotations

from dataclasses import replace

from shapely.geometry import LineString, MultiPolygon, Point, box
from shapely.ops import nearest_points, unary_union

from .errores import ErrorEntrada
from .geometria import cilindro, multipoligono, poligonos, prisma, unir
from .texto import Letra

CONJUNTOS = {
    "individual": "Letras sueltas: una pieza (o varias, si se divide) por letra.",
    "unidas": "Letras fundidas en una sola pieza por palabra (huecos ≤ puente se cierran; barra opcional).",
    "placa": "Letras sueltas sobre una placa trasera común con marcas de posición grabadas.",
}
RANURA_ANCHO, RANURA_PROF = 0.8, 0.6


def agrupar(letras: list[Letra], d) -> tuple[list[Letra], list[str]]:
    """Devuelve las unidades a fabricar y avisos."""
    avisos: list[str] = []
    if d.conjunto != "unidas":
        if d.conjunto == "individual":
            for a, b in zip(letras, letras[1:]):
                if a.forma.intersects(b.forma) and a.forma.intersection(b.forma).area > 1.0:
                    avisos.append(f"«{a.caracter}» y «{b.caracter}» se solapan: con letras sueltas chocarán; "
                                  "usa el conjunto «unidas» o más espaciado.")
        return letras, avisos

    PUENTE_MAX = 15.0
    ancho_puente = max(8.0, 0.12 * d.altura)
    trozos = []
    for palabra in sorted({l.palabra for l in letras}):
        ls = [l for l in letras if l.palabra == palabra]
        piezas = [l.forma for l in ls]
        if d.barra > 0:
            piezas.append(box(min(l.forma.bounds[0] for l in ls), 0, max(l.forma.bounds[2] for l in ls), d.barra))
        # Puente explícito entre letras consecutivas que no se tocan (lo que haría un rotulista).
        for a, b in zip(ls, ls[1:]):
            hueco = a.forma.distance(b.forma)
            if hueco <= 0.01:
                continue
            if hueco > PUENTE_MAX:
                avisos.append(f"«{a.caracter}» y «{b.caracter}» están a {hueco:.1f} mm: demasiado para un puente; "
                              "reduce el espaciado o añade barra.")
                continue
            pa, pb = nearest_points(a.forma, b.forma)
            piezas.append(LineString([pa, pb]).buffer(ancho_puente / 2, cap_style=1))
        u = unary_union(piezas)
        if d.puente > 0:  # suavizado opcional de rincones entre letras
            r = d.puente / 2
            u = u.buffer(r, join_style=2, mitre_limit=3).buffer(-r, join_style=2, mitre_limit=3)
        trozos.append(u)
    union = unary_union(trozos)
    componentes = poligonos(union)

    # Agrupar letras que comparten componente; una letra con varias partes (Ñ, i) une sus componentes.
    padre = list(range(len(componentes)))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    letras_de = {i: [] for i in range(len(componentes))}
    for l in letras:
        idx = [i for i, c in enumerate(componentes) if c.intersects(l.forma)]
        for i in idx[1:]:
            padre[raiz(i)] = raiz(idx[0])
        if idx:
            letras_de[idx[0]].append(l)
    grupos: dict[int, list[int]] = {}
    for i in range(len(componentes)):
        grupos.setdefault(raiz(i), []).append(i)

    unidades = []
    for comps in sorted(grupos.values(), key=lambda cs: min(componentes[i].bounds[0] for i in cs)):
        ls = sorted({id(l): l for i in comps for l in letras_de[i]}.values(), key=lambda l: l.indice)
        forma = MultiPolygon([componentes[i] for i in comps])
        texto = "".join(l.caracter for l in ls) or "pieza"
        unidades.append(Letra(len(unidades) + 1, texto, forma, min(l.origen_x for l in ls) if ls else 0.0))
    if any(len(u.caracter) == 1 for u in unidades) and len(letras) > 1:
        sueltas = ", ".join(f"«{u.caracter}»" for u in unidades if len(u.caracter) == 1)
        avisos.append(f"Quedan letras sin unir ({sueltas}): sube el puente, añade barra o reduce el espaciado.")
    return unidades, avisos


def placa(unidades: list[Letra], resultados, d):
    """Construye la placa común (como una pieza maciza más) con ranuras de posición y agujeros."""
    from .estructuras import construir_letra

    if d.estructura == "halo":
        raise ErrorEntrada("La placa común no se combina con halo: el halo se separa de la pared con sus separadores.")
    formas = unary_union([u.forma for u in unidades])
    m = d.placa_margen
    if d.placa_forma == "silueta":
        contorno = multipoligono(formas.buffer(m, join_style=1).buffer(-m / 3, join_style=1).buffer(m / 3, join_style=1))
        contorno = multipoligono(unary_union(contorno.geoms).convex_hull) if len(contorno.geoms) > 1 else contorno
    else:
        minx, miny, maxx, maxy = formas.bounds
        contorno = MultiPolygon([box(minx - m, miny - m, maxx + m, maxy + m)])

    g = d.placa_grosor
    ranuras = multipoligono(unary_union([u.forma.boundary.buffer(RANURA_ANCHO / 2) for u in unidades]))
    agujeros = []
    for r in resultados:
        for x, y in getattr(r, "puntos_cable", []):
            agujeros.append(cilindro(x, y, d.cable / 2, -1, g + 1))
    avisos = []
    if d.placa_agujero > 0:
        if d.placa_forma == "rect":
            minx, miny, maxx, maxy = contorno.bounds
            ins = min(m / 2, 15)
            for x, y in ((minx + ins, miny + ins), (maxx - ins, miny + ins), (minx + ins, maxy - ins), (maxx - ins, maxy - ins)):
                if Point(x, y).buffer(d.placa_agujero / 2 + 1).disjoint(formas):
                    agujeros.append(cilindro(x, y, d.placa_agujero / 2, -1, g + 1))
        else:
            avisos.append("Placa con silueta: sin agujeros de fijación automáticos; taladra en obra o usa adhesivo.")

    def retocar(solido):
        return solido - unir([prisma(ranuras, g - RANURA_PROF, g + 1), *agujeros])

    d_placa = replace(d, estructura="maciza", profundidad=g, cable=0, drenaje=False, tira_led=0, comp_xy=0)
    res = construir_letra(Letra(0, "base", contorno, contorno.bounds[0]), d_placa, retoques={"cuerpo": retocar})
    for p in res.piezas:
        p.rol = "placa"
    res.avisos = [a.replace("'base'", "la placa") for a in res.avisos] + avisos
    return res
