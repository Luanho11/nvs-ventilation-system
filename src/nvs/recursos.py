"""Acceso a los datos empaquetados con la aplicación (`src/nvs/data`), tanto en el código fuente como en el .exe."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

DATOS = Path(__file__).resolve().parent / "data"
TAMANOS_ICONO = (16, 24, 32, 48, 64, 128, 256)


def imagen(nombre: str) -> QPixmap:
    """Logotipo de `data/img` (logo-software, logo-base o logo-loader-blanco)."""
    return QPixmap(str(DATOS / "img" / f"{nombre}.png"))


def icono_aplicacion() -> QIcon:
    logo = imagen("logo-software")
    icono = QIcon()
    for lado in TAMANOS_ICONO:
        icono.addPixmap(logo.scaled(lado, lado, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    return icono
