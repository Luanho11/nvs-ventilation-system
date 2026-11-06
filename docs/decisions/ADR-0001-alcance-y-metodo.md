# ADR-0001 · Alcance y método

**Fecha:** 2026-10-16 · **Estado:** vigente

## Decisión
- El objetivo es la reconstrucción funcional amplia de VentSim DESIGN 6.0.5.4 con equivalencia verificable; decidido por el usuario y no se reabre.
- Método: caja negra conductual. Se observan entradas/salidas (archivos de ejemplo del usuario, la aplicación en ejecución, documentación pública) y se implementan algoritmos propios.
- Sin descompilación, sin desempaquetado de recursos de los .DLL, sin elusión de protecciones. Las limitaciones de REA con los binarios están en docs/01 y no se repiten.

## Qué se observó de los binarios (y solo eso)
Metadatos estáticos de alto nivel (tipo de ensamblado, versión, referencias, P/Invoke declarados) con REA. No se leyó código.

## Consecuencias
- La matriz de cobertura se alimenta de las secciones/columnas de los archivos de proyecto (que enumeran las funciones del producto) y de experimentos.
- Las pruebas diferenciales usan resultados guardados en archivos; sus límites (versión que guardó, entradas fijas) se declaran en docs/05.
- Todo supuesto sin observación se marca (H5…).
