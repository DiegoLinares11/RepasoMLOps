"""mini_champions: paquete MÍNIMO para practicar empaquetado (tema 08).

Se instala como  ``mini-champions-uvg``  (nombre de DISTRIBUCIÓN, con guiones)
pero se importa como  ``mini_champions``  (nombre de IMPORT, con guion bajo),
igual que act3-pipeline-mlops / act3_pipeline en la Tarea 4.
"""

from .datos import cargar_partidos, contar_resultados

__all__ = ["cargar_partidos", "contar_resultados"]

# Versión que el código conoce de sí mismo. Debe coincidir con la de pyproject.toml.
__version__ = "0.1.0"
