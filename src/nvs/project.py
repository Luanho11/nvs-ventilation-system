"""Modelo de proyecto para la aplicación: carga .vsm (solo lectura), proyecto nativo (JSON) y cálculo.

Principio de procedencia: cada valor numérico lleva su origen.
  * `saved_*`  → leído del archivo (resultado que guardó VentSim). Nunca se presenta como cálculo del motor.
  * `calc_*`   → calculado por el motor propio en esta sesión (`solve_project`).
"""
from __future__ import annotations

import collections
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .escena import Escena, cargar_escena
from .fan import FanCurve, branch_source
from .network import Branch, solve
from .resistance import branch_resistance
from .vsmio import aligned_table, read_vsm
from .vsmnet import fl, model_density, network_predictive, node_ids

# Modelos con prueba diferencial D-NET-02 aprobada (tests/test_diff_network_predictive.py)
VALIDATED = {"tutorial1.vsm", "tutorial2.vsm", "demomine.vsm", "realmine.vsm"}


@dataclass
class Airway:
    uid: str
    name: str
    p1: tuple[float, float, float]
    p2: tuple[float, float, float]
    width: float = 0.0
    height: float = 0.0
    area: float = 0.0
    perimeter: float = 0.0
    length: float = 0.0
    k: float = 0.0
    le: float = 0.0
    # valores guardados en archivo (None si el proyecto es nativo)
    saved_R: float | None = None
    saved_Q: float | None = None
    saved_dp: float | None = None
    saved_p_from: float | None = None
    saved_p_to: float | None = None
    fan_type: str = ""
    fan_off: bool = False
    saved_fan_static: float | None = None
    raw_row: dict | None = None                           # fila completa del archivo (propiedades bajo demanda)
    etapas: int = -1                                      # máscara de bits de las etapas en que existe (-1 = todas)
    # proyecto nativo
    closed: bool = False
    fixed_q: float | None = None
    fan_curve: list[tuple[float, float]] | None = None   # puntos (Q por ventilador, P estática)
    fan_units: int = 1
    # resultados del motor (rellenados por solve_project)
    calc_Q: float | None = None
    calc_dp: float | None = None
    calc_R: float | None = None
    calc_p_from: float | None = None
    calc_p_to: float | None = None
    r_origin: str = ""
    fan_origin: str = ""

    @property
    def ficticia(self) -> bool:
        """Galería de enlace de 0,01 m × 0,01 m: Ventsim no la cuenta como «conducto de aire» (E-006)."""
        return 0 < self.area <= 0.0002

    @property
    def props(self) -> dict[str, str]:
        """Columnas del archivo con valor (se calculan al pedirlas; 279 columnas × miles de galerías pesan)."""
        if not self.raw_row:
            return {}
        return {k: v for k, v in self.raw_row.items() if v not in ("", "0", "False") and not k.startswith("_unnamed")}


@dataclass
class Project:
    name: str
    kind: str                       # "vsm" | "nativo"
    path: str = ""
    saved_version: str = ""
    descripcion: str = ""
    rho: float = 1.2
    airways: list[Airway] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    validated: bool = False
    _vsm: object = None
    _rows: list | None = None
    solved: bool = False
    solve_info: dict = field(default_factory=dict)
    escena: Escena = field(default_factory=Escena)


# --------------------------------------------------------------------- lectura de .vsm

def load_vsm(path: str | Path) -> Project:
    path = Path(path)
    v = read_vsm(path)
    rows = aligned_table(v)
    prj = Project(name=path.name, kind="vsm", path=str(path),
                  saved_version=v.header[11].strip() if len(v.header) > 11 else "?",
                  descripcion=v.header[1] if len(v.header) > 1 else "")
    prj._vsm, prj._rows = v, rows
    try:
        prj.rho = model_density(v)
    except Exception:  # noqa: BLE001
        prj.rho = 1.2
    for r in rows:
        a = Airway(
            uid=r["Unique No"],
            name=r.get("Branch Name", "") or r.get("Entry Node", ""),
            p1=(fl(r["X1"]), fl(r["Y1"]), fl(r["Z1"])),
            p2=(fl(r["X2"]), fl(r["Y2"]), fl(r["Z2"])),
            width=fl(r["Width"]), height=fl(r["Height"]), area=fl(r["Area"]), perimeter=fl(r["Perimeter"]),
            length=fl(r["Length"]), k=fl(r["kFactor"]), le=fl(r["shock factor"]),
            saved_R=fl(r["Resistance"]), saved_Q=fl(r["Quantity"]), saved_dp=abs(fl(r["Pressure Branch"])),
            saved_p_from=fl(r["Pressure From"]), saved_p_to=fl(r["Pressure To"]),
            fan_type=r["Fan Type"] if r["Fan Type"] not in ("", "0") else "",
            fan_off=r["Fan Off"] == "True",
            saved_fan_static=fl(r["Static Pressure"]) if r["Fan Type"] not in ("", "0") else None,
            raw_row=r,
            etapas=int(r["Stage"]) if r.get("Stage", "").lstrip("-").isdigit() else -1,
        )
        prj.airways.append(a)
    prj.validated = path.name.lower() in VALIDATED
    prj.warnings = _unsupported_features(v, rows)
    prj.escena = cargar_escena(v)
    return prj


