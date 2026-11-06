"""D-NET-02 (predictiva): R desde geometría + curvas de ventilador propias → caudales vs VentSim.

A diferencia de D-NET-01, aquí NO se usan presiones de ventilador ni resistencias resultantes guardadas
(salvo los tipos de resistencia aún sin descifrar, contados en `info`). Tolerancia 1e-3 relativo, |Q|>1.
"""
from pathlib import Path

import numpy as np
import pytest

from nvs.network import solve
from nvs.vsmio import aligned_table, read_vsm
from nvs.vsmnet import fl, network_predictive

EX = Path(r"C:\Program Files\Ventsim DESIGN 6\examples")
pytestmark = pytest.mark.skipif(not EX.exists(), reason="instalación de referencia ausente")


@pytest.mark.parametrize("fname", ["Tutorial1.vsm", "Tutorial2.vsm", "DemoMine.vsm", "RealMine.vsm"])
def test_predictive_flows(fname):
    v = read_vsm(EX / fname)
    rows = aligned_table(v)
    br, n, fixed, info = network_predictive(v, rows)
    res = solve(n, br, fixed, tol=1e-6)
    q = np.array([fl(r["Quantity"]) for r in rows])
    big = np.abs(q) > 1.0
    rel = np.abs(res.Q[big] - q[big]) / np.abs(q[big])
    assert rel.max() < 1e-3, (fname, float(rel.max()), dict(info))
