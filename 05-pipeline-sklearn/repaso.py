# %% [markdown]
# # 05 · Pipeline de scikit-learn, paso a paso
#
# Vamos a reconstruir el pipeline de la **Actividad 1**: preparar los datos de la Champions y
# predecir `result` (Home Win / Away Win / Draw). El original sacó **accuracy 0.724** en prueba,
# con 151 → 144 filas y una partición train = 115 / test = 29. Queremos llegar al mismo número
# entendiendo cada pieza.
#
# Ruta del notebook:
#
# 1. Lo previo: qué es un *transformer* y qué es un *estimator* (con un ejemplo de juguete).
# 2. Extraer, filtrar y separar (estratificado).
# 3. Un **transformador personalizado** que convierte `'63%'` y `'3 of 10'` a números.
# 4. `ColumnTransformer` por tipo de variable + `Pipeline` con el modelo.
# 5. Diagrama en texto, `get_feature_names_out` y `set_output`.
# 6. **Fuga de datos**: escalar fuera del pipeline vs dentro (y un ejemplo donde la fuga es enorme).
# 7. Por qué empaquetar: la función `main()` que se vuelve el comando `act1-demo`.

# %% [markdown]
# ## 0. Configuración

# %%
import tempfile
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn import set_config
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.validation import check_is_fitted

warnings.filterwarnings("ignore")
RANDOM_STATE = 42
RUTA = Path("../datos/champions_league_matches.csv")
pd.set_option("display.width", 120)

import sklearn
print("scikit-learn", sklearn.__version__)

# %% [markdown]
# ## 1. Lo previo: transformer vs estimator
#
# Todo en scikit-learn sigue el mismo "contrato":
#
# | Tipo | Métodos | Qué hace | Ejemplo |
# |---|---|---|---|
# | **Transformer** | `fit` + `transform` | aprende algo de los datos y luego los **cambia** | `StandardScaler`, `SimpleImputer`, `OneHotEncoder` |
# | **Estimator / predictor** | `fit` + `predict` | aprende y luego **predice** una etiqueta | `RandomForestClassifier`, `LogisticRegression` |
#
# **Analogía:** `fit` es estudiar; `transform`/`predict` es hacer el examen. Lo que se "aprende"
# en `fit` queda guardado en atributos que **terminan en guion bajo** (`mean_`, `scale_`,
# `classes_`). Veámoslo con números chiquitos:

# %%
juguete_train = pd.DataFrame({"posesion": [40.0, 50.0, 60.0]})
juguete_test = pd.DataFrame({"posesion": [70.0]})

escalador = StandardScaler()
escalador.fit(juguete_train)                  # "estudia": calcula media y desviación
print("media aprendida (mean_)  :", escalador.mean_)
print("desviación (scale_)      :", escalador.scale_.round(3))
print("train transformado       :", escalador.transform(juguete_train).ravel().round(3))
print("test transformado (70)   :", escalador.transform(juguete_test).ravel().round(3))

# %% [markdown]
# **Interpretación:** el escalador aprendió media 50 y desviación 8.165 **solo del train**. Al
# transformar el 70 de prueba usa esa misma media: (70 − 50) / 8.165 = 2.449. Nunca recalcula
# con los datos de prueba. Esa es la idea que evita la fuga de información.
#
# Un estimator funciona igual, pero termina en `predict`:

# %%
X_juguete = pd.DataFrame({"tiros_puerta_local": [1, 2, 7, 8], "tiros_puerta_visita": [6, 7, 2, 1]})
y_juguete = ["Away Win", "Away Win", "Home Win", "Home Win"]
modelo_juguete = LogisticRegression().fit(X_juguete, y_juguete)
print("clases aprendidas (classes_):", modelo_juguete.classes_)
print("predicción para 9 vs 1     :", modelo_juguete.predict(pd.DataFrame(
    {"tiros_puerta_local": [9], "tiros_puerta_visita": [1]})))

# %% [markdown]
# Un **`Pipeline`** encadena varios transformers y termina en un estimator. Se comporta como
# **un solo estimator**: `pipe.fit(X, y)` hace `fit_transform` en cada paso y `fit` en el último;
# `pipe.predict(X)` hace `transform` en cada paso (con lo aprendido) y `predict` al final.