def _unsupported_features(v, rows) -> list[str]:
    w = []
    n_rt = sum(1 for r in rows if r["Resistance Type"] not in ("0", "") and fl(r["Resistance"]) < 1000
               and r["Resistance Type"] not in {x[0] for x in v.sections["RESISTANCES"].rows if len(x) > 3})
    if n_rt:
        w.append(f"{n_rt} galerías con tipo de resistencia aún no descifrado: se usa la resistencia del archivo.")
    n_fc = sum(1 for r in rows if r["Fan Type"] not in ("", "0") and r["Fan Off"] != "True"
               and (r["Fan Config"] != "0" or fl(r["Fan Speed"]) != 100))
    if n_fc:
        w.append(f"{n_fc} ventiladores con configuración/velocidad no implementada: se usa su presión guardada.")
    try:
        d = [x for x in v.sections["AIRSIM"].rows if x != ["Description"]][0]
        if d[3] == "True":
            w.append("Simulación térmica / ventilación natural activa en el archivo: NO implementada "
                     "(densidad y presión natural por galería); los caudales pueden diferir.")
    except Exception:  # noqa: BLE001
        pass
    if any(r.get("DuctType", "") not in ("", "0") for r in rows):
        w.append("Contiene ductos: no implementados.")
    if any(len(v.sections[s].rows) > 1 for s in ("VENTFIREPRESETS",) if s in v.sections):
        w.append("Contiene presets de fuego: simulación de fuego no implementada.")
    return w


# --------------------------------------------------------------------- proyecto nativo

def new_native(name: str = "Proyecto nativo") -> Project:
    return Project(name=name, kind="nativo", rho=1.2, validated=False)


def demo_native() -> Project:
    """Red de demostración: pozo de entrada, galería, dos caminos en paralelo, chimenea de retorno con ventilador."""
    p = new_native("Red de demostración (nativa)")
    spec = [  # nombre, p1, p2, ancho, alto, forma, k, Le
        ("Pozo de entrada", (0, 0, 0), (0, 0, -200), 5, 5, "circle", 0.0417, 50),
        ("Galería principal", (0, 0, -200), (300, 0, -200), 4.5, 4, "rect", 0.012, 20),
        ("Ramal A-1", (300, 0, -200), (300, 200, -200), 4, 3.5, "rect", 0.015, 20),
        ("Ramal A-2", (300, 200, -200), (500, 200, -200), 4, 3.5, "rect", 0.015, 20),
        ("Ramal B-1", (300, 0, -200), (500, 0, -200), 4, 4, "rect", 0.01, 20),
        ("Ramal B-2", (500, 0, -200), (500, 200, -200), 4, 4, "rect", 0.01, 20),
        ("Chimenea de retorno (ventilador)", (500, 200, -200), (500, 200, 0), 4, 4, "circle", 0.005, 50),
    ]
    for i, (n, a, b, w, h, shp, k, le) in enumerate(spec, 1):
        p.airways.append(make_rect_airway(str(i), n, a, b, w, h, k, le, shp))
    p.airways[-1].fan_curve = [(40, 1800), (80, 1500), (120, 1000), (160, 450), (200, 0)]
    p.airways[-1].fan_units = 1
    return p


def native_to_dict(p: Project) -> dict:
    keys = ("uid", "name", "p1", "p2", "width", "height", "area", "perimeter", "length", "k", "le",
            "closed", "fixed_q", "fan_curve", "fan_units")
    return {"formato": "nvs-nativo", "version": 1, "name": p.name, "rho": p.rho,
            "airways": [{k: getattr(a, k) for k in keys} for a in p.airways]}


def save_native(p: Project, path: str | Path) -> None:
    Path(path).write_text(json.dumps(native_to_dict(p), indent=1, ensure_ascii=False), encoding="utf-8")
    p.path = str(path)


