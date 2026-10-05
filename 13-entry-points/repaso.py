# %% [markdown]
# # 13 · Entry points: el pipeline como comandos y plugins
#
# Este notebook muestra, con código que corre aquí mismo y sin internet, las tres ideas del tema:
#
# 1. Un entry point es solo una línea de metadata: **grupo**, **nombre** y **referencia** `modulo:objeto`.
# 2. `importlib.metadata.entry_points()` lee esa metadata de **todos** los paquetes instalados, y así
#    un programa descubre plugins que no conoce.
# 3. Lo que devuelve la función de un comando se vuelve su **código de salida**, y eso es lo que usan
#    `make` y CI para decidir si siguen.
#
# Para no instalar nada de verdad, vamos a **simular una instalación**: crear a mano la carpeta
# `.dist-info` que deja `pip install`. Para Python es exactamente lo mismo.

# %%
import subprocess
import sys
import tempfile
import textwrap
import tomllib
import warnings
from importlib.metadata import entry_points
from pathlib import Path

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
RANDOM_STATE = 42

# %% [markdown]
# ## 1. Cómo se declaran: el `pyproject.toml` de la Actividad 9
#
# `ejemplos/pyproject.toml` es el archivo real de la entrega. Lo leemos con `tomllib` (viene con
# Python 3.11+) para ver los dos tipos de entry points que declara.

# %%
with open("ejemplos/pyproject.toml", "rb") as f:
    proyecto = tomllib.load(f)["project"]

print("[project.scripts]  ->  grupo especial console_scripts (crea ejecutables)")
for nombre, ref in proyecto["scripts"].items():
    print(f"  {nombre:15s} = {ref}")

print()
for grupo, items in proyecto["entry-points"].items():
    print(f'[project.entry-points."{grupo}"]  ->  grupo propio (plugins, no crea ejecutables)')
    for nombre, ref in items.items():
        print(f"  {nombre:24s} = {ref}")

# %% [markdown]
# **Interpretación:** hay 6 comandos (uno por etapa, más `act9` y `act9-demo`) y 4 familias de
# modelos registradas en un grupo propio. La parte izquierda es el **nombre**; la derecha, la
# **referencia**: el módulo a importar y, después de los dos puntos, el objeto a usar.

# %% [markdown]
# ## 2. Los comandos que ya tienes instalados también son entry points
#
# Cada ejecutable de tu ambiente (`jupyter`, `pip`, `f2py`...) existe porque algún paquete declaró un
# `console_scripts`. `entry_points(group=...)` los devuelve como objetos `EntryPoint`.

# %%
comandos = sorted(entry_points(group="console_scripts"), key=lambda e: e.name)
print(f"Comandos registrados en este ambiente: {len(comandos)}\n")
for ep in comandos[:8]:
    print(f"  {ep.name:28s} -> módulo {ep.module!r}, objeto {ep.attr!r}")

# %% [markdown]
# **Interpretación:** el comando no "es" el código; solo apunta a una función. Si mañana el paquete
# mueve la función a otro módulo, cambia la línea del `pyproject.toml` y el comando sigue igual.
# Esa es la **interfaz estable** que buscan Docker, cron o Airflow.

# %% [markdown]
# ## 3. Simular `pip install`: la carpeta `.dist-info`
#
# Cuando pip instala un paquete deja una carpeta `<nombre>-<versión>.dist-info` con su metadata. Dos
# archivos bastan para que `importlib.metadata` lo encuentre:
#
# - `METADATA`: nombre y versión.
# - `entry_points.txt`: los entry points, en formato INI.
#
# La función `instalar_falso` crea eso en una carpeta temporal y la agrega a `sys.path`, que es justo
# lo que hace pip (pero en `site-packages`).

# %%
BASE = Path(tempfile.mkdtemp(prefix="repaso13_"))


