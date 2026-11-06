# Plan de reconstrucción conductual

Objetivo fijado por el usuario: reconstrucción funcional de VentSim DESIGN 6.0.5.4 con la máxima equivalencia observable
(funciones, comportamiento, cálculos, resultados, flujos), código propio, verificada con pruebas diferenciales.
No es un simulador genérico. No se declara paridad hasta demostrarla (ver matriz 03 y registro 05).

## Reglas de trabajo
1. Evidencia permitida: archivos de datos del usuario (ejemplos), la aplicación observada en ejecución (experimentos), documentación pública, física publicada. Sin eludir protecciones, sin recuperar código propietario (ver 01).
2. Cada regla implementada cita su evidencia (E-nnn) y su prueba diferencial (D-xxx). Nada se ajusta para que una prueba pase.
3. Cuando falta evidencia, se registra qué falta (06) y se sigue con otra función.

## Grafo de dependencias (qué necesita qué)
```
Formato de proyecto (vsmio) ──► Modelo de datos (galerías, nodos, presets, unidades)
        │                              │
        │                              ├─► Resistencia (geometría, k, choques, densidad)      [D-RES-01 ✔ parcial]
        │                              ├─► Ventiladores (curvas, serie/paralelo, velocidad)    [D-FAN-01 ✔ parcial]
        │                              └─► Red (solver, bocas, caudal fijo, bloqueos)          [D-NET-01/02 ✔ parcial]
        │                                        │
        │                                        ├─► Aire: densidad, psicrometría, NVP         [pendiente D-NVP-01]
        │                                        │      └─► Calor (roca, equipos, enfriadores) [pendiente]
        │                                        │             └─► Humedad / confort / refrigeración
        │                                        ├─► Contaminantes en régimen estacionario (gas, DPM, polvo, radón)
        │                                        │      └─► Dinámica en el tiempo (voladuras, eventos, scripts)
        │                                        ├─► Fuego y humo (presión de fuego, propagación)
        │                                        ├─► Ductos y fugas
        │                                        └─► Rutas de escape, tráfico, refugios, efecto pistón
Presentación: editor 3D, vistas, flechas/colores, tablas de resultados, gráficos, informes, importar/exportar (DXF…)
```

## Secuencia (cada hito termina con prueba diferencial o experimento registrado)
| # | Hito | Estado | Siguiente acción concreta |
|---|---|---|---|
| 1 | Lector de proyectos + oráculo | hecho (23/23 archivos) | Alinear columnas por versión (hoy: detección por GUID) |
| 2 | Solver nodal + resistencia + curvas | hecho para 4 modelos | Extender a RealMine 2, Blue_sky (Fan Config), Heat Strategies en pytest |
| 3 | Descifrar tipos de resistencia (`Resistance Type`<0, presets, formas de sección, perímetro) | en curso | Estadística de 3 modelos + EXP-RT-01 |
| 4 | Presión dinámica / bocas con p≠0 (B09), tratamiento de salidas | pendiente | EXP-NET-01 |
| 5 | Psicrometría + densidad por galería + autocompresión | pendiente | Probar ρ de galería contra columnas `p/db/wb air In/out` (E-001) |
| 6 | Ventilación natural | pendiente | D-NVP-01 (Natural Ventilation Effects) |
| 7 | Calor: roca, equipos, enfriadores, humedad | pendiente | D-HEAT-01 |
| 8 | Contaminantes estacionarios y dinámicos | pendiente | D-GAS-01 |
| 9 | Fuego | pendiente | D-FIRE-01 |
| 10 | Ductos y fugas | pendiente | D-DUCT-01 |
| 11 | Herramientas (escape, tráfico, refugios, pistón…) | pendiente | Observación de UI necesaria |
| 12 | Aplicación de escritorio: modelo de datos propio, editor 3D, resultados, informes, E/S | pendiente | Elegir pila UI (ADR-0002) después de congelar el modelo de datos |

## Arquitectura (decisiones)
- `nvs.vsmio`: lectura del contenedor (solo lectura de archivos del usuario).
- `nvs.network|resistance|fan|…`: motores matemáticos independientes, sin dependencia de UI ni de formato.
- `nvs.vsmnet`: puente formato→motor (aquí viven las hipótesis H*, con su evidencia).
- UI y persistencia propia: se diseñarán sobre el modelo de datos del motor (ADR-0002), no sobre el .vsm.
Ver docs/decisions/.
