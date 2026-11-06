"""Escala de color por umbrales, editable, con el esquema observado en «Exponer» (docs/evidence/E-004).

Hay n umbrales ascendentes t0 < … < tn-1 y n+2 colores: uno para «< t0», uno por umbral y uno para «> tn-1».
Modo continuo (el de la referencia): el color se interpola entre los colores de los umbrales vecinos.
Modo por bandas: un valor toma el color del mayor umbral que no supera.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# colores observados en «Exponer» (docs/evidence/ui_spec.json → exponer.colores), de bajo a alto
PALETTE_8 = ["#000040", "#000080", "#00ffff", "#00ff00", "#ffff00", "#ff0000", "#e400e4", "#ff96ff"]


@dataclass
class ColorScale:
    title: str
    unit: str
    thresholds: list[float]
    colors: list[str]                  # len = len(thresholds) + 2
    banded: bool = False
    nodata: str = "#7d8794"
    _defaults: tuple = field(default=None, repr=False)

    def __post_init__(self):
        assert len(self.colors) == len(self.thresholds) + 2
        if self._defaults is None:
            self._defaults = (list(self.thresholds), list(self.colors))

    @property
    def base_thresholds(self) -> list[float]:
        return self._defaults[0]

    def reset(self):
        self.thresholds, self.colors = list(self._defaults[0]), list(self._defaults[1])

    def set_threshold(self, i: int, v: float):
        self.thresholds[i] = v
        self.thresholds.sort()           # mantiene el orden creciente (los colores siguen a su posición)

    def band_index(self, v: np.ndarray) -> np.ndarray:
        """Índice 0..n+1 (0 = por debajo del primer umbral, n+1 = por encima del último)."""
        th = np.asarray(self.thresholds)
        idx = np.searchsorted(th, v, side="right")
        return np.where(v > th[-1], len(th) + 1, idx)

    def rgb(self, values: np.ndarray) -> np.ndarray:
        """Devuelve (N,3) uint8. NaN → color de «sin dato»."""
        v = np.asarray(values, float)
        out = np.empty((len(v), 3), np.uint8)
        fin = np.isfinite(v)
        out[~fin] = _rgb(self.nodata)
        cols = np.array([_rgb(c) for c in self.colors], float)
        if self.banded:
            out[fin] = cols[self.band_index(v[fin])].astype(np.uint8)
            return out
        th = np.asarray(self.thresholds)
        for ch in range(3):
            interior = np.interp(v[fin], th, cols[1:-1, ch])
            interior = np.where(v[fin] < th[0], cols[0, ch], np.where(v[fin] > th[-1], cols[-1, ch], interior))
            out[fin, ch] = interior.round().astype(np.uint8)
        return out

    def legend(self) -> list[tuple[str, str]]:
        """[(color, texto)] de arriba (valores altos) a abajo, como la leyenda de «Exponer»."""
        th = self.thresholds
        rows = [(self.colors[-1], f"> {th[-1]:.1f}")]
        rows += [(self.colors[k + 1], f"{th[k]:.1f}") for k in range(len(th) - 1, -1, -1)]
        rows.append((self.colors[0], f"< {th[0]:.1f}"))
        return rows


def default_scales() -> dict[str, ColorScale]:
    P = PALETTE_8
    return {
        "Q": ColorScale("Cantidad", "m³/s", [0.0, 10.0, 25.0, 50.0, 100.0, 250.0], P),
        "V": ColorScale("Velocidad", "m/s", [0.0, 1.0, 2.5, 5.0, 8.0, 12.0], P),
        "DP": ColorScale("Pérdida de presión", "Pa", [0.0, 25.0, 100.0, 250.0, 500.0, 1000.0], P),
        "DIFF": ColorScale("Diferencia motor − archivo", "%", [0.0, 0.01, 0.1, 1.0, 5.0, 20.0],
                           ["#1b9e4b", "#1b9e4b", "#b8d94a", "#f2d21b", "#f08a1c", "#e3262b", "#8e1a8f", "#4a0a4a"]),
    }
