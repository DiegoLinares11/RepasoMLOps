# %% [markdown]
# # 06 · Calibración de hiperparámetros con pipelines
#
# Partimos del pipeline del tema 05 (preprocesamiento de la Champions) y le agregamos un paso de
# **selección de variables** (`SelectKBest`). Después lo calibramos con los tres objetos de
# búsqueda que investigamos en la **Actividad 3**:
#
# | Objeto | Idea en una frase |
# |---|---|
# | `GridSearchCV` | prueba **todas** las combinaciones de una rejilla |
# | `RandomizedSearchCV` | **muestrea** `n_iter` combinaciones de distribuciones (y puede cambiar de modelo) |
# | `HalvingGridSearchCV` | arranca con todos los candidatos y pocos datos, y en cada ronda se queda con el mejor tercio |
#
# En la actividad original la rejilla completa tenía 96 combinaciones (55.7 s). Aquí usamos
# rejillas más chicas para que el notebook corra en menos de 2 minutos, pero con la misma
# lógica, y medimos tiempos reales.

# %% [markdown]
# ## 0. Configuración

# %%
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import loguniform, randint, uniform
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.experimental import enable_halving_search_cv  # noqa: F401  (habilita Halving*)
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import (GridSearchCV, HalvingGridSearchCV, RandomizedSearchCV,
                                     StratifiedKFold, cross_val_score, train_test_split)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.utils.validation import check_is_fitted

warnings.filterwarnings("ignore")
RANDOM_STATE = 42
RUTA = Path("../datos/champions_league_matches.csv")
pd.set_option("display.width", 140)
pd.set_option("display.max_colwidth", 120)
T0_NOTEBOOK = time.perf_counter()

# %% [markdown]
# ## 1. Lo previo: parámetro vs hiperparámetro
#
# - **Parámetro:** lo que el modelo **aprende** de los datos durante `fit`. Ejemplo: los
#   coeficientes de una regresión logística (`coef_`).
# - **Hiperparámetro:** lo que **tú decides antes** de entrenar y el modelo no puede aprender
#   solo. Ejemplo: `C` (cuánta regularización), `max_depth` de un árbol, `k` de `SelectKBest`.
#
# **Analogía:** en una receta, los hiperparámetros son la temperatura del horno y el tiempo
# (los eliges tú); los parámetros son cómo queda el pastel por dentro (resultado del horneado).
# Calibrar es probar varias temperaturas y quedarse con la que da el mejor pastel... probándolo
# con gente que **no** lo vio hornear.

# %%
X_mini = np.array([[1, 6], [2, 7], [7, 2], [8, 1]])
y_mini = np.array([0, 0, 1, 1])
for C in [0.01, 1.0, 100.0]:                     # hiperparámetro: lo elijo yo
    m = LogisticRegression(C=C).fit(X_mini, y_mini)
    print(f"C={C:<6} -> coef_ aprendidos = {m.coef_.round(3)}")   # parámetros: los aprende

# %% [markdown]
# **Interpretación:** el mismo dato con distinto `C` da coeficientes muy distintos. Con `C`
# chico (mucha regularización) los coeficientes quedan casi en cero; con `C` grande crecen. El
# modelo no puede elegir su propio `C` mirando el train (siempre "preferiría" el que mejor
# memoriza), por eso se elige con **validación cruzada**.

# %% [markdown]
# ## 2. Datos y pipeline (el mismo del tema 05, más `SelectKBest`)
#
# Repetimos el transformador personalizado y el `ColumnTransformer`. La única novedad es el paso
# `seleccion` entre el preprocesamiento y el modelo:
#
# ```
# preprocesamiento (ColumnTransformer, 12 -> 86 columnas)
#     -> seleccion (SelectKBest: se queda con las k mejores según el test F de ANOVA)
#     -> modelo (clasificador)
# ```
#
# **Por qué `SelectKBest`:** 72 de las 86 columnas son el One-Hot de los equipos y cada equipo
# aparece en pocos partidos: casi ruido. Con 115 filas de entrenamiento, arrastrar 86 columnas
# invita al sobreajuste. Cuántas conservar (`k`) **no se sabe de antemano**: es un
# hiperparámetro más, y se calibra junto al modelo.

# %%
NUMERICAS = ["home_shots_on_target_pct", "away_shots_on_target_pct",
             "home_saves_pct", "away_saves_pct"]
