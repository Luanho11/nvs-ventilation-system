# NVS — Noova Ventilation System

Aplicación de escritorio independiente para visualizar y analizar redes de ventilación minera subterránea. El proyecto explora la lectura de archivos `.vsm`, la edición de redes propias y el cálculo de caudales con un solucionador desarrollado para NVS.

NVS no es un producto oficial de VentSim ni de Howden. La lectura de archivos `.vsm` es de solo lectura y algunas funciones del software de referencia todavía no están implementadas.

## Funciones actuales

- Vista 3D de galerías, nodos, terreno y datos de ventilación.
- Importación de redes `.vsm` compatibles en modo de solo lectura.
- Creación y edición de proyectos nativos `.nvs.json`.
- Cálculo de la estática con el motor propio del proyecto.
- Visualización de caudal y velocidad, con comparación entre valores importados y calculados.
- Exportación de resultados a CSV e imagen.

## Tecnologías

- Python 3.12 o superior.
- PySide6 para la aplicación de escritorio.
- NumPy y SciPy para cálculos numéricos.
- Pytest para las pruebas existentes.

## Ejecutar desde el código

Instala [uv](https://docs.astral.sh/uv/) y ejecuta desde la carpeta del proyecto:

```powershell
uv sync
uv run python run_app.py
```

Para correr las pruebas existentes:

```powershell
uv run pytest
```

La compilación para Windows se describe en `build.ps1`. Las instrucciones detalladas de uso están en [`LEEME.txt`](LEEME.txt).

## Estado y límites

La versión indicada por el proyecto es **0.3.1**. Las pruebas diferenciales descritas en la documentación cubren Tutorial1, Tutorial2, DemoMine y RealMine. Otras redes pueden mostrar diferencias porque todavía faltan modelos de ventilación natural, calor, gases, polvo, radón, fuego, ductos y algunos tipos de resistencia y ventilador.

Consulta [`docs/09-primer-entregable.md`](docs/09-primer-entregable.md) para conocer el alcance técnico documentado.
