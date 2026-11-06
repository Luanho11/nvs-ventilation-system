"""Elementos visuales de un .vsm que no son galerías: superficies de referencia, notas, etapas y vistas.

Evidencia (docs/evidence/E-004): REFERENCE guarda caras de 4 vértices (x, y, z, ..., capa, u, v); cuando el tercer y
el cuarto vértice coinciden es un triángulo. REFLAYERS guarda la textura JPEG de la capa en base64 (troceada en celdas).
MESSAGEBOX guarda las notas: posición en fracción de pantalla, color ARGB y texto con campos ``<código:modo:clave>``;
tras el GUID de la nota van el número de campos, sus pares (código, modo), el número de galerías y sus GUID.
Códigos (E-005): 101 caudal, 102 velocidad, 316 diámetro y 407 coste anual de la potencia del ventilador
= Fan Power [kW] × 8760 h × precio [$/kWh] ÷ eficiencia (AIRSIM columnas 8 y 12); coincide con las cifras de la referencia.
TRACKS guarda las pistas (rutas de galerías). SAVEVIEWS y STATE guardan la cámara: objetivo (3), distancia, giro y elevación.
"""
from __future__ import annotations

import base64
import io
import re
from dataclasses import dataclass, field

import numpy as np
from PySide6.QtGui import QImage

def colores_por_cota(z: np.ndarray, zmin: float, zmax: float) -> np.ndarray:
    """Arco iris por cota observado en CoalMine real (E-006): bajo = magenta/rojo, medio = amarillo/verde, alto = cian/azul."""
    t = np.clip((z - zmin) / max(zmax - zmin, 1e-9), 0.0, 1.0)
    h6 = ((300.0 + 300.0 * t) % 360.0) / 60.0
    rgb = np.stack([np.clip(np.abs(h6 - 3) - 1, 0, 1), np.clip(2 - np.abs(h6 - 2), 0, 1), np.clip(2 - np.abs(h6 - 4), 0, 1)], axis=1)
    return (rgb * 255).astype(np.uint8)
CODIGO_CAMPO = re.compile(r"<(\d+):(\w+)(?::(\d+))?>")


@dataclass
class Malla:
    nombre: str
    vertices: np.ndarray                       # (3T, 3) float32, triángulos consecutivos
    colores: np.ndarray                        # (3T, 3) uint8
    translucida: bool = False                  # capa sin textura: se colorea por cota y se dibuja translúcida (como en Ventsim)


@dataclass
class Nota:
    texto: str
    fx: float                                  # posición como fracción del visor (si no está anclada al modelo)
    fy: float
    color: tuple[int, int, int]
    posicion: tuple[float, float, float] | None    # punto del modelo al que está anclada, o None si es fija en pantalla
    etapas: int                                # máscara de las etapas en que se muestra
    guids: tuple[str, ...] = ()                # galerías sobre las que se agregan los campos sin clave (p. ej. «Maximum»)


@dataclass
class Pista:
    nombre: str
    color: tuple[int, int, int]
    guids: tuple[str, ...]                     # galerías de la pista


@dataclass
class Rejilla:
    """Rejilla de trabajo: rectángulo finito centrado en (cx, cy) a la cota z (COORDINATES; por defecto el de un proyecto vacío)."""
    espaciado: float = 50.0
    cx: float = 500.0
    cy: float = 500.0
    z: float = 0.0
    sx: float = 1000.0
    sy: float = 1000.0


@dataclass
class Vista:
    nombre: str
    objetivo: tuple[float, float, float]
    distancia: float
    giro: float
    elevacion: float


