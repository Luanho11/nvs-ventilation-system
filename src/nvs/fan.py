"""Curvas características de ventilador (implementación propia; reglas observadas, ver docs/05 D-FAN-01).

Modelo observado:
  * La curva de presión estática es lineal a tramos entre los puntos de entrada (Q, P).
  * n unidades idénticas en paralelo: cada una mueve Q/n; la presión de la rama es P(Q/n).
  * Presión total = estática + ½·ρ·(Q/n / A_ventilador)², A = π·d²/4 con d el diámetro del preset.
  * Por debajo del primer punto la presión se mantiene constante (cierre del ventilador).
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass


@dataclass
class FanCurve:
    q: list[float]            # caudal por ventilador [m³/s], creciente
    p: list[float]            # presión estática [Pa]
    diameter: float = 0.0     # [m]
    rho_curve: float = 1.2    # densidad a la que está definida la curva [kg/m³]

    def static(self, q_unit: float) -> float:
        """Presión estática de una unidad con caudal q_unit (interpolación lineal, extremos constantes)."""
        qs, ps = self.q, self.p
        if q_unit <= qs[0]:
            return ps[0]
        if q_unit >= qs[-1]:
            return ps[-1]
        i = bisect.bisect_right(qs, q_unit) - 1
        t = (q_unit - qs[i]) / (qs[i + 1] - qs[i])
        return ps[i] + t * (ps[i + 1] - ps[i])

    def slope(self, q_unit: float) -> float:
        qs, ps = self.q, self.p
        if q_unit <= qs[0] or q_unit >= qs[-1]:
            return 0.0
        i = bisect.bisect_right(qs, q_unit) - 1
        return (ps[i + 1] - ps[i]) / (qs[i + 1] - qs[i])


def branch_source(curve: FanCurve, n_units: int):
    """Fuente de presión de la rama en función del caudal total: devuelve (S, dS/dQ)."""
    n = max(1, n_units)

    def fn(q: float) -> tuple[float, float]:
        # Para q <= 0 (flujo contra el ventilador) se mantiene la presión de cierre del ventilador (hipótesis H5,
        # sin observación aún: ver docs/05); la derivada es 0.
        if q <= 0:
            return curve.static(0.0), 0.0
        qu = q / n
        return curve.static(qu), curve.slope(qu) / n

    return fn


def parse_curves(fans_rows: list[list[str]]) -> dict[str, FanCurve]:
    """Extrae las curvas de la sección FANS: cabecera de 36 campos + filas de curva de 14 campos.

    Cabecera: [0]=id, [1]=nombre, [2]=diámetro, [7]=densidad de la curva.
    Fila de curva: [6]=Q de entrada, [7]=P de entrada (estática). Termina en la primera fila con Q=0 tras la 0.
    """
    out: dict[str, FanCurve] = {}
    cur: FanCurve | None = None
    for r in fans_rows:
        if len(r) >= 30:
            cur = FanCurve([], [], diameter=_f(r[2]), rho_curve=_f(r[7]) or 1.2)
            out[r[0]] = cur
        elif cur is not None and len(r) >= 8:
            qin, pin = _f(r[6]), _f(r[7])
            if (qin > 0 or not cur.q) and (not cur.q or qin > cur.q[-1]):
                cur.q.append(qin)
                cur.p.append(pin)
    return out


def _f(x: str) -> float:
    try:
        return float(x)
    except ValueError:
        return 0.0
