# E-003 · Interfaz construida desde `ui_spec.json` (2026-10-16)

**Fuentes:** volcados MSAA de la app real (`docs/evidence/raw/msaa_*.txt`, `observe_ventsim.ps1`) → `tools/build_ui_spec.py` →
`docs/evidence/ui_spec.json` (copia empaquetada: `src/nvs/data/ui_spec.json`, la misma que escribe el script; una
prueba comprueba que no divergen) + captura de ventana `docs/evidence/img/ventsim-real-blue_sky.png` (solo ventana).
**Código:** `src/nvs/gui/chrome.py` (constructor genérico) y `main_window._build_actions_and_bars` (enlaces).

## Qué sale de la especificación (no escrito a mano)
Menús Archivo · Ver · Vistas guardadas · Correr · Nota · Ventlog · Configuración · Ventana · Ayuda con sus submenús, separadores y
casillas; barra 1 (11 filas); barra 2 (16 filas, ordenadas por posición, con el ancho observado y las listas de los combos);
raíl de 9 botones; barra de estado (reproducción ×5 · Coordenadas · Estado · Compresible/NVP · Conductos de aire · vistas ×5);
fondo del visor `#6394e5 → #010203`; colores de «Exponer» (`#000040 #000080 #00ffff #00ff00 #ffff00 #ff0000 #e400e4 #ff96ff`);
chrome `#f0f0f0`.

## Estado de funcionamiento (hoy)
Elementos de menú de la referencia: **116** (11 con función, 105 «pendiente» = deshabilitados con tooltip).
Con función: Archivo › ABRIR, Otros ejemplos (lista de `.vsm`), Salir · Ver › Todos los aptos, Barras de herramientas, Copiar al
portapapeles, Crear imagen · Vistas guardadas › Plan, Isométrica · Correr › Escritura de la estática, Resumen · Ayuda › Sobre.
Barra 1: Nuevo, Abrir, ▶ (ejecutar). Raíl: Sólidos, Todos los aptos, Cuadrícula, Flechas. Barra 2: botón de «Exponer», «T»
(texto), combos Flujo de aire/Cantidad/Velocidad. El resto, deshabilitado.

## Correspondencias con interpretación (revisables; ninguna es dato observado salvo el nombre)
| Elemento (nombre MSAA) | Se enlaza a | Por qué / duda |
|---|---|---|
| Archivo › ABRIR | diálogo de abrir | nombre en mayúsculas tal cual lo vuelca MSAA |
| Correr › Escritura de la estática | solucionador F5 | traducción automática de «run steady-state»; la dinámica es otro elemento |
| Vistas guardadas › Plan / Isométrica | vista planta / isométrica | «Sección del Eje X/Y» NO se enlaza: no se sabe a qué cámara equivalen |
| Raíl › Sólidos / Cuadrícula / Flechas / Todos los aptos | tubos / rejilla / flechas / ajustar vista | por nombre; Nodos, Texturas, Referencias, Pistas, Visibilidad quedan pendientes |
| Barra 1, fila 8 (sin nombre, 43 px) | ejecutar | por el icono ▶ de la captura; el nombre no se observó |
| Barra 1, fila 7 «Mostrar todo» (40 px) | pendiente | en la captura esa posición muestra el icono de película; el nombre MSAA y el icono no cuadran |

## Iconos
Dibujados en este proyecto (`gui/icons.py`), NO tomados de VentSim. Se eligieron por posición/significado visible en la captura:
barra 1 = nuevo, abrir, copiar, pegar | ventanas, prismáticos, película, ▶, lupa, mover; raíl = cubo, malla, ajustar, tabla,
círculo, cursor, globo, «n con flechas», engranaje. Los botones sin nombre observado muestran «Botón sin nombre observado».

**Actualización V0.2 (E-004):** estos iconos se sustituyeron por un set nuevo con el estilo de la referencia y la
correspondencia de la barra 1 se corrigió: fila 7 «Mostrar todo» = película▾, fila 8 = ▶▾ (ejecutar), fila 9 «Enfocar» =
lupa, fila 10 = mover; el botón enmarcado de la barra 2 es la fila 1 («Administrador de datos y color»).

## Omitido a propósito
- «Mantenimiento» (barra de estado): estado de licencia de VentSim, no aplicable a esta app.
- Esquina del menú: «Etapa» (combo) y «Mensajes» están en la captura pero no en los volcados; se muestran deshabilitados.
- Los 4 menús sin nombre al final del volcado se descartan (ruido del árbol MSAA).

## Añadido que NO está en la referencia
Un único menú final, **«NVS»**, con lo propio: proyecto nativo, exportar CSV/imagen, origen del dato (archivo/motor),
magnitudes propias (pérdida de presión, diferencia motor − archivo), texto de etiquetas, grosor, paneles Tabla y Propiedades
(ocultos por defecto; en la referencia no hay paneles acoplados). Si se prefiere, puede eliminarse y dejar solo lo observado.
