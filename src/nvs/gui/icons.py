"""Iconos vectoriales propios con el estilo de la interfaz de referencia (docs/evidence/E-004): planos, con degradado,
contorno fino y colores por función (documentos azul claro, carpeta ocre, cubo dorado, globo azul y verde...).

Cada icono es un SVG de 32×32 dibujado en este proyecto (no se copia ningún recurso de la aplicación de referencia).
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


def _grad(id_: str, a: str, b: str, vertical: bool = True) -> str:
    x2, y2 = ("0", "1") if vertical else ("1", "0")
    return (f'<linearGradient id="{id_}" x1="0" y1="0" x2="{x2}" y2="{y2}">'
            f'<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>')


_HOJA = _grad("h", "#ffffff", "#d4e3f5")
_AZUL = _grad("b", "#7fc0f7", "#1d62b8")
_ORO = _grad("o", "#ffe08a", "#d99a1e")
_GRIS = _grad("g", "#b4b4b4", "#4f4f4f")

CUBO = ('<path d="M16 3l12 6.5v13L16 29 4 22.5v-13z" fill="{c1}" stroke="{c4}" stroke-width="1.2" stroke-linejoin="round"/>'
        '<path d="M16 16L4 9.5M16 16l12-6.5M16 16v13" stroke="{c4}" stroke-width="1.1" fill="none"/>'
        '<path d="M16 16L4 9.5 16 3l12 6.5z" fill="{c2}"/><path d="M16 16v13L4 22.5v-13z" fill="{c3}"/>')

SVG: dict[str, str] = {
    "nuevo": f'<defs>{_HOJA}</defs><path d="M7 3h13l6 6v20H7z" fill="url(#h)" stroke="#8aa0bb"/>'
             '<path d="M20 3v6h6" fill="#e6eef9" stroke="#8aa0bb"/>',
    "abrir": '<path d="M3 8h9l2 3h14v16H3z" fill="#e9bd80" stroke="#c4893f"/>'
             '<path d="M3 27l4-12h22l-3 12z" fill="#f4d3a1" stroke="#c4893f"/>',
    "copiar": f'<defs>{_HOJA}</defs><path d="M5 3h9l4 4v13H5z" fill="url(#h)" stroke="#6f86a3"/>'
              '<path d="M8 9h7M8 12h7M8 15h7" stroke="#6f86a3"/>'
              '<path d="M13 11h9l4 4v14H13z" fill="url(#h)" stroke="#6f86a3"/>'
              '<path d="M16 18h7M16 21h7M16 24h7" stroke="#6f86a3"/>',
    "pegar": f'<defs>{_ORO}{_HOJA}</defs><rect x="4" y="5" width="19" height="24" rx="2" fill="url(#o)" stroke="#8a5a14"/>'
             '<rect x="9" y="3" width="9" height="5" rx="1.5" fill="#6b4a1e"/>'
             '<path d="M14 13h9l5 5v11H14z" fill="url(#h)" stroke="#6f86a3"/>'
             '<path d="M17 20h8M17 23h8M17 26h8" stroke="#6f86a3"/>',
    "ventanas": f'<defs>{_AZUL}{_HOJA}</defs><rect x="3" y="3" width="19" height="15" fill="url(#h)" stroke="#4a78b5"/>'
                '<rect x="3" y="3" width="19" height="4" fill="url(#b)"/>'
                '<rect x="9" y="14" width="19" height="15" fill="url(#h)" stroke="#4a78b5"/>'
                '<rect x="9" y="14" width="19" height="4" fill="url(#b)"/>'
                '<path d="M18.5 20v8M14.5 24h8" stroke="#2f7ed8" stroke-width="2.4"/>',
    "prismaticos": f'<defs>{_GRIS}</defs><rect x="4" y="12" width="9" height="16" rx="3" fill="url(#g)"/>'
                   '<rect x="19" y="12" width="9" height="16" rx="3" fill="url(#g)"/>'
                   '<rect x="11" y="9" width="10" height="7" rx="1.5" fill="#7a7a7a"/>'
                   '<rect x="5" y="6" width="7" height="8" rx="1.5" fill="#8c8c8c"/>'
                   '<rect x="20" y="6" width="7" height="8" rx="1.5" fill="#8c8c8c"/>',
    "pelicula": '<rect x="6" y="3" width="20" height="26" rx="1.5" fill="#173f6b"/>'
                '<rect x="10.5" y="5" width="11" height="22" fill="#79c4ee"/>'
                '<path d="M6 8h4M6 13h4M6 18h4M6 23h4M22 8h4M22 13h4M22 18h4M22 23h4" stroke="#dfe9f4" stroke-width="2.4"/>'
                '<path d="M10.5 11h11M10.5 17h11M10.5 22h11" stroke="#173f6b" stroke-width="1.2"/>',
    "ejecutar": '<defs><radialGradient id="r" cx=".38" cy=".3" r=".8"><stop offset="0" stop-color="#8fd0ff"/>'
                '<stop offset=".55" stop-color="#2a79d6"/><stop offset="1" stop-color="#0b3f94"/></radialGradient></defs>'
                '<circle cx="16" cy="16" r="13" fill="url(#r)" stroke="#0b3f94"/>'
                '<path d="M12 8.5v15l12-7.5z" fill="#ffffff"/>',
    "lupa": '<circle cx="13" cy="13" r="9" fill="#d8ecfb" stroke="#667a92" stroke-width="2.4"/>'
            '<path d="M9 9a6 6 0 0 1 7-1.5" stroke="#ffffff" stroke-width="2" fill="none"/>'
            '<path d="M20 20l9 9" stroke="#59687a" stroke-width="4" stroke-linecap="round"/>',
    "mover": '<path d="M16 3l5 6h-3.5v5.5H23V11l6 5-6 5v-3.5h-5.5V23H21l-5 6-5-6h3.5v-5.5H9V21l-6-5 6-5v3.5h5.5V9H11z" '
             'fill="#4d6c99" stroke="#34507a" stroke-linejoin="round"/>',
    "desplegable": '<path d="M9 13h14l-7 8z" fill="#202020"/>',
    "exponer": f'<defs>{_AZUL}</defs><rect x="3" y="12" width="14" height="16" fill="#c6d8ee" stroke="#6f90bd"/>'
               '<rect x="9" y="5" width="20" height="16" fill="url(#b)" stroke="#2f6bb5"/>'
               '<path d="M14 18l10-9M16 9h8v8" stroke="#ffffff" stroke-width="2" fill="none"/>',
    "paleta": '<rect x="4" y="4" width="7.5" height="7.5" fill="#2f4fd6"/><rect x="12.3" y="4" width="7.5" height="7.5" fill="#2f4fd6"/>'
              '<rect x="20.5" y="4" width="7.5" height="7.5" fill="#5c2fb8"/><rect x="4" y="12.3" width="7.5" height="7.5" fill="#8a4a1e"/>'
              '<rect x="12.3" y="12.3" width="7.5" height="7.5" fill="#e0231c"/><rect x="20.5" y="12.3" width="7.5" height="7.5" fill="#e0231c"/>'
              '<rect x="4" y="20.5" width="7.5" height="7.5" fill="#f5d015"/><rect x="12.3" y="20.5" width="7.5" height="7.5" fill="#9a9a9a"/>'
              '<rect x="20.5" y="20.5" width="7.5" height="7.5" fill="#555555"/>',
    "enlace": '<rect x="3" y="11" width="14" height="10" rx="5" fill="none" stroke="#8c8c8c" stroke-width="3"/>'
              '<rect x="15" y="11" width="14" height="10" rx="5" fill="none" stroke="#8c8c8c" stroke-width="3"/>',
    "texto": '<path d="M6 6h20v6h-2.5l-.8-3H18v15l3 1.5V27H11v-2.5l3-1.5V9H9.3l-.8 3H6z" fill="#111111"/>',
    "texto_relativo": '<path d="M4 28L14 4h5l9 24h-5l-1.8-5.5h-8L11 28z" fill="#bfe0fa" stroke="#2a7fd0" stroke-width="2" '
                      'stroke-linejoin="round"/><path d="M13 19h6l-3-9z" fill="#ffffff" stroke="#2a7fd0"/>',
    "estrella": '<path d="M16 4l3.6 7.6 8.2 1-6 5.7 1.6 8.2L16 22.4 8.6 26.5l1.6-8.2-6-5.7 8.2-1z" fill="none" '
                'stroke="#555555" stroke-width="2" stroke-linejoin="round"/>',
    "cubo_solido": CUBO.format(c1="#e9a825", c2="#ffd86e", c3="#d88a14", c4="#a9680f"),
    "cubo_malla": CUBO.format(c1="#d8d8d8", c2="#e9e9e9", c3="#c4c4c4", c4="#6a6a6a")
                  + '<path d="M10 6.2l12 6.6M22 6.2L10 12.8M4 16l12 6.5L28 16M10 19.5v5M22 19.5v5" stroke="#6a6a6a" fill="none"/>',
    "ajustar": '<path d="M4 4h9l-3.3 3.3 4 4-3 3-4-4L4 13zM28 4v9l-3.3-3.3-4 4-3-3 4-4L19 4zM4 28v-9l3.3 3.3 4-4 3 3-4 4L13 28zM28 28h-9l3.3-3.3-4-4 3-3 4 4L28 19z" '
               'fill="#2b8ee0" stroke="#1d63a8" stroke-linejoin="round"/>',
    "tabla": f'<defs>{_AZUL}</defs><rect x="3" y="4" width="26" height="24" fill="#e8f2fc" stroke="#1d4f9c" stroke-width="1.5"/>'
             '<rect x="3" y="4" width="26" height="6" fill="#1d4f9c"/>'
             '<path d="M3 16h26M3 22h26M12 10v18M21 10v18" stroke="#2f7fd8" stroke-width="1.8"/>',
    "nodo": '<defs><radialGradient id="n" cx=".4" cy=".3" r=".8"><stop offset="0" stop-color="#bfe3ff"/>'
            '<stop offset="1" stop-color="#4b9ae6"/></radialGradient></defs>'
            '<circle cx="16" cy="16" r="12" fill="url(#n)" stroke="#16264a" stroke-width="3"/>',
    "flechas": '<path d="M6 5l20 11L6 27z" fill="#8fc6ef" stroke="#111111" stroke-width="2.6" stroke-linejoin="round"/>',
    "referencias": '<defs><radialGradient id="e" cx=".4" cy=".3" r=".8"><stop offset="0" stop-color="#7fc4f5"/>'
                   '<stop offset="1" stop-color="#1b6cc4"/></radialGradient></defs>'
                   '<circle cx="16" cy="16" r="13" fill="url(#e)" stroke="#144f95"/>'
                   '<path d="M8 8c4-3 8 0 7 4s-5 2-4 7-3 4-5 1c-3-3-2-9 2-12zM19 20c3-3 6-1 7 2-2 4-6 6-9 5 1-3 0-5 2-7z" fill="#35a851"/>',
    "pistas": '<path d="M7 27V14c0-6 12-6 12 0v13" fill="none" stroke="#7b7b7b" stroke-width="4" stroke-linecap="round"/>'
              '<path d="M19 6v10M15 10l4-4 4 4" stroke="#7b7b7b" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
    "visibilidad": f'<defs>{_AZUL}</defs><path d="M14 3h4l1 4 3 1.3 3.4-2.2 2.8 2.8-2.2 3.4L27 15l4 1v4l-4 1-1.3 3 2.2 3.4-2.8 2.8-3.4-2.2L19 29l-1 4h-4l-1-4-3-1.3-3.4 2.2-2.8-2.8L6 24l-1.3-3L1 20v-4l3.7-1L6 12 3.8 8.6l2.8-2.8L10 8l3-1.3z" '
                   'transform="translate(1 -2) scale(.93)" fill="url(#b)" stroke="#144f95"/><circle cx="16" cy="16" r="4.5" fill="#e8f2fc" stroke="#144f95"/>',
    "pestana_lista": '<path d="M3 10l5 4-5 4z" fill="#8c8c8c"/><rect x="11" y="6" width="9" height="5" fill="#2f7fd8"/>'
                     '<rect x="11" y="13" width="16" height="5" fill="#e9962a"/><rect x="11" y="20" width="12" height="5" fill="#d83a2a"/>',
    "pestana_cubo": CUBO.format(c1="#3a8fe0", c2="#f2c53a", c3="#d83a2a", c4="#3a3a3a"),
    "capa_1": '<path d="M3 21l13-6 13 6-13 6z" fill="#d83a2a" stroke="#7a1f16"/><path d="M3 16l13-6 13 6-13 6z" fill="#3a8fe0" stroke="#1d4f9c"/>'
              '<ellipse cx="16" cy="10" rx="9" ry="4.5" fill="#f2c53a" stroke="#8a6a10"/><text x="16" y="13" font-size="9" font-weight="bold" '
              'text-anchor="middle" fill="#111">1</text>',
    "capa_2": '<path d="M3 21l13-6 13 6-13 6z" fill="#d83a2a" stroke="#7a1f16"/><path d="M3 16l13-6 13 6-13 6z" fill="#3a8fe0" stroke="#1d4f9c"/>'
              '<ellipse cx="16" cy="10" rx="9" ry="4.5" fill="#f2c53a" stroke="#8a6a10"/><text x="16" y="13" font-size="9" font-weight="bold" '
              'text-anchor="middle" fill="#111">2</text>',
    "pestana_ventana": f'<defs>{_AZUL}</defs><rect x="3" y="12" width="16" height="16" fill="#cfe0f4" stroke="#6f90bd"/>'
                       '<rect x="10" y="4" width="19" height="17" fill="url(#b)" stroke="#2f6bb5"/><path d="M15 17l9-9M17 8h7v7" stroke="#fff" stroke-width="2" fill="none"/>',
    "orden_asc": '<path d="M9 4v16M4 15l5 6 5-6" stroke="#2f8fe0" stroke-width="3" fill="none" stroke-linejoin="round"/>'
                 '<rect x="16" y="5" width="12" height="4" fill="#8a4ac8"/><rect x="16" y="11" width="9" height="4" fill="#e9962a"/>'
                 '<rect x="16" y="17" width="6" height="4" fill="#d83a2a"/>',
    "orden_desc": '<path d="M9 4v16M4 15l5 6 5-6" stroke="#2f8fe0" stroke-width="3" fill="none" stroke-linejoin="round"/>'
                  '<rect x="16" y="5" width="12" height="4" fill="#d83a2a"/><rect x="16" y="11" width="9" height="4" fill="#e9962a"/>'
                  '<rect x="16" y="17" width="6" height="4" fill="#8a4ac8"/>',
    "rueda_color": '<circle cx="16" cy="16" r="12" fill="#ffffff" stroke="#7a7a7a"/>'
                   '<path d="M16 16L16 4A12 12 0 0 1 26.4 10z" fill="#f2c53a"/><path d="M16 16L26.4 10A12 12 0 0 1 26.4 22z" fill="#e0231c"/>'
                   '<path d="M16 16L26.4 22A12 12 0 0 1 16 28z" fill="#c43ac8"/><path d="M16 16L16 28A12 12 0 0 1 5.6 22z" fill="#2f4fd6"/>'
                   '<path d="M16 16L5.6 22A12 12 0 0 1 5.6 10z" fill="#2fc8e0"/><path d="M16 16L5.6 10A12 12 0 0 1 16 4z" fill="#3ac84a"/>'
                   '<circle cx="16" cy="16" r="3" fill="#ffffff"/>',
    "mosaico": '<rect x="4" y="4" width="8" height="8" fill="#2f4fd6"/><rect x="12" y="4" width="8" height="8" fill="#c43ac8"/>'
               '<rect x="20" y="4" width="8" height="8" fill="#f2a0d8"/><rect x="4" y="12" width="8" height="8" fill="#f2c53a"/>'
               '<rect x="12" y="12" width="8" height="8" fill="#2f4fd6"/><rect x="20" y="12" width="8" height="8" fill="#3ac84a"/>'
               '<rect x="4" y="20" width="8" height="8" fill="#f2c53a"/><rect x="12" y="20" width="8" height="8" fill="#e0231c"/>'
               '<rect x="20" y="20" width="8" height="8" fill="#e0231c"/>',
    "transparencia": '<circle cx="12" cy="16" r="8" fill="#7fd0e8" fill-opacity=".85" stroke="#3a9ab8"/>'
                     '<circle cx="20" cy="16" r="8" fill="#f2e05a" fill-opacity=".85" stroke="#b8a53a"/>',
    "candado": '<path d="M10 14v-4a6 6 0 0 1 12 0" fill="none" stroke="#2a6fc0" stroke-width="3"/>'
               '<rect x="6" y="14" width="20" height="14" rx="2" fill="#3a8fe0" stroke="#1d4f9c"/><circle cx="16" cy="21" r="2.2" fill="#1d4f9c"/>',
    "flecha_izq": '<path d="M22 5v22L8 16z" fill="#2f8fe0" stroke="#1d63a8"/>',
    "flecha_der": '<path d="M10 5v22l14-11z" fill="#9db4cc" stroke="#7a90a8"/>',
    "mensajes": '<rect x="3" y="7" width="26" height="18" fill="#e8f2fc" stroke="#2f7fd8" stroke-width="1.6"/>'
                '<path d="M3 8l13 10L29 8" stroke="#2f7fd8" stroke-width="2" fill="none"/>',
    "camara": '<rect x="3" y="9" width="26" height="18" rx="3" fill="#b9bfc7" stroke="#8a929c"/><rect x="10" y="5" width="12" height="6" rx="1.5" fill="#b9bfc7" stroke="#8a929c"/>'
              '<circle cx="16" cy="18" r="6" fill="#e9eef4" stroke="#8a929c" stroke-width="2"/>',
    "tarjeta": '<rect x="3" y="6" width="26" height="20" rx="3" fill="#f2c53a" stroke="#b88a14"/><path d="M8 12h16M8 17h16M8 22h10" stroke="#8a6a10" stroke-width="2"/>',
    "ayuda": '<circle cx="16" cy="16" r="13" fill="#3a8fe0" stroke="#1d63a8"/>'
             '<path d="M11.5 12.5a4.5 4.5 0 1 1 6.5 4c-1.5.9-2 1.6-2 3" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/>'
             '<circle cx="16" cy="25" r="1.8" fill="#fff"/>',
    "cerrar": '<rect x="2" y="2" width="28" height="28" rx="3" fill="#a9a9a9"/><path d="M10 10l12 12M22 10L10 22" stroke="#fff" stroke-width="3.4"/>',
    "pb_play": '<defs><radialGradient id="r" cx=".4" cy=".3" r=".8"><stop offset="0" stop-color="#bfe0ff"/><stop offset="1" stop-color="#3a86d8"/></radialGradient></defs>'
               '<circle cx="16" cy="16" r="13" fill="url(#r)" stroke="#1d5fb0" stroke-width="2"/><path d="M12 9v14l11-7z" fill="#fff"/>',
    "pb_rapido": '<defs><radialGradient id="r" cx=".4" cy=".3" r=".8"><stop offset="0" stop-color="#bfe0ff"/><stop offset="1" stop-color="#3a86d8"/></radialGradient></defs>'
                 '<circle cx="16" cy="16" r="13" fill="url(#r)" stroke="#1d5fb0" stroke-width="2"/><path d="M7 10v12l8-6zM15 10v12l8-6z" fill="#fff"/>',
    "pb_pausa": '<defs><radialGradient id="r" cx=".4" cy=".3" r=".8"><stop offset="0" stop-color="#bfe0ff"/><stop offset="1" stop-color="#3a86d8"/></radialGradient></defs>'
                '<circle cx="16" cy="16" r="13" fill="url(#r)" stroke="#1d5fb0" stroke-width="2"/><path d="M10 9h4v14h-4zM18 9h4v14h-4z" fill="#fff"/>',
    "vista_malla": '<path d="M16 4l11 6v12l-11 6-11-6V10z" fill="#fff" stroke="#222" stroke-width="1.6" stroke-linejoin="round"/>'
                   '<path d="M5 10l11 6 11-6M16 16v12" stroke="#222" fill="none" stroke-width="1.4"/>',
    "vista_solida": '<path d="M16 4l11 6v12l-11 6-11-6V10z" fill="#fff" stroke="#222" stroke-width="1.6" stroke-linejoin="round"/>'
                    '<path d="M16 16L5 10 16 4l11 6z" fill="#111"/><path d="M5 10l11 6 11-6M16 16v12" stroke="#222" fill="none" stroke-width="1.4"/>',
    "vista_lado": '<path d="M16 4l11 6v12l-11 6-11-6V10z" fill="#fff" stroke="#222" stroke-width="1.6" stroke-linejoin="round"/>'
                  '<path d="M16 16v12L5 22V10z" fill="#111"/><path d="M5 10l11 6 11-6M16 16v12" stroke="#222" fill="none" stroke-width="1.4"/>',
    "vista_sombra": '<path d="M16 4l11 6v12l-11 6-11-6V10z" fill="#fff" stroke="#222" stroke-width="1.6" stroke-linejoin="round"/>'
                    '<path d="M16 16l11-6v12l-11 6z" fill="#8a8a8a"/><path d="M5 10l11 6 11-6M16 16v12" stroke="#222" fill="none" stroke-width="1.4"/>',
    "vista_cuadro": '<path d="M5 5h20v20H5z" fill="#fff" stroke="#222" stroke-width="1.6"/><path d="M11 11h18v18H11z" fill="#fff" stroke="#222" stroke-width="1.6"/>',
    "vista_expandir": '<path d="M4 4h8M4 4v8M28 4h-8M28 4v8M4 28h8M4 28v-8M28 28h-8M28 28v-8" stroke="#222" stroke-width="2.6" fill="none"/>',
    "bombilla_on": '<path d="M16 3a8 8 0 0 0-4.5 14.6V21h9v-3.4A8 8 0 0 0 16 3z" fill="#ffd84a" stroke="#b8860b" stroke-width="1.4"/>'
                   '<rect x="11.5" y="22" width="9" height="3" rx="1" fill="#8a8a8a"/><rect x="13" y="26" width="6" height="2.5" rx="1" fill="#6a6a6a"/>',
    "bombilla_off": '<path d="M16 3a8 8 0 0 0-4.5 14.6V21h9v-3.4A8 8 0 0 0 16 3z" fill="#3a3a3a" stroke="#161616" stroke-width="1.4"/>'
                    '<rect x="11.5" y="22" width="9" height="3" rx="1" fill="#8a8a8a"/><rect x="13" y="26" width="6" height="2.5" rx="1" fill="#6a6a6a"/>',
}


def _render(name: str, size: int, scale: float, opacidad: float = 1.0) -> QPixmap:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
           f'{SVG[name]}</svg>')
    px = int(size * scale)
    img = QImage(px, px, QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setOpacity(opacidad)
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(p, QRectF(0, 0, px, px))
    p.end()
    pm = QPixmap.fromImage(img)
    pm.setDevicePixelRatio(scale)
    return pm


_cache: dict[tuple, QIcon] = {}


def icon(name: str, size: int = 28) -> QIcon:
    """Icono normal y deshabilitado (a color pero más tenue, para que los botones «pendientes» no pierdan el aspecto
    de la referencia), a 1× y 2× para pantallas de alta densidad."""
    key = (name, size)
    if key not in _cache:
        ic = QIcon()
        for scale in (1.0, 2.0):
            ic.addPixmap(_render(name, size, scale), QIcon.Normal)
            ic.addPixmap(_render(name, size, scale, 0.72), QIcon.Disabled)
        _cache[key] = ic
    return _cache[key]


def icon_desplegable(name: str, size: int = 28) -> QIcon:
    """Icono seguido de la flecha de lista desplegable (botones «Mostrar todo», «Ejecutar» y «Flechas»)."""
    key = (name, size, "desplegable")
    if key not in _cache:
        ic = QIcon()
        for scale in (1.0, 2.0):
            lado = int(size * scale)
            img = QImage(int(lado * 1.5), lado, QImage.Format_ARGB32_Premultiplied)
            img.fill(0)
            p = QPainter(img)
            p.drawPixmap(0, 0, _render(name, size, scale))
            p.drawPixmap(int(lado * 1.0), int(lado * 0.2), _render("desplegable", int(size * 0.7), scale))
            p.end()
            pm = QPixmap.fromImage(img)
            pm.setDevicePixelRatio(scale)
            ic.addPixmap(pm, QIcon.Normal)
            ic.addPixmap(pm, QIcon.Disabled)
        _cache[key] = ic
    return _cache[key]
