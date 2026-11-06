# E-005 · Notas, pistas, nodos, flujo animado y marca (V0.3, 2026-10-16)

Cada fila dice **de dónde sale** el dato y si intervino REA. Nada de esto se inventó: lo que no está observado se marca «inferido».

## Qué se hizo con REA y qué no
| Paso | Herramienta | Resultado |
|---|---|---|
| Inventario de recursos de idioma | **REA** `inspect_managed_artifact` + `inspect_analysis_view` sobre `es\VentsimNoteForms.resources.dll` (31) y `es\VentsimUI.resources.dll` (139) | Completo; evidencia `ev_4e991fbd…`, `ev_2503964e…` |
| Lectura de los textos de esos recursos | `tools/read_resources.py` (REA no decodifica el contenido de un `.resources`, ver U-01) | Textos de «Pistas», «Nodos», formularios |
| Intento de leer la lógica en `VentsimUI.DLL` | **REA** `open_binary`, `binary_overview`, `search_strings`, `inspect_managed_members` | **Falla** (L-07, L-08): sin proveedor para .NET en Windows y metadatos fuera de presupuesto. No se eluden protecciones |
| Observación de la aplicación en ejecución | `tools/observe_ventsim.ps1` (MSAA/PrintWindow, solo la ventana) | Ventsim se abrió, cargó `blue_sky.vsm` (Archivo › Cargar demostración › Mina de metal) y se cerró antes de capturar el movimiento del flujo: **el flujo animado NO está observado en movimiento** |
| Pantalla de carga | Captura entregada por el usuario `ref/loader-ventsim.png` (518×388) | Disposición y colores copiados; logotipos entregados por Noova |

## Pistas (rail «Pistas»)
- **Recursos (REA/U-01):** formulario de «pistas de actividad»: «Agregar pista», «Seleccione arranque», «Ir a empezar» (la pista empieza en el conducto no conectado más cercano), «Despejar la pista», «Crea una gráfica de variables a lo largo de la pista», «Efecto pistón», «Bi-direccional», unidades por hora, vehículos/calor.
- **Datos (`.vsm`, sección `TRACKS`):** tres filas por pista: cabecera (nombre, color ARGB en la columna 4: `-65536` = rojo), vehículo (`Truck AD55`) y lista de GUID de galerías. Blue_sky: «Decline Path», 131 galerías.
- **Implementado:** el botón resalta las galerías de la pista con su color. **Inferido:** el aspecto del resalte (tubo opaco algo más grueso). No implementado: formulario de edición, vehículos, efecto pistón, gráfica.

## Nodos (rail «Nodos»)
- **Recursos (REA/U-01):** «Nodos» (menú), «Tamaño de nodo» (barra de imagen), «Texto de entrada / salida del nodo».
- **Implementado:** punto blanco con borde oscuro en cada extremo de galería. **Inferido:** el aspecto. No implementado: tamaño de nodo, texto de entrada/salida.

## Campos de las notas (`MESSAGEBOX`)
- Estructura (leída de los datos): tras el GUID de la nota, columna 26 = n.º de campos, 2 columnas por campo (código, modo), n.º de galerías y sus GUID.
- **101** caudal, **102** velocidad (`|Q|/área`), **316** diámetro: confirmados con los umbrales de la tabla `COLORS` (la clave 102 trae umbrales de velocidad) y con la lista de «Flujo de aire» observada en el combo.
- **407** coste anual de la potencia del ventilador = `Fan Power` [kW] × 8760 h × precio [$/kWh] ÷ eficiencia. Verificado numéricamente contra la captura de la referencia: **195 605 $/año** y **166 323 $/año** (precio 0,1 = `AIRSIM` col. 8; eficiencia 95 % = col. 12; moneda = `OTHER` col. 21). El texto «/yr» se muestra en inglés como en la referencia.
- Modo `Maximum` sin clave: máximo sobre las galerías de la nota. «Decline max velocity: **3.3 m/s**» coincide con la referencia.
- Pendiente: otros modos (mínimo, media, suma) no vistos en ningún ejemplo → «—».

## Flujo animado y tubos translúcidos
- **Origen:** petición del usuario («el ducto está tieso… no es medio invisible») y la captura estática de la referencia. **No hay observación del movimiento real** (L-06 y Ventsim cerrado): el diseño es inferido.
- **Implementado (GPU):** tubos con transparencia (centro 78 %, bordes opacos); bandas brillantes que recorren el tubo en el sentido del caudal, a velocidad ∝ velocidad del aire (recortada a 1–12 m/s para que siempre se vea); el botón «Flechas» lo activa/desactiva. En el respaldo por software se conservan las flechas estáticas.
- **Verificado:** prueba `test_gpu_path`: dos fotogramas con 0,4 s de diferencia difieren con flujo y son idénticos sin él.

## Marca
Logotipos entregados en `ref/` (`noova-software.png` = icono y esquina de la pantalla de carga; `logo-loader-blanco.png` = pantalla de carga; `Logo-base.png` = «Acerca de»). `tools/hacer_logos.py` solo reduce tamaños y crea el `.ico`; no vectoriza ni redibuja.
