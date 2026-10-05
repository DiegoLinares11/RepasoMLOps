# Lo que hay DENTRO del ejecutable que crea pip para un entry point.
#
# Al instalar act9-pipeline, pip crea .venv\Scripts\act9-entrenar.exe (en Linux,
# .venv/bin/act9-entrenar). En Windows es un lanzador pequeño que trae pegado este
# __main__.py; lo sacamos del .exe en la Actividad 9. No hay magia: importa la
# función que dice el pyproject.toml, la llama sin argumentos y usa lo que devuelve
# como código de salida del proceso.

import sys

from act9_pipeline.cli.entrenar import main  # "act9_pipeline.cli.entrenar:main" del pyproject

if __name__ == "__main__":
    # El nombre del comando que ve argparse queda sin ".exe".
    sys.argv[0] = sys.argv[0].removesuffix(".exe")
    # main() devuelve 0 (bien), 1 (no pasó el umbral) o 2 (error de uso).
    # Ese número es lo que leen make, GitHub Actions o un orquestador.
    sys.exit(main())
