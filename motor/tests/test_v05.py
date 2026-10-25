"""Pruebas v0.5: fuentes, HarfBuzz, letras unidas, placa común, división, plantilla y presupuesto."""
import json

import pytest
import trimesh

from letreros_motor import Diseno, ErrorEntrada, exportar, generar_letrero
from letreros_motor.__main__ import main
from letreros_motor.fuentes import FUENTES, POR_FAMILIA_WEB, obtener_fuente, ttfont
from letreros_motor.texto import maquetar


# --- Fuentes ------------------------------------------------------------------

@pytest.mark.parametrize("clave", sorted(FUENTES))
def test_las_10_fuentes_cargan_y_respetan_la_mayuscula(clave):
    f = obtener_fuente(clave)
    assert (f.ruta.parent / f.archivo_licencia).is_file()
    letras = maquetar("H", clave, 100)
    tope = letras[0].forma.bounds[3]
    if f.estilo == "rotulo":
        assert tope == pytest.approx(100, abs=1.5)  # H = altura de mayúscula
    else:
        assert 98 <= tope <= 112  # manuscritas: la H lleva adornos que sobresalen un poco
    assert "fvar" not in ttfont(clave)  # las variables quedan fijadas


def test_familias_de_la_web():
    assert set(POR_FAMILIA_WEB) == {"Montserrat", "Poppins", "Roboto", "Oswald", "Bebas Neue", "Playfair Display",
                                    "Lobster", "Pacifico", "Dancing Script", "Great Vibes"}


# --- HarfBuzz -------------------------------------------------------------------

def test_kerning_acerca_av():
    av = maquetar("AV", "montserrat-bold", 100)
    ah = maquetar("AH", "montserrat-bold", 100)
    assert av[1].origen_x < ah[1].origen_x  # la V se mete bajo la A


def test_ligadura_y_formas_contextuales():
    letras = maquetar("fi", "lobster", 100)
    assert len(letras) == 1 and letras[0].caracter == "fi"


def test_palabras_numeradas():
    letras = maquetar("Bar Lucy", "pacifico", 80)
    assert {l.palabra for l in letras} == {0, 1}


# --- Letras unidas --------------------------------------------------------------

@pytest.mark.parametrize("fuente", ["pacifico", "lobster", "dancing-script-bold"])
def test_unidas_una_pieza_por_palabra(fuente):
    pr = generar_letrero(Diseno("aperto", fuente=fuente, conjunto="unidas", altura=60, estructura="maciza"))
    assert len(pr.letras) == 1 and pr.letras[0].letra.caracter == "aperto"
    assert all(p.malla.is_watertight for p in pr.piezas)


def test_unidas_dos_palabras_dos_piezas():
    pr = generar_letrero(Diseno("Bar Lucy", fuente="dancing-script-bold", conjunto="unidas", altura=60))
    assert [r.letra.caracter for r in pr.letras] == ["Bar", "Lucy"]


def test_unidas_con_barra():
    pr = generar_letrero(Diseno("IIII", conjunto="unidas", barra=10, altura=60, espaciado=10, estructura="maciza"))
    assert len(pr.letras) == 1
    assert pr.letras[0].letra.forma.bounds[1] == pytest.approx(0, abs=0.01)


def test_barra_demasiado_alta():
    with pytest.raises(ErrorEntrada, match="barra"):
        generar_letrero(Diseno("AB", conjunto="unidas", barra=50, altura=60))


# --- Placa común ------------------------------------------------------------------

def test_placa_con_ranuras_y_agujeros():
    pr = generar_letrero(Diseno("LU", conjunto="placa", altura=60, estructura="frontal"))
    placas = [p for p in pr.piezas if p.rol == "placa"]
    assert len(placas) == 1
    m = placas[0].malla
    x0, y0, z0 = m.bounds[0]
    x1, y1, z1 = m.bounds[1]
    assert z1 - z0 == pytest.approx(4)
    assert m.volume < (x1 - x0) * (y1 - y0) * 4 - 50  # ranuras + agujeros de cable y fijación


def test_placa_y_halo_incompatibles():
    with pytest.raises(ErrorEntrada, match="halo"):
        generar_letrero(Diseno("LU", conjunto="placa", estructura="halo"))


# --- División -------------------------------------------------------------------

def test_division_maciza_con_colas_sin_interferencia():
    pr = generar_letrero(Diseno("W", estructura="maciza", altura=250))
    a, b = pr.piezas
    assert (a.parte, b.parte) == ("A", "B")
    assert a.malla.bounds[1][0] > pr.letras[0].cortes[0] + 5  # la cola entra en B
    inter = trimesh.boolean.intersection([a.malla, b.malla], engine="manifold")
    assert inter.is_empty or inter.volume < 1e-3


@pytest.mark.parametrize("estructura", ["caja", "frontal", "halo"])
def test_division_hueca_con_empalme(estructura):
    pr = generar_letrero(Diseno("W", estructura=estructura, altura=250))
    roles = [(p.parte, p.rol) for p in pr.piezas]
    assert ("AB", "empalme") in roles
    cx, cy, _ = pr.diseno.cama
    for p in pr.piezas:
        assert p.malla.is_watertight
        w, h = sorted(p.malla.extents[:2])
        assert w <= min(cx, cy) and h <= max(cx, cy)


def test_division_desactivada():
    with pytest.raises(ErrorEntrada, match="no cabe"):
        generar_letrero(Diseno("W", altura=250, dividir=False))


# --- Plantilla, presupuesto y CLI -----------------------------------------------

def test_plantilla_svg_y_costes(tmp_path):
    pr = generar_letrero(Diseno("W", estructura="frontal", altura=250, precio_kg=30, precio_led_m=5))
    c = pr.costes()
    assert c["total_eur"] == pytest.approx(c["material_eur"] + c["led_eur"], abs=0.01) and c["led_eur"] > 0
    exportar(pr, tmp_path / "W")
    svg = (tmp_path / "W" / "plantilla-montaje.svg").read_text(encoding="utf-8")
    assert 'width="' in svg and 'mm"' in svg and "stroke-dasharray" in svg  # línea de corte
    ficha = json.loads((tmp_path / "W" / "ficha.json").read_text(encoding="utf-8"))
    assert ficha["resumen"]["costes"]["total_eur"] > 0 and ficha["montaje"][0]["cortes_x_mm"]


def test_cli_v05(tmp_path, capsys):
    assert main(["letrero", "aperto", "--fuente", "pacifico", "--conjunto", "unidas", "--altura", "60",
                 "--estructura", "frontal", "--precio-kg", "20", "-o", str(tmp_path / "a")]) == 0
    out = capsys.readouterr().out
    assert "Piezas: 2" in out and "Coste" in out
    assert (tmp_path / "a" / "plantilla-montaje.svg").exists()
