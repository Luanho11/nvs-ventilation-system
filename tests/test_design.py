"""Pruebas del diseño: escala de color, panel de color, magnitudes, etiquetas, vistas y coordenadas (offscreen)."""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QLineEdit, QWidget  # noqa: E402

from nvs.gui.colorscale import ColorScale, default_scales  # noqa: E402
from nvs.gui.exponer_panel import PanelExponer  # noqa: E402
from nvs.gui.main_window import MainWindow, auto_thresholds  # noqa: E402
from nvs.project import demo_native  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    from nvs.gui.theme import apply_theme
    apply_theme(a)
    return a


# ---------------------------------------------------------------- escala de color
def test_banded_and_continuous_colors():
    sc = ColorScale("t", "u", [0.0, 10.0, 20.0], ["#000000", "#ff0000", "#00ff00", "#0000ff", "#ffffff"], banded=True)
    rgb = sc.rgb(np.array([-5, 0, 9.99, 10, 20, 25, np.nan]))
    assert rgb[0].tolist() == [0, 0, 0]                  # < t0
    assert rgb[1].tolist() == rgb[2].tolist() == [255, 0, 0]
    assert rgb[3].tolist() == [0, 255, 0]
    assert rgb[4].tolist() == [0, 0, 255]                # el último umbral conserva su color
    assert rgb[5].tolist() == [255, 255, 255]            # > último umbral
    assert rgb[6].tolist() == [125, 135, 148]            # sin dato
    sc.banded = False
    mid = sc.rgb(np.array([5.0, -5.0, 25.0]))
    assert mid[0].tolist() in ([128, 128, 0], [127, 128, 0])       # entre rojo (0) y verde (10)
    assert mid[1].tolist() == [0, 0, 0] and mid[2].tolist() == [255, 255, 255]


def test_default_scale_matches_exponer_reference():
    sc = default_scales()["Q"]
    assert sc.thresholds == [0.0, 10.0, 25.0, 50.0, 100.0, 250.0] and len(sc.colors) == 8 and not sc.banded
    assert [t for _c, t in sc.legend()] == ["> 250.0", "250.0", "100.0", "50.0", "25.0", "10.0", "0.0", "< 0.0"]


def test_threshold_edit_keeps_order_and_reset():
    sc = default_scales()["Q"]
    sc.set_threshold(0, 400.0)
    assert sc.thresholds == sorted(sc.thresholds) and sc.thresholds[-1] == 400.0
    sc.reset()
    assert sc.thresholds[0] == 0.0 and sc.thresholds[-1] == 250.0


def test_auto_thresholds_increasing():
    rng = np.random.default_rng(1)
    th = auto_thresholds(rng.gamma(2.0, 20.0, 500))
    assert len(th) == 6 and all(b > a for a, b in zip(th, th[1:]))
    assert auto_thresholds(np.zeros(5)) is None


# ---------------------------------------------------------------- panel Exponer
def test_exponer_edits_scale(app):
    host = QWidget()
    host.resize(400, 600)
    p = PanelExponer(host)
    sc = default_scales()["Q"]
    p.set_scale(sc)
    host.show()
    got = []
    p.changed.connect(lambda: got.append(1))
    edits = p.findChildren(QLineEdit)
    assert len(edits) == 6 and [e.text() for e in edits] == ["250.0", "100.0", "50.0", "25.0", "10.0", "0.0"]
    edits[0].setText("300")                                   # umbral más alto
    edits[0].editingFinished.emit()
    QTest.qWait(120)                                          # los avisos de cambio se agrupan cada 40 ms
    assert sc.thresholds[-1] == 300.0 and got
    c0 = list(sc.colors)
    p._invertir()
    assert sc.colors == c0[::-1]
    p._restaurar()
    assert sc.thresholds[-1] == 250.0
    assert sc.colors == c0


