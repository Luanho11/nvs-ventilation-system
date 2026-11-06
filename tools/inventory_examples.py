"""Inventario de los archivos de ejemplo de la instalación de referencia (solo lectura).

Uso: PYTHONPATH=src python tools/inventory_examples.py [carpeta_examples]
"""
from __future__ import annotations

import sys
from pathlib import Path

from nvs.vsmio import read_vsm

DEFAULT = Path(r"C:\Program Files\Ventsim DESIGN 6\examples")

# columnas de la tabla MAIN que parecen resultados calculados (a confirmar por experimento)
RESULT_COLS = ["Quantity", "Pressure From", "Pressure To", "Pressure Branch", "Resistance Total",
               "Calc Sensible", "Calc Latent", "wb air In", "db air In", "p air In",
               "Sim Concentration", "radonsim", "Dry Massflow"]


def num(x: str) -> float:
    try:
        return float(x)
    except ValueError:
        return 0.0


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    print("| archivo | versión | airways | ventiladores(tipo!=0) | columnas con valor distinto de 0 (resultados) |")
    print("|---|---|---|---|---|")
    for p in sorted(root.glob("*.vsm*")):
        if p.suffix not in (".vsm", ".vsmt"):
            continue
        try:
            v = read_vsm(p)
        except Exception as e:  # noqa: BLE001
            print(f"| {p.name} | ERROR {e} | | | |")
            continue
        rows = v.table("MAIN")
        ver = v.header[11].strip() if len(v.header) > 11 else "?"
        fans = sum(1 for r in rows if r.get("Fan Type", "0") not in ("", "0"))
        nz = [c for c in RESULT_COLS if any(num(r.get(c, "0")) != 0 for r in rows)]
        print(f"| {p.name} | {ver} | {len(rows)} | {fans} | {', '.join(nz) or '-'} |")


if __name__ == "__main__":
    main()
