# ¿Seguimos con Python? (decisión revisada el 2026-10-16, V0.3)

**Respuesta corta: sí, por ahora.** Cambiarlo hoy costaría semanas y no arregla nada que hoy importe. Hay cuatro motivos para volver a decidir más adelante (abajo).

## Medido con NVS 0.3.0 (Windows 11, GPU integrada)
| Medida | Valor |
|---|---|
| Arranque hasta tener Blue_sky (835 galerías, terreno con textura) cargado y dibujado | 5,6 s |
| Memoria con el ejemplo abierto | 260 MB |
| `NVS.exe` / carpeta completa / zip | 12,5 MB / 221 MB / 88 MB |
| Fotograma del visor (GPU, 835–6.728 galerías) | 4–5,5 ms (≈200 fps; 60 fps con sincronía vertical) |
| Carga de `diamondmine` (1,1 M de líneas) / cálculo de sus 6.728 galerías | ≈ 4 s / 1,0 s |
| Pruebas automáticas | 64 pasan |

## Opciones comparadas
| Opción | A favor | En contra |
|---|---|---|
| **Python + PySide6 (actual)** | Lo que más rápido permite descifrar formatos y comprobar la física (NumPy/SciPy); el motor ya está validado en 4 modelos con pruebas; GPU ya fluida | Instalador grande (221 MB), arranque de 5 s, el código no queda protegido en el .exe, cálculos largos (calor, dinámica) pedirán código compilado |
| C# / .NET 8 (WPF/WinForms + OpenGL o DirectX) | Es la tecnología de Ventsim; instalador ≈ 40–70 MB; arranque < 2 s; fácil de proteger y de firmar | Reescribir ≈ 5.000 líneas y rehacer el visor; el análisis de formatos sería más lento |
| C++ / Qt | Máximo rendimiento y tamaño pequeño | La opción más lenta de desarrollar; no hace falta con el rendimiento actual |
| Web (Tauri/Electron + three.js) | Coincide con el resto de productos de Noova; multiusuario; sin instalación | Visor 3D y cálculos pesados en el navegador son más limitados; requiere rehacer todo |

## Decisión
1. **Mantener Python mientras el trabajo sea descifrar y verificar** (formato, física, interfaz). Es donde más se avanza por hora.
2. **El motor numérico queda separado** (`network.py`, `resistance.py`, `fan.py`, `vsmio.py`, `vsmnet.py`, sin dependencias de interfaz) y sus 23 pruebas contra los archivos de Ventsim son la especificación exacta de una futura migración.
3. **Volver a decidir** si ocurre alguna de estas cuatro cosas: (a) el instalador de 221 MB o el arranque de 5 s molestan a los clientes; (b) se necesita proteger el código; (c) el calor o la simulación dinámica tardan demasiado; (d) se quiere ofrecer NVS por navegador.
4. Si se migra, el destino recomendado es **C# .NET 8** para escritorio (o web si se prioriza multiusuario); los cálculos pesados pueden pasar antes a una extensión compilada sin tocar la interfaz.
