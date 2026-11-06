# Diseño de la interfaz (V0.3) — especificación y estado

Objetivo: parecerse a Ventsim DESIGN 6 lo más posible **de forma observable** (aspecto, iconos, disposición, ejemplo cargado,
pantalla de carga), sin copiar sus recursos. Evidencia y decisiones: `docs/evidence/E-004-interfaz-fidelidad.md` (V0.2) y `E-005-notas-pistas-nodos-flujo.md` (V0.3).
Capturas generadas por la propia aplicación: `docs/img/ui-v03-bluesky.png` (comparar con `ref/` y
`docs/evidence/img/ventsim-real-blue_sky.png`), `docs/img/ui-v03-splash.png` (comparar con `ref/loader-ventsim.png`).

## Rendimiento (revisión V0.1.2, medido; la ruta de dibujo no cambió salvo las superficies)
| Qué | Antes | Ahora |
|---|---|---|
| Fotograma del visor, girando (835–6.728 galerías) | 90–290 ms (3–11 fps) | **4–5,5 ms** (≈200–240 fps; 60 fps con vsync) |
| Carga de diamondmine (1,1 M de líneas) | ≈ 9 s | ≈ 4 s con 800 000 vértices de terreno (la prueba de GPU limita 6.000 galerías a < 16 ms) |
| Cálculo de diamondmine (6.728 galerías) | 35 s, **no convergía** | **1,0 s**, converge (62 it.) |
Causas y arreglos: malla 3D en GPU (ADR-0003); lector perezoso de secciones; solución exacta vectorizada por ventilador;
las superficies de referencia se leen en bloque con `numpy.loadtxt` (un lector por filas tardaba 15 s en diamondmine).

## Sistema visual
| Elemento | Diseño |
|---|---|
| Chrome | Clásico de Windows: `#f0f0f0`, Segoe UI 9 pt, estilo `windowsvista`, botones planos (hover celeste, marcado con borde azul `#2e8bd8`), campos blancos con borde gris |
| Iconos | 60 SVG propios (32×32) con degradado y color por función; deshabilitados = misma imagen al 72 % (no se pierde el aspecto de la referencia) |
| Visor 3D | GPU (OpenGL), fondo degradado azul → negro, rejilla en perspectiva, tubos de 8 caras con luz, **superficies de referencia con textura**, etiquetas blancas con contorno que se solapan, **notas** (fijas en pantalla o ancladas al modelo), gizmo con flechas 3D (X verde, Y rojo, Z azul); respaldo por software sin superficies |
| Color | Escala continua de 6 umbrales y 8 colores (`#000040 #000080 #00ffff #00ff00 #ffff00 #ff0000 #e400e4 #ff96ff`), modo por bandas opcional |
| Cámara | Se abre con la cámara guardada del proyecto (`STATE`); «Vistas guardadas» mueve a las de `SAVEVIEWS`; teclas 1–4 y Home |
| Pantalla de carga | Disposición de `ref/loader-ventsim.png` (518×388, fondo pizarra, logotipo a la izquierda, título y datos a la derecha, versión y créditos abajo) con los logotipos de Noova y barra de progreso real |
| Tubos | Casi opacos con **flechas** (triángulos oscuros con degradado) que avanzan en el sentido del caudal, a velocidad ∝ velocidad del aire (GPU; observado en la demo de fuego real, E-006) |
| Rejilla, cielo, terreno | Rejilla finita a la cota de `COORDINATES`; cielo y color de rejilla de `GRAPHICS`; terreno sin textura coloreado por cota en arco iris y translúcido (E-006) |
| Nodos / Pistas | Puntos en los extremos de galería / resalte de la ruta guardada en `TRACKS` con su color |

## Estructura de la ventana
- **Título:** «NVS 0.3.1  - archivo.vsm   descripción del proyecto». Sin proyecto: visor vacío con rejilla, «Coordenadas 500.0 E 500.0 N 0 Z», sin «Exponer».
- **Menús (especificación MSAA):** Archivo · Ver · Vistas guardadas · Correr · Nota · Ventlog · Configuración · Ventana · Ayuda ·
  «NVS» (propio). Esquina: `?` · Etapa (lista, candado, anterior/siguiente) · Mensajes · imagen · tarjeta.
- **Barra 1** (11 elementos), **barra 2** (16, con las listas observadas) y **raíl** (9) construidos desde `ui_spec.json`.
- **Visor:** «Exponer» arrastrable (arriba a la derecha), notas, gizmo; sin botones superpuestos.
- **Estado:** reproducción ×5 · Coordenadas · Estado · Compresible/NVP · Conductos de aire `visibles(total)` · mensaje ·
  validez del modelo y render (propios) · 6 modos de vista.
- **Paneles acoplables propios** (ocultos por defecto, menú «NVS»): Resultados por galería y Galería seleccionada.

## Funciones enlazadas (el resto: deshabilitado con tooltip «Pendiente»)
Archivo: ABRIR, Cargar demostración (6 ejemplos + «Otros ejemplos»), Salir · Ver: Todos los aptos, Mostrar todo, Restablecer la
Pantalla, Barras de herramientas, Copiar al portapapeles, Crear imagen · Vistas guardadas: Plan, Isométrica · Correr: Escritura de
la estática, Resumen · Ayuda: Sobre · Barra 1: Nuevo, Abrir, Encontrar, Mostrar todo, Ejecutar, Panear vista · Raíl: Sólidos,
Todos los aptos, Cuadrícula, Nodos, Flechas, Referencias, Pistas · Barra 2: Administrador de datos y color (Exponer), T, combos
Flujo de aire/Cantidad/Velocidad, Vistas guardadas · Esquina: Etapa (filtra por máscara de bits), Mensajes, imagen.

## Verificación
- **64 pruebas pasan** (incluye notas con coste y máximo, pistas, flujo animado, escena de Blue_sky, etapas, vistas, escala de 8 colores, panel «Exponer», ruta GPU con
  superficie y nota). `pyflakes` sin avisos en `src`.
- Capturas a 1360×725 revisadas visualmente frente a la referencia tras cada cambio.

## Brechas respecto a la referencia (honestas)
| Brecha | Estado |
|---|---|
| Pantalla de carga idéntica | Disposición y colores copiados de la captura entregada; tipografía y textos propios |
| «522(757)» frente a 531(835), etapa activa guardada | Sin descifrar (E-004). Las notas 102/407 ya están resueltas (E-005) |
| Transparencia del terreno, texturas sin JPEG, sólidos con color propio | Terreno opaco; colores por capa sin descifrar |
| Visibilidad, Texturas de conductos, reproducción dinámica, modos de vista; edición de pistas, tamaño y texto de nodos | Pendientes (iconos presentes, deshabilitados). Nodos y Pistas funcionan en su versión básica |
| Menús (≈100 elementos), Nota, Ventlog, Configuración | Pendientes |
| Brillo/grosor de tubos, rejilla, texto sobre el visor | Semejantes, no idénticos (DirectX en la referencia) |
| HiDPI > 150 %, accesibilidad, idiomas distintos del español | No auditado |
| Interacción manual del usuario con el .exe | No probada por una persona; sí eventos sintéticos y capturas |
