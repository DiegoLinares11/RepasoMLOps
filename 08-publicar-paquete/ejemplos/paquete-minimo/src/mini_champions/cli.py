"""Punto de entrada del comando de consola ``mini-champions``.

pyproject.toml declara:  mini-champions = "mini_champions.cli:main"
Al instalar, pip crea un ejecutable (mini-champions.exe en Windows) que importa
este módulo y llama a main(). El valor que devuelve main() es el código de salida.
"""

from __future__ import annotations

import sys

from . import __version__
from .datos import cargar_partidos, contar_resultados


def main() -> int:
    partidos = cargar_partidos()
    print(f"mini_champions v{__version__} (Python {sys.version.split()[0]})")
    print(f"Partidos empaquetados: {len(partidos)}")
    for resultado, n in sorted(contar_resultados().items()):
        print(f"  {resultado:<9} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
