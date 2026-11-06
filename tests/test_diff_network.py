"""Pruebas diferenciales de red (D-NET-01): nuestro solucionador vs caudales guardados por VentSim.

Las entradas (R, presión estática del ventilador, bloqueos, caudales fijos) se toman del archivo;
la salida comparada es el caudal por galería que NUESTRO solucionador calcula frente a `Quantity`.
Tolerancia: error relativo < 1e-3 en galerías con |Q| > 1 m³/s. Justificación: VentSim guarda
Quantity con ~7 cifras significativas y converge con tolerancia propia (no documentada); 1e-3 es
holgado frente al ruido observado (< 2e-5) pero lo bastante estricto para detectar errores físicos.
"""
from pathlib import Path

import numpy as np
import pytest

from nvs.network import solve
from nvs.vsmnet import fl, load_rows, network_from_rows

EX = Path(r"C:\Program Files\Ventsim DESIGN 6\examples")
pytestmark = pytest.mark.skipif(not EX.exists(), reason="instalación de referencia ausente")

# id de prueba -> (archivo, versión que guardó el archivo)
CASES = {
    "D-NET-01a": "Tutorial1.vsm",   # 6.0.4.6
    "D-NET-01b": "Tutorial2.vsm",   # 6.0.1.0
    "D-NET-01c": "DemoMine.vsm",    # 6.0.1.0
}


@pytest.mark.parametrize("case,fname", CASES.items())
def test_flows_match_ventsim(case, fname):
    rows = load_rows(str(EX / fname))
    branches, n, fixed = network_from_rows(rows)
    res = solve(n, branches, fixed, tol=1e-6)  # residuo nodal < 1e-6 m³/s (1e-8 se estanca por redondeo)
    assert res.converged
    q_ref = np.array([fl(r["Quantity"]) for r in rows])
    big = np.abs(q_ref) > 1.0
    rel = np.abs(res.Q[big] - q_ref[big]) / np.abs(q_ref[big])
    assert rel.max() < 1e-3, f"{case}: max rel err {rel.max():.2e}"
    # galerías bloqueadas: Q exactamente 0
    closed = np.array([b.closed for b in branches])
    assert np.all(res.Q[closed] == 0.0)
