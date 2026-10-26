"""v0.7: estructuras profesionales (lateral, doble, neón, caja de luz), LED y fijaciones."""
import json

import numpy as np
import pytest

from letreros_motor import Diseno, ErrorEntrada, exportar, generar_letrero
from letreros_motor.estructuras import plan_led, separacion_filas


def _cerradas(pr):
    for p in pr.piezas:
        assert p.malla.is_watertight and p.malla.is_volume, p.archivo


def _montada(p):
    v = np.c_[p.malla.vertices, np.ones(len(p.malla.vertices))]
    m = p.montaje if p.montaje is not None else np.eye(4)
    return (v @ m.T)[:, :3]


def test_lateral_materiales_invertidos():
    pr = generar_letrero(Diseno("H", estructura="lateral", altura=80))
    mat = {p.rol: p.material for p in pr.piezas}
    assert mat == {"cuerpo": "difusor", "frente": "opaco"}
    _cerradas(pr)


def test_doble_frente_y_trasera_translucidos_con_separadores():
    pr = generar_letrero(Diseno("O", estructura="doble", altura=100, profundidad=40))
    piezas = {p.rol: p for p in pr.piezas}
    assert set(piezas) == {"cuerpo", "frente", "trasera"}
    assert piezas["frente"].material == piezas["trasera"].material == "difusor"
    assert pr.letras[0].puntos_separadores, "la trasera lleva agujeros para separadores"
    _cerradas(pr)
    # montadas: trasera abajo, anillo en medio, frente arriba hasta la profundidad
    assert _montada(piezas["trasera"])[:, 2].min() == pytest.approx(0, abs=1e-6)
    assert _montada(piezas["frente"])[:, 2].max() == pytest.approx(40, abs=1e-6)
    c = _montada(piezas["cuerpo"])[:, 2]
    assert c.min() == pytest.approx(2, abs=1e-6) and c.max() == pytest.approx(38, abs=1e-6)
    # LED lateral: una vuelta por hueco
    assert pr.letras[0].led["montaje"].startswith("lateral")


def test_doble_validacion():
    with pytest.raises(ErrorEntrada, match="doble"):
        generar_letrero(Diseno("O", estructura="doble", profundidad=12))
    with pytest.raises(ErrorEntrada, match="placa"):
        generar_letrero(Diseno("O", estructura="doble", conjunto="placa"))


def test_neon_canal_y_tubo():
    d = Diseno("S", estructura="neon", altura=120, profundidad=10, neon_ancho=8, neon_alto=12)
    pr = generar_letrero(d)
    (base,) = pr.piezas
    assert base.rol == "base" and base.material == "opaco"
    _cerradas(pr)
    r = pr.letras[0]
    assert r.visual and r.visual[0][0] == "neon"
    assert r.puntos_cable and 0.3 < r.metros_led < 1.5
    # la base tiene el canal: su volumen es menor que la silueta llena
    assert base.malla.volume < base.huella.area * 10 * 0.95


def test_neon_en_placa_comun():
    pr = generar_letrero(Diseno("ON", estructura="neon", altura=80, profundidad=10, conjunto="placa"))
    roles = [p.rol for p in pr.piezas]
    assert roles == ["placa"]
    assert pr.metros_led > 0
    assert pr.piezas[0].montaje is None  # la placa de neón es el propio letrero


def test_neon_validacion():
    with pytest.raises(ErrorEntrada, match="Neón"):
        generar_letrero(Diseno("S", estructura="neon", profundidad=40))