PORCENTAJES = ["home_possession", "away_possession"]
RAZONES = ["home_shots_on_target", "away_shots_on_target", "home_saves", "away_saves"]
CATEGORICAS = ["home_team", "away_team"]
FEATURES = NUMERICAS + PORCENTAJES + RAZONES + CATEGORICAS
TARGET = "result"


class TextoANumero(BaseEstimator, TransformerMixin):
    """'63%' -> 63.0  |  '3 of 10' -> 3.0 y 10.0 (igual que en el tema 05)."""

    PATRON_RAZON = r"^\s*(\d+)\s*of\s*(\d+)\s*$"

    def fit(self, X, y=None):
        X = pd.DataFrame(X)
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        self.n_features_in_ = X.shape[1]
        self.tipos_ = {c: ("porcentaje" if X[c].dropna().astype(str).str.endswith("%").all()
                           else "razon") for c in X.columns}
        return self

    def transform(self, X):
        check_is_fitted(self, "tipos_")
        X = pd.DataFrame(X)
        salida = []
        for col, tipo in self.tipos_.items():
            texto = X[col].astype("string")
            if tipo == "porcentaje":
                salida.append(pd.to_numeric(texto.str.replace("%", "", regex=False),
                                            errors="coerce"))
            else:
                partes = texto.str.extract(self.PATRON_RAZON)
                salida += [pd.to_numeric(partes[0], errors="coerce"),
                           pd.to_numeric(partes[1], errors="coerce")]
        return pd.concat(salida, axis=1).to_numpy(dtype=float, na_value=np.nan)

    def get_feature_names_out(self, input_features=None):
        nombres = []
        for col, tipo in self.tipos_.items():
            nombres += [f"{col}_pct"] if tipo == "porcentaje" else [f"{col}_hechos",
                                                                     f"{col}_intentos"]
        return np.asarray(nombres, dtype=object)


def construir_pipeline(modelo=None) -> Pipeline:
    def rama(*pasos):
        return Pipeline(list(pasos))
    prep = ColumnTransformer([
        ("numericas", rama(("imputar", SimpleImputer(strategy="median")),
                           ("escalar", StandardScaler())), NUMERICAS),
        ("porcentajes", rama(("parsear", TextoANumero()),
                             ("imputar", SimpleImputer(strategy="median")),
                             ("escalar", StandardScaler())), PORCENTAJES),
        ("razones", rama(("parsear", TextoANumero()),
                         ("imputar", SimpleImputer(strategy="median")),
                         ("escalar", StandardScaler())), RAZONES),
        ("categoricas", rama(("imputar", SimpleImputer(strategy="most_frequent")),
                             ("onehot", OneHotEncoder(handle_unknown="ignore",
                                                      sparse_output=False))), CATEGORICAS),
    ], remainder="drop")
    if modelo is None:
        modelo = RandomForestClassifier(n_estimators=300, random_state=RANDOM_STATE)
    return Pipeline([("preprocesamiento", prep),
                     ("seleccion", SelectKBest(score_func=f_classif, k="all")),
                     ("modelo", modelo)])


df = pd.read_csv(RUTA).dropna(how="all").dropna(subset=[TARGET]).reset_index(drop=True)
X, y = df[FEATURES], df[TARGET]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y)
print(f"{len(df)} partidos -> train={len(X_train)}  test={len(X_test)}")
print("Clases en train:", y_train.value_counts().to_dict())

# %% [markdown]
# **Regla de oro desde ya:** `X_test` / `y_test` **no se tocan** hasta la sección 9. Toda la
# calibración usa solo los 115 partidos de entrenamiento (con validación cruzada adentro).

# %% [markdown]
# ## 3. La sintaxis `paso__parametro`
#
# ¿Cómo le dice uno a `GridSearchCV` "prueba `max_depth` del bosque" si el bosque está metido
# dentro de un pipeline? Con **doble guion bajo**: `nombre_del_paso__hiperparametro`. Si hay
# pipelines anidados, se encadenan más niveles:
#
# ```
# modelo__max_depth                                   -> paso "modelo", hiperparámetro max_depth
# seleccion__k                                        -> paso "seleccion", hiperparámetro k
# preprocesamiento__numericas__imputar__strategy      -> ColumnTransformer -> rama -> paso -> hiperparámetro
# ```
#
# `get_params()` lista todas las llaves válidas:

