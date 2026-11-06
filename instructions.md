# Instrucciones permanentes del proyecto NVS (Noova Ventilation System)

Leer SIEMPRE antes de trabajar. Mandan sobre cualquier costumbre por defecto.

## 1. Regla madre: SIEMPRE con REA, RECONSTRUIR, nunca construir desde cero
NVS no se escribe «desde la imaginación». Se **reconstruye** a partir de lo que la aplicación de referencia (Ventsim DESIGN 6) deja
ver: sus archivos binarios y de recursos, sus archivos de datos (`.vsm`), su interfaz en ejecución y las capturas que da el usuario.
Construir desde cero tomaría años, tiempo y tokens; no es el método.

1. **Antes de tocar código**, abrir las herramientas de REA (`rea-local`; cargarlas con ToolSearch) y consultar la evidencia del rasgo
   que se va a reproducir: `inspect_managed_artifact`, `inspect_analysis_view`, `inspect_pe_resources`, `inspect_managed_members`,
   `open_binary`, `search_strings`, `trace_feature`, etc.
2. **Decir en cada paso si se usa REA.** Cada mensaje de trabajo empieza con «REA: <herramienta> para <objetivo>» o
   «Sin REA: <motivo>». No se agrupan pasos para ocultar que uno no usó REA. Pedido expreso del usuario.
3. **Registrar** cada uso, éxito o fallo de REA: éxitos en `docs/evidence/E-xxx`, fallos con el error exacto en `docs/01-limitaciones-rea.md`.
   No se rellena un hueco de REA con suposiciones: se marca «inferido» o «pendiente».
4. Si algo no está observado, **no se dibuja ni se inventa**: se muestra deshabilitado con el tooltip «Pendiente».

## 2. Fuentes de evidencia (de más a menos fiable)
- Archivos `.vsm` de ejemplo (datos reales; formato descifrado, ver `docs/evidence/E-001`).
- Recursos de los ensamblados satélite `es\*.resources.dll` (textos, nombres de controles, formularios): REA inventaría, `tools/read_resources.py` lee el texto.
- Accesibilidad MSAA y captura de la **ventana** de Ventsim abierta (`tools/observe_ventsim.ps1`); nunca el escritorio completo.
- Capturas y logotipos que deja el usuario en `ref/`.
- Experimentos de caja negra comparados con los ejemplos; física de ventilación publicada.

## 3. Límites firmes (no negociables)
- Los ensamblados principales de Ventsim (`VVentsim.exe`, `VentsimUI.DLL`, `Chasm*.DLL`) están protegidos: REA no admite sus metadatos
  y no hay proveedor profundo para .NET en Windows (L-01, L-07, L-08). **No se eluden protecciones, no se desempaqueta, no se vuelca memoria,
  no se modifica la instalación de Ventsim.** Si aparece una herramienta REA que lo admita legítimamente, se usa y se registra.
- No se escribe `.vsm` sin verificar. No se afirma paridad sin prueba diferencial (`docs/05`).
- Los iconos son propios dibujados con el estilo observado; los logotipos son solo los entregados por Noova (`ref/`), sin vectorizar ni redibujar.

## 4. Método de trabajo
- Interfaz dirigida por datos: la UI sale de `docs/evidence/ui_spec.json` (`tools/build_ui_spec.py`), no de listas escritas a mano.
- Rendimiento medido antes de afirmar (visor GPU, análisis perezoso).
- Código limpio (skill `codigo-limpio`): simple, nombres en español, sin código muerto ni comentarios decorativos; pasar `pyflakes` y `pytest`.
- Compilar con `build.ps1` (ejecuta pruebas, compila, autoprueba el .exe).
- Responder al usuario en español, sin adornos, con lo hecho, lo que falla y lo que falta.

## 5. Estado y mapa
- Producto: **NVS** = Noova Ventilation System. Carpeta: `VentSim-Alternativa`. Código en `src/nvs`.
- Estado, porcentajes y pendientes en lenguaje llano: `INFORME.md`. Decisión de lenguaje: `docs/12-python-o-no.md`.
- Evidencias: `docs/evidence/E-001 … E-005`. Limitaciones de REA: `docs/01-limitaciones-rea.md`.
