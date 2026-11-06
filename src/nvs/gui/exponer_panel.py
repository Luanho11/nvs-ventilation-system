"""Panel flotante «Exponer»: umbrales y colores de la magnitud mostrada (estructura observada en docs/evidence/E-004).

Cabecera con cierre, deslizador de transparencia, 7 pestañas, campos de umbral, deslizador vertical de rango,
«Opciones de» y leyenda de 8 colores.  Todo cambio modifica de verdad la escala (`ColorScale`) que usa el visor;
lo que la referencia tiene y aquí no se implementa queda deshabilitado con el tooltip «pendiente».
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDoubleValidator, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLayout, QLineEdit,
                               QPushButton, QSlider, QToolButton, QVBoxLayout, QWidget)

from .chrome import PENDING_TIP
from .colorscale import ColorScale
from .icons import icon

ANCHO = 222
MS_AGRUPAR = 40          # los cambios de la escala se avisan como máximo cada 40 ms mientras se arrastra el medidor
PESTANAS_ACTIVAS = {0: "Escala numérica del dato mostrado", 2: "Tipo de aire", 3: "Capa primaria", 5: "Capas de referencia (terreno)"}
PESTANAS = ("paleta", "pestana_lista", "pestana_cubo", "capa_1", "capa_2", "referencias", "pestana_ventana")


class _Rango(QWidget):
    """Deslizador vertical con dos marcadores: el negro fija el umbral máximo y el azul el mínimo."""
    cambio = Signal(float, float)          # fracciones 0..1 (alto, bajo)

    def __init__(self):
        super().__init__()
        self.setFixedSize(22, 127)
        self.alto, self.bajo = 1.0, 0.0
        self._arrastre = None

    def _y(self, f: float) -> float:
        return 6 + (1.0 - f) * (self.height() - 12)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#a8a8a8"), 1))
        p.setBrush(QColor("#e4e4e4"))
        p.drawRect(QRectF(9, 6, 6, self.height() - 12))
        p.setPen(QColor("#888888"))
        for k in range(1, 10):
            y = 6 + k * (self.height() - 12) / 10
            p.drawLine(QPoint(3, int(y)), QPoint(6, int(y)))
        for f, col in ((self.alto, "#1a1a1a"), (self.bajo, "#1f7fd8")):
            y = self._y(f)
            p.setPen(QPen(QColor("#202020"), 1))
            p.setBrush(QColor(col))
            p.drawPolygon(QPolygonF([QPoint(22, int(y)), QPoint(14, int(y) - 5), QPoint(1, int(y) - 5),
                                     QPoint(1, int(y) + 5), QPoint(14, int(y) + 5)]))

    def mousePressEvent(self, ev):
        y = ev.position().y()
        self._arrastre = "alto" if abs(y - self._y(self.alto)) <= abs(y - self._y(self.bajo)) else "bajo"
        self.mouseMoveEvent(ev)

    def mouseMoveEvent(self, ev):
        if self._arrastre is None:
            return
        f = min(max(1.0 - (ev.position().y() - 6) / (self.height() - 12), 0.0), 1.0)
        if self._arrastre == "alto":
            self.alto = max(f, self.bajo + 0.02)
        else:
            self.bajo = min(f, self.alto - 0.02)
        self.update()
        self.cambio.emit(self.alto, self.bajo)

    def mouseReleaseEvent(self, _ev):
        self._arrastre = None


class _Muestra(QPushButton):
    def __init__(self, color: str):
        super().__init__()
        self.setFixedSize(26, 17)
        self.setCursor(Qt.PointingHandCursor)
        self.pintar(color)

    def pintar(self, color: str):
        self.setStyleSheet(f"QPushButton{{background:{color};border:none;}}")


class PanelExponer(QFrame):
    changed = Signal()                 # la escala se modificó
    autoescala = Signal()
    transparencia = Signal(float)      # 0 (opaco) .. 1 (transparente)
    closed = Signal()
    pestana = Signal(int)              # pestaña elegida (0 = escala numérica; 2 = tipo de aire; 3 = capa primaria; 5 = referencias)
    categorias = Signal(list)          # visibilidad de cada categoría (True/False)
    ocultar_bajo = Signal(bool)        # ocultar los datos por debajo del marcador azul (recursos de Ventsim: chkHideRange)

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("exponer")
        self.setFixedWidth(ANCHO)
        self.setStyleSheet("QFrame#exponer{background:#eceff4;border:1px solid #9fb0c8;}"
                           "QLabel#titulo{color:#8a8a8a;font-size:10pt;}"
                           "QLabel#valor{background:#f4f4f4;border:1px solid #6e6e6e;color:#1f5fbf;padding:0 3px;}"
                           "QLineEdit{background:#ffffff;border:none;border-bottom:1px solid #6e6e6e;padding:1px 4px;}"
                           "QGroupBox{border:1px solid #c4c4c4;margin-top:9px;padding-top:4px;}"
                           "QGroupBox::title{subcontrol-origin:margin;left:8px;padding:0 3px;font-size:10pt;}")
        self.scale: ColorScale | None = None
        self._campos: list[QLineEdit] = []
        self._muestras: list[_Muestra] = []
        self._valores: list[QLabel] = []
        self._ocupado = False
        self._aviso = QTimer(self)
        self._aviso.setSingleShot(True)
        self._aviso.setInterval(MS_AGRUPAR)
        self._aviso.timeout.connect(self.changed.emit)
        self.movido = False
        self._arrastre: QPoint | None = None
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(7, 5, 7, 7)
        raiz.setSizeConstraint(QLayout.SetFixedSize)
        raiz.setSpacing(4)

        cab = QHBoxLayout()
        self.titulo = QLabel("Exponer")
        self.titulo.setObjectName("titulo")
        cerrar = QToolButton()
        cerrar.setIcon(icon("cerrar", 18))
        cerrar.setAutoRaise(True)
        cerrar.clicked.connect(self._cerrar)
        cab.addWidget(self.titulo, 1)
        cab.addWidget(cerrar)
        raiz.addLayout(cab)

        fila = QHBoxLayout()
        lab = QLabel()
        lab.setPixmap(icon("transparencia", 24).pixmap(24, 24))
        self.deslizador = QSlider(Qt.Horizontal)
        self.deslizador.setRange(0, 100)
        self.deslizador.setValue(27)          # posición por defecto observada en Ventsim (≈27 %)
        self.deslizador.setToolTip("Transparencia de las superficies de referencia (función inferida del icono)")
        self.deslizador.valueChanged.connect(lambda v: self.transparencia.emit(v / 100.0))
        fila.addWidget(lab)
        fila.addWidget(self.deslizador, 1)
        raiz.addLayout(fila)

        tabs = QHBoxLayout()
        tabs.setSpacing(0)
        self._pestanas: dict[int, QToolButton] = {}
        for i, nombre in enumerate(PESTANAS):
            b = QToolButton()
            b.setIcon(icon(nombre, 22))
            b.setIconSize(QSize(22, 22))
            b.setFixedSize(28, 28)
            b.setCheckable(True)
            b.setChecked(i == 0)
            if i in PESTANAS_ACTIVAS:
                b.setToolTip(PESTANAS_ACTIVAS[i])
                b.clicked.connect(lambda _c=False, k=i: self.pestana.emit(k))
            else:
                b.setEnabled(False)
                b.setToolTip(PENDING_TIP)
            self._pestanas[i] = b
            tabs.addWidget(b)
        tabs.addStretch(1)
        raiz.addLayout(tabs)

        self.pagina_num = QWidget()
        pn = QVBoxLayout(self.pagina_num)
        pn.setContentsMargins(0, 0, 0, 0)
        pn.setSpacing(4)
        self.etiqueta = QLabel()
        self.etiqueta.setStyleSheet("font-size:10pt;")
        pn.addWidget(self.etiqueta)
        medio = QHBoxLayout()
        self.campos_host = QWidget()
        self.campos = QVBoxLayout(self.campos_host)
        self.campos.setContentsMargins(0, 0, 0, 0)
        self.campos.setSpacing(0)
        medio.addWidget(self.campos_host, 1)
        lado = QVBoxLayout()
        self.rango = _Rango()
        self.rango.cambio.connect(self._rango)
        self.casilla = QPushButton()
        self.casilla.setCheckable(True)
        self.casilla.setFixedSize(18, 18)
        self.casilla.setToolTip("Ocultar datos por debajo de la barra deslizante")
        self.casilla.toggled.connect(self.ocultar_bajo.emit)
        lado.addWidget(self.rango)
        lado.addWidget(self.casilla, 0, Qt.AlignHCenter)
        medio.addLayout(lado)
        pn.addLayout(medio)

        grupo = QGroupBox("Opciones de")
        gl = QHBoxLayout(grupo)
        gl.setContentsMargins(4, 6, 4, 4)
        gl.setSpacing(0)
        for nombre, tip, fn in (("orden_asc", "Restaurar los umbrales y colores por defecto", self._restaurar),
                                ("orden_desc", "Invertir la paleta", self._invertir),
                                ("rueda_color", "Escala de color pendiente: edite cada color en la leyenda", None),
                                ("mosaico", "Escala automática según los datos", self.autoescala.emit)):
            b = QToolButton()
            b.setIcon(icon(nombre, 22))
            b.setIconSize(QSize(22, 22))
            b.setFixedSize(28, 28)
            b.setToolTip(tip)
            if fn is None:
                b.setEnabled(False)
            else:
                b.clicked.connect(fn)
            gl.addWidget(b)
        gl.addStretch(1)
        pn.addWidget(grupo)

        self.leyenda_host = QWidget()
        self.leyenda = QGridLayout(self.leyenda_host)
        self.leyenda.setContentsMargins(0, 0, 0, 0)
        self.leyenda.setSpacing(0)
        pn.addWidget(self.leyenda_host)
        self.unidad = QLabel()
        self.unidad.setStyleSheet("font-size:7pt;")
        self.unidad.setAlignment(Qt.AlignRight)
        pn.addWidget(self.unidad)
        raiz.addWidget(self.pagina_num)

        self.pagina_cat = QWidget()
        pc = QVBoxLayout(self.pagina_cat)
        pc.setContentsMargins(0, 2, 0, 0)
        pc.setSpacing(3)
        barra = QHBoxLayout()
        barra.setContentsMargins(4, 0, 0, 0)
        for nombre, tip, valor in (("bombilla_on", "Mostrar todo", True), ("bombilla_off", "Ocultar todo", False)):
            b = QToolButton()
            b.setIcon(icon(nombre, 22))
            b.setIconSize(QSize(22, 22))
            b.setFixedSize(28, 28)
            b.setToolTip(tip)
            b.clicked.connect(lambda _c=False, v=valor: self._todas(v))
            barra.addWidget(b)
        barra.addStretch(1)
        pc.addLayout(barra)
        self.lista_cat = QVBoxLayout()
        self.lista_cat.setSpacing(1)
        pc.addLayout(self.lista_cat)
        self._casillas: list[QCheckBox] = []
        self.pagina_cat.hide()
        raiz.addWidget(self.pagina_cat)

    def set_scale(self, scale: ColorScale):
        misma_forma = (self.scale is not None and len(self.scale.thresholds) == len(scale.thresholds)
                       and len(self._campos) == len(scale.thresholds))
        self.scale = scale
        self.etiqueta.setText(f"{scale.title} {scale.unit}")
        self.unidad.setText(scale.unit)
        self._refrescar() if misma_forma else self._reconstruir()

    def set_categorias(self, nombres: list[str], colores: list[str], visibles: list[bool]):
        """Lista de categorías con casilla y color (tipo de aire): cada casilla muestra u oculta esa categoría."""
        while self.lista_cat.count():
            w = self.lista_cat.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._casillas = []
        for k, (n, c) in enumerate(zip(nombres, colores)):
            fila = QWidget()
            fl = QHBoxLayout(fila)
            fl.setContentsMargins(4, 0, 0, 0)
            fl.setSpacing(4)
            cb = QCheckBox()
            cb.setChecked(visibles[k])
            cb.toggled.connect(lambda _v, i=k: self._cambio_categoria())
            claro = QColor(c).lightness() > 150
            et = QLabel(n)
            et.setFixedHeight(20)
            et.setStyleSheet(f"background:{c};color:{'#000000' if claro else '#ffffff'};padding-left:5px;")
            fl.addWidget(cb)
            fl.addWidget(et, 1)
            self.lista_cat.addWidget(fila)
            self._casillas.append(cb)
        self.layout().activate()

    def _cambio_categoria(self):
        self._avisar_categorias()

    def _avisar_categorias(self):
        self.categorias.emit([c.isChecked() for c in self._casillas])

    def _todas(self, valor: bool):
        for c in self._casillas:
            c.blockSignals(True)
            c.setChecked(valor)
            c.blockSignals(False)
        self._avisar_categorias()

    def mostrar_pestana(self, k: int):
        """Pestaña activa: 0 = escala numérica; las demás muestran su lista de categorías con casillas."""
        self.pagina_cat.setVisible(k != 0)
        self.pagina_num.setVisible(k == 0)
        for i, b in self._pestanas.items():
            b.setChecked(i == k)
        self.layout().activate()

    def _refrescar(self):
        """Actualiza textos y colores sin destruir widgets (se llama mientras se arrastra el medidor)."""
        sc = self.scale
        self._ocupado = True
        try:
            for fila, e in enumerate(self._campos):
                if not e.hasFocus():
                    e.setText(f"{sc.thresholds[len(sc.thresholds) - 1 - fila]:.1f}")
            for (color, texto), muestra, valor in zip(sc.legend(), self._muestras, self._valores):
                muestra.pintar(color)
                valor.setText(texto)
        finally:
            self._ocupado = False

    def _avisar(self):
        """La escala cambió: se avisa al visor una vez por intervalo, no una vez por evento de ratón."""
        if not self._aviso.isActive():
            self._aviso.start()

    def _reconstruir(self):
        self._campos, self._muestras, self._valores = [], [], []
        for lay in (self.campos, self.leyenda):
            while lay.count():
                w = lay.takeAt(0).widget()
                if w is not None:
                    w.setParent(None)
                    w.deleteLater()
        sc = self.scale
        for j in range(len(sc.thresholds) - 1, -1, -1):
            e = QLineEdit(f"{sc.thresholds[j]:.1f}")
            e.setValidator(QDoubleValidator(-1e9, 1e9, 6, e))
            e.setAlignment(Qt.AlignRight)
            e.editingFinished.connect(lambda k=j, w=e: self._editar(k, w.text()))
            self.campos.addWidget(e)
            self._campos.append(e)
        for fila, (color, texto) in enumerate(sc.legend()):
            m = _Muestra(color)
            k = len(sc.colors) - 1 - fila
            m.clicked.connect(lambda _c=False, i=k, w=m: self._elegir(i, w))
            v = QLabel(texto)
            v.setObjectName("valor")
            v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            v.setFixedHeight(17)
            self.leyenda.addWidget(m, fila, 0)
            self.leyenda.addWidget(v, fila, 1)
            self._muestras.append(m)
            self._valores.append(v)
        self.leyenda.setColumnStretch(1, 1)
        self.layout().activate()

    def _elegir(self, k: int, muestra: _Muestra):
        c = QColorDialog.getColor(QColor(self.scale.colors[k]), self, "Color")
        if c.isValid():
            self.scale.colors[k] = c.name()
            muestra.pintar(c.name())
            self._avisar()

    def _editar(self, j: int, texto: str):
        if self._ocupado or self.scale is None:
            return
        try:
            v = float(texto.replace(",", "."))
        except ValueError:
            return
        if abs(self.scale.thresholds[j] - v) < 1e-12:
            return
        antes = list(self.scale.thresholds)
        self.scale.set_threshold(j, v)
        if self.scale.thresholds != antes:
            self._refrescar()
            self._avisar()

    def _rango(self, alto: float, bajo: float):
        """Marcador negro = umbral máximo (escala logarítmica 1…10 000); azul = mínimo (fracción del máximo).
        Los umbrales intermedios conservan su posición relativa respecto a los valores por defecto."""
        if self.scale is None:
            return
        base = self.scale.base_thresholds
        tope = 10 ** (alto * 4)
        piso = bajo * tope
        ancho = base[-1] - base[0]
        self.scale.thresholds = [piso + (t - base[0]) / ancho * (tope - piso) for t in base]
        self._refrescar()
        self._avisar()

    def _restaurar(self):
        self.scale.reset()
        self._refrescar()
        self._avisar()

    def _invertir(self):
        self.scale.colors.reverse()
        self._refrescar()
        self._avisar()

    def _cerrar(self):
        self.hide()
        self.closed.emit()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton and ev.position().y() < 28:
            self._arrastre = ev.globalPosition().toPoint() - self.pos()
        else:
            super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if self._arrastre is None:
            return super().mouseMoveEvent(ev)
        self.movido = True
        p = ev.globalPosition().toPoint() - self._arrastre
        host = self.parentWidget()
        self.move(max(0, min(p.x(), host.width() - self.width())), max(0, min(p.y(), host.height() - self.height())))

    def mouseReleaseEvent(self, ev):
        if self._arrastre is None:
            return super().mouseReleaseEvent(ev)
        self._arrastre = None
