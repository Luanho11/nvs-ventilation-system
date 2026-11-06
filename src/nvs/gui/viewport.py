"""Visor 3D: GPU (OpenGL) con respaldo por software (QPainter).

Arquitectura
  * `ViewportCore`  : cámara orbital, proyección, selección, eventos, etiquetas/flechas/notas/gizmo (QPainter).
  * `GLViewport`    : tubos como malla 3D real (8 caras, normales suaves, luz + brillo especular + borde oscuro + niebla,
                      buffer de profundidad, MSAA), superficies de referencia con textura, cielo y rejilla en shaders.
  * `SoftwareViewport`: respaldo sin GPU (más lento, sin superficies); también se usa en pruebas sin pantalla.
Las etiquetas y flechas se dibujan en una capa en caché que solo se rehace si cambia la cámara o los datos; mientras se
arrastra/gira en modelos con >400 galerías se omiten y reaparecen al soltar.
Z es la cota (arriba), como en los proyectos de VentSim.
"""
from __future__ import annotations

import math
import os

import numpy as np
from PySide6.QtCore import QEasingCurve, QElapsedTimer, QLineF, QPointF, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QLinearGradient, QMatrix4x4, QOffscreenSurface,
                           QOpenGLContext, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QSurfaceFormat)
from PySide6.QtOpenGL import QOpenGLBuffer, QOpenGLShader, QOpenGLShaderProgram
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from ..escena import Rejilla
from .colorscale import ColorScale

FOV_GRADOS = 45.0
DESFASE_GIRO = math.radians(90.0)      # giro guardado en el .vsm + 90° = giro de esta cámara (ajustado con Blue_sky, CoalMine y Fire reales, E-006)
BASE_RGB = (139, 176, 216)
NBUCKETS = 14
SKY_FOG = np.array([70, 84, 108], float)
LIGHT_N = 400            # a partir de aquí se omiten etiquetas/flechas mientras se mueve la cámara
MAX_ETIQUETAS = 700
MAX_NODOS = 4000
ZOOM_POR_MUESCA = 1.077      # medido en Ventsim real: una muesca de rueda acerca ×1,077, sobre el centro de la pantalla (E-006)
SUAVIZADO_ZOOM = 0.34        # fracción del recorrido pendiente que se recorre en cada fotograma (zoom fluido)

# constantes OpenGL (QOpenGLFunctions no las exporta todas)
GL_FLOAT, GL_UNSIGNED_BYTE = 0x1406, 0x1401
GL_LINES, GL_TRIANGLES, GL_TRIANGLE_STRIP = 0x0001, 0x0004, 0x0005
GL_DEPTH_TEST, GL_BLEND = 0x0B71, 0x0BE2
GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT = 0x4000, 0x0100
GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA = 0x0302, 0x0303
GL_LEQUAL, GL_LESS = 0x0203, 0x0201
SIDES = 8
VERTS_PER_SEG = SIDES * 6
FLOATS_VERTICE = 12                 # eje(3), dirección(3), radio, posición a lo largo (0..1), longitud, dirección de la galería(3)
TRANSPARENCIA_TUBO = 0.90           # opacidad del centro del tubo (en Ventsim real son casi opacos, con grano en los bordes)
VEL_FLUJO_MIN, VEL_FLUJO_MAX = 1.0, 12.0   # m/s mostrados en la animación (el flujo real se recorta para que siempre se vea)
FACTOR_ANIMACION = 1.6
MS_FOTOGRAMA = 33



def _nice_step(span: float, target_lines: int = 18) -> float:
    raw = max(span / target_lines, 1e-9)
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def default_format() -> QSurfaceFormat:
    fmt = QSurfaceFormat()
    fmt.setDepthBufferSize(24)
    fmt.setSamples(4)
    fmt.setSwapInterval(1)
    return fmt


def gl_available() -> bool:
    """¿Se puede crear un contexto OpenGL y compilar un shader? (requiere QApplication)."""
    if os.environ.get("NVS_RENDER", "").lower() == "software":
        return False
    try:
        from PySide6.QtGui import QGuiApplication
        if QGuiApplication.platformName() in ("offscreen", "minimal"):
            return False
        ctx = QOpenGLContext()
        if not ctx.create():
            return False
        surf = QOffscreenSurface()
        surf.setFormat(ctx.format())
        surf.create()
        if not ctx.makeCurrent(surf):
            return False
        es = ctx.isOpenGLES()
        prog = QOpenGLShaderProgram()
        hdr = "" if es else "#version 120\n"
        ok = (prog.addShaderFromSourceCode(QOpenGLShader.Vertex, hdr + "attribute vec3 p;void main(){gl_Position=vec4(p,1.0);}")
              and prog.addShaderFromSourceCode(QOpenGLShader.Fragment, hdr + ("precision mediump float;\n" if es else "")
                                               + "void main(){gl_FragColor=vec4(1.0);}")
              and prog.link())
        ctx.doneCurrent()
        return bool(ok)
    except Exception:  # noqa: BLE001
        return False


def _set(prog, name: str, *vals):
    """setUniformValue por nombre. PySide6 exige la ubicación y falla (OverflowError) con floats negativos
    en la sobrecarga genérica, por eso los escalares usan setUniformValue1f."""
    loc = prog.uniformLocation(name)
    if len(vals) == 1 and isinstance(vals[0], (int, float)):
        prog.setUniformValue1f(loc, float(vals[0]))
    else:
        prog.setUniformValue(loc, *vals)


