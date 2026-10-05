"""Lee el CSV que viaja DENTRO del paquete.

Solo usa la librería estándar (csv, importlib.resources, collections) para que
el paquete se pueda instalar sin internet y sin dependencias.
"""

from __future__ import annotations

import csv
from collections import Counter
from importlib import resources


def cargar_partidos() -> list[dict]:
    """Devuelve los partidos del CSV empaquetado como lista de diccionarios.

    ``resources.files`` encuentra el archivo dentro del paquete instalado, esté
    donde esté (site-packages de un venv, un wheel, una imagen de Docker...).
    Nunca uses una ruta fija como "C:/Users/.../partidos.csv": en otra compu no existe.
    """
    ruta = resources.files("mini_champions") / "datasets" / "partidos.csv"
    with ruta.open("r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def contar_resultados() -> dict[str, int]:
    """Cuántos partidos terminaron en Home Win, Away Win y Draw."""
    return dict(Counter(p["result"] for p in cargar_partidos()))
