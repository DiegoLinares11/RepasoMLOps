# %% [markdown]
# # 09 · Docker sin Docker: capas, contenedores, volúmenes y Compose en Python
#
# Este notebook **no ejecuta Docker** (no hace falta tenerlo instalado). Usa Python para
# hacer visibles cuatro ideas que en Docker pasan "por debajo":
#
# 1. Un **Dockerfile** es una lista de instrucciones; algunas crean **capas** de archivos.
# 2. La **caché de capas**: por qué se copia `requirements.txt` **antes** que el código.
# 3. **Imagen vs. contenedor vs. volumen**: la capa escribible desaparece con el
#    contenedor, el volumen no. Lo simulamos con `collections.ChainMap`, que funciona
#    exactamente como el sistema de archivos por capas de Docker.
# 4. **Compose**: leemos el `docker-compose.yml` real de la Actividad 4, calculamos el
#    orden de arranque y reemplazamos las variables `${VAR:-defecto}` del `.env`.
#
# Los archivos reales están en `ejemplos/` (copias comentadas de la Actividad 4).

# %%
import hashlib
import re
import warnings
from collections import ChainMap
from graphlib import TopologicalSorter
from pathlib import Path
from types import MappingProxyType

import pandas as pd

warnings.filterwarnings("ignore")
RANDOM_STATE = 42  # convención del repo; aquí no hay azar
pd.set_option("display.max_colwidth", 80)

EJEMPLOS = Path("ejemplos")

# %% [markdown]
# ## 1. Leer el Dockerfile del entrenador
#
# Quitamos los comentarios, unimos las líneas que terminan en `\` y separamos cada
# instrucción. Marcamos cuáles **cambian archivos** (crean una capa con contenido:
# `FROM`, `COPY`, `RUN`) y cuáles solo guardan **metadatos** (`ENV`, `WORKDIR`, `USER`,
# `CMD`, `EXPOSE`).

# %%
def leer_dockerfile(ruta):
    instrucciones, actual = [], ""
    for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
        s = linea.strip()
        if not s or s.startswith("#"):
            continue
        actual += s.rstrip("\\").strip() + " "
        if not s.endswith("\\"):
            orden, _, argumento = actual.strip().partition(" ")
            instrucciones.append((orden.upper(), " ".join(argumento.split())))
            actual = ""
    return instrucciones


CREA_ARCHIVOS = {"FROM", "COPY", "ADD", "RUN"}
df_entrenador = leer_dockerfile(EJEMPLOS / "entrenador" / "Dockerfile")
pd.DataFrame(
    [(i + 1, o, a, "sí" if o in CREA_ARCHIVOS else "no (metadato)") for i, (o, a) in enumerate(df_entrenador)],
    columns=["paso", "instrucción", "argumento", "¿cambia archivos?"],
).set_index("paso")

# %% [markdown]
# **Interpretación:** el Dockerfile real tiene 10 instrucciones. Cinco cambian archivos:
# la imagen base (`FROM python:3.12-slim`), dos `COPY` de dependencias, el `RUN pip
# install` (el paso lento: descarga e instala scikit-learn, pandas, numpy y scipy), el
# `COPY` de `entrenar.py` y el `RUN useradd ... chown`. El orden no es casual: **lo que
# cambia poco va arriba, lo que cambia mucho (el código) va abajo**.
#
# ## 2. Simular la caché de capas
#
# Docker decide si reutiliza una capa con una regla simple: **la capa se reutiliza si la
# instrucción es idéntica, los archivos que copia no cambiaron, y TODAS las capas
# anteriores también se reutilizaron**. En cuanto una capa cambia, todas las de abajo se
# reconstruyen.
#
# Lo simulamos con un *hash* encadenado: la "huella" de cada capa depende de la huella
# de la anterior, de la instrucción y del contenido de los archivos que copia.

# %%
def construir(instrucciones, archivos, cache):
    """Devuelve una tabla con HIT (reutilizada) o MISS (reconstruida) por paso."""
    filas, huella = [], ""
    for orden, argumento in instrucciones:
        contenido = ""
        if orden == "COPY":
            origen = argumento.split()[0]
            contenido = archivos.get(origen, "")
        huella = hashlib.sha256(f"{huella}|{orden} {argumento}|{contenido}".encode()).hexdigest()[:10]
        estado = "HIT (caché)" if huella in cache else "MISS (reconstruye)"
        cache.add(huella)
        lento = "  <-- pip install (lento)" if orden == "RUN" and "pip install" in argumento else ""
        filas.append({"instrucción": f"{orden} {argumento[:55]}", "resultado": estado + lento})
    return pd.DataFrame(filas)


