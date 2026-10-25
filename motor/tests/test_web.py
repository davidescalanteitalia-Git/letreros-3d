import json

import pytest

from letreros_motor import ErrorEntrada
from letreros_motor.__main__ import main
from letreros_motor.web import diseno_desde_web

BASE = {"schema_version": 1, "letters": "LUCY", "font": "Montserrat", "height": "120", "depth": "40",
        "wall": "1.6", "clearance": ".25", "style": "front", "bedx": "320", "bedy": "310"}


def test_traduccion_basica():
    d = diseno_desde_web(BASE)
    assert (d.texto, d.estructura, d.altura, d.profundidad, d.pared, d.holgura) == ("LUCY", "frontal", 120, 40, 1.6, 0.25)
    assert d.cama == (320, 310, 325)


@pytest.mark.parametrize("estilo, estructura", [("front", "frontal"), ("halo", "halo"), ("box", "caja"), ("solid", "maciza")])
def test_estilos(estilo, estructura):
    assert diseno_desde_web({**BASE, "style": estilo}).estructura == estructura


def test_campos_extra_y_coma_decimal():
    d = diseno_desde_web({**BASE, "frente": "2,4", "tira_led": "10", "drenaje": True, "cable": "0"})
    assert d.frente == 2.4 and d.tira_led == 10 and d.drenaje and d.cable == 0


@pytest.mark.parametrize("cambio", [
    {"schema_version": 3}, {"style": "neon"}, {"style": "dual"}, {"style": "x"}, {"font": "Pacifico"},
    {"height": "doce"}, {"bedx": "10", "bedy": "10"}, {"letters": {"a": 1}},
])
def test_rechazos(cambio):
    with pytest.raises(ErrorEntrada):
        diseno_desde_web({**BASE, **cambio})


def test_cli_desde_web(tmp_path, capsys):
    f = tmp_path / "lucy.json"
    f.write_text(json.dumps({**BASE, "letters": "LU"}), encoding="utf-8")
    assert main(["desde-web", str(f), "-o", str(tmp_path / "s")]) == 0
    assert len(list((tmp_path / "s").glob("*.stl"))) == 4
    assert main(["desde-web", str(tmp_path / "no.json"), "-o", str(tmp_path / "t")]) == 2
    (tmp_path / "malo.json").write_text("{", encoding="utf-8")
    assert main(["desde-web", str(tmp_path / "malo.json"), "-o", str(tmp_path / "u")]) == 2
