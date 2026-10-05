# %% [markdown]
# # 11 · Databricks en local: medallón, linaje y un "MLflow" casero
#
# En Databricks construimos tres tablas en Unity Catalog (`partidos_bronze` →
# `partidos_silver` → `partidos_gold`) y registramos el entrenamiento con MLflow.
# Aquí no hay Databricks, ni Spark, ni MLflow, así que **imitamos las ideas** con pandas:
#
# | En Databricks | Aquí, en local |
# |---|---|
# | Unity Catalog `workspace.champions.<tabla>` | una carpeta temporal `lakehouse/workspace/champions/<tabla>/` |
# | Tabla Delta con versiones (*time travel*) | un archivo por versión: `v0`, `v1`, ... |
# | `spark.table("...")` (crea linaje) | `leer_tabla("...")`, que **siempre lee de disco** y anota la dependencia |
# | `.saveAsTable("...")` | `guardar_tabla(df, "...")`, que registra el linaje automáticamente |
# | Celda `%sql` | `sqlite3` en memoria |
# | MLflow: experimento, runs, params, métricas, artefactos, Model Registry | un JSON con runs + un registro de modelos con versiones y alias |
#
# **Por qué lo hacemos así:** el principio clave del medallón en Unity Catalog es que **cada
# capa lee la TABLA anterior** (no un DataFrame que quedó en memoria). Al obligarnos a leer
# siempre de disco, ese principio se vuelve visible.

# %%
import hashlib
import json
import shutil
import sqlite3
import tempfile
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")
RANDOM_STATE = 42
FUENTE = Path("../datos/champions_league_matches.csv").resolve()

try:
    import pyarrow  # noqa: F401  (parquet necesita pyarrow)
    FORMATO = "parquet"
except ImportError:
    FORMATO = "csv"

LAKEHOUSE = Path(tempfile.mkdtemp(prefix="lakehouse_"))
CATALOGO, ESQUEMA = "workspace", "champions"
print("Lakehouse temporal:", LAKEHOUSE.name, "| formato de archivo:", FORMATO)

# %% [markdown]
# ## 1. Un "Unity Catalog" de juguete
#
# **Qué hace cada función:**
#
# - `guardar_tabla(df, nombre)`: escribe una **nueva versión** de la tabla (como Delta: nunca
#   sobreescribe a ciegas, agrega `v0`, `v1`...). Guarda además el **esquema** (tipos) y anota en
#   el catálogo de qué tablas se leyó para producirla: eso es el **linaje**.
# - `leer_tabla(nombre, version=None)`: lee **desde disco** la última versión (o una anterior:
#   *time travel*) y deja constancia de la lectura.
#
# **Por qué el linaje se arma solo:** igual que Unity Catalog, no le decimos "plata depende de
# bronce"; lo deduce porque, entre una escritura y la siguiente, la celda leyó la tabla bronce.
# Si en vez de leer la tabla usáramos un DataFrame en memoria, el catálogo **no tendría forma de
# saberlo**.
#
# Detalle técnico: si no hay `pyarrow` se guarda en CSV, que **no conserva tipos**; por eso
# guardamos el esquema aparte y lo reaplicamos al leer (Delta/parquet guardan el esquema dentro
# del archivo).

# %%
CATALOGO_META = {}        # nombre completo -> metadatos de la tabla
_lecturas_pendientes = []  # tablas leídas desde la última escritura


def _ruta(nombre):
    return LAKEHOUSE / CATALOGO / ESQUEMA / nombre


