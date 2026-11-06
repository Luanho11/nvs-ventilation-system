# ADR-0003 · Visor 3D en GPU (OpenGL) con respaldo por software

**Fecha:** 2026-10-16 · **Estado:** vigente · **Sustituye** la decisión de render por software de ADR-0002.

## Contexto (medido)
El visor por software (QPainter, 3 pasadas por tubo) costaba **90–290 ms por fotograma** (3–11 fps) con 835–6.728 galerías.
La proyección era <1 ms; el coste estaba en el rasterizador de CPU (contorno + cuerpo + brillo con suavizado) y en
etiquetas/flechas en bucles de Python. El panel flotante no era el problema.

## Decisión
- Tubos como **malla 3D real** (8 caras, normales suaves; iluminación difusa + brillo especular + oscurecimiento de borde +
  niebla; buffer de profundidad; MSAA ×4), cielo y rejilla en shaders. Radio mínimo en píxeles calculado en el vertex shader.
- Etiquetas, flechas, callout, gizmo y chip siguen en QPainter **sobre** la escena, con las etiquetas/flechas en una **capa en
  caché** (se rehace solo si cambia cámara o datos) y omitidas mientras se mueve la cámara en modelos con >400 galerías.
- **Respaldo automático por software** si no hay contexto OpenGL/shaders (también `NVS_RENDER=software` y pruebas sin pantalla).
- Los shaders usan GLSL 1.20 (o ES 1.00 con precisión); formato por defecto con profundidad 24 bits y 4 muestras.

## Resultado medido (AMD Vega 8, 1365×740)
| Modelo (galerías) | Antes | Ahora |
|---|---|---|
| Blue_sky (835) | 100 ms | 4,1 ms |
| RealMine (1.342) | 90 ms | 4,1 ms |
| CoalMine (5.205) | 236 ms | 4,9 ms |
| diamondmine (6.728) | 289 ms | 5,5 ms |
Con sincronización vertical el visor va a 60 fps constantes.

## Consecuencias
- `QWidget.grab()` de la ventana no incluye las superposiciones QPainter de un QOpenGLWidget; las capturas deben hacerse del
  framebuffer o de la pantalla (la autoprueba del .exe ya lo hace). En pantalla real todo se ve bien.
- PySide6 falla (`OverflowError`) al pasar floats negativos con la sobrecarga genérica de `setUniformValue`: se usa `setUniformValue1f`.
- Prueba específica de GPU (`tests/test_gpu_render.py`, proceso aparte con pantalla real; se omite sin GPU).
