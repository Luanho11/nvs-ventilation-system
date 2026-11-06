# Viabilidad y hoja de ruta (estado a 2026-10-16, V0.1)

> **Todas las cifras de este documento son estimaciones razonadas, no mediciones.** Los porcentajes de cobertura derivan de
> la matriz (docs/03) y de pesos de esfuerzo que asigno yo; los plazos dependen de recursos que aún no están decididos.
> El objetivo no cambia: reconstrucción funcional amplia de VentSim DESIGN 6.0.5.4; no se declara paridad por módulo hasta que
> su criterio de validación (§6) esté cumplido.

## 1. Tres ejes que no deben confundirse
| Eje | Qué mide | Cómo se mide aquí |
|---|---|---|
| **Cobertura funcional** | ¿La función existe y hace lo que hace VentSim en su alcance? | Filas de la matriz con Impl ≥ 1 / Impl = 2; y estimación ponderada por esfuerzo (§2) |
| **Precisión numérica** | ¿Cuánto se parece el resultado al de VentSim donde ya se compara? | Error relativo en pruebas diferenciales (hoy: caudal ≤ 5e-5 en 6 modelos; resistencia 0,00000 en 4; curva de ventilador ≤ 5e-4) |
| **Grado de validación** | ¿Con qué rigor está comprobado? | Niveles L0–L4 (§6). Hoy: lo implementado está en L2 (frente a resultados guardados en archivos) como máximo; **nada está en L3** |

## 2. Cobertura actual y prevista para V0.1
**Por conteo de filas (73 funciones tras añadir las vistas en la interfaz de referencia, sin ponderar):** con alguna implementación 17 (23 %); completa 4 (5 %); con prueba diferencial aprobada 11 (15 %).
Es optimista: una fila «parcial» puede ser una fracción pequeña de la función real, y las filas pesan distinto.

**Ponderada por esfuerzo (estimación mía).** Grupos con esfuerzo total estimado en persona-meses (PM) y avance estimado:

| Grupo | Esfuerzo PM (rango) | Avance antes de V0.1 | Avance con V0.1 |
|---|---|---|---|
| 1 Formato de proyecto (lectura/escritura .vsm/.vsmt, .vlg, .vtp, DXF) | 8 (5–12) | 25 % | 25 % |
| 2 Red y resistencia (solver, tipos de resistencia, secciones, puertas, fugas, goafs) | 10 (7–16) | 35 % | 35 % |
| 3 Ventiladores (curvas, velocidad, serie/paralelo, reverso, potencia, biblioteca) | 5 (3–8) | 25 % | 25 % |
| 4 Aire: psicrometría, densidad, compresibilidad, ventilación natural | 6 (4–10) | 0 % | 0 % |
| 5 Calor y clima (roca, equipos, refrigeración, calefacción, confort) | 14 (9–22) | 0 % | 0 % |
| 6 Contaminantes estacionarios y dinámicos (gas, DPM, polvo, radón, voladuras, eventos, scripts) | 14 (9–22) | 0 % | 0 % |
| 7 Fuego y humo | 8 (5–14) | 0 % | 0 % |
| 8 Ductos, fugas y redes de fluidos (tuberías, bombas, tanques, válvulas) | 10 (6–16) | 0 % | 0 % |
| 9 Herramientas especiales (escape, refugios, tráfico, pistón, cintas, finanzas/carbono, sensores/vivo) | 12 (7–20) | 0 % | 0 % |
| 10 Editor 3D completo (dibujo, snaps, selección múltiple, deshacer, capas, filtros, referencias, niveles) | 14 (9–22) | 1 % | 8 % |
| 11 Presentación (gráficos, tablas, informes PDF, impresión, unidades, exportaciones) | 12 (7–18) | 0 % | 8 % |
| 12 Infraestructura de verificación (experimentos en la aplicación, corpus, regresión) | 8 (6–12) | 20 % | 25 % |
| 13 Empaquetado, instalador, localización, documentación | 4 (3–6) | 5 % | 25 % |
| **Total** | **≈ 125 PM (rango ≈ 80–200)** | **≈ 7 %** | **≈ 10 %** (incertidumbre ±4 puntos; suma ponderada: 8,7 PM → 11,8 PM de ≈125) |

