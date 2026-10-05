# %% [markdown]
# # 10 · CI/CD: el pipeline del Ejercicio 3, reproducido paso a paso
#
# En el Ejercicio 3, GitHub Actions corría 4 jobs encadenados:
#
# ```
# extraer ---> limpiar ---> entrenar ---> evaluar (compuerta de calidad)
# ```
#
# Aquí no tenemos GitHub, así que vamos a **simular** lo que hace el runner:
#
# 1. Primero entendemos cómo se entera el CI de que algo falló (**códigos de salida**).
# 2. Luego corremos las 4 etapas, cada una en su propia "máquina limpia" (una carpeta
#    temporal vacía), pasándose archivos por un "almacén de artefactos", igual que
#    `upload-artifact` / `download-artifact`.
# 3. Implementamos la **compuerta de calidad** contra `DummyClassifier(strategy="most_frequent")`.
# 4. Simulamos modelos malos y vemos que la compuerta los bloquea **sin romper el notebook**
#    (capturando `SystemExit`).
# 5. Vemos un caso que la compuerta **no** detecta y por qué hacen falta pruebas de datos
#    (la parte de la Actividad 5).

# %%
import json
import os
import shutil
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")
RANDOM_STATE = 42
DATOS = Path("../datos/champions_league_matches.csv").resolve()
print("Dataset:", DATOS.name, "| existe:", DATOS.exists())

# %% [markdown]
# ## 1. Conocimiento previo: el código de salida (exit code)
#
# **Qué:** todo programa, al terminar, le devuelve al sistema operativo un número entero.
# `0` significa "todo bien"; cualquier otro número significa "algo falló".
#
# **Por qué importa:** GitHub Actions **no lee tus `print`**. Para decidir si un step queda
# en verde o en rojo, mira únicamente ese número. Por eso `evaluar.py` termina con
# `raise SystemExit(main())`: si `main()` devuelve `1`, el proceso sale con código 1 y el
# workflow falla.
#
# Lo comprobamos lanzando dos mini-programas como lo haría el runner:

# %%
for codigo in ["print('todo bien')", "raise SystemExit(1)", "1/0"]:
    r = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True)
    estado = "VERDE (step OK)" if r.returncode == 0 else "ROJO (step falla)"
    print(f"{codigo:<22} -> returncode={r.returncode}  {estado}")

# %% [markdown]
# **Interpretación:** un `print` normal devuelve 0; `raise SystemExit(1)` devuelve 1
# **a propósito** (así falla la compuerta); y una excepción no capturada (`1/0`) también
# devuelve 1. Para el CI las dos últimas son iguales: "rojo".
#
# Dentro de un notebook, en cambio, `SystemExit` no mata el proceso: lo podemos **capturar**
# con `try/except SystemExit`. Eso es lo que usaremos para simular la compuerta sin
# romper el notebook.

# %% [markdown]
# ## 2. Las 4 etapas, igual que en `src/`
#
# Copiamos la lógica de los scripts del Ejercicio 3. Cada función recibe la carpeta de
# trabajo de "su máquina" (`base`) y devuelve un código de salida, como `main()` en los
# scripts originales.
#
# - **extraer:** lee la fuente y la deja en `artefactos/crudo.csv`.
# - **limpiar:** quita las filas vacías (separadores de jornada), las filas sin etiqueta y
#   las columnas con **fuga** (`score`, `winner`) más las irrelevantes (`date`, `venue`, `referee`).
# - **entrenar:** convierte `'63%'` → 63.0 y `'3 of 10'` → 3 y 10, arma el `Pipeline`
#   (imputar + escalar + One-Hot + `LogisticRegression(C=0.541, class_weight="balanced")`)
#   y guarda `modelo.joblib` **y** `prueba.csv`.
# - **evaluar:** mide en prueba, compara contra el modelo trivial y aplica la compuerta.

# %%
OBJETIVO = "result"
FUGA = ["score", "winner"]
IRRELEVANTES = ["date", "venue", "referee"]
NUMERICAS = ["home_shots_on_target_pct", "away_shots_on_target_pct",
             "home_saves_pct", "away_saves_pct"]
PORCENTAJES = ["home_possession", "away_possession"]
RAZONES = ["home_shots_on_target", "away_shots_on_target", "home_saves", "away_saves"]
CATEGORICAS = ["home_team", "away_team"]
MINIMO_F1 = 0.40


