#!/usr/bin/env bash
# =============================================================================
# subir_a_testpypi.sh: el MISMO flujo que subir_a_testpypi.ps1, en bash
# =============================================================================
# (No estaba en la Tarea 4; es la traducción para Linux / macOS / Git Bash.)
#
# Uso, desde la carpeta del proyecto (donde está pyproject.toml):
#   python3 -m pip install build twine     # una vez
#   cp .env.example .env                   # y pegar el token real
#   bash subir_a_testpypi.sh
# =============================================================================

set -euo pipefail                 # detenerse ante cualquier error
cd "$(dirname "$0")"              # trabajar en la carpeta del script

if [[ ! -f .env ]]; then
    echo "No encuentro .env en esta carpeta. Copia .env.example a .env y pon tu token." >&2
    exit 1
fi

# Cargar el .env como variables de entorno de ESTE proceso.
# set -a = "exporta automáticamente toda variable que se defina"; luego
# "source" ejecuta el .env como si fueran asignaciones VAR=valor.
set -a
# shellcheck disable=SC1091
source .env
set +a

if [[ -z "${TWINE_PASSWORD:-}" ]]; then
    echo "El .env no define TWINE_PASSWORD." >&2
    exit 1
fi
echo "Token cargado desde .env (usuario: ${TWINE_USERNAME:-})"   # nunca imprimir el token

echo; echo "[1/3] Construyendo el paquete..."
rm -rf dist
python3 -m build

echo; echo "[2/3] Validando la metadata..."
python3 -m twine check dist/*

echo; echo "[3/3] Subiendo a TestPyPI..."
python3 -m twine upload --repository testpypi dist/*

echo
echo "Listo. Comprueba la instalación en un venv limpio:"
echo "  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ act3-pipeline-mlops"