def test_caja_de_luz_piezas_y_encaje():
    d = Diseno("BAR", estructura="caja_luz", altura=60, profundidad=60, placa_margen=20)
    pr = generar_letrero(d)
    piezas = {p.rol: p for p in pr.piezas}
    assert set(piezas) == {"cuerpo", "difusor", "mascara"}
    assert piezas["difusor"].material == "difusor" and piezas["mascara"].material == "opaco"
    _cerradas(pr)
    r = pr.letras[0]
    assert r.led["filas"] >= 1 and r.metros_led > 0
    assert len(r.puntos_fijacion) == 2  # dos colgadores
    # cara a ras: difusor + máscara montados acaban en la profundidad
    assert _montada(piezas["mascara"])[:, 2].max() == pytest.approx(60, abs=1e-6)
    assert _montada(piezas["difusor"])[:, 2].max() == pytest.approx(60, abs=1e-6)
    # las letras del difusor no chocan con la máscara (hay holgura)
    huecos_mascara = piezas["mascara"].huella  # contorno completo
    assert huecos_mascara.area > 0


def test_caja_de_luz_grande_se_divide():
    pr = generar_letrero(Diseno("ABIERTO", estructura="caja_luz", altura=80, profundidad=60))
    assert any(p.parte for p in pr.piezas)
    _cerradas(pr)


@pytest.mark.parametrize("fijacion", ["insertos", "pasantes"])
def test_fijaciones(fijacion):
    base = generar_letrero(Diseno("O", estructura="frontal", altura=120))
    con = generar_letrero(Diseno("O", estructura="frontal", altura=120, fijacion=fijacion))
    assert con.letras[0].puntos_fijacion
    v0 = next(p for p in base.piezas if p.rol == "cuerpo").malla.volume
    v1 = next(p for p in con.piezas if p.rol == "cuerpo").malla.volume
    assert (v1 > v0) if fijacion == "insertos" else (v1 < v0)
    _cerradas(con)


def test_fijacion_desconocida():
    with pytest.raises(ErrorEntrada, match="Fijación"):
        generar_letrero(Diseno("O", fijacion="clavos"))


def test_plan_led_y_electrico(tmp_path):
    d = Diseno("LUZ", estructura="frontal", altura=150, profundidad=60, w_por_metro=10, tension=24)
    pr = generar_letrero(d)
    assert separacion_filas(pr.diseno) == pytest.approx(60 - 2 - 2)
    exportar(pr, tmp_path / "L")
    ficha = json.loads((tmp_path / "L" / "ficha.json").read_text(encoding="utf-8"))
    e = ficha["resumen"]["electrico"]
    assert e["vatios"] == pytest.approx(pr.metros_led * 10, abs=0.1)
    assert e["amperios"] == pytest.approx(e["vatios"] / 24, abs=0.01)
    assert e["fuente_w"] >= e["vatios"] * 1.2
    leeme = (tmp_path / "L" / "LEEME.txt").read_text(encoding="utf-8")
    assert "LUZ E INSTALACIÓN" in leeme and "Fuente recomendada" in leeme
    assert all("led" in m for m in ficha["montaje"])


def test_sin_w_por_metro_no_inventa_consumo():
    pr = generar_letrero(Diseno("I", estructura="frontal", altura=100))
    from letreros_motor.proyecto import plan_electrico
    assert "vatios" not in plan_electrico(pr)


def test_paso_led_manual_da_mas_metros():
    auto = generar_letrero(Diseno("O", estructura="frontal", altura=200, profundidad=60))
    denso = generar_letrero(Diseno("O", estructura="frontal", altura=200, profundidad=60, paso_led=15))
    assert denso.metros_led > auto.metros_led


def test_plantilla_marca_fijaciones(tmp_path):
    pr = generar_letrero(Diseno("O", estructura="caja", altura=120, fijacion="pasantes"))
    exportar(pr, tmp_path / "O")
    svg = (tmp_path / "O" / "plantilla-montaje.svg").read_text(encoding="utf-8")
    assert svg.count('stroke="#7a3db8"') >= 2


def test_camas_por_material_en_caja_de_luz():
    pr = generar_letrero(Diseno("BAR", estructura="caja_luz", altura=60, profundidad=60))
    mats = {c.material for c in pr.camas()}
    assert mats == {"opaco", "difusor"}