def etapa_extraer(base: Path, fuente: Path = DATOS) -> int:
    salida = base / "artefactos/crudo.csv"
    salida.parent.mkdir(parents=True, exist_ok=True)
    if not fuente.exists():
        print(f"[extraer] ERROR: no encuentro {fuente}")
        return 1
    df = pd.read_csv(fuente)
    df.to_csv(salida, index=False)
    print(f"[extraer] {len(df)} filas y {df.shape[1]} columnas -> crudo.csv")
    return 0


def etapa_limpiar(base: Path) -> int:
    df = pd.read_csv(base / "artefactos/crudo.csv")
    antes = len(df)
    df = df.dropna(how="all").dropna(subset=[OBJETIVO])
    quitar = [c for c in FUGA + IRRELEVANTES if c in df.columns]
    df = df.drop(columns=quitar).reset_index(drop=True)
    df.to_csv(base / "artefactos/limpio.csv", index=False)
    print(f"[limpiar] {antes} -> {len(df)} filas (se eliminaron {antes - len(df)} vacias)")
    print(f"[limpiar] columnas descartadas: {quitar}")
    print(f"[limpiar] clases: {df[OBJETIVO].value_counts().to_dict()}")
    return 0


def convertir_texto_a_numero(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in PORCENTAJES:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace("%", "", regex=False)
                                .str.strip(), errors="coerce")
    for col in RAZONES:
        partes = df[col].astype(str).str.extract(r"(\d+)\s*of\s*(\d+)")
        df[col] = pd.to_numeric(partes[0], errors="coerce")
        df[col + "_intentos"] = pd.to_numeric(partes[1], errors="coerce")
    return df


