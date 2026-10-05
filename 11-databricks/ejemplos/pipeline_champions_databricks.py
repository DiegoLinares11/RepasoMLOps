# Databricks notebook source
# =============================================================================
# pipeline_champions_databricks.py  -  Ejercicio 4 / Actividad 7
# (Ejecicio3-MLOPS/databricks/pipeline_champions_databricks.py)
# -----------------------------------------------------------------------------
# Notebook REAL con comentarios de repaso; el código es idéntico al original.
#
# Qué es: el MISMO pipeline del Ejercicio 3 (extraer -> limpiar -> entrenar ->
# evaluar con compuerta), pero corriendo en Databricks. Lo nuevo:
#   - Unity Catalog: los datos limpios quedan como TABLA (workspace.default.partidos_limpios)
#     consultable con SQL, en vez de un CSV suelto en artefactos/.
#   - MLflow: mlflow.sklearn.autolog() registra parámetros, métricas y modelo
#     de cada entrenamiento -> el "registro de modelos" que en la Actividad 4
#     se resolvió a mano con un volumen de Docker (un único modelo.joblib).
#
# Formato: "# COMMAND ----------" separa celdas; "# MAGIC %md" / "%sql" cambian
# el lenguaje de la celda; `spark` y `display` existen solos en Databricks.
# (Esta celda de comentarios es del repaso; el notebook original empieza en la siguiente.)
# =============================================================================

# COMMAND ----------

# MAGIC %md
# MAGIC # Pipeline de la Champions League en Databricks
# MAGIC
# MAGIC Curso **Machine Learning Engineering (MLE/MLOps)** — Universidad del Valle de Guatemala
# MAGIC
# MAGIC Diego Linares · Andy Fuentes · Christian Echeverria · Diederich Solis
# MAGIC
# MAGIC Es el mismo pipeline del Ejercicio 3 (extracción, limpieza, entrenamiento y evaluación),
# MAGIC traído a Databricks. Lo que agrega este ambiente y no teníamos antes:
# MAGIC
# MAGIC - **Unity Catalog**: los datos limpios quedan como tabla consultable con SQL.
# MAGIC - **MLflow**: cada entrenamiento queda registrado con sus parámetros y métricas — justo el
# MAGIC   *registro de modelos* que en la Actividad 4 resolvimos a mano con un volumen.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Etapa 1 — Extracción
# MAGIC
# MAGIC Leemos el CSV directo del repositorio del Ejercicio 3, así no hay que subir archivos.

# COMMAND ----------

import pandas as pd

URL = (
    "https://raw.githubusercontent.com/DiegoLinares11/Ejecicio3-MLOPS/"
    "main/datos/champions_league_matches.csv"
)

crudo = pd.read_csv(URL)                       # 151 filas x 18 columnas
print(f"[extraer] {crudo.shape[0]} filas x {crudo.shape[1]} columnas")
display(crudo.head())                          # display() también acepta DataFrames de pandas

# COMMAND ----------

# MAGIC %md
# MAGIC ## Etapa 2 — Limpieza
# MAGIC
# MAGIC Lo que descubrimos en el Ejercicio 1: hay 7 filas vacías que separan jornadas, y las
# MAGIC columnas `score` y `winner` revelan el resultado (fuga de información).

# COMMAND ----------

OBJETIVO = "result"
FUGA = ["score", "winner"]
IRRELEVANTES = ["date", "venue", "referee"]

# Misma lógica que src/limpiar.py del Ejercicio 3 (aquí en pandas, no en Spark).
limpio = crudo.dropna(how="all").dropna(subset=[OBJETIVO])   # filas vacías y sin etiqueta
quitar = [c for c in FUGA + IRRELEVANTES if c in limpio.columns]
limpio = limpio.drop(columns=quitar).reset_index(drop=True)  # 144 filas

print(f"[limpiar] {len(crudo)} -> {len(limpio)} filas")
print(f"[limpiar] columnas descartadas: {quitar}")
display(limpio[OBJETIVO].value_counts().rename_axis("resultado").reset_index(name="partidos"))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Guardar como tabla en Unity Catalog
# MAGIC
# MAGIC Esto sí es propio de Databricks: los datos limpios dejan de ser un CSV suelto y quedan como
# MAGIC tabla, consultable con SQL desde cualquier notebook o dashboard del workspace.

# COMMAND ----------

