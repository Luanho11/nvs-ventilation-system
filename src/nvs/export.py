"""Exportación de la tabla de resultados a CSV, con columnas de procedencia explícitas."""
from __future__ import annotations

import csv
from pathlib import Path

from .project import Project

COLUMNS = ["N", "Nombre", "Longitud_m", "Area_m2", "Perimetro_m",
           "R_archivo_Ns2m8", "R_motor_Ns2m8", "Origen_R_motor",
           "Q_archivo_m3s", "Q_motor_m3s", "dQ_m3s", "dQ_pct",
           "dp_archivo_Pa", "dp_motor_Pa", "Ventilador", "Origen_ventilador"]


def result_rows(p: Project) -> list[list]:
    out = []
    for a in p.airways:
        dq = dpct = None
        if a.saved_Q is not None and a.calc_Q is not None:
            dq = a.calc_Q - a.saved_Q
            dpct = 100.0 * dq / abs(a.saved_Q) if abs(a.saved_Q) >= 0.01 else None   # |Q archivo| ≥ 0,01 m³/s
        out.append([a.uid, a.name, a.length, a.area, a.perimeter, a.saved_R, a.calc_R, a.r_origin,
                    a.saved_Q, a.calc_Q, dq, dpct, a.saved_dp, a.calc_dp,
                    a.fan_type or ("nativo" if a.fan_curve else ""), a.fan_origin])
    return out


def export_csv(p: Project, path: str | Path) -> int:
    rows = result_rows(p)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # BOM: Excel abre bien los acentos
        w = csv.writer(f, delimiter=";")
        w.writerow([f"# Proyecto: {p.name} | tipo: {p.kind} | versión que guardó el archivo: {p.saved_version or '-'}"])
        w.writerow(["# Columnas *_archivo: valores leídos del archivo (resultado de VentSim). "
                    "Columnas *_motor: calculadas por el motor propio en esta sesión."])
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow(["" if v is None else (f"{v:.9g}" if isinstance(v, float) else v) for v in r])
    return len(rows)