# %% [markdown]
# ## 2. Extraer, filtrar y separar
#
# Mismas decisiones que la Actividad 1 (y que el Ejercicio 1):
#
# - quitar las 7 filas vacías y las filas sin `result`;
# - quitar `score` y `winner` porque **revelan el resultado** (fuga: el modelo sacaría 100 % y
#   no serviría antes de que termine el partido);
# - quitar `date`, `venue`, `referee` porque no aportan.

# %%
NUMERICAS = ["home_shots_on_target_pct", "away_shots_on_target_pct",
             "home_saves_pct", "away_saves_pct"]                       # ya son float
PORCENTAJES = ["home_possession", "away_possession"]                   # '63%'
RAZONES = ["home_shots_on_target", "away_shots_on_target",
           "home_saves", "away_saves"]                                 # '3 of 10'
CATEGORICAS = ["home_team", "away_team"]
FEATURES = NUMERICAS + PORCENTAJES + RAZONES + CATEGORICAS
FUGA = ["score", "winner"]
IRRELEVANTES = ["date", "venue", "referee"]
TARGET = "result"


def extraer_datos(ruta=RUTA) -> pd.DataFrame:
    return pd.read_csv(ruta)


def filtrar_datos(df: pd.DataFrame) -> pd.DataFrame:
    return (df.dropna(how="all")
              .dropna(subset=[TARGET])
              .drop(columns=FUGA + IRRELEVANTES)
              .reset_index(drop=True))


crudo = extraer_datos()
df = filtrar_datos(crudo)
print("Crudo   :", crudo.shape)
print("Filtrado:", df.shape)
print(df[TARGET].value_counts())

# %% [markdown]
# **Separación estratificada.** Con `stratify=y`, train y test conservan la proporción de las
# tres clases. ¿Por qué importa? `Draw` es solo el 17 %: con una partición al azar podría tocar
# un test con 2 empates o con 8, y la métrica dependería de la suerte del corte.

# %%
X, y = df[FEATURES], df[TARGET]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y)

print(f"train={len(X_train)}  test={len(X_test)}")
print(pd.DataFrame({"total": y.value_counts(normalize=True),
                    "train": y_train.value_counts(normalize=True),
                    "test": y_test.value_counts(normalize=True)}).round(3))

# %% [markdown]
# **Interpretación:** 144 partidos → 115 de entrenamiento y 29 de prueba, igual que la
# Actividad 1. Las proporciones casi no cambian entre total, train y test (Home Win ~0.49,
# Away Win ~0.33, Draw ~0.17): eso es lo que garantiza `stratify`.

# %% [markdown]
# ## 3. Transformador personalizado: `'63%'` y `'3 of 10'` → números
#
# Ningún transformer de scikit-learn sabe leer `'3 of 10'`. Podríamos limpiarlo con pandas
# antes (como en el tema 04), pero entonces la limpieza **viviría fuera del modelo**: el día que
# llegue un partido nuevo, alguien tendría que acordarse de repetirla igual. Si la metemos en el
# pipeline, viaja con el modelo.
#
# Para crear uno propio se hereda de dos clases:
#
# - **`BaseEstimator`**: da `get_params`/`set_params` gratis (lo necesitan `GridSearchCV` y
#   `clone`). Regla: el `__init__` solo guarda sus argumentos, sin lógica.
# - **`TransformerMixin`**: da `fit_transform` gratis (llama `fit` y luego `transform`) y
#   habilita `set_output`.
#
# Nuestro `TextoANumero` **aprende en `fit`** qué tipo es cada columna (porcentaje o razón) y lo
# guarda en `tipos_`. En `transform` aplica la conversión: un porcentaje da 1 columna, una razón
# da 2 (hechos e intentos).

