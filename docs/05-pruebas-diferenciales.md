# Pruebas diferenciales contra VentSim DESIGN 6 (oráculo)

## Fuentes de oráculo
1. **Resultados guardados en los .vsm de ejemplo** (instalación 6.0.5.4 del usuario; los archivos los guardaron versiones 5.1 – 6.0.4.6).
   Ventaja: reproducible, sin interacción de UI. Limitación: el resultado es de la versión que guardó el archivo, no
   necesariamente de 6.0.5.4; y solo se conocen los resultados almacenados (no cualquier entrada).
2. **Experimentos controlados en la aplicación** (pendiente; requiere ejecutar VentSim por una persona o por
   automatización de UI aprobada). Protocolo en docs/06-experimentos-manuales.md.

## Registro de pruebas (ejecutar: `uv run pytest -q`)
Estado: ✔ pasa · ✖ falla (causa investigada) · ⏳ pendiente. Tolerancia de caudal: error relativo < 1e-3 en |Q| > 1 m³/s.
«Máx. error» = máximo relativo en galerías con |Q|>1 de ese modelo. Archivos de prueba: `tests/test_diff_*.py`.

### D-NET-01 · solución de red con R y presión de ventilador guardadas (aísla el solucionador)
| ID | Modelo (versión que guardó) | Máx. error | Estado | Notas |
|---|---|---|---|---|
| D-NET-01a | Tutorial1 (6.0.4.6) | 2,7e-7 | ✔ | |
| D-NET-01b | Tutorial2 (6.0.1.0) | 8,4e-8 | ✔ | requirió H2 (bloqueo) |
| D-NET-01c | DemoMine (6.0.1.0) | 4,9e-5 | ✔ | requirió H3 (caudal fijo) |
| D-NET-01d | RealMine (6.0.1.0) | 3,9e-5 | ✔ | requirió H4b (Fan Off); solver con tolerancia 1e-8 no cierra en 200 it. (error de flujo < 4e-5) |
| D-NET-01e | Heat Strategies (6.0.1.0) | 6,1e-9 | ✔ | solo con script exploratorio, no incluida aún en pytest |
| D-NET-01f | DevSolids (6.0.1.0) | 1,8e-7 | ✔ | idem |
| D-NET-01g | RealMine 2 (6.0.1.0) | 0,28 | ✖ | fuente no modelada en ramas con flags 0x3102 |
| D-NVP-01 | Natural Ventilation Effects (6.0.1.0) | 0,04 | ✖ | falta ventilación natural |
| D-NET-01h | Blue_sky (6.0.2.9) | 40 | ✖ | ventiladores tipo 22 (`Fan Config` ≠ 0) |
| D-HEAT-NET | InclinedHeatMine (6.0.1.0) | 4,2 | ✖ | calor / NVP |
| D-FIRE-01 | Fire, Fire2 (6.0.1.0) | 92 | ✖ | fuego |
| D-DUCT-01 | without_ducting (6.0.1.0) | 1,0 | ✖ | ductos |

### D-RES-01 · resistencia desde geometría (módulo `resistance.py`) — ✔
`R = (k·(L+Le)·P/A³ + R_preset)·ρ/1,2` con ρ = AIRSIM[13]. Desviación 0,00000 respecto de `Resistance` guardada en
DemoMine (228+13 galerías), Tutorial1 (129), Tutorial2 (172+2), RealMine (1090+69). Tolerancia de la prueba 1e-5.
Quedan fuera y **sin descifrar** (se usan valores guardados en las pruebas predictivas): `Resistance Type` negativos
(-1, -2, -7, -9), galerías con densidad por galería (simulación térmica), ductos, y 1 galería de Heat Strategies.

### D-FAN-01 · curva de ventilador (módulo `fan.py`) — ✔
Presión estática = interpolación **lineal** entre los puntos de entrada de la tabla FANS, por unidad (Q/n), 100 % de
velocidad. Verificado en DemoMine, Tutorial2, RealMine. No cubierto: velocidad ≠ 100 %, `Fan Config` ≠ 0, densidad
≠ densidad de la curva, curvas reversas, eficiencia y potencia.

### D-NET-02 · predicción completa (R de geometría + curvas de ventilador, sin presiones guardadas) — ✔ con salvedades
| Modelo | Máx. error | R calculada / R guardada (tipo sin descifrar) | Ventiladores por curva |
|---|---|---|---|
| Tutorial1 | < 1e-3 | casi todas / 2 | 0 (caudal fijo) |
| Tutorial2 | < 1e-3 | 174 / 10 | 1 |
| DemoMine | < 1e-3 | 239 / 11 | 7 |
| RealMine | < 1e-3 | 1159 / 183 | 25 |
Salvedad honesta: en 4–14 % de las galerías la resistencia se toma del archivo porque su tipo aún no está descifrado.
Por tanto D-NET-02 prueba el solucionador + fricción + curvas, **no** la totalidad del modelo de resistencias.

## Hipótesis (estado)
| H | Enunciado | Evidencia | Estado |
|---|---|---|---|
| H1 | Nodos por coincidencia de extremos; grado-1 ⇒ boca a 0 Pa | 4 modelos predictivos | Aceptada para esos modelos; bocas con p≠0 (Tutorial2 +202 Pa en la salida del ventilador = presión dinámica) quedan por modelar (B09) |
| H2 | R≥1000 con Q=0 ⇒ bloqueada | Tutorial2: 0,94 % → 0 % | Aceptada |
| H3 | `Branch Flags` & 4 ⇒ caudal fijo | DemoMine (n=1) | Provisional |
| H4 | Fuente de ventilador = presión estática de la curva | 57 ventiladores | Aceptada; `Pressure Fan` = estática + ½ρ(Q/n/A_fan)² (verificado a mano en 3 casos) |
| H4b | `Fan Off`=True ⇒ fuente 0 | RealMine | Aceptada |
| H5 | Para Q≤0 contra el ventilador, la presión es la de cierre (constante) | **sin observación** | Supuesto de implementación, no verificado |
| H6 | La densidad constante del modelo está en AIRSIM[13]; AIRSIM[3] activa ventilación natural | 5 modelos | Provisional (col. 3 sin probar) |

## Reglas metodológicas
- No se ajusta ningún parámetro para que una prueba pase. Cada diferencia se investiga y se documenta con su causa.
- Los resultados guardados por versiones anteriores a 6.0.5.4 se marcan como tales; si difieren de 6.0.5.4 se verá en experimentos de la aplicación.
- Los datos derivados del oráculo (`oracle/`) permanecen locales y no se redistribuyen.
- Un valor guardado usado como entrada se declara explícitamente (columna «R guardada»).
