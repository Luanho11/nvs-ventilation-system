"""Tema visual: aspecto clásico de Windows (WinForms) observado en la referencia, fondo #f0f0f0, Segoe UI 9 pt,
botones planos que se marcan con borde azul y campos blancos con borde gris (docs/evidence/E-004)."""
from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPen, QPixmap

BG = "#f0f0f0"
FILE_BLUE = "#2f6fdc"
ENGINE_GREEN = "#1b9e57"
MARCA = "#2e8bd8"
MARCA_FONDO = "#cde6f7"

QSS = f"""
* {{ font-family: 'Segoe UI'; font-size: 9pt; }}
QMainWindow, QDialog {{ background: {BG}; }}

QMenuBar {{ background: {BG}; padding: 1px 0; }}
QMenuBar::item {{ padding: 4px 6px; background: transparent; }}
QMenuBar::item:selected {{ background: {MARCA_FONDO}; border: 1px solid #8fbfe6; padding: 3px 5px; }}
QMenu {{ background: #ffffff; border: 1px solid #979797; padding: 2px; }}
QMenu::item {{ padding: 4px 26px 4px 22px; }}
QMenu::item:selected {{ background: {MARCA_FONDO}; border: 1px solid #8fbfe6; padding: 3px 25px 3px 21px; }}
QMenu::item:disabled {{ color: #9a9a9a; }}
QMenu::separator {{ height: 1px; background: #d0d0d0; margin: 3px 2px 3px 24px; }}

QToolBar {{ background: {BG}; border: none; spacing: 0; padding: 1px 2px; }}
QToolBar::separator {{ background: #a0a0a0; width: 1px; margin: 2px 3px; }}
QToolButton {{ background: transparent; border: 1px solid transparent; padding: 1px; }}
QToolButton:hover {{ background: #e3f1fb; border-color: #9cc9ec; }}
QToolButton:pressed, QToolButton:checked {{ background: {MARCA_FONDO}; border-color: {MARCA}; }}
QToolButton:disabled {{ background: transparent; border-color: transparent; }}

QComboBox {{ background: #ffffff; border: 1px solid #acacac; padding: 1px 3px; min-height: 18px; }}
QComboBox:hover {{ border-color: #7eb4ea; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{ background: #ffffff; border: 1px solid #979797; selection-background-color: {MARCA_FONDO};
    selection-color: #000000; outline: 0; }}

QDockWidget {{ font-weight: normal; }}
QDockWidget::title {{ background: #dfe6ef; border: 1px solid #a9b4c4; padding: 3px 6px; }}
QTabWidget::pane {{ border: 1px solid #a9b4c4; background: #ffffff; }}
QTabBar::tab {{ background: #e8e8e8; border: 1px solid #a9b4c4; border-bottom: none; padding: 3px 12px; margin-right: 1px; }}
QTabBar::tab:selected {{ background: #ffffff; }}

QTreeWidget, QTableView, QTextBrowser {{ background: #ffffff; border: 1px solid #a9b4c4; alternate-background-color: #f4f7fb;
    gridline-color: #e0e0e0; selection-background-color: {MARCA_FONDO}; selection-color: #000000; outline: 0; }}
QHeaderView::section {{ background: #f0f0f0; border: none; border-right: 1px solid #d0d0d0; border-bottom: 1px solid #b4b4b4;
    padding: 3px 6px; }}

QStatusBar {{ background: {BG}; }}
QStatusBar::item {{ border: none; }}

QLineEdit, QPlainTextEdit {{ background: #ffffff; border: 1px solid #acacac; padding: 1px 3px; }}
QLineEdit:focus, QPlainTextEdit:focus {{ border-color: {MARCA}; }}
QToolTip {{ background: #ffffe1; color: #000000; border: 1px solid #767676; padding: 2px 4px; }}
"""


def _chevron() -> str:
    """Flecha de las listas desplegables (QSS solo admite imágenes de archivo): se genera una vez en la carpeta temporal."""
    ruta = Path(tempfile.gettempdir()) / "nvs_chevron.png"
    if not ruta.exists():
        pm = QPixmap(9, 6)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#404040"), 1.5))
        p.drawPolyline([QPointF(1, 1), QPointF(4.5, 4.5), QPointF(8, 1)])
        p.end()
        pm.save(str(ruta))
    return ruta.as_posix()


def apply_theme(app) -> None:
    app.setStyle("windowsvista")
    f = QFont("Segoe UI", 9)
    f.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(f)
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(BG))
    pal.setColor(QPalette.Base, QColor("#ffffff"))
    pal.setColor(QPalette.Highlight, QColor(MARCA_FONDO))
    pal.setColor(QPalette.HighlightedText, QColor("#000000"))
    app.setPalette(pal)
    app.setStyleSheet(QSS + f"QComboBox::down-arrow {{ image: url({_chevron()}); width: 9px; height: 6px; }}")
