"""Construcción de una red de ventilación a partir de las filas de un modelo .vsm (E-001).

Reglas de interpretación (hipótesis verificadas contra los archivos de ejemplo, ver docs/05):
  H1  Topología: dos extremos son el mismo nodo si coinciden en (X,Y,Z) redondeadas a 0,01 m.
  H1b Los nodos de grado 1 son bocas a presión de referencia 0.
  H2  Una galería con R >= 1000 y Q = 0 guardado está bloqueada (Q = 0 exacto).
  H3  Branch Flags & 0x4 marca caudal fijo (valor en `Quantity`).
  H4  La fuente de presión de un ventilador es `Static Pressure` en su punto de operación guardado.
  H4b Si `Fan Off` = True la fuente es 0 (el valor guardado es residual).
"""
from __future__ import annotations

import collections

from .network import Branch
from .vsmio import aligned_table, read_vsm


def fl(x: str) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def node_ids(rows: list[dict[str, str]]):
    ids: dict[tuple, int] = {}

    def nid(r, s):
        k = tuple(round(fl(r[c]), 2) for c in (f"X{s}", f"Y{s}", f"Z{s}"))
        return ids.setdefault(k, len(ids))

    pairs = [(nid(r, 1), nid(r, 2)) for r in rows]
    deg = collections.Counter(x for p in pairs for x in p)
    return pairs, len(ids), deg


def network_from_rows(rows: list[dict[str, str]]):
    """Devuelve (branches, n_nodos, nodos_fijos{nodo: presión})."""
    pairs, n, deg = node_ids(rows)
    branches = []
    for (a, b), r in zip(pairs, rows):
        R, Q = fl(r["Resistance"]), fl(r["Quantity"])
        closed = R >= 1000 and Q == 0
        fixed_q = Q if (int(fl(r["Branch Flags"])) & 4) and not closed else None
        src = 0.0 if r.get("Fan Off") == "True" else fl(r["Static Pressure"])  # H4b: ventilador apagado
        branches.append(Branch(a, b, R, source=src, closed=closed, fixed_q=fixed_q))
    fixed = {k: 0.0 for k, d in deg.items() if d == 1}
    return branches, n, fixed


def load_rows(path: str) -> list[dict[str, str]]:
    return aligned_table(read_vsm(path))


def model_density(v) -> float:
    d = [x for x in v.sections["AIRSIM"].rows if x != ["Description"]][0]
    return fl(d[13])


def network_predictive(v, rows):
    """Red con R calculada desde la geometría y fuentes de ventilador desde la CURVA (no desde valores guardados).

    Devuelve (branches, n_nodos, fijos, info) con info = contadores de qué se calculó y qué se tomó del archivo.
    Resistencias de tipo aún no descifrado (`Resistance Type` negativo o preset desconocido) usan el valor guardado.
    """
    from .fan import branch_source, parse_curves
    from .resistance import branch_resistance

    pairs, n, deg = node_ids(rows)
    rho = model_density(v)
    presets = {r[0]: fl(r[2]) for r in v.sections["RESISTANCES"].rows if len(r) > 3}
    curves = parse_curves(v.sections["FANS"].rows)
    info = collections.Counter()
    branches = []
    for (a, b), r in zip(pairs, rows):
        R_saved, Q_saved = fl(r["Resistance"]), fl(r["Quantity"])
        closed = R_saved >= 1000 and Q_saved == 0
        fixed_q = Q_saved if (int(fl(r["Branch Flags"])) & 4) and not closed else None
        rt = r["Resistance Type"]
        A, P = fl(r["Area"]), fl(r["Perimeter"])
        if (rt == "0" or rt in presets) and A > 0 and P > 0 and R_saved < 1000:
            R = branch_resistance(fl(r["kFactor"]), fl(r["Length"]), fl(r["shock factor"]), P, A, rho,
                                  0.0 if rt == "0" else presets[rt])
            info["R calculada"] += 1
            r_origin = "motor"
        else:
            R = R_saved
            info["R guardada (tipo no descifrado)"] += 1
            r_origin = "archivo"
        br = Branch(a, b, R, closed=closed, fixed_q=fixed_q, r_origin=r_origin)
        ft = r["Fan Type"]
        if ft not in ("", "0") and r["Fan Off"] == "True":
            br.fan_origin = "apagado"
        elif ft not in ("", "0"):
            if ft in curves and fl(r["Fan Speed"]) == 100 and r["Fan Config"] == "0":
                br.source_fn = branch_source(curves[ft], max(1, int(fl(r["Fan Numbers"]))))
                br.fan = (curves[ft].q, curves[ft].p, max(1, int(fl(r["Fan Numbers"]))))
                br.fan_origin = "curva"
                info["ventilador por curva"] += 1
            else:
                br.source = fl(r["Static Pressure"])
                br.fan_origin = "archivo"
                info["ventilador: presión guardada (config no descifrada)"] += 1
        branches.append(br)
    fixed = {k: 0.0 for k, d in deg.items() if d == 1}
    return branches, n, fixed, info
