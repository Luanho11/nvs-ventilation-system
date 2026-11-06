"""Diálogos de edición del proyecto nativo."""
from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QLabel, QLineEdit, QPlainTextEdit, QSpinBox, QVBoxLayout)

from ..project import Airway, make_rect_airway

# Valores k de referencia (N·s²/m⁴ a 1,2 kg/m³) observados en los presets de los proyectos de ejemplo.
K_PRESETS = [("Tuberías lisas", 0.0025), ("Conducto flexible", 0.0029), ("Hormigón", 0.0033),
             ("Chimenea perforada", 0.005), ("Voladura suave", 0.0083), ("Voladura media", 0.01),
             ("Voladura rugosa", 0.015), ("Voladura muy rugosa", 0.0208), ("Entibado", 0.0333),
             ("Pozo con cuadros de hormigón", 0.0417)]


def _spin(lo=-1e6, hi=1e6, val=0.0, dec=3):
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(dec)
    s.setValue(val)
    s.setSingleStep(1.0)
    return s


class AirwayDialog(QDialog):
    def __init__(self, parent, airway: Airway | None, default_start=(0.0, 0.0, 0.0), next_uid="1"):
        super().__init__(parent)
        self.setWindowTitle("Galería" if airway is None else f"Editar galería {airway.uid}")
        self._uid = airway.uid if airway else next_uid
        lay = QFormLayout(self)
        self.name = QLineEdit(airway.name if airway else "")
        lay.addRow("Nombre", self.name)
        p1 = airway.p1 if airway else default_start
        p2 = airway.p2 if airway else (default_start[0] + 100, default_start[1], default_start[2])
        self.c1 = [_spin(val=v) for v in p1]
        self.c2 = [_spin(val=v) for v in p2]
        lay.addRow("Inicio X, Y, Z [m]", self._row(self.c1))
        lay.addRow("Fin X, Y, Z [m]", self._row(self.c2))
        self.shape = QComboBox()
        self.shape.addItems(["Rectangular (ancho × alto)", "Circular (diámetro = ancho)"])
        if airway and abs(airway.perimeter - 3.14159265 * airway.width) < 1e-6 and airway.width == airway.height:
            self.shape.setCurrentIndex(1)
        lay.addRow("Sección", self.shape)
        self.w = _spin(0.1, 200, airway.width if airway else 4.0, 2)
        self.h = _spin(0.1, 200, airway.height if airway else 4.0, 2)
        lay.addRow("Ancho / diámetro [m]", self.w)
        lay.addRow("Alto [m]", self.h)
        self.kpre = QComboBox()
        self.kpre.addItem("— personalizado —", None)
        for n, v in K_PRESETS:
            self.kpre.addItem(f"{n}  ({v})", v)
        self.k = _spin(0.0001, 1, airway.k if airway else 0.01, 5)
        self.kpre.currentIndexChanged.connect(lambda _i: self.kpre.currentData() is not None and
                                              self.k.setValue(self.kpre.currentData()))
        lay.addRow("Preset de fricción", self.kpre)
        lay.addRow("k de Atkinson [N·s²/m⁴]", self.k)
        self.le = _spin(0, 5000, airway.le if airway else 0.0, 1)
        lay.addRow("Longitud equivalente por choques Le [m]", self.le)
        self.closed = QCheckBox("Galería cerrada (Q = 0)")
        self.closed.setChecked(bool(airway and airway.closed))
        lay.addRow(self.closed)
        self.fixed = QCheckBox("Caudal fijo")
        self.fixed.setChecked(bool(airway and airway.fixed_q is not None))
        self.fixedq = _spin(-1e5, 1e5, airway.fixed_q if airway and airway.fixed_q is not None else 10.0, 3)
        lay.addRow(self.fixed)
        lay.addRow("Caudal fijo [m³/s] (sentido inicio→fin)", self.fixedq)
        lay.addRow(QLabel("Longitud = distancia entre extremos. Nodos: extremos coincidentes en 0,01 m.\n"
                          "Los nodos de grado 1 son bocas a presión de referencia (0 Pa)."))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addRow(bb)
        self._src = airway
        self.result_airway: Airway | None = None

    @staticmethod
    def _row(spins):
        from PySide6.QtWidgets import QHBoxLayout, QWidget
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        for s in spins:
            h.addWidget(s)
        return w

    def _ok(self):
        p1 = tuple(s.value() for s in self.c1)
        p2 = tuple(s.value() for s in self.c2)
        if p1 == p2:
            self.setWindowTitle("Los extremos no pueden coincidir")
            return
        a = make_rect_airway(self._uid, self.name.text(), p1, p2, self.w.value(), self.h.value(), self.k.value(),
                             self.le.value(), "circle" if self.shape.currentIndex() == 1 else "rect")
        a.closed = self.closed.isChecked()
        a.fixed_q = self.fixedq.value() if self.fixed.isChecked() and not a.closed else None
        if self._src is not None:
            a.fan_curve, a.fan_units = self._src.fan_curve, self._src.fan_units
        self.result_airway = a
        self.accept()


class FanDialog(QDialog):
    def __init__(self, parent, airway: Airway):
        super().__init__(parent)
        self.setWindowTitle(f"Ventilador de la galería {airway.uid}")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Curva de presión estática por ventilador: una línea «Q, P» por punto\n"
                             "(Q en m³/s creciente, P en Pa). Interpolación lineal, como en los archivos observados."))
        self.txt = QPlainTextEdit()
        pts = airway.fan_curve or [(20, 1200), (40, 1000), (60, 700), (80, 300), (100, 0)]
        self.txt.setPlainText("\n".join(f"{q:g}, {p:g}" for q, p in pts))
        lay.addWidget(self.txt)
        self.n = QSpinBox()
        self.n.setRange(1, 20)
        self.n.setValue(airway.fan_units)
        f = QFormLayout()
        f.addRow("Ventiladores idénticos en paralelo", self.n)
        lay.addLayout(f)
        self.remove = QCheckBox("Quitar el ventilador de esta galería")
        lay.addWidget(self.remove)
        self.err = QLabel("")
        lay.addWidget(self.err)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.points = None
        self.units = 1

    def _ok(self):
        if self.remove.isChecked():
            self.points, self.units = None, 1
            return self.accept()
        pts = []
        try:
            for ln in self.txt.toPlainText().splitlines():
                if ln.strip():
                    q, p = ln.replace(";", ",").split(",")
                    pts.append((float(q), float(p)))
            if len(pts) < 2 or any(b[0] <= a[0] for a, b in zip(pts, pts[1:])):
                raise ValueError("Se necesitan ≥ 2 puntos con Q estrictamente creciente")
            if any(b[1] > a[1] for a, b in zip(pts, pts[1:])):
                raise ValueError("La presión debe ser no creciente con Q (curva estable)")
        except Exception as e:  # noqa: BLE001
            self.err.setText(f"Error: {e}")
            return
        self.points, self.units = pts, self.n.value()
        self.accept()
