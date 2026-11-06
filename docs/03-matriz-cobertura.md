# Matriz de cobertura funcional (objetivo: TODAS las funciones identificables de VentSim DESIGN 6.0.5.4)

Leyenda de estado — **Ev**: evidencia (0 ninguna · 1 solo nombre de sección/columna en archivos · 2 comportamiento observado en datos · 3 reglas verificadas)
· **Impl**: 0 no · 1 parcial · 2 completo · **Dif**: prueba diferencial (— ninguna · ID de prueba · ✔ pasa · ✖ falla).
Fuente de la lista: secciones y columnas observadas en los .vsm de ejemplo (E-001) + áreas pedidas. Es un punto de partida, **no un catálogo cerrado**: se añaden filas cuando se descubren funciones nuevas.

## A. Modelado y edición
| ID | Función | Ev | Impl | Dif | Notas / qué falta |
|---|---|---|---|---|---|
| A01 | Galerías (segmentos con extremos 3D, nodos por coincidencia) | 3 | 1 | D-NET ✔ | Falta editor, división/unión automática, tolerancia de nodo configurable |
| A02 | Nodos con nombre / intersecciones | 1 | 0 | — | Columnas Entry/Exit Node = nombres |
| A03 | Secciones: ancho, alto, área, perímetro, tipo de forma | 2 | 0 | — | `Shape Type`, `shapetype52`, `shapepresetindex`, `Obstruction`; ver PROFILESORTORDER |
| A04 | Perfiles de túnel / presets (TUNNELPRESETS, TUNNELPROFILES) | 1 | 0 | — | Vacíos en los ejemplos revisados |
| A05 | Niveles (LEVELS) | 1 | 0 | — | |
| A06 | Capas/primary-secondary layers, filtros, colores | 1 | 0 | — | |
| A07 | Selección, copiar, mover, rotar, eliminar, deshacer (ROLLBACK) | 1 | 1 | — | V0.1: añadir/editar/eliminar en proyecto nativo; sin deshacer ni selección múltiple |
| A08 | Importación DXF (carpeta examples/dxf) | 1 | 0 | — | 9 DXF de ejemplo disponibles |
| A09 | Importación de datos de levantamiento (.vlg, texto/CSV, Jet DB) | 1 | 0 | — | SurveyBackend.vlg |
| A10 | Referencias (REFERENCE, REFLAYERS, REFTEXT, imágenes de fondo) | 1 | 0 | — | |
| A11 | Grupos / favoritos / vistas guardadas (SAVEVIEWS, FAVOURITES) | 1 | 0 | — | |
| A12 | Validación y mensajes de error (MESSAGEBOX, Warning Key, ErrorBranch) | 1 | 0 | — | Requiere observación de la UI |
| A13 | Visor 3D (zoom, rotación, desplazamiento, selección, panel de propiedades) | 2 | 1 | — | V0.1.1: tubos con volumen, cielo/horizonte, rejilla, etiquetas sin solapes, callout, gizmo, vistas estándar (docs/10); sin snaps, cortes ni z-buffer |
| A14 | Superficie/terreno 3D y sólidos (vistos en la referencia, E-002) | 1 | 0 | — | Sin datos de sólidos cargados |
| A15 | Etapas (selector «Etapa», STAGES) | 1 | 0 | — | Visto en E-002 |
| A16 | Vistas guardadas (menú y selector) | 1 | 0 | — | SAVEVIEWS en archivo; selector visto en E-002 |
| A17 | Notas / anotaciones en el modelo (menú «Nota», cuadros de texto) | 1 | 0 | — | Visto en E-002 |
| A18 | Estilos de exposición por pestañas (capas, estilos, transparencia) | 1 | 0 | — | Panel «Exponer» de E-002; NVS solo implementa la pestaña de color |

