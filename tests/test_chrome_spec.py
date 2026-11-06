"""La interfaz (menús, barras, raíl) sale de docs/evidence/ui_spec.json: nombres y orden idénticos; lo no implementado
queda deshabilitado con tooltip «pendiente»; nada inventado dentro de los menús de la referencia."""
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QComboBox  # noqa: E402

from nvs.gui import chrome  # noqa: E402
from nvs.gui.main_window import MainWindow  # noqa: E402

EVIDENCE = Path(__file__).resolve().parents[1] / "docs" / "evidence" / "ui_spec.json"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app):
    w = MainWindow()
    w.show()
    return w


def test_packaged_spec_equals_evidence():
    """La copia empaquetada con la app no diverge de la evidencia generada."""
    packaged = Path(chrome.__file__).resolve().parents[1] / "data" / "ui_spec.json"
    assert json.loads(packaged.read_text("utf-8")) == json.loads(EVIDENCE.read_text("utf-8"))


def test_top_menus_follow_spec_order(win):
    spec_names = [m["name"].strip() for m in win.spec["menus"] if m["name"].strip()]
    got = [a.text() for a in win.menuBar().actions()]
    assert got[:len(spec_names)] == spec_names
    assert got[len(spec_names):] == ["NVS"]            # único menú propio, aparte y rotulado


def test_every_spec_leaf_exists_and_unbound_ones_are_pending(win):
    n_leaf = 0

    def walk(items, path):
        nonlocal n_leaf
        for it in items:
            if it == "-":
                continue
            key = f"{path}/{it['name'].strip()}"
            assert key in win.menu_actions, key
            if not it["items"] and key != "Archivo/Cargar demostración/Otros ejemplos":
                n_leaf += 1
                act = win.menu_actions[key]
                if not act.isEnabled():
                    assert "Pendiente" in act.toolTip()
            walk(it["items"], key)

    for m in win.spec["menus"]:
        if m["name"].strip():
            walk(m["items"], m["name"].strip())
    ok, pending = win.menu_stats
    assert ok + pending == n_leaf and ok >= 10 and pending > ok


def test_bound_menu_items_work(win, app):
    assert win.menu_actions["Correr/Escritura de la estática"].isEnabled()
    assert win.menu_actions["Archivo/Cargar demostración/Mina de metal"].isEnabled()
    assert not win.menu_actions["Archivo/Importar"].isEnabled()
    win.menu_actions["Ver/Barras de herramientas"].setChecked(False)
    assert not win.bar1.isVisible() and not win.rail.isVisible()
    win.menu_actions["Ver/Barras de herramientas"].setChecked(True)
    assert win.bar1.isVisible() and win.bar2.isVisible() and win.rail.isVisible()


def test_bars_follow_spec(win):
    """Botones y separadores de barra 1 y raíl: mismo número y orden que la evidencia."""
    sp = win.spec
    assert len(win.bar1_actions) == sum(r["role"] != "separador" for r in sp["barra1"])
    assert [win.rail_actions[i].text() for i in sorted(win.rail_actions)] == [r["name"].strip() for r in sp["raiL_izquierdo"]]
    # lo no implementado está deshabilitado y lo dice
    bound = {0, 2, 3, 4, 5, 6, 7, 8}                  # Sólidos, Todos los aptos, Cuadrícula, Nodos, Flechas, Referencias, Pistas, Visibilidad
    for i, a in win.rail_actions.items():
        assert a.isEnabled() or "Pendiente" in a.toolTip() or i in bound
        assert (i in bound) == (a.isEnabled() or "Pendiente" not in a.toolTip())
    assert win.rail_actions[0].isCheckable() and win.rail_actions[3].isCheckable()   # Sólidos y Cuadrícula (casillas)


def test_bar2_combos_use_observed_lists(win):
    lists = [list(v) for v in win.spec["combos"].values()]
    assert [win.cb_cat.itemText(i) for i in range(win.cb_cat.count())
            if win.cb_cat.itemText(i)] == [t for t in lists[0] if not t.startswith("-----")]
    assert win.cb_cat.currentText() == "Flujo de aire"
    assert win.cb_views.currentText() == "Por defecto"
    # solo «Cantidad» y «Velocidad» están disponibles: el resto aparece deshabilitado
    en = {win.cb_qty.itemText(i) for i in range(win.cb_qty.count()) if win.cb_qty.model().item(i).isEnabled()}
    assert en == {"Cantidad", "Velocidad"}


def test_quantity_combo_drives_magnitude(win):
    win.cb_qty.setCurrentIndex(win.cb_qty.findText("Velocidad"))
    win.cb_qty.activated.emit(win.cb_qty.currentIndex())
    assert win.cb_mag.currentData() == "V" and win.lb_unit.text() == "m/s"
    win.cb_mag.setCurrentIndex(2)                     # magnitud propia (pérdida de presión) → el combo queda en blanco
    assert win.cb_qty.currentIndex() == -1
    win.cb_mag.setCurrentIndex(0)
    assert win.cb_qty.currentText() == "Cantidad"
    assert isinstance(win.cb_qty, QComboBox)


def test_docks_hidden_by_default_like_reference(win):
    assert not win.dock_props.isVisible() and not win.dock_table.isVisible()
    win.act_table.setChecked(True)
    assert win.dock_table.isVisible()
