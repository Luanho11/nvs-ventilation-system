"""Construye docs/evidence/ui_spec.json a partir de los volcados MSAA de la aplicación real (observación, no código).

Entradas: docs/evidence/raw/msaa_main_menus_toolbar1_status.txt y msaa_toolbar2_rail_combos.txt
Salida: especificación de menús (árbol con orden y separadores), barras, raíl, combos y barra de estado.
"""
import json
import re
from pathlib import Path

RAW = Path("docs/evidence/raw")
LINE = re.compile(r"^(\s*)(.+?) \| '(.*?)' \| desc='(.*?)' \| kb='(.*?)' \| st=(\d+) \| (-?\d+),(-?\d+),(-?\d+),(-?\d+)$")


def parse(lines):
    out = []
    for ln in lines:
        m = LINE.match(ln.rstrip("\n"))
        if not m:
            continue
        ind, role, name, desc, kb, st, x, y, w, h = m.groups()
        out.append({"depth": len(ind) // 2, "role": role, "name": name, "kb": kb, "state": int(st),
                    "rect": [int(x), int(y), int(w), int(h)]})
    return out


def section(text, header):
    parts = re.split(r"^=== ", text, flags=re.M)
    for p in parts:
        if p.startswith(header):
            return p.splitlines()[1:]
    return []


def menu_tree(rows, base_depth):
    """Convierte filas (profundidad relativa) en árbol de menús: [{name, items:[...]}|'-']"""
    root = {"items": []}
    stack = [(base_depth - 1, root)]
    for r in rows:
        if r["role"] not in ("elemento de menú", "separador"):
            continue
        while stack and stack[-1][0] >= r["depth"]:
            stack.pop()
        parent = stack[-1][1]
        if r["role"] == "separador":
            parent["items"].append("-")
            continue
        node = {"name": r["name"], "items": [], "checkable": bool(r["state"] & 0x10)}
        parent["items"].append(node)
        stack.append((r["depth"], node))
    return root["items"]


main = (RAW / "msaa_main_menus_toolbar1_status.txt").read_text(encoding="utf-8-sig").splitlines()
bars = (RAW / "msaa_toolbar2_rail_combos.txt").read_text(encoding="utf-8-sig")
text_main = "\n".join(main)

menu_rows = parse(section(text_main, "HWND 462640"))
# los menús de nivel 1 están en profundidad 1 (la barra es profundidad 0); el resto de elementos sueltos van a la derecha
top = []
i = 0
while i < len(menu_rows):
    r = menu_rows[i]
    if r["depth"] == 1 and r["role"] == "elemento de menú":
        j = i + 1
        while j < len(menu_rows) and menu_rows[j]["depth"] > 1:
            j += 1
        top.append({"name": r["name"], "x": r["rect"][0], "items": menu_tree(menu_rows[i + 1:j], 2)})
        i = j
    else:
        i += 1
menus = [m for m in top if m["name"] not in ("Etapa", "Mensajes") and m["items"] or m["name"] in ("Ayuda",)]
stage_menu = next((m for m in top if m["name"] == "Etapa"), None)

tb1 = [r for r in parse(section(text_main, "HWND 528056")) if r["depth"] == 1 and r["role"] != "asidero"]
status = [r for r in parse(section(text_main, "HWND 8324978")) if r["depth"] == 1 and r["role"] != "asidero"]
tb2_rows = [r for r in parse(section(bars, "MSAA 1183684")) if r["depth"] == 1 and r["role"] != "asidero"]
rail = [r for r in parse(section(bars, "MSAA 5114010")) if r["depth"] == 1 and r["role"] != "asidero"]


def combos():
    out = {}
    for m in re.finditer(r"=== COMBO (\d+)\n(.*?)(?=\n===|\Z)", bars, flags=re.S):
        items = re.findall(r"^\s+\[\d+\] (.*)$", m.group(2), flags=re.M)
        out[m.group(1)] = items
    return out


spec = {
    "fuente": "Observación de la aplicación en ejecución (MSAA) + satélite de idioma es/VVentsim.resources.dll; ver docs/evidence/E-003",
    "ventana": {"titulo": "Ventsim DESIGN 6.0", "cliente_px": [1366, 720]},
    "menus": [{"name": m["name"], "items": m["items"]} for m in top if m["name"] not in ("Etapa", "Mensajes")],
    "menu_etapa": stage_menu["items"] if stage_menu else [],
    "barra1": [{"name": r["name"], "role": r["role"], "kb": r["kb"], "rect": r["rect"]} for r in tb1],
    "barra2": [{"name": r["name"], "role": r["role"], "rect": r["rect"]} for r in tb2_rows],
    "raiL_izquierdo": [{"name": r["name"], "role": r["role"], "rect": r["rect"]} for r in rail],
    "estado": [{"name": r["name"], "role": r["role"], "rect": r["rect"]} for r in status],
    "combos": combos(),
    "exponer": {"rect": [1143, 115, 222, 437], "slider_transparencia": [1172, 148, 181, 20], "tabs": [1151, 172, 206, 372],
                "campos_umbral": [[1161, 224 + 19 * k, 140, 19] for k in range(6)], "slider_vertical": [1312, 224, 20, 127],
                "opciones": [[1167 + 27 * k, 355, 28, 28] for k in range(4)],
                "muestras": [[1165, 389 + 16 * k, 26, 17] for k in range(8)],
                "colores": ["#ff96ff", "#e400e4", "#ff0000", "#ffff00", "#00ff00", "#00ffff", "#000080", "#000040"],
                "umbrales_por_defecto": [250, 100, 50, 25, 10, 0]},
    "visor": {"degradado_cielo": ["#6394e5", "#010203"], "color_rejilla": "#ffffff", "chrome": "#f0f0f0"},
}
_txt = json.dumps(spec, ensure_ascii=False, indent=1)
Path("docs/evidence/ui_spec.json").write_text(_txt, encoding="utf-8")
Path("src/nvs/data").mkdir(parents=True, exist_ok=True)       # copia empaquetada con la aplicación
Path("src/nvs/data/ui_spec.json").write_text(_txt, encoding="utf-8")
print("menús:", [(m["name"], len(m["items"])) for m in spec["menus"]])
print("barra1:", [b["name"] or b["role"] for b in spec["barra1"]])
print("raíl:", [b["name"] for b in spec["raiL_izquierdo"]])
print("barra2:", [b["name"] or b["role"] for b in spec["barra2"]])
print("estado:", [b["name"] or b["role"] for b in spec["estado"]])
print("combos:", {k: len(v) for k, v in spec["combos"].items()})