## B. Cálculo y ventilación
| ID | Función | Ev | Impl | Dif | Notas |
|---|---|---|---|---|---|
| B01 | Ley cuadrática ΔP = R·Q² y red por presiones nodales | 3 | 2 | D-NET-01 ✔ (6 modelos) | `network.py` |
| B02 | Galerías bloqueadas (R≥1000, Q=0) | 3 | 2 | ✔ | |
| B03 | Caudal fijo (Branch Flags&4) | 2 | 2 | ✔ DemoMine | Falta decodificar resto de banderas |
| B04 | Ventiladores: fuente = Static Pressure en punto de operación | 3 | 1 | ✔ | Falta evaluar la curva (spline) → D-FAN-01 |
| B05 | Ventilador apagado (Fan Off) | 3 | 2 | ✔ RealMine | |
| B06 | Curvas de ventilador (tabla FANS, spline, eficiencia, potencia, velocidad %, densidad) | 3 | 1 | D-FAN-01 ✔ | V0.1: curva lineal por unidad (n en paralelo); sin velocidad≠100 %, serie, reverso, potencia |
| B07 | Ventiladores en serie/paralelo (`Fan Config`, `Fan Numbers`) | 2 | 0 | — | Falla Blue_sky (tipo 22) |
| B08 | Ventilador inverso / reversible (`Fan Run Reverse`, `Fan Reverse Flag`) | 2 | 0 | — | |
| B09 | Presión dinámica del ventilador / nodos de salida (p_exit = Pv) | 2 | 0 | — | Tutorial2: nodo de salida +202,33 Pa |
| B10 | Resistencia desde k-factor, longitud, perímetro, área (Atkinson) | 3 | 1 | D-RES-01 ✔ | V0.1: sección rectangular/circular propia; formas de VentSim sin descifrar |
| B11 | Pérdidas por choque (shock type/factor, SHOCKFACTORS, LOSSFACTORS, CONTRACTION) | 2 | 1 | D-RES-01 ✔ | V0.1: solo longitud equivalente Le (shock factor); X-factor y contracciones sin descifrar |
| B12 | Resistencias discretas: puertas, reguladores, tapones (RESISTANCES, DOORPRESETS, REGULATORPRESETS) | 2 | 1 | D-RES-01 ✔ | V0.1: presets numéricos (puertas…); tipos negativos sin descifrar |
| B13 | Fugas (LEAKAGES, `LeakageType`) | 1 | 0 | — | |
| B14 | Presión/caudal fijos con fuente (Pressure Fix, pqP/pqQ/pqL) | 1 | 0 | — | |
| B15 | Flujo compresible, densidad, presión atmosférica (`p air In`, `Dry Massflow`) | 2 | 0 | — | `Dry Massflow` = 1,2·Q exacto en los ejemplos |
| B16 | Ventilación natural (NVP; `Calc NVP Pressure`) | 2 | 0 | D-NVP-01 ✖ | Falla Natural Ventilation Effects (1–4 %) |
| B17 | Ductos (DuctType, ductHeatTransferType, PIPEPRESETS, fugas de ducto) | 1 | 0 | D-DUCT-01 ✖ | Falla without_ducting |
| B18 | Filtros (FILTERPRESETS, filterType/Clogging/NumberUnits) | 1 | 0 | — | |
| B19 | Goafs (GOAFS) | 1 | 0 | — | |
| B20 | Recirculación (Recirc %) | 1 | 0 | — | |
| B21 | Turbinas, bombas, válvulas, tanques, emisores, junctions, monitores (PUMP, VALVE, TANK, EMITTER, JUNCTION, MONITOR, TURBINES, FLYWHEELDATA) | 1 | 0 | — | Redes de fluidos (agua/refrigerante) |
| B22 | Etapas (STAGES, Stage/newstage) | 1 | 0 | — | |

## C. Simulación ambiental y dinámica
| ID | Función | Ev | Impl | Dif | Notas |
|---|---|---|---|---|---|
| C01 | Calor sensible/latente, psicrometría (wb/db/p entrada/salida) | 2 | 0 | D-HEAT-01 | Columnas `wb/db air In/out` guardan resultados |
| C02 | Calor de roca (ROCKPRESETS, rock conductivity/age/diffuse…) | 2 | 0 | — | |
| C03 | Humedad/mojado de galería (WETNESS, Wetness) | 1 | 0 | — | |
| C04 | Fuentes de calor (HEATFACTORS: diésel, lineales, puntuales, oxidación) | 2 | 0 | — | |
| C05 | Enfriadores (coolertype, capacity, COP, coolant…) | 1 | 0 | — | |
| C06 | Calentadores (heater*) | 1 | 0 | — | |
| C07 | Autocompresión / densidad por profundidad | 2 | 0 | — | |
| C08 | Equipos diésel, flotas, vehículos, emisiones (FLEETPRESETS, VEHICLEPRESETS, dieselkw, DPM) | 1 | 0 | — | |
| C09 | Gases y contaminantes (CONTAMINANT, GASES, columnas O2…SOOT; dinámica) | 1 | 0 | D-GAS-01 | |
| C10 | Polvo (DUSTPROFILEPRESETS, dust*) | 1 | 0 | — | |
| C11 | Radón (radon*) | 1 | 0 | — | |
| C12 | Humo/fuego: VENTFIREPRESETS, ROOMFIREPRESETS, DOORFIREPRESETS, COMBUSTABLES, BATTERYCOMBUSTIBLES | 2 | 0 | D-FIRE-01 ✖ | Fire.vsm / Fire2.vsm |
| C13 | Voladuras/explosivos (EXPLOSIVEPRESETS, Blast) | 1 | 0 | — | |
| C14 | Simulación dinámica con scripts/eventos (DYNAMICSCRIPT, EVENTS, EVENTDATA) | 1 | 0 | — | |
| C15 | Sensores y datos en vivo (SENSORS, LIVEVIEW, LOGGERSETTINGS, SENSORTYPES, Modbus) | 1 | 0 | — | |