Funciones que entrega V0.1 (todas verificadas por pruebas automáticas o ejecución del .exe): lectura de 23 proyectos de ejemplo,
visor 3D (rotar/desplazar/zoom/seleccionar), propiedades con procedencia (archivo/motor), solucionador de red con resistencia
desde geometría y curvas de ventilador, comparación archivo-vs-motor con estadísticas, tabla ordenable, exportación CSV, proyecto
nativo editable (JSON propio) y ejecutable de Windows. **Lo que V0.1 NO es:** reproducción de la interfaz de VentSim, ni simulación
térmica, de gases, de fuego, etc.

## 3. Dependencias entre módulos
```
Formato (1) ──► Red/Resistencia (2) ──► Ventiladores (3) ──► Aire/psicrometría (4) ──► Calor (5) ──► Fuego (7)
      │                │                                         │                      │
      │                └─► Ductos/fugas/fluidos (8)              └─► Contaminantes (6) ◄─┘ (necesita caudales estables y, para
      │                                                              │                       fuego/calor, densidad y temperatura)
      └─► Editor 3D (10) ──► Presentación (11) ◄── Herramientas especiales (9) ◄── (2)(4)(6)
Infraestructura de verificación (12) alimenta a todos. Empaquetado (13) es transversal.
```
Camino crítico: 2 → 4 → 5 → 6/7. El editor (10) y la presentación (11) pueden avanzar en paralelo, pero dependen del modelo de
datos de 2–6 para no rehacerse.

## 4. Hitos (supuesto de equipo: ~5 FTE = 3 desarrolladores + 1 ingeniero de ventilación + 1 verificación; acceso a VentSim 6.0.5.4)
| Plazo | Entregable previsto | Funciones nuevas | Cobertura ponderada prevista* |
|---|---|---|---|
| **3 meses** (V0.3) | Red completa: tipos de resistencia, formas de sección, serie/paralelo/velocidad/reverso de ventiladores, presión dinámica de salida; psicrometría y densidad por galería; ventilación natural; editor con deshacer/selección múltiple/importar DXF; primera escritura de proyecto nativo robusta | grupos 2, 3, parte de 4 y 10 | ~25 % |
| **6 meses** (V0.5) | Calor y humedad (roca, equipos, refrigeración/calefacción); contaminantes estacionarios (gas, DPM, polvo, radón); gráficos y primer informe | grupo 5, parte de 6 y 11 | ~40 % |
| **12 meses** (V1.0) | Simulación dinámica (transitorios, voladuras, eventos/scripts); fuego/humo básico; ductos y fugas; editor completo; informes PDF; escritura .vsm solo si hay roundtrip verificado | grupos 6, 7, 8, 10, 11 | ~65 % |
| **24 meses** (V2.0) | Herramientas especiales (escape, refugios, tráfico, pistón, cintas, finanzas/carbono), redes de fluidos, sensores/en vivo, localización | grupo 9 y resto de 8 | ~90 % |
| **36 meses** (V3.0) | Cola larga, rendimiento en modelos de 10⁴–10⁵ galerías, validación cruzada de versiones, documentación completa | cierre | ~95–100 % de cobertura; paridad declarada **solo** en módulos que cumplan L3/L4 |
\* Cobertura = esfuerzo ponderado completado. Con 125 PM de esfuerzo central, 5 FTE dan ~25 meses de calendario si todo va bien y sin
sobrecarga de coordinación; los 36 meses incluyen holgura (≈ +40 %) para las incertidumbres de §5. El rango de esfuerzo (80–200 PM)
corresponde a **16–40 meses con 5 FTE**. Con 1 FTE (la situación actual, apoyada por un asistente de IA), 125 PM serían ≈ 10 años
sin asistencia; con asistencia el factor de aceleración es desconocido y **no lo estimo**.

## 5. Recursos y riesgos de calendario
**Recursos necesarios:** (a) acceso continuado a VentSim DESIGN 6.0.5.4 con licencia para experimentos de caja negra (docs/06) — es el recurso
más crítico; (b) ingeniero de ventilación/termodinámica para validar fenómenos (compresibilidad, psicrometría, transferencia de calor, fuego);
(c) corpus de modelos reales con resultados (los 23 ejemplos son insuficientes para L3); (d) máquina Windows con GPU modesta para el visor
(si se pasa de render por software a OpenGL, ver riesgo R6); (e) licencia/asesoría legal sobre el alcance de la ingeniería inversa de
comportamiento (R1).

