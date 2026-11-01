"""v0.9: logotipos SVG/DXF con las mismas estructuras que las letras."""
from pathlib import Path

import pytest

from letreros_motor import Diseno, ErrorEntrada, generar_letrero
from letreros_motor.logos import leer_logo, proporcion

DATOS = Path(__file__).parent / "datos"


def _logo(nombre):
    return leer_logo((DATOS / nombre).read_text(encoding="utf-8"), nombre)


def test_svg_relleno_agujeros_y_transformaciones():
    forma, avisos = _logo("logo.svg")
    assert forma.bounds[1] == pytest.approx(0) and forma.bounds[3] == pytest.approx(1)
    assert len(forma.geoms) == 3  # anillo, estrella, barra
    assert sum(len(g.interiors) for g in forma.geoms) == 1  # el agujero del anillo
    assert proporcion(forma) == pytest.approx(180 / 88, rel=0.02)
    assert any("sin relleno" in a for a in avisos)


def test_dxf_regiones_por_niveles():
    forma, _ = _logo("logo.dxf")
    grande = max(forma.geoms, key=lambda g: g.area)
    assert len(grande.interiors) == 2  # círculo y triángulo vaciados
    assert len(forma.geoms) == 2  # + la isla del círculo pequeño


@pytest.mark.parametrize("texto", [
    '<!DOCTYPE svg [<!ENTITY a "x">]><svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><line x1="0" y1="0" x2="5" y2="5" stroke="#000"/></svg>',
    "no es un archivo",
])
def test_svg_rechazados(texto):
    with pytest.raises(ErrorEntrada):
        leer_logo(texto, "x.svg")


@pytest.mark.parametrize("estructura, posicion", [("frontal", "izquierda"), ("neon", "arriba"),
                                                   ("maciza", "derecha"), ("halo", "abajo")])
def test_letrero_con_logo(estructura, posicion):
    logo, _ = _logo("logo.svg")
    d = Diseno("BAR", estructura=estructura, altura=80, profundidad=10 if estructura == "neon" else 40,
               logo_altura=90, logo_posicion=posicion, logo_separacion=20)
    pr = generar_letrero(d, logo)
    del_logo = [p for p in pr.piezas if p.letra.caracter == "logo"]
    assert del_logo and all(p.malla.is_watertight for p in pr.piezas)
    letras = [r for r in pr.letras if r.letra.caracter != "logo"]
    lb = letras[0].letra.forma.bounds
    gb = next(r for r in pr.letras if r.letra.caracter == "logo").letra.forma.bounds
    assert gb[3] - gb[1] == pytest.approx(90, abs=0.5)
    if posicion == "izquierda":
        assert gb[2] < lb[0]
    if posicion == "arriba":
        assert gb[1] > max(r.letra.forma.bounds[3] for r in letras)


def test_solo_logo_sin_texto():
    logo, _ = _logo("logo.dxf")
    pr = generar_letrero(Diseno("", estructura="caja", logo_altura=100), logo)
    assert pr.piezas and "logo" in pr.resumen()


def test_logo_en_placa_comun():
    logo, _ = _logo("logo.svg")
    pr = generar_letrero(Diseno("BAR", estructura="frontal", altura=60, conjunto="placa", logo_altura=60), logo)
    placa = next(p for p in pr.piezas if p.rol == "placa")
    assert placa.huella.bounds[0] < -60  # la placa abarca también el logo


def test_posicion_desconocida():
    with pytest.raises(ErrorEntrada, match="Posición del logo"):
        generar_letrero(Diseno("A", logo_posicion="centro"))


def test_tiempo_de_impresion(tmp_path):
    import json

    from letreros_motor import exportar
    pr = generar_letrero(Diseno("LUCY", estructura="frontal", altura=100))
    h = pr.horas_impresion()
    assert 1.0 < h < 20.0
    assert "de impresión" in pr.resumen()
    exportar(pr, tmp_path / "L")
    ficha = json.loads((tmp_path / "L" / "ficha.json").read_text(encoding="utf-8"))
    assert ficha["resumen"]["impresion_h"] == pytest.approx(h, abs=0.01)
    assert all(c["tiempo_min"] > 5 for c in ficha["camas"])
    leeme = (tmp_path / "L" / "LEEME.txt").read_text(encoding="utf-8")
    assert "AJUSTES RECOMENDADOS EN BAMBU STUDIO" in leeme and "Bambu Studio da el tiempo exacto" in leeme


def test_mas_material_mas_tiempo():
    a = generar_letrero(Diseno("I", estructura="maciza", altura=80, profundidad=10)).horas_impresion()
    b = generar_letrero(Diseno("I", estructura="maciza", altura=160, profundidad=10)).horas_impresion()
    assert b > a
