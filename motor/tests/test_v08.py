"""v0.8: letras unidas por piezas de N letras, tapas desplazadas y una sola salida de cable."""
import pytest

from letreros_motor import Diseno, ErrorEntrada, generar_letrero


@pytest.mark.parametrize("fuente", ["pacifico", "montserrat-bold", "dancing-script-bold"])
def test_aperto_en_piezas_de_dos(fuente):
    pr = generar_letrero(Diseno("aperto", estructura="frontal", fuente=fuente, conjunto="unidas",
                                letras_por_pieza=2, altura=100))
    cuerpos = [p.parte for p in pr.piezas if p.rol == "cuerpo"]
    assert cuerpos == ["ap", "er", "to"]
    assert sorted(p.parte for p in pr.piezas if p.rol == "empalme") == ["ap+er", "er+to"]
    for p in pr.piezas:
        assert p.malla.is_watertight
        w, h = sorted(p.malla.extents[:2])
        assert w <= 310 and h <= 320


def test_tapas_desplazadas_cruzan_la_junta():
    pr = generar_letrero(Diseno("aperto", estructura="frontal", fuente="pacifico", conjunto="unidas",
                                letras_por_pieza=2, altura=100))
    corte = pr.letras[0].cortes[0]
    tapa_ap = next(p for p in pr.piezas if p.rol == "frente" and p.parte == "ap")
    cuerpo_ap = next(p for p in pr.piezas if p.rol == "cuerpo" and p.parte == "ap")
    assert cuerpo_ap.huella.bounds[2] <= corte + 1
    assert tapa_ap.huella.bounds[2] > corte + 10  # la tapa pisa la pieza siguiente


def test_maciza_por_piezas_con_cola_de_milano():
    pr = generar_letrero(Diseno("aperto", estructura="maciza", fuente="pacifico", conjunto="unidas",
                                letras_por_pieza=2, altura=80, profundidad=15))
    assert [p.parte for p in pr.piezas] == ["ap", "er", "to"]
    assert any("cola de milano" in a for a in pr.avisos)


@pytest.mark.parametrize("salida", ["inicio", "fin"])
def test_una_sola_salida_de_cable(salida):
    pr = generar_letrero(Diseno("aperto", estructura="frontal", fuente="pacifico", conjunto="unidas",
                                letras_por_pieza=2, altura=100, salida_cable=salida))
    (pc,) = pr.letras[0].puntos_cable
    minx, _, maxx, _ = pr.letras[0].letra.forma.bounds
    if salida == "inicio":
        assert pc[0] < minx + 0.35 * (maxx - minx)
    else:
        assert pc[0] > maxx - 0.35 * (maxx - minx)
    con_agujero = [p for p in pr.piezas if p.rol == "cuerpo" and p.malla.volume < 0]  # (ninguna invertida)
    assert not con_agujero


def test_salida_unica_con_varias_palabras_avisa():
    pr = generar_letrero(Diseno("bar abierto", estructura="frontal", fuente="pacifico", conjunto="unidas",
                                altura=60, salida_cable="fin"))
    cables = [r.puntos_cable for r in pr.letras]
    assert sum(1 for c in cables if c) == 1
    assert any("Una sola salida" in a for a in pr.avisos)


def test_pieza_demasiado_grande_explica():
    with pytest.raises(ErrorEntrada, match="menos letras por pieza"):
        generar_letrero(Diseno("aperto", estructura="frontal", fuente="pacifico", conjunto="unidas",
                               letras_por_pieza=5, altura=200))


def test_validacion_campos():
    with pytest.raises(ErrorEntrada, match="Letras por pieza"):
        generar_letrero(Diseno("aperto", letras_por_pieza=20))
    with pytest.raises(ErrorEntrada, match="Salida de cable"):
        generar_letrero(Diseno("aperto", salida_cable="arriba"))


def test_neon_por_piezas():
    pr = generar_letrero(Diseno("aperto", estructura="neon", fuente="lobster", conjunto="unidas",
                                letras_por_pieza=2, altura=100, profundidad=10))
    assert [p.parte for p in pr.piezas] == ["ap", "er", "to"]
