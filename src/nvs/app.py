"""Punto de entrada de la aplicación de escritorio.

Uso:
    NVS.exe [proyecto.vsm]
    NVS.exe --selftest CARPETA_SALIDA [proyecto.vsm]   # carga, calcula, renderiza a PNG y exporta CSV; sale con 0/1
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _qt_setup():
    """Formato OpenGL por defecto (profundidad + MSAA ×4) y OpenGL de escritorio; debe ir antes de QApplication."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QSurfaceFormat
    from PySide6.QtWidgets import QApplication

    from .gui.viewport import default_format
    QSurfaceFormat.setDefaultFormat(default_format())
    QApplication.setAttribute(Qt.AA_UseDesktopOpenGL, True)


def _shot(app, w, path: Path, view_only: bool = False) -> None:
    """Captura lo que se ve en pantalla. `QWidget.grab()` no incluye las superposiciones (QPainter) de un QOpenGLWidget,
    así que con GPU se captura el framebuffer del visor o la ventana desde el escritorio."""
    from PySide6.QtTest import QTest
    QTest.qWait(250)
    app.processEvents()
    if view_only:
        img = w.view.grabFramebuffer() if hasattr(w.view, "grabFramebuffer") and w.view.render_mode() == "gpu" else w.view.grab().toImage()
        img.save(str(path))
        return
    if w.view.render_mode() == "gpu":
        w.raise_()
        w.activateWindow()
        QTest.qWait(250)
        pm = app.primaryScreen().grabWindow(int(w.winId()))
        if not pm.isNull() and pm.save(str(path)):
            return
    w.grab().save(str(path))


def _selftest(outdir: Path, path: Path | None) -> int:
    from PySide6.QtWidgets import QApplication

    from .export import export_csv
    from .gui.main_window import EXAMPLES_DIR, MainWindow
    from .project import comparison_stats, demo_native, load_vsm

    _qt_setup()
    app = QApplication.instance() or QApplication(sys.argv)
    from .gui.theme import apply_theme
    apply_theme(app)
    outdir.mkdir(parents=True, exist_ok=True)
    w = MainWindow()
    w.show()
    app.processEvents()
    report: dict = {"ok": False}
    try:
        if path is None:
            cand = EXAMPLES_DIR / "DemoMine.vsm"
            path = cand if cand.exists() else None
        prj = load_vsm(path) if path else demo_native()
        w.set_project(prj)
        info = w.solve_sync()
        app.processEvents()
        w.resize(1500, 900)
        app.processEvents()
        _shot(app, w, outdir / "vista3d.png", view_only=True)
        _shot(app, w, outdir / "ventana.png")
        # selección programática: la galería con mayor caudal
        best = max(range(len(prj.airways)), key=lambda i: abs(prj.airways[i].calc_Q or 0))
        w.view.set_selected(best)
        w.on_view_selected(best)
        _shot(app, w, outdir / "ventana_seleccion.png")
        n = export_csv(prj, outdir / "resultados.csv")
        report.update(ok=True, render=w.view.render_mode(), proyecto=prj.name, galerias=len(prj.airways), csv_filas=n, solver=info,
                      comparacion=comparison_stats(prj))
    except Exception as e:  # noqa: BLE001
        import traceback
        report["error"] = f"{type(e).__name__}: {e}"
        report["trace"] = traceback.format_exc()
    (outdir / "selftest.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(json.dumps(report, default=str)[:600])
    return 0 if report["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--selftest":
        out = Path(argv[1]) if len(argv) > 1 else Path("selftest_out")
        return _selftest(out, Path(argv[2]) if len(argv) > 2 else None)
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import QApplication

    from .errores import instalar as instalar_filtro_errores
    from .recursos import icono_aplicacion
    from .gui.main_window import MainWindow
    from .gui.splash import PantallaCarga
    from .gui.theme import apply_theme
    _qt_setup()
    app = QApplication(sys.argv)
    instalar_filtro_errores()
    app.setApplicationName("NVS")
    apply_theme(app)
    app.setWindowIcon(icono_aplicacion())
    splash = PantallaCarga()
    splash.show()
    splash.paso("Iniciando el motor gráfico…", 10)
    w = MainWindow()
    splash.paso("Construyendo la interfaz…", 45)
    ruta = Path(argv[0]) if argv else None

    def mostrar():
        splash.paso("Listo", 100)
        w.showMaximized()
        QTimer.singleShot(250, splash.close)

    if ruta is not None and ruta.exists():
        splash.paso(f"Leyendo {ruta.name}…", 60)
        w.carga_terminada.connect(mostrar, Qt.SingleShotConnection)
        w.open_path(ruta)
    else:
        mostrar()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
