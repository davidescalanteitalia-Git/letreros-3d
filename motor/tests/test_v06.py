"""v0.6: varias líneas, división horizontal (rejilla), camas 3MF y contornos DXF."""
import io
import json
import zipfile

import numpy as np
import pytest
import trimesh

from letreros_motor import Diseno, ErrorEntrada, exportar, generar_letrero
from letreros_motor.camas import distribuir, leer_3mf
from letreros_motor.diseno import CAMA_A2L_MM
from letreros_motor.texto import maquetar


# --------------------------------------------------------------------------- varias líneas

def test_dos_lineas_centradas():
    letras = maquetar("BAR\nLUCY", "montserrat-bold", 60)
    assert [l.linea for l in letras] == [0, 0, 0, 1, 1, 1, 1]
    # la segunda línea baja 1,4 × altura
    assert letras[3].forma.bounds[3] == pytest.approx(60 - 1.4 * 60, abs=1.5)
    # centradas: el centro de la tinta coincide
    def centro(ls):
        return (min(l.forma.bounds[0] for l in ls) + max(l.forma.bounds[2] for l in ls)) / 2
    assert centro(letras[:3]) == pytest.approx(centro(letras[3:]), abs=0.01)
    # cada línea es palabra nueva (para «unidas»)
    assert letras[2].palabra != letras[3].palabra


@pytest.mark.parametrize("alineacion", ["izquierda", "derecha"])
def test_alineacion(alineacion):
    letras = maquetar("I\nMMM", "montserrat-bold", 50, alineacion=alineacion)
    i, mmm = letras[0], letras[1:]
    if alineacion == "izquierda":
        assert i.forma.bounds[0] == pytest.approx(min(l.forma.bounds[0] for l in mmm), abs=0.01)
    else:
        assert i.forma.bounds[2] == pytest.approx(max(l.forma.bounds[2] for l in mmm), abs=0.01)


def test_una_linea_igual_que_antes():
    a = maquetar("LUCY", "montserrat-bold", 100)
    b = maquetar("LUCY\n", "montserrat-bold", 100)
    assert [l.forma.bounds for l in a] == [l.forma.bounds for l in b]
    assert a[0].forma.bounds[0] > 0  # sin desplazamiento: se conserva el origen tipográfico


def test_interlineado_y_errores():
    junto = maquetar("A\nA", "montserrat-bold", 50, interlineado=1.0)
    assert junto[0].forma.bounds[1] - junto[1].forma.bounds[1] == pytest.approx(50, abs=0.01)
    with pytest.raises(ErrorEntrada, match="Interlineado"):
        generar_letrero(Diseno("A\nB", interlineado=5))
    with pytest.raises(ErrorEntrada, match="Alineación"):
        generar_letrero(Diseno("A\nB", alineacion="justificada"))
    with pytest.raises(ErrorEntrada, match="líneas"):
        generar_letrero(Diseno("A\nB\nC\nD\nE"))


def test_unidas_por_linea():
    pr = generar_letrero(Diseno("ab\ncd", fuente="pacifico", conjunto="unidas", altura=40, estructura="maciza"))
    assert sorted(r.letra.caracter for r in pr.letras) == ["ab", "cd"]


# --------------------------------------------------------------------------- división horizontal

def _todas_cerradas(pr):
    for p in pr.piezas:
        assert p.malla.is_watertight and p.malla.is_volume, p.archivo


def test_rejilla_maciza_conserva_material():
    pr = generar_letrero(Diseno("W", estructura="maciza", altura=700, profundidad=20))
    r = pr.letras[0]
    assert r.cortes_y and r.cortes
    nombres = {p.parte for p in pr.piezas}
    assert all(n[0] in "ABCD" and n[1:].isdigit() for n in nombres)
    _todas_cerradas(pr)
    entera = r.letra.forma.area * 20
    suma = sum(p.malla.volume for p in pr.piezas)
    assert suma == pytest.approx(entera, rel=0.01)  # solo se pierde la holgura de las colas
    assert suma < entera
    for p in pr.piezas:
        w, h = sorted(p.malla.extents[:2])
        assert w <= CAMA_A2L_MM[1] and h <= CAMA_A2L_MM[0]


def test_rejilla_hueca_con_empalmes_horizontales():
    pr = generar_letrero(Diseno("I", estructura="frontal", altura=450))
    partes = {(p.parte, p.rol) for p in pr.piezas}
    assert {("1", "cuerpo"), ("2", "cuerpo"), ("1", "frente"), ("2", "frente"), ("12", "empalme")} <= partes
    _todas_cerradas(pr)
    empalme = next(p for p in pr.piezas if p.rol == "empalme")
    y = pr.letras[0].cortes_y[0]
    # la placa de empalme cruza la junta horizontal
    assert empalme.huella.bounds[1] < y < empalme.huella.bounds[3]


