"""Comparación diferencial D-NET-01 (exploratoria): resolver con R y presión estática de ventilador guardadas.

Usa la `Resistance` y la `Static Pressure` (presión estática de ventilador en su punto de operación) que
VentSim guardó como entradas conocidas, y compara el caudal resuelto por NUESTRO solucionador con la
`Quantity` guardada por VentSim. Los nodos de grado 1 se toman como bocas a presión 0 (hipótesis H1).

Limitaciones conocidas (se levantan en pasos posteriores): no modela flujos fijos, NVP, densidad variable
ni curvas de ventilador.
"""
from __future__ import annotations

import collections
import sys

import numpy as np

from nvs.network import Branch, solve
from nvs.vsmio import aligned_table, read_vsm


def fl(x: str) -> float:
    try:
        return float(x)
    except ValueError:
        return 0.0


def build(rows):
    ids: dict[tuple, int] = {}

    def nid(r, s):
        k = tuple(round(fl(r[c]), 2) for c in (f"X{s}", f"Y{s}", f"Z{s}"))
        return ids.setdefault(k, len(ids))

    pairs = [(nid(r, 1), nid(r, 2)) for r in rows]
    deg = collections.Counter(x for p in pairs for x in p)
    return pairs, len(ids), deg


def main(path: str) -> None:
    rows = aligned_table(read_vsm(path))
    pairs, n, deg = build(rows)
    branches = []
    for (a, b), r in zip(pairs, rows):
        R, Q = fl(r["Resistance"]), fl(r["Quantity"])
        closed = R >= 1000 and Q == 0          # H2: bloqueada (observado: R>=1000 ⇒ Q=0 exacto)
        fixed_q = Q if (int(fl(r["Branch Flags"])) & 4) and not closed else None  # H3: bit 0x4 = caudal fijo
        branches.append(Branch(a, b, R, source=fl(r["Static Pressure"]), closed=closed, fixed_q=fixed_q))
    fixed = {k: 0.0 for k, d in deg.items() if d == 1}
    res = solve(n, branches, fixed)
    qf = np.array([fl(r["Quantity"]) for r in rows])
    err = res.Q - qf
    big = np.abs(qf) > 1.0
    rel = np.abs(err[big]) / np.abs(qf[big])
    print(f"{path.split(chr(92))[-1]}: nodos={n} ramas={len(rows)} fijos={len(fixed)} "
          f"convergió={res.converged} it={res.iterations} resid={res.residual:.2e}")
    print(f"  |Q|>1 m3/s: {big.sum()} ramas; error relativo mediano={np.median(rel):.4f} "
          f"p95={np.percentile(rel,95):.4f} max={rel.max():.4f}")
    worst = np.argsort(-np.abs(err))[:5]
    for i in worst:
        print(f"   #{rows[i]['Unique No']:>4} VentSim Q={qf[i]:9.3f}  nuestro Q={res.Q[i]:9.3f}  R={rows[i]['Resistance']}")


if __name__ == "__main__":
    main(sys.argv[1])