# %%
pipe = construir_pipeline()
llaves = sorted(pipe.get_params().keys())
print("Total de llaves calibrables:", len(llaves))
for k in llaves:
    if k in {"modelo__max_depth", "modelo__class_weight", "seleccion__k",
             "preprocesamiento__numericas__imputar__strategy",
             "preprocesamiento__categoricas__onehot__handle_unknown"}:
        print("  ", k, "=", pipe.get_params()[k])

# %% [markdown]
# Y con `set_params` se cambian igual. Esto es exactamente lo que hace `GridSearchCV` por dentro
# con cada combinación (sobre una copia del pipeline):

# %%
copia = construir_pipeline().set_params(seleccion__k=15, modelo__max_depth=6)
print(copia.named_steps["seleccion"].k, copia.named_steps["modelo"].max_depth)

# %% [markdown]
# ## 4. La métrica y la validación cruzada
#
# **`StratifiedKFold(5)`**: parte los 115 partidos en 5 bloques que conservan la proporción de
# clases. Cada combinación se entrena 5 veces (4 bloques) y se valida en el bloque restante.
# Con solo 20 empates en train, un `KFold` normal podría dejar un fold casi sin empates.
#
# **`f1_macro` y no `accuracy`:** con clases 57 / 38 / 20 en train, el `accuracy` premia acertar
# la clase mayoritaria. `f1_macro` calcula el F1 de **cada** clase y los promedia **sin
# ponderar**: un modelo que ignora los empates saca F1 = 0 en esa clase y se hunde el
# promedio. Veámoslo con un modelo tonto:

# %%
CV = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
SCORING = "f1_macro"

tonto = DummyClassifier(strategy="most_frequent")
acc_tonto = cross_val_score(tonto, X_train, y_train, cv=CV, scoring="accuracy").mean()
f1_tonto = cross_val_score(tonto, X_train, y_train, cv=CV, scoring="f1_macro").mean()
print(f"Modelo tonto (siempre Home Win): accuracy={acc_tonto:.3f}  f1_macro={f1_tonto:.3f}")

inicio = time.perf_counter()
base = cross_val_score(construir_pipeline(), X_train, y_train, cv=CV, scoring=SCORING, n_jobs=-1)
print(f"Pipeline SIN calibrar (RF por defecto, k='all'): f1_macro CV = {base.mean():.3f} "
      f"(+/- {base.std():.3f})  [{time.perf_counter() - inicio:.1f} s]")
print("Por fold:", base.round(3))

# %% [markdown]
# **Interpretación:** el modelo tonto saca casi 0.50 de accuracy sin aprender nada, pero su
# `f1_macro` es ~0.22: la métrica correcta lo delata. El pipeline sin calibrar da **0.508** de
# `f1_macro` en CV, el mismo punto de partida que reportó la Actividad 3 (0.508 ± 0.037). Ese
# es el número a mejorar.

# %% [markdown]
# ## 5. `GridSearchCV`: búsqueda exhaustiva
#
# Rejilla sobre el bosque aleatorio. Mezcla a propósito hiperparámetros de **preprocesamiento**
# (`seleccion__k`) y de **modelo**, porque interactúan: cuántas variables conviene conservar
# depende de qué tan profundo sea el árbol.
#
# | Hiperparámetro | Valores | Por qué |
# |---|---|---|
# | `seleccion__k` | 15, 30, `"all"` | ¿sobran columnas de equipos? |
# | `modelo__max_depth` | `None`, 6 | **la** perilla de sobreajuste del árbol |
# | `modelo__min_samples_leaf` | 1, 3 | con 1, una hoja puede sostenerse en un solo partido raro |
# | `modelo__class_weight` | `None`, `"balanced"` | respuesta directa al desbalance: fallar un empate cuesta más |
#
# 3 × 2 × 2 × 2 = **24 combinaciones × 5 folds = 120 ajustes**. Fijamos `n_estimators=200`
# porque en la Actividad 3 medimos que 200 y 400 daban lo mismo (y 200 es más barato).
#
# - `refit=True`: al terminar, reentrena la mejor combinación con los 115 partidos completos y la
#   deja en `best_estimator_`, lista para predecir.
# - `return_train_score=True`: guarda también el puntaje en entrenamiento, para ver sobreajuste.
# - `n_jobs=-1`: usa todos los núcleos.

