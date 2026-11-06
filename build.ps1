# Compila NVS para Windows (PyInstaller, carpeta autocontenida) y ejecuta una autoprueba del .exe.
# Requisitos: Windows 10/11 x64 y uv (https://docs.astral.sh/uv/). Python 3.12 lo descarga uv si hace falta.
# Uso:  powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host '== 1/4 Sincronizando dependencias (uv.lock)'
uv sync
if ($LASTEXITCODE) { throw 'uv sync falló' }

Write-Host '== 2/4 Ejecutando pruebas'
uv run pytest -q
if ($LASTEXITCODE) { throw 'Las pruebas fallaron; no se compila.' }

Write-Host '== 3/4 Compilando con PyInstaller'
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist\NVS) { Remove-Item dist\NVS -Recurse -Force }
uv run pyinstaller --noconfirm --clean --windowed --name NVS --paths src `
    --distpath dist --workpath build --icon assets/nvs.ico `
    --add-data "src/nvs/data;nvs/data" `
    --exclude-module tkinter --exclude-module matplotlib --exclude-module PySide6.QtNetwork `
    --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick --exclude-module PySide6.QtPdf `
    run_app.py
if ($LASTEXITCODE) { throw 'PyInstaller falló' }
Copy-Item LEEME.txt dist\NVS\LEEME.txt -Force

Write-Host '== 4/4 Autoprueba del ejecutable (carga, cálculo, render, CSV)'
$out = Join-Path $env:TEMP 'nvs_selftest'
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
$p = Start-Process -FilePath dist\NVS\NVS.exe -ArgumentList '--selftest', $out -PassThru -Wait
if ($p.ExitCode -ne 0) { throw "La autoprueba del .exe terminó con código $($p.ExitCode); ver $out\selftest.json" }
Get-Content "$out\selftest.json" | Select-Object -First 12
Compress-Archive -Path dist\NVS -DestinationPath dist\NVS-0.3.1-win64.zip -Force
# build\ solo contiene un .exe intermedio SIN bibliotecas (da 'Failed to load Python DLL'); se borra para evitar confusiones
if (Test-Path build) { Remove-Item build -Recurse -Force }
Write-Host "Listo: dist\NVS\NVS.exe  (y dist\NVS-0.3.1-win64.zip)"