# %%
class TextoANumero(BaseEstimator, TransformerMixin):
    """'63%' -> 63.0  |  '3 of 10' -> 3.0 (hechos) y 10.0 (intentos)."""

    PATRON_RAZON = r"^\s*(\d+)\s*of\s*(\d+)\s*$"

    def fit(self, X, y=None):
        X = pd.DataFrame(X)
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        self.n_features_in_ = X.shape[1]
        self.tipos_ = {}
        for col in X.columns:
            muestra = X[col].dropna().astype(str)
            if muestra.str.strip().str.endswith("%").all():
                self.tipos_[col] = "porcentaje"
            elif muestra.str.match(self.PATRON_RAZON).all():
                self.tipos_[col] = "razon"
            else:
                raise ValueError(f"No sé convertir la columna {col!r}")
        return self

    def transform(self, X):
        check_is_fitted(self, "tipos_")
        X = pd.DataFrame(X)
        salida = []
        for col, tipo in self.tipos_.items():
            texto = X[col].astype("string")
            if tipo == "porcentaje":
                salida.append(pd.to_numeric(texto.str.replace("%", "", regex=False).str.strip(),
                                            errors="coerce"))
            else:
                partes = texto.str.extract(self.PATRON_RAZON)
                salida.append(pd.to_numeric(partes[0], errors="coerce"))
                salida.append(pd.to_numeric(partes[1], errors="coerce"))
        return pd.concat(salida, axis=1).to_numpy(dtype=float, na_value=np.nan)

    def get_feature_names_out(self, input_features=None):
        check_is_fitted(self, "tipos_")
        nombres = []
        for col, tipo in self.tipos_.items():
            nombres += [f"{col}_pct"] if tipo == "porcentaje" else [f"{col}_hechos",
                                                                     f"{col}_intentos"]
        return np.asarray(nombres, dtype=object)


ejemplo = pd.DataFrame({"home_possession": ["63%", "38%", None],
                        "home_saves": ["4 of 8", "0 of 0", "2 of 3"]})
conv = TextoANumero().fit(ejemplo)
print("tipos aprendidos:", conv.tipos_)
print("columnas de salida:", list(conv.get_feature_names_out()))
print(conv.transform(ejemplo))

# %% [markdown]
# **Interpretación:** detectó solo que `home_possession` es porcentaje y `home_saves` es razón.
# Una columna de entrada de razón produjo dos de salida (3 columnas en total), y el `None` se
# convirtió en `nan` en lugar de reventar: de rellenarlo se encarga el `SimpleImputer` que viene
# después.

# %% [markdown]
# ## 4. `ColumnTransformer` + `Pipeline`
#
# Cada tipo de variable necesita un tratamiento distinto. `ColumnTransformer` es como una
# **cocina con estaciones**: las verduras van a una tabla, la carne a otra, y al final todo se
# junta en el mismo plato (una sola matriz numérica).
#
# | Rama | Columnas | Pasos |
# |---|---|---|
# | `numericas` | 4 columnas `*_pct` | `SimpleImputer(median)` → `StandardScaler` |
# | `porcentajes` | posesión local y visitante | `TextoANumero` → imputar → escalar |
# | `razones` | tiros a puerta y atajadas | `TextoANumero` (×2 columnas) → imputar → escalar |
# | `categoricas` | equipos | `SimpleImputer(most_frequent)` → `OneHotEncoder(handle_unknown="ignore")` |
#
# - `SimpleImputer(strategy="median")`: la mediana aguanta valores extremos mejor que la media.
#   La aprende en `fit` con el train y la reutiliza en test.
# - `OneHotEncoder`: convierte "Arsenal" en una columna 0/1 por equipo. `handle_unknown="ignore"`
#   hace que un equipo nunca visto produzca una fila de ceros en lugar de un error.
#   `sparse_output=False` para poder ver la salida como DataFrame más abajo.
# - `StandardScaler`: deja media 0 y desviación 1. Al bosque aleatorio le da igual la escala,
#   pero lo dejamos para que el mismo preprocesamiento sirva a modelos que sí la necesitan.
# - `remainder="drop"`: cualquier columna no declarada se descarta (filtro de seguridad).

# %%
def construir_preprocesamiento() -> ColumnTransformer:
    numerico = Pipeline([("imputar", SimpleImputer(strategy="median")),
                         ("escalar", StandardScaler())])
    porcentaje = Pipeline([("parsear", TextoANumero()),
                           ("imputar", SimpleImputer(strategy="median")),
                           ("escalar", StandardScaler())])
    razon = Pipeline([("parsear", TextoANumero()),
                      ("imputar", SimpleImputer(strategy="median")),
                      ("escalar", StandardScaler())])
    categorico = Pipeline([("imputar", SimpleImputer(strategy="most_frequent")),
                           ("onehot", OneHotEncoder(handle_unknown="ignore",
                                                    sparse_output=False))])
    return ColumnTransformer(
        [("numericas", numerico, NUMERICAS),
         ("porcentajes", porcentaje, PORCENTAJES),
         ("razones", razon, RAZONES),
         ("categoricas", categorico, CATEGORICAS)],
        remainder="drop",
    )


