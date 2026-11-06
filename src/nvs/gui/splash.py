"""Pantalla de carga: se muestra al arrancar mientras se prepara la ventana y se lee el ejemplo inicial.

Disposición tomada de la pantalla de inicio de la referencia (`ref/loader-ventsim.png`, 518×388): fondo pizarra con degradado,
logotipo a la izquierda, título y datos a la derecha separados por líneas blancas, versión y créditos abajo y el logotipo
de la empresa en la esquina inferior derecha. Los logotipos son los entregados por Noova (`data/img`); la barra de
progreso es real (cada paso lo anuncia quien carga)."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

from .. import __version__
from ..recursos import imagen

ANCHO, ALTO = 518, 388
COLUMNA_DERECHA = 272


class PantallaCarga(QWidget):
    def __init__(self):
        super().__init__(None, Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(ANCHO, ALTO)
        self.texto = "Iniciando…"
        self.avance = 0
        blanco = imagen("logo-loader-blanco")
        self.logo_blanco = blanco.copy(blanco.toImage().rect().adjusted(40, 14, -46, -16))
        self.logo_software = imagen("logo-software")
        pantalla = QApplication.primaryScreen().availableGeometry()
        self.move(pantalla.center().x() - ANCHO // 2, pantalla.center().y() - ALTO // 2)

    def paso(self, texto: str, porcentaje: int):
        self.texto, self.avance = texto, porcentaje
        self.repaint()
        QApplication.processEvents()

    @staticmethod
    def _texto(p: QPainter, x: float, y: float, w: float, texto: str, px: int, negrita=False, color="#ffffff",
               alinear=Qt.AlignLeft):
        fuente = QFont("Arial")
        fuente.setPixelSize(px)
        fuente.setBold(negrita)
        p.setFont(fuente)
        p.setPen(QColor(color))
        p.drawText(QRectF(x, y, w, px * 1.5), alinear | Qt.AlignVCenter, texto)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        fondo = QLinearGradient(0, 0, 0, ALTO)
        fondo.setColorAt(0, QColor("#34444f"))
        fondo.setColorAt(1, QColor("#111c26"))
        p.fillRect(self.rect(), fondo)

        p.drawPixmap(30, 76, self.logo_blanco.scaledToWidth(212, Qt.SmoothTransformation))

        x = COLUMNA_DERECHA + 3
        self._texto(p, x, 28, 240, "NVS", 30, negrita=True)
        self._texto(p, x + 1, 76, 240, "Noova Ventilation System", 15, negrita=True)
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.drawLine(x + 2, 148, ANCHO, 148)
        self._texto(p, x, 172, 240, "Compañía", 13, negrita=True)
        self._texto(p, x, 196, 240, "Noova Consulting", 13, color="#e0e8ee")
        self._texto(p, x, 226, 240, "Estado", 13, negrita=True)
        self._texto(p, x, 250, 240, self.texto, 13, color="#e0e8ee")
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.drawLine(x + 2, 280, ANCHO, 280)

        self._texto(p, 0, 262, COLUMNA_DERECHA, f"Versión {__version__} : 64 bit", 15, negrita=True, alinear=Qt.AlignHCenter)
        self._texto(p, 0, 300, COLUMNA_DERECHA, "Reconstrucción funcional independiente", 12, alinear=Qt.AlignHCenter)
        self._texto(p, 0, 322, COLUMNA_DERECHA, "Interfaz basada en Ventsim DESIGN 6.0", 12, alinear=Qt.AlignHCenter)
        self._texto(p, 14, 348, ANCHO - 28, "© Noova Consulting 2026. No es un producto de Ventsim ni de Howden.", 11)

        sello = self.logo_software.scaled(92, 92, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        p.drawPixmap(ANCHO - 92 - 36, 288, sello)

        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#0b141c"))
        p.drawRect(QRectF(0, ALTO - 6, ANCHO, 6))
        p.setBrush(QColor("#19b8d6"))
        p.drawRect(QRectF(0, ALTO - 6, ANCHO * self.avance / 100, 6))
