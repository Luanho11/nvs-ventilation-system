# NVS (Noova Ventilation System): leer SIEMPRE antes de trabajar

REGLA MADRE: trabajar SIEMPRE con REA, RECONSTRUIR desde los archivos y recursos de la aplicación de referencia, nunca construir desde cero,
y DECIR en cada paso «REA: <herramienta> para <objetivo>» o «Sin REA: <motivo>». Detalle completo, límites y método:

@instructions.md

Hecho clave: Ventsim NO es Python (.NET Framework 4.7.2 x86, WinForms + DevExpress, DirectX); sus ensamblados principales están protegidos y no se eluden.
Python/PySide6 es la elección de NVS (ver `docs/12-python-o-no.md`).