def construir_pipeline(modelo=None) -> Pipeline:
    if modelo is None:
        modelo = RandomForestClassifier(n_estimators=300, random_state=RANDOM_STATE)
    return Pipeline([("preprocesamiento", construir_preprocesamiento()),
                     ("modelo", modelo)])


pipe = construir_pipeline()
pipe.fit(X_train, y_train)
y_pred = pipe.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"Accuracy en prueba: {acc:.3f}  ({int((y_pred == y_test).sum())} de {len(y_test)} aciertos)")
print(classification_report(y_test, y_pred, digits=3))

# %% [markdown]
# **Interpretación:** sale **0.724** (21 de 29), el mismo número de la Actividad 1, aunque aquí
# usamos un solo transformador personalizado en vez de dos: misma lógica, mismo orden de
# columnas, misma semilla, mismo resultado. Por clase se repite lo del original: `Home Win` y
# `Away Win` se predicen bien, pero `Draw` tiene recall 0.200 (solo 1 de 5 empates). Pocos
# ejemplos y sin una huella estadística clara.
#
# ¿Es bueno 0.724? Hay que compararlo con un modelo tonto que siempre dice "gana el local":

# %%
tonto = DummyClassifier(strategy="most_frequent").fit(X_train, y_train)
print(f"Baseline (siempre {tonto.classes_[np.argmax(tonto.class_prior_)]}): "
      f"{accuracy_score(y_test, tonto.predict(X_test)):.3f}")

# %% [markdown]
# **Interpretación:** el baseline saca 0.483 (14 de 29 son victorias locales). El pipeline
# supera ese piso por 24 puntos: cumple el criterio de éxito que planteamos en CRISP-DM.

# %% [markdown]
# ## 5. Mirar adentro del pipeline
#
# ### 5.1 Diagrama en texto
# En Jupyter, poner `pipe` al final de una celda dibuja un diagrama interactivo (HTML). Para
# leerlo también en texto plano, recorremos el pipeline con una función recursiva:

# %%
def dibujar(est, nombre="pipe", prefijo=""):
    print(f"{prefijo}{nombre}: {type(est).__name__}")
    if isinstance(est, Pipeline):
        for paso, sub in est.steps:
            dibujar(sub, paso, prefijo + "    ")
    elif isinstance(est, ColumnTransformer):
        for rama, sub, cols in est.transformers:
            print(f"{prefijo}    ├─ {rama}  <- {cols}")
            dibujar(sub, rama, prefijo + "    │   ")


dibujar(pipe)

# %% [markdown]
# Y el diagrama interactivo (en Jupyter se puede hacer clic en cada caja):

# %%
set_config(display="diagram")
pipe

# %% [markdown]
# ### 5.2 `get_feature_names_out`: ¿qué columnas le llegan al modelo?
# Entran 12 columnas crudas. ¿Cuántas salen? Cada transformer sabe nombrar sus salidas, y el
# `ColumnTransformer` les antepone el nombre de la rama (`razones__...`). Por eso nuestro
# transformador personalizado implementa `get_feature_names_out`.

# %%
prep = pipe.named_steps["preprocesamiento"]
nombres = prep.get_feature_names_out()
print("Columnas de entrada:", len(FEATURES), "-> columnas de salida:", len(nombres))
print(pd.Series([n.split("__")[0] for n in nombres]).value_counts().to_string())
print("\nPrimeras 12:", list(nombres[:12]))

# %% [markdown]
# **Interpretación:** 12 → 86 columnas: 4 numéricas + 2 de posesión + 8 de razones (4 columnas
# × hechos/intentos) + 72 del One-Hot (36 equipos como local + 36 como visitante). Con solo 115
# partidos de entrenamiento, 72 columnas de equipos donde cada equipo aparece unas pocas veces
# son casi ruido. Esa observación motiva el `SelectKBest` del tema 06.

# %% [markdown]
# ### 5.3 `set_output(transform="pandas")`
# Por defecto los transformers devuelven arrays de NumPy (sin nombres de columna). Con
# `set_output` la salida es un DataFrame con los nombres de `get_feature_names_out`: mucho más
# fácil de depurar.

# %%
prep_df = construir_preprocesamiento().set_output(transform="pandas")
Xt = prep_df.fit_transform(X_train)
print(type(Xt).__name__, Xt.shape)
Xt.iloc[:3, :10].round(2)

