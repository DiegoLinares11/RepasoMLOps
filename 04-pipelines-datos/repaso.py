# %% [markdown]
# # 04 · Mini pipeline de datos con pandas
#
# En este notebook construimos, paso a paso, un **pipeline de datos** pequeño pero
# completo sobre el CSV de la Champions League:
#
# ```
# extraer  →  validar (crudo)  →  limpiar  →  transformar  →  validar (limpio)  →  guardar
# ```
#
# **Analogía (la del video de IBM que usamos en la Tarea 3):** el agua no va directo del río a
# tu llave. Se recolecta, pasa por tuberías, se purifica en una planta, se revisa su calidad y
# hasta entonces se distribuye. Con los datos es igual: el CSV crudo es el río; la función
# `limpiar` es la planta de tratamiento; los `assert` de `validar` son el laboratorio que revisa
# que el agua sea potable; `guardar` es la red que la reparte.
#
# Cada etapa es **una función separada**. ¿Por qué no un solo bloque de código gigante?
#
# - Se puede probar y depurar cada etapa por aparte.
# - Si cambia la fuente (de CSV a SQL), solo cambia `extraer`.
# - El orquestador final (`correr_pipeline`) se lee como una receta.
#
# Al final comprobamos la propiedad más importante de un pipeline: la **idempotencia**
# (correrlo dos veces da exactamente lo mismo).

# %% [markdown]
# ## 0. Configuración
#
# Importamos solo pandas, numpy y la librería estándar. `RANDOM_STATE` no se usa para azar aquí
# (este pipeline es determinista), pero lo dejamos por convención del repo. La salida va a la
# carpeta `salida/` del tema (está en `.gitignore`, porque es un archivo **generado**: se
# reconstruye corriendo el pipeline, no se versiona).

# %%
import hashlib
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
RANDOM_STATE = 42

RUTA_CRUDO = Path("../datos/champions_league_matches.csv")
CARPETA_SALIDA = Path("salida")

pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 20)
print("pandas", pd.__version__)

# %% [markdown]
# ## 1. Extraer (Extract)
#
# **Qué:** traer los datos desde su origen al entorno de trabajo. Aquí es un CSV, así que basta
# `pd.read_csv`. Si la fuente fuera Excel, JSON, SQL o una API, cambiaría solo esta función
# (`read_excel`, `read_json`, `read_sql`, `json_normalize`...).
#
# **Por qué una función:** el resto del pipeline no tiene por qué saber de dónde vienen los
# datos. Si mañana el CSV se reemplaza por una tabla de PostgreSQL, solo se toca aquí.

# %%
def extraer(ruta: Path = RUTA_CRUDO) -> pd.DataFrame:
    """Extract: lee el CSV crudo tal cual, sin tocar nada."""
    return pd.read_csv(ruta)


crudo = extraer()
print("Forma del CSV crudo:", crudo.shape)
crudo.head(3)

# %% [markdown]
# Lo primero después de extraer es **inspeccionar**: ¿qué tipos llegaron? ¿cuántos nulos?
# `info()` responde las dos cosas a la vez.

# %%
crudo.info()

# %% [markdown]
# **Interpretación:** casi todo llegó como texto (`str`/`object`), incluso columnas que son
# números: `home_possession` ('63%') y `home_shots_on_target` ('3 of 10'). Solo las cuatro
# columnas `*_pct` llegaron como `float64`. Además todas las columnas tienen 144 valores no
# nulos de 151 filas: hay filas vacías. Vamos a contarlas.

# %%
nulos = crudo.isna().sum()
print("Nulos por columna (solo las que tienen):")
print(nulos[nulos > 0])
print("\nTotal de nulos en el CSV crudo:", int(crudo.isna().sum().sum()))
print("Filas TOTALMENTE vacías       :", int(crudo.isna().all(axis=1).sum()))

# %% [markdown]
# **Interpretación:** hay **7 filas totalmente vacías** (separan jornadas en el CSV original),
# que aportan 7 × 18 = 126 nulos. Los otros 3 nulos están en `home_saves_pct`: 129 en total,
# igual que reportamos en el Ejercicio 2. Ahora veamos esos 3 casos especiales:

# %%
crudo.loc[crudo["home_saves_pct"].isna() & crudo["home_team"].notna(),
          ["home_team", "away_team", "home_saves", "home_saves_pct"]]