# %%
REJILLA = {
    "seleccion__k": [15, 30, "all"],
    "modelo__max_depth": [None, 6],
    "modelo__min_samples_leaf": [1, 3],
    "modelo__class_weight": [None, "balanced"],
}
pipe_rf = construir_pipeline(RandomForestClassifier(n_estimators=200, random_state=RANDOM_STATE))

grid = GridSearchCV(pipe_rf, REJILLA, scoring=SCORING, cv=CV, n_jobs=-1,
                    refit=True, return_train_score=True)
inicio = time.perf_counter()
grid.fit(X_train, y_train)
t_grid = time.perf_counter() - inicio

print(f"Combinaciones: {len(grid.cv_results_['params'])}   Tiempo: {t_grid:.1f} s")
print(f"Mejor f1_macro en CV: {grid.best_score_:.3f}")
print("Mejores hiperparámetros:", grid.best_params_)

# %% [markdown]
# ### 5.1 Leer `cv_results_`
#
# `cv_results_` es un diccionario con una fila por combinación: puntaje medio en validación, su
# desviación, el ranking, el puntaje en entrenamiento y los parámetros. En un DataFrame ordenado
# por `rank_test_score` se lee de un vistazo:

# %%
def tabla_cv(search, top=8):
    res = pd.DataFrame(search.cv_results_)
    cols = ["rank_test_score", "mean_test_score", "std_test_score"]
    if "mean_train_score" in res:
        cols.append("mean_train_score")
    tabla = res[cols + ["params"]].sort_values("rank_test_score").head(top).copy()
    if "mean_train_score" in tabla:
        tabla["brecha"] = tabla["mean_train_score"] - tabla["mean_test_score"]
    return tabla.round(3).reset_index(drop=True)


tabla_cv(grid)

# %% [markdown]
# **Interpretación:** la columna `brecha` (entrenamiento − validación) es la señal de
# **sobreajuste**. Las combinaciones con `min_samples_leaf=1` llegan a 0.994–1.000 en
# entrenamiento: el bosque memoriza los 115 partidos y la brecha sube a 0.43–0.45. Con
# `min_samples_leaf=3` el train baja a ~0.91–0.94, la brecha a ~0.35–0.39, y además quedan
# arriba en validación. Las 8 mejores usan `class_weight="balanced"`. Las dos primeras empatan
# en 0.562 (con `max_depth` 6 o `None`): cuando las hojas ya tienen mínimo 3 partidos, limitar la
# profundidad casi no cambia nada. Fíjate también en `std_test_score` (~0.05): con folds de 23
# partidos, diferencias de 0.01 entre las primeras filas están muy por dentro del ruido.
#
# ¿Qué hiperparámetro pesó de verdad? Promediamos `mean_test_score` por cada valor:

# %%
res_grid = pd.DataFrame(grid.cv_results_)
for p in REJILLA:
    col = res_grid[f"param_{p}"].astype(object)
    etiqueta = col.where(col.notna(), "None").map(str)       # None -> "None" para agrupar
    efecto = res_grid.groupby(etiqueta)["mean_test_score"].mean()
    print(f"{p:<26}", efecto.round(3).to_dict())

# %% [markdown]
# **Interpretación:** el efecto más grande es `class_weight`: `"balanced"` promedia 0.549 contra
# 0.516 de `None` (fallar un empate cuesta más, y `f1_macro` lo premia). `max_depth` (0.536 vs
# 0.529) y `min_samples_leaf` (0.534 vs 0.531) casi no mueven el promedio. `seleccion__k`
# repite en promedio el patrón de la Actividad 3: recortar ayuda (30 → 0.539, 15 → 0.534,
# `all` → 0.525; allá fue 0.525 / 0.523 / 0.509, y `n_estimators` e imputación resultaron
# irrelevantes). Aun así, la mejor combinación individual usó `k="all"`: el promedio por valor y
# el máximo cuentan historias distintas, y con diferencias tan chicas manda el ruido.
# Saber qué hiperparámetro **no** importa vale tanto como saber cuál sí: permite fijarlo en el
# valor barato con evidencia.

