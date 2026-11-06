"""Solucionador de redes de ventilación (implementación propia).

Formulación nodal: incógnitas = presiones en nodos libres. Para cada rama (i→j):

    Δ = p_i − p_j + S(Q)            (S = fuente de presión: ventilador, etc.)
    Δ = R · Q · |Q|                 (ley cuadrática de Atkinson)

Se resuelve Σ Q = 0 en cada nodo libre con Newton-Raphson amortiguado (búsqueda de línea).
Convención: Q > 0 circula de n1 a n2. Las ramas «simples» (sin fuente dependiente del caudal) se
evalúan vectorizadas; las ramas con curva de ventilador se resuelven una a una con raíz acotada.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.optimize import brentq


@dataclass
class Branch:
    n1: int
    n2: int
    R: float                                   # N·s²/m⁸
    source: float = 0.0                        # presión constante añadida a favor de n1→n2 [Pa]
    # fuente dependiente del caudal: devuelve (S, dS/dQ)
    source_fn: Callable[[float], tuple[float, float]] | None = None
    closed: bool = False                       # galería bloqueada: Q = 0 exacto
    fixed_q: float | None = None               # caudal impuesto [m³/s] (presión desconocida)
    r_origin: str = ""                         # procedencia de R: "motor" | "archivo"
    fan_origin: str = ""                       # "" sin ventilador | "curva" | "archivo" | "apagado"
    # curva lineal a tramos de ventilador (qs, ps, n_unidades): permite resolver todos los ventiladores vectorizados
    fan: tuple[list[float], list[float], int] | None = None


def _pack_fans(fans: list[tuple[list[float], list[float], int]]):
    """Curvas de ventilador a matrices (F,K): caudales (relleno +inf), presiones (relleno último valor), nº de unidades."""
    K = max(len(f[0]) for f in fans)
    QS = np.full((len(fans), K), np.inf)
    PS = np.zeros((len(fans), K))
    for i, (qs, ps, _n) in enumerate(fans):
        QS[i, :len(qs)] = qs
        PS[i, :] = ps[-1]
        PS[i, :len(ps)] = ps
    return QS, PS, np.array([max(1, f[2]) for f in fans], float)


def _fan_flow(d, R, QS, PS, N):
    """Resuelve d + S(q) − R·q|q| = 0 para todos los ventiladores a la vez, SIN iterar. Devuelve (q, G=dq/dΔp).

    La curva S es lineal a tramos, así que en cada tramo la ecuación es una cuadrática con raíz exacta.
    Para q ≤ 0 la presión es la de cierre (constante). Para q > 0 se toma el primer cambio de signo de
    h(q) = d + S(q) − R·q² recorriendo los puntos de la curva desde q = 0 (raíz más baja, como el acotado original).
    """
    n = len(d)
    top = d + PS[:, 0]                                   # h(0)
    q = np.zeros(n)
    slope = np.zeros(n)
    neg = top <= 0
    q[neg] = -np.sqrt(-top[neg] / R[neg])
    pos = ~neg
    if pos.any():
        dp, Rp, QSp, PSp, Np = d[pos], R[pos], QS[pos], PS[pos], N[pos]
        K = QSp.shape[1]
        qb = Np[:, None] * QSp                            # caudales totales de los puntos (relleno = +inf)
        with np.errstate(invalid="ignore", over="ignore"):
            hb = dp[:, None] + PSp - Rp[:, None] * qb * qb
        hb = np.where(np.isfinite(qb), hb, -np.inf)
        nonpos = hb <= 0
        k0 = np.where(nonpos.any(axis=1), np.argmax(nonpos, axis=1), K)
        kreal = np.isfinite(qb).sum(axis=1)
        rows = np.arange(len(dp))
        qpos = np.empty(len(dp))
        mpos = np.zeros(len(dp))
        flat_lo = k0 == 0                                  # por debajo del primer punto: presión constante P0
        flat_hi = (k0 >= kreal) & ~flat_lo                 # por encima del último punto: presión constante P_last
        seg = ~(flat_lo | flat_hi)
        qpos[flat_lo] = np.sqrt(np.maximum(dp[flat_lo] + PSp[flat_lo, 0], 0.0) / Rp[flat_lo])
        last = np.maximum(kreal - 1, 0)
        qpos[flat_hi] = np.sqrt(np.maximum(dp[flat_hi] + PSp[rows[flat_hi], last[flat_hi]], 0.0) / Rp[flat_hi])
        if seg.any():
            r = rows[seg]
            k = k0[seg]
            q0, q1 = qb[r, k - 1], qb[r, k]
            p0, p1 = PSp[r, k - 1], PSp[r, k]
            m = (p1 - p0) / (q1 - q0)
            c = dp[seg] + p0 - m * q0
            s_ = np.sqrt(np.maximum(m * m + 4.0 * Rp[seg] * c, 0.0))
            # raíz mayor de R q² − m q − c = 0 en forma numéricamente estable (sin cancelación cuando m < 0)
            qpos[seg] = np.where(m >= 0, (m + s_) / (2.0 * Rp[seg]), 2.0 * c / np.maximum(s_ - m, 1e-300))
            mpos[seg] = m
        q[pos] = qpos
        slope[pos] = mpos
    G = 1.0 / np.maximum(2.0 * R * np.abs(q) - slope, 1e-9)
    return q, G


@dataclass
class NetworkResult:
    Q: np.ndarray
    p: np.ndarray
    iterations: int
    converged: bool
    residual: float


def solve(n_nodes: int, branches: list[Branch], fixed: dict[int, float],
          tol: float = 1e-8, max_iter: int = 200) -> NetworkResult:
    nb = len(branches)
    n1 = np.array([b.n1 for b in branches], dtype=int)
    n2 = np.array([b.n2 for b in branches], dtype=int)
    R = np.array([max(b.R, 1e-12) for b in branches])
    src = np.array([b.source for b in branches])
    closed = np.array([b.closed for b in branches], dtype=bool)
    fixq = np.array([b.fixed_q is not None and not b.closed for b in branches], dtype=bool)
    fixq_val = np.array([b.fixed_q if b.fixed_q is not None else 0.0 for b in branches])
    active = [i for i, b in enumerate(branches) if not b.closed and b.fixed_q is None]
    vec_idx = np.array([i for i in active if branches[i].fan is not None], dtype=int)      # curvas lineales: vectorizado
    fan_idx = np.array([i for i in active if branches[i].fan is None and branches[i].source_fn is not None], dtype=int)
    if len(vec_idx):
        QS, PS, NU = _pack_fans([branches[i].fan for i in vec_idx])
    plain = ~closed & ~fixq
    plain[fan_idx] = False
    plain[vec_idx] = False

    free = np.array([i for i in range(n_nodes) if i not in fixed], dtype=int)
    idx = -np.ones(n_nodes, dtype=int)
    idx[free] = np.arange(len(free))
    p = np.zeros(n_nodes)
    for k, v in fixed.items():
        p[k] = v

    def branch_flow(p):
        d = p[n1] - p[n2]
        Q = np.zeros(nb)
        G = np.zeros(nb)
        dd = d[plain] + src[plain]
        qp = np.sign(dd) * np.sqrt(np.abs(dd) / R[plain])
        Q[plain] = qp
        G[plain] = 1.0 / (2.0 * R[plain] * np.maximum(np.abs(qp), 1e-3))
        Q[fixq] = fixq_val[fixq]
        if len(vec_idx):
            qv, gv = _fan_flow(d[vec_idx], R[vec_idx], QS, PS, NU)
            Q[vec_idx], G[vec_idx] = qv, gv
        for b in fan_idx:
            br = branches[b]

            def h(q, d0=d[b], fn=br.source_fn, Rb=R[b]):
                return d0 + fn(q)[0] - Rb * q * abs(q)

            # h es monótona decreciente si S no crece con q → raíz única acotada
            if h(0.0) > 0:
                hi = 1.0
                while h(hi) > 0:
                    hi *= 2.0
                q = brentq(h, 0.0, hi, xtol=1e-13, rtol=1e-13)
            else:
                lo = -1.0
                while h(lo) < 0:
                    lo *= 2.0
                q = brentq(h, lo, 0.0, xtol=1e-13, rtol=1e-13)
            _s, ds = br.source_fn(q)
            Q[b] = q
            G[b] = 1.0 / max(2.0 * R[b] * abs(q) - ds, 1e-9)
        return Q, G

    def residual(Q):
        res = np.zeros(n_nodes)
        np.add.at(res, n2, Q)
        np.add.at(res, n1, -Q)
        return res[free]

    hist: list[float] = []
    for it in range(1, max_iter + 1):
        Q, G = branch_flow(p)
        r = residual(Q)
        nrm = float(np.max(np.abs(r))) if len(r) else 0.0
        hist.append(nrm)
        if nrm < tol:
            return NetworkResult(Q, p, it, True, nrm)
        # Jacobiano (COO vectorizado): res_c = +Q → d/dp_c = −g, d/dp_a = +g ; res_a = −Q → d/dp_a = −g, d/dp_c = +g
        ia, ic = idx[n1], idx[n2]
        rows = np.concatenate([ic[ic >= 0], ia[ia >= 0], ic[(ic >= 0) & (ia >= 0)], ia[(ia >= 0) & (ic >= 0)]])
        cols = np.concatenate([ic[ic >= 0], ia[ia >= 0], ia[(ic >= 0) & (ia >= 0)], ic[(ia >= 0) & (ic >= 0)]])
        vals = np.concatenate([-G[ic >= 0], -G[ia >= 0], G[(ic >= 0) & (ia >= 0)], G[(ia >= 0) & (ic >= 0)]])
        J = sp.csc_matrix((vals, (rows, cols)), shape=(len(free), len(free)))
        J = J + sp.identity(len(free), format="csc") * 1e-12
        dp = spla.spsolve(J, -r)
        lam = 1.0
        for _ in range(12):  # búsqueda de línea
            p_try = p.copy()
            p_try[free] += lam * dp
            Qt, _g = branch_flow(p_try)
            if np.max(np.abs(residual(Qt))) < nrm or lam < 1e-3:
                break
            lam *= 0.5
        p = p_try
    Q, _ = branch_flow(p)
    return NetworkResult(Q, p, max_iter, False, hist[-1])