# %% [markdown]
# **Interpretación:** el portero local tuvo `0 of 0` atajadas, y 0/0 es una división indefinida.
# No es un error de captura: es un nulo **con significado**. Eso cambia la decisión: no lo
# borramos, lo dejamos documentado (y en el pipeline de ML, tema 05, se imputa con la mediana).

# %% [markdown]
# ## 2. Validar el crudo (antes de transformar)
#
# **Qué:** revisar que lo que llegó tiene la forma que esperamos: columnas, valores permitidos,
# formatos. Usamos `assert`: si algo no cuadra, el pipeline **se detiene con un mensaje claro**.
#
# **Por qué:** un pipeline que sigue corriendo con datos rotos es peor que uno que falla. Si la
# fuente cambia (alguien renombra una columna o el proveedor cambia '63%' por '0.63'), queremos
# enterarnos en la etapa 2, no cuando el modelo ya predice basura. Es el "laboratorio de
# calidad" de la planta de agua.

# %%
COLUMNAS_ESPERADAS = [
    "date", "home_team", "away_team", "score", "venue", "referee",
    "home_possession", "away_possession", "home_shots_on_target", "away_shots_on_target",
    "home_saves", "away_saves", "home_shots_on_target_pct", "away_shots_on_target_pct",
    "home_saves_pct", "away_saves_pct", "result", "winner",
]
RESULTADOS_VALIDOS = {"Home Win", "Away Win", "Draw"}
PATRON_PORCENTAJE = r"^\d{1,3}%$"          # '63%'
PATRON_RAZON = r"^\d+ of \d+$"             # '3 of 10'


def validar_crudo(df: pd.DataFrame) -> pd.DataFrame:
    """Valida el esquema y los formatos del CSV crudo. Devuelve el df intacto."""
    faltan = set(COLUMNAS_ESPERADAS) - set(df.columns)
    assert not faltan, f"Faltan columnas: {faltan}"
    assert len(df) > 0, "El archivo llegó vacío"

    partidos = df.dropna(how="all")  # las filas vacías se tratan en limpiar()
    raros = set(partidos["result"].dropna()) - RESULTADOS_VALIDOS
    assert not raros, f"Valores de result no permitidos: {raros}"

    for col in ["home_possession", "away_possession"]:
        ok = partidos[col].str.match(PATRON_PORCENTAJE)
        assert ok.all(), f"{col}: formato inesperado en {(~ok).sum()} filas"
    for col in ["home_shots_on_target", "away_shots_on_target", "home_saves", "away_saves"]:
        ok = partidos[col].str.match(PATRON_RAZON)
        assert ok.all(), f"{col}: formato inesperado en {(~ok).sum()} filas"
    return df


validar_crudo(crudo)
print("Validación del crudo: OK")

# %% [markdown]
# ¿Y si llega un archivo roto? Simulemos que el proveedor cambió el formato de la posesión en
# una fila. La validación debe **frenar** el pipeline:

# %%
roto = crudo.copy()
roto.loc[0, "home_possession"] = "0.63"
try:
    validar_crudo(roto)
except AssertionError as e:
    print("El pipeline se detuvo ->", e)

# %% [markdown]
# **Interpretación:** el `assert` detectó la única fila mala entre 144 partidos y dijo
# exactamente qué columna falló. Sin esta validación, `str.replace('%', '')` habría dejado
# `0.63` y el modelo habría creído que ese equipo tuvo 0.63 % de posesión.

# %% [markdown]
# ## 3. Limpiar
#
# **Qué:** quitar lo que no es un partido y dejar los tipos básicos correctos.
#
# | Comando | Para qué aquí |
# |---|---|
# | `dropna(how="all")` | quita las 7 filas separadoras (vacías por completo) |
# | `dropna(subset=["result"])` | una fila sin etiqueta no sirve para el modelo |
# | `drop_duplicates()` | si la fuente repite un partido, se cuenta una vez |
# | `str.strip()` | '  PSV ' y 'PSV' serían dos equipos distintos |
# | `pd.to_datetime` | la fecha llega como texto; como fecha se puede ordenar y filtrar |
# | `reset_index(drop=True)` | índice limpio 0..n-1 después de borrar filas |
#
# Fíjate que **nunca modificamos `df` en su lugar**: cada paso devuelve un DataFrame nuevo.
# Eso es clave para la idempotencia (la entrada no cambia aunque llames la función 10 veces).