# %% [markdown]
# ## 6. `RandomizedSearchCV`: muestrear en vez de recorrer, y comparar familias
#
# Dos ideas clave:
#
# 1. **Distribuciones en vez de listas.** Para `C` de la regresión logística no sabemos si el
#    bueno es 0.001 o 50: cambia en **órdenes de magnitud**. `loguniform(1e-3, 1e2)` muestrea
#    uniforme en escala logarítmica (tan probable caer entre 0.001 y 0.01 como entre 10 y 100).
#    `randint(a, b)` da enteros y `uniform(loc, scale)` decimales en `[loc, loc + scale]`.
# 2. **Una lista de diccionarios** = varios espacios. Como el clasificador es un paso más del
#    pipeline (`modelo`), se puede reemplazar entero: `"modelo": [SVC()]`. La búsqueda primero
#    elige un diccionario al azar y luego muestrea dentro de él.
#
# Con `n_iter=40` exploramos cuatro familias en un espacio que, en rejilla, tendría miles de
# combinaciones.

# %%
print("5 muestras de loguniform(1e-3, 1e2):",
      loguniform(1e-3, 1e2).rvs(5, random_state=RANDOM_STATE).round(4))

comun = {"seleccion__k": [10, 20, 40, "all"]}
ESPACIO = [
    {**comun,
     "modelo": [LogisticRegression(max_iter=5000, random_state=RANDOM_STATE)],
     "modelo__C": loguniform(1e-3, 1e2),
     "modelo__class_weight": [None, "balanced"]},
    {**comun,
     "modelo": [SVC(random_state=RANDOM_STATE)],
     "modelo__C": loguniform(1e-2, 1e2),
     "modelo__gamma": loguniform(1e-4, 1e0),
     "modelo__kernel": ["rbf", "linear"],
     "modelo__class_weight": [None, "balanced"]},
    {**comun,
     "modelo": [RandomForestClassifier(random_state=RANDOM_STATE)],
     "modelo__n_estimators": randint(100, 300),
     "modelo__max_depth": [None, 4, 6, 10],
     "modelo__min_samples_leaf": randint(1, 6),
     "modelo__class_weight": [None, "balanced"]},
    {**comun,
     "modelo": [HistGradientBoostingClassifier(random_state=RANDOM_STATE)],
     "modelo__learning_rate": uniform(0.02, 0.28),
     "modelo__max_iter": randint(50, 200),
     "modelo__min_samples_leaf": randint(5, 25)},
]

rnd = RandomizedSearchCV(construir_pipeline(), ESPACIO, n_iter=40, scoring=SCORING, cv=CV,
                         n_jobs=-1, random_state=RANDOM_STATE, refit=True,
                         return_train_score=True)
inicio = time.perf_counter()
rnd.fit(X_train, y_train)
t_rnd = time.perf_counter() - inicio

familia_ganadora = type(rnd.best_estimator_.named_steps["modelo"]).__name__
print(f"Combinaciones: {len(rnd.cv_results_['params'])}   Tiempo: {t_rnd:.1f} s")
print(f"Mejor f1_macro en CV: {rnd.best_score_:.3f}   Familia ganadora: {familia_ganadora}")
for k, v in sorted(rnd.best_params_.items()):
    if k != "modelo":
        print(f"  {k} = {round(v, 4) if isinstance(v, float) else v}")

# %%
res_rnd = pd.DataFrame(rnd.cv_results_)
res_rnd["familia"] = [type(p["modelo"]).__name__ for p in res_rnd["params"]]
(res_rnd.groupby("familia")["mean_test_score"]
        .agg(intentos="count", mejor="max", media="mean")
        .sort_values("mejor", ascending=False).round(3))

# %% [markdown]
# **Interpretación:** con la misma validación cruzada para todas las familias, aquí ganó un
# **SVC con kernel lineal** (`f1_macro` 0.687, `C`≈0.63, `class_weight="balanced"`, `k=40`; el
# `gamma` muestreado no se usa con kernel lineal). Le siguen LogisticRegression (0.601),
# HistGradientBoosting (0.594) y RandomForest (0.579). Mira la columna `media`: el SVC tiene el
# mejor máximo pero la peor media (0.379), porque es muy sensible a `C`/`gamma` y varias muestras
# cayeron en zonas malas; la regresión logística es la más estable (0.553).
#
# La conclusión coincide con la Actividad 3, donde ganó la regresión logística (0.619; SVC
# 0.612, HistGradientBoosting 0.561, RandomForest 0.556): con 115 filas y 86 columnas, un
# **modelo lineal regularizado** le gana a los árboles. Y `GridSearchCV` nunca lo habría
# encontrado, porque estaba encerrado en el vecindario del Random Forest.