@dataclass
class Escena:
    mallas: list[Malla] = field(default_factory=list)
    notas: list[Nota] = field(default_factory=list)
    etapas: list[str] = field(default_factory=list)
    vistas: list[Vista] = field(default_factory=list)
    camara: Vista | None = None
    precio_kwh: float = 0.0                    # AIRSIM columna 8
    eficiencia: float = 1.0                    # AIRSIM columna 12 (95 → 0,95)
    moneda: str = "$"                          # OTHER columna 21
    pistas: list[Pista] = field(default_factory=list)
    rejilla: Rejilla = field(default_factory=Rejilla)
    etapa_activa: int = -1                     # STATE columna 79
    codigo_color: int = 101                    # STATE columna 7: tipo de dato con que se colorea (101 caudal, 613 tipo de aire)
    codigo_texto: int = 101                    # STATE columna 8: tipo de dato del texto
    tipos_aire: list[tuple[str, str]] = field(default_factory=list)    # AIRTYPES: (nombre, color #rrggbb) por índice
    capas_primarias: list[tuple[str, str]] = field(default_factory=list)   # PRIMARY: (nombre, color) por índice
    capas_referencia: list[str] = field(default_factory=list)              # REFLAYERS: nombre de cada capa del terreno
    cielo: str = "#6495ed"                     # GRAPHICS columna 2: color del fondo arriba (abajo, columna 1, es negro)
    color_rejilla: str = "#bcbcbc"             # GRAPHICS columna 3


def _entero_argb(texto: str) -> tuple[int, int, int]:
    n = int(texto) & 0xFFFFFFFF
    return (n >> 16) & 255, (n >> 8) & 255, n & 255


def _textura(celdas: list[str]) -> QImage | None:
    b64 = "".join(celdas)
    img = QImage()
    if not b64 or not img.loadFromData(base64.b64decode(b64 + "=" * (-len(b64) % 4))):
        return None
    return img.convertToFormat(QImage.Format_RGB888)


def _texturas_por_capa(filas: list[list[str]]) -> dict[str, QImage]:
    out, capa = {}, None
    for f in filas:
        if len(f) == 13 and f[0].isdigit():
            capa = f[0]
        elif capa is not None and (img := _textura(f)) is not None:
            out[capa] = img
    return out