| Riesgo | Efecto en calendario | Mitigación |
|---|---|---|
| R1 Alcance legal/contractual (EULA, derechos sobre formatos) | Puede bloquear importación/exportación de .vsm o la distribución | Consultar antes de publicar; mantener proyecto nativo propio; no escribir .vsm sin verificación |
| R2 Los resultados guardados en ejemplos son de versiones anteriores a 6.0.5.4 | Diferencias de versión pueden hacer pasar/fallar pruebas por motivos ajenos | Experimentos en 6.0.5.4 (L3); no ajustar parámetros para «cuadrar» |
| R3 Módulos térmicos/fuego/dinámicos con modelos físicos no documentados | Es el grueso del esfuerzo y la mayor incertidumbre (rango ×2) | Experimentos mínimos aislados por fenómeno antes de implementar |
| R4 Falta de observación de la interfaz (menús, defaults, validaciones, informes) | Retrasa matriz completa y paridad de flujos de trabajo | Sesiones de recorrido guiadas con capturas y plantilla de docs/06 |
| R5 Tipos de resistencia, banderas y columnas aún sin descifrar | Diferencias residuales en modelos reales | Estadística sobre más modelos + experimentos EXP-RT |
| R6 Rendimiento en modelos grandes | Mitigado en V0.1.2: visor GPU 4–5 ms/fotograma, cálculo de 6.728 galerías ≈1 s. Queda por medir > 20.000 galerías y simulaciones dinámicas | Medir con modelos sintéticos grandes; mantener el respaldo por software |
| R7 Dependencia de una sola persona/asistente | Sin redundancia | Documentación, pruebas, ADRs, equipo |

## 6. Cuándo se considera «realmente reconstruida» una función
Niveles de validación: **L0** sin implementar · **L1** implementada, pruebas unitarias propias · **L2** diferencial frente a resultados
guardados en archivos de ejemplo · **L3** diferencial frente a experimentos controlados en 6.0.5.4 con entradas arbitrarias y casos límite ·
**L4** L3 + regresión con modelos reales de terceros y comportamiento ante errores/validaciones.
Una función se declara **reconstruida** solo en L3 (y su «paridad» en L4). Criterios propuestos (a ratificar con un experto):

| Familia | Prueba que la hace «reconstruida» (L3) | Tolerancia propuesta |
|---|---|---|
| Resistencia | EXP-RES en ≥ 30 combinaciones (forma, k, Le, densidad, presets) | error relativo en R < 1e-5 |
| Red y caudales | ≥ 10 redes de 10–5.000 galerías, incluidos bloqueos, caudales fijos y mallas | caudal < 1e-3 relativo; presión < 0,1 Pa |
| Ventiladores | Curvas, serie/paralelo, velocidad, reverso, potencia y eficiencia en ≥ 20 casos | presión < 0,5 %; potencia < 1 % |
| Aire/psicrometría | Barrido de T, humedad, presión, cota | densidad < 0,1 %; temperatura húmeda < 0,05 °C |
| Ventilación natural | ≥ 5 casos con diferencia de cota y de temperatura | presión natural < 1 % |
| Calor | Casos aislados (roca sola, equipo, refrigeración, mixto), régimen estacionario y transitorio | temperatura < 0,2 °C; potencia < 2 % |
| Contaminantes | Series temporales en ≥ 10 escenarios (gas, DPM, polvo, voladura) | concentración < 2 % del máximo; tiempo de llegada < 1 paso |
| Fuego | ≥ 5 escenarios con comparación de caudales, humo y temperaturas | a definir con el experto (mayor incertidumbre) |
| Editor / E-S | Roundtrip de proyectos y conjuntos de operaciones (crear/mover/copiar/deshacer) con comparación de estado | igualdad exacta de datos |
| Informes/exportaciones | Comparación campo a campo con las salidas de VentSim | igualdad de valores a la precisión mostrada |
Cada fila exige además: pruebas automáticas en el repositorio, registro de experimentos reproducibles y documento de diferencias conocidas.

## 7. Qué haré a continuación (orden de mayor palanca)
1. Descifrar los tipos de resistencia y las formas de sección (cierra D-NET-02 sin valores del archivo; destraba RealMine 2).
2. Presión dinámica/bocas con p ≠ 0 y ventiladores en serie/paralelo (Blue_sky, Tutorial2 con total).
3. Psicrometría + densidad por galería + ventilación natural (destraba 6 modelos de ejemplo).
4. Primeros experimentos en la aplicación (docs/06) cuando haya acceso; en paralelo, rendimiento del solucionador.
