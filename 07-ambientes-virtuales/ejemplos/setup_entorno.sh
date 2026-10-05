#!/usr/bin/env bash
# =============================================================================
# setup_entorno.sh: crea (o recrea) el ambiente virtual en Linux / macOS / Git Bash
# =============================================================================
# Es el gemelo de setup_entorno.ps1. Uso, desde la carpeta del proyecto:
#
#   bash setup_entorno.sh              # crea .venv si no existe e instala dependencias
#   bash setup_entorno.sh --recrear    # borra .venv y lo crea de cero
#
# (o dale permiso de ejecución una vez con  chmod +x setup_entorno.sh  y luego
#  ./setup_entorno.sh)
# =============================================================================

# -e: salir si un comando falla.  -u: error si usas una variable no definida.
# -o pipefail: si falla un comando dentro de un "a | b", el pipe entero falla.
set -euo pipefail

# Moverse a la carpeta del script (equivalente a Set-Location $PSScriptRoot).
cd "$(dirname "$0")"

# --- 1. Encontrar un Python ------------------------------------------------------
# En Linux/macOS el comando suele ser python3 ("python" a veces no existe o es 2.7).
# En Git Bash sobre Windows suele ser "python" o "py".
PYTHON="${PYTHON:-python3}"          # se puede cambiar:  PYTHON=python3.12 bash setup_entorno.sh
command -v "$PYTHON" >/dev/null || PYTHON=python
echo "Usando: $PYTHON ($($PYTHON --version))"

# --- 2. Crear el ambiente --------------------------------------------------------
if [[ "${1:-}" == "--recrear" && -d .venv ]]; then
    echo "Borrando .venv anterior..."
    rm -rf .venv
fi

if [[ ! -d .venv ]]; then
    echo "Creando .venv..."
    # En Ubuntu/Debian, si falla con "ensurepip is not available":
    #   sudo apt install python3-venv
    "$PYTHON" -m venv .venv
fi

# --- 3. Ruta del Python del ambiente (sin activar) --------------------------------
# Linux/macOS: .venv/bin/python     Windows (Git Bash): .venv/Scripts/python.exe
if [[ -x .venv/bin/python ]]; then
    PY_VENV=.venv/bin/python
else
    PY_VENV=.venv/Scripts/python.exe
fi

"$PY_VENV" -m pip install --upgrade pip

# --- 4. Instalar dependencias ------------------------------------------------------
if [[ -f requirements-lock.txt ]]; then
    "$PY_VENV" -m pip install -r requirements-lock.txt
elif [[ -f requirements.txt ]]; then
    "$PY_VENV" -m pip install -r requirements.txt
else
    echo "No hay requirements.txt; el ambiente queda vacío."
fi

# --- 5. Comprobar --------------------------------------------------------------------
"$PY_VENV" -c "import sys; print('sys.prefix =', sys.prefix)"

echo
echo "Listo. Para activarlo en esta terminal:"
echo "   source .venv/bin/activate      # Linux/macOS"
echo "   source .venv/Scripts/activate  # Git Bash en Windows"
echo "Para salir:  deactivate"
# Nota: "source" es obligatorio. Si ejecutas  ./activate  corre en una subshell,
# cambia el PATH de ESA subshell y al terminar no queda nada activado.
