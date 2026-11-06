"""Ventana principal de NVS: menús, barras, raíl, visor 3D con el panel «Exponer», paneles y barra de estado."""
from __future__ import annotations

import html
import math
import os
import time
import traceback
from pathlib import Path

import numpy as np
from PySide6.QtCore import (QAbstractTableModel, QEvent, QModelIndex, QSize, QSortFilterProxyModel, Qt, QThread, QTimer,
                            Signal)
from PySide6.QtGui import QAction, QActionGroup, QBrush, QColor, QKeySequence
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDockWidget, QFileDialog, QHeaderView, QInputDialog,
                               QLabel, QMainWindow, QMenu, QMessageBox, QSizePolicy, QTableView, QTabWidget, QTextBrowser,
                               QToolBar, QToolButton, QTreeWidget, QTreeWidgetItem, QHBoxLayout, QVBoxLayout, QWidget)

from .. import __version__
from ..escena import resolver_campos
from ..export import export_csv
from ..project import (Project, comparison_stats, demo_native, load_native, load_vsm, new_native, save_native,
                       solve_project)
from ..recursos import icono_aplicacion, imagen
from . import chrome, theme
from .colorscale import ColorScale, default_scales
from .dialogs import AirwayDialog, FanDialog
from .exponer_panel import PanelExponer
from .icons import icon, icon_desplegable
from .viewport import create_viewport

EXAMPLES_DIR = Path(os.environ.get("NVS_EXAMPLES", r"C:\Program Files\Ventsim DESIGN 6\examples"))
DEMOSTRACIONES = {                    # Archivo › Cargar demostración (nombres observados; archivos asignados por su contenido)
    "Mina de metal": "Blue_sky.vsm", "Mina de carbón": "CoalMine.vsm", "Mina de carbón texturada": "CoalMine2.vsm",
    "Mina de diamante": "diamondmine.vsm", "Demo de fuego": "Fire.vsm", "Sólidos simples": "DevSolids.vsm",
}
ICONOS_BARRA1 = {0: "nuevo", 1: "abrir", 2: "copiar", 3: "pegar", 5: "ventanas", 6: "prismaticos", 7: "pelicula",
                 8: "ejecutar", 9: "lupa", 10: "mover"}
ICONOS_BARRA2 = {0: "exponer", 1: "paleta", 6: "enlace", 8: "texto", 9: "texto_relativo", 13: "estrella"}
ICONOS_RAIL = {0: "cubo_solido", 1: "cubo_malla", 2: "ajustar", 3: "tabla", 4: "nodo", 5: "flechas", 6: "referencias",
               7: "pistas", 8: "visibilidad"}
ICONOS_VISTA = ("vista_cuadro", "vista_malla", "vista_solida", "vista_lado", "vista_sombra", "vista_expandir")
C_FILE = QColor(theme.FILE_BLUE)      # azul: valor leído del archivo
C_ENGINE = QColor(theme.ENGINE_GREEN)  # verde: calculado por el motor propio

COLS = [  # (título, origen, función valor, formato)
    ("N", "", lambda a: a.uid, None),
    ("Nombre", "", lambda a: a.name, None),
    ("Longitud [m]", "", lambda a: a.length, "{:.2f}"),
    ("Área [m²]", "", lambda a: a.area, "{:.2f}"),
    ("R archivo [Ns²/m⁸]", "f", lambda a: a.saved_R, "{:.6g}"),
    ("R motor [Ns²/m⁸]", "m", lambda a: a.calc_R, "{:.6g}"),
    ("Origen R motor", "m", lambda a: a.r_origin, None),
    ("Q archivo [m³/s]", "f", lambda a: a.saved_Q, "{:.4f}"),
    ("Q motor [m³/s]", "m", lambda a: a.calc_Q, "{:.4f}"),
    ("ΔQ [m³/s]", "m", lambda a: None if a.saved_Q is None or a.calc_Q is None else a.calc_Q - a.saved_Q, "{:+.4f}"),
    ("ΔQ [%]", "m", lambda a: None if a.saved_Q is None or a.calc_Q is None or abs(a.saved_Q) < 0.01
     else 100 * (a.calc_Q - a.saved_Q) / abs(a.saved_Q), "{:+.3f}"),   # solo si |Q archivo| ≥ 0,01 m³/s
    ("Δp archivo [Pa]", "f", lambda a: a.saved_dp, "{:.2f}"),
    ("Δp motor [Pa]", "m", lambda a: None if a.calc_dp is None else abs(a.calc_dp), "{:.2f}"),
    ("Ventilador", "", lambda a: a.fan_type or ("nativo" if a.fan_curve else ""), None),
    ("Origen ventilador", "m", lambda a: a.fan_origin, None),
]

MAGS = [("Q", "Caudal"), ("V", "Velocidad del aire"), ("DP", "Pérdida de presión"), ("DIFF", "Diferencia motor − archivo")]
THICKNESS = [("Real", 1.0), ("Realzado ×1,5", 1.5), ("Grueso ×2", 2.0), ("Muy grueso ×3", 3.0), ("Máximo ×4,5", 4.5)]
LABEL_MODES = [("val", "Valor"), ("name", "Nombre"), ("uid", "Nº de galería"), ("both", "Valor · nombre"), ("none", "Ninguna")]


class ResultsModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.prj: Project | None = None

    def set_project(self, prj):
        self.beginResetModel()
        self.prj = prj
        self.endResetModel()

    def refresh(self):
        if self.prj and self.prj.airways:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.prj.airways) - 1, len(COLS) - 1))

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() or not self.prj else len(self.prj.airways)

    def columnCount(self, parent=QModelIndex()):
        return len(COLS)

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return COLS[section][0]
            if role == Qt.ForegroundRole and COLS[section][1]:
                return QBrush(C_FILE if COLS[section][1] == "f" else C_ENGINE)
            if role == Qt.ToolTipRole:
                return {"f": "Leído del archivo (resultado guardado por VentSim)", "m": "Calculado por el motor propio",
                        "": "Dato del proyecto"}[COLS[section][1]]
        elif role == Qt.DisplayRole:
            return str(section + 1)
        return None

    def data(self, index, role=Qt.DisplayRole):
        a = self.prj.airways[index.row()]
        _t, org, fn, fmt = COLS[index.column()]
        v = fn(a)
        if role == Qt.DisplayRole:
            if v is None:
                return ""
            return fmt.format(v) if fmt and isinstance(v, (int, float)) else str(v)
        if role == Qt.UserRole:      # clave de ordenación numérica
            if v is None or v == "":
                return float("-inf")
            try:
                return float(v)
            except (TypeError, ValueError):
                return str(v)
        if role == Qt.ForegroundRole and org:
            return QBrush(C_FILE if org == "f" else C_ENGINE)
        if role == Qt.BackgroundRole and a.saved_Q is not None and a.calc_Q is not None and index.column() in (9, 10):
            rel = abs(a.calc_Q - a.saved_Q) / max(abs(a.saved_Q), 1.0)
            if rel > 0.05:
                return QBrush(QColor("#fbd9d9"))
            if rel > 1e-3:
                return QBrush(QColor("#fdecc8"))
        if role == Qt.TextAlignmentRole and index.column() > 1:
            return int(Qt.AlignRight | Qt.AlignVCenter)
        return None


class Worker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *args):
        super().__init__()
        self.fn, self.args = fn, args

    def run(self):
        try:
            self.done.emit(self.fn(*self.args))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")


def _nice(x: float) -> float:
    """Redondea a 2 cifras significativas 'agradables' (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8)."""
    if x <= 0:
        return 0.0
    mag = 10 ** math.floor(math.log10(x))
    m = x / mag
    for c in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m <= c * 1.0001:
            return round(c * mag, 10)
    return round(10 * mag, 10)


def auto_thresholds(vals: np.ndarray, n: int = 6) -> list[float] | None:
    v = vals[np.isfinite(vals)]
    if len(v) == 0 or v.max() <= 0:
        return None
    pos = np.sort(v[v > 0]) if (v > 0).any() else v
    qs = np.quantile(pos, [0.12, 0.28, 0.45, 0.62, 0.78, 0.90, 0.97])[:n]
    th = [0.0]
    for q in qs[1:]:
        t = _nice(float(q))
        if t > th[-1]:
            th.append(t)
    while len(th) < n:
        th.append(_nice(th[-1] * 1.6 if th[-1] > 0 else float(pos.max()) / 8))
    return th[:n]


