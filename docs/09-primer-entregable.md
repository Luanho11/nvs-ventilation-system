# Entregable · NVS 0.3.1 (Noova Ventilation System)

Antes llamado VentRebuild. **No es Ventsim ni un producto de Howden.** Este documento resume el entregable; el estado explicado
sin tecnicismos está en `INFORME.md` en la raíz del proyecto.

## Qué se entrega
| Elemento | Ruta |
|---|---|
| Ejecutable de Windows (carpeta autocontenida; no requiere Python) | `dist\NVS\NVS.exe` (12,5 MB; carpeta 221 MB) |
| Copia comprimida | `dist\NVS-0.3.1-win64.zip` (88 MB) |
| Instrucciones breves | `LEEME.txt` |
| Compilación reproducible | `build.ps1` (sincroniza dependencias, ejecuta las 70 pruebas, compila, autoprueba el .exe, crea el zip) |
| Código | `src\nvs\` (lectura, motor, interfaz) · `run_app.py` |
| Reglas de trabajo | `instructions.md` |

Ejecutar desde código: `uv run python run_app.py [proyecto.vsm]`.

## Qué hace (resumen; detalle en `docs/10-diseno-ui.md`)
Abre `.vsm`/`.vsmt` en solo lectura (y proyectos nativos `.nvs.json`), muestra la red en 3D con terreno, notas, etapas y vistas guardadas,
colorea por caudal/velocidad con la escala de Ventsim, anima el aire dentro de los tubos, resalta pistas y nodos, calcula la red con el
motor propio (caudales validados en 4 modelos), compara archivo vs motor y exporta CSV.

## Pruebas (70, todas pasan)
Consistencia de los archivos de Ventsim (9), solucionador (3), resistencia (4), ventiladores (3), predicción completa (4), aplicación y
proyecto nativo (4), visor (5), diálogos y ventana (4), diseño e interfaz, escena/notas/pistas y ruta GPU (incluye el aire animado).
Con los 23 ejemplos: carga, vista, selección, cálculo y CSV sin fallos de lectura. Solo Tutorial1, Tutorial2, DemoMine y RealMine tienen
prueba diferencial aprobada; en el resto el panel «Resumen y validez» lista las funciones sin implementar.

## Limitaciones
Ver `INFORME.md` (lenguaje llano) y `docs/03-matriz-cobertura.md` (detalle). No probado: interacción manual de una persona con el .exe empaquetado.
