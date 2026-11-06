# E-002 · Interfaz de la aplicación de referencia (observada en captura)

Fuente: `ref\Captura de pantalla 2026-10-16 120303.png` (1365×767), aportada por el usuario: Ventsim DESIGN 6 con `blue_sky.vsm`
abierto («Example Metal Mine with Problems»), interfaz en español. Es evidencia **visual**; no se ha ejecutado VentSim en esta
sesión. Solo se registran elementos visibles; ninguna regla de cálculo se deduce de aquí.

## Estructura de la ventana
| Zona | Observación |
|---|---|
| Barra de título | Icono de la aplicación + «Ventsim DESIGN 6 - blue_sky.vsm  Example Metal Mine with Problems» |
| Menús | Archivo · Ver · Vistas guardadas · Correr · Nota · Ventlog · Configuración · Ventana · Ayuda (+ icono de ayuda) |
| Selector «Etapa» | Lista desplegable («Production») con candado y flechas anterior/siguiente |
| Mensajes / cámara / teclado | Botón «Mensajes» y dos iconos a la derecha de la fila de menús |
| Barra 1 | Nuevo, abrir, copiar/pegar, ventanas, prismáticos (buscar), película (animación), **reproducir** (con desplegable), lupa, mover |
| Barra 2 («qué se muestra») | Botón de paleta, combos «Flujo de aire» + «Cantidad», unidad `m³/s`, botón de enlace, **T** (texto), **A** (estilo de texto), segundo par de combos para el texto, estrella (favoritos), «Vistas guardadas: Por defecto» |
| Raíl izquierdo | Iconos verticales: sólido, malla, ajustar vista, tabla, círculo, cursor/selección (con desplegable), globo, serpentín, engranaje |
| Visor 3D | Fondo degradado (cielo azul-grisáceo claro arriba → suelo oscuro abajo) con línea de horizonte; **rejilla blanca** sobre el suelo en perspectiva; galerías como **tubos** con volumen coloreados por caudal en **bandas** (marino, azul, cian, verde, amarillo, rojo, magenta, rosa); etiquetas blancas grandes con contorno oscuro (a veces solapadas); cuadros azules con texto blanco («Decline max velocity 3.3 m/s», resultados de ventilador); recuadro explicativo azul abajo-izquierda; terreno/superficie 3D marrón escalonado; gizmo de ejes abajo-derecha (Y rojo, Z azul, X verde) |
| Panel flotante «Exponer» | Cabecera con título y cierre; deslizador de transparencia; pestañas con iconos (paleta, estilos, cubo, capas 1 y 2, globo, vista); «Cantidad m³/s»; **lista de umbrales editables** (250, 100, 50, 25, 10, 0.0) con deslizador vertical; «Opciones de»: 4 botones (ordenar ↓, ordenar, rueda de color, mosaico); **leyenda de bandas** con muestra de color + valor (> 250.0, 250.0, 100.0, 50.0, 25.0, 10.0, 0.0, < 0.0) y unidad |
| Barra de estado | Botones de reproducción (4) y pausa; campo «Coordenadas 1317.5 E 1459.8 N 84 Z»; «Estado»; «Compresible [Sí] : NVP [No]»; «Conductos de aire 522(757)»; iconos de vistas (cubo) y expandir; texto de modo «Mantenimiento» (color marrón) |

## Qué se adopta, qué se adapta y qué NO se copia
- **Se adopta el nivel de calidad y la funcionalidad visible**: tubos con volumen, color por bandas con umbrales editables, rejilla y horizonte, etiquetas con contorno, callouts, gizmo, panel flotante, barras de herramientas en dos filas, estado con coordenadas.
- **Se adapta**: diseño visual propio (paleta, iconos vectoriales dibujados aquí, tipografía Segoe UI, chrome claro + visor oscuro), nombres propios («Mapa de color», «Mostrar», «Origen»), solo controles que funcionan con el motor actual.
- **No se copia**: logotipo, iconos, textos de los modelos de ejemplo ni la identidad de marca. La aplicación se identifica como no oficial.

## Funciones vistas en la referencia que aún no existen en NVS (candidatas a la matriz)
Etapas · vistas guardadas · Ventlog/sensores · notas/anotaciones en el modelo · animación/película · superficie/terreno 3D y sólidos · pestañas de exposición (capas, estilos, vistas) · favoritos de exposición · conductos de aire (conteo en estado) · modo compresible/NVP en la barra · deslizador de transparencia · reproducción de simulación dinámica. Se han añadido a docs/03 (A14–A18, E11–E12).
