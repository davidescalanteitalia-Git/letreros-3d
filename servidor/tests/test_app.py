import io
import zipfile

import pytest
import trimesh
from fastapi.testclient import TestClient

from servidor import app as modulo

PROYECTO = {
    "schema_version": 1, "project": "Lucy Hairstyle", "letters": "LUCY", "font": "Montserrat",
    "layout": "individual", "height": "120", "depth": "40", "wall": "1.6", "clearance": ".25",
    "style": "front", "material": "PETG", "ledtype": "white", "back": "snap",
    "face": "#f8fbff", "side": "#3d789f", "bedx": "320", "bedy": "310",
}


@pytest.fixture()
def cliente(monkeypatch):
    modulo._historial.clear()
    monkeypatch.setattr(modulo, "CLAVE", "")
    return TestClient(modulo.app)


def test_portada_y_cabeceras(cliente):
    r = cliente.get("/")
    assert r.status_code == 200 and "Letreros 3D Studio" in r.text
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


def test_salud_y_opciones(cliente):
    assert cliente.get("/api/salud").json()["ok"] is True
    o = cliente.get("/api/opciones").json()
    assert set(o["estilos_fabricables"]) == {"front", "halo", "box", "solid"}
    assert len(o["fuentes_fabricables"]) == 10 and "Pacifico" in o["fuentes_fabricables"]
    assert o["protegido"] is False


def test_comprobar(cliente):
    r = cliente.post("/api/comprobar", json=PROYECTO)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["estructura"] == "frontal" and len(d["piezas"]) == 8
    assert d["metros_led"] > 0 and "LUCY" in d["resumen"]