def test_plantilla_dibuja_cortes_horizontales(tmp_path):
    pr = generar_letrero(Diseno("I", estructura="maciza", altura=400, profundidad=10))
    exportar(pr, tmp_path / "I")
    svg = (tmp_path / "I" / "plantilla-montaje.svg").read_text(encoding="utf-8")
    assert svg.count('stroke-dasharray="3 2"') == len(pr.letras[0].juntas) >= 1
    ficha = json.loads((tmp_path / "I" / "ficha.json").read_text(encoding="utf-8"))
    assert ficha["montaje"][0]["cortes_y_mm"]
    assert "abajo arriba" in (tmp_path / "I" / "LEEME.txt").read_text(encoding="utf-8")


# --------------------------------------------------------------------------- camas y 3MF

def test_camas_sin_solapes_y_dentro():
    pr = generar_letrero(Diseno("LUCY\nHAIR", estructura="frontal", altura=120))
    camas = distribuir(pr.piezas, CAMA_A2L_MM)
    assert sum(len(c.colocaciones) for c in camas) == len(pr.piezas)
    assert {c.material for c in camas} == {"opaco", "difusor"}
    for c in camas:
        assert all((col.pieza.rol == "frente") == (c.material == "difusor") for col in c.colocaciones)
        rects = []
        for col in c.colocaciones:
            v = np.c_[col.pieza.malla.vertices, np.ones(len(col.pieza.malla.vertices))] @ col.matriz.T
            lo, hi = v[:, :3].min(axis=0), v[:, :3].max(axis=0)
            assert lo[2] == pytest.approx(0, abs=1e-6)
            assert lo[0] >= 5 - 1e-6 and lo[1] >= 5 - 1e-6
            assert hi[0] <= 5 + CAMA_A2L_MM[0] + 1e-6 and hi[1] <= 5 + CAMA_A2L_MM[1] + 1e-6
            rects.append((lo[0], lo[1], hi[0], hi[1]))
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], "piezas solapadas"


def test_pieza_larga_se_gira_para_caber():
    pr = generar_letrero(Diseno("I", estructura="maciza", altura=315, profundidad=10))
    camas = distribuir(pr.piezas, CAMA_A2L_MM)
    assert len(camas) == 1 and camas[0].colocaciones[0].alto <= CAMA_A2L_MM[1]


def test_zip_con_camas_3mf_y_dxf(tmp_path):
    pr = generar_letrero(Diseno("LU", estructura="caja", altura=80))
    ruta = exportar(pr, tmp_path / "LU", comprimir=True)
    z = zipfile.ZipFile(ruta)
    nombres = z.namelist()
    tres = [n for n in nombres if n.endswith(".3mf")]
    assert tres and all(n.startswith("LU/camas/cama-") for n in tres)
    objetos = [o for n in tres for o in leer_3mf(z.read(n))]
    assert sorted(o[0] + ".stl" for o in objetos) == sorted(p.archivo for p in pr.piezas)
    for nombre, v, f in objetos:
        malla = trimesh.Trimesh(v, f, process=True)
        original = next(p for p in pr.piezas if p.archivo == nombre + ".stl").malla
        assert malla.is_watertight
        assert malla.volume == pytest.approx(original.volume, rel=1e-4)
    # el 3MF es determinista
    assert exportar(pr, tmp_path / "LU2", comprimir=True).read_bytes().count(b"cama-") >= 1
    a = zipfile.ZipFile(tmp_path / "LU2.zip").read(tres[0].replace("LU/", "LU2/"))
    assert a == z.read(tres[0])
    ficha = json.loads(z.read("LU/ficha.json"))
    assert ficha["camas"] and ficha["camas"][0]["archivo"].startswith("camas/")


def test_dxf_contornos(tmp_path):
    import ezdxf

    pr = generar_letrero(Diseno("O", estructura="caja", altura=100, conjunto="placa"))
    exportar(pr, tmp_path / "O")
    doc = ezdxf.readfile(tmp_path / "O" / "contornos.dxf")
    assert doc.units == ezdxf.units.MM
    msp = doc.modelspace()
    letras = msp.query('LWPOLYLINE[layer=="LETRAS"]')
    assert len(letras) == 2  # contorno exterior + agujero de la O
    assert len(msp.query('LWPOLYLINE[layer=="PLACA"]')) == 1
    assert len(msp.query('CIRCLE[layer=="CABLE"]')) == 1
    # medidas 1:1: ancho de la O
    xs = [x for e in letras for x, *_ in e.get_points()]
    ancho = pr.letras[0].letra.forma.bounds[2] - pr.letras[0].letra.forma.bounds[0]
    assert max(xs) - min(xs) == pytest.approx(ancho, abs=0.05)


def test_carpeta_reutilizable(tmp_path):
    pr = generar_letrero(Diseno("I", estructura="maciza", altura=40, profundidad=5))
    exportar(pr, tmp_path / "I")
    exportar(pr, tmp_path / "I")  # volver a exportar en la misma carpeta no falla
    with pytest.raises(ErrorEntrada):
        (tmp_path / "otra").mkdir()
        (tmp_path / "otra" / "foto.jpg").write_bytes(b"x")
        exportar(pr, tmp_path / "otra")
