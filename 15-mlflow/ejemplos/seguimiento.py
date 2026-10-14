"""Seguimiento del pipeline de Champions League con MLflow.

Aquí está el registro **manual** (cada parámetro, métrica y archivo se guarda a
propósito). El notebook ``03_pipeline_sklearn_mlflow.ipynb`` lo compara con el
registro **automático** (``mlflow.sklearn.autolog``).

Qué se guarda en cada run
-------------------------
- **Parámetros**: la familia, la configuración de la búsqueda y los mejores
  hiperparámetros que encontró ``RandomizedSearchCV``.
- **Métricas**: F1 macro de la validación cruzada, accuracy y F1 macro en el
  conjunto de prueba, y el F1 macro de un modelo que siempre predice la clase
  mayoritaria (para saber si el modelo aporta algo).
- **Datasets** (``mlflow.data``): los conjuntos de entrenamiento y de prueba,
  con su huella digital (*digest*) y la ruta del CSV de origen.
- **Archivos**: la matriz de confusión, el reporte de clasificación y la tabla
  completa de la búsqueda.
- **Modelo**: el pipeline completo (preprocesamiento + selección + modelo) con
  su firma de entrada y salida y con el código de este paquete
  (``code_paths``). Sin ese código, quien cargue el modelo en otra máquina
  necesitaría tener instalado ``taller3_pipeline`` para que funcionen los
  transformadores propios (``PorcentajeATexto`` y ``RatioATexto``).

Formato del modelo
------------------
Desde MLflow 3, fuera de Databricks, ``mlflow.sklearn.log_model`` guarda los
modelos con **skops** en lugar de pickle. Pickle puede ejecutar cualquier
código al cargar un archivo; skops solo reconstruye los tipos que se declaran
como confiables. Por eso hay que listar los que usa nuestro pipeline
(``TIPOS_CONFIABLES``); si falta uno, MLflow se niega a guardar el modelo.
"""

from __future__ import annotations

import os
import urllib.request
import warnings
from importlib import resources
from pathlib import Path

import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold

from .data import TARGET, cargar_datos
from .modelos import FAMILIAS, espacio_del_pipeline
from .pipeline import SEED, construir_pipeline

URI_POR_DEFECTO = "http://127.0.0.1:8080"
EXPERIMENTO = "Champions_Resultado"
MODELO_REGISTRADO = "champions-resultado"
ALIAS = "campeon"

# Tipos que skops debe aceptar al reconstruir nuestros pipelines. Se obtuvieron
# con skops.io.get_untrusted_types() sobre las cuatro familias y se revisaron
# uno por uno: son de scikit-learn, de NumPy o de este mismo paquete.
TIPOS_CONFIABLES = [
    "numpy.dtype",
    "sklearn.feature_selection._univariate_selection.f_classif",
    "sklearn.tree._tree.Tree",
    "sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor",
    "taller3_pipeline.transformers.PorcentajeATexto",
    "taller3_pipeline.transformers.RatioATexto",
]


def uri_de_seguimiento(uri: str | None = None) -> str:
    """El servidor de MLflow: el argumento, la variable ``MLFLOW_TRACKING_URI`` o el local."""
    return uri or os.environ.get("MLFLOW_TRACKING_URI") or URI_POR_DEFECTO


def servidor_disponible(uri: str | None = None, espera: float = 3) -> bool:
    """``True`` si el servidor de MLflow responde en ``/health``."""
    uri = uri_de_seguimiento(uri)
    if not uri.startswith("http"):
        return True  # una base de datos o carpeta local no necesita servidor
    try:
        with urllib.request.urlopen(f"{uri.rstrip('/')}/health", timeout=espera) as r:
            return r.status == 200
    except OSError:
        return False


def configurar_mlflow(experimento: str = EXPERIMENTO, uri: str | None = None):
    """Apunta MLflow al servidor y activa el experimento (lo crea si no existe)."""
    import mlflow

    mlflow.set_tracking_uri(uri_de_seguimiento(uri))
    return mlflow.set_experiment(experimento)


def ruta_del_csv() -> str:
    """Ruta del CSV empaquetado, para guardarla como origen de los datasets."""
    return str(resources.files("taller3_pipeline.datasets").joinpath("champions_league_matches.csv"))


def dataset_mlflow(X: pd.DataFrame, y: pd.Series, nombre: str):
    """Envuelve X e y en un dataset de MLflow (calcula su digest y su esquema)."""
    import mlflow.data

    with warnings.catch_warnings():
        # MLflow avisa que una ruta local "se puede interpretar de varias formas" (dos
        # tipos de origen registrados con el mismo nombre); elige el correcto igual.
        warnings.filterwarnings("ignore", message="The specified dataset source can be interpreted")
        return mlflow.data.from_pandas(
            X.assign(**{TARGET: y.values}), source=ruta_del_csv(), name=nombre, targets=TARGET
        )


