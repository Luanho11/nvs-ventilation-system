# E-006 · Cámara, rejilla, flechas, terreno, estado guardado y ratón (V0.3.1, 2026-10-16)

Fuente principal: **Ventsim DESIGN 6 real, abierto y visible** (el usuario lo dejó abierto con `coalmine.vsm`; después se cargaron desde su
menú «Cargar demostración» Mina de carbón, Demo de fuego y Mina de metal). Observación con `tools/observe_ventsim.ps1` (MSAA +
PrintWindow, **solo la ventana**). REA no puede observar ventanas en Windows (L-06).

## Uso de REA en esta fase (honesto)
| Paso | Herramienta | Resultado |
|---|---|---|
| Inventario de recursos de `VVentsim.resources.dll` | **REA** `inspect_managed_artifact` | 3 recursos, cobertura completa (`ev_53dbe686…`) |
| Motor gráfico `ChasmGraphics.DLL` (43 MB) | **REA** `inspect_pe_resources`, `inspect_managed_artifact`, `inspect_analysis_view` | 4 recursos incrustados con nombres aleatorios (42,8 MB): código cifrado por un protector; **no se abre** (L-09) |
| Textos de ayuda del ratón, «Visibilidad», «Ocultar flujo cero», «chkHideRange», «Nodos», «Pistas» | `tools/read_resources.py` sobre los recursos que REA inventarió | Evidencia de funciones y del gesto de panear (`izquierda + derecha`, botón central) |
| Cámara, rejilla, flechas, terreno, conteo, etapa | **Sin REA**: observación de la ventana real y análisis de los `.vsm` | Abajo |

## Hallazgos (todos medidos contra la ventana real)
| Qué | Resultado | Cómo se comprobó |
|---|---|---|
| Cámara | giro de la vista = giro guardado + **90°**; elevación sin corrección; campo de visión **≈45°** | Ajuste conjunto de giro/elevación/FOV con la forma de la mina en Blue_sky, CoalMine y Fire (solape 0,88/0,58/0,87 frente a 0,27–0,53 del azar). La calibración anterior (100° y 50°) estaba mal |
| Rejilla | `COORDINATES` = espaciado, centro X, **cota**, centro Y, tamaño X, tamaño de cota, tamaño Y. Rectángulo finito a esa cota (Blue_sky z=0 cortando la mina por el medio) | Coincide con la cota medida en Blue_sky (0) y CoalMine (1700 → 1720 medido). En Fire el archivo dice 2300 y la ventana real ≈2160: **sin explicar** |
| Colores | `GRAPHICS` col. 2 = cielo arriba, col. 3 = rejilla (abajo siempre casi negro) | Píxeles reales: Fire `#aec1db` (archivo `#b0c4de`), CoalMine `#6393ea` (`#6495ed`) |
| Etapa activa | `STATE` col. 79 | Blue_sky 3 = «Production», CoalMine 4 = «Year 5…» (ambas capturas) |
| Dato de color guardado | `STATE` col. 7 = 101 caudal, 102 velocidad, **613 tipo de aire**; col. 8 = dato del texto | CoalMine se ve coloreada por «Identificadores › Tipo de aire» |
| Conteo de galerías | No se cuentan las galerías «ficticias» de 0,01 m × 0,01 m (área 0,0001): Blue_sky 757 totales (78 ficticias, 9 en la etapa) → **522(757)**; CoalMine **3403(5146)** | Cifras exactas de las dos capturas |
| Tipos de aire | `AIRTYPES` = nombre y color ARGB; columna `Air Type` de cada galería; casillas de visibilidad | Lista y colores idénticos a «Exponer» real |
| Terreno sin textura | Color por **cota** con arco iris (bajo magenta/rojo → amarillo → verde → cian/azul), translúcido (~58 %) | Correlación tono/cota en 15.000 vértices proyectados |
| Flujo | **Flechas** (triángulos oscuros con degradado) que avanzan por las galerías en el sentido del caudal; tubos casi opacos | 6 cuadros de la demo de fuego: 7.000–8.000 píxeles cambian entre cuadros separados 250 ms y las flechas se desplazan |
| Zoom de la rueda | **×1,077 por muesca**, anclado al centro de la pantalla (no al cursor) | Área del terreno +15,9 % tras una muesca; el centroide se mueve igual con la rueda en el centro y en una esquina |
| Rotación con el botón izquierdo | **No medida**: los mensajes de ratón enviados a la ventana no la mueven y no se toma el cursor real del usuario | Se conserva 0,46°/px |

## Función del ratón en NVS tras esta fase
Rueda ×1,077 con suavizado (zoom fluido, ~100 ms), botón izquierdo = rotar, botón derecho / central / izquierda+derecha = panear (texto de Ventsim:
«pan (arrastre del centro o izquierda + derecha)»), flechas izquierda/derecha = vistas rápidas, doble clic = ajustar.

## Pendiente
Modo de color «Calor» (Fire), cota de la rejilla de Fire, rotación medida, tipo de letra y tamaños de las etiquetas, «Texturas de conductos».