# Contenido "de mentira" de los archivos que se copian (solo importa si cambia o no)
archivos_v1 = {
    "entrenador/requirements.txt": "scikit-learn==1.8.0\npandas==2.3.3\n...",
    "libreria/act3_pipeline-0.1.0-py3-none-any.whl": "<binario del wheel>",
    "entrenador/entrenar.py": "print('entrenando v1')",
}
cache = set()
primera = construir(df_entrenador, archivos_v1, cache)
primera

# %% [markdown]
# **Interpretación:** la primera vez no hay nada en caché: los 10 pasos son `MISS`. Es
# la construcción lenta de la primera vez de `docker compose up --build`.
#
# Ahora **cambiamos solo una línea de `entrenar.py`** y reconstruimos, con el orden
# real (dependencias primero) y con un orden "ingenuo" (copiar todo el código antes de
# instalar).

# %%
archivos_v2 = {**archivos_v1, "entrenador/entrenar.py": "print('entrenando v2')"}

# Orden REAL de la Actividad 4, con la caché llena de la primera construcción
bueno = construir(df_entrenador, archivos_v2, set(cache))

# Orden INGENUO: el COPY del código se mueve ANTES de las dependencias
idx_codigo = next(i for i, (o, a) in enumerate(df_entrenador) if o == "COPY" and "entrenar.py" in a)
idx_req = next(i for i, (o, a) in enumerate(df_entrenador) if o == "COPY" and "requirements" in a)
ingenuo_instr = df_entrenador.copy()
paso_codigo = ingenuo_instr.pop(idx_codigo)
ingenuo_instr.insert(idx_req, paso_codigo)
cache_ingenuo = set()
construir(ingenuo_instr, archivos_v1, cache_ingenuo)          # 1a construcción (llena caché)
ingenuo = construir(ingenuo_instr, archivos_v2, cache_ingenuo)  # 2a, tras editar entrenar.py

pd.concat({"orden real (deps primero)": bueno, "orden ingenuo (código primero)": ingenuo}, axis=1)

# %% [markdown]
# **Interpretación:** con el orden real, editar `entrenar.py` solo invalida sus capas
# finales: el `RUN pip install` sale `HIT`, así que la reconstrucción no reinstala
# nada. Con el orden ingenuo, el `COPY` del código está arriba; al cambiar, **todo lo de
# abajo** sale `MISS`, incluido `pip install`: cada cambio de una línea obligaría a
# descargar e instalar scikit-learn otra vez. Es exactamente lo que explica el
# comentario del Dockerfile real y el PDF de la Actividad 4.
#
# ## 3. Imagen, contenedor y capa escribible (con `ChainMap`)
#
# Un `ChainMap` busca una clave en varios diccionarios **en orden** y **escribe siempre
# en el primero**. Es el mismo truco del sistema de archivos de Docker (*overlay*):
#
# - Las **capas de la imagen** son diccionarios de **solo lectura** (`MappingProxyType`).
# - Un **contenedor** = un diccionario vacío y escribible **encima** de esas capas.
#
# Analogía: la imagen es la **clase**, el contenedor es un **objeto** creado a partir de
# ella. De una clase salen muchos objetos y modificar uno no modifica la clase.

# %%
capa_base = MappingProxyType({"/usr/local/bin/python": "Python 3.12", "/etc/os-release": "Debian"})
capa_deps = MappingProxyType({"/usr/local/lib/python3.12/site-packages/sklearn": "scikit-learn 1.8.0"})
capa_codigo = MappingProxyType({"/app/entrenar.py": "código del entrenador"})
IMAGEN = (capa_codigo, capa_deps, capa_base)           # la de arriba primero


def crear_contenedor(imagen, volumenes=None):
    """Capa escribible propia + (opcional) volúmenes montados + capas de la imagen."""
    return {"escribible": {}, "volumenes": volumenes or {}, "imagen": imagen}


def escribir(cont, ruta, valor):
    for punto, vol in cont["volumenes"].items():         # ¿la ruta cae en un volumen?
        if ruta.startswith(punto):
            vol[ruta] = valor
            return f"{ruta} -> VOLUMEN montado en {punto}"
    cont["escribible"][ruta] = valor                      # si no, a la capa escribible
    return f"{ruta} -> capa escribible del contenedor"


def ver(cont):
    vols = [v for v in cont["volumenes"].values()]
    return ChainMap(cont["escribible"], *vols, *cont["imagen"])


c1 = crear_contenedor(IMAGEN)
c2 = crear_contenedor(IMAGEN)
print(escribir(c1, "/app/modelo.joblib", "modelo entrenado"))
print("¿c1 ve el modelo?            ", "/app/modelo.joblib" in ver(c1))
print("¿c2 (misma imagen) lo ve?    ", "/app/modelo.joblib" in ver(c2))
print("¿la IMAGEN cambió?           ", any("/app/modelo.joblib" in capa for capa in IMAGEN))
try:
    capa_codigo["/app/hack.py"] = "x"
