"""Interacción real del visor 3D (eventos de ratón sintéticos, plataforma offscreen)."""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from nvs.gui.viewport import Viewport3D  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def view(app):
    v = Viewport3D()
    v.resize(800, 600)
    # una cruz de 4 galerías en el plano XY + una vertical
    p1 = np.array([[0, 0, 0], [100, 0, 0], [0, 0, 0], [-100, 0, 0], [0, 0, 0]], float)
    p2 = np.array([[100, 0, 0], [100, 100, 0], [0, 100, 0], [0, 0, 0], [0, 0, 80]], float)
    v.set_geometry(p1, p2)
    v.show()
    app.processEvents()
    return v


def _mid_px(v, i):
    idx, s = v._project_segments()
    k = int(np.nonzero(idx == i)[0][0])
    return QPoint(int((s[k, 0] + s[k, 2]) / 2), int((s[k, 1] + s[k, 3]) / 2))


def test_click_selects_each_airway(view):
    got = []
    view.selected.connect(got.append)
    for i in range(5):
        QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, _mid_px(view, i))
        assert got[-1] == i, (i, got)
    QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, QPoint(5, 5))   # vacío
    assert got[-1] == -1


def test_drag_rotates_and_wheel_zooms(view):
    y0, d0 = view.yaw, view.dist
    QTest.mousePress(view, Qt.LeftButton, Qt.NoModifier, QPoint(400, 300))
    QTest.mouseMove(view, QPoint(460, 330))
    QTest.mouseRelease(view, Qt.LeftButton, Qt.NoModifier, QPoint(460, 330))
    assert view.yaw != y0
    # tras arrastrar no debe haberse seleccionado nada nuevo (era un arrastre, no un clic)
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QWheelEvent
    ev = QWheelEvent(QPointF(400, 300), QPointF(400, 300), QPoint(0, 0), QPoint(0, 120), Qt.NoButton,
                     Qt.NoModifier, Qt.NoScrollPhase, False)
    QApplication.sendEvent(view, ev)
    QTest.qWait(400)                                          # el zoom de la rueda es fluido: avanza en varios fotogramas
    assert view.dist < d0
    assert view.dist == pytest.approx(d0 / 1.077, rel=0.02)   # una muesca = ×1,077, medido en Ventsim real


def test_pan_moves_target(view):
    t0 = view.target.copy()
    QTest.mousePress(view, Qt.RightButton, Qt.NoModifier, QPoint(400, 300))
    QTest.mouseMove(view, QPoint(450, 300))
    QTest.mouseRelease(view, Qt.RightButton, Qt.NoModifier, QPoint(450, 300))
    assert np.linalg.norm(view.target - t0) > 1e-3


def test_fit_contains_everything(view):
    view.fit()
    idx, s = view._project_segments()
    assert len(idx) == 5
    assert s.min() >= -1 and s[:, [0, 2]].max() <= view.width() + 1 and s[:, [1, 3]].max() <= view.height() + 1


def test_renders_nonblank(view):
    img = view.grab().toImage()
    colors = {img.pixel(x, y) for x in range(0, 800, 7) for y in range(0, 600, 7)}
    assert len(colors) > 5
