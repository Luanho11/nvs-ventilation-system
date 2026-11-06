# Observaciones que faltan y experimentos reproducibles (requieren VentSim en ejecución)

**Estado:** no se ha ejecutado VentSim en esta sesión. Nada de lo siguiente se ha observado todavía. Las herramientas
disponibles (REA estático + shell) no controlan la interfaz gráfica de VentSim. Si se dispone de automatización de
escritorio autorizada se podrán ejecutar; si no, los realiza una persona y anota los valores en las plantillas.

## Qué falta observar y por qué los archivos no lo dan
| Observación | Para qué | Por qué los .vsm no bastan |
|---|---|---|
| Menús, cuadros de diálogo y opciones (todas las pestañas de preferencias y simulación) | Inventario completo de funciones (matriz de cobertura) | Los archivos solo guardan los valores, no los controles ni sus rangos/validaciones |
| Valores predeterminados de cada propiedad al crear galerías, ventiladores, etc. | Defaults y validaciones | Idem |
| Rangos y mensajes de error ante entradas inválidas | Casos límite | Idem |
| Resultados para entradas arbitrarias (no las guardadas en ejemplos) | Pruebas diferenciales más allá de 13 modelos | Los ejemplos tienen solo un conjunto de resultados cada uno |
| Informes, exportaciones (CSV, DXF, imágenes, PDF), importaciones | Interoperabilidad | |
| Simulaciones dinámicas (gas, DPM, fuego, humo, voladura) resultados en el tiempo | Verificar C09–C14 | Los archivos guardan el estado final, no la serie temporal |

## Plantilla de experimento (una por prueba)
```
ID:                     EXP-<área>-<nn>
Versión:                VentSim DESIGN 6.0.5.4 (confirmar en Ayuda › Acerca de)
Objetivo:               qué función/regla se quiere medir
Preparación:            archivo base (ruta) o pasos para crear el modelo desde cero
Pasos:                  1… (clics/atajos exactos)
Entradas:               valores exactos + unidades
Salidas observadas:     valores exactos (copiar todos los decimales que muestre; indicar la pantalla)
Guardado:               nombre del .vsm resultante (se podrá leer con vsmio) 
Fecha / quién:
```

## Primeros experimentos propuestos (en orden de dependencia)
1. **EXP-NET-01 — red mínima de 3 galerías con un ventilador.** Crear 3 galerías en serie (L=100 m, 5×4 m, k=0,01, sin choques), una boca de entrada y otra de salida, un ventilador de curva conocida. Anotar Q, ΔP por galería, presiones de nodo, potencia. Guardar el .vsm. Sirve para fijar: referencia de presión de bocas, tratamiento de la presión dinámica de salida (B09), unidades por defecto.
2. **EXP-RES-01 — variar un parámetro por vez** (k, L, Le/shock, forma de la sección) y leer la resistencia mostrada. Confirma `R=(k(L+Le)P/A³)·ρ/1,2` para formas distintas (el perímetro depende del tipo de sección: circular, rectangular, arco…; los archivos guardan `Shape Type`/`shapepresetindex` y habrá que comprobar cómo se calcula P a partir de ancho, alto y forma).
3. **EXP-DEN-01 — cambiar la densidad del aire** (AIRSIM[13]) y la altitud; observar R y Q.
4. **EXP-FAN-02 — velocidad ≠ 100 %, ventiladores en serie (Fan Config), inversión.**
5. **EXP-NVP-01 — ventilación natural** con dos bocas a distinta cota y temperaturas conocidas.
6. **EXP-RT-01 — tipos de resistencia** (puerta, regulador, tapón, resistencia personalizada) para descifrar `Resistance Type` negativo.
7. Recorrer **todos los menús** documentando comandos y diálogos (para completar la matriz de cobertura).

## Qué NO se hará
- No se extraerán ni descifrarán recursos o código de los .DLL/.exe; no se instrumentará la memoria del proceso.
- No se tocará la instalación; los archivos de experimento se crean en `experiments/`.
