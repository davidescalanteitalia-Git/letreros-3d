import hashlib
import math

import pytest
import trimesh

from letreros_motor import ErrorEntrada, Parametros, exportar_stl, generar_letra
from letreros_motor.__main__ import main


def generar(letra="A", altura=120, profundidad=35, **kw):
    return generar_letra(Parametros(letra, altura, profundidad, **kw))


# --- Geometría auténtica ---------------------------------------------------

@pytest.mark.parametrize(
    "letra, cuerpos, agujeros",
    [("A", 1, 1), ("B", 1, 2), ("O", 1, 1), ("L", 1, 0), ("8", 1, 2), ("i", 2, 0), ("Ñ", 2, 0), ("Á", 2, 1)],
)
def test_topologia_contornos_interiores(letra, cuerpos, agujeros):
    malla, inf = generar(letra)
    assert (inf.cuerpos, inf.agujeros) == (cuerpos, agujeros)
    # Característica de Euler de la superficie: 2 por cuerpo, −2 por cada agujero pasante.
    assert malla.euler_number == 2 * cuerpos - 2 * agujeros
    assert len(malla.split(only_watertight=True)) == cuerpos


@pytest.mark.parametrize("letra", list("ABCDEFGHIJKLMNÑOPQRSTUVWXYZ0123456789") + list("aegñ&"))
def test_malla_manifold(letra):
    malla, inf = generar(letra, altura=60, profundidad=10)
    assert malla.is_watertight and malla.is_winding_consistent and malla.is_volume
    assert inf.estanca and malla.volume > 0


@pytest.mark.parametrize("altura, profundidad", [(20, 5), (120, 35), (300, 250)])
def test_dimensiones_en_mm(altura, profundidad):
    malla, inf = generar("H", altura, profundidad)
    minimo, maximo = malla.bounds
    assert minimo == pytest.approx([0, 0, 0], abs=1e-9)
    assert maximo[1] == pytest.approx(altura, abs=1e-6)
    assert maximo[2] == pytest.approx(profundidad, abs=1e-9)
    assert inf.alto_mm == pytest.approx(altura, abs=1e-6)


def test_volumen_igual_area_por_profundidad():
    malla, inf = generar("B", 120, 35)
    assert malla.volume == pytest.approx(inf.area_cara_mm2 * 35, rel=1e-9)


def test_escala_proporcional():
    _, chica = generar("A", 60, 10)
    _, grande = generar("A", 120, 10)
    assert grande.ancho_mm / chica.ancho_mm == pytest.approx(2, rel=1e-3)
    assert grande.area_cara_mm2 / chica.area_cara_mm2 == pytest.approx(4, rel=5e-3)


def test_tolerancia_de_curvas():
    _, fina = generar("O", 120, 10, tolerancia_mm=0.01)
    _, basta = generar("O", 120, 10, tolerancia_mm=0.3)
    # El área converge al afinar; la diferencia queda acotada.
    assert abs(fina.area_cara_mm2 - basta.area_cara_mm2) / fina.area_cara_mm2 < 0.01
    assert fina.triangulos > basta.triangulos


# --- STL --------------------------------------------------------------------

def test_stl_ida_y_vuelta(tmp_path):
    malla, _ = generar("A")
    ruta = exportar_stl(malla, tmp_path / "A.stl")
    leida = trimesh.load(ruta)
    assert leida.is_watertight and leida.is_volume
    assert leida.volume == pytest.approx(malla.volume, rel=1e-5)  # STL guarda float32
    assert leida.extents == pytest.approx(malla.extents, abs=1e-3)


def test_stl_reproducible(tmp_path):
    a = exportar_stl(generar("R")[0], tmp_path / "a.stl").read_bytes()
    b = exportar_stl(generar("R")[0], tmp_path / "b.stl").read_bytes()
    assert hashlib.sha256(a).digest() == hashlib.sha256(b).digest()


def test_extension_obligatoria(tmp_path):
    with pytest.raises(ErrorEntrada):
        exportar_stl(generar("A")[0], tmp_path / "A.obj")


# --- Entradas y errores -----------------------------------------------------

@pytest.mark.parametrize(
    "letra, altura, profundidad",
    [
        ("", 120, 35), ("AB", 120, 35), (" ", 120, 35), ("\n", 120, 35),
        ("A", 0, 35), ("A", 19.9, 35), ("A", 1501, 35), ("A", math.nan, 35), ("A", "x", 35),
        ("A", 120, 4), ("A", 120, 251), ("A", 120, math.inf),
        ("漢", 120, 35),  # no está en la fuente
        ("W", 400, 35),   # no cabe en la cama A2L
    ],
)
def test_entradas_invalidas(letra, altura, profundidad):
    with pytest.raises(ErrorEntrada):
        generar(letra, altura, profundidad)


def test_fuente_no_autorizada():
    with pytest.raises(ErrorEntrada):
        generar(fuente="arial")


def test_unicode_normalizado():
    # "A" + acento combinado (2 puntos de código) equivale a "Á".
    _, inf = generar("Á")
    assert inf.letra == "Á"


def test_aviso_trazos_finos():
    from shapely.geometry import MultiPolygon, box
    from letreros_motor.generador import _comprobar_trazos

    assert _comprobar_trazos(MultiPolygon([box(0, 0, 10, 50)])) == []
    avisos = _comprobar_trazos(MultiPolygon([box(0, 0, 10, 50), box(20, 0, 20.3, 50)]))
    assert any("boquilla" in a for a in avisos)
    # Montserrat Bold a 20 mm no tiene trazos por debajo de 0,4 mm.
    assert generar("A", 20, 5)[1].advertencias == []


def test_cama_util_y_giro():
    # 315 mm de alto supera Y=310 pero cabe girada (Y↔X).
    _, inf = generar("I", 315, 10)
    assert any("girada" in a for a in inf.advertencias)
    with pytest.raises(ErrorEntrada, match="no cabe"):
        generar("I", 330, 10)


# --- CLI --------------------------------------------------------------------

def test_cli_ok(tmp_path, capsys):
    destino = tmp_path / "A.stl"
    assert main(["A", "--altura", "120", "--profundidad", "35", "-o", str(destino)]) == 0
    assert destino.stat().st_size > 84
    assert "manifold): sí" in capsys.readouterr().out


def test_cli_error(tmp_path, capsys):
    assert main(["AB", "--altura", "120", "--profundidad", "35", "-o", str(tmp_path / "x.stl")]) == 2
    assert "Error" in capsys.readouterr().err