# ============================================================================ núcleo común
class ViewportCore:
    """Estado, cámara, selección y superposiciones. Se mezcla con QWidget o QOpenGLWidget."""

    def _init_core(self):
        self.setMinimumSize(420, 320)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.p1 = np.zeros((0, 3))
        self.p2 = np.zeros((0, 3))
        self.widths = np.zeros(0)
        self.visible = np.ones(0, bool)
        self.values: np.ndarray | None = None
        self.signs: np.ndarray | None = None
        self.flujo: np.ndarray | None = None          # velocidad con signo [m/s] de cada galería (+ = de p1 a p2)
        self.scale: ColorScale | None = None
        self.label_texts: list[str] | None = None
        self.nombres: list[str] | None = None                 # nombre de cada galería, se dibuja sobre su valor
        self.callout: list | None = None
        self.notas: list[tuple[str, float, float, tuple, tuple | None]] = []
        self.mallas: list = []
        self.show_notas = True
        self.show_referencias = True
        self.opacidad_referencias = 0.58                     # capas sin textura (opacidad medida en CoalMine real); lo cambia el deslizador de «Exponer»
        self.pan_activo = False
        self.show_labels = True
        self.show_grid = True
        self.rejilla = Rejilla()
        self.cielo = "#6495ed"                      # fondo arriba (el de abajo es casi negro); por proyecto, de GRAPHICS
        self.color_rejilla = "#bcbcbc"
        self.show_arrows = True
        self.show_nodos = False
        self.colores_directos: np.ndarray | None = None    # color por galería (N,3) cuando se colorea por categoría
        self.pista_idx = np.zeros(0, int)             # galerías de la pista visible y su color
        self.pista_color = (255, 0, 0)
        self.tubes = True
        self.tube_scale = 1.4                         # exageración del grosor real de las galerías (Ventsim las dibuja más finas)
        self.sel = -1
        self.target = np.zeros(3)
        self.dist = 100.0
        self.yaw = math.radians(-80)
        self.pitch = math.radians(23)
        self.radius = 100.0
        self.floor_z = 0.0
        self._press = None
        self._moved = False
        self._auto_fit = True
        self._interacting = False
        self._anim: QVariantAnimation | None = None
        self.overlays: list[QWidget] = []             # paneles flotantes que el callout debe esquivar
        self._data_version = 0
        self._layer: QPixmap | None = None
        self._layer_key = None
        self._reloj = QElapsedTimer()
        self._reloj.start()
        self._animacion = QTimer(self)
        self._animacion.setInterval(MS_FOTOGRAMA)
        self._animacion.timeout.connect(self._fotograma)
        self.vistas_rapidas: list[tuple] = []         # «Vista rápida»: cámaras temporales, se recorren con las flechas izquierda/derecha
        self._vista_rapida = -1
        self._dist_objetivo: float | None = None
        self._zoom = QTimer(self)
        self._zoom.setInterval(16)
        self._zoom.timeout.connect(self._paso_zoom)
        self._idle = QTimer(self)
        self._idle.setSingleShot(True)
        self._idle.setInterval(160)
        self._idle.timeout.connect(self._end_interacting)

    # ------------------------------------------------------------ datos
    def set_ambiente(self, cielo: str, color_rejilla: str):
        self.cielo, self.color_rejilla = cielo, color_rejilla
        self.update()

    def set_rejilla(self, rejilla: Rejilla):
        self.rejilla = rejilla
        self._rejilla_cambio()
        if len(self.p1) == 0:
            self.fit()
        self.update()

    def _rejilla_cambio(self):
        pass

    def set_mallas(self, mallas):
        self.mallas = list(mallas)
        self._mallas_changed()
        self.update()

    def set_notas(self, notas):
        """`notas`: [(texto, fx, fy, color, posición del modelo o None)]."""
        self.notas = list(notas)
        self.update()

    def _mallas_changed(self):
        pass

    def set_geometry(self, p1, p2, widths=None):
        self.p1, self.p2 = np.asarray(p1, float).reshape(-1, 3), np.asarray(p2, float).reshape(-1, 3)
        self.widths = np.full(len(self.p1), 4.0) if widths is None else np.asarray(widths, float)
        self.visible = np.ones(len(self.p1), bool)
        self.values = None
        self.signs = None
        self.flujo = None
        self.pista_idx = np.zeros(0, int)
        self.label_texts = None
        self.callout = None
        self.sel = -1
        self._geom_changed()
        self.fit()

    def _geom_changed(self):
        self._data_version += 1

    def set_visible(self, mascara):
        """Galerías que se muestran (p. ej. las de la etapa elegida); las demás no se dibujan ni se pueden elegir."""
        self.visible = np.asarray(mascara, bool)
        self._data_version += 1
        self._colors_changed()
        self.update()

    def set_values(self, values, signs=None, scale: ColorScale | None = None):
        self.values = None if values is None else np.asarray(values, float)
        self.signs = None if signs is None else np.asarray(signs, float)
        self.scale = scale
        self._data_version += 1
        self._colors_changed()
        self.update()

    def set_colores_directos(self, rgb):
        """Color propio de cada galería (p. ej. por tipo de aire); None vuelve a la escala numérica."""
        self.colores_directos = None if rgb is None else np.asarray(rgb, np.uint8)
        self._data_version += 1
        self._colors_changed()
        self.update()

    def set_flujo(self, velocidad):
        """Velocidad con signo de cada galería (m/s): alimenta la animación del aire dentro de los tubos."""
        self.flujo = None if velocidad is None else np.nan_to_num(np.asarray(velocidad, float))
        self._colors_changed()
        self._actualizar_animacion()
        self.update()

    def set_nodos(self, activo: bool):
        self.show_nodos = activo
        self._data_version += 1
        self.update()

    def set_pista(self, indices, color):
        """Pista de actividad: ruta de galerías que se resalta con el color guardado en el proyecto."""
        self.pista_idx = np.asarray(indices, int)
        self.pista_color = color
        self._data_version += 1
        self.update()

    def set_flechas(self, activo: bool):
        """Flechas de sentido: estáticas en el respaldo por software; en GPU, el aire animado dentro de los tubos."""
        self.show_arrows = activo
        self._colors_changed()
        self._actualizar_animacion()
        self.update()

    def _flujo_en_gpu(self) -> bool:
        return False

    def _fotograma(self):
        """Solo se redibuja la animación si la ventana se ve y está en primer plano (no consume GPU en segundo plano)."""
        ventana = self.window()
        if self.isVisible() and ventana.isActiveWindow() and not ventana.isMinimized():
            self.update()

    def _actualizar_animacion(self):
        """El reloj solo corre si hay algo que mover: flujo con datos, animación activa y respaldo GPU."""
        activo = self._flujo_en_gpu() and self.show_arrows and self.flujo is not None and bool(np.any(self.flujo))
        if activo and not self._animacion.isActive():
            self._animacion.start()
        elif not activo:
            self._animacion.stop()

    def _colors_changed(self):
        pass

    def set_labels(self, texts: list[str] | None):
        self.label_texts = texts
        self._data_version += 1
        self.update()

    def set_nombres(self, nombres):
        self.nombres = nombres
        self._data_version += 1
        self.update()

    def set_callout(self, lines):
        self.callout = lines
        self.update()

    def set_selected(self, i: int):
        self.sel = i
        self.update()

    def set_tube_scale(self, k: float):
        self.tube_scale = k
        self._data_version += 1
        self.update()

    # ------------------------------------------------------------ cámara
    def guardar_vista_rapida(self):
        self.vistas_rapidas.append((self.target.copy(), self.dist, self.yaw, self.pitch))
        self._vista_rapida = len(self.vistas_rapidas) - 1

    def borrar_vista_rapida(self):
        if 0 <= self._vista_rapida < len(self.vistas_rapidas):
            del self.vistas_rapidas[self._vista_rapida]
            self._vista_rapida = min(self._vista_rapida, len(self.vistas_rapidas) - 1)

    def borrar_vistas_rapidas(self):
        self.vistas_rapidas.clear()
        self._vista_rapida = -1

    def vista_rapida(self, paso: int):
        if not self.vistas_rapidas:
            return
        self._vista_rapida = (self._vista_rapida + paso) % len(self.vistas_rapidas)
        objetivo, dist, giro, elevacion = self.vistas_rapidas[self._vista_rapida]
        self._cancelar_zoom()
        self.target, self.dist, self.yaw, self.pitch = objetivo.copy(), dist, giro, elevacion
        self._auto_fit = False
        self.update()

    def alejar(self):
        self._cancelar_zoom()
        self.dist *= 2.0
        self._auto_fit = False
        self.update()

    def _cancelar_zoom(self):
        self._dist_objetivo = None
        self._zoom.stop()

    def fit(self):
        self._cancelar_zoom()
        if len(self.p1) == 0:
            r = self.rejilla
            self.target, self.radius, self.dist = np.array([r.cx, r.cy, r.z]), max(r.sx, r.sy) * 0.7, max(r.sx, r.sy) * 0.42
            self.floor_z = r.z
        else:
            pts = np.vstack([self.p1[self.visible], self.p2[self.visible]]) if self.visible.any() \
                else np.vstack([self.p1, self.p2])
            lo, hi = pts.min(axis=0), pts.max(axis=0)
            self.target = (lo + hi) / 2
            self.radius = max(float(np.linalg.norm(hi - lo)) / 2, 1.0)
            self.floor_z = float(lo[2]) - 0.02 * max(float(hi[2] - lo[2]), self.radius * 0.1)
            h, w = max(self.height(), 1), max(self.width(), 1)
            tan_half = math.tan(math.radians(FOV_GRADOS) / 2) * min(w, h) / h
            self.dist = self.radius * 1.08 / math.sin(math.atan(tan_half))
            self._tighten_fit(pts)
        self._auto_fit = True
        self.update()

    def _tighten_fit(self, pts: np.ndarray, fill: float = 0.86):
        if len(pts) > 20000:
            pts = pts[:: len(pts) // 20000 + 1]
        w, h = max(self.width(), 1), max(self.height(), 1)
        for _ in range(10):
            eye, f, right, up = self._basis()
            c = self._to_cam(pts, eye, f, right, up)
            if (c[:, 2] <= self.dist * 0.05).any():
                self.dist *= 1.15
                continue
            F = self._focal()
            ext = max(np.abs(F * c[:, 0] / c[:, 2]).max() / (w / 2), np.abs(F * c[:, 1] / c[:, 2]).max() / (h / 2))
            if abs(ext - fill) < 0.01:
                break
            self.dist *= ext / fill

    def set_camera(self, objetivo, distancia: float, giro: float, elevacion: float):
        """Cámara guardada en el .vsm (STATE/SAVEVIEWS): objetivo, distancia, giro y elevación."""
        self._cancelar_zoom()
        self.target = np.array(objetivo, float)
        self.dist = float(distancia)
        self.yaw = giro + DESFASE_GIRO
        self.pitch = float(np.clip(elevacion, -math.pi / 2 + 0.02, math.pi / 2 - 0.02))
        self._auto_fit = False
        self.update()

    def focus_selected(self):
        if self.sel >= 0:
            self.target = (self.p1[self.sel] + self.p2[self.sel]) / 2
            self._auto_fit = False
            self.update()

    def _animate_to(self, yaw: float, pitch: float):
        """Giro suave a una orientación; después reencuadra."""
        if self._anim is not None:
            self._anim.stop()
        y0, p0 = self.yaw, self.pitch
        dy = (yaw - y0 + math.pi) % (2 * math.pi) - math.pi
        a = QVariantAnimation(self)
        a.setDuration(320)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        a.setEasingCurve(QEasingCurve.InOutCubic)

        def step(t):
            self.yaw = y0 + dy * t
            self.pitch = p0 + (pitch - p0) * t
            self._interacting = t < 1.0
            if t >= 1.0:
                self.fit()
            self.update()
        a.valueChanged.connect(step)
        self._anim = a
        a.start()

    def view_top(self):
        self._animate_to(math.radians(-90), math.radians(89))

    def view_front(self):
        self._animate_to(math.radians(-90), math.radians(0))

    def view_side(self):
        self._animate_to(math.radians(0), math.radians(0))

    def view_iso(self):
        self._animate_to(math.radians(-50), math.radians(28))

    def _basis(self):
        cp, sp_ = math.cos(self.pitch), math.sin(self.pitch)
        eye = self.target + self.dist * np.array([cp * math.cos(self.yaw), cp * math.sin(self.yaw), sp_])
        f = self.target - eye
        f /= np.linalg.norm(f)
        right = np.cross(f, [0.0, 0.0, 1.0])
        right /= np.linalg.norm(right)
        up = np.cross(right, f)
        return eye, f, right, up

    def _focal(self):
        return (self.height() / 2) / math.tan(math.radians(FOV_GRADOS) / 2)

    @staticmethod
    def _to_cam(pts, eye, f, right, up):
        d = pts - eye
        return np.stack([d @ right, d @ up, d @ f], axis=1)

    def _near(self) -> float:
        return max(self.dist * 0.02, 0.05)

    def _project_pairs(self, A: np.ndarray, B: np.ndarray):
        """Proyecta segmentos A→B con recorte al plano cercano. Devuelve (idx, s[x1,y1,x2,y2], zmid)."""
        if len(A) == 0:
            return np.zeros(0, int), np.zeros((0, 4)), np.zeros(0)
        eye, f, right, up = self._basis()
        a = self._to_cam(A, eye, f, right, up)
        b = self._to_cam(B, eye, f, right, up)
        near = self._near()
        za, zb = a[:, 2], b[:, 2]
        idx = np.nonzero((za > near) | (zb > near))[0]
        a, b = a[idx].copy(), b[idx].copy()
        za, zb = a[:, 2], b[:, 2]
        m = za < near
        t = (near - za[m]) / (zb[m] - za[m])
        a[m] = a[m] + (b[m] - a[m]) * t[:, None]
        m = zb < near
        t = (near - zb[m]) / (za[m] - zb[m])
        b[m] = b[m] + (a[m] - b[m]) * t[:, None]
        F = self._focal()
        cx, cy = self.width() / 2, self.height() / 2
        s = np.stack([cx + F * a[:, 0] / a[:, 2], cy - F * a[:, 1] / a[:, 2],
                      cx + F * b[:, 0] / b[:, 2], cy - F * b[:, 1] / b[:, 2]], axis=1)
        return idx, s, (a[:, 2] + b[:, 2]) / 2

    def _project_red(self):
        """Proyecta las galerías visibles: (índices de proyecto, segmentos en pantalla, profundidad)."""
        idx, s, zm = self._project_pairs(self.p1, self.p2)
        ok = self.visible[idx]
        return idx[ok], s[ok], zm[ok]

    def _project_segments(self):
        idx, s, _z = self._project_red()
        return idx, s

    def _horizon_y(self) -> float:
        return self.height() / 2 - self._focal() * math.tan(self.pitch)

    def _wpx(self, idx, zm) -> np.ndarray:
        """Ancho en píxeles de cada tubo (para flechas y picking)."""
        return np.clip(self.widths[idx] * self._focal() / np.maximum(zm, 1e-6) * self.tube_scale, 3.2, 46.0)

    # ------------------------------------------------------------ pintura por software
    def _paint_sky(self, qp: QPainter):
        H = self.height()
        g = QLinearGradient(0, 0, 0, H)
        for t, c in ((0.0, self.cielo), (1.0, "#010203")):
            g.setColorAt(t, QColor(c))
        qp.fillRect(self.rect(), QBrush(g))

    def _grid_lines(self):
        """(A, B, mayor) de la rejilla finita en coordenadas del mundo: rectángulo centrado en (cx, cy) a la cota z."""
        r = self.rejilla
        x0, x1 = r.cx - r.sx / 2, r.cx + r.sx / 2
        y0, y1 = r.cy - r.sy / 2, r.cy + r.sy / 2
        xs = np.arange(x0, x1 + r.espaciado * 0.01, r.espaciado)
        ys = np.arange(y0, y1 + r.espaciado * 0.01, r.espaciado)
        z = r.z
        A = np.vstack([np.column_stack([xs, np.full_like(xs, y0), np.full_like(xs, z)]),
                       np.column_stack([np.full_like(ys, x0), ys, np.full_like(ys, z)])])
        B = np.vstack([np.column_stack([xs, np.full_like(xs, y1), np.full_like(xs, z)]),
                       np.column_stack([np.full_like(ys, x1), ys, np.full_like(ys, z)])])
        major = np.concatenate([(np.round((xs - x0) / r.espaciado) % 5 == 0), (np.round((ys - y0) / r.espaciado) % 5 == 0)])
        return A, B, major

    def _paint_grid(self, qp: QPainter):
        if not self.show_grid:
            return
        A, B, major = self._grid_lines()
        K = 6
        t = np.linspace(0, 1, K + 1)
        P = A[:, None, :] * (1 - t)[None, :, None] + B[:, None, :] * t[None, :, None]
        a, b = P[:, :-1].reshape(-1, 3), P[:, 1:].reshape(-1, 3)
        mj = np.repeat(major, K)
        idx, s, zm = self._project_pairs(a, b)
        if len(idx) == 0:
            return
        far = self.dist + max(self.rejilla.sx, self.rejilla.sy) * 1.5
        fade = np.clip(1.0 - (zm / far), 0.0, 1.0) ** 0.8
        tier = np.clip((fade * 5).astype(int), 0, 4)
        for mjr in (False, True):
            for tr in range(5):
                sel = (mj[idx] == mjr) & (tier == tr)
                if not sel.any():
                    continue
                color = QColor(self.color_rejilla)
                color.setAlpha(min(int(60 + tr * 30 + (40 if mjr else 0)), 235))
                qp.setPen(QPen(color, 1.4 if mjr else 1.0))
                qp.drawLines([QLineF(*r) for r in s[sel]])

    def _seg_colors(self, idx) -> np.ndarray:
        if self.colores_directos is not None and len(self.colores_directos) == len(self.p1):
            return self.colores_directos[idx]
        if self.values is None or self.scale is None:
            return np.tile(np.array(BASE_RGB, np.uint8), (len(idx), 1))
        return self.scale.rgb(self.values[idx])

    def _paint_network_soft(self, qp: QPainter, idx, s, zm):
        n = len(idx)
        light = self._interacting and n > 2500
        rgb = self._seg_colors(idx).astype(float)
        wpx = self._wpx(idx, zm)
        if not self.tubes or light:
            wpx = np.full(n, 2.2 if n < 3000 else 1.6)
        order = np.argsort(-zm)
        nb = 6 if light else NBUCKETS
        bucket = (np.arange(n) * nb) // max(n, 1)
        zmin, zmax = float(zm.min()), float(zm.max())
        for b in range(nb):
            sel = order[bucket == b]
            if len(sel) == 0:
                continue
            fog = 0.0 if zmax - zmin < 1e-9 else 0.38 * ((zm[sel].mean() - zmin) / (zmax - zmin)) ** 1.2
            col = rgb[sel] * (1 - fog) + SKY_FOG * fog
            q = np.round(col).astype(int)
            key = (q[:, 0] << 16 | q[:, 1] << 8 | q[:, 2]).astype(np.int64) * 64 + np.round(wpx[sel]).astype(np.int64)
            uk, inv = np.unique(key, return_inverse=True)
            groups = [(int(k), sel[inv == i]) for i, k in enumerate(uk)]
            passes = (0,) if (not self.tubes or light) else (0, 1, 2)
            for ps in passes:
                for k, members in groups:
                    w = k % 64
                    rgbk = (k // 64 >> 16 & 255, k // 64 >> 8 & 255, k // 64 & 255)
                    segs = s[members]
                    if not self.tubes or light:
                        pen = QPen(QColor(*rgbk), float(w))
                        pen.setCapStyle(Qt.RoundCap)
                        qp.setPen(pen)
                        qp.drawLines([QLineF(*r) for r in segs])
                        continue
                    if ps == 0:
                        pen = QPen(QColor(int(rgbk[0] * .32), int(rgbk[1] * .32), int(rgbk[2] * .32), 235), w + 2.6)
                        off = 0.0
                    elif ps == 1:
                        pen = QPen(QColor(*rgbk), float(w))
                        off = 0.0
                    else:
                        hl = tuple(int(c + (255 - c) * 0.46) for c in rgbk)
                        pen = QPen(QColor(*hl, 200), max(1.0, w * 0.34))
                        off = -w * 0.17
                    pen.setCapStyle(Qt.RoundCap)
                    qp.setPen(pen)
                    qp.drawLines([QLineF(r[0] + off, r[1] + off, r[2] + off, r[3] + off) for r in segs])

    def _paint_selection(self, qp, idx, s):
        pos = np.nonzero(idx == self.sel)[0]
        if not len(pos):
            return
        x1, y1, x2, y2 = s[pos[0]]
        qp.setPen(QPen(QColor(20, 30, 50), 1.5))
        qp.setBrush(QColor("#ffd23f"))
        qp.drawEllipse(QPointF(x1, y1), 5.5, 5.5)
        qp.drawEllipse(QPointF(x2, y2), 5.5, 5.5)

    def _paint_selection_soft(self, qp, idx, s):
        pos = np.nonzero(idx == self.sel)[0]
        if not len(pos):
            return
        x1, y1, x2, y2 = s[pos[0]]
        for w, col in ((15, QColor(255, 255, 255, 55)), (9, QColor(255, 255, 255, 120)), (4.5, QColor(255, 255, 255, 255))):
            qp.setPen(QPen(col, w, Qt.SolidLine, Qt.RoundCap))
            qp.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        self._paint_selection(qp, idx, s)

    # ------------------------------------------------------------ capa de etiquetas y flechas (en caché)
    def _layer_state_key(self):
        return (self._data_version, round(float(self.yaw), 5), round(float(self.pitch), 5), round(float(self.dist), 4),
                tuple(np.round(self.target, 3)), self.width(), self.height(), self.show_labels, self.show_arrows,
                self.show_nodos, self.tube_scale, self.tubes, round(float(self.devicePixelRatioF()), 2))

    def _paint_layer(self, qp: QPainter, idx, s, zm):
        n = len(idx)
        if self._interacting and n > LIGHT_N:
            return
        flechas = self.show_arrows and self.signs is not None and not self._flujo_en_gpu()
        if not ((self.show_labels and self.label_texts) or flechas or self.show_nodos):
            return
        key = self._layer_state_key()
        if self._layer is None or key != self._layer_key:
            dpr = self.devicePixelRatioF()
            pm = QPixmap(int(self.width() * dpr), int(self.height() * dpr))
            pm.setDevicePixelRatio(dpr)
            pm.fill(Qt.transparent)
            lp = QPainter(pm)
            lp.setRenderHint(QPainter.Antialiasing, True)
            if self.show_nodos:
                self._paint_nodos(lp, s)
            if flechas:
                self._paint_arrows(lp, idx, s, zm)
            if self.show_labels and self.label_texts:
                self._paint_labels(lp, idx, s)
            lp.end()
            self._layer, self._layer_key = pm, key
        qp.drawPixmap(0, 0, self._layer)

    def _paint_nodos(self, qp, s):
        """Un punto en cada extremo de galería (los extremos compartidos se dibujan una vez)."""
        extremos = np.round(np.vstack([s[:, :2], s[:, 2:]]), 0)
        extremos = np.unique(extremos, axis=0)[:MAX_NODOS]
        qp.setPen(QPen(QColor(10, 20, 36, 230), 1.2))
        qp.setBrush(QColor(255, 255, 255, 235))
        for x, y in extremos:
            qp.drawEllipse(QPointF(x, y), 3.2, 3.2)

    def _paint_pista_soft(self, qp, idx, s):
        pos = np.nonzero(np.isin(idx, self.pista_idx))[0]
        if not len(pos):
            return
        qp.setPen(QPen(QColor(*self.pista_color), 5.0, Qt.SolidLine, Qt.RoundCap))
        qp.drawLines([QLineF(*s[k]) for k in pos])

    def _paint_arrows(self, qp, idx, s, zm):
        dx, dy = s[:, 2] - s[:, 0], s[:, 3] - s[:, 1]
        ln = np.hypot(dx, dy)
        ok = np.nonzero((ln > 34) & (np.abs(self.signs[idx]) > 1e-6))[0]
        ok = ok[np.argsort(-ln[ok])][:700]
        wpx = self._wpx(idx, zm)
        qp.setPen(QPen(QColor(8, 12, 20, 210), 1.0))
        qp.setBrush(QColor(255, 255, 255, 240))
        for k in ok:
            sg = 1.0 if self.signs[idx[k]] > 0 else -1.0
            ux, uy = sg * dx[k] / ln[k], sg * dy[k] / ln[k]
            mx, my = s[k, 0] + (s[k, 2] - s[k, 0]) * 0.27, s[k, 1] + (s[k, 3] - s[k, 1]) * 0.27
            sz = 4.0 + min(wpx[k], 14) * 0.3
            qp.drawPolygon(QPolygonF([QPointF(mx + ux * sz, my + uy * sz),
                                      QPointF(mx - ux * sz - uy * sz * .78, my - uy * sz + ux * sz * .78),
                                      QPointF(mx - ux * sz * .45, my - uy * sz * .45),
                                      QPointF(mx - ux * sz + uy * sz * .78, my - uy * sz - ux * sz * .78)]))

    def _paint_labels(self, qp, idx, s):
        """Texto blanco con contorno fino sobre el centro de cada galería; como en la referencia, los textos pueden solaparse.
        El nombre de la galería (si lo tiene) va más grande encima del valor."""
        font = QFont("Segoe UI")
        font.setPixelSize(15)
        fm = QFontMetricsF(font)
        font_nombre = QFont("Segoe UI")
        font_nombre.setPixelSize(19)
        fm_nombre = QFontMetricsF(font_nombre)
        ln = np.hypot(s[:, 2] - s[:, 0], s[:, 3] - s[:, 1])
        cand = np.nonzero(ln > 28)[0]
        cand = cand[np.argsort(-ln[cand])][:MAX_ETIQUETAS]
        W, H = self.width(), self.height()

        def dibujar(texto, fuente, medidas, cx, cy):
            w = medidas.horizontalAdvance(texto)
            if cx - w / 2 < 0 or cx + w / 2 > W or cy < 8 or cy > H - 8:
                return
            path = QPainterPath()
            path.addText(cx - w / 2, cy + medidas.ascent() / 2 - 2, fuente, texto)
            qp.strokePath(path, QPen(QColor(0, 0, 0, 210), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            qp.fillPath(path, QColor("#ffffff"))

        for k in cand:
            i = int(idx[k])
            txt = self.label_texts[i] if i < len(self.label_texts) else ""
            nombre = self.nombres[i] if self.nombres and i < len(self.nombres) else ""
            cx, cy = (s[k, 0] + s[k, 2]) / 2, (s[k, 1] + s[k, 3]) / 2
            if nombre and ln[k] > 140:
                dibujar(nombre, font_nombre, fm_nombre, cx, cy - 10)
                if txt:
                    dibujar(txt, font, fm, cx, cy + 11)
            elif txt:
                dibujar(txt, font, fm, cx, cy)

    # ------------------------------------------------------------ notas, callout y gizmo
    def _caja_nota(self, qp, x: float, y: float, texto: str, color, px: int, sobre_punto: bool = False) -> QRectF:
        """Caja de texto con el estilo de las notas de la referencia: fondo de color, borde blanco, letra blanca.
        Con `sobre_punto` (nota anclada) la caja queda arriba a la derecha del punto (x, y); el desplazamiento se ajustó
        a la posición observada de las notas de Blue_sky en la referencia."""
        font = QFont("Segoe UI")
        font.setPixelSize(px)
        fm = QFontMetricsF(font)
        lineas = texto.split("\n")
        ancho, alto = max(fm.horizontalAdvance(t) for t in lineas) + 14, len(lineas) * fm.lineSpacing() + 10
        if sobre_punto:
            x, y = x - 25, y - alto - 10
        r = QRectF(x, y, ancho, alto)
        qp.setPen(QPen(QColor("#ffffff"), 2))
        qp.setBrush(QColor(*color))
        qp.drawRect(r)
        qp.setFont(font)
        for i, t in enumerate(lineas):
            qp.drawText(QPointF(x + 7, y + 5 + fm.ascent() + i * fm.lineSpacing()), t)
        return r

    def _paint_notas(self, qp):
        """Notas fijas en pantalla (posición en fracción del visor) y notas ancladas a un punto del modelo."""
        if not self.show_notas:
            return
        ancladas = [n for n in self.notas if n[4] is not None]
        if ancladas:
            pts = np.array([n[4] for n in ancladas], float)
            idx, s, _z = self._project_pairs(pts, pts)
            en_pantalla = {int(i): (r[0], r[1]) for i, r in zip(idx, s)}
        k = 0
        for texto, fx, fy, color, posicion in self.notas:
            if posicion is None:
                self._caja_nota(qp, fx * self.width(), fy * self.height(), texto, color, 15)
                continue
            xy = en_pantalla.get(k)
            k += 1
            if xy is not None and 0 <= xy[0] <= self.width() and 0 <= xy[1] <= self.height():
                self._caja_nota(qp, *xy, texto, color, 11, sobre_punto=True)

    def _paint_callout(self, qp, idx, s):
        """`callout` = [título, (etiqueta, valor), ...]; se dibuja como una nota unida a la galería."""
        if not self.callout or self.sel < 0:
            return
        pos = np.nonzero(idx == self.sel)[0]
        if not len(pos):
            return
        x1, y1, x2, y2 = s[pos[0]]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        texto = "\n".join([self.callout[0]] + [f"{k}: {v}" for k, v in self.callout[1:]])
        font = QFont("Segoe UI")
        font.setPixelSize(12)
        fm = QFontMetricsF(font)
        lineas = texto.split("\n")
        w = max(fm.horizontalAdvance(t) for t in lineas) + 14
        h = len(lineas) * fm.lineSpacing() + 10
        bx = min(max(mx + 26, 8), self.width() - w - 8)
        by = min(max(my - h - 26, 8), self.height() - h - 8)
        avoid = [o.geometry() for o in self.overlays if o.isVisible()]
        if any(QRectF(bx, by, w, h).intersects(QRectF(g)) for g in avoid):
            bx = min(max(mx - 26 - w, 8), self.width() - w - 8)
        qp.setPen(QPen(QColor("#ffffff"), 1.5))
        qp.drawLine(QPointF(mx, my), QPointF(bx + w / 2, by + h))
        self._caja_nota(qp, bx, by, texto, (0, 0, 160), 12)

    def _paint_gizmo(self, qp):
        """Ejes con flecha 3D (X verde, Y rojo, Z azul y esfera blanca en el origen) abajo a la derecha."""
        eye, f, right, up = self._basis()
        o = QPointF(self.width() - 90, self.height() - 62)
        items = []
        for vec, col, lab in (([1, 0, 0], "#1f9d1f", "X"), ([0, 1, 0], "#e00000", "Y"), ([0, 0, 1], "#0000f0", "Z")):
            v = np.array(vec, float)
            items.append((float(v @ f), float(v @ right), float(v @ up), col, lab))
        items.sort(reverse=True)
        fuente = QFont("Segoe UI")
        fuente.setPixelSize(22)
        fuente.setBold(True)
        for _dz, x, y, col, lab in items:
            d = QPointF(x, -y)
            largo = float(np.hypot(d.x(), d.y()))
            if largo < 0.05:
                d = QPointF(0.0, -0.05)
                largo = 0.05
            u = QPointF(d.x() / largo, d.y() / largo)
            tip = QPointF(o.x() + 46 * d.x(), o.y() + 46 * d.y())
            base = QPointF(tip.x() - 16 * u.x(), tip.y() - 16 * u.y())
            n = QPointF(-u.y(), u.x())
            qp.setPen(QPen(QColor(col).darker(140), 7, Qt.SolidLine, Qt.RoundCap))
            qp.drawLine(o, base)
            qp.setPen(QPen(QColor(col), 4.5, Qt.SolidLine, Qt.RoundCap))
            qp.drawLine(o, base)
            qp.setPen(Qt.NoPen)
            qp.setBrush(QColor(col))
            qp.drawPolygon(QPolygonF([tip, QPointF(base.x() + 8 * n.x(), base.y() + 8 * n.y()),
                                      QPointF(base.x() - 8 * n.x(), base.y() - 8 * n.y())]))
            ruta = QPainterPath()
            ruta.addText(tip.x() + 16 * u.x() - 8, tip.y() + 16 * u.y() + 8, fuente, lab)
            qp.strokePath(ruta, QPen(QColor(0, 0, 0), 3))
            qp.fillPath(ruta, QColor(col))
        qp.setPen(Qt.NoPen)
        qp.setBrush(QColor("#e8f6fb"))
        qp.drawEllipse(o, 6, 6)

    def _paint_overlays(self, qp: QPainter, soft_selection: bool):
        """Lo que va encima de la escena 3D: capa de etiquetas, selección, notas, callout y gizmo."""
        idx, s, zm = self._project_red()
        if len(idx):
            self._paint_layer(qp, idx, s, zm)
            if soft_selection and len(self.pista_idx):
                self._paint_pista_soft(qp, idx, s)
            (self._paint_selection_soft if soft_selection else self._paint_selection)(qp, idx, s)
        self._paint_notas(qp)
        if len(idx):
            self._paint_callout(qp, idx, s)
        self._paint_gizmo(qp)

    def _paint_software_scene(self, qp: QPainter):
        qp.setRenderHint(QPainter.Antialiasing, True)
        self._paint_sky(qp)
        if self.show_grid:
            self._paint_grid(qp)
        idx, s, zm = self._project_red()
        if len(idx):
            self._paint_network_soft(qp, idx, s, zm)
        self._paint_overlays(qp, soft_selection=True)

    # ------------------------------------------------------------ interacción
    def _begin_interacting(self):
        self._interacting = True
        self._idle.start()

    def _end_interacting(self):
        if self._interacting:
            self._interacting = False
            self.update()

    def _cursor_world(self, px: float, py: float):
        eye, f, right, up = self._basis()
        F = self._focal()
        d = f + ((px - self.width() / 2) / F) * right - ((py - self.height() / 2) / F) * up
        if abs(d[2]) < 1e-6:
            return None
        t = (self.target[2] - eye[2]) / d[2]
        if t <= 0 or t > self.dist * 50:
            return None
        p = eye + t * d
        return float(p[0]), float(p[1]), float(self.target[2])

    def mousePressEvent(self, ev):
        self._press = (ev.position(), ev.button(), self.yaw, self.pitch, self.target.copy())
        self._moved = False
        self._auto_fit = False
        if self._anim is not None:
            self._anim.stop()

    def mouseMoveEvent(self, ev):
        if self._press is None:
            self.cursor_moved.emit(self._cursor_world(ev.position().x(), ev.position().y()))
            return
        p0, btn, yaw0, pitch0, tgt0 = self._press
        d = ev.position() - p0
        if abs(d.x()) + abs(d.y()) > 3:
            self._moved = True
        if not self._moved:
            return
        self._interacting = True
        ambos = bool(ev.buttons() & Qt.LeftButton) and bool(ev.buttons() & Qt.RightButton)      # «izquierda + derecha» panea (recursos de Ventsim)
        pan = btn in (Qt.RightButton, Qt.MiddleButton) or ambos or (ev.modifiers() & Qt.ShiftModifier) or self.pan_activo
        if pan:
            eye, f, right, up = self._basis()
            k = self.dist / self._focal()
            self.target = tgt0 - right * d.x() * k + up * d.y() * k
        else:
            self.yaw = yaw0 - d.x() * 0.008
            self.pitch = float(np.clip(pitch0 + d.y() * 0.008, -math.pi / 2 + 0.02, math.pi / 2 - 0.02))
        self.update()

    def mouseReleaseEvent(self, ev):
        was = self._interacting
        self._interacting = False
        if was:
            self.update()
        if self._press is not None and not self._moved and self._press[1] == Qt.LeftButton:
            i = self.pick(ev.position().x(), ev.position().y())
            self.sel = i
            self.selected.emit(i)
            self.update()
        self._press = None

    def leaveEvent(self, _ev):
        self.cursor_moved.emit(None)

    def mouseDoubleClickEvent(self, _ev):
        self.fit()

    def wheelEvent(self, ev):
        steps = ev.angleDelta().y() / 120.0
        self._auto_fit = False
        base = self.dist if self._dist_objetivo is None else self._dist_objetivo
        self._dist_objetivo = float(np.clip(base / ZOOM_POR_MUESCA ** steps, self.radius * 0.003, self.radius * 60))
        if not self._zoom.isActive():
            self._zoom.start()

    def _paso_zoom(self):
        """Acerca la cámara hacia la distancia pedida por la rueda, un tramo por fotograma, para que el zoom sea fluido."""
        restante = self._dist_objetivo - self.dist
        if abs(restante) < self.dist * 0.002:
            self.dist, self._dist_objetivo = self._dist_objetivo, None
            self._zoom.stop()
            self._end_interacting()
        else:
            self.dist += restante * SUAVIZADO_ZOOM
            self._begin_interacting()
        self.update()

    def keyPressEvent(self, ev):
        k = ev.key()
        if k in (Qt.Key_Home, Qt.Key_F):
            self.fit()
        elif k == Qt.Key_Left:
            self.vista_rapida(-1)
        elif k == Qt.Key_Right:
            self.vista_rapida(1)
        elif k == Qt.Key_Plus:
            self.dist *= 0.85
            self.update()
        elif k == Qt.Key_Minus:
            self.dist /= 0.85
            self.update()
        elif k == Qt.Key_1:
            self.view_top()
        elif k == Qt.Key_2:
            self.view_front()
        elif k == Qt.Key_3:
            self.view_side()
        elif k == Qt.Key_4:
            self.view_iso()

    def pick(self, px: float, py: float, tol: float = 10.0) -> int:
        idx, s, zm = self._project_red()
        if len(idx) == 0:
            return -1
        x1, y1, x2, y2 = s[:, 0], s[:, 1], s[:, 2], s[:, 3]
        dx, dy = x2 - x1, y2 - y1
        l2 = dx * dx + dy * dy
        t = np.where(l2 > 1e-9, ((px - x1) * dx + (py - y1) * dy) / np.where(l2 > 1e-9, l2, 1), 0.0)
        t = np.clip(t, 0, 1)
        d = np.hypot(px - (x1 + t * dx), py - (y1 + t * dy))
        d = d - (self._wpx(idx, zm) / 2 if self.tubes else 1.0)
        k = int(np.argmin(d))
        return int(idx[k]) if d[k] <= tol else -1

    def screenshot(self, path: str) -> bool:
        return self.grab().save(path)

    def render_mode(self) -> str:
        return "software"


# ============================================================================ respaldo por software
class SoftwareViewport(ViewportCore, QWidget):
    selected = Signal(int)
    cursor_moved = Signal(object)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self._init_core()

    def resizeEvent(self, ev):
        QWidget.resizeEvent(self, ev)
        if self._auto_fit:
            self.fit()

    def paintEvent(self, _ev):
        qp = QPainter(self)
        self._paint_software_scene(qp)
        qp.end()


# ============================================================================ GPU (OpenGL)
_VS_TUBE = """
attribute vec3 aAxis; attribute vec3 aDir; attribute float aRad; attribute float aT; attribute float aLen;
attribute vec4 aCol; attribute float aFlow; attribute vec3 aAx;
uniform mat4 uMvp; uniform vec3 uEye; uniform vec3 uFwd; uniform float uPxMin; uniform float uRadScale;
varying vec3 vN; varying vec3 vPos; varying vec4 vCol; varying float vDepth; varying float vS; varying float vFlow; varying float vPer;
varying vec3 vAx;
void main(){
  float depth = max(dot(aAxis - uEye, uFwd), 0.01);
  float r = max(aRad * uRadScale, uPxMin * depth);
  vec3 p = aAxis + aDir * r;
  vPos = p; vN = aDir; vCol = aCol; vDepth = depth;
  vS = aT * aLen; vFlow = aFlow; vAx = aAx;
  vPer = max(aRad * uRadScale * 10.0, depth * uPxMin * 26.0);
  gl_Position = uMvp * vec4(p, 1.0);
}
"""
_FS_TUBE = """
uniform vec3 uEye; uniform vec3 uLight; uniform vec3 uFog; uniform vec2 uFogRange; uniform vec4 uOverride;
uniform float uTrans; uniform float uTime;
varying vec3 vN; varying vec3 vPos; varying vec4 vCol; varying float vDepth; varying float vS; varying float vFlow; varying float vPer;
varying vec3 vAx;
void main(){
  if (vCol.a < 0.5) discard;
  vec3 N = normalize(vN);
  vec3 V = normalize(uEye - vPos);
  float ndl = max(dot(N, uLight), 0.0);
  float ndv = max(dot(N, V), 0.0);
  bool sel = uOverride.a > 0.5;
  vec3 base = sel ? uOverride.rgb : vCol.rgb;
  float diff = 0.62 + 0.46 * ndl;
  vec3 H = normalize(uLight + V);
  float spec = pow(max(dot(N, H), 0.0), 30.0) * 0.12;
  float rim = mix(0.58, 1.0, smoothstep(0.0, 0.40, ndv));
  vec3 c = base * diff * rim + vec3(spec) * rim;
  float alpha = sel ? 1.0 : mix(uTrans, 1.0, pow(1.0 - ndv, 2.5));
  if (!sel && abs(vFlow) > 0.01) {
    // flechas que avanzan por la galería (Ventsim real: triángulos oscuros con degradado, en el sentido del caudal)
    float a = fract((vS - vFlow * uTime) / vPer);
    if (vFlow < 0.0) a = 1.0 - a;
    float lat = abs(dot(N, normalize(cross(normalize(vAx), V))));
    float largo = 0.30;
    float dentro = smoothstep(0.0, 0.06, (largo - a) / largo * 0.92 - lat) * smoothstep(0.0, 0.015, a);
    vec3 flecha = mix(vec3(0.05), vec3(0.60), clamp(a / largo, 0.0, 1.0));
    c = mix(c, flecha, dentro);
    alpha = max(alpha, dentro);
  }
  float f = clamp((vDepth - uFogRange.x) / max(uFogRange.y - uFogRange.x, 0.0001), 0.0, 1.0) * 0.38;
  c = mix(c, uFog, f);
  gl_FragColor = vec4(c, alpha);
}
"""
_VS_GRID = """
attribute vec3 aPos; uniform mat4 uMvp; varying vec3 vP;
void main(){ vP = aPos; gl_Position = uMvp * vec4(aPos, 1.0); }
"""
_FS_GRID = """
uniform vec4 uColor; uniform vec3 uTarget; uniform float uRadius; varying vec3 vP;
void main(){
  float d = distance(vP.xy, uTarget.xy) / uRadius;
  float fade = pow(clamp(1.0 - d, 0.0, 1.0), 0.8);
  gl_FragColor = vec4(uColor.rgb, uColor.a * (0.55 + 0.45 * fade));
}
"""
_VS_MESH = """
attribute vec3 aPos; attribute vec3 aNor; attribute vec3 aCol;
uniform mat4 uMvp; varying vec3 vN; varying vec3 vC;
void main(){ vN = aNor; vC = aCol; gl_Position = uMvp * vec4(aPos, 1.0); }
"""
_FS_MESH = """
uniform vec3 uLight; uniform float uAlpha; varying vec3 vN; varying vec3 vC;
void main(){
  float d = 0.42 + 0.66 * abs(dot(normalize(vN), uLight));
  gl_FragColor = vec4(vC * d, uAlpha);
}
"""
_VS_SKY = "attribute vec2 aP; void main(){ gl_Position = vec4(aP, 0.0, 1.0); }"
_FS_SKY = """
uniform float uH; uniform float uHor; uniform vec3 uTop;
void main(){
  float t = clamp((uH - gl_FragCoord.y) / uH, 0.0, 1.0);
  gl_FragColor = vec4(mix(uTop, vec3(0.004, 0.008, 0.012), t), 1.0);
}
"""


class GLViewport(ViewportCore, QOpenGLWidget):
    selected = Signal(int)
    cursor_moved = Signal(object)

    def __init__(self, parent=None):
        QOpenGLWidget.__init__(self, parent)
        self.setFormat(default_format())
        self._init_core()
        self._gl_ok: bool | None = None            # None = sin inicializar; False = respaldo por software
        self._geom_dirty = True
        self._col_dirty = True
        self._mesh_dirty = True
        self._grid_dirty = True
        self._n = 0
        self._mesh_n = 0
        self._mesh_opacas = 0
        self._grid_minor_n = 0
        self._grid_major_n = 0
        self._grid_radius = 1.0

    def render_mode(self) -> str:
        return "gpu" if self._gl_ok else ("software" if self._gl_ok is False else "iniciando")

    # ------------------------------------------------------------ inicialización
    def initializeGL(self):
        try:
            self._f = self.context().functions()
            es = self.context().isOpenGLES()
            ver, pre = ("", "precision highp float;\n") if es else ("#version 120\n", "")

            def prog(vs, fs):
                p = QOpenGLShaderProgram(self)
                ok = (p.addShaderFromSourceCode(QOpenGLShader.Vertex, ver + vs)
                      and p.addShaderFromSourceCode(QOpenGLShader.Fragment, ver + pre + fs) and p.link())
                if not ok:
                    raise RuntimeError(p.log())
                return p
            self._p_tube = prog(_VS_TUBE, _FS_TUBE)
            self._p_grid = prog(_VS_GRID, _FS_GRID)
            self._p_sky = prog(_VS_SKY, _FS_SKY)
            self._p_mesh = prog(_VS_MESH, _FS_MESH)
            self._vb_geom = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
            self._vb_col = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
            self._vb_flow = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
            self._vb_grid = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
            self._vb_sky = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
            self._vb_mesh = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
            for b in (self._vb_geom, self._vb_col, self._vb_flow, self._vb_grid, self._vb_sky, self._vb_mesh):
                b.create()
            self._vb_sky.bind()
            quad = np.array([-1, -1, 1, -1, -1, 1, 1, 1], np.float32).tobytes()
            self._vb_sky.allocate(quad, len(quad))
            self._vb_sky.release()
            self._gl_ok = True
            self._geom_dirty = self._col_dirty = True
        except Exception:  # noqa: BLE001
            self._gl_ok = False

    # ------------------------------------------------------------ geometría (tubos)
    def _geom_changed(self):
        super()._geom_changed()
        self._geom_dirty = True
        self._col_dirty = True

    def _colors_changed(self):
        self._col_dirty = True

    def _mallas_changed(self):
        self._mesh_dirty = True

    def _rejilla_cambio(self):
        self._grid_dirty = True

    def _upload_mallas(self):
        """Superficies de referencia: posición, normal plana por triángulo y color por vértice (36 bytes por vértice)."""
        partes = []
        ordenadas = [m for m in self.mallas if not m.translucida] + [m for m in self.mallas if m.translucida]
        self._mesh_opacas = sum(len(m.vertices) for m in self.mallas if not m.translucida)
        for m in ordenadas:
            tri = m.vertices.reshape(-1, 3, 3)
            n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
            largo = np.linalg.norm(n, axis=1, keepdims=True)
            n = np.where(largo > 1e-9, n / np.maximum(largo, 1e-9), np.array([0.0, 0.0, 1.0]))
            partes.append(np.hstack([m.vertices, np.repeat(n, 3, axis=0), m.colores / 255.0]).astype(np.float32))
        datos = np.vstack(partes) if partes else np.zeros((0, 9), np.float32)
        self._mesh_n = len(datos)
        raw = datos.tobytes()
        self._vb_mesh.bind()
        self._vb_mesh.allocate(raw, len(raw))
        self._vb_mesh.release()
        self._mesh_dirty = False

    def _flujo_en_gpu(self) -> bool:
        return bool(self._gl_ok)

    def _build_tube_mesh(self) -> np.ndarray:
        """(N*48, 9) float32: [eje(3), dirección(3), radio, posición 0..1 a lo largo, longitud]. Tubo de 8 caras con
        normales suaves (normal = dirección)."""
        A, B = self.p1, self.p2
        n = len(A)
        d = B - A
        L = np.linalg.norm(d, axis=1)
        d = np.where(L[:, None] > 1e-9, d / np.maximum(L[:, None], 1e-9), np.array([0.0, 0.0, 1.0]))
        helper = np.where(np.abs(d[:, 2:3]) < 0.9, np.array([[0.0, 0.0, 1.0]]), np.array([[1.0, 0.0, 0.0]]))
        u = np.cross(d, helper)
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        v = np.cross(d, u)
        th = np.arange(SIDES) * (2 * np.pi / SIDES)
        ring = u[:, None, :] * np.cos(th)[None, :, None] + v[:, None, :] * np.sin(th)[None, :, None]   # (N,8,3)
        k0 = np.arange(SIDES)
        k1 = (k0 + 1) % SIDES
        end_pat = np.array([0, 1, 1, 0, 1, 0])               # por cuadrilátero: [A,k0][B,k0][B,k1][A,k0][B,k1][A,k1]
        ends = np.stack([A, B])                              # (2,N,3)
        axis = np.broadcast_to(ends[end_pat].transpose(1, 0, 2)[:, None, :, :], (n, SIDES, 6, 3))
        kk = np.stack([k0, k0, k1, k0, k1, k1], axis=1)      # (8,6)
        dirs = ring[:, kk, :]                                # (N,8,6,3)
        rad = np.broadcast_to((self.widths / 2.0)[:, None, None, None], (n, SIDES, 6, 1))
        a_lo_largo = np.broadcast_to(end_pat.astype(float)[None, None, :, None], (n, SIDES, 6, 1))
        largo = np.broadcast_to(L[:, None, None, None], (n, SIDES, 6, 1))
        eje = np.broadcast_to(d[:, None, None, :], (n, SIDES, 6, 3))
        return np.concatenate([axis, dirs, rad, a_lo_largo, largo, eje], axis=3).reshape(n * VERTS_PER_SEG, FLOATS_VERTICE).astype(np.float32)

    def _upload(self):
        self._n = len(self.p1)
        if self._n:
            mesh = self._build_tube_mesh().tobytes()
            self._vb_geom.bind()
            self._vb_geom.allocate(mesh, len(mesh))
            self._vb_geom.release()
        self._geom_dirty = False

    def _upload_rejilla(self):
        A, B, major = self._grid_lines()
        r = self.rejilla
        self._grid_radius = math.hypot(r.sx, r.sy) * 0.75
        pairs = np.stack([A, B], axis=1)
        lines = np.concatenate([pairs[~major].reshape(-1, 3), pairs[major].reshape(-1, 3)]).astype(np.float32)
        self._grid_minor_n = int((~major).sum()) * 2
        self._grid_major_n = int(major.sum()) * 2
        raw = lines.tobytes()
        self._vb_grid.bind()
        self._vb_grid.allocate(raw, len(raw))
        self._vb_grid.release()
        self._grid_dirty = False

    def _upload_colors(self):
        if self._n:
            rgb = self._seg_colors(np.arange(self._n))
            col = np.empty((self._n, 4), np.uint8)
            col[:, :3] = rgb
            col[:, 3] = np.where(self.visible, 255, 0)
            raw = np.repeat(col, VERTS_PER_SEG, axis=0).tobytes()
            self._vb_col.bind()
            self._vb_col.allocate(raw, len(raw))
            self._vb_col.release()
            raw = np.repeat(self._velocidad_animada(), VERTS_PER_SEG).astype(np.float32).tobytes()
            self._vb_flow.bind()
            self._vb_flow.allocate(raw, len(raw))
            self._vb_flow.release()
        self._col_dirty = False

    def _velocidad_animada(self) -> np.ndarray:
        """Velocidad con signo que mueve la animación: la real recortada a un rango visible; 0 = sin animar."""
        if self.flujo is None or len(self.flujo) != self._n or not self.show_arrows:
            return np.zeros(self._n)
        v = np.abs(self.flujo)
        visible = np.clip(v, VEL_FLUJO_MIN, VEL_FLUJO_MAX) * FACTOR_ANIMACION
        return np.where(v > 1e-6, np.sign(self.flujo) * visible, 0.0)

    # ------------------------------------------------------------ matrices
    def _mvp(self):
        eye, f, right, up = self._basis()
        V = np.eye(4)
        V[0, :3], V[1, :3], V[2, :3] = right, up, -f
        V[0, 3], V[1, 3], V[2, 3] = -right @ eye, -up @ eye, f @ eye
        near = self._near()
        far = self.dist + self.radius * 6 + 100.0
        fy = 1.0 / math.tan(math.radians(FOV_GRADOS) / 2)
        asp = max(self.width(), 1) / max(self.height(), 1)
        P = np.zeros((4, 4))
        P[0, 0], P[1, 1] = fy / asp, fy
        P[2, 2], P[2, 3] = (far + near) / (near - far), 2 * far * near / (near - far)
        P[3, 2] = -1.0
        return QMatrix4x4(*(P @ V).flatten().tolist()), eye, f, right, up

    # ------------------------------------------------------------ pintura
    def resizeEvent(self, ev):
        QOpenGLWidget.resizeEvent(self, ev)
        if self._auto_fit:
            self.fit()

    def paintGL(self):
        if self._gl_ok is False:                       # respaldo: toda la escena por software sobre el mismo widget
            qp = QPainter(self)
            self._paint_software_scene(qp)
            qp.end()
            return
        f = self._f
        dpr = self.devicePixelRatioF()
        Wd, Hd = int(self.width() * dpr), int(self.height() * dpr)
        if self._geom_dirty:
            self._upload()
        if self._col_dirty:
            self._upload_colors()
        if self._mesh_dirty:
            self._upload_mallas()
        if self._grid_dirty:
            self._upload_rejilla()
        f.glViewport(0, 0, Wd, Hd)
        f.glDisable(GL_DEPTH_TEST)
        f.glDisable(GL_BLEND)
        f.glClearColor(0.05, 0.06, 0.09, 1.0)
        f.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self._draw_sky(f, Hd, dpr)
        mvp, eye, fwd, right, up = self._mvp()
        if self.show_referencias and self._mesh_n:
            self._draw_mallas(f, mvp, fwd, right, up)
        if self.show_grid:
            self._draw_grid(f, mvp)
        if self._n:
            self._draw_tubes(f, mvp, eye, fwd, right, up, Hd, dpr)
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing, True)
        self._paint_overlays(qp, soft_selection=False)
        qp.end()

    def _draw_sky(self, f, Hd, dpr):
        sp = self._p_sky
        sp.bind()
        _set(sp, "uH", float(Hd))
        _set(sp, "uHor", float(self._horizon_y() * dpr))
        c = QColor(self.cielo)
        _set(sp, "uTop", c.redF(), c.greenF(), c.blueF())
        self._vb_sky.bind()
        loc = sp.attributeLocation("aP")
        sp.enableAttributeArray(loc)
        sp.setAttributeBuffer(loc, GL_FLOAT, 0, 2, 8)
        f.glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        sp.disableAttributeArray(loc)
        self._vb_sky.release()
        sp.release()

    def _draw_mallas(self, f, mvp, fwd, right, up):
        f.glEnable(GL_DEPTH_TEST)
        f.glDepthFunc(GL_LESS)
        mp = self._p_mesh
        mp.bind()
        _set(mp, "uMvp", mvp)
        luz = fwd * -0.55 + up * 0.75 - right * 0.45
        luz /= np.linalg.norm(luz)
        _set(mp, "uLight", float(luz[0]), float(luz[1]), float(luz[2]))
        self._vb_mesh.bind()
        atributos = [mp.attributeLocation(n) for n in ("aPos", "aNor", "aCol")]
        for loc, off in zip(atributos, (0, 12, 24)):
            mp.enableAttributeArray(loc)
            mp.setAttributeBuffer(loc, GL_FLOAT, off, 3, 36)
        f.glDisable(GL_BLEND)
        f.glDepthMask(True)
        _set(mp, "uAlpha", 1.0)
        f.glDrawArrays(GL_TRIANGLES, 0, self._mesh_opacas)
        if self._mesh_n > self._mesh_opacas:                  # capas sin textura: translúcidas, sin escribir profundidad
            f.glEnable(GL_BLEND)
            f.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            f.glDepthMask(False)
            _set(mp, "uAlpha", float(self.opacidad_referencias))
            f.glDrawArrays(GL_TRIANGLES, self._mesh_opacas, self._mesh_n - self._mesh_opacas)
        for loc in atributos:
            mp.disableAttributeArray(loc)
        self._vb_mesh.release()
        mp.release()
        f.glDepthMask(True)
        f.glDisable(GL_BLEND)

    def _draw_grid(self, f, mvp):
        f.glEnable(GL_DEPTH_TEST)
        f.glDepthFunc(GL_LEQUAL)
        f.glEnable(GL_BLEND)
        f.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        f.glDepthMask(False)
        gp = self._p_grid
        gp.bind()
        _set(gp, "uMvp", mvp)
        _set(gp, "uTarget", float(self.target[0]), float(self.target[1]), float(self.target[2]))
        _set(gp, "uRadius", float(self._grid_radius))
        self._vb_grid.bind()
        loc = gp.attributeLocation("aPos")
        gp.enableAttributeArray(loc)
        gp.setAttributeBuffer(loc, GL_FLOAT, 0, 3, 12)
        c = QColor(self.color_rejilla)
        _set(gp, "uColor", c.redF(), c.greenF(), c.blueF(), 0.85)
        f.glDrawArrays(GL_LINES, 0, self._grid_minor_n)
        _set(gp, "uColor", c.redF(), c.greenF(), c.blueF(), 1.0)
        f.glDrawArrays(GL_LINES, self._grid_minor_n, self._grid_major_n)
        gp.disableAttributeArray(loc)
        self._vb_grid.release()
        gp.release()
        f.glDepthMask(True)
        f.glDisable(GL_BLEND)

    def _draw_tubes(self, f, mvp, eye, fwd, right, up, Hd, dpr):
        f.glEnable(GL_DEPTH_TEST)
        f.glDepthFunc(GL_LESS)
        tp = self._p_tube
        tp.bind()
        _set(tp, "uMvp", mvp)
        _set(tp, "uEye", float(eye[0]), float(eye[1]), float(eye[2]))
        _set(tp, "uFwd", float(fwd[0]), float(fwd[1]), float(fwd[2]))
        light = fwd * -0.55 + up * 0.75 - right * 0.45
        light /= np.linalg.norm(light)
        _set(tp, "uLight", float(light[0]), float(light[1]), float(light[2]))
        fog = SKY_FOG / 255.0
        _set(tp, "uFog", float(fog[0]), float(fog[1]), float(fog[2]))
        _set(tp, "uFogRange", float(max(self.dist - self.radius, 0.0)), float(self.dist + self.radius * 1.6))
        F_dev = (Hd / 2) / math.tan(math.radians(FOV_GRADOS) / 2)
        min_px = 1.0 if self.tubes else 0.8
        _set(tp, "uPxMin", float(min_px * dpr / F_dev))
        scale = self.tube_scale if self.tubes else 0.0
        _set(tp, "uRadScale", float(scale))
        _set(tp, "uOverride", 0.0, 0.0, 0.0, 0.0)
        _set(tp, "uTrans", TRANSPARENCIA_TUBO)
        _set(tp, "uTime", float(self._reloj.elapsed() % 600000) / 1000.0)
        self._bind_tube_attrs(tp)
        f.glEnable(GL_BLEND)
        f.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        f.glDepthMask(False)
        f.glDrawArrays(GL_TRIANGLES, 0, self._n * VERTS_PER_SEG)
        f.glDepthMask(True)
        if len(self.pista_idx):                        # pista: sus galerías, opacas y algo más gruesas, con el color del proyecto
            _set(tp, "uOverride", *(c / 255.0 for c in self.pista_color), 1.0)
            _set(tp, "uRadScale", float(scale * 1.15 + 0.1))
            f.glDepthFunc(GL_LEQUAL)
            for i in self.pista_idx:
                f.glDrawArrays(GL_TRIANGLES, int(i) * VERTS_PER_SEG, VERTS_PER_SEG)
        if 0 <= self.sel < self._n:                    # selección: tubo blanco opaco algo más grueso
            _set(tp, "uOverride", 1.0, 1.0, 1.0, 1.0)
            _set(tp, "uRadScale", float(scale * 1.25 + 0.15))
            f.glDepthFunc(GL_LEQUAL)
            f.glDrawArrays(GL_TRIANGLES, self.sel * VERTS_PER_SEG, VERTS_PER_SEG)
        for loc in self._attr.values():
            tp.disableAttributeArray(loc)
        tp.release()
        f.glDisable(GL_BLEND)
        f.glDisable(GL_DEPTH_TEST)

    def _bind_tube_attrs(self, tp):
        self._attr = {n: tp.attributeLocation(n) for n in ("aAxis", "aDir", "aRad", "aT", "aLen", "aAx", "aCol", "aFlow")}
        self._vb_geom.bind()
        for name, off, tup in (("aAxis", 0, 3), ("aDir", 12, 3), ("aRad", 24, 1), ("aT", 28, 1), ("aLen", 32, 1), ("aAx", 36, 3)):
            tp.enableAttributeArray(self._attr[name])
            tp.setAttributeBuffer(self._attr[name], GL_FLOAT, off, tup, 4 * FLOATS_VERTICE)
        self._vb_geom.release()
        self._vb_flow.bind()
        tp.enableAttributeArray(self._attr["aFlow"])
        tp.setAttributeBuffer(self._attr["aFlow"], GL_FLOAT, 0, 1, 4)
        self._vb_flow.release()
        self._vb_col.bind()
        tp.enableAttributeArray(self._attr["aCol"])
        tp.setAttributeBuffer(self._attr["aCol"], GL_UNSIGNED_BYTE, 0, 4, 4)
        self._vb_col.release()


# alias histórico: las pruebas sin pantalla usan el visor por software
Viewport3D = SoftwareViewport


def create_viewport(parent=None):
    """GPU si se puede (y no se fuerza `NVS_RENDER=software`); si no, respaldo por software."""
    if gl_available():
        return GLViewport(parent)
    return SoftwareViewport(parent)
