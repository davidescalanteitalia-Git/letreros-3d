"""Pruebas de la fase M2: letreros completos con estructuras huecas para LED."""
import json
import math

import pytest
import trimesh

from letreros_motor import Diseno, ErrorEntrada, exportar, generar_letrero, generar_probeta, validar
from letreros_motor.__main__ import main
from letreros_motor.fuentes import obtener_fuente
from letreros_motor.texto import maquetar, nombre_seguro

RUTA = obtener_fuente("montserrat-bold").ruta


def piezas_de(texto="L", **kw):
    return generar_letrero(Diseno(texto, **kw))


# --- Maquetación y altura de mayúscula -------------------------------------

def test_altura_es_la_mayuscula():
    h, o = maquetar("HO", RUTA, 120)
    assert h.forma.bounds[1] == pytest.approx(0, abs=1e-6)
    assert h.forma.bounds[3] == pytest.approx(120, abs=1e-6)
    # La O sobresale de la línea base y de la altura de mayúscula, como en la fuente.
    assert o.forma.bounds[1] < 0 and o.forma.bounds[3] > 120


def test_acentos_y_tilde_por_encima_de_la_mayuscula():
    (enie,) = maquetar("Ñ", RUTA, 120)
    assert enie.forma.bounds[3] > 140
    assert len(enie.forma.geoms) == 2  # N + tilde


def test_espacios_y_espaciado():
    a = maquetar("I I", RUTA, 100)
    b = maquetar("I I", RUTA, 100, espaciado_mm=10)
    assert [l.indice for l in a] == [1, 2]
    assert b[1].origen_x - a[1].origen_x == pytest.approx(20)  # dos huecos de 10 mm


@pytest.mark.parametrize("texto", ["", "   ", "A\nB", "X" * 41, "A\u0007"])
def test_texto_invalido(texto):
    with pytest.raises(ErrorEntrada):
        piezas_de(texto)


def test_nombre_de_archivo_seguro():
    assert nombre_seguro("Ñ") == "N" and nombre_seguro("á") == "a" and nombre_seguro("&") == "u0026"


# --- Estructuras ------------------------------------------------------------

@pytest.mark.parametrize("estructura, roles", [
    ("maciza", ["cuerpo"]), ("caja", ["cuerpo"]), ("frontal", ["cuerpo", "frente"]), ("halo", ["cuerpo"]),
])
def test_todas_las_piezas_son_solidos_cerrados(estructura, roles):
    pr = piezas_de("LUCY ÑÁ", estructura=estructura, drenaje=True)
    assert len(pr.letras) == 6
    for r in pr.letras:
        assert [p.rol for p in r.piezas] == roles
        for p in r.piezas:
            assert p.malla.is_watertight and p.malla.is_winding_consistent and p.malla.is_volume
            assert p.malla.bounds[0][2] == pytest.approx(0, abs=1e-6)  # apoyada en la cama


def test_caja_es_hueca_con_fondo():
    d = Diseno("I", estructura="caja", cable=0, profundidad=40, pared=1.6, fondo=2)
    pr = generar_letrero(d)
    pieza = pr.piezas[0]
    forma = pr.letras[0].letra.forma
    interior = forma.buffer(-1.6, join_style=2, mitre_limit=3)
    esperado = forma.area * 40 - interior.area * 38
    assert pieza.malla.volume == pytest.approx(esperado, rel=1e-3)


def test_frontal_encaja_y_suma_la_profundidad():
    d = Diseno("I", estructura="frontal", profundidad=40, frente=2, encaje=4, cable=0)
    cuerpo, frente = generar_letrero(d).piezas
    assert cuerpo.malla.extents[2] == pytest.approx(38)
    assert frente.malla.extents[2] == pytest.approx(6)
    # El faldón cabe dentro del hueco con la holgura indicada: sin interferencia.
    montado = frente.malla.copy()
    montado.apply_transform(trimesh.transformations.reflection_matrix([0, 0, 0], [0, 0, 1]))
    montado.apply_translation([0, 0, 40])
    assert montado.is_volume
    inter = trimesh.boolean.intersection([montado, cuerpo.malla], engine="manifold")
    assert inter.is_empty or inter.volume < 1e-3  # solo se tocan, no se interfieren


def test_holgura_cambia_el_faldon():
    v = [generar_letrero(Diseno("I", holgura=h, cable=0)).piezas[1].malla.volume for h in (0.15, 0.45)]
    assert v[0] > v[1]


def test_agujero_de_cable_y_drenaje():
    base = generar_letrero(Diseno("O", estructura="frontal", cable=0)).piezas[0].malla.volume
    con_cable = generar_letrero(Diseno("O", estructura="frontal", cable=6)).piezas[0].malla.volume
    con_todo = generar_letrero(Diseno("O", estructura="frontal", cable=6, drenaje=True)).piezas[0].malla.volume
    assert base - con_cable == pytest.approx(math.pi * 9 * 2, rel=0.02)  # Ø6 × fondo 2
    assert con_cable > con_todo


def test_halo_lleva_separadores_con_agujero():
    pr = piezas_de("L", estructura="halo", profundidad=40, separacion=20)
    m = pr.piezas[0].malla
    assert m.extents[2] == pytest.approx(60)  # 40 + 20 de separador
    # Partes de la L de más de 150 mm no hay; a 300 mm sí: dos separadores en el trazo largo.
    grande = piezas_de("I", estructura="halo", altura=300, profundidad=30).piezas[0].malla
    corte = grande.section(plane_origin=[0, 0, 45], plane_normal=[0, 0, 1])
    assert len(corte.discrete) == 4  # 2 separadores × (exterior + agujero)


