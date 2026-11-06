# ADR-0002 · Pila gráfica y empaquetado de V0.1

**Fecha:** 2026-10-16 · **Estado:** vigente para V0.1 (revisable en V0.3)

## Contexto
Código existente en Python 3.12 (NumPy/SciPy). Entorno Windows 11 x64; Python 3.14 y uv disponibles; sin .NET SDK, sin Node necesario.

## Decisión
- **Interfaz:** PySide6 (Qt 6.12). Alternativas descartadas: Tkinter (sin 3D ni tablas ordenables ricas), Electron/Three.js (dos pilas y reescribir la conexión con el motor), Dear PyGui/PyQtGraph-GL (dependen de OpenGL y de controladores).
- **Visor 3D:** render por software con QPainter y proyección perspectiva propia (NumPy vectorizado). Ventajas: sin dependencias de GPU, empaquetado fiable, selección exacta por distancia en pantalla, pruebas con eventos sintéticos. Coste: límite práctico ≈ 20.000 galerías (≈ 0,2 s/fotograma a 6.700). Se reevaluará OpenGL con instancing en V0.3 si el rendimiento lo exige.
- **Empaquetado:** PyInstaller 6 en modo carpeta (`--windowed`). Alternativas: modo un-solo-archivo (arranque lento y extracción a temporal por cada ejecución; antivirus) y Nuitka (compilación más larga; sin ventaja necesaria hoy).
- **Procedencia de datos:** cada campo se etiqueta `archivo` o `motor` en el modelo (`Airway.saved_*` / `calc_*`), no solo en la interfaz.
- **Proyecto nativo:** JSON propio versionado (`nvs-nativo`, v1). **No se escribe .vsm** hasta verificar un roundtrip contra la aplicación.
- **Hilos:** carga y cálculo en `QThread`; la interfaz nunca se bloquea.

## Consecuencias
El mismo motor sirve a la GUI, a las pruebas y a la autoprueba del .exe (`--selftest`). La carpeta distribuible es grande (196 MB) por SciPy/Qt; aceptable para V0.1.