def figura_matriz_confusion(y_real, y_pred):
    """Matriz de confusión como figura de matplotlib, lista para ``mlflow.log_figure``."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import ConfusionMatrixDisplay

    fig, ax = plt.subplots(figsize=(5, 4))
    ConfusionMatrixDisplay.from_predictions(y_real, y_pred, ax=ax, cmap="Blues", colorbar=False)
    ax.set_title("Matriz de confusión (prueba)")
    ax.set_xlabel("Predicción")
    ax.set_ylabel("Real")
    fig.tight_layout()
    plt.close(fig)
    return fig


def entrenar_familia(
    familia: str,
    n_iter: int = 40,
    folds: int = 5,
    n_jobs: int = -1,
    registrar_como: str | None = None,
    nombre_run: str | None = None,
) -> dict:
    """Calibra una familia con ``RandomizedSearchCV`` y guarda todo en un run de MLflow.

    Hay que llamar antes a ``configurar_mlflow``. Si ya hay un run activo (por
    ejemplo, el que abre ``mlflow run`` desde el ``MLproject``), se usa ese.
    """
    import mlflow
    from mlflow.models import infer_signature

    X_train, X_test, y_train, y_test = cargar_datos(seed=SEED)
    definicion = FAMILIAS[familia]()
    busqueda = RandomizedSearchCV(
        construir_pipeline(definicion["estimador"]),
        espacio_del_pipeline(definicion["espacio"]),
        n_iter=n_iter,
        scoring="f1_macro",
        cv=StratifiedKFold(n_splits=folds, shuffle=True, random_state=SEED),
        random_state=SEED,
        n_jobs=n_jobs,
    )

    # Si ya hay un run abierto (el de una comparación), este queda como run hijo.
    with mlflow.start_run(run_name=nombre_run or familia, nested=mlflow.active_run() is not None) as run:
        mlflow.set_tags({"familia": familia, "tipo_de_registro": "manual", "dataset": "champions_league_matches"})
        mlflow.log_input(dataset_mlflow(X_train, y_train, "champions-entrenamiento"), context="training")
        mlflow.log_input(dataset_mlflow(X_test, y_test, "champions-prueba"), context="testing")

        busqueda.fit(X_train, y_train)
        mejor = busqueda.best_estimator_
        y_pred = mejor.predict(X_test)
        mayoritaria = DummyClassifier(strategy="most_frequent").fit(X_train, y_train).predict(X_test)
        indice = busqueda.best_index_

        parametros = {"familia": familia, "n_iter": n_iter, "cv_folds": folds, "scoring": "f1_macro"}
        parametros.update({nombre.removeprefix("modelo__"): valor for nombre, valor in busqueda.best_params_.items()})
        metricas = {
            "cv_f1_macro": float(busqueda.best_score_),
            "cv_f1_macro_std": float(busqueda.cv_results_["std_test_score"][indice]),
            "test_accuracy": float(accuracy_score(y_test, y_pred)),
            "test_f1_macro": float(f1_score(y_test, y_pred, average="macro")),
            "baseline_test_f1_macro": float(f1_score(y_test, mayoritaria, average="macro", zero_division=0)),
        }
        mlflow.log_params(parametros)
        mlflow.log_metrics(metricas)

        mlflow.log_figure(figura_matriz_confusion(y_test, y_pred), "evaluacion/matriz_confusion.png")
        mlflow.log_text(classification_report(y_test, y_pred, digits=3, zero_division=0), "evaluacion/reporte.txt")
        mlflow.log_text(pd.DataFrame(busqueda.cv_results_).to_csv(index=False), "busqueda/cv_results.csv")

        info = mlflow.sklearn.log_model(
            mejor,
            name="modelo",
            signature=infer_signature(X_test, y_pred),
            input_example=X_test.head(3),
            code_paths=[str(Path(__file__).parent)],
            skops_trusted_types=TIPOS_CONFIABLES,
            registered_model_name=registrar_como,
        )

    return {
        "familia": familia,
        "run_id": run.info.run_id,
        "model_uri": info.model_uri,
        "version": getattr(info, "registered_model_version", None),
        "parametros": parametros,
        "metricas": metricas,
    }


def asignar_alias(version: int | str, nombre: str = MODELO_REGISTRADO, alias: str = ALIAS) -> None:
    """Apunta el alias (``@campeon``) a una versión del modelo registrado."""
    from mlflow import MlflowClient

    MlflowClient().set_registered_model_alias(nombre, alias, str(version))