def test_descargar_letrero_zip(cliente):
    r = cliente.post("/api/letrero", json={**PROYECTO, "drenaje": True, "cable": "6"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert 'filename="LUCY-frontal.zip"' in r.headers["content-disposition"]
    z = zipfile.ZipFile(io.BytesIO(r.content))
    nombres = z.namelist()
    assert "LUCY-frontal/ficha.json" in nombres and "LUCY-frontal/LEEME.txt" in nombres
    stls = [n for n in nombres if n.endswith(".stl")]
    assert len(stls) == 8
    for n in stls:
        malla = trimesh.load(io.BytesIO(z.read(n)), file_type="stl")
        assert malla.is_watertight


@pytest.mark.parametrize("estilo, piezas", [("halo", 4), ("box", 4), ("solid", 4)])
def test_otras_estructuras(cliente, estilo, piezas):
    r = cliente.post("/api/comprobar", json={**PROYECTO, "style": estilo})
    assert r.status_code == 200 and len(r.json()["piezas"]) == piezas


def test_probeta(cliente):
    r = cliente.post("/api/probeta", json=PROYECTO)
    assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert len([n for n in z.namelist() if n.endswith(".stl")]) == 5


@pytest.mark.parametrize("cambio, texto", [
    ({"style": "neon"}, "aún no se fabrica"),
    ({"font": "Comic Sans"}, "no está entre las fuentes fabricables"),
    ({"height": "5000"}, "Altura"),
    ({"wall": "abc"}, "no es un número"),
    ({"letters": ""}, "vacío"),
    ({"schema_version": 2}, "versión"),
    ({"letters": "A\nB\nC\nD\nE"}, "líneas"),
    ({"letters": "A\nB", "alineacion": "justificada"}, "Alineación"),
])
def test_errores_claros(cliente, cambio, texto):
    r = cliente.post("/api/comprobar", json={**PROYECTO, **cambio})
    assert r.status_code == 422 and texto in r.json()["error"]


def test_cuerpo_invalido_y_grande(cliente):
    assert cliente.post("/api/comprobar", content=b"no json").status_code == 400
    assert cliente.post("/api/comprobar", json=[1, 2]).status_code == 400
    assert cliente.post("/api/comprobar", content=b"{" + b" " * 30000 + b"}").status_code == 413


def test_limite_de_peticiones(cliente, monkeypatch):
    monkeypatch.setattr(modulo, "LIMITE_MIN", 2)
    for _ in range(2):
        assert cliente.post("/api/comprobar", json={**PROYECTO, "letters": "I"}).status_code == 200
    assert cliente.post("/api/comprobar", json={**PROYECTO, "letters": "I"}).status_code == 429


def test_clave_opcional(cliente, monkeypatch):
    monkeypatch.setattr(modulo, "CLAVE", "secreta")
    assert cliente.post("/api/comprobar", json=PROYECTO).status_code == 401
    assert cliente.post("/api/comprobar", json=PROYECTO, headers={"X-Clave": "mala"}).status_code == 401
    ok = cliente.post("/api/comprobar", json={**PROYECTO, "letters": "I"}, headers={"X-Clave": "secreta"})
    assert ok.status_code == 200


def test_modelo_para_el_visor(cliente):
    import base64

    import numpy as np
    r = cliente.post("/api/modelo", json=PROYECTO)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["estructura"] == "frontal" and len(d["piezas"]) == 8
    frente = next(p for p in d["piezas"] if p["rol"] == "frente")
    v = np.frombuffer(base64.b64decode(frente["v"]), dtype=np.float32).reshape(-1, 3)
    i = np.frombuffer(base64.b64decode(frente["i"]), dtype=np.uint32).reshape(-1, 3)
    assert i.max() < len(v)
    # montado: el frente queda delante (z entre profundidad-encaje-frente y profundidad)
    assert v[:, 2].max() == pytest.approx(40, abs=1e-3) and v[:, 2].min() == pytest.approx(34, abs=1e-3)
    assert d["maximo"][2] == pytest.approx(40, abs=1e-3)


def test_modelo_halo_separadores_detras(cliente):
    d = cliente.post("/api/modelo", json={**PROYECTO, "style": "halo"}).json()
    assert d["minimo"][2] == pytest.approx(-20, abs=1e-3) and d["maximo"][2] == pytest.approx(40, abs=1e-3)


def test_vendor_three(cliente):
    r = cliente.get("/vendor/three.module.min.js")
    assert r.status_code == 200 and len(r.content) > 500_000
    assert cliente.get("/vendor/OrbitControls.js").status_code == 200


def test_v05_unidas_placa_y_division(cliente):
    unidas = cliente.post("/api/comprobar", json={**PROYECTO, "letters": "aperto", "font": "Pacifico",
                                                  "layout": "connected", "height": "60"}).json()
    assert [p["archivo"] for p in unidas["piezas"]] == ["01-aperto-cuerpo.stl", "01-aperto-frente.stl"]
    placa = cliente.post("/api/comprobar", json={**PROYECTO, "letters": "LU", "layout": "base", "height": "60"}).json()
    assert any(p["rol"] == "placa" for p in placa["piezas"]) and placa["costes"]["total_eur"] > 0
    m = cliente.post("/api/modelo", json={**PROYECTO, "letters": "W", "height": "250"}).json()
    roles = {(p["parte"], p["rol"]) for p in m["piezas"]}
    assert ("AB", "empalme") in roles and ("A", "cuerpo") in roles and ("B", "frente") in roles


def test_v06_lineas_camas_y_3mf(cliente):
    datos = {**PROYECTO, "letters": "LU\nCY", "height": "80", "alineacion": "izquierda", "interlineado": "1.3"}
    d = cliente.post("/api/comprobar", json=datos).json()
    assert len(d["piezas"]) == 8 and all(p["cama"] >= 1 for p in d["piezas"])
    assert {c["material"] for c in d["camas"]} == {"opaco", "difusor"}
    r = cliente.post("/api/letrero", json=datos)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert 'filename="LU-CY-frontal.zip"' in r.headers["content-disposition"]
    nombres = z.namelist()
    assert "LU-CY-frontal/contornos.dxf" in nombres
    assert any(n.startswith("LU-CY-frontal/camas/") and n.endswith(".3mf") for n in nombres)


def test_v06_visor_camas_y_division_horizontal(cliente):
    import numpy as np
    m = cliente.post("/api/modelo", json={**PROYECTO, "letters": "I", "height": "450"}).json()
    roles = {(p["parte"], p["rol"]) for p in m["piezas"]}
    assert ("12", "empalme") in roles and ("2", "frente") in roles
    for p in m["piezas"]:
        M = np.array(p["m_cama"]).reshape(4, 4).T
        assert M.shape == (4, 4) and p["cama"] >= 1
        assert abs(abs(np.linalg.det(M[:3, :3])) - 1) < 1e-4  # giro (o reflejo del frente), sin escala
