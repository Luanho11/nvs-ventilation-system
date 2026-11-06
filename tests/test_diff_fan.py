"""D-FAN-01: presión estática de ventilador evaluada con NUESTRA curva vs `Static Pressure` guardada.

Se evalúa en el caudal guardado de VentSim (`Quantity`), por unidad (Quantity / Fan Numbers).
Tolerancia: 5e-4 relativo (+0,05 Pa absoluto); VentSim guarda ~7 cifras, el error de lectura de los
puntos de entrada es del orden de 1e-5.
Alcance: ventiladores encendidos, 100 % de velocidad, un solo preset (Fan Config 0), densidad del
aire = densidad de la curva.
"""
from pathlib import Path

import pytest

from nvs.fan import parse_curves
from nvs.vsmio import aligned_table, read_vsm
from nvs.vsmnet import fl

EX = Path(r"C:\Program Files\Ventsim DESIGN 6\examples")
pytestmark = pytest.mark.skipif(not EX.exists(), reason="instalación de referencia ausente")


@pytest.mark.parametrize("fname", ["DemoMine.vsm", "Tutorial2.vsm", "RealMine.vsm"])
def test_static_pressure_from_curve(fname):
    v = read_vsm(EX / fname)
    rows = aligned_table(v)
    curves = parse_curves(v.sections["FANS"].rows)
    n_checked = 0
    for r in rows:
        ft = r["Fan Type"]
        if ft in ("", "0") or r["Fan Off"] == "True" or fl(r["Fan Speed"]) != 100 or r["Fan Config"] != "0":
            continue
        q = fl(r["Quantity"])
        if q <= 0 or ft not in curves:
            continue
        n = max(1, int(fl(r["Fan Numbers"])))
        got = curves[ft].static(q / n)
        ref = fl(r["Static Pressure"])
        assert abs(got - ref) <= 5e-4 * abs(ref) + 0.05, (fname, r["Unique No"], got, ref)
        n_checked += 1
    assert n_checked >= 1