# %%
print("¿Quedan nulos después de imputar?", bool(Xt.isna().any().any()))
print("Medias de las columnas escaladas (train):",
      Xt.filter(like="porcentajes__").mean().round(6).to_dict())

# %% [markdown]
# **Interpretación:** la salida ya es un DataFrame de 115 × 86 sin nulos. Las columnas escaladas
# tienen media 0 en el train (por construcción del `StandardScaler`). En test **no** tendrán
# media exactamente 0, porque se escalan con la media del train. Y está bien que así sea.

# %% [markdown]
# ## 6. Fuga de datos: escalar fuera del pipeline vs dentro
#
# **Fuga de información (data leakage):** cuando información del conjunto de prueba (o del fold
# de validación) se cuela en el entrenamiento. El resultado: métricas infladas que no se
# repiten en producción.
#
# **Analogía:** es como estudiar con el examen ya resuelto. Sacas 100, pero no aprendiste nada.
#
# El error clásico es preprocesar **todo** el dataset antes de partirlo:
#
# ```python
# X_escalado = StandardScaler().fit_transform(X)          # usa la media de los 144 (incluye test)
# cross_val_score(modelo, X_escalado, y)                  # cada fold de validación ya "se vio"
# ```
#
# Lo correcto es meter el escalador en el pipeline: `cross_val_score(pipeline, X, y)` reajusta
# el escalador **dentro de cada fold**, solo con los datos de entrenamiento de ese fold.
#
# ### 6.1 La media que aprende el escalador

# %%
num_train = prep.named_transformers_["porcentajes"].named_steps["parsear"].transform(X_train)
num_todo = prep.named_transformers_["porcentajes"].named_steps["parsear"].transform(X)
print("Media de home_possession que aprende el escalador:")
print(f"  dentro del pipeline (solo train, 115): {num_train[:, 0].mean():.3f}")
print(f"  fuera del pipeline (todo, 144)       : {num_todo[:, 0].mean():.3f}")

# %% [markdown]
# **Interpretación:** si escalas fuera, la media incluye los 29 partidos de prueba. La diferencia
# es pequeña en este caso, pero el principio es el que importa: el modelo ya "sabe" algo de los
# datos con los que lo vas a evaluar.
#
# ### 6.2 ¿Cambia la métrica? KNN (sensible a la escala) con validación cruzada
#
# Usamos solo las columnas numéricas y un `KNeighborsClassifier`, que depende totalmente de las
# distancias (y por lo tanto de la escala). Comparamos con validación cruzada estratificada de
# 5 folds y la misma partición en ambos casos.

# %%
convertidor = Pipeline([("parsear", ColumnTransformer(
    [("num", "passthrough", NUMERICAS),
     ("pct", TextoANumero(), PORCENTAJES),
     ("raz", TextoANumero(), RAZONES)])),
    ("imputar", SimpleImputer(strategy="median"))])
X_num = convertidor.fit_transform(X)     # solo parsea texto e imputa (no escala)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
knn = KNeighborsClassifier(n_neighbors=7)

# MAL: escalar los 144 partidos y después validar
X_num_escalado = StandardScaler().fit_transform(X_num)
fuera = cross_val_score(knn, X_num_escalado, y, cv=cv, scoring="accuracy")

# BIEN: el escalador vive dentro del pipeline y se reajusta en cada fold
dentro = cross_val_score(Pipeline([("escalar", StandardScaler()), ("knn", knn)]),
                         X_num, y, cv=cv, scoring="accuracy")

print(f"Escalando FUERA del pipeline : {fuera.mean():.3f}  por fold {fuera.round(3)}")
print(f"Escalando DENTRO del pipeline: {dentro.mean():.3f}  por fold {dentro.round(3)}")