class MainWindow(QMainWindow):
    carga_terminada = Signal()         # terminó el intento de abrir un proyecto (con éxito o con error)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self._titulo(None))
        self.resize(1382, 777)
        self.setWindowIcon(icono_aplicacion())
        self.prj: Project | None = None
        self.worker: Worker | None = None
        self.scales: dict[str, ColorScale] = default_scales()
        self.etapa_actual = -1
        self.sin_datos = ""
        self.setAcceptDrops(True)
        self.setDockNestingEnabled(True)
        self._last_cursor_t = 0.0
        self._pending_cursor = None
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setSingleShot(True)
        self._cursor_timer.timeout.connect(self._flush_cursor)

        self.view_host = QWidget()
        lay = QVBoxLayout(self.view_host)
        lay.setContentsMargins(0, 0, 0, 0)
        self.view = create_viewport()
        lay.addWidget(self.view)
        self.view.selected.connect(self.on_view_selected)
        self.view.cursor_moved.connect(self.on_cursor)
        self.exponer = PanelExponer(self.view)
        self.view.overlays = [self.exponer]
        self.color_categorico = False
        self.ocultar_flujo_cero = False
        self.ocultar_bajo = False
        self.pestana = 0
        self.categorias: dict[int, tuple[list[str], list[str], np.ndarray | None]] = {}     # pestaña → (nombres, colores, índice por galería)
        self.cat_visibles: dict[int, list[bool]] = {}
        self.exponer.pestana.connect(self._on_pestana)
        self.exponer.ocultar_bajo.connect(self._toggle_ocultar_bajo)
        self.exponer.categorias.connect(self._on_categorias)
        self.exponer.changed.connect(self.update_colors)
        self.exponer.autoescala.connect(self.autoscale)
        self.exponer.transparencia.connect(self._on_transparencia)
        self.exponer.closed.connect(lambda: self.act_palette.setChecked(False))
        self.view.installEventFilter(self)
        self.setCentralWidget(self.view_host)

        self.props = QTreeWidget()
        self.props.setColumnCount(3)
        self.props.setHeaderLabels(["Propiedad", "Valor", "Origen"])
        self.props.setAlternatingRowColors(True)
        self.props.setIndentation(14)
        self.props.setColumnWidth(0, 190)
        self.props.setColumnWidth(1, 135)
        self.props.header().setStretchLastSection(True)
        self.summary = QTextBrowser()
        self.tabs = QTabWidget()
        self.tabs.addTab(self.props, "Propiedades")
        self.tabs.addTab(self.summary, "Resumen y validez")
        self.dock_props = QDockWidget("Galería seleccionada", self)
        self.dock_props.setWidget(self.tabs)
        self.dock_props.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_props)

        self.model = ResultsModel()
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(Qt.UserRole)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setDefaultSectionSize(22)
        self.table.verticalHeader().hide()
        self.table.selectionModel().currentRowChanged.connect(self.on_table_row)
        self.table.doubleClicked.connect(lambda _i: self.view.focus_selected())
        for i, w in enumerate([60, 170, 90, 80, 130, 130, 105, 120, 120, 95, 85, 110, 110, 95, 120]):
            self.table.setColumnWidth(i, w)
        self.dock_table = QDockWidget("Resultados por galería", self)
        self.dock_table.setWidget(self.table)
        self.dock_table.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_table)

        self._build_status_bar()
        self._build_actions_and_bars()
        self.dock_props.visibilityChanged.connect(lambda v: self.act_props.setChecked(self.dock_props.isVisible()))
        self.dock_table.visibilityChanged.connect(lambda v: self.act_table.setChecked(self.dock_table.isVisible()))
        self.exponer.set_scale(self.scales["Q"])
        self.dock_props.hide()      # la referencia no tiene paneles acoplados: se abren desde el menú «NVS»
        self.dock_table.hide()
        self.act_palette.setChecked(False)      # sin proyecto, como Ventsim al abrir: visor vacío con la rejilla y sin «Exponer»
        self.refresh_all()
        self.resizeDocks([self.dock_props], [360], Qt.Horizontal)
        self.resizeDocks([self.dock_table], [185], Qt.Vertical)

    @staticmethod
    def _titulo(prj: Project | None) -> str:
        if prj is None:
            return f"NVS {__version__}"
        return f"NVS {__version__}  - {prj.name}   {prj.descripcion}".rstrip()

    @staticmethod
    def _campo(text: str, minw: int = 0, negrita: bool = False, blanco: bool = False) -> QLabel:
        lab = QLabel(text)
        lab.setStyleSheet(f"QLabel{{border:1px solid #a0a0a0;padding:2px 6px;background:{'#ffffff' if blanco else '#f0f0f0'};"
                          f"font-weight:{'bold' if negrita else 'normal'};}}")
        lab.setMinimumWidth(minw)
        return lab

    def _build_status_bar(self):
        """Orden y textos observados: reproducción ×5 · Coordenadas · Estado · Compresible/NVP · Conductos de aire ... modos de vista."""
        self.status = QLabel("Listo")
        self.status.setContentsMargins(10, 0, 0, 0)
        self.status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)   # el mensaje cede espacio antes que los campos
        self.seg_coord = self._campo("Coordenadas 500.0 E   500.0 N   0 Z", 212, negrita=True, blanco=True)
        self.seg_state = self._campo("Estado", 46)
        self.seg_compress = self._campo("Compresible [—] : NVP [—]", 155, negrita=True)
        self.seg_compress.setToolTip("Pendiente: el motor propio aún no lee/aplica compresibilidad ni ventilación natural (NVP)")
        self.seg_count = self._campo("Conductos de aire 0", 116)
        self.seg_model = QLabel("")
        self.seg_render = QLabel("Render: …")
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        for nombre in ("pb_play", "pb_rapido", "pb_pausa", "pb_rapido", "pb_play"):
            sb.addWidget(self._boton_estado(nombre, "Simulación dinámica"))
        for w in (self.seg_coord, self.seg_state, self.seg_compress, self.seg_count):
            sb.addWidget(w)
        sb.addWidget(self.status, 1)
        for w in (self.seg_model, self.seg_render):
            sb.addPermanentWidget(w)
        for nombre in ICONOS_VISTA:
            sb.addPermanentWidget(self._boton_estado(nombre, "Modo de vista"))

    @staticmethod
    def _boton_estado(nombre: str, tip: str) -> QToolButton:
        b = QToolButton()
        b.setIcon(icon(nombre, 20))
        b.setIconSize(QSize(20, 20))
        b.setAutoRaise(True)
        b.setEnabled(False)
        b.setToolTip(f"{tip} — {chrome.PENDING_TIP}")
        return b

    # ------------------------------------------------------------ acciones, menús y barras
    def _act(self, text, slot, shortcut=None, tip=None, checkable=False, checked=False):
        a = QAction(text, self)
        if checkable:
            a.setCheckable(True)
            a.setChecked(checked)
            a.toggled.connect(slot)
        else:
            a.triggered.connect(slot)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        a.setToolTip(tip or text.replace("&", "").rstrip("…"))
        if tip:
            a.setStatusTip(tip)
        return a

    def _mirror(self, src: QAction, name: str, tip: str | None = None) -> QAction:
        """Acción con el nombre observado en la referencia que delega en una acción propia (y la refleja)."""
        m = QAction(name, self)
        m.setToolTip(tip or name)
        m.setStatusTip(tip or name)
        m.setCheckable(src.isCheckable())
        m.setEnabled(src.isEnabled())
        if src.isCheckable():
            m.setChecked(src.isChecked())
            m.toggled.connect(lambda c: src.setChecked(c) if src.isChecked() != c else None)
            src.toggled.connect(lambda c: m.setChecked(c) if m.isChecked() != c else None)
        else:
            m.triggered.connect(lambda _c=False: src.trigger())
        src.changed.connect(lambda: m.setEnabled(src.isEnabled()))
        return m

    def _hidden_combo(self, items, slot, index=0):
        """Combo de estado (no visible): guarda la selección que los controles de la referencia o el menú propio cambian."""
        cb = QComboBox(self)
        for k, t in items:
            cb.addItem(t, k)
        cb.setCurrentIndex(index)
        cb.currentIndexChanged.connect(slot)
        cb.hide()
        return cb

    def _radio_menu(self, parent_menu: QMenu, title: str, cb: QComboBox):
        sub = parent_menu.addMenu(title)
        grp = QActionGroup(self)
        grp.setExclusive(True)
        acts = []
        for i in range(cb.count()):
            a = QAction(cb.itemText(i), self)
            a.setCheckable(True)
            a.setChecked(i == cb.currentIndex())
            a.triggered.connect(lambda _c=False, k=i: cb.setCurrentIndex(k))
            grp.addAction(a)
            sub.addAction(a)
            acts.append(a)
        cb.currentIndexChanged.connect(lambda k: acts[k].setChecked(True) if 0 <= k < len(acts) else None)
        return sub

    def _build_actions_and_bars(self):
        A = self._act
        spec = self.spec = chrome.load_spec()
        self.act_open = A("&Abrir proyecto (.vsm / .vsmt / nativo)…", self.open_dialog, "Ctrl+O", "Abrir proyecto (Ctrl+O)")
        self.act_new = A("&Nuevo proyecto nativo", self.new_native_project, "Ctrl+Shift+N", "Nuevo proyecto nativo")
        self.act_demo = A("Cargar red de &demostración", self.load_demo, None, "Cargar red de demostración")
        self.act_save = A("&Guardar proyecto nativo como…", self.save_native_dialog, "Ctrl+S", "Guardar proyecto nativo (Ctrl+S)")
        self.act_csv = A("&Exportar tabla a CSV…", self.export_csv_dialog, "Ctrl+E", "Exportar la tabla de resultados a CSV (Ctrl+E)")
        self.act_png = A("Exportar &imagen del visor…", self.export_png_dialog, "Ctrl+Shift+E", "Guardar la vista 3D como imagen PNG")
        self.act_solve = A("&Ejecutar solucionador propio", self.run_solver, "F5", "Ejecutar el solucionador propio (F5)")
        self.act_fit = A("&Ajustar vista a la red", self.view.fit, "Home", "Ajustar la vista a la red (Inicio)")
        self.act_center = A("&Centrar en la galería seleccionada", self.view.focus_selected, "C")
        self.act_find = A("&Encontrar galería…", self.find_airway, "Ctrl+F", "Encontrar una galería por número o nombre (Ctrl+F)")
        self.act_add = A("&Añadir galería…", self.add_airway, "Ctrl+N", "Añadir galería (proyecto nativo)")
        self.act_edit = A("&Editar galería seleccionada…", self.edit_airway, "Ctrl+Return", "Editar la galería seleccionada")
        self.act_del = A("E&liminar galería seleccionada", self.delete_airway, "Del", "Eliminar la galería seleccionada")
        self.act_fan = A("Asignar &ventilador a la seleccionada…", self.edit_fan, None, "Asignar o editar ventilador")
        self.act_table = A("Tabla de resultados", lambda c: self.dock_table.setVisible(c), None,
                           "Mostrar/ocultar la tabla de resultados", True, False)
        self.act_props = A("Panel de propiedades y resumen", lambda c: self.dock_props.setVisible(c), None,
                           "Mostrar/ocultar propiedades y resumen", True, False)
        self.act_palette = A("Exponer (escala de color)", self._toggle_palette, "P", "Mostrar/ocultar «Exponer» (P)", True, True)
        self.act_labels = A("Texto sobre las galerías", self._toggle_labels, "T", "Mostrar texto sobre las galerías (T)", True, True)
        self.act_arrows = A("Flechas de sentido", self._toggle_arrows, None, "Mostrar el sentido del flujo", True, True)
        self.act_grid = A("Cuadrícula", self._toggle_grid, "G", "Mostrar la cuadrícula (G)", True, True)
        self.act_tubes = A("Sólidos (galerías con volumen)", self._toggle_tubes, None, "Galerías con volumen / líneas simples", True, True)
        self.act_refs = A("Referencias (superficies y notas)", self._toggle_refs, None, "Mostrar las superficies de referencia y las notas", True, True)
        self.act_nodos = A("Nodos", self._toggle_nodos, None, "Mostrar los nodos (extremos de las galerías)", True, False)
        self.act_pistas = A("Pistas", self._toggle_pistas, None, "Resaltar las pistas (rutas de galerías) del proyecto", True, False)
        self.act_visibilidad = A("Visibilidad", self._abrir_visibilidad, None,
                                 "Abrir las listas de visibilidad (tipo de aire, capa primaria y capas de referencia) de «Exponer»", False, False)
        self.act_pan = A("Panear vista", self._toggle_pan, None, "Panear vista: arrastre con el botón izquierdo para desplazar la vista", True, False)

        # estado de los controles que la referencia no tiene tal cual (origen del dato, magnitud propia, etiquetas, grosor)
        self.cb_mag = self._hidden_combo(MAGS, self._on_mag)
        self.cb_src = self._hidden_combo([("file", "Archivo (VentSim)"), ("calc", "Motor propio")], self.update_colors)
        self.cb_lab = self._hidden_combo(LABEL_MODES, self.update_colors, 0)
        self.cb_thick = self._hidden_combo([(k, txt) for txt, k in THICKNESS],
                                           lambda _i: self.view.set_tube_scale(self.cb_thick.currentData()), 2)
        self.cb_thick.setToolTip("Exagera el grosor de las galerías respecto a su sección real")

        # ---- menús (Archivo … Ayuda) desde la especificación
        handlers = {
            "Archivo/ABRIR": self.open_dialog,
            "Archivo/Salir": self.close,
            "Ver/Todos los aptos": self.view.fit,
            "Ver/Mostrar todo": self.view.fit,
            "Ver/Restablecer la Pantalla": self.reset_camera,
            "Ver/Ocultar Flujo Cero": self._toggle_flujo_cero,
            "Ver/Mostrar todas las capas": self._mostrar_todas_capas,
            "Ver/Mostrar todas las elevaciones": self._mostrar_todas_capas,
            "Ver/Establecer el Centro de Edición": self.view.focus_selected,
            "Ver/Vista rápida/Guardar Vista rápida": self.view.guardar_vista_rapida,
            "Ver/Vista rápida/Borrar actual": self.view.borrar_vista_rapida,
            "Ver/Vista rápida/Borrar Todo": self.view.borrar_vistas_rapidas,
            "Ver/Vista rápida/Vista rápida anterior": lambda: self.view.vista_rapida(-1),
            "Ver/Vista rápida/Siguiente Vista rápida": lambda: self.view.vista_rapida(1),
            "Ventana/Alejar": self.view.alejar,
            "Archivo/Cerrar": self.cerrar_proyecto,
            "Ver/Barras de herramientas": self._toggle_bars,
            "Ver/Copiar al portapapeles": self.copy_view_clipboard,
            "Ver/Crear imagen": self.export_png_dialog,
            "Vistas guardadas/Plan": self.view.view_top,
            "Vistas guardadas/Isométrica": self.view.view_iso,
            "Correr/Escritura de la estática": self.run_solver,
            "Correr/Resumen": self.show_summary,
            "Ayuda/Sobre": self.show_about,
        }
        for nombre, archivo in DEMOSTRACIONES.items():
            handlers[f"Archivo/Cargar demostración/{nombre}"] = lambda a=archivo: self.abrir_demostracion(a)
        mb = self.menuBar()
        self.menu_actions, n_ok, n_pend = chrome.build_menus(self, mb, spec, handlers,
                                                             {"Archivo/Cargar demostración/Otros ejemplos": self._fill_examples})
        self.menu_stats = (n_ok, n_pend)
        self.menu_actions["Ver/Ocultar Flujo Cero"].setCheckable(True)

        # ---- menú propio (no existe en la referencia): lo que NVS añade
        x = mb.addMenu("NVS")
        x.setToolTipsVisible(True)
        x.menuAction().setToolTip("Funciones propias de NVS que NO existen en Ventsim DESIGN")
        x.addActions([self.act_new, self.act_demo, self.act_save])
        x.addSeparator()
        x.addActions([self.act_add, self.act_edit, self.act_del, self.act_fan])
        x.addSeparator()
        x.addActions([self.act_solve, self.act_csv, self.act_png])
        x.addSeparator()
        self._radio_menu(x, "Origen del dato", self.cb_src)
        self._radio_menu(x, "Magnitud", self.cb_mag)
        self._radio_menu(x, "Texto de las etiquetas", self.cb_lab)
        self._radio_menu(x, "Grosor de las galerías", self.cb_thick)
        x.addSeparator()
        x.addActions([self.act_arrows, self.act_tubes, self.act_refs, self.act_nodos, self.act_pistas])
        x.addAction(self.act_center)
        x.addSeparator()
        x.addActions([self.act_table, self.act_props])
        x.addSeparator()
        x.addAction(self._act("Controles del visor", self.show_help))
        self._build_corner(mb)

        # ---- barra 1
        tb = self.bar1 = QToolBar("Barra 1")
        tb.setObjectName("mainBar")
        tb.setMovable(False)
        tb.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.TopToolBarArea, tb)
        b1_act = {0: self._mirror(self.act_new, "Nuevo", "Nuevo proyecto nativo"),
                  1: self._mirror(self.act_open, "Abrir", "Abrir proyecto (Ctrl+O)"),
                  6: self._mirror(self.act_find, "Encontrar...", "Encontrar una galería por número o nombre (Ctrl+F)"),
                  7: self._mirror(self.act_fit, "Mostrar todo", "Mostrar todo (ajusta la vista a la red)"),
                  8: self._mirror(self.act_solve, "Ejecutar", "Ejecutar el solucionador propio (F5)"),
                  10: self._mirror(self.act_pan, "Panear vista", "Panear vista (mantenga presionado el botón izquierdo del ratón para panear la vista)")}
        b1_ico = {**ICONOS_BARRA1, 7: icon_desplegable("pelicula"), 8: icon_desplegable("ejecutar")}
        self.bar1_actions = chrome.build_button_strip(self, tb, spec["barra1"], b1_act, b1_ico, 24)
        for i in (7, 8):
            tb.widgetForAction(self.bar1_actions[i]).setIconSize(QSize(40, 24))

        self.addToolBarBreak(Qt.TopToolBarArea)
        # ---- barra 2 («qué se muestra»)
        db = self.bar2 = QToolBar("Barra 2")
        db.setObjectName("displayBar")
        db.setMovable(False)
        db.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.TopToolBarArea, db)
        lists = [list(v) for v in spec["combos"].values()]
        only_air = {"Flujo de aire", "Identificadores"}
        qty_ok = {"Cantidad", "Velocidad"}
        t_act = self._mirror(self.act_labels, "T", "Texto sobre las galerías (T)")
        t_act.setText("T")
        b2_act = {1: self._mirror(self.act_palette, "Administrador de datos y color", "Mostrar/ocultar «Exponer» (P)"), 8: t_act}
        _acts2, combos2, labels2 = chrome.build_bar2(self, db, spec["barra2"], lists[:5], [only_air, qty_ok, only_air, {"Cantidad"}, {"Por defecto"}],
                                                    b2_act, ICONOS_BARRA2)
        self.cb_cat, self.cb_qty = combos2[2], combos2[3]
        self.cb_cat2, self.cb_views = combos2[10], combos2[14]
        self.lb_unit = labels2[4]
        for cb in (self.cb_cat, self.cb_cat2):
            cb.setCurrentIndex(cb.findText("Flujo de aire"))
        self.cb_views.setCurrentIndex(0)
        self.cb_views.setEnabled(True)
        self.cb_views.activated.connect(self._on_view_combo)
        self.cb_qty.activated.connect(self._on_qty_combo)
        self.cb_cat.activated.connect(self._on_cat_combo)
        self._cantidades = [self.cb_qty.itemText(i) for i in range(self.cb_qty.count())]

        # ---- raíl izquierdo
        rail = self.rail = QToolBar("Herramientas")
        rail.setObjectName("rail")
        rail.setMovable(False)
        rail.setOrientation(Qt.Vertical)
        rail.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.LeftToolBarArea, rail)
        r_act = {0: self._mirror(self.act_tubes, "Sólidos", "Sólidos (galerías con volumen)"),
                 2: self._mirror(self.act_fit, "Todos los aptos", "Todos los aptos (ajustar la vista a la red)"),
                 3: self._mirror(self.act_grid, "Cuadrícula", "Cuadrícula (G)"),
                 4: self._mirror(self.act_nodos, "Nodos", "Nodos: extremos de las galerías"),
                 5: self._mirror(self.act_arrows, "Flechas", "Flechas de sentido del flujo"),
                 6: self._mirror(self.act_refs, "Referencias", "Referencias: superficies y notas del proyecto"),
                 7: self._mirror(self.act_pistas, "Pistas", "Pistas: rutas de galerías del proyecto"),
                 8: self._mirror(self.act_visibilidad, "Visibilidad", "Visibilidad: tipo de aire, capa primaria y capas de referencia")}
        r_ico = {**ICONOS_RAIL, 5: icon_desplegable("flechas")}
        self.rail_actions = chrome.build_button_strip(self, rail, spec["raiL_izquierdo"], r_act, r_ico, 24)
        rail.widgetForAction(self.rail_actions[5]).setIconSize(QSize(36, 24))
        self.menu_actions["Ver/Barras de herramientas"].setChecked(True)

    def _build_corner(self, mb):
        """Esquina de la fila de menús: Etapa (lista del proyecto), candado y flechas, Mensajes, imagen y tarjeta."""
        corner = self.corner = QWidget()
        cl = QHBoxLayout(corner)
        cl.setContentsMargins(0, 0, 4, 0)
        cl.setSpacing(4)
        ayuda = QLabel()
        ayuda.setPixmap(icon("ayuda", 20).pixmap(20, 20))
        self.cb_stage = QComboBox()
        self.cb_stage.setFixedWidth(240)
        self.cb_stage.activated.connect(self._on_stage)
        msg = QToolButton()
        msg.setText("Mensajes")
        msg.setIcon(icon("mensajes", 20))
        msg.setIconSize(QSize(20, 20))
        msg.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        msg.setStyleSheet("QToolButton{color:#1f5fbf;font-weight:bold;}")
        msg.clicked.connect(self.show_messages)
        cl.addWidget(ayuda)
        cl.addSpacing(18)
        cl.addWidget(QLabel("Etapa"))
        cl.addWidget(self.cb_stage)
        for nombre, tip, fn in (("candado", "Bloqueo de etapa", None), ("flecha_izq", "Etapa anterior", self._stage_prev),
                                ("flecha_der", "Etapa siguiente", self._stage_next)):
            b = QToolButton()
            b.setIcon(icon(nombre, 18))
            b.setIconSize(QSize(18, 18))
            b.setAutoRaise(True)
            b.setToolTip(tip if fn else f"{tip} — {chrome.PENDING_TIP}")
            if fn:
                b.clicked.connect(fn)
            else:
                b.setEnabled(False)
            cl.addWidget(b)
        cl.addStretch(1)
        cl.addWidget(msg)
        for nombre, tip, fn in (("camara", "Crear imagen de la vista", self.export_png_dialog),
                                ("tarjeta", "Pendiente", None)):
            b = QToolButton()
            b.setIcon(icon(nombre, 24))
            b.setIconSize(QSize(24, 24))
            b.setAutoRaise(True)
            b.setToolTip(tip if fn else chrome.PENDING_TIP)
            if fn:
                b.clicked.connect(fn)
            else:
                b.setEnabled(False)
            cl.addWidget(b)
        mb.setCornerWidget(corner, Qt.TopRightCorner)

    def _toggle_bars(self, on):
        for b in (self.bar1, self.bar2, self.rail):
            b.setVisible(on)

    def _on_cat_combo(self, idx):
        """«Identificadores › Tipo de aire» colorea por categoría; «Flujo de aire» vuelve a las cantidades numéricas."""
        self._fijar_color_categorico(self.cb_cat.itemText(idx) == "Identificadores")

    def _fijar_color_categorico(self, si: bool):
        self.color_categorico = si
        self.pestana = 2 if si else 0
        self.cb_cat.blockSignals(True)
        self.cb_cat.setCurrentIndex(self.cb_cat.findText("Identificadores" if si else "Flujo de aire"))
        self.cb_cat.blockSignals(False)
        self.cb_qty.blockSignals(True)
        self.cb_qty.clear()
        self.cb_qty.addItems(["Tipo de aire"] if si else self._cantidades)
        self.cb_qty.setCurrentIndex(0)
        self.cb_qty.blockSignals(False)
        if not si:
            self._sync_qty_combo()
        self.update_colors()
        self._aplicar_etapa()

    def _on_qty_combo(self, idx):
        t = self.cb_qty.itemText(idx)
        k = {"Cantidad": 0, "Velocidad": 1}.get(t)
        if k is not None:
            self.cb_mag.setCurrentIndex(k)

    def _sync_qty_combo(self):
        """El combo «Cantidad/Velocidad» de la referencia refleja la magnitud activa (las propias quedan en blanco)."""
        k = self.cb_mag.currentIndex()
        name = {0: "Cantidad", 1: "Velocidad"}.get(k)
        self.cb_qty.blockSignals(True)
        self.cb_qty.setCurrentIndex(self.cb_qty.findText(name) if name else -1)
        self.cb_qty.blockSignals(False)

    def copy_view_clipboard(self):
        QApplication.clipboard().setImage(self.view.grab().toImage())
        self.status.setText("Vista copiada al portapapeles")

    def show_summary(self):
        self.tabs.setCurrentIndex(1)
        self.act_props.setChecked(True)
        self.dock_props.setVisible(True)

    # --- conmutadores del visor
    def _toggle_palette(self, on):
        self.exponer.setVisible(on)
        if on:
            self._place_panel(force=True)

    def _toggle_refs(self, on):
        self.view.show_referencias = on
        self.view.show_notas = on
        self.view.update()

    def _toggle_pan(self, on):
        self.view.pan_activo = on

    def _on_transparencia(self, t: float):
        self.view.opacidad_referencias = float(np.clip(1.0 - 1.55 * t, 0.05, 1.0))      # 27 % del deslizador ≈ 58 % de opacidad
        self.view.update()

    def _toggle_labels(self, on):
        self.view.show_labels = on
        self.cb_lab.setEnabled(on)
        self.view.update()

    def _toggle_arrows(self, on):
        self.view.set_flechas(on)

    def _toggle_nodos(self, on):
        self.view.set_nodos(on)

    def _toggle_pistas(self, on):
        """Pistas: resalta las rutas de galerías guardadas en el proyecto (sección TRACKS)."""
        if not (on and self.prj and self.prj.escena.pistas):
            self.view.set_pista([], (255, 0, 0))
            return
        por_guid = {a.raw_row.get("GUID"): i for i, a in enumerate(self.prj.airways) if a.raw_row}
        pista = self.prj.escena.pistas[0]
        self.view.set_pista([por_guid[g] for g in pista.guids if g in por_guid], pista.color)

    def _toggle_grid(self, on):
        self.view.show_grid = on
        self.view.update()

    def _toggle_tubes(self, on):
        self.view.tubes = on
        self.view.update()

    def showEvent(self, ev):
        super().showEvent(ev)
        QTimer.singleShot(0, lambda: self._place_panel(force=True))
        QTimer.singleShot(60, lambda: self._place_panel(force=True))

    def eventFilter(self, obj, ev):
        if obj is self.view and ev.type() == QEvent.Resize:
            self._place_panel()
        return super().eventFilter(obj, ev)

    def _place_panel(self, force=False):
        p = self.exponer
        if not self.act_palette.isChecked() and not force:
            return
        p.adjustSize()
        if p.movido and not force:
            p.move(min(p.x(), max(0, self.view.width() - p.width())), p.y())
        else:
            p.move(self.view.width() - p.width(), 0)
        p.raise_()

    def _fill_examples(self, menu: QMenu):
        menu.clear()
        if EXAMPLES_DIR.exists():
            for p in sorted(q for q in EXAMPLES_DIR.iterdir() if q.suffix.lower() in (".vsm", ".vsmt")):
                menu.addAction(self._act(f"{p.name}  ({p.stat().st_size / 1e6:.1f} MB)",
                                         lambda _c=False, q=p: self.open_path(q)))
        else:
            a = menu.addAction("Carpeta de ejemplos no encontrada")
            a.setEnabled(False)

    def abrir_demostracion(self, archivo: str):
        ruta = EXAMPLES_DIR / archivo
        if ruta.exists():
            self.open_path(ruta)
        else:
            QMessageBox.information(self, "Cargar demostración", f"No se encontró {archivo} en\n{EXAMPLES_DIR}")

    def find_airway(self):
        if not self.prj or not self.prj.airways:
            return
        texto, ok = QInputDialog.getText(self, "Encontrar", "Número o nombre de la galería:")
        if not ok or not texto.strip():
            return
        t = texto.strip().lower()
        for i, a in enumerate(self.prj.airways):
            if a.uid == t or t in a.name.lower():
                self.view.set_selected(i)
                self.view.focus_selected()
                self.on_view_selected(i)
                return
        self.status.setText(f"No se encontró «{texto.strip()}»")

    def show_messages(self):
        avisos = self.prj.warnings if self.prj else []
        QMessageBox.information(self, "Mensajes", "\n\n".join(avisos) if avisos else "Sin mensajes.")

    # ------------------------------------------------------------ etapas y vistas guardadas
    def _fill_etapas(self):
        etapas = self.prj.escena.etapas if self.prj else []
        self.cb_stage.blockSignals(True)
        self.cb_stage.clear()
        self.cb_stage.addItems(etapas)
        self.etapa_actual = self._etapa_inicial(etapas)
        self.cb_stage.setCurrentIndex(self.etapa_actual)
        self.cb_stage.blockSignals(False)
        self._aplicar_etapa()

    def _etapa_inicial(self, etapas: list[str]) -> int:
        """Etapa activa guardada en el proyecto (STATE columna 79); si falta, la última que usa alguna galería."""
        if not etapas:
            return -1
        guardada = self.prj.escena.etapa_activa
        if 0 <= guardada < len(etapas):
            return guardada
        usadas = 0
        for a in self.prj.airways:
            usadas |= a.etapas
        return min(usadas.bit_length() - 1, len(etapas) - 1) if usadas > 0 else len(etapas) - 1

    def _on_stage(self, idx: int):
        self.etapa_actual = idx
        self._aplicar_etapa()

    def _stage_prev(self):
        if self.etapa_actual > 0:
            self.cb_stage.setCurrentIndex(self.etapa_actual - 1)
            self._on_stage(self.etapa_actual - 1)

    def _stage_next(self):
        if 0 <= self.etapa_actual < self.cb_stage.count() - 1:
            self.cb_stage.setCurrentIndex(self.etapa_actual + 1)
            self._on_stage(self.etapa_actual + 1)

    def _aplicar_etapa(self):
        """Cada galería del .vsm guarda en «Stage» una máscara de bits con las etapas en que existe."""
        p = self.prj
        if p is None or not p.airways:
            return
        bit = 1 << self.etapa_actual if self.etapa_actual >= 0 else -1
        visibles = np.array([a.etapas & bit != 0 for a in p.airways], bool)
        if self.ocultar_flujo_cero or self.ocultar_bajo:
            visibles &= self._visibles_por_valor()
        for k in (2, 3):
            marcas = self.cat_visibles.get(k)
            if marcas and not all(marcas):
                visibles &= np.array(marcas + [True], bool)[self.categorias[k][2]]
        self.view.set_visible(visibles)
        self.view.set_notas([(resolver_campos(n.texto, p.airways, p.escena, n.guids), n.fx, n.fy, n.color, n.posicion)
                             for n in p.escena.notas if n.etapas & bit])
        self.update_status()

    def _aplicar_modo_guardado(self, prj: Project):
        """Con qué dato se coloreaba el proyecto al guardarlo (STATE columna 7: 101 caudal, 102 velocidad, 613 tipo de aire)."""
        codigo = prj.escena.codigo_color
        self.color_categorico = codigo == 613 and bool(prj.escena.tipos_aire)
        self.cb_cat.blockSignals(True)
        self.cb_cat.setCurrentIndex(self.cb_cat.findText("Identificadores" if self.color_categorico else "Flujo de aire"))
        self.cb_cat.blockSignals(False)
        self.cb_qty.blockSignals(True)
        self.cb_qty.clear()
        self.cb_qty.addItems(["Tipo de aire"] if self.color_categorico else self._cantidades)
        self.cb_qty.blockSignals(False)
        self.cb_mag.blockSignals(True)
        self.cb_mag.setCurrentIndex(1 if codigo == 102 else 0)
        self.cb_mag.blockSignals(False)
        if self.color_categorico:
            self.cb_qty.setCurrentIndex(0)
        else:
            self._sync_qty_combo()

    def _visibles_por_valor(self) -> np.ndarray:
        """Galerías que superan los filtros por valor: flujo cero y datos por debajo del marcador azul de «Exponer»."""
        src = self.cb_src.currentData()
        ok = np.ones(len(self.prj.airways), bool)
        if self.ocultar_flujo_cero:
            q, _s, hay = self.magnitude_values("Q", src)
            if hay:
                ok &= np.nan_to_num(q) > 1e-9
        if self.ocultar_bajo:
            mag = self._mag()
            vals, _s, hay = self.magnitude_values(mag, src)
            if hay:
                ok &= ~(np.nan_to_num(vals, nan=np.inf) < self.scales[mag].thresholds[0])
        return ok

    def _toggle_flujo_cero(self, *_):
        self.ocultar_flujo_cero = self.menu_actions["Ver/Ocultar Flujo Cero"].isChecked()
        self._aplicar_etapa()

    def _toggle_ocultar_bajo(self, on: bool):
        self.ocultar_bajo = on
        self._aplicar_etapa()

    def _mostrar_todas_capas(self):
        """Vuelve a mostrar todo: casillas de categorías, flujo cero y datos bajos."""
        self.cat_visibles = {k: [True] * len(v[0]) for k, v in self.categorias.items()}
        self.ocultar_flujo_cero = self.ocultar_bajo = False
        self.menu_actions["Ver/Ocultar Flujo Cero"].setChecked(False)
        self.exponer.casilla.setChecked(False)
        if self.prj:
            self.view.set_mallas(self.prj.escena.mallas)
        if self.pestana:
            self._mostrar_pestana(self.pestana)
        self._aplicar_etapa()

    def cerrar_proyecto(self):
        """Archivo › Cerrar: vuelve al visor vacío con la rejilla por defecto, como Ventsim recién abierto."""
        from ..escena import Rejilla
        self.prj = None
        self.setWindowTitle(self._titulo(None))
        self.model.set_project(None)
        self.view.set_geometry(np.zeros((0, 3)), np.zeros((0, 3)))
        self.view.set_mallas([])
        self.view.set_notas([])
        self.view.set_rejilla(Rejilla())
        self.view.set_ambiente("#6495ed", "#bcbcbc")
        self.cb_stage.clear()
        self.etapa_actual = -1
        self.color_categorico = False
        self.pestana = 0
        self.act_palette.setChecked(False)
        self.refresh_all()

    def _abrir_visibilidad(self, *_):
        self.act_palette.setChecked(True)
        self._mostrar_pestana(2)

    def _on_pestana(self, k: int):
        """Pestañas de «Exponer»: escala numérica, tipo de aire (colorea por categoría), capa primaria y capas de referencia."""
        if k == 0:
            self._fijar_color_categorico(False)
        elif k == 2:
            self._fijar_color_categorico(True)
        else:
            self._mostrar_pestana(k)

    def _mostrar_pestana(self, k: int):
        self.pestana = k
        nombres, colores, _idx = self.categorias.get(k, ([], [], None))
        self.exponer.set_categorias(nombres, colores, self.cat_visibles.get(k, [True] * len(nombres)))
        self.exponer.mostrar_pestana(k)

    def _on_categorias(self, visibles: list):
        self.cat_visibles[self.pestana] = visibles
        if self.pestana == 5:
            self.view.set_mallas([m for m, ok in zip(self.prj.escena.mallas, visibles) if ok])
        else:
            self._aplicar_etapa()

    @staticmethod
    def _indices_columna(airways, columna: str, n: int) -> np.ndarray:
        """Índice de categoría de cada galería (columna del archivo); los valores fuera de la lista quedan en `n`."""
        return np.array([min(int(a.raw_row.get(columna) or 0), n) if a.raw_row else n for a in airways], int)

    def _construir_categorias(self, prj: Project):
        e = prj.escena
        self.categorias = {
            2: ([n for n, _c in e.tipos_aire], [c for _n, c in e.tipos_aire], self._indices_columna(prj.airways, "Air Type", len(e.tipos_aire))),
            3: ([n for n, _c in e.capas_primarias], [c for _n, c in e.capas_primarias],
                self._indices_columna(prj.airways, "Primary Layer", len(e.capas_primarias))),
            5: (e.capas_referencia, ["#7d8794"] * len(e.capas_referencia), None),
        }
        self.cat_visibles = {k: [True] * len(v[0]) for k, v in self.categorias.items()}

    def _rgb_tipos_aire(self) -> np.ndarray:
        nombres, colores, idx = self.categorias[2]
        paleta = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] for c in colores] + [[125, 135, 148]], np.uint8)
        return paleta[idx]

    def _fill_vistas(self):
        self.cb_views.clear()
        self.cb_views.addItem("Por defecto")
        if self.prj:
            self.cb_views.addItems([v.nombre for v in self.prj.escena.vistas])

    def _on_view_combo(self, idx: int):
        escena = self.prj.escena if self.prj else None
        if escena is None:
            return
        vista = escena.camara if idx == 0 else escena.vistas[idx - 1]
        if vista is not None:
            self.view.set_camera(vista.objetivo, vista.distancia, vista.giro, vista.elevacion)

    def reset_camera(self):
        self.cb_views.setCurrentIndex(0)
        self._on_view_combo(0)

    # ------------------------------------------------------------ apertura
    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        for u in ev.mimeData().urls():
            self.open_path(Path(u.toLocalFile()))
            break

    def open_dialog(self):
        start = str(EXAMPLES_DIR) if EXAMPLES_DIR.exists() else ""
        p, _ = QFileDialog.getOpenFileName(self, "Abrir proyecto", start,
                                           "Proyectos (*.vsm *.vsmt *.nvs.json *.json);;Todos (*)")
        if p:
            self.open_path(Path(p))

    def open_path(self, path: Path):
        path = Path(path)
        self._busy(f"Cargando {path.name}…")
        loader = load_native if path.suffix.lower() == ".json" else load_vsm
        self._start(Worker(loader, path), self._on_loaded)

    def _start(self, worker: Worker, slot):
        self.worker = worker
        worker.done.connect(slot)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(lambda: QApplication.restoreOverrideCursor())
        worker.start()

    def _busy(self, msg):
        self.status.setText(msg)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.act_solve.setEnabled(False)

    def _on_failed(self, msg):
        self.status.setText("Error")
        self.act_solve.setEnabled(self.prj is not None)
        self.carga_terminada.emit()
        QMessageBox.critical(self, "Error", msg)

    def _on_loaded(self, prj: Project):
        self.set_project(prj)
        self.status.setText(f"{prj.name}: {len(prj.airways)} galerías cargadas")
        self.carga_terminada.emit()

    def set_project(self, prj: Project):
        self.prj = prj
        self.setWindowTitle(self._titulo(prj))
        self.model.set_project(prj)
        self.view.set_geometry(np.array([a.p1 for a in prj.airways]).reshape(-1, 3),
                               np.array([a.p2 for a in prj.airways]).reshape(-1, 3),
                               np.array([max(a.width, 2.0) for a in prj.airways]))
        self.view.set_mallas(prj.escena.mallas)
        self.view.set_rejilla(prj.escena.rejilla)
        self.view.set_ambiente(prj.escena.cielo, prj.escena.color_rejilla)
        self._construir_categorias(prj)
        self.act_pistas.setChecked(False)
        self.act_palette.setChecked(True)
        self._fill_vistas()
        self._fill_etapas()
        if prj.escena.camara is not None:
            self.reset_camera()
        self.scales = default_scales()
        self.cb_src.blockSignals(True)
        self.cb_src.setCurrentIndex(0 if prj.kind == "vsm" else 1)
        self.cb_src.blockSignals(False)
        self._aplicar_modo_guardado(prj)
        self.refresh_all(autoscale_if_needed=True)

    # ------------------------------------------------------------ cálculo
    def run_solver(self):
        if not self.prj or not self.prj.airways:
            return QMessageBox.information(self, "Cálculo", "No hay proyecto cargado.")
        self._busy("Resolviendo la red…")
        self.seg_state.setText("Estado: calculando…")
        self._start(Worker(solve_project, self.prj), self._on_solved)

    def _on_solved(self, info):
        self.act_solve.setEnabled(True)
        self.cb_src.blockSignals(True)
        self.cb_src.setCurrentIndex(1)
        self.cb_src.blockSignals(False)
        self.refresh_all()
        ok = "convergió" if info["converged"] else "NO convergió"
        self.status.setText(f"Solucionador propio: {ok} en {info['iterations']} iteraciones; residuo {info['residual']:.2e} m³/s")

    def solve_sync(self):   # para autoprueba
        info = solve_project(self.prj)
        self._on_solved(info)
        return info

    # ------------------------------------------------------------ datos mostrados
    def _mag(self) -> str:
        return self.cb_mag.currentData()

    def _on_mag(self):
        mag = self._mag()
        self.lb_unit.setText(self.scales[mag].unit)
        self.cb_src.setEnabled(mag != "DIFF")
        self._sync_qty_combo()
        self.update_colors()

    def magnitude_values(self, mag: str, src: str):
        """(valores, signos, hay_datos). Los valores NO disponibles son NaN."""
        p = self.prj
        n = len(p.airways)
        nan = np.full(n, np.nan)
        sq = np.array([np.nan if a.saved_Q is None else a.saved_Q for a in p.airways])
        cq = np.array([np.nan if a.calc_Q is None else a.calc_Q for a in p.airways])
        q = sq if src == "file" else cq
        if mag == "Q":
            return np.abs(q), np.nan_to_num(q), np.isfinite(q).any()
        if mag == "V":
            area = np.array([a.area for a in p.airways])
            with np.errstate(divide="ignore", invalid="ignore"):
                v = np.where(area > 0, np.abs(q) / area, np.nan)
            return v, np.nan_to_num(q), np.isfinite(v).any()
        if mag == "DP":
            if src == "file":
                dp = np.array([np.nan if a.saved_dp is None else a.saved_dp for a in p.airways])
            else:
                dp = np.array([np.nan if a.calc_dp is None else abs(a.calc_dp) for a in p.airways])
            return dp, np.nan_to_num(q), np.isfinite(dp).any()
        if mag == "DIFF":
            with np.errstate(invalid="ignore"):
                rel = 100 * np.abs(cq - sq) / np.maximum(np.abs(sq), 1.0)
            return rel, np.nan_to_num(cq), np.isfinite(rel).any()
        return nan, nan, False

    def _velocidad_firmada(self, src: str) -> np.ndarray:
        """Caudal con signo ÷ sección de cada galería (m/s): sentido y rapidez del aire animado."""
        a = self.prj.airways
        q = np.array([np.nan if v is None else v for v in (x.saved_Q if src == "file" else x.calc_Q for x in a)])
        area = np.array([x.area for x in a])
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(area > 0, q / area, 0.0)

    def autoscale(self):
        if not self.prj or not self.prj.airways:
            return
        mag = self._mag()
        vals, _s, ok = self.magnitude_values(mag, self.cb_src.currentData())
        if not ok:
            return
        th = auto_thresholds(vals)
        if th:
            self.scales[mag].thresholds = th
            self.update_colors()

    @staticmethod
    def _fmt(v: float, mag: str) -> str:
        if not np.isfinite(v):
            return ""
        if mag == "DIFF":
            return "≈0" if v < 0.0005 else f"{v:.3g}%"
        return f"{v:.1f}" if abs(v) >= 1 else f"{v:.2f}"

    def update_colors(self):
        p = self.prj
        mag, src = self._mag(), self.cb_src.currentData()
        sc = self.scales[mag]
        self.lb_unit.setText(sc.unit)
        self.cb_src.setEnabled(mag != "DIFF")
        self.exponer.set_scale(sc)
        if self.pestana in (0, 2):
            self.pestana = 2 if self.color_categorico else 0
            self._mostrar_pestana(self.pestana) if self.pestana else self.exponer.mostrar_pestana(0)
        if not p or not p.airways:
            self.view.set_values(None)
            self.view.set_flujo(None)
            self.view.set_labels(None)
            return
        vals, signs, ok = self.magnitude_values(mag, src)
        if not ok:
            self.sin_datos = (f"{sc.title}: sin datos. " + ("Este proyecto no trae valores guardados en el archivo." if src == "file" and mag != "DIFF"
                              else "Ejecute el solucionador (F5) para obtener valores del motor." if mag != "DIFF"
                              else "Abra un .vsm y ejecute el solucionador (F5) para comparar."))
            self.status.setText(self.sin_datos)
            self.view.set_values(None, None, None)
            self.view.set_flujo(None)
            self.view.set_labels(None)
            return
        self.sin_datos = ""
        self.view.set_colores_directos(self._rgb_tipos_aire() if self.color_categorico and p.escena.tipos_aire else None)
        self.view.set_values(vals, signs, sc)
        self.view.set_flujo(self._velocidad_firmada(src))
        lm = self.cb_lab.currentData()
        txts = []
        for a, v in zip(p.airways, vals):
            t = self._fmt(v, mag)
            if lm == "none":
                txts.append("")
            elif lm == "val":
                txts.append(t)
            elif lm == "name":
                txts.append(a.name)
            elif lm == "uid":
                txts.append(a.uid)
            else:
                txts.append(f"{t} · {a.name}" if a.name else t)
        if self.ocultar_flujo_cero or self.ocultar_bajo:
            self._aplicar_etapa()
        self.view.set_labels(txts)
        self.view.set_nombres([a.name for a in p.airways] if lm == "val" else None)
        self.update_callout()

    def update_callout(self):
        p, i = self.prj, self.view.sel
        if not p or i < 0 or i >= len(p.airways):
            self.view.set_callout(None)
            return
        a = p.airways[i]
        rows = [f"{a.uid} · {a.name}" if a.name else f"Galería {a.uid}"]
        if a.saved_Q is not None:
            rows.append(("Q archivo", f"{a.saved_Q:.2f} m³/s"))
        if a.calc_Q is not None:
            rows.append(("Q motor", f"{a.calc_Q:.2f} m³/s"))
        q = a.calc_Q if a.calc_Q is not None else a.saved_Q
        if a.area > 0 and q is not None:
            rows.append(("Velocidad", f"{abs(q) / a.area:.2f} m/s"))
        rows.append(("Longitud", f"{a.length:.1f} m"))
        rows.append(("Sección", f"{a.area:.1f} m²"))
        self.view.set_callout(rows)

    # ------------------------------------------------------------ refresco de la UI
    def refresh_all(self, autoscale_if_needed: bool = False):
        has = self.prj is not None and bool(self.prj.airways)
        self.act_solve.setEnabled(has)
        self.act_csv.setEnabled(has)
        self.act_png.setEnabled(has)
        self.act_fit.setEnabled(has)
        self.act_save.setEnabled(self.prj is not None and self.prj.kind == "nativo")
        self.model.refresh()
        if autoscale_if_needed and has:
            self._maybe_autoscale()
        self.update_colors()
        self.fill_summary()
        self.fill_props(self.view.sel if has else -1)
        self.refresh_actions()
        self.update_status()

    def _maybe_autoscale(self):
        """Si casi todo cae en una sola banda con los umbrales por defecto, ajusta la escala a los datos."""
        mag, src = self._mag(), self.cb_src.currentData()
        vals, _s, ok = self.magnitude_values(mag, src)
        if not ok:
            return
        v = vals[np.isfinite(vals)]
        if len(v) < 10:
            return
        band = self.scales[mag].band_index(v)
        if np.bincount(band).max() / len(v) > 0.7:
            th = auto_thresholds(vals)
            if th:
                self.scales[mag].thresholds = th

    def update_status(self):
        p = self.prj
        mode = self.view.render_mode()
        self.seg_render.setText({"gpu": "Render: GPU", "software": "Render: CPU (sin GPU)"}.get(mode, "Render: …"))
        if p is None:
            self.seg_model.setText("")
            self.seg_count.setText("Conductos de aire 0")
            self.seg_state.setText("Estado")
            return
        reales = np.array([not a.ficticia for a in p.airways], bool)
        total, visibles = int(reales.sum()), int((self.view.visible & reales).sum())
        self.seg_count.setText(f"Conductos de aire {total}" if visibles == total else f"Conductos de aire {visibles}({total})")
        if p.solved:
            i = p.solve_info
            self.seg_state.setText(f"Estado: {'convergió' if i['converged'] else 'NO convergió'} · {i['iterations']} it.")
        else:
            self.seg_state.setText("Estado")
        if p.kind == "nativo":
            dot, txt, tip = "#2d6ad6", "Proyecto nativo", "Proyecto nativo · sin referencia de VentSim"
        elif p.validated:
            dot, txt, tip = "#1b9e57", "Modelo validado", "Modelo validado por prueba diferencial (D-NET-02)"
        else:
            dot, txt, tip = "#c27a00", "Modelo SIN validar", "Modelo SIN validar: usa funciones no implementadas (ver «Resumen y validez»)"
        self.seg_model.setToolTip(tip)
        self.seg_model.setText(f'<span style="color:{dot}">●</span> {txt}')

    def on_cursor(self, pos):
        """Coordenadas del cursor en la barra de estado, a lo sumo ~25 veces/s (la última posición no se pierde)."""
        now = time.perf_counter()
        if pos is None or now - self._last_cursor_t >= 0.04:
            self._apply_cursor(pos)
            return
        self._pending_cursor = pos
        if not self._cursor_timer.isActive():
            self._cursor_timer.start(40)

    def _flush_cursor(self):
        if self._pending_cursor is not None:
            self._apply_cursor(self._pending_cursor)

    def _apply_cursor(self, pos):
        self._last_cursor_t = time.perf_counter()
        self._pending_cursor = None
        if pos is not None:                      # fuera de la rejilla se conserva la última posición, como Ventsim
            self.seg_coord.setText(f"Coordenadas {pos[0]:,.1f} E   {pos[1]:,.1f} N   {pos[2]:,.0f} Z".replace(",", " "))

    def fill_summary(self):
        p = self.prj
        if p is None:
            self.summary.setHtml("<p style='color:#5d6b82'>Sin proyecto. Abra un .vsm o cree un proyecto nativo.</p>")
            return
        e = html.escape
        css = ("<style>h3{margin:0 0 4px 0}.k{color:#5d6b82}.card{background:#f5f8fd;border:1px solid #d3d9e4}"
               "li{margin-bottom:3px}</style>")
        s = [css, f"<h3>{e(p.name)}</h3>", f"<p><span class='k'>Tipo</span> <b>{p.kind}</b> &nbsp; "
             f"<span class='k'>Galerías</span> <b>{len(p.airways)}</b>"]
        if p.kind == "vsm":
            s.append(f" &nbsp; <span class='k'>Guardó la versión</span> <b>{e(p.saved_version)}</b> &nbsp; "
                     f"<span class='k'>ρ</span> <b>{p.rho}</b> kg/m³")
        s.append("</p>")
        if p.kind == "vsm":
            s.append(f"<p><span style='color:{theme.FILE_BLUE}'>■</span> Azul = valores <b>leídos del archivo</b> (resultados que guardó VentSim)<br>"
                     f"<span style='color:{theme.ENGINE_GREEN}'>■</span> Verde = valores <b>calculados por el motor propio</b></p>")
        if p.validated:
            s.append("<p><b>Validez:</b> este modelo pertenece al conjunto de la prueba diferencial D-NET-02 "
                     "(caudales del motor = caudales de VentSim, error relativo &lt; 1e-3).</p>")
        elif p.kind == "vsm":
            s.append("<p><b>Validez:</b> este modelo <b>no</b> pertenece al conjunto validado. Las diferencias "
                     "mostradas son esperables si usa funciones aún no implementadas.</p>")
        else:
            s.append("<p><b>Validez:</b> proyecto nativo; el motor usa las reglas verificadas con archivos de ejemplo, "
                     "pero este modelo no tiene resultado de referencia de VentSim.</p>")
        if p.warnings:
            s.append("<p><b>Funciones presentes no implementadas / aproximaciones:</b></p><ul>")
            s += [f"<li>{e(w)}</li>" for w in p.warnings]
            s.append("</ul>")
        if p.solved:
            i = p.solve_info
            s.append(f"<p><b>Solucionador:</b> {'convergió' if i['converged'] else '<b>NO convergió</b>'} · "
                     f"iteraciones {i['iterations']} · residuo {i['residual']:.2e} m³/s · nodos {i['n_nodes']} · "
                     f"bocas (p=0): {i['n_fixed_nodes']}</p>")
            extra = {k: v for k, v in i.items() if k not in ("converged", "iterations", "residual", "n_nodes", "n_fixed_nodes")}
            if extra:
                s.append("<ul>" + "".join(f"<li>{e(str(k))}: {v}</li>" for k, v in extra.items()) + "</ul>")
            st = comparison_stats(p)
            if st:
                s.append(f"<p><b>Comparación con el archivo</b> (|Q|&gt;1 m³/s, n={st['n']}):<br>"
                         f"error relativo mediano {st['median']:.2e} · p95 {st['p95']:.2e} · máximo {st['max']:.2e} · "
                         f"{100 * st['within_1e-3']:.1f} % dentro de 1e-3</p>")
        else:
            s.append("<p><i>Solucionador aún no ejecutado (menú Correr › Escritura de la estática, F5).</i></p>")
        self.summary.setHtml("".join(s))

    def fill_props(self, i: int):
        self.props.clear()
        p = self.prj
        if p is None or i < 0 or i >= len(p.airways):
            return
        a = p.airways[i]

        def group(title):
            g = QTreeWidgetItem([title, "", ""])
            f = g.font(0)
            f.setBold(True)
            g.setFont(0, f)
            for c in range(3):
                g.setBackground(c, QBrush(QColor("#eef3fb")))
            self.props.addTopLevelItem(g)
            g.setExpanded(True)
            return g

        def row(g, k, v, org="", fmt="{:.6g}"):
            if v is None:
                return
            txt = fmt.format(v) if isinstance(v, float) else str(v)
            it = QTreeWidgetItem(g, [k, txt, {"f": "archivo", "m": "motor", "": ""}[org]])
            if org:
                col = C_FILE if org == "f" else C_ENGINE
                for c in range(3):
                    it.setForeground(c, QBrush(col))

        g = group("Identificación")
        row(g, "Nº", a.uid)
        row(g, "Nombre", a.name or "(sin nombre)")
        g = group("Geometría")
        row(g, "Inicio (X, Y, Z) [m]", "({:.2f}, {:.2f}, {:.2f})".format(*a.p1))
        row(g, "Fin (X, Y, Z) [m]", "({:.2f}, {:.2f}, {:.2f})".format(*a.p2))
        row(g, "Longitud [m]", float(a.length))
        row(g, "Ancho × alto [m]", f"{a.width:g} × {a.height:g}")
        row(g, "Área [m²]", float(a.area))
        row(g, "Perímetro [m]", float(a.perimeter))
        g = group("Resistencia (parámetros)")
        row(g, "k de Atkinson [N·s²/m⁴]", float(a.k))
        row(g, "Longitud equivalente Le [m]", float(a.le))
        if a.closed:
            row(g, "Estado", "cerrada")
        if a.fixed_q is not None:
            row(g, "Caudal fijo [m³/s]", float(a.fixed_q))
        if a.saved_Q is not None:
            g = group("Guardado en el archivo (resultado de VentSim)")
            row(g, "R [Ns²/m⁸]", a.saved_R, "f")
            row(g, "Q [m³/s]", a.saved_Q, "f")
            row(g, "Pérdida de presión [Pa]", a.saved_dp, "f")
            row(g, "Presión inicio [Pa]", a.saved_p_from, "f")
            row(g, "Presión fin [Pa]", a.saved_p_to, "f")
            if a.fan_type:
                row(g, "Ventilador (preset)", a.fan_type, "f")
                row(g, "Apagado", "sí" if a.fan_off else "no", "f")
                row(g, "Presión estática ventilador [Pa]", a.saved_fan_static, "f")
        g = group("Calculado por el motor propio")
        if a.calc_Q is None:
            row(g, "Estado", "sin calcular (F5)")
        else:
            row(g, "R [Ns²/m⁸]", a.calc_R, "m")
            row(g, "Origen de R", "calculada desde geometría" if a.r_origin == "motor" else "tomada del archivo", "m")
            row(g, "Q [m³/s]", a.calc_Q, "m")
            row(g, "Pérdida de presión R·Q² [Pa]", abs(a.calc_dp), "m")
            row(g, "Presión inicio [Pa]", a.calc_p_from, "m")
            row(g, "Presión fin [Pa]", a.calc_p_to, "m")
            if a.fan_origin:
                row(g, "Ventilador", {"curva": "por curva (motor)", "archivo": "presión guardada en archivo",
                                      "apagado": "apagado"}[a.fan_origin], "m")
            if a.saved_Q is not None:
                row(g, "ΔQ motor − archivo [m³/s]", a.calc_Q - a.saved_Q, "m")
        if a.props:
            g = group(f"Todas las columnas del archivo ({len(a.props)})")
            g.setExpanded(False)
            for k, v in a.props.items():
                row(g, k, v, "f")

    # ------------------------------------------------------------ selección
    def on_view_selected(self, i: int):
        self._select_row(i)
        self.fill_props(i)
        self.update_callout()
        self.refresh_actions()

    def refresh_actions(self):
        native = self.prj is not None and self.prj.kind == "nativo"
        sel = self.view.sel >= 0
        for a in (self.act_edit, self.act_del, self.act_fan):
            a.setEnabled(native and sel)
        self.act_add.setEnabled(True)
        self.act_center.setEnabled(sel)

    def _select_row(self, i: int):
        if i < 0:
            self.table.clearSelection()
            return
        px = self.proxy.mapFromSource(self.model.index(i, 0))
        self.table.blockSignals(True)
        self.table.selectionModel().blockSignals(True)
        self.table.selectRow(px.row())
        self.table.scrollTo(px, QAbstractItemView.PositionAtCenter)
        self.table.selectionModel().blockSignals(False)
        self.table.blockSignals(False)

    def on_table_row(self, cur, _prev):
        if not cur.isValid():
            return
        i = self.proxy.mapToSource(cur).row()
        self.view.set_selected(i)
        self.fill_props(i)
        self.update_callout()
        self.refresh_actions()

    # ------------------------------------------------------------ exportación
    def export_csv_dialog(self):
        if not self.prj:
            return
        p, _ = QFileDialog.getSaveFileName(self, "Exportar tabla de resultados", f"{Path(self.prj.name).stem}_resultados.csv",
                                           "CSV (*.csv)")
        if p:
            n = export_csv(self.prj, p)
            self.status.setText(f"{n} filas exportadas a {p}")

    def export_png_dialog(self):
        if not self.prj:
            return
        p, _ = QFileDialog.getSaveFileName(self, "Guardar imagen de la vista 3D", f"{Path(self.prj.name).stem}_vista.png",
                                           "Imagen PNG (*.png)")
        if p and self.view.screenshot(p):
            self.status.setText(f"Imagen guardada en {p}")

    # ------------------------------------------------------------ proyecto nativo
    def _invalidate(self):
        p = self.prj
        p.solved = False
        for a in p.airways:
            a.calc_Q = a.calc_R = a.calc_dp = a.calc_p_from = a.calc_p_to = None
            a.r_origin = a.fan_origin = ""
        self.model.set_project(p)
        self.view.set_geometry(np.array([a.p1 for a in p.airways]).reshape(-1, 3) if p.airways else np.zeros((0, 3)),
                               np.array([a.p2 for a in p.airways]).reshape(-1, 3) if p.airways else np.zeros((0, 3)),
                               np.array([max(a.width, 2.0) for a in p.airways]) if p.airways else None)
        self.refresh_all()

    def _need_native(self) -> bool:
        if self.prj is None or self.prj.kind != "nativo":
            QMessageBox.information(self, "Proyecto nativo",
                                    "La edición solo está disponible en proyectos nativos.\n"
                                    "Use «Proyecto nativo › Nuevo» o «Cargar red de demostración».\n"
                                    "(Los archivos .vsm se abren en solo lectura.)")
            return False
        return True

    def new_native_project(self):
        self.set_project(new_native())

    def load_demo(self):
        self.set_project(demo_native())
        self.status.setText("Red de demostración cargada. Pulse F5 (Correr › Escritura de la estática).")

    def add_airway(self):
        if self.prj is None or self.prj.kind != "nativo":
            self.new_native_project()
        start = (0.0, 0.0, 0.0)
        if 0 <= self.view.sel < len(self.prj.airways):
            start = self.prj.airways[self.view.sel].p2
        uid = str(max([int(a.uid) for a in self.prj.airways if a.uid.isdigit()] + [0]) + 1)
        d = AirwayDialog(self, None, start, uid)
        if d.exec() and d.result_airway:
            self.prj.airways.append(d.result_airway)
            self._invalidate()

    def edit_airway(self):
        if not self._need_native() or self.view.sel < 0:
            return
        d = AirwayDialog(self, self.prj.airways[self.view.sel])
        if d.exec() and d.result_airway:
            self.prj.airways[self.view.sel] = d.result_airway
            self._invalidate()

    def delete_airway(self):
        if not self._need_native() or self.view.sel < 0:
            return
        del self.prj.airways[self.view.sel]
        self.view.sel = -1
        self._invalidate()

    def edit_fan(self):
        if not self._need_native() or self.view.sel < 0:
            return
        a = self.prj.airways[self.view.sel]
        d = FanDialog(self, a)
        if d.exec():
            a.fan_curve, a.fan_units = d.points, d.units
            self._invalidate()

    def save_native_dialog(self):
        if not self._need_native():
            return
        p, _ = QFileDialog.getSaveFileName(self, "Guardar proyecto nativo", f"{self.prj.name}.nvs.json", "Proyecto nativo (*.json)")
        if p:
            save_native(self.prj, p)
            self.status.setText(f"Proyecto nativo guardado en {p}")

    # ------------------------------------------------------------ ayuda
    def show_help(self):
        QMessageBox.information(self, "Controles del visor",
                                "Rotar: arrastrar con el botón izquierdo\n"
                                "Desplazar: botón derecho o central (o Mayús + izquierdo)\n"
                                "Zoom: rueda del ratón (o + / −)\n"
                                "Seleccionar galería: clic izquierdo sobre ella\n"
                                "Ajustar vista: doble clic, Inicio o F\n"
                                "Vistas: 1 planta · 2 alzado frontal · 3 alzado lateral · 4 isométrica\n"
                                "Centrar en la selección: C · Etiquetas: T · Rejilla: G · Mapa de color: P\n"
                                "Calcular: F5 · Exportar CSV: Ctrl+E")

    def show_about(self):
        cuadro = QMessageBox(self)
        cuadro.setWindowTitle("Acerca de NVS")
        cuadro.setIconPixmap(imagen("logo-base").scaledToWidth(170, Qt.SmoothTransformation))
        cuadro.setText(f"<b>NVS {__version__}</b> · Noova Ventilation System<br>Reconstrucción funcional independiente de un "
                       "simulador de ventilación de minas. Código propio; <b>no es un producto de Ventsim ni de Howden</b>.<br><br>"
                       "Los resultados «archivo» se leen de proyectos .vsm (solo lectura); los «motor» los calcula este "
                       "programa. No se declara equivalencia total: ver INFORME.md.")
        cuadro.exec()
