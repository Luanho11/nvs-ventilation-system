# Verificación de herramientas de análisis (2026-10-16)

Alcance: solo lectura sobre `C:\Program Files\Ventsim DESIGN 6`. No se ejecutó ni modificó nada de la instalación.

## 1. Servidor MCP rea-local
- Responde. Paquete `rea-agents` 6.5.0, raíz `C:\Users\Hostos\Desktop\rea`, comando `scripts\rea.mjs`, catálogo de 207 herramientas MCP.
- `alignment.state = unknown`: no se comparó con una versión/catálogo esperado (no se pasaron `expected_*`).
- Aviso: `dist\index.js` no existe en el clon; el servidor arranca desde `scripts\rea.mjs`, así que funciona, pero no se verificó que el clon esté compilado.

## 2. Capacidades disponibles en este Windows (x64, Win 11)
| Disponible (probado) | Resultado |
|---|---|
| `inspect_pe_resources` | OK sobre `VVentsim.exe` (12 recursos, solo iconos/manifest) |
| `inspect_managed_artifact` (summary) | OK, **cobertura parcial** (ver §3) |
| `inspect_managed_native_boundaries` | OK, **cobertura parcial** |
| `inspect_managed_members` | **NO funciona** sobre `VentsimUI.DLL` ("CLI metadata could not be admitted") |

Disponibles pero no relevantes para este objetivo: Frida (sin probar), navegador/Electron/Flutter/Go/Rust, pcap, sqlite.

## 3. Limitaciones / dependencias que impiden el análisis
- **Sin decompilador nativo**: Ghidra (`GHIDRA_INSTALL_DIR` sin definir), IDA (`REA_IDA_MCP_CONFIG`), Kuna (`REA_KUNA_COMMAND`) no configurados; Hopper no soportado en Windows. Por tanto `open_binary` y las herramientas de procedimientos/pseudocódigo no se han podido usar con un proveedor profundo. No se ha llamado a `open_binary`.
- **Sin decompilación C#**: REA es solo metadatos estáticos; no hay ILSpy/dnSpy/dotnet SDK en el PATH (`dotnet`, `ilspycmd` no encontrados). Java 26, Node 24, Python 3.14, uv y Git sí están.
- Sin `rizin`, `objdump`, `gdb`, `dumpbin` en el PATH (hay Windows SDK 10.0.26100 instalado, no se buscó dumpbin dentro).
- `inspect_binary_layout` (ELF) e `inspect_macho` no aplican a PE.

## 4. Lo que se observó realmente sobre los binarios
- `VVentsim.exe`, `VentsimUI.DLL`, `ChasmCommon.DLL`, `ChasmGraphics.DLL`: PE32 x86, CIL puro, .NET Framework 4.7.2, versión 6.0.5.4 (exe) / 6.0.4.6 (UI) / 1.2.0.1 (Chasm*). Howden Group.
- Anomalías de metadatos en los cuatro: tablas Module y Assembly con 2 filas, streams `#Blop` y `#GUlD` además de `#Blob`/`#GUID`, índices de heap fuera de rango. Hay recursos incrustados enormes (exe 10,3 MB; UI 12,8 MB; Common 11,6 MB; Graphics 42,9 MB).
- `VVentsim.exe` declara P/Invoke con nombres aleatorios a `VirtualProtect`, `VirtualAlloc`, `LoadLibrary`, `GetProcAddress`, `WriteProcessMemory`, `ReadProcessMemory`, `OpenProcess`, `FindResource`.
- **Interpretación (inferencia, no verificada)**: el patrón es compatible con un protector/ofuscador con código o recursos empaquetados. No se ha comprobado qué hay dentro de los recursos ni cómo se cargan.

## 5. Qué NO se ha hecho
- No se han leído tipos, métodos, cadenas ni lógica de VentSim. No hay conclusión alguna sobre su algoritmo ni sus formatos de archivo.
- No se ha ejecutado VentSim ni se ha instrumentado.

## 6. Pendiente de decisión del usuario
Ver mensaje de la sesión (licencia/alcance y vía de trabajo recomendada).
