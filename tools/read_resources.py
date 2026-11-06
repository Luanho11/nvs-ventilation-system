"""Lee los recursos localizados (.resources) de un ensamblado satélite de idioma (solo lectura, solo textos).

Uso: python tools/read_resources.py <ensamblado.resources.dll> [nombre_recurso_contiene] [--all]
Los satélites de idioma son datos de localización sin protección. Formato: .NET ResourceReader estándar.
"""
import struct
import sys

import pefile


def read7(b, o):
    n = shift = 0
    while True:
        c = b[o]
        o += 1
        n |= (c & 0x7F) << shift
        if not c & 0x80:
            return n, o
        shift += 7


def read_str(b, o):
    n, o = read7(b, o)
    return b[o:o + n].decode("utf-8", "replace"), o + n


def parse_resources(b):
    magic, hv, hs = struct.unpack_from("<III", b, 0)
    assert magic == 0xBEEFCACE, hex(magic)
    o = 12 + hs
    ver, count, ntypes = struct.unpack_from("<III", b, o)
    o += 12
    types = []
    for _ in range(ntypes):
        t, o = read_str(b, o)
        types.append(t)
    o = (o + 7) & ~7
    o += count * 4                      # hashes
    name_offsets = struct.unpack_from(f"<{count}I", b, o)
    o += count * 4
    data_base, = struct.unpack_from("<I", b, o)
    name_base = o + 4
    out = {}
    for no in name_offsets:
        p = name_base + no
        n, p = read7(b, p)
        name = b[p:p + n].decode("utf-16-le")
        p += n
        doff, = struct.unpack_from("<I", b, p)
        q = data_base + doff
        ti, q = read7(b, q)
        if ti == 1:
            tshort, val = "System.String", read_str(b, q)[0]
        elif ti == 2:
            tshort, val = "System.Boolean", bool(b[q])
        elif ti == 8:
            tshort, val = "System.Int32", struct.unpack_from("<i", b, q)[0]
        elif ti == 0x20:
            ln, = struct.unpack_from("<I", b, q)
            tshort, val = "System.Byte[]", f"<bytes {ln}>"
        elif ti >= 0x40 and ti - 0x40 < len(types):
            tshort = types[ti - 0x40].split(",")[0]
            val = f"<{tshort}>"
        else:
            tshort, val = f"code{ti}", f"<code {ti}>"
        tname = tshort
        out[name] = (tname.split(",")[0], val)
    return out


def manifest_resources(path):
    pe = pefile.PE(path, fast_load=True)
    cli = pe.OPTIONAL_HEADER.DATA_DIRECTORY[14]
    base = pe.get_offset_from_rva(cli.VirtualAddress)
    data = pe.__data__
    # CLI header: Resources RVA/size at +24
    res_rva, res_size = struct.unpack_from("<II", data, base + 24)
    res_off = pe.get_offset_from_rva(res_rva)
    # tabla ManifestResource: se localiza por nombres en el heap #Strings -> usamos secuencia de bloques con prefijo de longitud
    blocks = []
    o = res_off
    while o < res_off + res_size:
        ln, = struct.unpack_from("<I", data, o)
        blocks.append((o + 4, ln))
        o = (o + 4 + ln + 7) & ~7
    return data, blocks


if __name__ == "__main__":
    path = sys.argv[1]
    flt = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    data, blocks = manifest_resources(path)
    for off, ln in blocks:
        blob = data[off:off + ln]
        try:
            res = parse_resources(blob)
        except Exception as e:  # noqa: BLE001
            print(f"[bloque {off} len={ln}] no es .resources: {e}")
            continue
        strs = {k: v[1] for k, v in res.items() if v[0] == "System.String"}
        if "--json" in sys.argv:
            import json
            json.dump({k: v[1] for k, v in res.items()}, open(sys.argv[sys.argv.index("--json") + 1], "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print(f"[bloque len={ln}] entradas={len(res)} cadenas={len(strs)} otros={len(res) - len(strs)}")
        if flt or "--all" in sys.argv:
            for k, v in sorted(res.items()):
                if flt is None or flt.lower() in k.lower() or flt.lower() in str(v[1]).lower():
                    print(f"   {k} = {v[1]!r}"[:230])
