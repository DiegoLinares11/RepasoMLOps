# =============================================================================
# subir_a_testpypi.ps1 REAL de la Tarea 4, comentado línea por línea
# Repo original: https://github.com/DiegoLinares11/Tarea4-MLOPS
# =============================================================================
# Los comentarios con "##" son explicaciones agregadas para el repaso; los
# comentarios con un solo "#" venían en el script original.
#
## Requisitos antes de correrlo (una vez):
##   python -m pip install build twine
##   Copy-Item .env.example .env      y pegar el token real dentro de .env
## Si PowerShell bloquea el script:
##   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
# =============================================================================

# Publica el paquete en TestPyPI leyendo el token del archivo .env
#
#   Uso:   .\subir_a_testpypi.ps1
#
# El .env debe tener estas dos lineas (sin comillas):
#   TWINE_USERNAME=__token__
#   TWINE_PASSWORD=pypi-TU_TOKEN_AQUI
#
# El token nunca se escribe en la terminal ni queda en el historial de comandos.
## ^ Esa es LA razón del script. Si escribieras
##     twine upload -u __token__ -p pypi-AgEN... dist/*
## el token quedaría guardado en el historial de PowerShell
## (Get-Content (Get-PSReadLineOption).HistorySavePath lo muestra), en capturas
## de pantalla y en el video del curso. Quien tenga el token puede publicar
## versiones en tu nombre.

## Si cualquier comando falla, detener el script. Sin esto, si "python -m build"
## fallara, el script seguiría y subiría un dist/ viejo o vacío.
$ErrorActionPreference = "Stop"
## Moverse a la carpeta donde está el script, para que .env, dist/ y
## pyproject.toml se encuentren aunque lo llames desde otra carpeta.
Set-Location $PSScriptRoot

## Test-Path devuelve $true si el archivo existe. -not lo niega.
if (-not (Test-Path ".env")) {
    Write-Host "No encuentro .env en esta carpeta." -ForegroundColor Red
    Write-Host "Copia .env.example a .env y pone tu token de TestPyPI adentro."
    ## exit 1 = terminar con código de error (0 significa "todo bien").
    exit 1
}

# --- Cargar el .env en variables de entorno de esta sesion ---
## Get-Content lee el archivo línea por línea; ForEach-Object procesa cada una
## ($_ es la línea actual).
Get-Content ".env" | ForEach-Object {
    ## Expresión regular: "espacios opcionales, NOMBRE válido de variable,
    ## espacios, =, espacios, el resto de la línea". Las líneas de comentario
    ## (# ...) y las vacías no coinciden y se ignoran.
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
        ## $matches guarda los grupos capturados por la regex: [1] = nombre, [2] = valor.
        $nombre = $matches[1]
        ## Quitar espacios y comillas por si alguien escribió TWINE_PASSWORD="pypi-..."
        $valor = $matches[2].Trim().Trim('"').Trim("'")
        ## Crear la variable de entorno SOLO en este proceso ("Process"): al
        ## cerrar PowerShell desaparece. No queda guardada en Windows.
        [Environment]::SetEnvironmentVariable($nombre, $valor, "Process")
    }
}

## twine lee AUTOMÁTICAMENTE las variables TWINE_USERNAME y TWINE_PASSWORD, así
## que no hay que pasarlas como argumento. El usuario es literalmente "__token__"
## (así le indicas a PyPI que la contraseña es un token de API, no tu clave).
if (-not $env:TWINE_PASSWORD) {
    Write-Host "El .env no define TWINE_PASSWORD." -ForegroundColor Red
    exit 1
}
## Se imprime el usuario, NUNCA el token.
Write-Host "Token cargado desde .env (usuario: $env:TWINE_USERNAME)" -ForegroundColor Green

# --- 1. Construir ---
## `n es un salto de línea en PowerShell (el equivalente de \n).
Write-Host "`n[1/3] Construyendo el paquete..." -ForegroundColor Cyan
## Borrar el dist/ anterior: si quedara un 0.1.0 viejo junto a uno nuevo,
## "twine upload dist/*" intentaría subir los dos (y el viejo ya existe en el índice).
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
## Lee [build-system] de pyproject.toml, instala hatchling en un ambiente
## aislado y genera dist/act3_pipeline_mlops-0.1.0.tar.gz y
## dist/act3_pipeline_mlops-0.1.0-py3-none-any.whl
python -m build

# --- 2. Validar la metadata antes de subir ---
Write-Host "`n[2/3] Validando la metadata..." -ForegroundColor Cyan
## Revisa que el README se pueda mostrar como descripción, que la licencia y
## los clasificadores estén bien formados. Mejor fallar aquí que a medio subir.
python -m twine check dist/*

# --- 3. Subir a TestPyPI ---
Write-Host "`n[3/3] Subiendo a TestPyPI..." -ForegroundColor Cyan
## --repository testpypi apunta a https://test.pypi.org/legacy/ (twine ya
## conoce ese alias). Sin esta opción subiría al PyPI REAL.
python -m twine upload --repository testpypi dist/*

Write-Host "`nListo. El paquete deberia estar en:" -ForegroundColor Green
Write-Host "  https://test.pypi.org/project/act3-pipeline-mlops/"
Write-Host "`nPara comprobar que se instala:"
## --index-url        -> buscar PRIMERO en TestPyPI (ahí está nuestro paquete)
## --extra-index-url  -> si algo no está ahí, buscarlo en el PyPI real.
##                       TestPyPI NO tiene scikit-learn, pandas, numpy ni scipy,
##                       así que sin esta opción la instalación falla.
Write-Host "  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ act3-pipeline-mlops"
