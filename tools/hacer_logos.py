"""Genera los recursos de marca de NVS a partir de los logotipos entregados en `ref/` (no se dibuja nada nuevo).

    uv run python tools/hacer_logos.py

Salida:
  assets/nvs.ico            icono del .exe (7 tamaños, reducidos del PNG entregado; no se vectoriza ni se redibuja)
  src/nvs/data/img/*.png    los PNG entregados, sin alterar salvo el tamaño del logotipo del software
"""
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
REF, ASSETS, IMG = RAIZ / "ref", RAIZ / "assets", RAIZ / "src" / "nvs" / "data" / "img"
TAMANOS_ICO = [16, 24, 32, 48, 64, 128, 256]


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    IMG.mkdir(parents=True, exist_ok=True)
    software = Image.open(REF / "noova-software.png").convert("RGBA")
    software = software.crop(software.getbbox())
    lado = max(software.size)
    lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    lienzo.paste(software, ((lado - software.width) // 2, (lado - software.height) // 2))

    lienzo.resize((256, 256), Image.LANCZOS).save(ASSETS / "nvs.ico", sizes=[(t, t) for t in TAMANOS_ICO])
    lienzo.resize((512, 512), Image.LANCZOS).save(IMG / "logo-software.png", optimize=True)
    for nombre in ("Logo-base.png", "logo-loader-blanco.png"):
        Image.open(REF / nombre).convert("RGBA").save(IMG / nombre.lower(), optimize=True)


if __name__ == "__main__":
    main()
