"""MLflow de punta a punta con el dataset de la Champions, en un solo archivo.

Necesita MLflow (no está en el requirements.txt del repo):

    pip install mlflow
    cd 15-mlflow/ejemplos
    python mlflow_minimo.py
    mlflow ui --backend-store-uri sqlite:///mlflow.db     # y abrir http://127.0.0.1:5000

Usa una base SQLite local (mlflow.db), así que no hace falta levantar un servidor. Hace tres cosas:

1. Un run con registro MANUAL: parámetros, métricas, un dataset y el modelo.
2. Un run con AUTOLOG sobre una búsqueda de hiperparámetros (run padre + 5 hijos).
3. Registra el mejor modelo en el Model Registry, le pone el alias @campeon y lo carga por el alias.
"""

import warnings
from pathlib import Path

import mlflow
import pandas as pd
from mlflow import MlflowClient
from mlflow.models import infer_signature
from sklearn import metrics
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")
RANDOM_STATE = 42
CSV = Path(__file__).resolve().parents[2] / "datos" / "champions_league_matches.csv"
NUMERICAS = ["home_shots_on_target_pct", "away_shots_on_target_pct", "home_saves_pct", "away_saves_pct"]
EQUIPOS = ["home_team", "away_team"]
# Tipos que skops debe aceptar al guardar el pipeline (los da skops.io.get_untrusted_types).
TIPOS_CONFIABLES = ["numpy.dtype", "sklearn.tree._tree.Tree"]

# --- Datos: sin score ni winner, que revelan el resultado (fuga de información) ---------------
partidos = pd.read_csv(CSV).dropna(how="all")
X, y = partidos[NUMERICAS + EQUIPOS], partidos["result"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y)

pipe = Pipeline([
    ("preprocesamiento", ColumnTransformer([
        ("numericas", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), NUMERICAS),
        ("equipos", OneHotEncoder(handle_unknown="ignore"), EQUIPOS),
    ])),
    ("modelo", RandomForestClassifier(n_estimators=200, max_depth=6, random_state=RANDOM_STATE)),
])

mlflow.set_tracking_uri("sqlite:///mlflow.db")
mlflow.set_experiment("Champions_Repaso")

# --- 1. Registro manual -----------------------------------------------------------------------
with mlflow.start_run(run_name="manual-random-forest"):
    pipe.fit(X_train, y_train)
    pred = pipe.predict(X_test)
    mlflow.log_params({"n_estimators": 200, "max_depth": 6})
    mlflow.log_metrics({
        "test_accuracy": metrics.accuracy_score(y_test, pred),
        "test_f1_macro": metrics.f1_score(y_test, pred, average="macro"),
    })
    mlflow.log_input(mlflow.data.from_pandas(X_train.assign(result=y_train.values), source=str(CSV),
                                             name="champions-entrenamiento", targets="result"), context="training")
    # Desde MLflow 3, log_model guarda con skops (formato seguro) fuera de Databricks: hay que
    # declarar los tipos que no son de su lista blanca (TIPOS_CONFIABLES, arriba).
    mlflow.sklearn.log_model(pipe, name="modelo", signature=infer_signature(X_test, pred),
                             input_example=X_test.head(3), skops_trusted_types=TIPOS_CONFIABLES)

# --- 2. Autolog sobre una búsqueda -------------------------------------------------------------
# Ojo: autolog() parcha sklearn.metrics al activarse. Si f1_score se hubiera importado antes con
# "from sklearn.metrics import f1_score", la métrica de prueba NO se registraría.
mlflow.sklearn.autolog(max_tuning_runs=5)
busqueda = RandomizedSearchCV(
    pipe,
    {"modelo__n_estimators": [100, 200, 400], "modelo__max_depth": [None, 4, 6, 10],
     "modelo__min_samples_leaf": [1, 2, 4], "modelo__class_weight": [None, "balanced"]},
    n_iter=15, scoring="f1_macro", cv=StratifiedKFold(5, shuffle=True, random_state=RANDOM_STATE),
    random_state=RANDOM_STATE,
)
with mlflow.start_run(run_name="autolog-busqueda") as run_auto:
    busqueda.fit(X_train, y_train)
    f1_prueba = metrics.f1_score(y_test, busqueda.predict(X_test), average="macro")  # se registra sola
mlflow.sklearn.autolog(disable=True)

run = MlflowClient().get_run(run_auto.info.run_id)
print(f"Autolog · run padre con {len(run.data.params)} parámetros y métricas: {sorted(run.data.metrics)}")
print(f"F1 macro: validación cruzada {busqueda.best_score_:.3f} · prueba {f1_prueba:.3f}")

# --- 3. Model Registry: versión + alias --------------------------------------------------------
with mlflow.start_run(run_name="mejor-de-la-busqueda"):
    info = mlflow.sklearn.log_model(busqueda.best_estimator_, name="modelo", input_example=X_test.head(3),
                                    skops_trusted_types=TIPOS_CONFIABLES,
                                    registered_model_name="champions-repaso")
version = info.registered_model_version
MlflowClient().set_registered_model_alias("champions-repaso", "campeon", version)

campeon = mlflow.sklearn.load_model("models:/champions-repaso@campeon")
print(f"Cargado por alias: champions-repaso v{version} · "
      f"F1 macro en prueba {metrics.f1_score(y_test, campeon.predict(X_test), average='macro'):.3f}")
print("Abre la interfaz con:  mlflow ui --backend-store-uri sqlite:///mlflow.db")