# %% [markdown]
# ## 7. `HalvingGridSearchCV`: mitades sucesivas (*successive halving*)
#
# **Analogía:** un torneo con eliminatorias. En la primera ronda juegan **todos** los candidatos,
# pero con poco tiempo (pocos datos). Solo el mejor tercio (`factor=3`) pasa a la siguiente
# ronda, donde juega con más datos. Así no se gasta cómputo completo en combinaciones que desde
# el inicio se ven malas.
#
# - Sigue siendo **experimental**: hay que importar
#   `from sklearn.experimental import enable_halving_search_cv` **antes** de
#   `from sklearn.model_selection import HalvingGridSearchCV` (lo hicimos en la configuración).
# - El "recurso" por defecto es `n_samples` (cuántos partidos se usan para entrenar).
#
# Usamos **la misma rejilla de 24** que `GridSearchCV` para comparar directo.

# %%
halving = HalvingGridSearchCV(pipe_rf, REJILLA, factor=3, scoring=SCORING, cv=CV, n_jobs=-1,
                              random_state=RANDOM_STATE, refit=True)
inicio = time.perf_counter()
halving.fit(X_train, y_train)
t_halving = time.perf_counter() - inicio

print(f"Rondas (n_iterations_)        : {halving.n_iterations_}")
print(f"Candidatos por ronda          : {list(halving.n_candidates_)}")
print(f"Partidos por ronda (recursos) : {list(halving.n_resources_)}")
print(f"Tiempo: {t_halving:.1f} s   Mejor f1_macro en CV: {halving.best_score_:.3f}")
print("Mejores hiperparámetros:", halving.best_params_)

# %% [markdown]
# **Interpretación:** ronda 1: los 24 candidatos con 30 partidos; ronda 2: sobreviven 8 (un
# tercio) con 90 partidos. En la Actividad 3 fue igual: 96 → 32 candidatos con 30 → 90 partidos.
# El mínimo de 30 no es casualidad: scikit-learn exige al menos `2 × n_splits × n_clases` =
# 2 × 5 × 3 = 30 muestras para que cada fold tenga de todas las clases.
#
# Dos detalles importantes:
#
# - Eligió **otra** combinación que la rejilla (`class_weight=None`, `max_depth=6`,
#   `min_samples_leaf=1`, `k=15`). Con 30 partidos (6 por fold de validación) la primera ronda es
#   muy ruidosa, y un buen candidato puede quedar eliminado temprano.
# - Su `best_score_` (0.615) se mide en la **última** ronda, con 90 partidos y no con 115, así que
#   **no** es directamente comparable con el 0.562 de `GridSearchCV`.

# %% [markdown]
# ## 8. Comparación de los tres objetos

# %%
def ajustes(search):
    """Cuántos modelos se entrenaron (combinaciones evaluadas × folds)."""
    return len(search.cv_results_["params"]) * CV.get_n_splits()


comparacion = pd.DataFrame([
    {"objeto": "Sin calibrar", "combinaciones": 1, "ajustes": 5,
     "segundos": np.nan, "mejor_f1_macro_cv": base.mean()},
    {"objeto": "GridSearchCV", "combinaciones": len(grid.cv_results_["params"]),
     "ajustes": ajustes(grid), "segundos": t_grid, "mejor_f1_macro_cv": grid.best_score_},
    {"objeto": "RandomizedSearchCV", "combinaciones": len(rnd.cv_results_["params"]),
     "ajustes": ajustes(rnd), "segundos": t_rnd, "mejor_f1_macro_cv": rnd.best_score_},
    {"objeto": "HalvingGridSearchCV", "combinaciones": len(halving.cv_results_["params"]),
     "ajustes": ajustes(halving), "segundos": t_halving,
     "mejor_f1_macro_cv": halving.best_score_},
]).round(3)
comparacion