def instalar_falso(nombre: str, version: str, modulos: dict[str, str], entradas: dict[str, dict]) -> Path:
    """Escribe los módulos y su .dist-info, y los pone en sys.path."""
    carpeta = BASE / nombre
    carpeta.mkdir()
    for modulo, codigo in modulos.items():
        (carpeta / f"{modulo}.py").write_text(textwrap.dedent(codigo), encoding="utf-8")
    info = carpeta / f"{nombre.replace('-', '_')}-{version}.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {nombre}\nVersion: {version}\n", encoding="utf-8"
    )
    lineas = []
    for grupo, items in entradas.items():
        lineas.append(f"[{grupo}]")
        lineas += [f"{k} = {v}" for k, v in items.items()]
    (info / "entry_points.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    sys.path.append(str(carpeta))
    return info


# %% [markdown]
# Ahora "instalamos" un mini pipeline con el mismo diseño que la Actividad 9: dos familias de modelos
# en el grupo `repaso.modelos` y un comando `mini-entrenar`. Cada familia cumple un **contrato**: una
# función sin argumentos que devuelve un diccionario con el estimador y una descripción.

# %%
info = instalar_falso(
    "mini-pipeline",
    "0.1.0",
    modulos={
        "mini_modelos": '''
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.linear_model import LogisticRegression

            def regresion_logistica():
                return {"estimador": LogisticRegression(max_iter=2000, class_weight="balanced"),
                        "descripcion": "LogisticRegression con clases balanceadas"}

            def random_forest():
                return {"estimador": RandomForestClassifier(n_estimators=200, random_state=42),
                        "descripcion": "RandomForest de 200 árboles"}
        ''',
        "mini_cli": '''
            from importlib.metadata import entry_points

            def main():
                familias = sorted(ep.name for ep in entry_points(group="repaso.modelos"))
                print(f"mini-entrenar: encontré {len(familias)} familias -> {familias}")
                return 0
        ''',
    },
    entradas={
        "console_scripts": {"mini-entrenar": "mini_cli:main"},
        "repaso.modelos": {
            "regresion_logistica": "mini_modelos:regresion_logistica",
            "random_forest": "mini_modelos:random_forest",
        },
    },
)
print(info.name)
print((info / "entry_points.txt").read_text(encoding="utf-8"))

# %% [markdown]
# **Interpretación:** ese `entry_points.txt` es lo mismo que pip escribió para `act9-pipeline` en la
# Actividad 9 (`act9_pipeline-0.1.0.dist-info/entry_points.txt`). No hay registro central: cada
# paquete trae el suyo.

# %% [markdown]
# ## 4. Descubrir los plugins con `importlib.metadata`
#
# Esta función es una versión corta de `plugins.descubrir_modelos()` de la Actividad 9 (completa en
# `ejemplos/plugins.py`). Ordena por nombre para que el resultado no dependa del orden del sistema de
# archivos, y si un plugin falla lo omite con un aviso en lugar de tumbar todo.

# %%
def descubrir(grupo: str = "repaso.modelos") -> dict[str, dict]:
    familias = {}
    for ep in sorted(entry_points(group=grupo), key=lambda e: e.name):
        try:
            spec = ep.load()()  # load() importa el objeto; () llama a la función
        except Exception as exc:
            print(f"  aviso: se omite {ep.name}: {exc}")
            continue
        familias[ep.name] = {**spec, "paquete": f"{ep.dist.name} {ep.dist.version}"}
    return familias


familias = descubrir()
for nombre, spec in familias.items():
    print(f"  {nombre:20s} {spec['descripcion']:42s} (paquete: {spec['paquete']})")

# %% [markdown]
# ## 5. Un paquete externo agrega una familia sin tocar el pipeline
#
# En la Actividad 9, `plugins/act9-modelo-knn` era **otro paquete** que no importaba nada del
# pipeline: solo se registraba en el mismo grupo. Aquí "instalamos" el equivalente.

# %%
instalar_falso(
    "mini-plugin-knn",
    "0.1.0",
    modulos={
        "mini_knn": '''
            from sklearn.neighbors import KNeighborsClassifier

            def knn():
                return {"estimador": KNeighborsClassifier(n_neighbors=15),
                        "descripcion": "KNN con 15 vecinos (plugin externo)"}
        '''
    },
    entradas={"repaso.modelos": {"knn": "mini_knn:knn"}},
)

familias = descubrir()
for nombre, spec in familias.items():
    print(f"  {nombre:20s} {spec['descripcion']:42s} (paquete: {spec['paquete']})")

# %% [markdown]
# **Interpretación:** el pipeline no cambió ni una línea, y ahora ve 3 familias. Así funcionan los
# plugins de pytest (grupo `pytest11`), los comandos de Flask (`flask.commands`) o los backends de
# MLflow: instalas un paquete y aparece la funcionalidad.

# %% [markdown]
# ## 6. Usar las familias descubiertas para entrenar
#
# Con el dataset de la Champions (solo las 6 columnas numéricas, para que sea rápido) evaluamos cada
# familia descubierta con validación cruzada estratificada de 5 partes y `f1_macro`, la métrica del
# curso por el desbalance de clases.

# %%
df = pd.read_csv("../datos/champions_league_matches.csv").dropna(how="all")
X = pd.DataFrame({
    "home_possession": df["home_possession"].str.rstrip("%").astype(float),
    "away_possession": df["away_possession"].str.rstrip("%").astype(float),
    "home_shots_on_target_pct": df["home_shots_on_target_pct"],
    "away_shots_on_target_pct": df["away_shots_on_target_pct"],
    "home_saves_pct": df["home_saves_pct"],
    "away_saves_pct": df["away_saves_pct"],
})
y = df["result"]
print(f"{len(X)} partidos, {X.shape[1]} variables")

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
resultados = {}
for nombre, spec in familias.items():
    pipe = Pipeline([
        ("imputar", SimpleImputer(strategy="median")),
        ("escalar", StandardScaler()),
        ("modelo", spec["estimador"]),
    ])
    resultados[nombre] = cross_val_score(pipe, X, y, cv=cv, scoring="f1_macro").mean()

tabla = pd.Series(resultados, name="f1_macro (CV)").sort_values(ascending=False).round(3)
tabla

# %% [markdown]
# **Interpretación:** el pipeline entrenó también el KNN aunque ese código no existía cuando se
# escribió `descubrir()`. Los números no son los de la Actividad 9 (allá había más variables,
# `RandomizedSearchCV` y 60 combinaciones), pero la mecánica es la misma: la lista de familias sale
# de la metadata, no del código.
#
# Ojo con la trampa que encontramos en la Actividad 9: **instalar un plugin cambió el resultado**
# (0.652 → 0.622 en CV), porque la búsqueda repartió sus combinaciones entre más familias. En
# producción conviene fijar las familias de forma explícita.

# %% [markdown]
# ## 7. Lo que hace el ejecutable: importar, llamar y devolver un código
#
# `pip` no copia tu código al `.exe`: crea un lanzador que hace lo de `ejemplos/lanzador_generado.py`.
# Podemos imitarlo con el `EntryPoint` de `mini-entrenar`.

# %%
(ep,) = entry_points(group="console_scripts", name="mini-entrenar")
print(f"{ep.name} -> {ep.value}")
main = ep.load()
codigo = main()
print(f"código de salida: {codigo}")

# %% [markdown]
# ## 8. El código de salida como compuerta de calidad
#
# `act9-evaluar --umbral 0.50` devolvía 1 si el `f1_macro` no llegaba al mínimo. Un proceso aparte
# (como el que lanza `make`) solo ve ese número. Lo simulamos con un subproceso: el mejor resultado de
# arriba y uno malo inventado.

# %%
evaluar = """
import sys
f1, umbral = float(sys.argv[1]), 0.50
print(f"f1_macro={f1:.3f}  umbral={umbral}")
sys.exit(0 if f1 >= umbral else 1)
"""
for f1 in [tabla.iloc[0], 0.42]:
    r = subprocess.run([sys.executable, "-c", evaluar, str(f1)], capture_output=True, text=True)
    estado = "make sigue" if r.returncode == 0 else "make se detiene"
    print(f"{r.stdout.strip():30s} -> código {r.returncode}: {estado}")

# %% [markdown]
# **Interpretación:** `make`, GitHub Actions o Airflow no leen el texto: solo el código. Con 0
# siguen; con cualquier otro número se detienen. Por eso en la Actividad 9, con `UMBRAL=0.90`, make no
# llegó a `act9-predecir`.

# %% [markdown]
# ## Resumen
#
# - Un entry point es una línea de metadata: **grupo**, **nombre** y referencia `modulo:objeto`.
# - `[project.scripts]` (grupo `console_scripts`) hace que el instalador cree un **ejecutable** por
#   línea; un grupo propio (`[project.entry-points."paquete.algo"]`) solo deja el registro.
# - `importlib.metadata.entry_points(group=...)` lee los `entry_points.txt` de todos los paquetes
#   instalados: así un programa descubre **plugins** que no conoce.
# - El ejecutable importa la función, la llama y usa lo que devuelve como **código de salida**, que es
#   lo que encadena `make` y detiene CI.
# - Trampas: sin el ambiente activado el comando no existe, y un plugin nuevo puede cambiar los
#   resultados de una búsqueda.
