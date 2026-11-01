"""v0.10: acabados (canto en chaflán/redondeado, reborde) y colores por pieza y cama."""
import pytest

from letreros_motor import Diseno, ErrorEntrada, generar_letrero
from letreros_motor.camas import nombre_color


def _frente(pr):
    return next(p for p in pr.piezas if p.rol == "frente")


@pytest.mark.parametrize("canto", ["chaflan", "redondeado"])
def test_canto_quita_material_en_la_cara(canto):
    recto = _frente(generar_letrero(Diseno("O", estructura="frontal", altura=100)))
    trabajado = _frente(generar_letrero(Diseno("O", estructura="frontal", altura=100, canto=canto, canto_mm=1.2)))
    assert trabajado.malla.is_watertight
    assert trabajado.malla.volume < recto.malla.volume
    # misma huella exterior (el canto no cambia la medida de la letra)
    assert trabajado.malla.extents[0] == pytest.approx(recto.malla.extents[0], abs=0.01)
    # la cara apoyada en la cama es más pequeña que la sección completa
    z0 = trabajado.malla.vertices[:, 2].min()
    base = trabajado.malla.vertices[abs(trabajado.malla.vertices[:, 2] - z0) < 1e-6]
    assert base[:, 0].max() - base[:, 0].min() < trabajado.malla.extents[0] - 1.0


def test_chaflan_mas_material_que_redondeado():
    ch = _frente(generar_letrero(Diseno("H", estructura="frontal", canto="chaflan", canto_mm=1.4)))
    rd = _frente(generar_letrero(Diseno("H", estructura="frontal", canto="redondeado", canto_mm=1.4)))
    assert rd.malla.volume > ch.malla.volume  # el redondeo quita menos que el chaflán


@pytest.mark.parametrize("estructura, kw", [("maciza", {"profundidad": 15}), ("halo", {}), ("neon", {"profundidad": 10}),
                                            ("doble", {}), ("lateral", {})])
def test_canto_en_todas_las_estructuras(estructura, kw):
    pr = generar_letrero(Diseno("A", estructura=estructura, altura=80, canto="chaflan", canto_mm=1.0, **kw))
    assert all(p.malla.is_watertight for p in pr.piezas)


def test_reborde_agranda_el_frente():
    sin = _frente(generar_letrero(Diseno("I", estructura="frontal", altura=100)))
    con = _frente(generar_letrero(Diseno("I", estructura="frontal", altura=100, reborde=1.5)))
    assert con.malla.extents[0] == pytest.approx(sin.malla.extents[0] + 3.0, abs=0.05)


def test_colores_por_pieza_y_camas():
    pr = generar_letrero(Diseno("LU", estructura="frontal", altura=80, color_cuerpo="#c81e1e", color_frente="#f2f2f2"))
    assert {p.rol: p.color for p in pr.piezas} == {"cuerpo": "#c81e1e", "frente": "#f2f2f2"}
    nombres = [c.archivo for c in pr.camas()]
    assert any(n.endswith("opaco-rojo.3mf") for n in nombres) and any(n.endswith("difusor-blanco.3mf") for n in nombres)


def test_caja_de_luz_mascara_color_cuerpo():
    pr = generar_letrero(Diseno("BAR", estructura="caja_luz", altura=60, profundidad=60, color_cuerpo="#1f1f1f"))
    assert next(p for p in pr.piezas if p.rol == "mascara").color == "#1f1f1f"


def test_nombre_color():
    assert nombre_color("#c8a03c") == "dorado" and nombre_color("#101010") == "negro"


def test_validacion_acabado():
    with pytest.raises(ErrorEntrada, match="Canto"):
        generar_letrero(Diseno("A", canto="ondulado"))
    with pytest.raises(ErrorEntrada, match="Color"):
        generar_letrero(Diseno("A", color_frente="rojo"))
