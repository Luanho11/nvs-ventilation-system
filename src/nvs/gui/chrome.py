"""Menús, barras, raíl y barra de estado construidos a partir de `ui_spec.json` (evidencia MSAA de la app de referencia).

Nada de esto se escribe a mano: nombres, orden, separadores y casillas vienen de la especificación.  Lo que existe en
la referencia y NVS aún no implementa se muestra DESHABILITADO con el tooltip «pendiente» (CLAUDE.md, regla 3).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QComboBox, QLabel, QMenu, QSizePolicy, QToolBar, QWidget

from .icons import icon

PENDING_TIP = "Pendiente: existe en Ventsim DESIGN (observado) y todavía no está implementado en NVS."


def load_spec() -> dict:
    here = Path(__file__).resolve()
    for p in (here.parents[1] / "data" / "ui_spec.json", here.parents[3] / "docs" / "evidence" / "ui_spec.json"):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError("ui_spec.json no encontrado (ver tools/build_ui_spec.py)")


def _mark_pending(act: QAction):
    act.setEnabled(False)
    act.setToolTip(PENDING_TIP)
    act.setStatusTip(PENDING_TIP)


# ---------------------------------------------------------------------------------------------- menús
def build_menus(owner, menubar, spec: dict, handlers: dict[str, Callable], fillers: dict[str, Callable] | None = None):
    """Crea los menús de la especificación.

    handlers: «Menú/Submenú/Elemento» → función (los elementos marcables reciben el booleano).
    fillers:  «Menú/Elemento» → función(QMenu) para submenús dinámicos (p. ej. la lista de ejemplos).
    Devuelve (acciones por ruta, nº implementados, nº pendientes).
    """
    fillers = fillers or {}
    reg: dict[str, QAction] = {}
    count = {"ok": 0, "pending": 0}

    def fill(menu: QMenu, items: list, path: str):
        menu.setToolTipsVisible(True)
        for it in items:
            if it == "-":
                menu.addSeparator()
                continue
            name = it["name"].strip()
            key = f"{path}/{name}"
            if it["items"] or key in fillers:
                sub = menu.addMenu(name)
                reg[key] = sub.menuAction()
                if key in fillers:
                    fillers[key](sub)
                fill(sub, it["items"], key)
                continue
            act = QAction(name, owner)
            reg[key] = act
            h = handlers.get(key)
            if it.get("checkable"):
                act.setCheckable(True)
            if h is None:
                _mark_pending(act)
                count["pending"] += 1
            else:
                if it.get("checkable"):
                    act.toggled.connect(h)
                else:
                    act.triggered.connect(lambda _c=False, f=h: f())
                count["ok"] += 1
            menu.addAction(act)

    for m in spec["menus"]:
        name = m["name"].strip()
        if not name:                       # los volcados traen 4 menús sin nombre al final: ruido, no evidencia
            continue
        menu = menubar.addMenu(name)
        reg[name] = menu.menuAction()
        fill(menu, m["items"], name)
    return reg, count["ok"], count["pending"]


# ---------------------------------------------------------------------------------------------- barras de botones
def _button(owner, row: dict, act: QAction | None, ico: str | None, size: int) -> QAction:
    name = row["name"].strip()
    if act is None:
        act = QAction(name or "(sin nombre observado)", owner)
        if row["role"] == "casilla":
            act.setCheckable(True)
        _mark_pending(act)
        act.setToolTip((name or "Botón sin nombre observado") + " — " + PENDING_TIP)
    if ico:
        act.setIcon(ico if isinstance(ico, QIcon) else icon(ico, size))
    return act


def build_button_strip(owner, tb: QToolBar, rows: list[dict], actions: dict[int, QAction], icons: dict[int, str],
                       size: int = 20) -> dict[int, QAction]:
    """Añade a `tb` una acción por fila de la especificación (en su orden).  `actions`/`icons` se indexan por fila."""
    out: dict[int, QAction] = {}
    for i, r in enumerate(rows):
        if r["role"] == "separador":
            tb.addSeparator()
            continue
        act = _button(owner, r, actions.get(i), icons.get(i), size)
        tb.addAction(act)
        out[i] = act
    return out


def fill_combo(cb: QComboBox, items: list[str], enabled: set[str] | None = None):
    """Rellena un combo con la lista observada; los elementos fuera de `enabled` quedan deshabilitados (pendientes)."""
    cb.clear()
    for t in items:
        if t.startswith("-----"):
            cb.insertSeparator(cb.count())
            continue
        cb.addItem(t)
        if enabled is not None and t not in enabled:
            it = cb.model().item(cb.count() - 1)
            it.setEnabled(False)
            it.setToolTip(PENDING_TIP)


def build_bar2(owner, tb: QToolBar, rows: list[dict], combo_lists: list[list[str]], enabled: list[set[str]],
               actions: dict[int, QAction], icons: dict[int, str], size: int = 20):
    """Barra 2 («qué se muestra»): botones, combos, textos y casillas ordenados por su posición observada (x) y con
    su ancho.  `combo_lists[k]`/`enabled[k]` describen el k-ésimo combo (de izquierda a derecha).
    Devuelve (acciones por fila, combos por fila, etiquetas por fila); «fila» = índice en `rows`."""
    acts: dict[int, QAction] = {}
    combos: dict[int, QComboBox] = {}
    labels: dict[int, QLabel] = {}
    ci = 0
    prev_end = None
    for i, r in sorted(enumerate(rows), key=lambda t: t[1]["rect"][0]):
        x, _y, w, _h = r["rect"]
        if prev_end is not None and x - prev_end > 60:           # hueco observado → separa el grupo derecho
            sp = QWidget()
            sp.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            tb.addWidget(sp)
        prev_end = x + w
        role = r["role"]
        if role == "separador":
            tb.addSeparator()
        elif role == "cuadro combinado":
            cb = QComboBox()
            if ci < len(combo_lists):
                fill_combo(cb, combo_lists[ci], enabled[ci] if ci < len(enabled) else set())
            ci += 1
            cb.setFixedWidth(max(w, 60))
            tb.addWidget(cb)
            combos[i] = cb
        elif role == "texto":
            lab = QLabel(r["name"].strip())
            lab.setObjectName("unit" if "/" in r["name"] else "toolbarCaption")
            tb.addWidget(lab)
            labels[i] = lab
        else:
            act = _button(owner, r, actions.get(i), icons.get(i), size)
            tb.addAction(act)
            acts[i] = act
    return acts, combos, labels