def test_parte_fina_se_hace_maciza():
    pr = piezas_de("Ñ", estructura="frontal", altura=25, profundidad=15, encaje=3)
    assert any("queda maciza" in a for a in pr.avisos)
    for p in pr.piezas:
        assert p.malla.is_watertight


def test_aviso_tira_led_estrecha():
    pr = piezas_de("i", estructura="frontal", altura=40, profundidad=25, tira_led=10)
    assert any("no cabe la tira de 10 mm" in a for a in pr.avisos)
    assert not any("no cabe la tira" in a for a in piezas_de("I", tira_led=8).avisos)


def test_metros_led_y_consumo():
    pr = piezas_de("LUCY", w_por_metro=10)
    assert 0.5 < pr.metros_led < 2.0
    assert "consumo nominal" in pr.resumen()


def test_compensacion_xy_reduce_el_contorno():
    a = piezas_de("H", estructura="maciza").piezas[0].malla.extents[0]
    b = piezas_de("H", estructura="maciza", comp_xy=0.2).piezas[0].malla.extents[0]
    assert a - b == pytest.approx(0.4, abs=0.02)


# --- Validación -------------------------------------------------------------

@pytest.mark.parametrize("campo, valor", [
    ("altura", 10), ("altura", 2000), ("pared", 0), ("pared", 0.5), ("frente", 0), ("fondo", 7),
    ("holgura", -0.1), ("holgura", 2), ("profundidad", math.nan), ("comp_xy", 1), ("tira_led", 2),
    ("cable", 1), ("estructura", "neon"), ("profundidad", "x"),
])
def test_valores_imposibles(campo, valor):
    with pytest.raises(ErrorEntrada):
        validar(Diseno("A", **{campo: valor}))


def test_profundidad_minima_frontal():
    with pytest.raises(ErrorEntrada, match="insuficiente"):
        validar(Diseno("A", estructura="frontal", profundidad=8))


def test_aviso_pared_no_multiplo_de_boquilla():
    _, avisos = validar(Diseno("A", pared=1.5))
    assert any("múltiplo" in a for a in avisos)
    _, avisos = validar(Diseno("A", pared=1.6))
    assert not any("múltiplo" in a for a in avisos)


def test_letra_que_no_cabe_en_la_cama():
    with pytest.raises(ErrorEntrada, match="no cabe"):
        piezas_de("W", altura=300)


def test_letra_que_solo_cabe_girada():
    pr = piezas_de("I", estructura="maciza", altura=315)
    assert any("girada" in a for a in pr.avisos)


# --- Probeta ----------------------------------------------------------------

def test_probeta_cuatro_holguras():
    piezas, avisos, d = generar_probeta()
    assert [p.archivo for p in piezas] == [
        "00-probeta-cuerpo.stl", "01-h015-frente.stl", "02-h025-frente.stl",
        "03-h035-frente.stl", "04-h045-frente.stl",
    ]
    assert all(p.malla.is_watertight for p in piezas)
    vols = [p.malla.volume for p in piezas[1:]]
    assert vols == sorted(vols, reverse=True)  # más holgura y más puntos = menos material
    assert any("--holgura" in a for a in avisos)


# --- Exportación y CLI ------------------------------------------------------

def test_exportar_paquete(tmp_path):
    pr = piezas_de("LUCY", drenaje=True)
    carpeta = exportar(pr, tmp_path / "LUCY", comprimir=True)
    assert carpeta.suffix == ".zip" and carpeta.exists()
    ficha = json.loads((tmp_path / "LUCY" / "ficha.json").read_text(encoding="utf-8"))
    assert ficha["resumen"]["piezas"] == 8
    assert [m["caracter"] for m in ficha["montaje"]] == list("LUCY")
    for p in ficha["piezas"]:
        malla = trimesh.load(tmp_path / "LUCY" / p["archivo"])
        assert malla.is_watertight
        assert malla.extents == pytest.approx(p["medidas_mm"], abs=0.01)
    assert "MONTAJE" in (tmp_path / "LUCY" / "LEEME.txt").read_text(encoding="utf-8")


def test_exportar_no_pisa_otra_carpeta(tmp_path):
    (tmp_path / "otra.txt").write_text("no tocar")
    with pytest.raises(ErrorEntrada):
        exportar(piezas_de("L"), tmp_path)


def test_exportar_reproducible(tmp_path):
    exportar(piezas_de("LU"), tmp_path / "a")
    exportar(piezas_de("LU"), tmp_path / "b")
    for f in ("01-L-cuerpo.stl", "02-U-frente.stl", "ficha.json"):
        assert (tmp_path / "a" / f).read_bytes() == (tmp_path / "b" / f).read_bytes()


def test_cli_letrero_y_probeta(tmp_path, capsys):
    assert main(["letrero", "LUCY", "--estructura", "halo", "-o", str(tmp_path / "s")]) == 0
    assert "Piezas: 4" in capsys.readouterr().out
    assert main(["probeta", "-o", str(tmp_path / "p")]) == 0
    assert len(list((tmp_path / "p").glob("*.stl"))) == 5
    assert main(["letrero", "LUCY", "--pared", "0", "-o", str(tmp_path / "x")]) == 2
    assert "Error" in capsys.readouterr().err


def test_cli_m1_sigue_funcionando(tmp_path):
    assert main(["A", "--altura", "120", "--profundidad", "35", "-o", str(tmp_path / "A.stl")]) == 0