TABLA = "workspace.default.partidos_limpios"   # catálogo.esquema.tabla (esquema "default")

# try/except: si el workspace no tiene permisos o UC no está habilitado, el notebook
# NO se cae; sigue con el DataFrame de pandas. Robustez para la entrega.
try:
    spark.createDataFrame(limpio).write.mode("overwrite").saveAsTable(TABLA)
    print(f"[tabla] guardada en {TABLA}")
except Exception as exc:
    print(f"[tabla] no se pudo guardar ({exc}).")
    print("[tabla] no importa: el resto del notebook sigue funcionando con el DataFrame.")

# COMMAND ----------

# MAGIC %sql
# MAGIC -- La misma tabla, ahora consultable con SQL
# MAGIC SELECT result AS resultado, COUNT(*) AS partidos
# MAGIC FROM workspace.default.partidos_limpios
# MAGIC GROUP BY result
# MAGIC ORDER BY partidos DESC

# COMMAND ----------

# MAGIC %md
# MAGIC ## Etapa 3 — Entrenamiento
# MAGIC
# MAGIC El mismo pipeline: convertir el texto a número, imputar, escalar, One-Hot y clasificar.
# MAGIC `mlflow.sklearn.autolog()` registra solo los parámetros, las métricas y el modelo.

# COMMAND ----------

import mlflow            # viene preinstalado en los runtimes de Databricks (en local NO está)
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 42

NUMERICAS = ["home_shots_on_target_pct", "away_shots_on_target_pct",
             "home_saves_pct", "away_saves_pct"]
PORCENTAJES = ["home_possession", "away_possession"]
RAZONES = ["home_shots_on_target", "away_shots_on_target", "home_saves", "away_saves"]
CATEGORICAS = ["home_team", "away_team"]


def convertir_texto_a_numero(df):
    """'63%' -> 63.0   y   '3 of 10' -> 3.0 (efectivos) y 10.0 (intentos)."""
    df = df.copy()
    for col in PORCENTAJES:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace("%", "", regex=False).str.strip(),
            errors="coerce",
        )
    for col in RAZONES:
        partes = df[col].astype(str).str.extract(r"(\d+)\s*of\s*(\d+)")
        df[col] = pd.to_numeric(partes[0], errors="coerce")
        df[col + "_intentos"] = pd.to_numeric(partes[1], errors="coerce")
    return df