# %%
COLUMNAS_TEXTO = ["home_team", "away_team", "venue", "referee", "result", "winner"]


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """Quita filas vacías/duplicadas, normaliza texto y fecha."""
    df = (
        df.dropna(how="all")
          .dropna(subset=["result"])
          .drop_duplicates()
          .copy()
    )
    for col in COLUMNAS_TEXTO:
        df[col] = df[col].str.strip()
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    return df.sort_values(["date", "home_team"]).reset_index(drop=True)


limpio = limpiar(crudo)
print("Antes :", crudo.shape)
print("Después:", limpio.shape)
print("Tipo de date:", limpio["date"].dtype)
print("Rango de fechas:", limpio["date"].min().date(), "->", limpio["date"].max().date())

# %% [markdown]
# **Interpretación:** de 151 filas quedan **144 partidos** (las 7 vacías fuera, 0 duplicados).
# La fecha ya es `datetime64`, y por eso podemos pedir el mínimo y el máximo: la muestra va del
# 16 de septiembre de 2025 al 28 de enero de 2026.

# %% [markdown]
# ## 4. Transformar
#
# **Qué:** convertir los "números disfrazados de texto" y crear variables nuevas.
#
# - `str.replace("%", "")` + `astype(float)`: '63%' → 63.0
# - `str.extract(r"(\d+) of (\d+)")`: '3 of 10' → dos columnas, 3 y 10. Cada par de paréntesis
#   del regex es un **grupo de captura** y se vuelve una columna.
# - `str.extract` sobre `score` ('1–3', con guion largo) para tener goles numéricos.
#
# Ojo: `score` y `winner` **revelan el resultado**. En un pipeline de *datos* para reportes
# está bien usarlas (queremos saber los goles). En el pipeline de *ML* (tema 05) se eliminan
# porque serían fuga de información.
#
# Cada transformación es una funcioncita, y las encadenamos con **`.pipe()`**. `df.pipe(f)` es
# lo mismo que `f(df)`, pero permite leer la cadena de arriba a abajo, en el orden en que pasa.

# %%
def convertir_porcentajes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["home_possession", "away_possession"]:
        df[col] = df[col].str.replace("%", "", regex=False).astype(float)
    return df


def separar_razones(df: pd.DataFrame) -> pd.DataFrame:
    """'3 of 10' -> <col>_hechos = 3, <col>_intentos = 10 (y borra la columna de texto)."""
    df = df.copy()
    for col in ["home_shots_on_target", "away_shots_on_target", "home_saves", "away_saves"]:
        partes = df[col].str.extract(r"(\d+)\s*of\s*(\d+)")
        df[f"{col}_hechos"] = partes[0].astype(int)
        df[f"{col}_intentos"] = partes[1].astype(int)
    return df.drop(columns=["home_shots_on_target", "away_shots_on_target",
                            "home_saves", "away_saves"])


def extraer_goles(df: pd.DataFrame) -> pd.DataFrame:
    goles = df["score"].str.extract(r"(\d+)\s*[–-]\s*(\d+)").astype(int)
    return df.assign(home_goals=goles[0], away_goals=goles[1])