def _colores_textura(img: QImage, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    w, h = img.width(), img.height()
    pix = np.frombuffer(img.constBits(), np.uint8).reshape(h, img.bytesPerLine())[:, : w * 3].reshape(h, w, 3)
    x = np.clip((u % 1.0) * (w - 1), 0, w - 1).astype(int)
    y = np.clip((1.0 - (v % 1.0)) * (h - 1), 0, h - 1).astype(int)
    return pix[y, x]


def _filas_referencia(sec) -> np.ndarray:
    """(N, 6) con x, y, z, capa, u, v de cada vértice. Las secciones llegan a más de un millón de filas: se lee en bloque."""
    try:
        return np.loadtxt(io.StringIO("\n".join(sec.lineas)), delimiter="\t", usecols=(0, 1, 2, 5, 6, 7), ndmin=2)
    except ValueError:                               # alguna fila corta o con texto en esas columnas
        filas = []
        for f in sec.rows:
            try:
                filas.append([float(f[0]), float(f[1]), float(f[2]), float(f[5]), float(f[6]), float(f[7])])
            except (ValueError, IndexError):
                continue
        return np.array(filas, float).reshape(-1, 6)


def _mallas(vsm) -> list[Malla]:
    sec = vsm.sections.get("REFERENCE")
    if sec is None or not len(sec):
        return []
    capas = vsm.sections["REFLAYERS"].rows if "REFLAYERS" in vsm.sections else []
    texturas = _texturas_por_capa(capas)
    nombres = {f[0]: f[1] for f in capas if len(f) == 13 and f[0].isdigit()}
    datos = _filas_referencia(sec)
    out = []
    for capa in np.unique(datos[:, 3]):
        d = datos[datos[:, 3] == capa]
        n = len(d) // 4 * 4
        xyz = d[:n, :3].astype(np.float32).reshape(-1, 4, 3)
        uv = d[:n, 4:6].astype(np.float32).reshape(-1, 4, 2)
        cuadrada = ~np.all(xyz[:, 3] == xyz[:, 2], axis=1)
        verts = np.concatenate([xyz[:, :3], xyz[cuadrada][:, [0, 2, 3]]]).reshape(-1, 3)
        coords = np.concatenate([uv[:, :3], uv[cuadrada][:, [0, 2, 3]]]).reshape(-1, 2)
        clave = str(int(capa))
        if clave in texturas:
            colores = _colores_textura(texturas[clave], coords[:, 0], coords[:, 1])
            sin_textura = False
        else:
            colores, sin_textura = None, True
        out.append(Malla(nombres.get(clave, clave), verts, colores, sin_textura))
    sin = [m for m in out if m.translucida]
    if sin:
        z = np.concatenate([m.vertices[:, 2] for m in sin])
        for m in sin:
            m.colores = colores_por_cota(m.vertices[:, 2], float(z.min()), float(z.max()))
    return out


def _notas(vsm) -> list[Nota]:
    sec = vsm.sections.get("MESSAGEBOX")
    if sec is None:
        return []
    out = []
    for f in sec.rows:
        if len(f) < 20:
            continue
        anclada = f[11] == "True"                    # columna 11: la nota sigue a un punto del modelo (columnas 1–3)
        posicion = (float(f[1]), float(f[2]), float(f[3])) if anclada else None
        out.append(Nota(f[13].replace("/c/n", "\n"), float(f[18]), float(f[19]), _entero_argb(f[6]), posicion, int(f[4]),
                        _guids_nota(f)))
    return out


def _guids_nota(f: list[str]) -> tuple[str, ...]:
    """Columna 26 = número de campos, luego 2 columnas por campo, el número de galerías y sus GUID."""
    try:
        i = 27 + 2 * int(f[26])
        return tuple(f[i + 1: i + 1 + int(f[i])])
    except (ValueError, IndexError):
        return ()


def _pistas(vsm) -> list[Pista]:
    """Una pista ocupa tres filas de TRACKS: cabecera (nombre, color ARGB en la columna 4), vehículo y GUID de galerías."""
    sec = vsm.sections.get("TRACKS")
    if sec is None:
        return []
    filas = sec.rows
    return [Pista(filas[i][0], _entero_argb(filas[i][4]), tuple(filas[i + 2]))
            for i in range(0, len(filas) - 2, 3) if len(filas[i]) > 4 and filas[i][4].lstrip("-").isdigit()]


def _costes(vsm) -> tuple[float, float, str]:
    """(precio por kWh, eficiencia, moneda) de AIRSIM y OTHER."""
    try:
        aire = vsm.sections["AIRSIM"].rows[-1]
        otros = vsm.sections["OTHER"].rows[-1]
        return float(aire[8]), float(aire[12]) / 100.0, otros[21].strip() or "$"
    except (KeyError, IndexError, ValueError):
        return 0.0, 1.0, "$"


def _rejilla(vsm) -> Rejilla:
    """COORDINATES: espaciado, centro X, cota, centro Y, tamaño X, tamaño de cota, tamaño Y (verificado con 14 ejemplos, E-006)."""
    try:
        f = [float(c) for c in vsm.sections["COORDINATES"].rows[-1][:7]]
        return Rejilla(f[0], f[1], f[3], f[2], f[4], f[6])
    except (KeyError, IndexError, ValueError):
        return Rejilla()


def _tipos_aire(vsm) -> list[tuple[str, str]]:
    """AIRTYPES: índice, nombre, color ARGB; solo los tipos con nombre (la tabla trae 250 filas casi vacías)."""
    sec = vsm.sections.get("AIRTYPES")
    if sec is None:
        return []
    out = []
    for f in sec.rows:
        if len(f) < 3 or not f[1]:
            break
        r, g, b = _entero_argb(f[2])
        out.append((f[1], f"#{r:02x}{g:02x}{b:02x}"))
    return out


def _capas_primarias(vsm) -> list[tuple[str, str]]:
    sec = vsm.sections.get("PRIMARY")
    out = []
    for f in (sec.rows if sec is not None else []):
        if len(f) < 4 or not f[1]:
            break
        r, g, b = _entero_argb(f[3])
        out.append((f[1], f"#{r:02x}{g:02x}{b:02x}"))
    return out


def _nombres_capas_referencia(vsm) -> list[str]:
    sec = vsm.sections.get("REFLAYERS")
    return [f[1] for f in (sec.rows if sec is not None else []) if len(f) == 13 and f[0].isdigit()]


def _colores_fondo(vsm) -> tuple[str, str]:
    """GRAPHICS: columna 2 = fondo arriba, columna 3 = rejilla (comprobado con los píxeles reales de Fire y CoalMine, E-006)."""
    try:
        f = vsm.sections["GRAPHICS"].rows[-1]
        return tuple("#%02x%02x%02x" % _entero_argb(f[i]) for i in (2, 3))
    except (KeyError, IndexError, ValueError):
        return "#6495ed", "#bcbcbc"


def _estado(vsm) -> tuple[int, int, int]:
    """(etapa activa, código de color, código de texto) de STATE; -1 y 101 si el archivo no los trae."""
    try:
        f = vsm.sections["STATE"].rows[0]
        return int(f[79]), int(f[7]), int(f[8])
    except (KeyError, IndexError, ValueError):
        return -1, 101, 101


def _vista(f: list[str]) -> Vista:
    return Vista(f[0], (float(f[1]), float(f[2]), float(f[3])), float(f[4]), float(f[5]), float(f[6]))


def cargar_escena(vsm) -> Escena:
    sec = lambda n: vsm.sections[n].rows if n in vsm.sections else []   # noqa: E731
    etapas = [f[1] for f in sec("STAGES") if len(f) > 1]
    vistas = [_vista(f) for f in sec("SAVEVIEWS") if len(f) > 6]
    estado = [_vista(f) for f in sec("STATE") if len(f) > 6]
    precio, eficiencia, moneda = _costes(vsm)
    etapa, color, texto = _estado(vsm)
    cielo, color_rejilla = _colores_fondo(vsm)
    return Escena(_mallas(vsm), _notas(vsm), etapas, vistas, estado[0] if estado else None, precio, eficiencia, moneda,
                  _pistas(vsm), _rejilla(vsm), etapa, color, texto, _tipos_aire(vsm),
                  _capas_primarias(vsm), _nombres_capas_referencia(vsm), cielo, color_rejilla)


HORAS_ANO = 8760


def resolver_campos(texto: str, airways, escena: Escena | None = None, guids: tuple[str, ...] = ()) -> str:
    """Sustituye los campos de una nota. Con clave («ShowAll:22») el valor es el de la galería con esa «Warning Key»;
    sin clave («Maximum») es el máximo sobre las galerías `guids` de la nota. Lo demás se muestra «—»."""
    por_clave = {a.raw_row.get("Warning Key"): a for a in airways if a.raw_row}
    por_guid = {a.raw_row.get("GUID"): a for a in airways if a.raw_row}

    def dato(codigo: str, a) -> float | None:
        if codigo == "101":
            return None if a.saved_Q is None else abs(a.saved_Q)
        if codigo == "102":
            return None if a.saved_Q is None or a.area <= 0 else abs(a.saved_Q) / a.area
        if codigo == "316":
            return a.width
        if codigo == "407" and escena is not None:
            return float(a.raw_row.get("Fan Power") or 0) * HORAS_ANO * escena.precio_kwh / escena.eficiencia
        return None

    def formato(codigo: str, v: float) -> str:
        if codigo == "407":
            return f"{escena.moneda}{v:,.0f} /yr"
        return f"{v:.1f} " + {"101": "m³/s", "102": "m/s", "316": "m"}[codigo]

    def valor(m: re.Match) -> str:
        codigo, modo, clave = m.groups()
        if clave:
            a = por_clave.get(clave)
            v = None if a is None else dato(codigo, a)
        elif modo == "Maximum":
            vs = [x for g in guids if (a := por_guid.get(g)) is not None and (x := dato(codigo, a)) is not None]
            v = max(vs) if vs else None
        else:
            v = None
        return "—" if v is None else formato(codigo, v)
    return CODIGO_CAMPO.sub(valor, texto)