def guardar_tabla(df: pd.DataFrame, nombre: str, comentario: str = "") -> None:
    completo = f"{CATALOGO}.{ESQUEMA}.{nombre}"
    carpeta = _ruta(nombre)
    carpeta.mkdir(parents=True, exist_ok=True)
    meta = CATALOGO_META.setdefault(completo, {"versiones": [], "lee_de": set()})
    version = len(meta["versiones"])
    archivo = carpeta / f"v{version}.{FORMATO}"
    if FORMATO == "parquet":
        df.to_parquet(archivo, index=False)
    else:
        df.to_csv(archivo, index=False)
    esquema = {c: str(t) for c, t in df.dtypes.items()}
    (carpeta / f"v{version}_schema.json").write_text(json.dumps(esquema))
    meta["versiones"].append({"version": version, "filas": len(df), "columnas": df.shape[1],
                              "comentario": comentario,
                              "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    meta["lee_de"] |= set(_lecturas_pendientes)
    _lecturas_pendientes.clear()
    print(f"[saveAsTable] {completo} v{version}: {len(df)} filas x {df.shape[1]} columnas")


def leer_tabla(nombre: str, version=None) -> pd.DataFrame:
    completo = f"{CATALOGO}.{ESQUEMA}.{nombre}"
    versiones = CATALOGO_META[completo]["versiones"]
    v = versiones[-1]["version"] if version is None else version
    carpeta = _ruta(nombre)
    esquema = json.loads((carpeta / f"v{v}_schema.json").read_text())
    if FORMATO == "parquet":
        df = pd.read_parquet(carpeta / f"v{v}.parquet")
    else:
        fechas = [c for c, t in esquema.items() if t.startswith("datetime")]
        textos = {c: str for c, t in esquema.items() if t in ("object", "string", "str")}
        df = pd.read_csv(carpeta / f"v{v}.csv", parse_dates=fechas, dtype=textos)
        df = df.astype({c: t for c, t in esquema.items() if c not in fechas and c not in textos})
    _lecturas_pendientes.append(completo)
    return df

# %% [markdown]
# ## 2. Capa BRONCE — los datos tal como llegan
#
# **Qué:** el CSV crudo, **sin tocar**: 151 filas (incluidas las 7 vacías que separan jornadas)
# y las 18 columnas (incluidas `score` y `winner`, que tienen fuga).
#
# **Por qué no se limpia bronce:** para poder **auditar**. Si mañana dudamos de un dato de plata
# o de un resultado del modelo, en bronce está el original tal cual llegó. Si limpias al ingerir y
# te equivocas, perdiste el dato para siempre.
#
# Leemos todo como texto (`dtype=str`) justamente para no "interpretar" nada todavía, y
# verificamos con un hash que el contenido es idéntico a la fuente.

# %%
crudo = pd.read_csv(FUENTE, dtype=str, keep_default_na=False, na_values=[""])
guardar_tabla(crudo, "partidos_bronze", "ingesta cruda del CSV de la Champions")

bronce = leer_tabla("partidos_bronze")
_lecturas_pendientes.clear()   # esta lectura solo era para verificar, no alimenta otra tabla


def huella(df):
    return hashlib.md5(pd.util.hash_pandas_object(df.fillna("<NA>"), index=False).values).hexdigest()[:10]


print("filas totalmente vacías en bronce:", int(bronce.isna().all(axis=1).sum()))
print("columnas con fuga presentes:", [c for c in ["score", "winner"] if c in bronce.columns])
print("huella fuente :", huella(crudo))
print("huella bronce :", huella(bronce), "-> idénticas:", huella(crudo) == huella(bronce))
bronce.head(3)

# %% [markdown]
# **Interpretación:** bronce tiene las 151 filas, las 7 filas vacías y las columnas `score` y
# `winner`. La huella coincide con la de la fuente: el dato quedó **exactamente** como llegó.
# Todo es texto (`'63%'`, `'3 of 10'`): todavía no "creemos" nada sobre los tipos.

# %% [markdown]
# ## 3. Capa PLATA — limpia, sin fuga y con tipos correctos
#
# **Qué:** se lee **la tabla bronce desde disco** (nunca la variable `crudo`) y se aplica lo que
# descubrimos en el Ejercicio 1, como en `medallon_champions.py`:
#
# - quitar filas sin `result` (las 7 vacías),
# - descartar `score` y `winner` (fuga) y `venue`, `referee`,
# - `'63%'` → 63.0 en `home_possession_pct` / `away_possession_pct`,
# - `'3 of 10'` → `home_shots_on_target_n = 3` y `home_shots_total = 10`.
#
# Dos cosas que **agregamos** respecto al notebook original (para poder entrenar con lo mismo
# que el Ejercicio 3): tipamos `date` como fecha y convertimos también las atajadas
# (`'4 of 8'` → `home_saves_n`, `home_saves_total`), que el original dejaba como texto.

# %%
def a_numero_porcentaje(s):
    return pd.to_numeric(s.str.replace("%", "", regex=False).str.strip(), errors="coerce")


def partir_razon(s):
    partes = s.str.extract(r"(\d+)\s*of\s*(\d+)")
    return pd.to_numeric(partes[0], errors="coerce"), pd.to_numeric(partes[1], errors="coerce")


bronce = leer_tabla("partidos_bronze")            # <-- lee la TABLA: esto crea linaje

plata = bronce[bronce["result"].notna()].drop(columns=["score", "winner", "venue", "referee"]).copy()
plata["date"] = pd.to_datetime(plata["date"])
for lado in ["home", "away"]:
    plata[f"{lado}_possession_pct"] = a_numero_porcentaje(plata[f"{lado}_possession"])
    plata[f"{lado}_shots_on_target_n"], plata[f"{lado}_shots_total"] = partir_razon(plata[f"{lado}_shots_on_target"])
    plata[f"{lado}_saves_n"], plata[f"{lado}_saves_total"] = partir_razon(plata[f"{lado}_saves"])
    for col in [f"{lado}_shots_on_target_pct", f"{lado}_saves_pct"]:
        plata[col] = pd.to_numeric(plata[col], errors="coerce")
plata = plata.drop(columns=[f"{l}_{c}" for l in ["home", "away"]
                            for c in ["possession", "shots_on_target", "saves"]]).reset_index(drop=True)

guardar_tabla(plata, "partidos_silver", "limpia, sin fuga, tipada")
print(f"[plata] {len(bronce)} -> {len(plata)} partidos")
print(leer_tabla("partidos_silver").dtypes.value_counts().to_string())
_lecturas_pendientes.clear()

# %% [markdown]
# **Interpretación:** de 151 filas en bronce quedan **144 partidos** en plata (se fueron las 7
# vacías). Ya no hay `score` ni `winner`, y al **releer de disco** los tipos sobreviven:
# 10 columnas enteras (posesión, tiros, atajadas), 4 decimales (los porcentajes de tiros y
# atajadas, que tienen algún nulo), 1 fecha (`date`) y solo 3 de texto: `home_team`,
# `away_team` y `result`. Plata responde a *"¿en qué puedo confiar?"*.

# %% [markdown]
# ## 4. Capa ORO — lista para consumir
#
# **Qué:** se lee **la tabla plata** y se arma lo que necesita quien consume. Dos tablas oro,
# porque cada una responde a una pregunta distinta:
#
# 1. `partidos_gold` (igual que en el curso): resumen **por equipo local** — partidos, victorias,
#    empates, posesión promedio, tiros a puerta promedio y tasa de victoria.
# 2. `equipos_gold` (extra del repaso): resumen por equipo **sumando local y visita** — victorias
#    totales, posesión y tiros a puerta promedio.

# %%
silver = leer_tabla("partidos_silver")             # <-- lee la TABLA: más linaje

oro = (silver.groupby("home_team")
       .agg(partidos_de_local=("result", "size"),
            victorias=("result", lambda r: int((r == "Home Win").sum())),
            empates=("result", lambda r: int((r == "Draw").sum())),
            posesion_promedio=("home_possession_pct", "mean"),
            tiros_a_puerta_promedio=("home_shots_on_target_n", "mean"))
       .reset_index())
oro["tasa_de_victoria"] = (oro["victorias"] / oro["partidos_de_local"]).round(3)
oro[["posesion_promedio", "tiros_a_puerta_promedio"]] = oro[["posesion_promedio", "tiros_a_puerta_promedio"]].round(1)
oro = oro.sort_values(["tasa_de_victoria", "partidos_de_local"], ascending=False).reset_index(drop=True)
guardar_tabla(oro, "partidos_gold", "resumen por equipo local")
print(f"[oro] resumen de {len(oro)} equipos")

# %%
silver = leer_tabla("partidos_silver")             # otra tabla oro que también nace de plata


def vista_por_lado(df, lado, gana):
    return pd.DataFrame({
        "equipo": df[f"{lado}_team"],
        "victoria": (df["result"] == gana).astype(int),
        "empate": (df["result"] == "Draw").astype(int),
        "posesion": df[f"{lado}_possession_pct"],
        "tiros_a_puerta": df[f"{lado}_shots_on_target_n"],
        "tiros_totales": df[f"{lado}_shots_total"]})


largo = pd.concat([vista_por_lado(silver, "home", "Home Win"),
                   vista_por_lado(silver, "away", "Away Win")])
equipos = (largo.groupby("equipo")
           .agg(partidos=("victoria", "size"), victorias=("victoria", "sum"),
                empates=("empate", "sum"), posesion_promedio=("posesion", "mean"),
                tiros_a_puerta_promedio=("tiros_a_puerta", "mean"),
                tiros_totales_promedio=("tiros_totales", "mean"))
           .round(1).sort_values(["victorias", "posesion_promedio"], ascending=False).reset_index())
guardar_tabla(equipos, "equipos_gold", "resumen por equipo (local + visita)")
equipos.head(8)

# %% [markdown]
# **Interpretación:** `equipos_gold` resume a los 36 equipos de la fase de liga
# (8 partidos cada uno: 144 partidos × 2 equipos / 36). Arsenal encabeza con 8 victorias en 8
# partidos, seguido de Bayern Munich (7) y Liverpool (6). Es la tabla que usaría un dashboard:
# nadie que la consulte necesita saber que la posesión venía como `'63%'`. Oro responde a
# *"¿qué necesita quien lo va a usar?"*.

# %% [markdown]
# ## 5. Consultar oro con SQL (lo que era la celda `%sql`)
#
# En Databricks las tablas son consultables con SQL desde cualquier notebook. Aquí cargamos
# `partidos_gold` (leída de disco) en SQLite y corremos **la misma consulta** del notebook original.

# %%
con = sqlite3.connect(":memory:")
leer_tabla("partidos_gold").to_sql("partidos_gold", con, index=False)
_lecturas_pendientes.clear()
consulta = """
SELECT home_team AS equipo, partidos_de_local, victorias, tasa_de_victoria, posesion_promedio
FROM partidos_gold
WHERE partidos_de_local >= 3
ORDER BY tasa_de_victoria DESC
LIMIT 10
"""
top = pd.read_sql(consulta, con)
top

# %% [markdown]
# **Interpretación:** cinco equipos ganaron sus 4 partidos de local (tasa 1.00): Arsenal,
# Bayern Munich, Chelsea, Sporting CP y Tottenham. La posesión **no** ordena igual que la tasa
# de victoria: Sporting CP ganó todo en casa con 46.8 % de posesión promedio, mientras que
# Barcelona, con 68.2 %, ganó 3 de 4. Tener el balón no garantiza ganar.

# %% [markdown]
# ## 6. El linaje que quedó registrado
#
# Nadie declaró las dependencias: salieron de qué tablas se leyeron antes de cada escritura.

# %%
for tabla, meta in CATALOGO_META.items():
    origen = ", ".join(sorted(t.split(".")[-1] for t in meta["lee_de"])) or "(fuente externa: CSV)"
    print(f"{tabla.split('.')[-1]:<16} <- {origen}")

# %% [markdown]
# ```
# partidos_bronze ──> partidos_silver ──┬──> partidos_gold
#                                       └──> equipos_gold
# ```
#
# ### ¿Y si NO leemos la tabla anterior?
#
# El error típico: construir oro con la variable `plata` que quedó en memoria. Funciona, da el
# mismo resultado... pero el catálogo **no se entera** de dónde vino.

# %%
oro_atajo = plata.groupby("home_team").size().reset_index(name="partidos")   # DataFrame en memoria
guardar_tabla(oro_atajo, "gold_sin_linaje", "hecha desde una variable en memoria")
print("gold_sin_linaje <-", CATALOGO_META[f"{CATALOGO}.{ESQUEMA}.gold_sin_linaje"]["lee_de"] or "¿? (sin linaje)")

# %% [markdown]
# **Interpretación:** `gold_sin_linaje` aparece como una tabla huérfana: si mañana cambia plata,
# nadie sabrá que esta tabla quedó desactualizada, ni podrá rastrear un número raro hasta bronce.
# Por eso en `medallon_champions.py` cada capa empieza con `spark.table(...)`.

# %% [markdown]
# ## 7. Time travel: volver a una versión anterior
#
# Delta Lake guarda cada escritura como una versión nueva. Simulamos un error: alguien
# reescribe plata con un filtro equivocado que borra los empates.

# %%
silver = leer_tabla("partidos_silver")
guardar_tabla(silver[silver["result"] != "Draw"], "partidos_silver", "BUG: se borraron los empates")
_lecturas_pendientes.clear()

historial = pd.DataFrame(CATALOGO_META[f"{CATALOGO}.{ESQUEMA}.partidos_silver"]["versiones"])
print(historial[["version", "filas", "comentario"]].to_string(index=False))

actual = leer_tabla("partidos_silver")
anterior = leer_tabla("partidos_silver", version=0)     # como: SELECT * FROM t VERSION AS OF 0
_lecturas_pendientes.clear()
print("\nempates en la versión actual:", int((actual["result"] == "Draw").sum()))
print("empates en la versión 0     :", int((anterior["result"] == "Draw").sum()))

# restaurar (como RESTORE TABLE ... TO VERSION AS OF 0)
guardar_tabla(anterior, "partidos_silver", "RESTORE a la versión 0")
_lecturas_pendientes.clear()

# %% [markdown]
# **Interpretación:** la versión 1 perdió los 25 empates (quedó con 119 filas), pero la versión 0
# sigue en disco con los 144 partidos y la restauramos como versión 2. En Delta esto es
# `DESCRIBE HISTORY`, `VERSION AS OF` y `RESTORE`: el historial es parte de la tabla.

# %% [markdown]
# ## 8. Un "MLflow" casero: experimentos, runs, parámetros, métricas y artefactos
#
# **Qué guarda MLflow por cada run** (cada vez que entrenas):
#
# | Concepto MLflow | Ejemplo | Aquí |
# |---|---|---|
# | Experimento | "champions" | carpeta `mlruns/champions/` |
# | Run (id + nombre) | `champions-logistica` | un `uuid` + nombre |
# | Parámetros | `C=0.541`, `class_weight=balanced` | dict `params` |
# | Métricas | `f1_macro=0.542` | dict `metricas` |
# | Artefactos | el modelo serializado | `modelo.joblib` en la carpeta del run |
# | Tags / timestamp | quién, cuándo, qué datos | `timestamp`, `datos=partidos_silver vN` |
#
# `mlflow.sklearn.autolog()` llena todo esto **solo**; aquí lo hacemos a mano para ver qué hay
# detrás. El entrenamiento lee **la tabla plata** (vuelve a importar el linaje: el modelo
# también depende de una versión concreta de los datos).

# %%
MLRUNS = LAKEHOUSE / "mlruns" / "champions"
MLRUNS.mkdir(parents=True)
REGISTRO_RUNS = MLRUNS / "runs.json"
REGISTRO_RUNS.write_text("[]")

silver = leer_tabla("partidos_silver")
version_datos = CATALOGO_META[f"{CATALOGO}.{ESQUEMA}.partidos_silver"]["versiones"][-1]["version"]
_lecturas_pendientes.clear()

NUMERICAS = [f"{l}_{c}" for l in ["home", "away"] for c in
             ["possession_pct", "shots_on_target_n", "shots_total", "saves_n", "saves_total",
              "shots_on_target_pct", "saves_pct"]]
CATEGORICAS = ["home_team", "away_team"]
y = silver["result"]
X = silver[NUMERICAS + CATEGORICAS]
X_ent, X_pru, y_ent, y_pru = train_test_split(X, y, test_size=0.2,
                                              random_state=RANDOM_STATE, stratify=y)
print(f"entrenamiento={len(X_ent)}  prueba={len(X_pru)}  | datos: partidos_silver v{version_datos}")


def construir_pipeline(modelo):
    pre = ColumnTransformer([
        ("num", Pipeline([("imputar", SimpleImputer(strategy="median")),
                          ("escalar", StandardScaler())]), NUMERICAS),
        ("cat", Pipeline([("imputar", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAS)])
    return Pipeline([("preprocesamiento", pre), ("modelo", modelo)])


def registrar_run(nombre, modelo):
    """Equivale a: with mlflow.start_run(run_name=nombre): fit + log_params + log_metrics + log_model"""
    run_id = uuid.uuid4().hex[:12]
    inicio = datetime.now(timezone.utc)
    pipe = construir_pipeline(modelo).fit(X_ent, y_ent)
    pred = pipe.predict(X_pru)
    metricas = {"accuracy": round(accuracy_score(y_pru, pred), 4),
                "f1_macro": round(f1_score(y_pru, pred, average="macro"), 4)}
    params = {k: v for k, v in modelo.get_params().items()
              if k in ["C", "class_weight", "max_iter", "n_estimators", "max_depth", "strategy"]}
    carpeta = MLRUNS / run_id
    carpeta.mkdir()
    joblib.dump(pipe, carpeta / "modelo.joblib")                     # log_model (artefacto)
    run = {"run_id": run_id, "run_name": nombre, "modelo": type(modelo).__name__,
           "params": params, "metricas": metricas,
           "tags": {"datos": f"partidos_silver v{version_datos}"},
           "timestamp": inicio.isoformat(timespec="seconds"),
           "artefacto": f"mlruns/champions/{run_id}/modelo.joblib"}
    runs = json.loads(REGISTRO_RUNS.read_text())
    runs.append(run)
    REGISTRO_RUNS.write_text(json.dumps(runs, indent=2, default=str))
    print(f"[run {run_id}] {nombre:<22} f1_macro={metricas['f1_macro']:.3f}")
    return run


registrar_run("champions-logistica", LogisticRegression(C=0.541, class_weight="balanced",
                                                        max_iter=5000, random_state=RANDOM_STATE))
registrar_run("logistica-C0.05", LogisticRegression(C=0.05, class_weight="balanced",
                                                    max_iter=5000, random_state=RANDOM_STATE))
registrar_run("logistica-C10", LogisticRegression(C=10, class_weight="balanced",
                                                  max_iter=5000, random_state=RANDOM_STATE))
registrar_run("random-forest", RandomForestClassifier(n_estimators=200, max_depth=5,
                                                      class_weight="balanced", random_state=RANDOM_STATE))
_ = registrar_run("trivial-mayoritaria", DummyClassifier(strategy="most_frequent"))

# %% [markdown]
# ### La "pestaña Experiments": comparar runs
#
# En MLflow abres el experimento y ves una tabla con todas las corridas. Aquí la armamos a
# partir del JSON (que es lo único que quedó guardado: no usamos variables en memoria).

# %%
runs = json.loads(REGISTRO_RUNS.read_text())
tabla_runs = pd.json_normalize(runs)[["run_id", "run_name", "modelo", "metricas.f1_macro",
                                      "metricas.accuracy", "params.C", "tags.datos", "timestamp"]]
tabla_runs = tabla_runs.sort_values("metricas.f1_macro", ascending=False).reset_index(drop=True)
tabla_runs

# %%
print(json.dumps(runs[0], indent=2))

# %% [markdown]
# **Interpretación:** el run `champions-logistica` (los hiperparámetros ganadores de la Actividad 3)
# reproduce el **f1_macro 0.542** y la accuracy 0.621 del Ejercicio 3, porque usa la misma
# información y el mismo split. En esta prueba de solo 29 partidos, `logistica-C0.05` saca más
# (**0.565**, accuracy 0.655), `C=10` empata (0.543), el random forest queda en 0.483 y el trivial
# en 0.217, como siempre.
#
# ¡Cuidado al leer esta tabla! Elegir el "mejor" mirando el conjunto de **prueba** es hacer
# trampa: con 29 partidos, un acierto más o menos mueve el F1 varios puntos. En la Actividad 3 se
# eligió C=0.541 con **validación cruzada**, que es lo correcto. Aun así, MLflow es justo lo que
# permite ver y discutir estas comparaciones.
#
# Cada run guarda además qué versión de datos usó (`partidos_silver v2`, la restaurada): si el
# modelo sale raro, se puede rastrear hasta la tabla y, por linaje, hasta bronce.

# %% [markdown]
# ## 9. Registro de modelos (Model Registry) con compuerta
#
# En la Actividad 4 el "registro" era un `modelo.joblib` con **un único nombre** en un volumen de
# Docker: cada reentrenamiento pisaba al anterior y no había historial. El Model Registry de
# MLflow resuelve eso: cada modelo registrado recibe **versiones** (1, 2, 3...) y un **alias**
# (p. ej. `champion`) que apunta a la versión que se usa en producción.
#
# Registramos el mejor run **solo si pasa la compuerta del Ejercicio 3** (f1_macro ≥ 0.40 y mayor
# que el trivial).

# %%
REGISTRO_MODELOS = LAKEHOUSE / "model_registry.json"
REGISTRO_MODELOS.write_text(json.dumps({}))


def registrar_modelo(nombre, run, alias=None, minimo=0.40):
    runs = json.loads(REGISTRO_RUNS.read_text())
    f1_trivial = next(r for r in runs if r["modelo"] == "DummyClassifier")["metricas"]["f1_macro"]
    f1 = run["metricas"]["f1_macro"]
    if f1 < minimo or f1 <= f1_trivial:
        print(f"[registry] RECHAZADO {run['run_name']}: f1={f1:.3f} (mínimo {minimo}, trivial {f1_trivial:.3f})")
        return None
    registro = json.loads(REGISTRO_MODELOS.read_text())
    modelo = registro.setdefault(nombre, {"versiones": [], "alias": {}})
    version = len(modelo["versiones"]) + 1
    modelo["versiones"].append({"version": version, "run_id": run["run_id"],
                                "f1_macro": f1, "artefacto": run["artefacto"]})
    if alias:
        modelo["alias"][alias] = version
    REGISTRO_MODELOS.write_text(json.dumps(registro, indent=2))
    print(f"[registry] {nombre} v{version} <- run {run['run_id']} (f1={f1:.3f})"
          + (f"  alias '{alias}'" if alias else ""))
    return version


runs = json.loads(REGISTRO_RUNS.read_text())
por_f1 = sorted(runs, key=lambda r: r["metricas"]["f1_macro"], reverse=True)
registrar_modelo("workspace.champions.clasificador_resultado", por_f1[0], alias="champion")
registrar_modelo("workspace.champions.clasificador_resultado",
                 next(r for r in runs if r["run_name"] == "trivial-mayoritaria"))
print(json.dumps(json.loads(REGISTRO_MODELOS.read_text()), indent=2))

# %% [markdown]
# ### Cargar el modelo "champion" y predecir
#
# Quien consume el modelo no necesita saber qué run ganó: pide `models:/<nombre>@champion`.

# %%
def cargar_modelo(nombre, alias="champion"):
    registro = json.loads(REGISTRO_MODELOS.read_text())[nombre]
    version = registro["alias"][alias]
    info = registro["versiones"][version - 1]
    print(f"cargando {nombre}@{alias} -> v{version} (run {info['run_id']})")
    return joblib.load(LAKEHOUSE / info["artefacto"])


modelo_prod = cargar_modelo("workspace.champions.clasificador_resultado")
muestra = X_pru.head(5)
pd.DataFrame({"home_team": muestra["home_team"].values, "away_team": muestra["away_team"].values,
              "real": y_pru.head(5).values, "predicho": modelo_prod.predict(muestra)})

# %% [markdown]
# **Interpretación:** el run con mayor f1_macro (`logistica-C0.05`, 0.565) se registró como
# **versión 1** con alias `champion`, y 4 de las 5 predicciones de muestra coinciden con el resultado
# real. El trivial fue **rechazado** por la compuerta (0.217 no llega a 0.40). (Con la advertencia de
# arriba: en un proyecto real se registraría el ganador de la validación cruzada.) Cambiar de modelo en producción sería
# registrar una v2 y mover el alias, sin tocar el código que carga `@champion`, y con la v1 a mano
# para volver atrás.

# %%
shutil.rmtree(LAKEHOUSE)   # limpiar la carpeta temporal
print("lakehouse temporal borrado")

# %% [markdown]
# ## Resumen
#
# - **Bronce** guardó el CSV tal cual (151 filas, 18 columnas, con filas vacías y fuga), con la
#   misma huella que la fuente: sirve para **auditar**.
# - **Plata** leyó bronce **desde disco**, quitó las 7 filas vacías y `score`/`winner`, y tipó
#   posesión, tiros y atajadas → **144 partidos** con tipos que sobreviven al releer.
# - **Oro** leyó plata y produjo `partidos_gold` (por equipo local, como en el curso) y
#   `equipos_gold` (36 equipos, local + visita), consultables con SQL.
# - El **linaje** se registró solo porque cada capa leyó la tabla anterior; la tabla hecha desde
#   una variable en memoria quedó **sin linaje**.
# - **Time travel:** una escritura con bug (119 filas, sin empates) se revirtió leyendo la versión 0.
# - El **"MLflow" casero** guardó por run: id, nombre, parámetros, métricas, artefacto, versión de
#   datos y timestamp. El run con los hiperparámetros de la Actividad 3 reprodujo **f1_macro 0.542**;
#   `C=0.05` sacó 0.565 en prueba, pero elegir con 29 partidos de prueba es poco confiable.
# - El **Model Registry** versionó el mejor modelo con alias `champion` y rechazó al trivial por la
#   compuerta: lo que en la Actividad 4 era un único `.joblib` sin historial.
