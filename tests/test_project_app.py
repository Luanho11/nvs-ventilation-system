"""Pruebas del núcleo de la aplicación: proyecto, procedencia, CSV, proyecto nativo y autoprueba de la GUI."""
import csv
import os
from pathlib import Path

import pytest

from nvs.export import COLUMNS, export_csv
from nvs.project import (comparison_stats, demo_native, load_native, load_vsm, make_rect_airway, new_native,
                                 save_native, solve_project)

EX = Path(r"C:\Program Files\Ventsim DESIGN 6\examples")
needs_ex = pytest.mark.skipif(not EX.exists(), reason="instalación de referencia ausente")


@needs_ex
def test_vsm_provenance_and_csv(tmp_path):
    p = load_vsm(EX / "Tutorial2.vsm")
    assert p.kind == "vsm" and len(p.airways) == 184
    # antes de calcular no hay valores del motor: no se atribuye nada al motor
    assert all(a.calc_Q is None for a in p.airways)
    export_csv(p, tmp_path / "a.csv")
    rows = list(csv.reader(open(tmp_path / "a.csv", encoding="utf-8-sig"), delimiter=";"))
    hdr = rows[2]
    assert hdr == COLUMNS
    qm = hdr.index("Q_motor_m3s")
    assert all(r[qm] == "" for r in rows[3:])
    info = solve_project(p)
    assert info["converged"]
    st = comparison_stats(p)
    assert st["max"] < 1e-3
    export_csv(p, tmp_path / "b.csv")
    rows = list(csv.reader(open(tmp_path / "b.csv", encoding="utf-8-sig"), delimiter=";"))
    assert all(r[qm] != "" for r in rows[3:])
    assert any(r[hdr.index("Origen_R_motor")] == "motor" for r in rows[3:])
    # el nombre de las columnas distingue archivo y motor
    assert "Q_archivo_m3s" in hdr and "Q_motor_m3s" in hdr


def test_native_demo_solves_physically(tmp_path):
    p = demo_native()
    info = solve_project(p)
    assert info["converged"]
    q = {a.name: a.calc_Q for a in p.airways}
    # el caudal del pozo = el de la galería principal = el de la chimenea (conservación)
    assert q["Pozo de entrada"] == pytest.approx(q["Galería principal"], rel=1e-6)
    assert q["Pozo de entrada"] == pytest.approx(q["Chimenea de retorno (ventilador)"], rel=1e-6)
    # reparto en paralelo: Q_A + Q_B = Q_principal, y misma pérdida de presión en ambos caminos
    assert q["Ramal A-1"] + q["Ramal B-1"] == pytest.approx(q["Galería principal"], rel=1e-6)
    a = {x.name: x for x in p.airways}
    dpA = abs(a["Ramal A-1"].calc_dp) + abs(a["Ramal A-2"].calc_dp)
    dpB = abs(a["Ramal B-1"].calc_dp) + abs(a["Ramal B-2"].calc_dp)
    assert dpA == pytest.approx(dpB, rel=1e-6)
    # el ventilador trabaja sobre su curva: presión de la curva en Q = pérdidas totales de la red
    fan = a["Chimenea de retorno (ventilador)"]
    from nvs.fan import FanCurve
    qs, ps = zip(*fan.fan_curve)
    s = FanCurve(list(qs), list(ps)).static(fan.calc_Q)
    total = sum(abs(x.calc_dp) for n, x in a.items() if n in ("Pozo de entrada", "Galería principal", "Ramal A-1", "Ramal A-2",
                                                              "Chimenea de retorno (ventilador)"))
    assert s == pytest.approx(total, rel=1e-6)
    # persistencia nativa
    save_native(p, tmp_path / "n.json")
    q2 = load_native(tmp_path / "n.json")
    solve_project(q2)
    assert [round(x.calc_Q, 9) for x in q2.airways] == [round(x.calc_Q, 9) for x in p.airways]


def test_native_add_and_closed():
    p = new_native()
    p.airways.append(make_rect_airway("1", "A", (0, 0, 0), (100, 0, 0), 4, 4, 0.01))
    p.airways.append(make_rect_airway("2", "B", (100, 0, 0), (200, 0, 0), 4, 4, 0.01))
    p.airways[0].fixed_q = 30.0
    solve_project(p)
    assert p.airways[1].calc_Q == pytest.approx(30.0)
    p.airways[1].closed = True
    solve_project(p)
    assert p.airways[1].calc_Q == 0.0


@needs_ex
def test_gui_selftest_runs(tmp_path):
    """La ventana se construye, carga un proyecto, calcula, renderiza y exporta (plataforma offscreen)."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from nvs.app import _selftest
    assert _selftest(tmp_path, EX / "Tutorial1.vsm") == 0
    assert (tmp_path / "vista3d.png").stat().st_size > 5000
    assert (tmp_path / "resultados.csv").exists()
