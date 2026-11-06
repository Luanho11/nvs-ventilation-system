"""Filtro global de excepciones: toda excepción no capturada se registra en un archivo y la persona ve, como mucho, UNA alerta.

Sin esto, una excepción repetida en un evento de ratón o de pintura (decenas por segundo) abriría una alerta por evento y
dejaría la aplicación inutilizable."""
from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

RUTA_REGISTRO = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "NVS" / "errores.log"


class FiltroErrores:
    def __init__(self, ruta: Path = RUTA_REGISTRO):
        self.ruta = ruta
        self.cantidad = 0
        self.avisado = False

    def __call__(self, tipo, valor, traza) -> None:
        self.cantidad += 1
        texto = "".join(traceback.format_exception(tipo, valor, traza))
        try:
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
            with self.ruta.open("a", encoding="utf-8") as f:
                f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} (error {self.cantidad})\n{texto}\n")
        except OSError:
            pass
        if not self.avisado:
            self.avisado = True
            self._avisar_una_vez(valor)

    def _avisar_una_vez(self, valor) -> None:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication, QMessageBox

        def mostrar():
            if QApplication.instance() is not None:
                QMessageBox.warning(None, "NVS", f"Ocurrió un error interno: {valor}\n\nEl detalle se guardó en:\n{self.ruta}\n"
                                    "La aplicación sigue funcionando; los errores siguientes solo se registran.")
        QTimer.singleShot(0, mostrar)


def instalar() -> FiltroErrores:
    filtro = FiltroErrores()
    sys.excepthook = filtro
    return filtro