def test_exponer_range_slider_rescales_thresholds(app):
    host = QWidget()
    host.resize(400, 600)
    p = PanelExponer(host)
    sc = default_scales()["Q"]
    p.set_scale(sc)
    p._rango(0.5, 0.0)                                        # máximo 10^2 = 100, mínimo 0
    assert sc.thresholds[-1] == pytest.approx(100.0) and sc.thresholds[0] == 0.0
    assert sc.thresholds == sorted(sc.thresholds)


# ---------------------------------------------------------------- ventana
@pytest.fixture
def win(app):
    w = MainWindow()
    w.show()
    w.load_demo()
    w.solve_sync()
    app.processEvents()
    return w


def test_magnitude_and_source_drive_viewport(win):
    win.cb_mag.setCurrentIndex(0)
    win.cb_src.setCurrentIndex(1)                                   # motor
    q = win.view.values.copy()
    assert np.isfinite(q).all() and q.max() > 10
    win.cb_mag.setCurrentIndex(1)                                   # velocidad
    v = win.view.values
    areas = np.array([a.area for a in win.prj.airways])
    assert np.allclose(v, q / areas)
    assert win.view.scale.unit == "m/s" and win.lb_unit.text() == "m/s"
    win.cb_mag.setCurrentIndex(2)                                   # pérdida de presión
    assert win.view.scale.unit == "Pa"
    win.cb_mag.setCurrentIndex(3)                                   # diferencia: sin archivo → sin datos
    assert win.view.values is None
    assert not win.cb_src.isEnabled()


def test_file_source_without_data_says_so(win):
    win.cb_mag.setCurrentIndex(0)
    win.cb_src.setCurrentIndex(0)                                   # archivo: el proyecto nativo no tiene
    assert win.view.values is None and "sin datos" in win.sin_datos


def test_labels_modes(win):
    win.cb_mag.setCurrentIndex(0)
    win.cb_src.setCurrentIndex(1)
    win.cb_lab.setCurrentIndex(1)                                   # nombre
    assert win.view.label_texts[0] == "Pozo de entrada"
    win.cb_lab.setCurrentIndex(2)                                   # nº
    assert win.view.label_texts[:3] == ["1", "2", "3"]
    win.cb_lab.setCurrentIndex(4)                                   # ninguna
    assert set(win.view.label_texts) == {""}
    win.cb_lab.setCurrentIndex(0)
    assert all(t for t in win.view.label_texts)


def test_toggles_and_palette_visibility(win):
    assert win.exponer.isVisible()
    win.act_palette.setChecked(False)
    assert not win.exponer.isVisible()
    win.act_palette.setChecked(True)
    assert win.exponer.isVisible()
    for act, attr in ((win.act_labels, "show_labels"), (win.act_arrows, "show_arrows"), (win.act_grid, "show_grid"),
                      (win.act_tubes, "tubes"), (win.act_refs, "show_referencias"), (win.act_pan, "pan_activo")):
        act.setChecked(False)
        assert getattr(win.view, attr) is False
        act.setChecked(True)
        assert getattr(win.view, attr) is True


def test_standard_views_and_cursor_coordinates(win, app):
    v = win.view
    v.view_top()
    QTest.qWait(500)
    assert np.degrees(v.pitch) == pytest.approx(89, abs=0.5)
    v.view_front()
    QTest.qWait(500)
    assert np.degrees(v.pitch) == pytest.approx(0, abs=0.5)
    v.view_top()
    QTest.qWait(500)
    # el punto del objetivo se proyecta en el centro y su coordenada inversa coincide con el objetivo
    pos = v._cursor_world(v.width() / 2, v.height() / 2)
    assert pos is not None
    assert pos[0] == pytest.approx(v.target[0], abs=1e-6) and pos[1] == pytest.approx(v.target[1], abs=1e-6)
    got = []
    v.cursor_moved.connect(got.append)
    ev = QMouseEvent(QEvent.MouseMove, QPointF(v.rect().center()), Qt.NoButton, Qt.NoButton, Qt.NoModifier)
    QApplication.sendEvent(v, ev)
    assert got and got[-1] is not None
    win.on_cursor((1317.5, 1459.8, 84.0))
    QTest.qWait(120)                                   # la actualización de la barra de estado está limitada en frecuencia
    assert "1 317.5 E" in win.seg_coord.text() and "1 459.8 N" in win.seg_coord.text()


