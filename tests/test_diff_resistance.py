"""D-RES-01: resistencia calculada por nuestro código desde la geometría vs `Resistance` guardada por VentSim.

Alcance: galerías con `Resistance Type` = 0 (fricción) o índice de preset discreto, en modelos con
densidad constante (AIRSIM[13]). Quedan fuera (registrado en docs/05): tipos negativos, galerías con
simulación térmica (densidad por galería) y ductos.
Tolerancia: error relativo < 1e-5 (VentSim guarda ~7 cifras significativas).
"""
from pathlib import Path

import pytest

from nvs.resistance import branch_resistance
from nvs.vsmio import aligned_table, read_vsm
from nvs.vsmnet import fl

EX = Path(r"C:\Program Files\Ventsim DESIGN 6\examples")
pytestmark = pytest.mark.skipif(not EX.exists(), reason="instalación de referencia ausente")


def model_density(v) -> float:
    d = [x for x in v.sections["AIRSIM"].rows if x != ["Description"]][0]
    return fl(d[13])


@pytest.mark.parametrize("fname", ["DemoMine.vsm", "Tutorial1.vsm", "Tutorial2.vsm", "RealMine.vsm"])
def test_resistance_from_geometry(fname):
    v = read_vsm(EX / fname)
    rows = aligned_table(v)
    rho = model_density(v)
    presets = {r[0]: fl(r[2]) for r in v.sections["RESISTANCES"].rows if len(r) > 3}
    checked = 0
    for r in rows:
        R_ref = fl(r["Resistance"])
        rt = r["Resistance Type"]
        if R_ref >= 1000 or fl(r["Area"]) <= 0 or fl(r["Perimeter"]) <= 0:
            continue
        if rt == "0":
            discrete = 0.0
        elif rt in presets:
            discrete = presets[rt]
        else:
            continue
        R = branch_resistance(fl(r["kFactor"]), fl(r["Length"]), fl(r["shock factor"]),
                              fl(r["Perimeter"]), fl(r["Area"]), rho, discrete)
        assert abs(R - R_ref) <= 1e-5 * max(abs(R_ref), 1e-9), (fname, r["Unique No"], R, R_ref)
        checked += 1
    assert checked > 100
