"""Resistencia aerodinámica de una galería (implementación propia, reglas observadas en E-001/D-RES-01).

    R = ( k · (L + Le) · P / A³  +  R_discreta ) · ρ / 1,2        [N·s²/m⁸]

k   factor de fricción de Atkinson a 1,2 kg/m³            [kg/m³ · … = N·s²/m⁴]
L   longitud de la galería [m];  Le longitud equivalente por pérdidas de choque [m]
P   perímetro [m];  A  área de la sección [m²]
R_discreta  resistencia de un preset discreto (puerta, regulador, tapón...)
ρ   densidad del aire de la galería (AIRSIM[13] si la simulación térmica está desactivada)
"""
from __future__ import annotations

RHO_REF = 1.2  # kg/m³, densidad de referencia de los factores k observada en los presets


def friction_resistance(k: float, length: float, equiv_length: float, perimeter: float, area: float) -> float:
    if area <= 0:
        raise ValueError("área no positiva")
    return k * (length + equiv_length) * perimeter / area**3


def branch_resistance(k: float, length: float, equiv_length: float, perimeter: float, area: float,
                      rho: float = RHO_REF, discrete: float = 0.0) -> float:
    return (friction_resistance(k, length, equiv_length, perimeter, area) + discrete) * rho / RHO_REF