def agregar_variables(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(
        diferencia_posesion=df["home_possession"] - df["away_possession"],
        jornada=df["date"].dt.strftime("%Y-%m-%d"),
    )


def transformar(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.pipe(convertir_porcentajes)
          .pipe(separar_razones)
          .pipe(extraer_goles)
          .pipe(agregar_variables)
    )


transformado = transformar(limpio)
transformado[["home_team", "away_team", "home_possession", "home_shots_on_target_hechos",
              "home_shots_on_target_intentos", "home_goals", "away_goals",
              "diferencia_posesion"]].head()

# %%
print(transformado.dtypes.value_counts())

# %% [markdown]
# **Interpretación:** la posesión ya es `float64`, los tiros y atajadas son enteros en dos
# columnas cada uno, y tenemos goles numéricos. Ya se puede hacer aritmética (promedios,
# diferencias), cosa imposible con '63%'.

# %% [markdown]
# ## 5. Validar el resultado (después de transformar)
#
# La segunda validación revisa **reglas de negocio**, no solo formatos:
#
# - Quedan 144 partidos y sin nulos en las columnas clave.
# - La posesión de ambos suma ~100 (por redondeo puede dar 101).
# - No puede haber más tiros a puerta que tiros totales (`hechos <= intentos`).
# - **Consistencia entre columnas:** si el local metió más goles, `result` debe ser `Home Win`.

# %%
def validar_limpio(df: pd.DataFrame) -> pd.DataFrame:
    assert len(df) == 144, f"Se esperaban 144 partidos y hay {len(df)}"
    clave = ["date", "home_team", "away_team", "home_possession", "result", "home_goals"]
    assert df[clave].notna().all().all(), "Hay nulos en columnas clave"

    suma = df["home_possession"] + df["away_possession"]
    assert suma.between(99, 101).all(), "La posesión no suma ~100"

    for lado in ["home", "away"]:
        for cosa in ["shots_on_target", "saves"]:
            h, i = df[f"{lado}_{cosa}_hechos"], df[f"{lado}_{cosa}_intentos"]
            assert (h <= i).all(), f"{lado}_{cosa}: hechos > intentos"

    esperado = np.select(
        [df["home_goals"] > df["away_goals"], df["home_goals"] < df["away_goals"]],
        ["Home Win", "Away Win"], default="Draw",
    )
    assert (df["result"] == esperado).all(), "result no coincide con el marcador"
    return df


validar_limpio(transformado)
print("Validación del resultado: OK")
suma_posesion = transformado["home_possession"] + transformado["away_possession"]
print("Suma de posesión observada:", suma_posesion.value_counts().sort_index().to_dict())

# %% [markdown]
# **Interpretación:** pasan todas las reglas. La posesión suma 100 en 132 partidos y 101 en
# 12 (redondeo de la fuente), por eso la regla usa `between(99, 101)` y no `== 100`: una validación demasiado
# estricta también es un error, porque detiene el pipeline con datos que están bien.

# %% [markdown]
# ## 6. Agregar: resumir con `groupby` / `agg`
#
# Agrupar es pasar de "144 partidos uno por uno" a "un renglón por categoría". La sintaxis
# `agg(nombre=("columna", "funcion"))` (named aggregation) deja nombres de columna legibles.

# %%
resumen_resultado = (
    transformado.groupby("result")
    .agg(partidos=("result", "size"),
         posesion_media=("home_possession", "mean"),
         tiros_puerta_local=("home_shots_on_target_hechos", "mean"))
    .round(1)
)
resumen_resultado

# %% [markdown]
# **Interpretación:** es la misma tabla del Ejercicio 2: Home Win 71 partidos con 53.6 % de
# posesión local, Away Win 48 con 48.5 %, Draw 25 con 48.3 %. Cuando gana el local también
# tira más a puerta en promedio. Es la ventaja de localía del Ejercicio 1 en un solo comando.
#
# Ahora una tabla **por equipo**. Un equipo aparece a veces como local y a veces como visitante,
# así que se agrega por separado cada rol y luego se **une** con `merge`, como un JOIN de SQL.

# %%
def puntos(goles_a_favor, goles_en_contra):
    return np.select([goles_a_favor > goles_en_contra, goles_a_favor == goles_en_contra],
                     [3, 1], default=0)


def tabla_equipos(df: pd.DataFrame) -> pd.DataFrame:
    como_local = (
        df.assign(pts=puntos(df["home_goals"], df["away_goals"]))
          .groupby("home_team")
          .agg(pj_local=("pts", "size"), pts_local=("pts", "sum"),
               gf_local=("home_goals", "sum"), gc_local=("away_goals", "sum"))
    )
    como_visita = (
        df.assign(pts=puntos(df["away_goals"], df["home_goals"]))
          .groupby("away_team")
          .agg(pj_visita=("pts", "size"), pts_visita=("pts", "sum"),
               gf_visita=("away_goals", "sum"), gc_visita=("home_goals", "sum"))
    )
    tabla = (
        como_local.merge(como_visita, left_index=True, right_index=True, how="outer")
                  .fillna(0).astype(int)
    )
    tabla["pj"] = tabla["pj_local"] + tabla["pj_visita"]
    tabla["pts"] = tabla["pts_local"] + tabla["pts_visita"]
    tabla["dg"] = (tabla["gf_local"] + tabla["gf_visita"]
                   - tabla["gc_local"] - tabla["gc_visita"])
    tabla.index.name = "equipo"
    return (tabla.reset_index()
                 .sort_values(["pts", "dg", "equipo"], ascending=[False, False, True])
                 .reset_index(drop=True))


equipos = tabla_equipos(transformado)
print("Equipos:", len(equipos), "| partidos contados (cada uno dos veces):", equipos["pj"].sum())
equipos[["equipo", "pj", "pts", "pts_local", "pts_visita", "dg"]].head(8)

# %% [markdown]
# **Interpretación:** hay 36 equipos y la suma de partidos jugados es 288 = 2 × 144 (cada
# partido cuenta para dos equipos): esa cuenta es en sí misma una validación del `merge`. Si
# hubiéramos usado `how="inner"` y algún equipo solo hubiera jugado de local, habría
# desaparecido de la tabla; con `how="outer"` + `fillna(0)` no se pierde nadie.
#
# Comparar `pts_local` contra `pts_visita` es otra forma de ver la ventaja de localía.

# %%
print("Puntos totales como local :", int(equipos["pts_local"].sum()))
print("Puntos totales como visita:", int(equipos["pts_visita"].sum()))

# %% [markdown]
# **Interpretación:** los equipos sumaron 238 puntos jugando en casa contra 169 de visita, un
# 41 % más como locales con el mismo número de partidos en cada rol. El Arsenal, líder con 24
# puntos (8 de 8 ganados), es la excepción que gana igual en ambos lados.

# %% [markdown]
# ## 7. Guardar (Load)
#
# **Qué:** dejar los datos limpios donde otros los puedan usar. Con pandas: `to_csv`,
# `to_excel`, `to_json`, `to_parquet`, `to_sql`.
#
# **Detalles que hacen la diferencia:**
#
# - `index=False`: si no, pandas escribe el índice como una columna extra sin nombre.
# - Modo `"w"` (sobrescribir, el que usa `to_csv` por defecto) y no `"a"` (agregar): esto es
#   lo que hace que el guardado sea **idempotente**. Lo comprobamos abajo.
# - Orden determinista (`sort_values` en `limpiar`): mismo contenido → mismo archivo, byte por
#   byte.

# %%
def guardar(df: pd.DataFrame, tabla: pd.DataFrame, carpeta: Path = CARPETA_SALIDA) -> dict:
    carpeta.mkdir(exist_ok=True)
    rutas = {"partidos": carpeta / "partidos_limpios.csv",
             "equipos": carpeta / "tabla_equipos.csv"}
    df.to_csv(rutas["partidos"], index=False, date_format="%Y-%m-%d")
    tabla.to_csv(rutas["equipos"], index=False)
    return rutas


def huella(ruta: Path) -> str:
    """Hash MD5 del archivo: si cambia un solo byte, cambia la huella."""
    return hashlib.md5(ruta.read_bytes()).hexdigest()[:12]


rutas = guardar(transformado, equipos)
for nombre, ruta in rutas.items():
    print(f"{nombre:<9} -> {ruta}  ({ruta.stat().st_size} bytes, md5 {huella(ruta)})")

# %% [markdown]
# ## 8. El orquestador: todo el pipeline en una receta
#
# Con las etapas listas, el pipeline completo cabe en pocas líneas. `.pipe()` hace que se lea
# en el mismo orden en que ocurre. En producción, este papel lo hace un orquestador como
# Airflow, Prefect o Dagster (que además agenda, reintenta y monitorea); aquí basta una función.

# %%
def correr_pipeline(ruta_crudo: Path = RUTA_CRUDO, carpeta: Path = CARPETA_SALIDA):
    partidos = (
        extraer(ruta_crudo)
        .pipe(validar_crudo)
        .pipe(limpiar)
        .pipe(transformar)
        .pipe(validar_limpio)
    )
    tabla = tabla_equipos(partidos)
    rutas = guardar(partidos, tabla, carpeta)
    return partidos, {k: huella(r) for k, r in rutas.items()}


partidos_1, huellas_1 = correr_pipeline()
print("Corrida 1:", partidos_1.shape, huellas_1)

# %% [markdown]
# ## 9. Idempotencia: correrlo dos veces da lo mismo
#
# **Idempotente** = aplicar la operación una vez o muchas deja el **mismo estado final**.
# Como el botón del ascensor: presionarlo 5 veces no hace que llegue 5 veces.
#
# **Por qué importa:** los pipelines fallan a medias y se reintentan; los orquestadores los
# vuelven a correr; alguien los ejecuta "por si acaso". Si cada corrida duplicara filas o
# cambiara el archivo, nadie podría confiar en los datos. Lo comprobamos de tres maneras:

# %%
partidos_2, huellas_2 = correr_pipeline()
print("Corrida 2:", partidos_2.shape, huellas_2)
print("\n¿Mismo DataFrame?        ", partidos_1.equals(partidos_2))
print("¿Mismos archivos (md5)?  ", huellas_1 == huellas_2)

# limpiar es idempotente como función: limpiar(limpiar(x)) == limpiar(x)
print("¿limpiar(limpiar(x)) == limpiar(x)?", limpiar(limpiar(crudo)).equals(limpiar(crudo)))
print("¿El crudo quedó intacto?  ", crudo.equals(extraer()))

# %% [markdown]
# **Interpretación:** las dos corridas producen el mismo DataFrame y archivos con la misma
# huella MD5, byte por byte. Además el DataFrame crudo no fue modificado por ninguna etapa
# (todas trabajan sobre copias).
#
# Un matiz importante: `transformar` **no** es idempotente como función suelta (la segunda vez
# la posesión ya es número y `.str.replace` falla). Por eso el pipeline siempre arranca
# **desde la fuente cruda**: lo que debe ser idempotente es la corrida completa
# fuente → destino, no necesariamente cada paso intermedio.
#
# ### Anti-ejemplo: un guardado que NO es idempotente
# Si en vez de sobrescribir usáramos modo `"a"` (append), cada corrida agregaría las filas otra
# vez:

# %%
anti = CARPETA_SALIDA / "anti_ejemplo_append.csv"
anti.unlink(missing_ok=True)
for corrida in range(1, 4):
    partidos_1.to_csv(anti, mode="a", header=not anti.exists(), index=False)
    print(f"después de la corrida {corrida}: {len(pd.read_csv(anti))} filas")
anti.unlink()

# %% [markdown]
# **Interpretación:** 144 → 288 → 432. Tres corridas, tres veces los mismos partidos. Un
# reporte encima de este archivo diría que el Real Madrid jugó el triple de partidos. Esto
# pasa de verdad en pipelines incrementales mal diseñados; las soluciones típicas son
# sobrescribir la partición completa, o hacer *upsert* (insertar o actualizar por llave, por
# ejemplo `(date, home_team, away_team)`).

# %% [markdown]
# ## 10. ¿Dónde encaja esto? ETL, batch y el ciclo de vida de ML
#
# - Lo que hicimos es **ETL**: transformamos en memoria (pandas) **antes** de cargar. En
#   **ELT** se cargaría el CSV crudo a un warehouse (BigQuery, Snowflake) y se transformaría
#   allá con SQL.
# - Es un pipeline **batch**: procesa el archivo completo de una vez. Uno **streaming**
#   procesaría cada partido al llegar (Kafka, Spark Streaming).
# - En CRISP-DM corresponde a **Data Understanding** (inspección, validación) y **Data
#   Preparation** (limpieza, transformación). Su salida alimenta el pipeline de ML del tema 05.

# %% [markdown]
# ## Resumen
#
# - Un pipeline de datos son **etapas separadas** encadenadas: extraer → validar → limpiar →
#   transformar → validar → guardar. Aquí cada una es una función, y `.pipe()` las encadena.
# - Comandos clave: `read_csv`, `info`, `isna().sum()`, `dropna(how="all")`,
#   `drop_duplicates`, `str.strip`, `pd.to_datetime`, `str.replace` + `astype`,
#   `str.extract` (regex con grupos), `assign`, `groupby().agg()`, `merge`, `to_csv`.
# - El CSV pasó de **151 filas a 144 partidos**; los 129 nulos eran 7 filas vacías (126) más 3
#   casos de `0 of 0` atajadas, que son nulos con significado.
# - Las **validaciones con `assert`** frenan el pipeline cuando la fuente cambia (detectamos el
#   '0.63' en una sola fila) y revisan reglas de negocio (posesión ~100, hechos ≤ intentos,
#   marcador coherente con `result`).
# - El pipeline es **idempotente**: dos corridas dieron el mismo DataFrame y la misma huella MD5;
#   el anti-ejemplo con `mode="a"` duplicó y triplicó las filas.