# %% [markdown]
# **Interpretación:** lee la tabla en tres ejes: **cuántos modelos** se entrenaron, **cuánto
# tardó** y **qué tan bueno** fue lo mejor que encontró.
#
# - `RandomizedSearchCV` entrenó más modelos (200 vs 120) en un tiempo parecido al de la rejilla
#   (alrededor de 10–12 s cada una en esta máquina de 4 núcleos; los segundos exactos cambian
#   un poco en cada corrida), porque muchas de sus muestras son modelos lineales baratos, y
#   encontró el mejor puntaje (0.687 vs 0.562).
# - `HalvingGridSearchCV` tardó **más** que la rejilla (alrededor de 15 s), aunque evaluó la misma
#   rejilla. Halving ahorra cuando el costo de entrenar crece con el número de muestras;
#   con 115 filas, entrenar 200 árboles con 30 o con 90 partidos cuesta casi lo mismo (domina el
#   costo fijo), y además paga dos rondas. En la Actividad 3 pasó lo mismo: 60.3 s contra 55.7 s.
#   Halving brilla con datasets grandes, no con 144 partidos.
# - Sus 32 "combinaciones" son 24 + 8: cada sobreviviente se vuelve a evaluar en la ronda
#   siguiente.
#
# Para referencia, los números originales de la Actividad 3 (`act3-demo`):
#
# | Objeto | Combinaciones | Tiempo | Mejor `f1_macro` CV |
# |---|---|---|---|
# | Sin calibrar | 1 | — | 0.508 |
# | GridSearchCV | 96 | 55.7 s | 0.563 |
# | **RandomizedSearchCV** | **60** | **17.0 s** | **0.619** |
# | HalvingGridSearchCV | 128 | 60.3 s | 0.594 |

# %% [markdown]
# ## 9. Elegir por CV, evaluar en test **una sola vez**
#
# El ganador se elige por `best_score_` (validación cruzada), **nunca** mirando el test. Como
# usamos `refit=True`, `best_estimator_` ya es el pipeline completo reentrenado con los 115
# partidos: no hay que volver a llamar `fit`.
#
# ¿Por qué solo una vez? Si pruebas los tres finalistas en test y te quedas con el que mejor
# salió, el test se convirtió en otro conjunto de validación y su número deja de ser una
# estimación honesta.

# %%
busquedas = {"GridSearchCV": grid, "RandomizedSearchCV": rnd, "HalvingGridSearchCV": halving}
ganadora = max(busquedas, key=lambda n: busquedas[n].best_score_)
final = busquedas[ganadora].best_estimator_
print(f"Búsqueda ganadora (por CV): {ganadora}  ->  "
      f"{type(final.named_steps['modelo']).__name__}, "
      f"k={final.named_steps['seleccion'].k}")

y_pred = final.predict(X_test)
tonto_test = DummyClassifier(strategy="most_frequent").fit(X_train, y_train).predict(X_test)
print(f"\nModelo final en TEST : accuracy={accuracy_score(y_test, y_pred):.3f}  "
      f"f1_macro={f1_score(y_test, y_pred, average='macro'):.3f}")
print(f"Baseline en TEST     : accuracy={accuracy_score(y_test, tonto_test):.3f}  "
      f"f1_macro={f1_score(y_test, tonto_test, average='macro'):.3f}\n")
print(classification_report(y_test, y_pred, digits=3, zero_division=0))

# %% [markdown]
# **Interpretación:** el modelo final (SVC lineal) saca **accuracy 0.690 y `f1_macro` 0.631** en
# test, contra 0.483 y 0.217 del baseline. Detecta 2 de los 5 empates (recall 0.400) y todas las
# victorias visitantes. Son exactamente los números del modelo final de la Actividad 3
# (`LogisticRegression(C=0.541, class_weight="balanced")`, `k=40`): dos modelos lineales
# regularizados con las mismas 40 variables terminaron con la misma matriz de confusión.
#
# Fíjate que el test (0.631) quedó **por debajo** del `best_score_` de CV (0.687). No es mala
# suerte: es lo esperado, como muestra la sección siguiente. Y con 29 partidos de prueba, cada
# acierto vale 3.4 puntos de accuracy, así que diferencias de uno o dos partidos son ruido.

# %% [markdown]
# ## 10. Sobreajuste a la validación: por qué `best_score_` es optimista
#
# `best_score_` es el **máximo** de muchos intentos medidos sobre las **mismas** particiones.
# Aunque ningún candidato sea bueno, el máximo de muchos números ruidosos sale alto por pura
# suerte. Experimento extremo: 100 "modelos" que **adivinan al azar** (`DummyClassifier`
# estratificado con 100 semillas distintas). Ninguno aprende nada.

# %%
azar = GridSearchCV(DummyClassifier(strategy="stratified"),
                    {"random_state": list(range(100))}, scoring=SCORING, cv=CV, n_jobs=-1)