def test_status_segments_reflect_state(win):
    assert "convergió" in win.seg_state.text()
    assert "Proyecto nativo" in win.seg_model.text()
    assert win.seg_count.text() == f"Conductos de aire {len(demo_native().airways)}"


def test_exponer_range_drag_updates_in_place_and_batches_changes(app):
    """Regresión: arrastrar el medidor reconstruía los campos en cada evento (alertas sin fin con un campo enfocado)."""
    host = QWidget()
    host.resize(400, 600)
    p = PanelExponer(host)
    p.set_scale(default_scales()["Q"])
    host.show()
    campos_antes = p.findChildren(QLineEdit)
    campos_antes[2].setFocus()
    avisos = []
    p.changed.connect(lambda: avisos.append(1))
    QTest.mousePress(p.rango, Qt.LeftButton, Qt.NoModifier, QPoint(11, 20))
    for k in range(1, 40):
        QTest.mouseMove(p.rango, QPoint(11, 20 + k * 2))
    QTest.mouseRelease(p.rango, Qt.LeftButton, Qt.NoModifier, QPoint(11, 98))
    QTest.qWait(120)
    assert p.findChildren(QLineEdit) == campos_antes                      # los mismos widgets: no se destruyen ni se crean
    assert 1 <= len(avisos) <= 6                                          # ~40 eventos de ratón → pocos avisos
    p.set_scale(p.scale)
    assert p.findChildren(QLineEdit) == campos_antes


def test_error_filter_logs_every_error_but_alerts_once(tmp_path, app):
    from nvs.errores import FiltroErrores
    filtro = FiltroErrores(tmp_path / "errores.log")
    avisos = []
    filtro._avisar_una_vez = lambda valor: avisos.append(str(valor))
    for i in range(50):
        try:
            raise ValueError(f"fallo {i}")
        except ValueError as e:
            filtro(type(e), e, e.__traceback__)
    assert filtro.cantidad == 50 and len(avisos) == 1
    assert (tmp_path / "errores.log").read_text(encoding="utf-8").count("ValueError") >= 50


def test_starts_empty_like_ventsim_and_close_returns_to_it(app):
    from nvs.gui.main_window import MainWindow
    from nvs.project import demo_native
    w = MainWindow()
    w.show()
    assert w.prj is None and w.seg_count.text() == "Conductos de aire 0" and w.exponer.isHidden()
    assert w.seg_coord.text().startswith("Coordenadas 500.0 E")
    w.set_project(demo_native())
    assert w.prj is not None and len(w.view.p1) > 0
    w.menu_actions["Archivo/Cerrar"].trigger()
    assert w.prj is None and len(w.view.p1) == 0 and w.seg_count.text() == "Conductos de aire 0"


def test_value_filters_quick_views_and_zoom_out(app):
    from nvs.gui.main_window import MainWindow
    from nvs.project import demo_native
    w = MainWindow()
    w.show()
    w.set_project(demo_native())
    w.solve_sync()
    todos = int(w.view.visible.sum())
    w.menu_actions["Ver/Ocultar Flujo Cero"].trigger()
    assert w.ocultar_flujo_cero and int(w.view.visible.sum()) <= todos
    w.menu_actions["Ver/Ocultar Flujo Cero"].trigger()
    assert int(w.view.visible.sum()) == todos
    w.exponer.casilla.setChecked(True)                                  # ocultar datos por debajo del marcador azul
    assert w.ocultar_bajo
    w.menu_actions["Ver/Mostrar todas las capas"].trigger()
    assert not w.ocultar_bajo and int(w.view.visible.sum()) == todos
    v = w.view
    d0 = v.dist
    v.guardar_vista_rapida()
    v.alejar()
    assert v.dist == d0 * 2
    v.vista_rapida(1)
    assert v.dist == d0
    v.borrar_vistas_rapidas()
    assert v.vistas_rapidas == []
