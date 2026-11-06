"""Lector del contenedor de texto de los archivos .vsm / .vsmt.

Implementación propia, derivada únicamente de la observación de los archivos
de ejemplo distribuidos con la instalación de referencia (ver
docs/evidence/E-001-formato-vsm.md). No usa ni reproduce código del producto.

Estructura observada:
  * El archivo es un gzip estándar que contiene texto UTF-8 con líneas CRLF y
    campos separados por TAB.
  * La primera línea es una cabecera global de campos.
  * Después aparecen secciones: una línea con un único token (p. ej. ``KFACTORS``)
    abre la sección y ``END<TAB>KFACTORS`` la cierra. Algunas secciones usan
    marcadores de un solo token (``ENDHEAT``, ``ENDROCK``...) en lugar de ``END<TAB>X``.
  * Las tablas (``MAIN``, ``ROLLBACK``, ``EVENTDATA``) abren con una línea cuyo
    primer campo es el nombre y el resto son los nombres de columna.

Rendimiento: las filas de cada sección se guardan como texto y solo se trocean en campos al acceder a
``Section.rows`` (diamondmine.vsm tiene 1,1 M de líneas, casi todas en secciones que la aplicación no usa).
"""
from __future__ import annotations

import gzip
import re
from dataclasses import dataclass
from pathlib import Path

TAB = "\t"
CRLF = "\r\n"


class Section:
    """Sección del archivo con filas perezosas."""

    __slots__ = ("name", "columns", "_raw", "_rows", "closed")

    def __init__(self, name: str, columns: list[str] | None = None):
        self.name = name
        self.columns = columns
        self._raw: list[str] = []
        self._rows: list[list[str]] | None = None
        self.closed = False

    @property
    def rows(self) -> list[list[str]]:
        if self._rows is None:
            self._rows = [ln.split(TAB) for ln in self._raw]
        return self._rows

    @property
    def lineas(self) -> list[str]:
        """Filas sin trocear (para lectores masivos que no necesitan todos los campos)."""
        return self._raw

    def __len__(self) -> int:
        return len(self._raw)


@dataclass
class VsmFile:
    path: str
    header: list[str]
    sections: dict[str, Section]
    order: list[str]

    def table(self, name: str = "MAIN") -> list[dict[str, str]]:
        """Devuelve la tabla como lista de dicts (las columnas repetidas se sufijan)."""
        sec = self.sections.get(name)
        if sec is None or sec.columns is None:
            return []
        cols = _unique(sec.columns)
        out = []
        for r in sec.rows:
            r = r + [""] * (len(cols) - len(r))
            out.append(dict(zip(cols, r)))
        return out


_GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def aligned_table(vsm: "VsmFile", name: str = "MAIN") -> list[dict[str, str]]:
    """Tabla con los nombres de columna realineados con los datos.

    Observación (E-001): la cabecera nombra GUID en la posición g, pero en las filas
    el GUID aparece en g+d (d=1 en todos los ejemplos). Las columnas anteriores al
    GUID no se desplazan; las intermedias sin nombre se llaman ``_unnamed<i>``.
    El desplazamiento se detecta por la posición del primer valor con forma de GUID.
    """
    sec = vsm.sections.get(name)
    if sec is None or sec.columns is None or not len(sec):
        return []
    cols = sec.columns
    if "GUID" not in cols:
        return vsm.table(name)
    g = cols.index("GUID")
    rows = sec.rows
    first = rows[0]
    gi = next((i for i, v in enumerate(first) if _GUID.match(v)), None)
    d = (gi - g) if gi is not None else 0
    names = cols[:g] + [f"_unnamed{i}" for i in range(d)] + cols[g:] if d >= 0 else cols
    names = _unique(names)
    out = []
    for r in rows:
        r = r + [""] * (len(names) - len(r))
        out.append(dict(zip(names, r)))
    return out


def _unique(cols: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for c in cols:
        n = seen.get(c, 0)
        seen[c] = n + 1
        out.append(c if n == 0 else f"{c}#{n}")
    return out


def _is_opener(fields: list[str]) -> bool:
    f0 = fields[0]
    if not f0 or f0[0].isdigit() or f0 != f0.strip():
        return False
    if len(fields) == 1:
        return f0.replace("_", "").isalnum() and f0.upper() == f0 and not f0.startswith("<")
    return False


_TABLES = {"MAIN", "ROLLBACK", "EVENTDATA"}


def parse_text(text: str, path: str = "<memory>") -> VsmFile:
    lines = text.split(CRLF)
    if lines and lines[-1] == "":
        lines.pop()
    header = lines[0].split(TAB) if lines else []
    sections: dict[str, Section] = {}
    order: list[str] = []
    cur: Section | None = None
    for ln in lines[1:]:
        if TAB not in ln:                                # una sola celda: apertura de sección o dato
            if _is_opener([ln]):
                cur = Section(ln)
                sections[ln] = cur
                order.append(ln)
            elif cur is not None:
                cur._raw.append(ln)
            continue
        n_tabs = ln.count(TAB)
        if n_tabs == 1 and ln.startswith("END" + TAB):   # cierre «END<TAB>NOMBRE»
            if cur is not None and cur.name == ln[4:]:
                cur.closed = True
                cur = None
            continue
        head = ln[: ln.index(TAB)]
        if n_tabs >= 2 and head in _TABLES:              # cabecera de tabla
            cur = Section(head, columns=ln.split(TAB)[1:])
            sections[head] = cur
            order.append(head)
            continue
        if cur is not None:
            cur._raw.append(ln)
    return VsmFile(path, header, sections, order)


def read_vsm(path: str | Path) -> VsmFile:
    p = Path(path)
    raw = p.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return parse_text(raw.decode("utf-8", errors="replace"), str(p))
