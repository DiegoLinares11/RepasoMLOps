"""Plugin de ejemplo para ``act9-pipeline``: k vecinos más cercanos.

No importa nada de ``act9_pipeline``. Solo cumple el contrato del grupo
``act9_pipeline.modelos``: una función sin argumentos que devuelve el
estimador, el espacio de hiperparámetros y una descripción.
"""

from scipy.stats import randint
from sklearn.neighbors import KNeighborsClassifier


def knn() -> dict:
    """KNN: el número de vecinos controla qué tan suave es la frontera."""
    return {
        "estimador": KNeighborsClassifier(),
        "espacio": {
            "n_neighbors": randint(3, 30),
            "weights": ["uniform", "distance"],
            "p": [1, 2],
        },
        "descripcion": "KNeighborsClassifier (plugin externo act9-modelo-knn)",
    }