def construir_pipeline(modelo=None) -> Pipeline:
    numericas = NUMERICAS + PORCENTAJES + RAZONES + [c + "_intentos" for c in RAZONES]
    pre = ColumnTransformer([
        ("num", Pipeline([("imputar", SimpleImputer(strategy="median")),
                          ("escalar", StandardScaler())]), numericas),
        ("cat", Pipeline([("imputar", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAS),
    ], remainder="drop")
    if modelo is None:
        modelo = LogisticRegression(C=0.541, class_weight="balanced",
                                    max_iter=5000, random_state=RANDOM_STATE)
    return Pipeline([("preprocesamiento", pre), ("modelo", modelo)])


def etapa_entrenar(base: Path, modelo=None, revolver_etiquetas=False) -> int:
    df = convertir_texto_a_numero(pd.read_csv(base / "artefactos/limpio.csv"))
    y, X = df[OBJETIVO], df.drop(columns=[OBJETIVO])
    X_ent, X_pru, y_ent, y_pru = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y)
    if revolver_etiquetas:   # solo para simular "datos corruptos" más adelante
        y_ent = pd.Series(np.random.RandomState(RANDOM_STATE).permutation(y_ent.values),
                          index=y_ent.index)
    pipe = construir_pipeline(modelo).fit(X_ent, y_ent)
    joblib.dump(pipe, base / "artefactos/modelo.joblib")
    prueba = X_pru.copy()
    prueba[OBJETIVO] = y_pru
    prueba.to_csv(base / "artefactos/prueba.csv", index=False)
    print(f"[entrenar] entrenamiento={len(X_ent)}  prueba={len(X_pru)}  "
          f"modelo={type(pipe.named_steps['modelo']).__name__}")
    return 0

# %% [markdown]
# ### La compuerta de calidad
#
# Es el corazón del Ejercicio 3: el pipeline no solo **ejecuta**, también **decide**.
# Dos criterios, cualquiera de los dos tumba el pipeline:
#
# 1. `f1_macro < 0.40` → no alcanza el mínimo que el equipo acordó.
# 2. `f1_macro <= f1_macro del modelo trivial` → no aprende nada que no sepa un modelo que
#    siempre dice la clase mayoritaria.
#
# ¿Por qué `f1_macro` y no `accuracy`? Porque las clases están desbalanceadas (Home Win es
# casi la mitad). El modelo trivial ya saca una accuracy "decente" sin aprender nada; el
# F1 macro promedia las tres clases por igual y lo desenmascara.

# %%
def etapa_evaluar(base: Path, verbose: bool = True) -> int:
    pipe = joblib.load(base / "artefactos/modelo.joblib")
    df = pd.read_csv(base / "artefactos/prueba.csv")
    y, X = df[OBJETIVO], df.drop(columns=[OBJETIVO])

    pred = pipe.predict(X)
    acc, f1 = accuracy_score(y, pred), f1_score(y, pred, average="macro")
    tonto = DummyClassifier(strategy="most_frequent").fit(X, y)
    pred_t = tonto.predict(X)
    acc_t = accuracy_score(y, pred_t)
    f1_t = f1_score(y, pred_t, average="macro", zero_division=0)

    metricas = {"accuracy": round(float(acc), 4), "f1_macro": round(float(f1), 4),
                "baseline_accuracy": round(float(acc_t), 4),
                "baseline_f1_macro": round(float(f1_t), 4), "minimo_exigido": MINIMO_F1}
    (base / "artefactos/metricas.json").write_text(json.dumps(metricas, indent=2))

    print(f"[evaluar] accuracy = {acc:.3f}   (modelo trivial: {acc_t:.3f})")
    print(f"[evaluar] f1_macro = {f1:.3f}   (modelo trivial: {f1_t:.3f})")
    if verbose:
        print(classification_report(y, pred, digits=3, zero_division=0))

    resumen = os.environ.get("GITHUB_STEP_SUMMARY")   # lo mismo que hacía evaluar.py
    if resumen:
        with open(resumen, "a", encoding="utf-8") as fh:
            fh.write("| Metrica | Modelo | Modelo trivial |\n|---|---|---|\n")
            fh.write(f"| accuracy | {acc:.3f} | {acc_t:.3f} |\n")
            fh.write(f"| f1_macro | {f1:.3f} | {f1_t:.3f} |\n")

    if f1 < MINIMO_F1:
        print(f"[evaluar] FALLA: f1_macro {f1:.3f} < minimo {MINIMO_F1}")
        return 1
    if f1 <= f1_t:
        print("[evaluar] FALLA: el modelo no le gana al modelo trivial")
        return 1
    print(f"[evaluar] OK: supera el minimo ({MINIMO_F1}) y al modelo trivial")
    return 0

# %% [markdown]
# ## 3. Un mini "GitHub Actions" casero
#
# **Qué simulamos:**
#
# | En GitHub Actions | Aquí |
# |---|---|
# | `runs-on: ubuntu-latest` (VM nueva por job) | una carpeta temporal **vacía** por job |
# | `upload-artifact` | copiar archivos al `almacen/<nombre>` |
# | `download-artifact` | copiar de `almacen/<nombre>` a la carpeta del job |
# | `needs: job_anterior` | si un job falla, los siguientes quedan `skipped` |
# | `run: python src/evaluar.py` | `raise SystemExit(etapa(...))` capturado con `except SystemExit` |
#
# **Por qué así:** la lección más importante de los artefactos es que **los jobs no comparten
# disco**. Si `limpiar` intentara leer `crudo.csv` sin descargarlo, fallaría, igual que en GitHub.

# %%
def correr_step(funcion, *args, **kwargs) -> int:
    """Ejecuta una etapa como si fuera un script: `raise SystemExit(main())`.
    Capturamos SystemExit para que el notebook siga vivo y leemos el código."""
    try:
        raise SystemExit(funcion(*args, **kwargs))
    except SystemExit as salida:
        return int(salida.code or 0)


def correr_workflow(jobs, nombre="Pipeline de ML"):
    """jobs: lista de dicts con id, needs, descarga, funcion, sube.
    Devuelve una tabla con el estado de cada job."""
    raiz = Path(tempfile.mkdtemp(prefix="actions_"))
    almacen = raiz / "almacen"
    estado = {}
    print(f"=== workflow: {nombre} ===")
    for job in jobs:
        if job["needs"] and estado.get(job["needs"]) != "success":
            estado[job["id"]] = "skipped"
            print(f"\n--- job {job['id']}: SKIPPED (needs: {job['needs']} no terminó bien)")
            continue
        maquina = raiz / f"runner_{job['id']}"          # máquina limpia
        (maquina / "artefactos").mkdir(parents=True)
        print(f"\n--- job {job['id']} (máquina limpia: {sorted(os.listdir(maquina / 'artefactos'))})")
        for art in job["descarga"]:                     # download-artifact
            for f in (almacen / art).iterdir():
                shutil.copy(f, maquina / "artefactos" / f.name)
            print(f"[download-artifact] {art}")
        codigo = correr_step(job["funcion"], maquina, **job.get("kwargs", {}))
        if codigo == 0:
            for art, archivos in job["sube"].items():   # upload-artifact
                (almacen / art).mkdir(parents=True, exist_ok=True)
                for a in archivos:
                    shutil.copy(maquina / "artefactos" / a, almacen / art / a)
                print(f"[upload-artifact] {art}: {archivos}")
        estado[job["id"]] = "success" if codigo == 0 else "failure"
        print(f"--- job {job['id']}: exit code {codigo} -> {estado[job['id']].upper()}")
    shutil.rmtree(raiz)
    return pd.Series(estado, name="estado")


def definir_jobs(kwargs_entrenar=None):
    return [
        {"id": "extraer", "needs": None, "descarga": [], "funcion": etapa_extraer,
         "sube": {"datos-crudos": ["crudo.csv"]}},
        {"id": "limpiar", "needs": "extraer", "descarga": ["datos-crudos"],
         "funcion": etapa_limpiar, "sube": {"datos-limpios": ["limpio.csv"]}},
        {"id": "entrenar", "needs": "limpiar", "descarga": ["datos-limpios"],
         "funcion": etapa_entrenar, "kwargs": kwargs_entrenar or {},
         "sube": {"modelo": ["modelo.joblib", "prueba.csv"]}},
        {"id": "evaluar", "needs": "entrenar", "descarga": ["modelo"],
         "funcion": etapa_evaluar, "sube": {"metricas": ["metricas.json"]}},
    ]

# %% [markdown]
# ### 3.1 Corrida normal (lo que pasó en el Ejercicio 3)
#
# Además simulamos `GITHUB_STEP_SUMMARY`: en GitHub es un archivo cuyo contenido Markdown
# aparece como resumen en la página de la ejecución.

# %%
resumen_md = Path(tempfile.mkstemp(suffix=".md")[1])
os.environ["GITHUB_STEP_SUMMARY"] = str(resumen_md)
estado_ok = correr_workflow(definir_jobs())
print("\nResumen del workflow:\n", estado_ok.to_string())
print("\nLo que GitHub mostraría en el Step Summary:\n" + resumen_md.read_text())
del os.environ["GITHUB_STEP_SUMMARY"]

# %% [markdown]
# **Interpretación:** los 4 jobs salen en verde. Limpiar dejó 144 partidos (se fueron las 7
# filas vacías) y entrenar separó 115 para entrenamiento y 29 para prueba. El modelo saca
# **accuracy 0.621 y f1_macro 0.542**, contra **0.483 y 0.217** del modelo trivial: son
# exactamente los números del PDF del Ejercicio 3. Ojo con la accuracy del trivial (0.483):
# parece "casi 50 %", pero su F1 macro de 0.217 revela que solo acierta una clase.
#
# Nota también la clase `Draw`: F1 de 0.182 con solo 5 empates en prueba. El modelo pasa la
# compuerta, pero los empates siguen siendo su punto débil.

# %% [markdown]
# ## 4. ¿Qué pasa si el modelo es malo? La compuerta lo bloquea
#
# Simulamos dos maneras realistas de que llegue un modelo malo **sin que nadie toque el
# código del pipeline**:
#
# - **Caso A — etiquetas corruptas:** alguien rompe el archivo y las etiquetas de
#   entrenamiento quedan revueltas. El modelo aprende ruido.
# - **Caso B — hiperparámetro absurdo:** un compañero cambia a `C=1e-6` sin `class_weight`.
#   La regularización es tan fuerte que el modelo acaba diciendo siempre la clase mayoritaria.

# %%
estado_a = correr_workflow(definir_jobs({"revolver_etiquetas": True}),
                           nombre="Caso A: etiquetas revueltas")

# %%
modelo_malo = LogisticRegression(C=1e-6, max_iter=5000, random_state=RANDOM_STATE)
estado_b = correr_workflow(definir_jobs({"modelo": modelo_malo}),
                           nombre="Caso B: C=1e-6")

# %%
comparacion = pd.DataFrame({"normal": estado_ok, "caso A (etiquetas)": estado_a,
                            "caso B (C=1e-6)": estado_b})
comparacion

# %% [markdown]
# **Interpretación:** en los dos casos `extraer`, `limpiar` y `entrenar` salen en **verde**:
# el código corrió sin excepciones. Solo `evaluar` sale en **rojo** (exit code 1):
#
# - Caso A: f1_macro de 0.320, por debajo del mínimo de 0.40 → bloqueado por el criterio 1.
# - Caso B: el modelo predice siempre "Home Win" (recall 1.000 en Home Win y 0 en las demás);
#   su accuracy (0.483) y su f1_macro (0.217) son **idénticos** a los del trivial. Viola los dos
#   criterios; el script reporta el primero que revisa (`f1 < 0.40`) y sale con 1.
#
# Fíjate en el caso A: su accuracy (0.345) es incluso **peor** que la del trivial (0.483).
#
# Esa es la diferencia entre "el pipeline corre" y "el pipeline decide". Y gracias a
# `except SystemExit` el notebook sigue vivo: en GitHub, en cambio, el workflow quedaría
# en rojo y el PR mostraría una ❌.
#
# Un detalle: con este dataset el trivial saca 0.217 < 0.40, así que el criterio 1 ya
# implica el 2. El segundo criterio importa si algún día cambian los datos y la clase
# mayoritaria domina más (p. ej. un dataset 90/10).

# %% [markdown]
# ## 5. Lo que la compuerta NO ve: cambio silencioso de formato
#
# El PDF del Ejercicio 3 lo dice en la reflexión: *"Nuestro pipeline asume que la posesión
# sigue llegando como '63%' y los tiros como '3 of 10'. Si la fuente cambiara de formato, el
# pipeline correría sin quejarse y produciría un modelo malo en silencio."*
#
# Probémoslo: la fuente ahora escribe los tiros y atajadas como `'3/10'` en lugar de `'3 of 10'`.

# %%
tmp_fuente = Path(tempfile.mkdtemp()) / "fuente_nueva.csv"
fuente_nueva = pd.read_csv(DATOS)
for col in RAZONES:
    fuente_nueva[col] = fuente_nueva[col].str.replace(" of ", "/", regex=False)
fuente_nueva.to_csv(tmp_fuente, index=False)
print(fuente_nueva[RAZONES].head(3))

jobs_formato = definir_jobs()
jobs_formato[0]["kwargs"] = {"fuente": tmp_fuente}
estado_c = correr_workflow(jobs_formato, nombre="Caso C: formato '3/10'")

# %%
conv = convertir_texto_a_numero(fuente_nueva.dropna(how="all"))
nulos = conv[RAZONES + [c + "_intentos" for c in RAZONES]].isna().mean()
print("Proporción de nulos tras convertir (formato nuevo):")
print(nulos.round(2).to_string())

# %% [markdown]
# **Interpretación:** ¡el workflow sale **todo verde**! Con el formato nuevo la regex
# `(\d+)\s*of\s*(\d+)` no encuentra nada, así que **8 columnas quedan 100 % nulas** y el
# `SimpleImputer` simplemente las descarta. Aun así el modelo saca accuracy 0.621 y
# **f1_macro 0.550** (¡incluso un poco más que el 0.542 original!) porque todavía tiene la
# posesión, los porcentajes de tiros/atajadas y los equipos. Pasa la compuerta y nadie se
# entera de que perdió 8 variables: con 29 partidos de prueba, una diferencia de 0.008 es
# puro ruido, no una mejora.
#
# Lección: la compuerta de **métricas** no reemplaza a las pruebas de **datos**. Por eso en la
# práctica se agrega un job de pruebas (pytest) antes de entrenar.

# %% [markdown]
# ## 6. Pruebas automáticas (Actividad 5): validar código, datos y modelo
#
# En CI las pruebas se escriben como funciones `test_*` con `assert` y se corren con `pytest`
# (ver `ejemplos/test_pipeline.py` y `ejemplos/ci-pytest-matrix.yml`). Aquí no tenemos pytest
# instalado, así que hacemos un mini-runner que hace lo mismo: corre cada prueba, atrapa el
# `AssertionError` y al final devuelve 0 o 1.

# %%
def test_convierte_porcentaje_y_razones(df_crudo):
    out = convertir_texto_a_numero(pd.DataFrame({
        "home_possession": ["63%"], "away_possession": ["37%"],
        "home_shots_on_target": ["3 of 10"], "away_shots_on_target": ["8 of 18"],
        "home_saves": ["4 of 8"], "away_saves": ["2 of 3"]}))
    assert out.loc[0, "home_possession"] == 63.0
    assert out.loc[0, "home_shots_on_target_intentos"] == 10.0


def test_columnas_esperadas(df_crudo):
    faltan = {"home_team", "away_team", "home_possession", OBJETIVO} - set(df_crudo.columns)
    assert not faltan, f"faltan columnas: {faltan}"


def test_formato_de_tiros(df_crudo):
    ok = df_crudo["home_shots_on_target"].astype(str).str.fullmatch(r"\d+ of \d+").mean()
    assert ok > 0.95, f"solo {ok:.0%} de filas con formato 'N of M'"


def test_sin_nulos_tras_convertir(df_crudo):
    conv = convertir_texto_a_numero(df_crudo)
    peor = conv[RAZONES + PORCENTAJES].isna().mean().max()
    assert peor < 0.05, f"una columna quedó con {peor:.0%} de nulos"


def test_clases_validas(df_crudo):
    extra = set(df_crudo[OBJETIVO].dropna()) - {"Home Win", "Away Win", "Draw"}
    assert not extra, f"clases desconocidas: {extra}"


PRUEBAS = [test_convierte_porcentaje_y_razones, test_columnas_esperadas,
           test_formato_de_tiros, test_sin_nulos_tras_convertir, test_clases_validas]


def mini_pytest(ruta_csv) -> int:
    df_crudo = pd.read_csv(ruta_csv).dropna(how="all")
    fallas = 0
    for prueba in PRUEBAS:
        try:
            prueba(df_crudo)
            print(f"PASSED  {prueba.__name__}")
        except AssertionError as e:
            fallas += 1
            print(f"FAILED  {prueba.__name__}: {e}")
    print(f"== {len(PRUEBAS) - fallas} passed, {fallas} failed ==")
    return 1 if fallas else 0


print("Datos originales:")
print("exit code:", correr_step(mini_pytest, DATOS))
print("\nFuente con formato '3/10':")
print("exit code:", correr_step(mini_pytest, tmp_fuente))

# %% [markdown]
# **Interpretación:** con los datos originales pasan las 5 pruebas (exit code 0). Con la
# fuente nueva fallan `test_formato_de_tiros` y `test_sin_nulos_tras_convertir` y el runner
# devuelve 1: en GitHub el job `pruebas` quedaría rojo y, con `needs: pruebas`, `entrenar`
# **ni siquiera se intentaría**. Justo lo que la compuerta de métricas no pudo atrapar.
#
# Así se ve el pipeline completo "a prueba de balas":
#
# ```
# lint -> pruebas (código + datos) -> extraer -> limpiar -> entrenar -> evaluar (compuerta del modelo)
# ```

# %% [markdown]
# ## Resumen
#
# - El CI decide verde/rojo **solo** con el **código de salida**: 0 = éxito, ≠0 = falla.
#   `raise SystemExit(main())` es el puente entre tu script y GitHub Actions.
# - Cada job corre en una **máquina limpia**: los resultados viajan como artefactos
#   (`upload-artifact` → `download-artifact`) y el orden lo pone `needs:`.
# - Corrida normal: **accuracy 0.621 / f1_macro 0.542** contra **0.483 / 0.217** del trivial
#   (115 entrenamiento, 29 prueba), igual que en el Ejercicio 3.
# - La **compuerta de calidad** bloqueó los dos modelos malos: etiquetas revueltas
#   (f1 0.320 < 0.40) y `C=1e-6` (f1 0.217, igual al trivial). Los jobs previos quedaron verdes:
#   en ML el pipeline puede fallar aunque el código esté bien.
# - Un cambio de formato (`'3 of 10'` → `'3/10'`) dejó 8 columnas vacías y **pasó la compuerta**
#   (f1 0.550). Solo las **pruebas de datos** lo detectaron. En ML hay que validar código,
#   datos **y** modelo.
