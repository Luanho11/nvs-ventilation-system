"""Escena visual del .vsm (superficies, notas, etapas, vistas) y su uso en la ventana: Blue_sky.vsm, ejemplo inicial."""
import os
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from nvs.escena import cargar_escena, resolver_campos  # noqa: E402
from nvs.gui.main_window import DEMOSTRACIONES, MainWindow  # noqa: E402
from nvs.project import load_vsm  # noqa: E402
from nvs.vsmio import read_vsm  # noqa: E402

EX = Path(r"C:\Program Files\Ventsim DESIGN 6\examples")
needs_ex = pytest.mark.skipif(not (EX / "Blue_sky.vsm").exists(), reason="instalación de referencia ausente")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@needs_ex
def test_blue_sky_scene_contents():
    e = cargar_escena(read_vsm(EX / "Blue_sky.vsm"))
    assert [m.nombre for m in e.mallas] == ["Pit Shell.dxf", "Tas Ore Zone.DXF"]
    assert e.mallas[0].vertices.shape == (7362, 3) and e.mallas[1].vertices.shape == (7296, 3)
    assert e.mallas[0].colores.std(axis=0).max() > 5            # la capa del pozo trae textura, no un color plano
    assert e.etapas == ["Initial Development", "Preliminary", "Pre Production", "Production"]
    assert len(e.vistas) == 16 and e.camara.nombre == "Default"
    assert len(e.notas) == 3 and e.notas[0].color == (0, 64, 128)
    assert e.notas[0].posicion is None and 0 < e.notas[0].fx < 1 and 0 < e.notas[0].fy < 1     # fija en pantalla
    assert e.notas[1].posicion == pytest.approx((1545.54, 1521.83, 127.38), abs=0.01)           # anclada al modelo


@needs_ex
def test_note_fields_use_file_values():
    p = load_vsm(EX / "Blue_sky.vsm")
    texto = resolver_campos(p.escena.notas[2].texto, p.airways, p.escena)
    assert "quantity 127.7 m³/s" in texto and "diameter 4.5 m" in texto
    assert "<" not in texto


@needs_ex
def test_note_costs_and_maximum_match_reference_screenshot():
    """Cifras de la captura de la referencia: coste anual de las dos chimeneas y velocidad máxima de la rampa."""
    p = load_vsm(EX / "Blue_sky.vsm")
    costes = resolver_campos(p.escena.notas[2].texto, p.airways, p.escena)
    assert "$195,605 /yr" in costes and "$166,323 /yr" in costes
    nota = p.escena.notas[1]
    assert len(nota.guids) == 127
    assert resolver_campos(nota.texto, p.airways, p.escena, nota.guids).endswith("3.3 m/s")


@needs_ex
def test_tracks_and_cost_settings_are_read():
    e = cargar_escena(read_vsm(EX / "Blue_sky.vsm"))
    assert (e.precio_kwh, e.eficiencia, e.moneda) == (0.1, 0.95, "$")
    assert [(t.nombre, t.color, len(t.guids)) for t in e.pistas] == [("Decline Path", (255, 0, 0), 131)]


@needs_ex
def test_stage_mask_filters_airways(app):
    w = MainWindow()
    w.show()
    w.set_project(load_vsm(EX / "Blue_sky.vsm"))
    produccion = sum(1 for a in w.prj.airways if a.etapas & 8)
    assert w.cb_stage.currentText() == "Production" and int(w.view.visible.sum()) == produccion
    assert w.seg_count.text() == "Conductos de aire 522(757)"        # cifra de la captura de Ventsim (sin galerías ficticias)
    w.cb_stage.setCurrentIndex(0)
    w._on_stage(0)
    assert int(w.view.visible.sum()) == sum(1 for a in w.prj.airways if a.etapas & 1)
    assert w.windowTitle().endswith("Blue_sky.vsm   Example Metal Mine with Problems")


@needs_ex
def test_saved_views_and_default_camera(app):
    w = MainWindow()
    w.show()
    w.set_project(load_vsm(EX / "Blue_sky.vsm"))
    assert w.cb_views.count() == 17 and w.cb_views.itemText(1) == "Initial Decline System"
    assert np.allclose(w.view.target, w.prj.escena.camara.objetivo)
    w.cb_views.setCurrentIndex(5)
    w._on_view_combo(5)
    assert np.allclose(w.view.target, w.prj.escena.vistas[4].objetivo)


def test_demonstration_menu_maps_to_example_files():
    assert set(DEMOSTRACIONES) == {"Mina de metal", "Mina de carbón", "Mina de carbón texturada", "Mina de diamante",
                                   "Demo de fuego", "Sólidos simples"}
    if EX.exists():
        assert all((EX / f).exists() for f in DEMOSTRACIONES.values())


@needs_ex
def test_saved_state_active_stage_and_air_type_mode():
    """STATE: columna 79 = etapa activa y columna 7 = dato de color (613 = tipo de aire), como se ve en Ventsim con CoalMine."""
    e = cargar_escena(read_vsm(EX / "CoalMine.vsm"))
    assert (e.etapa_activa, e.codigo_color) == (4, 613) and e.etapas[4].startswith("Year 5")
    assert [n for n, _c in e.tipos_aire][:4] == ["Not Set", "Intake Air", "Chilled Intake Air", "Return Air"]
    assert (e.cielo, e.color_rejilla) == ("#6495ed", "#404040")
    assert (e.rejilla.espaciado, e.rejilla.cx, e.rejilla.z) == (100.0, -45800.0, 1700.0)


@needs_ex
def test_air_type_colour_mode_and_visibility(app):
    w = MainWindow()
    w.show()
    w.set_project(load_vsm(EX / "CoalMine.vsm"))
    assert w.color_categorico and w.cb_cat.currentText() == "Identificadores" and w.cb_qty.currentText() == "Tipo de aire"
    assert w.seg_count.text() == "Conductos de aire 3403(5146)"      # cifra de la captura de Ventsim
    assert w.view.colores_directos is not None and w.exponer.pagina_cat.isVisibleTo(w.exponer)
    antes = int(w.view.visible.sum())
    w.exponer._casillas[1].setChecked(False)                          # ocultar «Intake Air»
    assert int(w.view.visible.sum()) < antes