# %% [markdown]
# **Interpretación:** escalando fuera salió 0.695 y dentro 0.716; los folds 1, 4 y 5 son
# idénticos y la diferencia viene de los folds 2 y 3. Ojo con la lección: aquí la versión con
# fuga salió **más baja**, no más alta. La fuga con `StandardScaler` es **sutil** (la media de
# 144 partidos casi no cambia al quitar un fold: 51.157 vs 50.979 en la posesión) y no infla la
# métrica de forma garantizada; lo que hace es que la validación deje de medir el procedimiento
# real (en producción el escalador nunca verá los datos que va a transformar). Como "no se
# nota", la gente lo hace. Con preprocesamientos que aprenden más de los datos, la fuga sí se
# vuelve enorme y siempre a favor de lo optimista. Mira el siguiente ejemplo.
#
# ### 6.3 Donde la fuga es enorme: seleccionar variables fuera del pipeline
#
# Experimento: a las etiquetas reales de los 144 partidos les pegamos **2 000 columnas de puro
# ruido aleatorio** (no tienen ninguna relación con el resultado). Luego elegimos las 20 "mejores"
# con `SelectKBest`.
#
# - **Fuera:** se eligen las 20 mirando los 144 partidos y después se valida.
# - **Dentro:** `SelectKBest` va en el pipeline, así que en cada fold elige mirando solo el train.

# %%
rng = np.random.default_rng(RANDOM_STATE)
ruido = rng.normal(size=(len(y), 2000))
modelo = LogisticRegression(max_iter=2000)

seleccion_fuera = SelectKBest(f_classif, k=20).fit_transform(ruido, y)     # mira TODO y
fuga_fuera = cross_val_score(modelo, seleccion_fuera, y, cv=cv, scoring="accuracy")

pipe_ruido = Pipeline([("seleccion", SelectKBest(f_classif, k=20)), ("modelo", modelo)])
fuga_dentro = cross_val_score(pipe_ruido, ruido, y, cv=cv, scoring="accuracy")

print(f"Selección FUERA del pipeline : accuracy CV = {fuga_fuera.mean():.3f}")
print(f"Selección DENTRO del pipeline: accuracy CV = {fuga_dentro.mean():.3f}")
print(f"Baseline (clase mayoritaria) : {y.value_counts(normalize=True).max():.3f}")

# %% [markdown]
# **Interpretación:** con datos que son **ruido puro**, seleccionar fuera del pipeline "logra"
# 0.750 de accuracy, muy por encima del baseline de 0.493: el selector eligió las 20 columnas que por casualidad
# se correlacionaban con `result` **en todos los partidos, incluidos los de validación**. Dentro
# del pipeline el resultado cae a 0.438, al nivel del azar (incluso debajo del baseline), que es
# la verdad: el ruido no predice nada.
# Mismo código, misma semilla; lo único que cambió fue **dónde** se hizo el `fit`.
#
# **Regla:** todo lo que aprende de los datos (imputar, escalar, codificar, seleccionar) va
# dentro del pipeline. Así `fit` solo ve train, y `cross_val_score`/`GridSearchCV` lo reajustan
# fold por fold.

# %% [markdown]
# ## 7. Predecir un partido nuevo (con texto crudo)
#
# Como la limpieza vive dentro del pipeline, se le puede pasar un partido tal como vendría en el
# CSV, con `'55%'` y `'6 of 12'`, e incluso con un equipo que nunca vio:

# %%
nuevo = pd.DataFrame([{
    "home_shots_on_target_pct": 50.0, "away_shots_on_target_pct": 20.0,
    "home_saves_pct": 80.0, "away_saves_pct": 50.0,
    "home_possession": "55%", "away_possession": "45%",
    "home_shots_on_target": "6 of 12", "away_shots_on_target": "2 of 10",
    "home_saves": "4 of 5", "away_saves": "3 of 6",
    "home_team": "Municipal", "away_team": "Comunicaciones",   # equipos que no existen en el train
}])
print("Predicción:", pipe.predict(nuevo)[0])
print("Probabilidades:", {c: round(float(p), 3) for c, p in zip(pipe.classes_, pipe.predict_proba(nuevo)[0])})

# %% [markdown]
# **Interpretación:** no hubo que limpiar nada a mano y el pipeline no reventó con equipos
# desconocidos (`handle_unknown="ignore"` los convierte en ceros). Predijo `Home Win` con
# probabilidad 0.897: el local tuvo 6 tiros a puerta contra 2 y su portero atajó 4 de 5.
#
# Y como el pipeline completo es un solo objeto, se guarda y se carga entero con `joblib`
# (preprocesamiento + modelo). Aquí lo guardamos en una carpeta temporal:

# %%
with tempfile.TemporaryDirectory() as carpeta:
    ruta_modelo = Path(carpeta) / "pipeline.joblib"
    joblib.dump(pipe, ruta_modelo)
    cargado = joblib.load(ruta_modelo)
    print(f"Tamaño del archivo: {ruta_modelo.stat().st_size / 1024:.0f} KB")
    print("¿Mismas predicciones en test?", bool((cargado.predict(X_test) == y_pred).all()))

