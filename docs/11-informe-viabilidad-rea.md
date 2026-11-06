# Informe breve de viabilidad usando REA (2026-10-16)

Los porcentajes son **estimaciones**, no mediciones.

## Qué da REA (y qué no)
| Área | Fuente | Similitud alcanzable (estimada) |
|---|---|---|
| Interfaz (menús, barras, orden de botones, textos, diálogos, colores, geometría) | Recursos satélite `es\` (139 recursos de UI), MSAA, capturas de ventana | **85–95 %** |
| Formato `.vsm` y datos | Ejemplos + análisis del formato (ya verificado) | **90 %** lectura; escritura solo tras validar |
| Física de ventilación (resistencias, ventiladores, redes) | Oráculo de archivos guardados + experimentos de caja negra | **70–85 %** (ya contrastada en 4 modelos) |
| Termodinámica, fuego, conductos, contaminantes, simulación dinámica | Solo experimentos de caja negra | **20–50 %** |
| Render 3D equivalente (sólidos, texturas, DirectX) | Capturas + imitación visual | **60–75 %** (visual, no idéntico) |
| Código interno de VentSim | **No disponible**: los ensamblados principales están protegidos (recursos opacos, metadatos corruptos) y no se van a eludir | 0 % por esa vía |

**Global estimado: ~65–75 % de similitud observable a largo plazo; ~30–40 % hoy.** Lo que falta no es de interfaz sino de algoritmos protegidos.

## Respuestas
- ¿VentSim es Python? No: .NET 4.7.2 x86 (WinForms/DevExpress/DirectX).
- ¿Por qué no se usa el código del ejecutable? Está protegido; REA no lo abre y no se hará.
- ¿Hace falta una versión antigua? No para la interfaz; solo serviría como evidencia adicional de comportamiento.
- Error mío: iconos y funciones de la V0.1 fueron inventados. Se corrige con `ui_spec.json`.

## Pendiente
1. ~~Arreglar `tools/build_ui_spec.py`~~ — hecho (menús, barras, raíl, estado y combos salen correctos; también escribe la copia empaquetada).
2. ~~Reconstruir la ventana principal desde `ui_spec.json`~~ — hecho en lo estructural (ver `docs/evidence/E-003`). Faltan: Etapa/Mensajes
   reales, panel «Exponer» con sus pestañas, deslizador de transparencia y umbrales (6 campos), y el resto de elementos «pendiente».
3. Calibrar la semántica de bandas de color con blue_sky.vsm: en la referencia hay 6 umbrales y 8 colores (> máx, cada umbral, < mín);
   `ColorScale` usa n umbrales y n+1 colores. Hoy solo se adoptaron los colores observados.
4. ~~Reconstruir exe y pruebas~~ — hecho (ver estado de la compilación en `build.ps1`).
5. Cerrar VentSim (PID 11712) cuando ya no se necesite para observar: no se ha cerrado por si hay trabajo abierto.
