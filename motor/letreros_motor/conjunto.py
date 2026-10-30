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

    PUENTE_MAX = max(15.0, 0.25 * d.altura)  # rotulación: puentes de hasta ~¼ de la altura
    # Puente con hueco suficiente para que el cable pase por dentro de una letra a otra.
    ancho_puente = max(8.0, 0.12 * d.altura, 2 * d.pared + 8.0 if d.estructura not in ("maciza", "neon") else 0.0)
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
        unidad = Letra(len(unidades) + 1, texto, forma, min(l.origen_x for l in ls) if ls else 0.0)
        if d.letras_por_pieza and len(ls) > d.letras_por_pieza:
            unidad = _por_piezas(unidad, ls, d.letras_por_pieza, avisos)
        unidades.append(unidad)
    if any(len(u.caracter) == 1 for u in unidades) and len(letras) > 1:
        sueltas = ", ".join(f"«{u.caracter}»" for u in unidades if len(u.caracter) == 1)
        avisos.append(f"Quedan letras sin unir ({sueltas}): sube el puente, añade barra o reduce el espaciado.")
    return unidades, avisos


def _por_piezas(unidad: Letra, ls: list[Letra], n: int, avisos: list[str]) -> Letra:
    """Corta una palabra unida en piezas de n letras, por el punto más estrecho entre grupos."""
    from dataclasses import replace as _r

    from .division import corte_estrecho
    from .texto import nombre_seguro
    ls = sorted(ls, key=lambda l: l.forma.centroid.x)
    grupos = [ls[i:i + n] for i in range(0, len(ls), n)]
    if len(grupos[-1]) == 1 and len(grupos) > 1 and n > 1:
        avisos.append(f"«{unidad.caracter}»: la última pieza lleva una sola letra ({grupos[-1][0].caracter}).")
    cortes = []
    for a, b in zip(grupos, grupos[1:]):
        izq, der = a[-1], b[0]
        x0 = max(izq.forma.centroid.x, izq.forma.bounds[2] - 0.6 * (izq.forma.bounds[2] - izq.forma.bounds[0]))
        x1 = min(der.forma.centroid.x, der.forma.bounds[0] + 0.4 * (der.forma.bounds[2] - der.forma.bounds[0]))
        if x1 <= x0:
            x0, x1 = izq.forma.centroid.x, der.forma.centroid.x
        cortes.append(corte_estrecho(unidad.forma, x0, x1))
    nombres = []
    for g in grupos:
        nombre = nombre_seguro("".join(l.caracter for l in g)) or "p"
        while nombre in nombres:
            nombre += "x"
        nombres.append(nombre)
    return _r(unidad, cortes=tuple(cortes), partes=tuple(nombres))


def contorno_placa(formas, d) -> MultiPolygon:
    """Contorno de la placa común o de la caja de luz: rectángulo con margen, o silueta suavizada."""
    m = d.placa_margen
    if d.placa_forma == "silueta":
        contorno = multipoligono(formas.buffer(m, join_style=1).buffer(-m / 3, join_style=1).buffer(m / 3, join_style=1))
        return multipoligono(unary_union(contorno.geoms).convex_hull) if len(contorno.geoms) > 1 else contorno
    minx, miny, maxx, maxy = formas.bounds
    return MultiPolygon([box(minx - m, miny - m, maxx + m, maxy + m)])


def placa(unidades: list[Letra], resultados, d):
    """Construye la placa común (como una pieza maciza más) con ranuras de posición y agujeros."""
    from .estructuras import construir_letra

    if d.estructura in ("halo", "doble"):
        raise ErrorEntrada("La placa común no se combina con halo ni doble: van separados de la pared.")
    formas = unary_union([u.forma for u in unidades])
    m = d.placa_margen
    contorno = contorno_placa(formas, d)

    neon = d.estructura == "neon"
    if neon:  # placa de neón: la placa ES el letrero, con un canal por letra
        from .estructuras import profundidad_ranura_neon, ranura_neon
        g = d.profundidad
        ranuras = multipoligono(unary_union([ranura_neon(u.forma, d) for u in unidades]))
        prof_ranura = profundidad_ranura_neon(d)
        r_cable = min(d.cable, d.neon_ancho) / 2
    else:
        g = d.placa_grosor
        ranuras = multipoligono(unary_union([u.forma.boundary.buffer(RANURA_ANCHO / 2) for u in unidades]))
        prof_ranura = RANURA_PROF
        r_cable = d.cable / 2
    agujeros = []
    for r in resultados:
        for x, y in getattr(r, "puntos_cable", []):
            agujeros.append(cilindro(x, y, r_cable, -1, g + 1))
    avisos = []
    if d.placa_agujero > 0:
        if d.placa_forma == "rect":
            minx, miny, maxx, maxy = contorno.bounds
            ins = min(m / 2, 15)
            for x, y in ((minx + ins, miny + ins), (maxx - ins, miny + ins), (minx + ins, maxy - ins), (maxx - ins, maxy - ins)):
                if Point(x, y).buffer(d.placa_agujero / 2 + 1).disjoint(formas.union(ranuras) if neon else formas):
                    agujeros.append(cilindro(x, y, d.placa_agujero / 2, -1, g + 1))
        else:
            avisos.append("Placa con silueta: sin agujeros de fijación automáticos; taladra en obra o usa adhesivo.")

    def retocar(solido):
        return solido - unir([prisma(ranuras, g - prof_ranura, g + 1), *agujeros])

    d_placa = replace(d, estructura="maciza", profundidad=g, cable=0, drenaje=False, tira_led=0, comp_xy=0,
                      fijacion="ninguna")
    res = construir_letra(Letra(0, "base", contorno, contorno.bounds[0]), d_placa, retoques={"cuerpo": retocar})
    from .estructuras import subir
    for p in res.piezas:
        p.rol = "placa"
        p.montaje = None if neon else subir(-g)
    res.avisos = [a.replace("'base'", "la placa") for a in res.avisos] + avisos
    return res