# %% [markdown]
# ## 8. Por qué empaquetar: de notebook a comando `act1-demo`
#
# En la Actividad 1 el código no se quedó en un notebook: se convirtió en un **paquete
# instalable**. Así cualquier integrante del equipo hace:
#
# ```bash
# git clone https://github.com/DiegoLinares11/Actividad1-MLOPS.git
# cd Actividad1-MLOPS
# pip install .
# act1-demo
# ```
#
# y obtiene **el mismo 0.724** (se comprobó en Windows 11 con Python 3.14.2 y en Linux con
# Python 3.14.4). Las piezas:
#
# - **`src/` layout**: el código vive en `src/act1_pipeline/`. Obliga a instalar el paquete para
#   importarlo, así se prueba lo mismo que recibirá un compañero (y no "lo que está suelto en mi
#   carpeta").
# - **`pyproject.toml`**: nombre, versión, dependencias (`scikit-learn>=1.3`, `pandas>=2.0`,
#   `numpy>=1.24`) y `package-data` para que el CSV viaje **dentro** del paquete. `setup.py`
#   queda solo como *shim* de compatibilidad.
# - **Entry point de consola**: `[project.scripts] act1-demo = "act1_pipeline.cli:main"`. Al
#   hacer `pip install .`, pip crea un ejecutable `act1-demo` que llama a la función `main()`.
#
# Esta es una versión mínima de esa `main()` (lo que hace el comando):

# %%
def main() -> int:
    print("=" * 60)
    print("ACTIVIDAD 1 - Pipeline de scikit-learn (UEFA Champions League)")
    print("=" * 60)
    datos = extraer_datos()
    print(f"[1] Extracción      -> {datos.shape[0]} filas, {datos.shape[1]} columnas")
    datos = filtrar_datos(datos)
    print(f"[2] Filtrado        -> {datos.shape[0]} filas, {datos.shape[1]} columnas")
    Xtr, Xte, ytr, yte = train_test_split(datos[FEATURES], datos[TARGET], test_size=0.2,
                                          random_state=RANDOM_STATE, stratify=datos[TARGET])
    print(f"[4] Separación      -> train={len(Xtr)}  test={len(Xte)}")
    modelo = construir_pipeline().fit(Xtr, ytr)
    print("=" * 60)
    print(f"RESULTADO - Accuracy en prueba = {accuracy_score(yte, modelo.predict(Xte)):.3f}")
    print("=" * 60)
    return 0


codigo_salida = main()   # el comando de consola devuelve 0 cuando todo salió bien

# %% [markdown]
# **Interpretación:** la misma salida que el README de la Actividad 1: 151 × 18 → 144 × 13 →
# train 115 / test 29 → accuracy 0.724. (Filtrado da 13 columnas: las 12 features más `result`.)
# El archivo `ejemplos/pyproject.toml` de este tema trae el `pyproject.toml` original comentado
# línea por línea.

# %% [markdown]
# ## Resumen
#
# - **Transformer** = `fit` + `transform` (aprende y cambia los datos); **estimator** = `fit` +
#   `predict`. Lo aprendido se guarda en atributos con `_` final (`mean_`, `tipos_`).
# - Un **`Pipeline`** encadena transformers y un estimator y se usa como un solo modelo.
#   **`ColumnTransformer`** aplica un tratamiento distinto a cada tipo de variable.
# - Un **transformador personalizado** hereda de `BaseEstimator` + `TransformerMixin`, aprende en
#   `fit` y define `get_feature_names_out`; el nuestro convirtió `'63%'` y `'3 of 10'` dentro del
#   pipeline.
# - Reconstruimos el resultado original: 151 → 144 filas, train 115 / test 29, **accuracy 0.724**
#   contra 0.483 del baseline; 12 columnas crudas → 86 transformadas; los empates siguen siendo
#   el punto débil (recall 0.200).
# - **Fuga:** escalar fuera del pipeline es una fuga sutil (casi no cambia la métrica);
#   seleccionar variables fuera convirtió ruido puro en un modelo "bueno". Dentro del pipeline,
#   el ruido vuelve al nivel del azar.
# - **Empaquetar** (`src/`, `pyproject.toml`, entry point `act1-demo`) hace que cualquiera
#   reproduzca el resultado con un comando.
