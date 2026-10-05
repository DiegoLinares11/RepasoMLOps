# =============================================================================
# setup_entorno.ps1: crea (o recrea) el ambiente virtual del proyecto en Windows
# =============================================================================
# Uso, desde la carpeta del proyecto en PowerShell:
#
#   .\setup_entorno.ps1              # crea .venv si no existe e instala dependencias
#   .\setup_entorno.ps1 -Recrear     # borra .venv y lo crea de cero
#
# Si PowerShell dice "la ejecución de scripts está deshabilitada en este sistema",
# ejecuta UNA vez (solo afecta a tu usuario, no pide administrador):
#
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
#
# O, solo para esta ventana de PowerShell:
#
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# =============================================================================

# param() declara los argumentos del script. [switch] es un sí/no: si escribes
# -Recrear vale $true, si no, $false.
param(
    [switch]$Recrear,
    [string]$VersionPython = "3.12"   # versión que pediremos al py launcher
)

# Si cualquier comando falla, detener el script (por defecto PowerShell sigue).
$ErrorActionPreference = "Stop"

# Trabajar SIEMPRE en la carpeta donde está este script, sin importar desde dónde
# lo llamaste. $PSScriptRoot es esa carpeta.
Set-Location $PSScriptRoot

# --- 1. Encontrar un Python --------------------------------------------------
# En Windows conviene usar el "py launcher" (py.exe), que se instala con el
# instalador oficial de python.org. Permite elegir versión:  py -3.12, py -3.11...
#   py --list   -> muestra todas las versiones instaladas
# Si no está, usamos "python" (ojo: puede ser el alias falso de la Microsoft Store,
# que abre la tienda en vez de ejecutar Python; se desactiva en
# Configuración > Aplicaciones > Alias de ejecución de aplicaciones).
if (Get-Command py -ErrorAction SilentlyContinue) {
    $python = "py"
    $argsPython = @("-$VersionPython")
} else {
    $python = "python"
    $argsPython = @()
}
Write-Host "Usando: $python $argsPython" -ForegroundColor Cyan
& $python @argsPython --version     # & ejecuta un comando guardado en una variable

# --- 2. Crear el ambiente ----------------------------------------------------
if ($Recrear -and (Test-Path ".venv")) {
    Write-Host "Borrando .venv anterior..." -ForegroundColor Yellow
    Remove-Item ".venv" -Recurse -Force
}

if (-not (Test-Path ".venv")) {
    Write-Host "Creando .venv..." -ForegroundColor Cyan
    # python -m venv .venv  ->  "ejecuta el módulo venv y crea la carpeta .venv"
    & $python @argsPython -m venv .venv
}

# --- 3. Usar el Python DEL AMBIENTE sin activarlo ----------------------------
# Activar solo cambia el PATH. En un script es más seguro llamar al ejecutable
# del ambiente por su ruta: así es imposible instalar en el Python global por error.
$pyVenv = Join-Path ".venv" "Scripts\python.exe"

# Actualizar pip primero (versiones viejas de pip fallan con wheels modernos).
& $pyVenv -m pip install --upgrade pip

# --- 4. Instalar dependencias --------------------------------------------------
# Si existe un lock (foto exacta), se usa ese: reproducibilidad total.
# Si no, el requirements.txt (intención).
if (Test-Path "requirements-lock.txt") {
    & $pyVenv -m pip install -r requirements-lock.txt
} elseif (Test-Path "requirements.txt") {
    & $pyVenv -m pip install -r requirements.txt
} else {
    Write-Host "No hay requirements.txt; el ambiente queda vacío." -ForegroundColor Yellow
}

# --- 5. Comprobar --------------------------------------------------------------
# sys.prefix debe terminar en .venv: prueba de que ese Python es el del ambiente.
& $pyVenv -c "import sys; print('sys.prefix =', sys.prefix)"

Write-Host "`nListo. Para activarlo en esta terminal:" -ForegroundColor Green
Write-Host "   .\.venv\Scripts\Activate.ps1"
Write-Host "Para salir:  deactivate"