def load_native(path: str | Path) -> Project:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if d.get("formato") != "nvs-nativo":
        raise ValueError("No es un proyecto nativo de nvs")
    p = Project(name=d.get("name", Path(path).stem), kind="nativo", path=str(path), rho=float(d.get("rho", 1.2)))
    for x in d["airways"]:
        a = Airway(uid=str(x["uid"]), name=x.get("name", ""), p1=tuple(x["p1"]), p2=tuple(x["p2"]),
                   width=x["width"], height=x["height"], area=x["area"], perimeter=x["perimeter"],
                   length=x["length"], k=x["k"], le=x["le"], closed=x.get("closed", False),
                   fixed_q=x.get("fixed_q"), fan_curve=[tuple(t) for t in x["fan_curve"]] if x.get("fan_curve") else None,
                   fan_units=x.get("fan_units", 1))
        p.airways.append(a)
    return p


def make_rect_airway(uid: str, name: str, p1, p2, width: float, height: float, k: float, le: float = 0.0,
                     shape: str = "rect") -> Airway:
    """Crea una galería nativa; longitud = distancia geométrica; sección rectangular o circular (ancho = diámetro)."""
    length = math.dist(p1, p2)
    if shape == "circle":
        area, per, h = math.pi * width**2 / 4.0, math.pi * width, width
    else:
        area, per, h = width * height, 2.0 * (width + height), height
    return Airway(uid=uid, name=name, p1=tuple(p1), p2=tuple(p2), width=width, height=h, area=area,
                  perimeter=per, length=length, k=k, le=le)


# --------------------------------------------------------------------- cálculo

def _native_network(p: Project):
    rows_like = [{"X1": a.p1[0], "Y1": a.p1[1], "Z1": a.p1[2], "X2": a.p2[0], "Y2": a.p2[1], "Z2": a.p2[2]}
                 for a in p.airways]
    # node_ids usa fl(str); adaptamos con str()
    rows_like = [{k: str(v) for k, v in r.items()} for r in rows_like]
    pairs, n, deg = node_ids(rows_like)
    branches = []
    for (i, j), a in zip(pairs, p.airways):
        R = branch_resistance(a.k, a.length, a.le, a.perimeter, a.area, p.rho)
        br = Branch(i, j, R, closed=a.closed, fixed_q=a.fixed_q, r_origin="motor")
        if a.fan_curve:
            qs, ps = zip(*sorted(a.fan_curve))
            br.source_fn = branch_source(FanCurve(list(qs), list(ps)), a.fan_units)
            br.fan = (list(qs), list(ps), a.fan_units)
            br.fan_origin = "curva"
        branches.append(br)
    fixed = {k: 0.0 for k, d in deg.items() if d == 1}
    return branches, n, fixed, pairs, collections.Counter()


def solve_project(p: Project, tol: float = 5e-6, max_iter: int = 300) -> dict:   # residuo nodal [m³/s]; 1e-6 queda por debajo del ruido de redondeo en redes grandes
    """Ejecuta el solucionador propio. Rellena los campos `calc_*` y `r_origin`/`fan_origin`."""
    if not p.airways:
        raise ValueError("El proyecto no tiene galerías")
    if p.kind == "vsm":
        branches, n, fixed, info = network_predictive(p._vsm, p._rows)
        pairs, _n, _d = node_ids(p._rows)
    else:
        branches, n, fixed, pairs, info = _native_network(p)
    if not fixed:
        raise ValueError("La red no tiene bocas (nodos de grado 1) que fijen la presión de referencia")
    res = solve(n, branches, fixed, tol=tol, max_iter=max_iter)
    for a, b, (i, j), q in zip(p.airways, branches, pairs, res.Q):
        a.calc_Q = float(q)
        a.calc_R = float(b.R)
        a.calc_dp = float(b.R * q * abs(q))
        a.calc_p_from, a.calc_p_to = float(res.p[i]), float(res.p[j])
        a.r_origin, a.fan_origin = b.r_origin, b.fan_origin
    p.solved = True
    p.solve_info = {"converged": res.converged, "iterations": res.iterations, "residual": res.residual,
                    "n_nodes": n, "n_fixed_nodes": len(fixed), **dict(info)}
    return p.solve_info


def comparison_stats(p: Project, qmin: float = 1.0) -> dict | None:
    """Estadísticas calculado-vs-archivo (solo proyectos .vsm resueltos)."""
    if p.kind != "vsm" or not p.solved:
        return None
    sq = np.array([a.saved_Q for a in p.airways])
    cq = np.array([a.calc_Q for a in p.airways])
    big = np.abs(sq) > qmin
    if not big.any():
        return None
    rel = np.abs(cq[big] - sq[big]) / np.abs(sq[big])
    return {"n": int(big.sum()), "median": float(np.median(rel)), "p95": float(np.percentile(rel, 95)),
            "max": float(rel.max()), "within_1e-3": float((rel < 1e-3).mean())}