azar.fit(X_train, y_train)
puntajes_azar = azar.cv_results_["mean_test_score"]
pred_azar = azar.best_estimator_.predict(X_test)
print(f"f1_macro CV promedio de los 100 adivinos : {puntajes_azar.mean():.3f}")
print(f"best_score_ (el adivino 'ganador')       : {azar.best_score_:.3f}")
print(f"Ese mismo adivino en TEST                : "
      f"{f1_score(y_test, pred_azar, average='macro'):.3f}")

# %% [markdown]
# **Interpretación:** los 100 adivinos promedian 0.317 de `f1_macro` en CV (lo esperable al
# azar con tres clases). El "ganador" marcó 0.447, muy por encima, pero en test sacó **0.109**:
# su ventaja era pura suerte en esas cinco particiones. Con modelos reales pasa lo mismo en
# menor grado, y crece con el número de candidatos que pruebas. Por eso:
#
# - el `best_score_` **no** se reporta como desempeño;
# - el test se usa **una vez**, al final;
# - para una estimación honesta del **procedimiento completo** (buscar + entrenar) se usa
#   **validación cruzada anidada**: la búsqueda se repite dentro de cada fold externo.
#
# Una versión rápida, con una rejilla chica de regresión logística:

# %%
interna = GridSearchCV(
    construir_pipeline(LogisticRegression(max_iter=5000, random_state=RANDOM_STATE)),
    {"modelo__C": [0.01, 0.1, 1, 10], "modelo__class_weight": [None, "balanced"]},
    scoring=SCORING, cv=CV, n_jobs=1)
inicio = time.perf_counter()
anidada = cross_val_score(interna, X_train, y_train, cv=CV, scoring=SCORING, n_jobs=-1)
interna.fit(X_train, y_train)
print(f"best_score_ de la búsqueda (optimista): {interna.best_score_:.3f}")
print(f"CV anidada (estimación honesta)       : {anidada.mean():.3f} (+/- {anidada.std():.3f})"
      f"   [{time.perf_counter() - inicio:.1f} s]")

# %% [markdown]
# **Interpretación:** la CV anidada mide qué tan bien generaliza "elegir el mejor `C` y
# entrenar", no solo el mejor `C` ya elegido. Aquí la diferencia es mínima (0.608 vs 0.605)
# porque la búsqueda interna solo tenía 8 candidatos muy parecidos entre sí: hay poco espacio
# para el optimismo. Ojo con la desviación (± 0.091): con 23 partidos por fold externo la
# estimación es ruidosa. En la Actividad 3, con la rejilla de Random Forest, la CV anidada dio
# **0.541** contra un `best_score_` de 0.563: esa diferencia es el optimismo que mete la propia
# búsqueda. A más candidatos (como los 100 adivinos o las 40 muestras de la búsqueda aleatoria),
# más optimismo.

# %%
print(f"Tiempo total del notebook: {time.perf_counter() - T0_NOTEBOOK:.1f} s")

# %% [markdown]
# ## Resumen
#
# - **Parámetros** se aprenden en `fit` (`coef_`); **hiperparámetros** se eligen antes (`C`,
#   `max_depth`, `k`) y se calibran con validación cruzada.
# - En un pipeline cada hiperparámetro se nombra `paso__parametro` (y se anida:
#   `preprocesamiento__numericas__imputar__strategy`). Así se calibran **juntos** el
#   preprocesamiento (`seleccion__k`) y el modelo, reajustando todo dentro de cada fold.
# - `StratifiedKFold(5)` + `f1_macro`: el modelo tonto saca ~0.50 de accuracy pero ~0.22 de
#   `f1_macro`; el pipeline sin calibrar parte de 0.508.
# - `GridSearchCV` recorre todo (24 combinaciones aquí, 96 en la actividad); `RandomizedSearchCV`
#   muestrea distribuciones de `scipy.stats` y puede comparar **familias de modelos** en una sola
#   búsqueda; `HalvingGridSearchCV` (experimental) elimina candidatos por rondas con pocos datos.
# - `cv_results_` ordenado por `rank_test_score` muestra el ranking, la desviación y la brecha
#   train − validación (sobreajuste); `refit=True` deja el ganador en `best_estimator_`.
# - `best_score_` es optimista (100 adivinos al azar lo demuestran); se elige por CV, se evalúa
#   en test **una sola vez**, y la CV anidada da la estimación honesta.