except TypeError as e:
    print("Escribir directo en la imagen ->", type(e).__name__, "(las capas son de solo lectura)")
del c1                                                   # docker rm
print("Tras borrar c1, el modelo existe en algún lado?", any("/app/modelo.joblib" in capa for capa in IMAGEN))

# %% [markdown]
# **Interpretación:** lo que escribe un contenedor va a **su** capa escribible: el otro
# contenedor de la misma imagen no lo ve, la imagen no cambia (sus capas ni siquiera
# aceptan escritura) y al borrar el contenedor el archivo **se pierde**. Si el
# entrenador guardara el modelo en `/app/modelo.joblib`, la API nunca lo vería.
#
# ## 4. Volumen con nombre: lo que sobrevive al contenedor
#
# Ahora repetimos la historia de la Actividad 4: el **entrenador** escribe en
# `/modelos` (un volumen), **muere**, y luego la **API** monta el mismo volumen en solo
# lectura.

# %%
volumen_modelos = {}        # vive FUERA de cualquier contenedor (lo administra Docker)
volumen_pgdata = {}

entrenador = crear_contenedor(IMAGEN, volumenes={"/modelos": volumen_modelos})
print(escribir(entrenador, "/modelos/modelo.joblib", "LogisticRegression calibrada"))
print(escribir(entrenador, "/modelos/metadatos.json", "{cv_f1_macro: 0.619}"))
print(escribir(entrenador, "/tmp/log.txt", "temporal"))
del entrenador              # el entrenador termina: Exited (0)

api = crear_contenedor(IMAGEN, volumenes={"/modelos": MappingProxyType(volumen_modelos)})  # :ro
fs_api = ver(api)
print("\nLa API ve /modelos/modelo.joblib ->", fs_api.get("/modelos/modelo.joblib"))
print("La API ve /tmp/log.txt del entrenador ->", fs_api.get("/tmp/log.txt", "NO (murió con su contenedor)"))
try:
    api["volumenes"]["/modelos"]["/modelos/modelo.joblib"] = "modelo alterado"
except TypeError:
    print("La API intenta modificar el modelo -> rechazado (montado :ro)")

# %% [markdown]
# **Interpretación:** el modelo y sus metadatos sobreviven a la muerte del entrenador
# porque estaban en el volumen; el `/tmp/log.txt`, que fue a la capa escribible, murió
# con él. La API lo lee pero no lo puede modificar (`modelos:/modelos:ro`). Es la
# **Prueba 1** del PDF: "el modelo sobrevive a su creador".
#
# Y la diferencia entre `docker compose down` y `docker compose down -v`:

# %%
def compose_down(borrar_volumenes=False):
    if borrar_volumenes:
        volumen_modelos.clear()
        volumen_pgdata.clear()


volumen_pgdata["fila_1"] = "Real Madrid vs Marseille -> Home Win"
volumen_pgdata["fila_2"] = "Ajax vs Inter -> Away Win"
compose_down()                       # down: borra contenedores y red, NO volúmenes
print("tras 'down'   : modelo existe =", "/modelos/modelo.joblib" in volumen_modelos,
      "| predicciones guardadas =", len(volumen_pgdata))
compose_down(borrar_volumenes=True)  # down -v: borra TAMBIÉN los volúmenes
print("tras 'down -v': modelo existe =", "/modelos/modelo.joblib" in volumen_modelos,
      "| predicciones guardadas =", len(volumen_pgdata))

# %% [markdown]
# **Interpretación:** tras `down` el modelo sigue y las 2 predicciones también (Prueba 2
# del PDF: `total_historico: 2`); tras `down -v` no queda nada (Prueba 3:
# `total_historico: 0` y el entrenador vuelve a calibrar desde cero).
#
# ## 5. Leer el `docker-compose.yml` real
#
# Un archivo de Compose es YAML: se puede leer como un diccionario de Python. Armamos
# una tabla con lo esencial de cada servicio.

# %%
try:
    import yaml
    compose = yaml.safe_load((EJEMPLOS / "docker-compose.yml").read_text(encoding="utf-8"))
except ImportError:
    compose = None
    print("PyYAML no está instalado: pip install pyyaml para correr esta sección.")

if compose:
    filas = []
    for nombre, s in compose["services"].items():
        filas.append({
            "servicio": nombre,
            "imagen": s.get("image"),
            "se construye": "sí, " + s["build"]["dockerfile"] if "build" in s else "no (imagen oficial)",
            "puertos publicados": ", ".join(s.get("ports", [])) or "ninguno",
            "volúmenes": " | ".join(s.get("volumes", [])),
            "depende de": ", ".join(f"{k} ({v['condition']})" for k, v in s.get("depends_on", {}).items()) or "-",
            "restart": s.get("restart"),
        })
    servicios = pd.DataFrame(filas).set_index("servicio")
    print("volúmenes con nombre:", list(compose["volumes"]), "| redes:", list(compose["networks"]))
