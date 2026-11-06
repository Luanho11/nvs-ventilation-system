"""Ruta GPU del visor (OpenGL). Se ejecuta en un proceso aparte con la plataforma de pantalla real; se omite si no hay GPU.

Comprueba: modo de render «gpu»; los tubos salen con el color de la escala (píxel en el centro de una galería);
las superposiciones (nota) están presentes; las superficies de referencia se dibujan; y el coste de un fotograma de
6.000 galerías (CPU+GPU, con glFinish) queda muy por debajo del presupuesto de 60 fps.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = r'''
import json, sys, time
import numpy as np
from nvs.app import _qt_setup
_qt_setup()
from PySide6.QtWidgets import QApplication
from nvs.gui.viewport import GLViewport, gl_available
app = QApplication([])
if not gl_available():
    print(json.dumps({"skip": "sin GPU/OpenGL"})); sys.exit(0)
from nvs.gui.colorscale import default_scales
from nvs.escena import Malla
v = GLViewport(); v.resize(900, 600)
# una galería horizontal larga y gruesa en el centro: caudal 100 -> umbral rojo de la paleta observada
v.set_geometry([[-200, 0, 0]], [[200, 0, 0]], [8])
v.set_values(np.array([100.0]), np.array([1.0]), default_scales()["Q"])
v.set_mallas([Malla("t", np.array([[-300, 100, 60], [300, 100, 60], [0, 100, 300]], np.float32),
                    np.tile(np.array([40, 200, 40], np.uint8), (3, 1)))])
v.set_notas([("nota de prueba", 0.02, 0.02, (0, 64, 128), None)])

v.yaw, v.pitch = -1.5707963, 0.0     # cámara de frente: la galería (eje X) cruza la pantalla
v.fit()
v.show(); app.processEvents(); app.processEvents()
img = v.grabFramebuffer()
cx, cy = img.width() // 2, img.height() // 2
best = max((img.pixelColor(cx, cy + dy) for dy in range(-6, 7)), key=lambda c: c.red() - c.blue())
nota = img.pixelColor(22, 26)      # fondo de la nota: entre su borde blanco y el texto
verde = max((img.pixelColor(cx, cy - dy) for dy in range(60, 140, 4)), key=lambda c: c.green() - c.red())
out = {"mode": v.render_mode(), "tube_rgb": [best.red(), best.green(), best.blue()], "nota_rgb": [nota.red(), nota.green(), nota.blue()],
       "malla_rgb": [verde.red(), verde.green(), verde.blue()]}
def fotograma():
    img = v.grabFramebuffer()          # la imagen debe seguir viva mientras se copian sus bytes
    return bytes(img.constBits())


# el aire animado dentro del tubo: dos fotogramas separados en el tiempo no son iguales; sin flujo sí lo son
v.set_flujo(np.array([6.0]))
v.fit(); app.processEvents()
a = fotograma(); time.sleep(0.4); b = fotograma()
out["flujo_cambia"] = a != b
v.set_flujo(None)
a = fotograma(); time.sleep(0.4); b = fotograma()
out["sin_flujo_estatico"] = a == b
# rendimiento con 6000 galerias
rng = np.random.default_rng(0)
n = 6000
p1 = rng.uniform(-500, 500, (n, 3)); p2 = p1 + rng.uniform(-60, 60, (n, 3))
v.set_geometry(p1, p2, np.full(n, 4.0))
v.set_values(rng.uniform(0, 200, n), None, default_scales()["Q"])
v.fit(); app.processEvents()
v.makeCurrent()
v._interacting = True
v.paintGL(); v._f.glFinish()
t = time.perf_counter()
for i in range(20):
    v.yaw += 0.03; v.paintGL(); v._f.glFinish()
out["ms_frame_6000"] = (time.perf_counter() - t) / 20 * 1000
v.doneCurrent()
print(json.dumps(out))
'''


def test_gpu_path():
    env = dict(os.environ)
    env.pop("QT_QPA_PLATFORM", None)
    env.pop("NVS_RENDER", None)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    r = subprocess.run([sys.executable, "-c", SCRIPT], capture_output=True, text=True, env=env, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    out = json.loads(r.stdout.strip().splitlines()[-1])
    if "skip" in out:
        pytest.skip(out["skip"])
    assert out["mode"] == "gpu", out
    R, G, B = out["tube_rgb"]
    assert R > 150 and G < 90 and B < 90, f"el tubo no tiene el color rojo esperado: {out['tube_rgb']}"
    assert out["nota_rgb"] == [0, 64, 128], f"la nota de superposición no se dibujó: {out['nota_rgb']}"
    assert out["malla_rgb"][1] > 80 and out["malla_rgb"][1] > out["malla_rgb"][0] + 30, f"la superficie no se dibujó: {out['malla_rgb']}"
    assert out["flujo_cambia"] and out["sin_flujo_estatico"], out
    assert out["ms_frame_6000"] < 16, out
