"""Pruebas de consistencia del oráculo (archivos de ejemplo de la instalación de referencia).

Verifican que nuestra comprensión del formato es correcta antes de usar los resultados
guardados como valores de referencia. Se omiten si la instalación no está presente.
"""
import collections
from pathlib import Path

import pytest

from nvs.vsmio import aligned_table, read_vsm

EX = Path(r"C:\Program Files\Ventsim DESIGN 6\examples")
pytestmark = pytest.mark.skipif(not EX.exists(), reason="instalación de referencia ausente")


def f(x: str) -> float:
    try:
        return float(x)
    except ValueError:
        return 0.0


@pytest.fixture(scope="module", params=["DemoMine", "Tutorial2", "RealMine"])
def rows(request):
    return aligned_table(read_vsm(EX / f"{request.param}.vsm"))


def test_unique_numbers_and_guid_alignment(rows):
    assert rows
    assert all(len(r["GUID"]) == 36 for r in rows)
    assert [r["Unique No"] for r in rows[:3]] == ["1", "2", "3"]


def test_pressure_equals_R_Q2_for_open_airways(rows):
    ok = tot = 0
    for r in rows:
        R, Q, dp = f(r["Resistance"]), f(r["Quantity"]), f(r["Pressure Branch"])
        if R >= 1000 or abs(Q) < 1:  # cerradas / flujo despreciable
            continue
        tot += 1
        ok += abs(abs(dp) - R * Q * Q) <= 0.02 * max(1.0, R * Q * Q)
    assert tot > 20 and ok / tot > 0.9, (ok, tot)


def test_flow_continuity_at_nodes(rows):
    node = collections.defaultdict(list)
    k = lambda r, s: tuple(round(f(r[c]), 2) for c in (f"X{s}", f"Y{s}", f"Z{s}"))  # noqa: E731
    for r in rows:
        node[k(r, 1)].append(-f(r["Quantity"]))
        node[k(r, 2)].append(+f(r["Quantity"]))
    resid = sorted(abs(sum(v)) / (sum(abs(x) for x in v) + 1e-9) for v in node.values() if len(v) > 1)
    assert resid[len(resid) // 2] < 1e-3