def construir_pipeline():
    # Idéntico a src/entrenar.py: 14 numéricas (imputar mediana + escalar) y
    # 2 categóricas (imputar moda + One-Hot). Hiperparámetros ganadores de la Actividad 3.
    numericas = NUMERICAS + PORCENTAJES + RAZONES + [c + "_intentos" for c in RAZONES]
    preprocesamiento = ColumnTransformer(
        [
            ("num", Pipeline([("imputar", SimpleImputer(strategy="median")),
                              ("escalar", StandardScaler())]), numericas),
            ("cat", Pipeline([("imputar", SimpleImputer(strategy="most_frequent")),
                              ("onehot", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAS),
        ],
        remainder="drop",
    )
    modelo = LogisticRegression(C=0.541, class_weight="balanced",
                                max_iter=5000, random_state=SEED)
    return Pipeline([("preprocesamiento", preprocesamiento), ("modelo", modelo)])

# COMMAND ----------

datos = convertir_texto_a_numero(limpio)
y = datos[OBJETIVO]
X = datos.drop(columns=[OBJETIVO])

X_ent, X_pru, y_ent, y_pru = train_test_split(
    X, y, test_size=0.2, random_state=SEED, stratify=y      # 115 / 29, mismas que el Ejercicio 3
)

# AUTOLOG: a partir de aquí, cada .fit() de scikit-learn dentro de un run registra
# automáticamente: todos los hiperparámetros (log_params), métricas de ENTRENAMIENTO
# (training_accuracy_score, training_f1_score...), el modelo serializado con su
# entorno (log_model) y la firma de entrada/salida.
mlflow.sklearn.autolog()

# start_run abre un RUN dentro del experimento del notebook (en Databricks, cada
# notebook tiene un experimento por defecto). run_name es la etiqueta legible.
with mlflow.start_run(run_name="champions-logistica") as run:
    pipe = construir_pipeline().fit(X_ent, y_ent)
    print(f"[entrenar] entrenamiento={len(X_ent)}  prueba={len(X_pru)}")
    print(f"[entrenar] run de MLflow: {run.info.run_id}")   # id único del run
# Al salir del `with`, el run se cierra (status FINISHED). Ojo: las métricas de PRUEBA
# de la celda siguiente NO quedan en el run (se calculan fuera del with y sin
# mlflow.log_metric). Mejora posible: mlflow.log_metric("test_f1_macro", f1).

# COMMAND ----------

# MAGIC %md
# MAGIC ## Etapa 4 — Evaluación y compuerta de calidad
# MAGIC
# MAGIC Igual que en el Ejercicio 3: si el modelo no supera el mínimo **ni** le gana al modelo
# MAGIC trivial que siempre predice la clase mayoritaria, la celda falla a propósito.

# COMMAND ----------

from sklearn.dummy import DummyClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score

MINIMO_F1 = 0.40

pred = pipe.predict(X_pru)
acc = accuracy_score(y_pru, pred)
f1 = f1_score(y_pru, pred, average="macro")

# Diferencia sutil con evaluar.py: aquí el trivial se ajusta con ENTRENAMIENTO (X_ent, y_ent),
# allá con prueba. Como Home Win es mayoría en los dos, predice lo mismo.
tonto = DummyClassifier(strategy="most_frequent").fit(X_ent, y_ent)
pred_tonto = tonto.predict(X_pru)
acc_tonto = accuracy_score(y_pru, pred_tonto)
f1_tonto = f1_score(y_pru, pred_tonto, average="macro", zero_division=0)

print(f"[evaluar] accuracy = {acc:.3f}   (modelo trivial: {acc_tonto:.3f})")
print(f"[evaluar] f1_macro = {f1:.3f}   (modelo trivial: {f1_tonto:.3f})\n")
print(classification_report(y_pru, pred, digits=3, zero_division=0))

# LA COMPUERTA en versión notebook: en vez de `return 1` (código de salida), un
# `assert` que lanza AssertionError. Si este notebook corre como tarea de un Job,
# la excepción marca la tarea como FALLIDA y detiene las tareas que dependen de ella
# (el equivalente a `needs:` de GitHub Actions).
assert f1 >= MINIMO_F1, f"COMPUERTA: f1_macro {f1:.3f} por debajo del minimo {MINIMO_F1}"
assert f1 > f1_tonto, "COMPUERTA: el modelo no le gana al modelo trivial"
print(f"[evaluar] OK: supera el minimo ({MINIMO_F1}) y al modelo trivial")

# COMMAND ----------

display(
    pd.DataFrame(
        [
            {"metrica": "accuracy", "modelo": round(acc, 3), "trivial": round(acc_tonto, 3)},
            {"metrica": "f1_macro", "modelo": round(f1, 3), "trivial": round(f1_tonto, 3)},
        ]
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Qué ganamos al traerlo aquí
# MAGIC
# MAGIC | En el Ejercicio 3 | En Databricks |
# MAGIC |---|---|
# MAGIC | Los datos limpios eran un CSV en `artefactos/` | Una tabla en Unity Catalog, consultable con SQL |
# MAGIC | El modelo era un `.joblib` en un volumen | Un run de MLflow con parámetros, métricas y modelo versionado |
# MAGIC | Comparar dos corridas era abrir dos archivos | La pestaña **Experiments** las compara sola |
# MAGIC | El pipeline lo disparaba GitHub Actions | Se puede programar con **Jobs & Pipelines** |
# MAGIC
# MAGIC Lo que **no** cambia es la lógica: es el mismo preprocesamiento y el mismo modelo, con los
# MAGIC mismos hiperparámetros que ganaron en la Actividad 3.

# COMMAND ----------

# -----------------------------------------------------------------------------
# (Repaso, no estaba en el original) El paso siguiente sería REGISTRAR el modelo
# en el Model Registry de Unity Catalog, con versión y alias:
#
#   mlflow.set_registry_uri("databricks-uc")
#   version = mlflow.register_model(f"runs:/{run.info.run_id}/model",
#                                   "workspace.champions.clasificador_resultado")
#   from mlflow import MlflowClient
#   MlflowClient().set_registered_model_alias(
#       "workspace.champions.clasificador_resultado", "champion", version.version)
#
#   # y para usarlo:
#   modelo = mlflow.sklearn.load_model("models:/workspace.champions.clasificador_resultado@champion")
# -----------------------------------------------------------------------------