servicios if compose else None

# %% [markdown]
# **Interpretación:** tres servicios. `entrenador` y `api` se construyen desde sus
# Dockerfiles; `db` usa la imagen oficial `postgres:16-alpine`. **Solo la API publica un
# puerto** (`${PUERTO_API:-8000}:8000`): Postgres es inalcanzable desde fuera. Los
# volúmenes muestran los dos tipos: *bind mounts* que empiezan con `./` (`./datos`,
# `./db/init.sql`, ambos `:ro`) y volúmenes con nombre (`modelos`, `pgdata`). El
# entrenador tiene `restart: "no"` (es un lote) y los otros `unless-stopped`.
#
# ## 6. Orden de arranque a partir de `depends_on`
#
# Compose arma un grafo con las dependencias y arranca en **orden topológico**: nadie
# arranca antes que aquello de lo que depende.

# %%
if compose:
    grafo = {n: set(s.get("depends_on", {})) for n, s in compose["services"].items()}
    orden = list(TopologicalSorter(grafo).static_order())
    print("grafo de dependencias:", grafo)
    print("orden de arranque     :", " -> ".join(orden))

# %% [markdown]
# **Interpretación:** `entrenador` y `db` no dependen de nada y pueden arrancar en
# paralelo; la `api` va al final porque espera **dos condiciones**: que el entrenador
# haya **terminado con código 0** (`service_completed_successfully`) y que Postgres esté
# **healthy** (`service_healthy`). Esto sustituye al "esperar 5 segundos y confiar".
#
# ## 7. Variables `${VAR:-defecto}` y el archivo `.env`
#
# Compose reemplaza `${VAR:-defecto}` con el valor de `VAR` en el `.env` (o el entorno),
# y si no existe usa `defecto`. Lo reproducimos con una expresión regular, primero
# **sin** `.env` y luego con el `.env.example` real.

# %%
def leer_env(ruta):
    vars_ = {}
    for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", linea)
        if m:
            vars_[m.group(1)] = m.group(2).strip()
    return vars_


def sustituir(texto, variables):
    return re.sub(r"\$\{(\w+):-([^}]*)\}", lambda m: variables.get(m.group(1), m.group(2)), texto)


env = leer_env(EJEMPLOS / ".env.example")
tabla_env = None
if compose:
    url_bd = compose["services"]["api"]["environment"]["URL_BD"]
    puerto = compose["services"]["api"]["ports"][0]
    tabla_env = pd.DataFrame({
        "URL_BD de la api": [url_bd, sustituir(url_bd, {}), sustituir(url_bd, env)],
        "ports de la api": [puerto, sustituir(puerto, {}), sustituir(puerto, env)],
    }, index=["en el YAML", "sin .env (valores por defecto)", "con .env.example"])
tabla_env

# %% [markdown]
# **Interpretación:** sin `.env`, la contraseña queda en `clave_de_ejemplo` (el valor
# por defecto escrito en el YAML); con el `.env`, pasa a `cambia_esta_clave`. El host de
# la base es literalmente **`db`**, el nombre del servicio: el DNS interno de la red
# `red-mlops` lo traduce a la IP del contenedor de Postgres. En tu compu,
# `docker compose config` muestra este mismo resultado ya sustituido.
#
# ## Resumen
#
# - Un **Dockerfile** es una receta; `FROM`, `COPY` y `RUN` crean capas de archivos y
#   `ENV`, `WORKDIR`, `USER`, `EXPOSE` y `CMD` guardan metadatos.
# - **Caché de capas**: una capa se reutiliza solo si ella y todas las anteriores no
#   cambiaron. Por eso `requirements.txt` + `pip install` van **antes** del código: editar
#   `entrenar.py` no reinstala nada.
# - **Imagen** = capas de solo lectura (la clase); **contenedor** = capa escribible encima
#   (el objeto). Lo escrito en esa capa muere con el contenedor.
# - **Volumen con nombre** = almacenamiento fuera del contenedor: el modelo sobrevive al
#   entrenador; montado `:ro`, la API no puede alterarlo. `down` conserva volúmenes,
#   `down -v` los borra.
# - **Compose** describe servicios, red y volúmenes; `depends_on` con condiciones define el
#   orden real de arranque; los servicios se llaman por **nombre** (`db:5432`); solo la
#   API publica puerto; `${VAR:-defecto}` se llena desde `.env`.
