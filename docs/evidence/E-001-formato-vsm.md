# E-001 · Formato de archivo .vsm / .vsmt (observado)

Fuente: 23 archivos de `C:\Program Files\Ventsim DESIGN 6\examples` (solo lectura, copias descomprimidas solo en
el scratchpad). Los datos derivados (`oracle/`) son locales y **no se redistribuyen**. Ninguna información procede
de los ejecutables.

## Contenedor
- gzip estándar (`1F 8B`) → texto UTF-8, líneas CRLF, campos separados por TAB. No es una protección.
- Línea 1: cabecera global (30 campos; locale `en-AU/en-US` en h[12], versión de guardado en h[11], p. ej. ` 6.0.4.6`).
- Secciones: línea de un token abre (`KFACTORS`), `END<TAB>KFACTORS` cierra; algunas usan un token de cierre
  (`ENDHEAT`, `ENDROCK`, `ENDTUNNEL`, `ENDPROFILES`, `ENDFILE`).
- Tablas con cabecera: `MAIN` (red actual), `ROLLBACK` (buffer de deshacer), `EVENTDATA`.

## Inventario de secciones (≈ 90) — ver matriz de cobertura
Presets: KFACTORS, RESISTANCES, SHOCKFACTORS, HEATFACTORS, ROCKPRESETS, TUNNELPRESETS/PROFILES, LEAKAGES, WETNESS,
COMBUSTABLES, VENTFIREPRESETS, ROOMFIREPRESETS, DOORFIREPRESETS, GASES, DOORPRESETS, ROOMACTIVITIES, PROFILESORTORDER,
BATTERYCOMBUSTIBLES, LOSSFACTORS, CONTRACTION, PIPEPRESETS, PIPEGROUPS, CHANNELS, VALVES, SPRAY, TANKEXIT, LEAKAGE,
LAYERS, PRIMARY/SECONDARY (capas), AIRTYPES, STAGES, FLUIDTYPES, LEVELS, FANS, FANPICS, SAVEVIEWS, STATE, MESSAGEBOX,
COLORS, FINANCE, SENSORS, LIVEVIEW, LIVESETTINGS, LOGGERSETTINGS, SETTINGS, CONTAMINANT, HEATSIM, HEATPHYSICALS, AIRSIM,
DEFAULTAIRWAY, GRAPHICS, COORDINATES, STARTUP, OTHER, ESCAPE, UNITS/UNITS_5/UNITS_6, SENSORTYPES, STATICSCRIPT,
DYNAMICSCRIPT, REFLAYERS, REFERENCE, REFTEXT, FAVOURITES, EVENTS, ICONPICTURES, BACKGROUNDPICTURES, STATICSCRIPTDATA,
SAVEFLIGHTS, SAVEGRAPHLIMITS, SENSORSETTINGS, WATERWAYS, DUCTHEATTRANSFERPRESETS, REGULATORPRESETS, ROOMS, DOORS,
REFUGESETTINGS, CONNECTPRESETS, TRACKS, FILTERPRESETS, FLEETPRESETS, VEHICLEPRESETS, SPREADSHEETS, EXPLOSIVEPRESETS,
CONVEYORS, CONNECTMACROS, GOAFS, FANSTATUSIDS, TRAFFIC, FLYWHEELDATA, DUSTPROFILEPRESETS, PUMPSDATA, PUMP, VALVE, TANK,
EMITTER, JUNCTION, MONITOR, TURBINES.

## Tabla MAIN (una fila por galería, 279 campos)
La cabecera nombra 278 columnas pero las filas llevan **una columna extra sin nombre antes de `GUID`**; desde `GUID`
todo está desplazado +1 respecto a la cabecera. Confirmado con valores (DemoMine `Unique No`=1: kFactor 0.0417 =
«Concrete Shaft Sets»; Length 328 = Δz). Implementado en `vsmio.aligned_table` (detección por la posición del GUID).

### Relaciones verificadas en los ejemplos (tests/test_oracle_consistency.py)
| Relación | Resultado |
|---|---|
| Topología: nodos = extremos coincidentes en (X,Y,Z) a 0,01 | DemoMine: 179 nodos |
| Continuidad de `Quantity` en nodos | residuo mediano 0,0000 |
| `Pressure Branch` ≈ `Resistance`·`Quantity`² | DemoMine 241/250, RealMine 1162/1342, Tutorial2 180/184 (resto: galerías cerradas, R=10³…10⁹) |
| `Length` = distancia geométrica | exacto en DemoMine/Tutorial2; RealMine tiene longitudes fijadas (override) |
| Extremos de grado 1 a la cota de superficie = bocas con presión de referencia | DemoMine: 3 (2 con ventilador, 1 natural) |
| `Fan Type` indexa la tabla FANS; `Fan Numbers` = nº de unidades | DemoMine: tipos 1,2,4,5 |

### Pendiente de decodificar (columnas)
Semántica exacta de: flags de rama, `Pressure Fix`/`QuantityFix`/`Fix Massflow` (el valor 218.09 kg/s parece masa),
tipos de resistencia/shock (índices a presets), formato de las filas de curva en FANS, aire (densidad, wb/db,
presiones de aire), calor, gases, DPM, radón, enfriadores, filtros, reguladores, refugios, goafs, explosivos.
