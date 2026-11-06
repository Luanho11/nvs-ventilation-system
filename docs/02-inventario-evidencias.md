# Inventario de evidencias y recursos (2026-10-16)

## Instalación de referencia `C:\Program Files\Ventsim DESIGN 6` (solo lectura)
| Recurso | Contenido | Uso |
|---|---|---|
| `examples\*.vsm/.vsmt` | 23 proyectos (gzip + texto TAB). Versiones de guardado 3.2.4.8 – 6.0.4.6 | Oráculo de resultados y de formato (E-001) |
| `examples\dxf\*.dxf` | 9 DXF (texto) | Pruebas de importación (A08) |
| `examples\SurveyBackend.vlg` | base Jet DB (4 MB) | Importación de datos de levantamiento (A09) |
| `examples\Settings.vtp` | plantilla visual (texto TAB): presets k-factor, etc. | D06, E04 |
| `examples\VentsimTunnellingDefaultFans.json` (8,6 MB) / `.vsmt` | biblioteca de ventiladores de túnel (JSON) | Curvas de ventilador (B06), D03 |
| `VVentsim.exe.config` | configuración de logging (NLog), proxy. Sin parámetros de cálculo | — |
| `es/ pl/ ru/ vi/` | carpetas de idioma | Etiquetas de UI para inventario (E08) — pendiente de inspección |
| `bin\` | DevExpress 25.1 (UI), WebView2, SQLite-net, EasyModbus, ffmpeg.exe, MDBAccess.exe, teighaimport.dll (DXF/DWG) y otros | **Solo indica tecnologías y funciones** (informes PDF/Office, Modbus, vídeo, MDB, DWG). Sin análisis de código |
| `VVentsim.exe`, `VentsimUI.DLL`, `ChasmCommon.DLL`, `ChasmGraphics.DLL` | .NET 4.7.2 x86, con metadatos anómalos y recursos grandes | **No se analizan** (docs/01) |
| Manuales / ayuda / PDF | **no hay** en la instalación | Pendiente: documentación pública en línea (ventsim.com) |

## Otros
- Datos del usuario: no se encontraron proyectos propios en Documentos/Escritorio (búsqueda por *.vsm/*.vnt en Escritorio).
- Registro: clave `VentsimDesignfile` (asociación de archivo).
- Logs de ejecución: `%ProgramData%\Howden\Ventsim\Logs\ventsim.log` (NLog) — se generan al ejecutar; no existen aún porque no se ha ejecutado.

## Evidencia derivada
- E-001 formato .vsm (docs/evidence/E-001-formato-vsm.md).
- Datos de oráculo locales: `oracle/` (vacío por ahora; las pruebas leen directamente de la instalación).