## D. Herramientas especializadas
| ID | Función | Ev | Impl | Dif | Notas |
|---|---|---|---|---|---|
| D01 | Rutas de escape / refugios (ESCAPE, REFUGESETTINGS, distancetorefuge/surface) | 1 | 0 | — | |
| D02 | Recorridos, tráfico, caminos de equipos (TRAFFIC, TRACKS) | 1 | 0 | — | |
| D03 | Efecto pistón / transitorio de túneles (Tunnel Ventilation.vsmt, Transverse.vsmt) | 1 | 0 | — | |
| D04 | Intercambiadores de calor, flywheel, conveyors (CONVEYORS, ROOMS, DOORS, WATERWAYS) | 1 | 0 | — | |
| D05 | Funciones de carbono / finanzas (FINANCE) | 1 | 0 | — | |
| D06 | Plantillas visuales (.vtp, `Settings.vtp`) | 2 | 0 | — | Texto tabulado legible |
| D07 | Hojas de cálculo (SPREADSHEETS), ventilador de túnel por defecto (.vsmt/.json) | 1 | 0 | — | |

## E. Gestión y presentación
| ID | Función | Ev | Impl | Dif | Notas |
|---|---|---|---|---|---|
| E01 | Lectura de proyectos .vsm / .vsmt | 3 | 1 | ✔ | `vsmio.py`; solo lectura |
| E02 | Escritura de proyectos (formato propio y, si se verifica, .vsm) | 0 | 1 | — | V0.1: proyecto nativo JSON propio; escritura .vsm NO implementada (a propósito) |
| E03 | Unidades y formatos (UNITS, UNITS_5/6; métrico/imperial) | 2 | 0 | — | Tabla de unidades con factores observada |
| E04 | Presets de proyecto (SETTINGS, DEFAULTAIRWAY, STARTUP, COORDINATES…) | 1 | 0 | — | |
| E05 | Gráficos, flechas, colores, leyendas (COLORS, GRAPHICS, SAVEGRAPHLIMITS) | 1 | 1 | — | V0.1.1: color por umbrales editables (bandas/continuo) para caudal, velocidad, pérdida de presión y diferencia; etiquetas; flechas; sin capas/filtros |
| E06 | Informes e impresión (DevExpress Printing/Pdf/RichEdit en bin) | 1 | 0 | — | Observación de UI necesaria |
| E07 | Exportaciones (DXF, imágenes, vídeo `ffmpeg.exe`, CSV, MDB `MDBAccess.exe`) | 1 | 1 | — | V0.1: solo CSV; DXF/imágenes/vídeo/MDB pendientes |
| E08 | Idiomas (es, pl, ru, vi presentes) | 1 | 0 | — | |
| E09 | Licencias / protección | 0 | — | — | **Fuera de alcance**: no se implementa ni se elude |
| E10 | Tabla de resultados y comparación archivo-vs-motor, con procedencia | 1 | 1 | — | V0.1: tabla ordenable + estadísticas; sin gráficos ni informes |
| E11 | Ventlog / sensores y datos en vivo en la interfaz | 1 | 0 | — | Menú visto en E-002 |
| E12 | Animación / reproducción de simulación (película, controles de reproducción en estado) | 1 | 0 | — | Visto en E-002 |

## Resumen de cobertura (V0.1.1, 2026-10-16) — conteo de filas, sin ponderar
- 73 funciones listadas (E09, «licencias/protección», se excluye por decisión). Se añadieron 7 filas (A14–A18, E11–E12) al observar la interfaz de referencia (E-002).
- Con alguna implementación (Impl ≥ 1): **17 de 73 (23 %)**; implementación completa (Impl = 2): 4 (5 %).
- Con prueba diferencial aprobada (✔) sobre al menos un modelo de ejemplo: 11 de 73 (15 %) — parcial en todos los casos.
- Con evidencia suficiente para implementar (Ev ≥ 2): 25 de 73 (34 %).
- Las filas no pesan lo mismo: ver docs/08 para la estimación ponderada por esfuerzo (≈ 10 %).
**No se declara paridad.**
