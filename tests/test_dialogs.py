"""Diálogos de edición del proyecto nativo y acciones de la ventana principal (plataforma offscreen)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from nvs.gui.dialogs import AirwayDialog, FanDialog  # noqa: E402
from nvs.gui.main_window import MainWindow  # noqa: E402
from nvs.project import demo_native, new_native  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_airway_dialog_creates_airway(app):
    d = AirwayDialog(None, None, (10.0, 20.0, 30.0), "7")
    d.c2[0].setValue(110.0)       # fin = (110, 20, 30)
    d.w.setValue(5.0)
    d.h.setValue(4.0)
    d.k.setValue(0.012)
    d.le.setValue(25.0)
    d._ok()
    a = d.result_airway
    assert a is not None and a.uid == "7"
    assert a.length == pytest.approx(100.0)
    assert a.area == pytest.approx(20.0) and a.perimeter == pytest.approx(18.0)
    assert a.k == 0.012 and a.le == 25.0 and a.fixed_q is None


def test_airway_dialog_rejects_zero_length(app):
    d = AirwayDialog(None, None, (0, 0, 0), "1")
    for s in d.c2:
        s.setValue(0.0)
    d._ok()
    assert d.result_airway is None


def test_fan_dialog_validates_curve(app):
    a = demo_native().airways[-1]
    d = FanDialog(None, a)
    d._ok()
    assert d.points == [(40.0, 1800.0), (80.0, 1500.0), (120.0, 1000.0), (160.0, 450.0), (200.0, 0.0)]
    d2 = FanDialog(None, a)
    d2.txt.setPlainText("10, 100\n20, 500")     # presión creciente: inestable → rechazada
    d2._ok()
    assert d2.points is None and "no creciente" in d2.err.text()
    d3 = FanDialog(None, a)
    d3.txt.setPlainText("10, 500\n10, 400")     # Q no creciente
    d3._ok()
    assert d3.points is None and d3.err.text()


def test_main_window_native_flow(app):
    w = MainWindow()
    w.show()
    w.load_demo()
    assert w.prj.kind == "nativo" and len(w.prj.airways) == 7
    w.view.set_selected(6)
    w.on_view_selected(6)
    assert w.act_edit.isEnabled() and w.act_fan.isEnabled()
    w.solve_sync()
    assert w.prj.solved and all(a.calc_Q is not None for a in w.prj.airways)
    qs = [a.calc_Q for a in w.prj.airways]
    # editar invalida resultados
    w.prj.airways[1].closed = True
    w._invalidate()
    assert not w.prj.solved and all(a.calc_Q is None for a in w.prj.airways)
    w.solve_sync()
    assert w.prj.airways[1].calc_Q == 0.0 and w.prj.airways[0].calc_Q == 0.0   # cerrada la principal: no circula nada
    assert qs[0] > 1
    # nuevo proyecto vacío
    w.new_native_project()
    assert w.prj.airways == [] and not w.act_edit.isEnabled()
    assert new_native().airways == []
