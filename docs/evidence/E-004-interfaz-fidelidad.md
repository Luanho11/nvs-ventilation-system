# E-004 · Fidelidad visual V0.2 (2026-10-16)

**Fuentes:** captura del usuario `ref/Captura de pantalla 2026-10-16 120303.png`, captura de ventana
`docs/evidence/img/ventsim-real-blue_sky.png` (solo ventana, `tools/observe_ventsim.ps1`), volcados MSAA ya registrados
(E-003) y el contenido de `Blue_sky.vsm` y los demás ejemplos (solo lectura). La ventana de Ventsim estaba minimizada: no
se restauró ni se tocó. REA no puede observar ventanas en Windows (L-06 en docs/01).

## Qué se observó y cómo se usó
| Elemento | Observación | Implementación |
|---|---|---|
| Aspecto general | Chrome clásico de Windows (`#f0f0f0`), Segoe UI 9 pt, botones planos, marcados con borde azul | `gui/theme.py` (estilo `windowsvista` + QSS mínimo) |
| Iconos | Planos con degradado y color por función; barra 1 = nuevo, abrir, copiar, pegar · ventanas, prismáticos, película▾, ▶▾, lupa, mover; raíl = cubo dorado, cubo malla, ajustar, tabla, esfera, triángulo▾, globo, «n» con flecha, engranaje | `gui/icons.py`: 60 SVG propios dibujados a mano (no se copia ningún recurso). Orden y significado ahora **cuadran con los nombres MSAA** (p. ej. fila 7 «Mostrar todo» = película, fila 8 = ▶, fila 9 «Enfocar» = lupa) |
| Barra de menús | Menús · `?` · «Etapa» + lista + candado + flechas · «Mensajes» · cámara · tarjeta | `MainWindow._build_corner` |
| Barra 2 | El botón enmarcado es el **segundo** («Administrador de datos y color»): es el que muestra «Exponer» | `ICONOS_BARRA2`, `act_palette` enlazado a la fila 1 |
| «Exponer» | Cabecera con cierre, deslizador de transparencia, 7 pestañas, 6 campos, deslizador vertical (marcador negro arriba, azul abajo), «Opciones de» (4 iconos), leyenda de 8 filas con valores en azul, unidad al pie | `gui/exponer_panel.py` |
| Escala de color | **Continua**: en la captura hay tubos naranja y tonos intermedios que no están en la leyenda; 127 m³/s es rojo y 225–237 m³/s es magenta (entre 100 y 250). Umbrales 0·10·25·50·100·250; «< 0» muy oscuro y «> 250» rosa | `ColorScale` con n umbrales y n+2 colores, modo continuo por defecto |
| Etiquetas | Blanco, ~15 px, contorno oscuro fino, **se solapan** | `viewport._paint_labels` (se eliminó la colocación sin solapes) |
| Gizmo | Abajo a la derecha, flechas 3D, **X verde, Y rojo, Z azul**, esfera clara en el origen | `viewport._paint_gizmo` |
| Barra de estado | 5 botones de reproducción azules · Coordenadas (blanco, negrita) · Estado · «Compresible [Si] : NVP [No]» · «Conductos de aire visibles(total)» · 6 iconos de modo de vista | `_build_status_bar`. «Mantenimiento» (estado de licencia) se omite |

## Datos de `.vsm` que alimentan la escena (`escena.py`)
- `REFERENCE`: caras de 4 vértices `x y z … capa u v`; si el 3.º y el 4.º coinciden es un triángulo (`Blue_sky`: 2454 + 2432 caras).
  `REFLAYERS`: textura JPEG en base64 troceada en celdas de 32 000 caracteres; la capa sin textura (zona de mineral) usa el
  naranja medido en la captura (`COLOR_CAPA_SIN_TEXTURA`, **estimado**).
- `MESSAGEBOX`: notas. Columna 6 = color ARGB (`-16760704` → `#004080`), 13 = texto (`/c/n` = salto de línea), 11 = anclada
  al modelo (columnas 1–3) o fija en pantalla (columnas 18–19 = fracción del visor), 4 = máscara de etapas. Los campos
  `<código:modo:clave>`: `101` = caudal y `316` = diámetro de la galería cuya **«Warning Key»** es `clave` (verificado con
  las galerías 22 y 2794 = 791 de Blue_sky: 127,7 m³/s y 4,5 m). `407` (coste) y `102` (máximo) **no están descifrados** → se muestran «—».
- `STAGES` = lista de etapas; `Stage` de cada galería = **máscara de bits** de las etapas en que existe (Blue_sky: 297 solo
  «Initial Development», 531 en «Production»). **Dónde se guarda la etapa activa no se ha encontrado**: se abre la última
  usada (coincide con «Production» en Blue_sky). La referencia muestra «522(757)»; aquí salen 531(835): **diferencia abierta**.
- `STATE` y `SAVEVIEWS`: cámara = objetivo (3), distancia, giro, elevación. `DESFASE_GIRO` = 100° y `FOV_GRADOS` = 50° se
  **calibraron visualmente** contra la captura (pozo arriba, rampa a la derecha); no son datos del archivo.

## Pendiente / no verificado
- La **pantalla de carga** no se ha observado nunca (la aplicación de referencia no se ha reiniciado): el diseño es propio.
- Funciones de los 4 iconos de «Opciones de», de la casilla bajo el deslizador y del deslizador de transparencia: **inferidas** del
  icono (restaurar, invertir, escala automática, transparencia de superficies); los tooltips lo dicen.
- Menús con 100+ elementos siguen «Pendiente» (deshabilitados). Notas con campos `102`/`407`, texturas de capas sin JPEG,
  transparencia del terreno por defecto (en `diamondmine` el terreno opaco oculta la red), nodos, pistas, visibilidad,
  reproducción dinámica y modos de vista de la barra de estado.
- Brillo y grosor de los tubos y rejilla: semejantes, no idénticos (la referencia usa DirectX).
