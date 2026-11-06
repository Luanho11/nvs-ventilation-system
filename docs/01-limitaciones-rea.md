# Registro de limitaciones de REA (no repetir sin evidencia o herramienta nueva)

Servidor: `rea-local` (rea-agents 6.5.0, clon `C:\Users\Hostos\Desktop\rea`). Fecha: 2026-10-16.

| ID | Operación | Objetivo | Resultado | Reintentar solo si... |
|---|---|---|---|---|
| L-01 | `inspect_managed_members` (summary) | `VentsimUI.DLL` | `CLI metadata could not be admitted` (metadatos > presupuesto de 64 MiB de representación y anómalos) | Cambia la versión de REA o aparece un parser de metadatos tolerante |
| L-02 | `inspect_managed_artifact` (summary) | `VVentsim.exe`, `VentsimUI.DLL`, `ChasmCommon.DLL`, `ChasmGraphics.DLL` | Funciona pero cobertura **parcial**: tablas Module/Assembly con 2 filas, streams `#Blop`/`#GUlD`, índices de heap fuera de rango | Idem |
| L-03 | `inspect_managed_native_boundaries` | `VVentsim.exe` | Funciona, parcial. 11 P/Invoke con nombres aleatorios (VirtualAlloc, VirtualProtect, LoadLibrary, GetProcAddress, WriteProcessMemory, ReadProcessMemory, OpenProcess, FindResource, RtlZeroMemory, CloseHandle) | Idem |
| L-04 | `open_binary` / familia de procedimientos | cualquier binario | **No intentado**: Ghidra (`GHIDRA_INSTALL_DIR`), IDA (`REA_IDA_MCP_CONFIG`), Kuna (`REA_KUNA_COMMAND`) sin configurar; Hopper no soportado en win32 | Se configure un proveedor |
| L-05 | `inspect_pe_resources` | `VVentsim.exe` | Funciona; solo 12 recursos (iconos, manifiesto) | — |

| L-06 | `observe_native_ui` | ventana de VVentsim.exe (PID 11712) con `open_binary` abierto | `capability_unavailable`: «Native macOS utilities require macOS» (error exacto: `provider_id composite:native-macos+rea-artifact-graph+rea-dotnet-static`) | Aparezca un proveedor de observación para Windows; mientras tanto se usan `tools/observe_ventsim.ps1` (MSAA + PrintWindow) |

| L-07 | `open_binary` + `binary_overview` / `search_strings` (2026-10-16, V0.3) | `VentsimUI.DLL` | `open_binary` abre el archivo, pero `binary_overview` y `search_strings` fallan con `provider_unavailable`: Ghidra `managed_target_unsupported` (no admite .NET) y `not_configured`; Hopper `unsupported_host` (win32); IDA y Kuna `not_configured` (Kuna además no admite PE) | Se configure un proveedor que admita .NET en Windows |
| L-08 | `inspect_managed_members` (summary) (2026-10-16, V0.3) | `VentsimUI.DLL` | Repite L-01: `Managed metadata exceeds the 67108864 byte representation budget`; 0 tipos, 0 métodos, 0 cadenas | Idem L-01 |
| U-01 | `inspect_managed_artifact` + `inspect_analysis_view` (resources) | `es\VentsimNoteForms.resources.dll`, `es\VentsimUI.resources.dll` | **Funciona, cobertura completa**: 31 y 139 recursos de formulario inventariados con hash. REA no decodifica el contenido de un `.resources`: los textos se leen con `tools/read_resources.py` | — |
| U-02 | `inspect_pe_resources` | `es\VentsimUI.resources.dll` | Funciona: un recurso de versión; los textos van como recursos administrados (U-01) | — |

| L-09 | `inspect_pe_resources` + `inspect_managed_artifact` + `inspect_analysis_view` (resources) (2026-10-16, V0.3.1) | `ChasmGraphics.DLL` (motor gráfico, 43 MB) | Metadatos parciales (2 filas Module y Assembly, índices de heap fuera de rango). **42,9 MB de recursos incrustados en 4 blobs con nombres aleatorios** (89.852 B, 42.780.196 B, 7.148 B, 304 B): patrón de código cifrado por un protector. Leerlos equivale a desproteger código: **no se hace**. No hay shaders ni texturas legibles | Aparezca una vía legítima de REA para este formato |

Conclusión operativa: la ruta «descompilar y leer el código» no está disponible con las herramientas actuales y
**este proyecto no la persigue**. No se eluden protecciones ni se recupera código propietario. La fuente de
evidencia son: archivos de datos de ejemplo del usuario, la aplicación observada en ejecución (experimentos
manuales, ver docs/05), documentación pública y fisica/ingeniería de ventilación publicada.

Rutas descartadas por decisión (no por limitación técnica): desempaquetar recursos de los .DLL, volcado de memoria
del proceso, uso de las funciones de P/Invoke de memoria que aparecen en el exe.
