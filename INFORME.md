# Informe de estado · NVS (Noova Ventilation System) 0.3.1 · 16-oct-2026

## Qué es hoy
Un programa de escritorio para Windows que **abre los modelos de mina de Ventsim, los muestra en 3D como Ventsim y calcula cuánto aire pasa por cada galería**.
Arranca con la pantalla de carga de Noova y se queda **vacío, con la rejilla, como Ventsim recién abierto**; el ejemplo se carga desde
Archivo › Cargar demostración. Está en `dist\NVS\NVS.exe`.

## Lo que se corrigió en esta versión
- **El fallo del panel «Exponer»** (alertas sin fin al tocar el medidor de la derecha): el panel reconstruía sus campos en cada movimiento del ratón.
  Ahora se actualiza en sitio, agrupa los cambios y hay un filtro que, si algo falla, lo anota en un archivo y muestra **una sola** alerta.
  Hay pruebas automáticas que reproducen el caso.
- **La computadora se ponía lenta**: la animación ya no corre si la ventana está en segundo plano o minimizada, y mis pruebas pesadas se acabaron.
- **Se miró Ventsim abierto** (sin tocar nada tuyo salvo cargar ejemplos desde su menú) y se corrigió lo que estaba mal:
  - **La rejilla** estaba abajo del modelo; en Ventsim es un rectángulo finito a una altura que guarda el archivo (en Blue_sky corta la mina por el medio).
  - **El aire no se ve como una banda sino con flechitas** oscuras que avanzan en el sentido del caudal; ya es así.
  - **La cámara** estaba mal calibrada: ahora Blue_sky, CoalMine y Fire se ven desde el mismo ángulo y encuadre que en Ventsim.
  - **CoalMine** estaba «totalmente diferente»: abre en la etapa «Year 5», coloreada por tipo de aire con su lista de colores y casillas, con el terreno
    translúcido en arco iris por altura, la rejilla gris oscura y el cielo azul del archivo. El contador marca **3403(5146)** como Ventsim.
  - En Blue_sky el contador ahora marca **522(757)**, igual que Ventsim (no cuenta las galerías «ficticias» de enlace).
- **Ratón**: la rueda acerca ×1,077 por muesca (medido en Ventsim) con zoom fluido; panear con botón central, derecho o **izquierda + derecha**
  (como dice Ventsim); flechas izquierda/derecha recorren «Vistas rápidas».
- **Más botones y menús activos**: de 19 a **30 de 115 elementos de menú** (Ocultar Flujo Cero, Vistas rápidas, Alejar, Cerrar, Mostrar todas las capas,
  Establecer centro…), el botón **Visibilidad** del raíl, las pestañas de «Exponer» **Tipo de aire, Capa primaria y Referencias** con sus casillas, y la casilla
  «Ocultar datos por debajo de la barra deslizante».

## Lo que ya hace
- Abre los 23 modelos de ejemplo (solo lectura): terreno, notas con sus cifras, etapas, vistas guardadas, rejilla, cielo y modo de color guardados.
- Colorea por caudal, velocidad o tipo de aire; tubos con aire animado; nodos y pistas.
- Calcula el aire de la red: **coincide con Ventsim en 4 de los modelos** comprobados a fondo. Compara «archivo» contra «motor» y exporta a Excel (CSV).

## Lo que falta (sin tecnicismos)
1. **Casi todo el cálculo avanzado**: calor y temperatura, gases, humo y fuego, polvo, radón, simulación en el tiempo, ductos y ventilación natural.
   Por eso la «Demo de fuego» se ve en NVS con los colores del caudal y no con los de temperatura como en Ventsim.
2. **Editar el modelo** y guardarlo en el formato de Ventsim (por seguridad solo se lee).
3. **85 de los 115 elementos de menú** siguen apagados («Pendiente»), más informes, impresión e importar planos.
4. **Ratón**: la rueda y el panear están medidos o documentados; **la velocidad de giro con el botón izquierdo no se pudo medir** sin tomar tu cursor.
5. **Rejilla de la demo de fuego**: en Ventsim real está unos 140 m más abajo de lo que dice el archivo; no sabemos por qué.
6. **Comprobación numérica**: en 19 de los 23 modelos el resultado puede diferir de Ventsim; el programa lo avisa.

## Porcentajes (estimaciones honestas, no mediciones exactas)
| Pregunta | Porcentaje | De dónde sale |
|---|---|---|
| **¿Cuánto de Ventsim está replicado?** (todo lo que sabe hacer) | **≈ 15 %** | 1 de 12 módulos de simulación; 30 de 115 menús; 8 de 9 botones del lado izquierdo; visor 3D, terreno, notas, etapas, rejilla y capas bastante avanzados |
| **¿Cuánto se parece por fuera?** (lo que ves al abrir un ejemplo) | **≈ 88 %** | Comparación lado a lado con Blue_sky, CoalMine y Fire reales: mismo encuadre, rejilla, cielo, terreno, leyendas, contadores y flechas. Falta el modo «Calor», tipografías y los iconos son nuestros |
| ¿Cuánto se parece al usarlo con el ratón? | **≈ 60 %** | Rueda y panear medidos; giro sin medir; menús y botones aún apagados |
| **¿Cuánto del cálculo de aire coincide con Ventsim?** | **4 modelos de 23 comprobados a fondo** (error < 0,001) | Pruebas automáticas contra los archivos guardados por Ventsim |

## Cómo se trabajó con REA (sin adornos)
- **Con REA**: inventario de los recursos de idioma de Ventsim (de ahí salen los textos de Pistas, Nodos, Visibilidad, el panear con izquierda+derecha y «Ocultar datos
  por debajo de la barra deslizante»). También se intentó leer el motor gráfico (`ChasmGraphics.DLL`): sus recursos son código cifrado por un protector;
  **no se abre** y queda registrado (`docs/01`, L-09).
- **Sin REA** (porque REA no puede hacerlo en Windows): ver la ventana abierta de Ventsim y compararla con NVS; eso se hizo con capturas de **solo esa ventana**.
- **De los archivos de Ventsim** (reconstrucción real): rejilla, cielo, etapa activa, modo de color, tipos de aire, capas, conteos y estado guardado.
- Detalle y cifras de cada hallazgo: `docs\evidence\E-006-camara-rejilla-flechas-terreno.md`. Reglas fijas: `instructions.md`.

## Lo que sigue (propuesta)
1. Que me dejes mover **tú** el visor de Ventsim 10 segundos mientras lo capturo, para medir el giro del ratón.
2. Modo de color «Calor» (Fire) y el módulo de calor.
3. Activar el resto de menús que ya tienen datos (Nota, Ventlog, Configuración) y «Texturas de conductos».

## Dónde está todo
`dist\NVS\NVS.exe` · `dist\NVS-0.3.1-win64.zip` · `LEEME.txt` · `instructions.md` · `docs\img\ui-v03-*.png` · `docs\12-python-o-no.md` · `docs\evidence\E-005…` y `E-006…`.
