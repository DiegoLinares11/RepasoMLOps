# %% [markdown]
# # 07 · Ambientes virtuales: lo que pasa por dentro
#
# Este notebook no entrena ningún modelo. Sirve para **ver con tus propios ojos**
# las tres ideas que casi nadie comprueba:
#
# 1. Un ambiente virtual es **solo una carpeta** con su propio `python` y su propia
#    carpeta `site-packages`.
# 2. "Activar" un ambiente **solo cambia el PATH** (la lista de carpetas donde la
#    terminal busca programas). No hay magia.
# 3. Los especificadores `==`, `>=` y `~=` aceptan versiones distintas, y conviene
#    saber exactamente cuáles.
#
# Todo corre **sin internet**: creamos un ambiente temporal con `python -m venv`,
# lo interrogamos y lo borramos. No se instala nada.

# %%
import os
import shutil
import subprocess
import sys
import tempfile
import time
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
RANDOM_STATE = 42  # convención del repo; aquí no hay azar


def correr(cmd, **kw):
    """Ejecuta un comando y devuelve (código de salida, salida de texto)."""
    env = {**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1"}  # sin avisos de "nueva versión de pip"
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, **kw)
    return r.returncode, (r.stdout + r.stderr).strip()


# %% [markdown]
# ## 1. ¿Qué Python está corriendo este notebook?
#
# Tres variables de `sys` lo dicen todo:
#
# | Variable | Qué significa |
# |---|---|
# | `sys.executable` | La ruta del programa `python` que está corriendo ahora mismo |
# | `sys.prefix` | La carpeta "raíz" del ambiente activo (donde busca sus librerías) |
# | `sys.base_prefix` | La carpeta del Python **original** con el que se creó el ambiente |
#
# **La regla:** si `sys.prefix != sys.base_prefix`, estás dentro de un ambiente
# virtual. Si son iguales, estás usando el Python "global" de la máquina.

# %%
print("sys.executable  :", sys.executable)
print("sys.prefix      :", sys.prefix)
print("sys.base_prefix :", sys.base_prefix)
print("¿Dentro de un venv?", sys.prefix != sys.base_prefix)

# %% [markdown]
# **Interpretación:** en la corrida que generó este notebook, `sys.prefix` y
# `sys.base_prefix` salieron iguales, o sea, el kernel usaba el Python global (no un
# venv). En tu compu, si abriste Jupyter después de activar `.venv`, deberías ver
# `True` y una ruta que termina en `.venv`. Si ves `False`, estás instalando cosas en el
# Python global sin darte cuenta: el error número uno.
#
# ## 2. ¿Dónde busca Python las librerías?
#
# Cuando escribes `import pandas`, Python recorre **en orden** la lista `sys.path`
# hasta encontrar una carpeta `pandas/`. Las librerías instaladas con pip viven en una
# carpeta llamada `site-packages` (o `dist-packages` en Debian/Ubuntu).

# %%
for p in sys.path:
    marca = "  <-- librerías instaladas con pip" if p.endswith(("site-packages", "dist-packages")) else ""
    print(repr(p), marca)

import pandas as _pd  # noqa: E402
print("\npandas se importó desde:", Path(_pd.__file__).parent)

# %% [markdown]
# **Interpretación:** pandas se cargó desde una carpeta que está dentro de
# `sys.prefix` (o de una ruta de usuario). Esa es la clave de todo: **cada ambiente
# tiene su propia `site-packages`**, así que cada uno puede tener su propia versión
# de pandas sin pelearse con los demás.
#
# ## 3. Crear un ambiente virtual temporal
#
# Es exactamente lo que harías en PowerShell con `python -m venv .venv`. Lo creamos en
# una carpeta temporal para no ensuciar el repo, y medimos cuánto tarda.

# %%
tmp = Path(tempfile.mkdtemp(prefix="repaso07_"))
venv_dir = tmp / ".venv"

t0 = time.perf_counter()
codigo, salida = correr([sys.executable, "-m", "venv", str(venv_dir)])
if codigo != 0:  # algunos Linux traen Python sin ensurepip: se crea sin pip
    print("venv con pip falló, reintento sin pip:\n", salida[:300])
    codigo, salida = correr([sys.executable, "-m", "venv", "--without-pip", str(venv_dir)])
segundos = time.perf_counter() - t0
print(f"código de salida: {codigo}   tiempo: {segundos:.1f} s")
print("contenido de la carpeta:", sorted(p.name for p in venv_dir.iterdir()))

# En Windows el ejecutable está en Scripts\python.exe; en Linux/macOS en bin/python
if os.name == "nt":
    carpeta_bin = venv_dir / "Scripts"
    py_venv = carpeta_bin / "python.exe"
else:
    carpeta_bin = venv_dir / "bin"
    py_venv = carpeta_bin / "python"
print("carpeta de ejecutables:", carpeta_bin.name, "->", sorted(p.name for p in carpeta_bin.iterdir()))

# %% [markdown]
# **Interpretación:** el ambiente es una carpeta normal con unas pocas cosas:
# `pyvenv.cfg`, una carpeta de ejecutables (`bin/` en Linux/macOS, `Scripts\` en
# Windows) y una carpeta `lib/` (o `Lib\` en Windows) donde vivirá su `site-packages`.
# Fíjate que aparecen **scripts de activación para cada terminal**: `activate`
# (bash/zsh), `activate.fish`, `activate.csh` y `Activate.ps1` (PowerShell).
#
# ## 4. El archivo `pyvenv.cfg`: el "DNI" del ambiente
#
# Al arrancar, el ejecutable de Python mira si junto a él (o una carpeta arriba) hay un
# `pyvenv.cfg`. Si lo hay, sabe que es un ambiente virtual y usa **su propia**
# `site-packages` en vez de la global.

# %%
print((venv_dir / "pyvenv.cfg").read_text())

# %% [markdown]
# **Interpretación:** `home` apunta al Python original (de ahí sale el intérprete; el
# venv **no copia Python completo**, reutiliza el instalado). La línea
# `include-system-site-packages = false` es la que garantiza el aislamiento: las
# librerías globales no se ven desde adentro. `version` dice con qué versión se creó:
# un venv **no puede cambiar de versión de Python**; si necesitas otra, creas otro venv.
#
# ## 5. Le preguntamos lo mismo al Python del ambiente
#
# Ejecutamos el `python` de adentro del venv y le pedimos sus `sys.prefix` y
# `sys.base_prefix`.

# %%
script = "import sys; print(sys.executable); print(sys.prefix); print(sys.base_prefix)"
filas = []
for nombre, exe in [("Python del notebook", sys.executable), ("Python del venv", str(py_venv))]:
    _, out = correr([exe, "-c", script])
    e, pfx, base = out.splitlines()
    filas.append({"intérprete": nombre, "sys.prefix": pfx, "sys.base_prefix": base,
                  "¿en venv?": pfx != base})
tabla = pd.DataFrame(filas).set_index("intérprete")
tabla

# %% [markdown]
# **Interpretación:** el Python del venv reporta como `sys.prefix` la carpeta `.venv`
# temporal, pero su `sys.base_prefix` es el mismo Python original. Por eso
# `¿en venv?` sale `True` solo en la segunda fila. Es **el mismo intérprete** con
# **otra carpeta de librerías**.
#
# ## 6. Aislamiento: pandas existe afuera, pero no adentro
#
# El notebook tiene pandas instalado. El venv recién creado está vacío. Intentamos
# importarlo en los dos.

# %%
for nombre, exe in [("Python del notebook", sys.executable), ("Python del venv", str(py_venv))]:
    codigo, out = correr([exe, "-c", "import pandas; print(pandas.__version__)"])
    resumen = out.splitlines()[-1] if out else ""
    print(f"{nombre:<20} código={codigo}  ->  {resumen}")

# %% [markdown]
# **Interpretación:** afuera `import pandas` funciona (código 0); adentro falla con
# `ModuleNotFoundError` (código 1). Eso **no es un error, es la idea**: cada proyecto
# arranca limpio y solo tiene lo que tú le instalas. Así el proyecto A puede tener
# `scikit-learn==1.3` y el proyecto B `scikit-learn==1.8` en la misma compu.
#
# ## 7. `pip freeze` dentro del ambiente vacío
#
# `pip freeze` lista **todo** lo instalado con versión exacta (`paquete==versión`).
# En un venv nuevo debería estar prácticamente vacío.

# %%
codigo, out = correr([str(py_venv), "-m", "pip", "freeze"])
print("código:", codigo)
print("pip freeze (venv nuevo):", repr(out) if out else "(vacío)")
codigo, out = correr([str(py_venv), "-m", "pip", "list"])
print("\npip list (venv nuevo):\n" + out)

# %% [markdown]
# **Interpretación:** `pip freeze` sale vacío y `pip list` solo muestra las
# herramientas de instalación (`pip`, y en Python 3.11 o anterior también
# `setuptools`). `pip freeze` las esconde a propósito porque no son dependencias de tu
# proyecto.
#
# ## 8. Comparar: `requirements.txt` escrito a mano vs. `pip freeze`
#
# El `requirements.txt` del repo lista lo que **tú** pediste (dependencias directas,
# casi sin versión). `pip freeze` del ambiente del notebook lista **todo lo que
# terminó instalado**, incluidas las dependencias de las dependencias (transitivas).

# %%
req_repo = [l.strip() for l in Path("../requirements.txt").read_text().splitlines()
            if l.strip() and not l.strip().startswith("#")]
codigo, freeze = correr([sys.executable, "-m", "pip", "freeze"])
lineas_freeze = [l for l in freeze.splitlines() if l and not l.startswith("#")]

print(f"requirements.txt del repo : {len(req_repo)} líneas -> {req_repo}")
print(f"pip freeze del notebook   : {len(lineas_freeze)} líneas. Primeras 8:")
for l in lineas_freeze[:8]:
    print("   ", l)

# %% [markdown]
# **Interpretación:** el `requirements.txt` del repo pide 11 paquetes, pero el ambiente
# donde se ejecutó este notebook tenía 114 líneas en `pip freeze`, todas con `==`. Las
# más de 100 restantes son transitivas (pandas trae `python-dateutil`, `tzdata`...; jupyter trae
# decenas). El `requirements.txt` corto expresa **intención**; el `freeze` es una
# **foto exacta**, que es lo que hace un *lock file*.
#
# ## 9. "Activar" = poner la carpeta del venv al principio del PATH
#
# Cuando escribes `python` en la terminal, el sistema recorre las carpetas del `PATH`
# en orden y ejecuta el **primer** `python` que encuentra. El script de activación
# solo hace esto:
#
# 1. Pone `.venv\Scripts` (o `.venv/bin`) **al principio** del PATH.
# 2. Define la variable `VIRTUAL_ENV`.
# 3. Cambia el prompt para que veas `(.venv)`.
#
# Lo simulamos sin tocar tu terminal: buscamos `python` con el PATH normal y con el
# PATH "activado".

# %%
path_normal = os.environ.get("PATH", "")
path_activado = str(carpeta_bin) + os.pathsep + path_normal

nombre_py = "python"
print("sin activar :", shutil.which(nombre_py, path=path_normal) or shutil.which("python3", path=path_normal))
print("activado    :", shutil.which(nombre_py, path=path_activado))

# Las líneas del script de PowerShell que hacen el trabajo
ps1 = (carpeta_bin / "Activate.ps1").read_text(encoding="utf-8", errors="ignore")
print("\nLíneas de Activate.ps1 que tocan PATH / VIRTUAL_ENV:")
for linea in ps1.splitlines():
    s = linea.strip()
    if s.startswith(("$Env:PATH =", "$env:VIRTUAL_ENV =")):
        print("   ", s)

# %% [markdown]
# **Interpretación:** con el PATH normal, `python` apunta al intérprete global; con la
# carpeta del venv al principio, apunta a `.venv/.../python`. Y las líneas de
# `Activate.ps1` lo confirman: `$Env:PATH = "$VenvExecDir..."` antepone la carpeta del
# venv y `$env:VIRTUAL_ENV` guarda su ruta. Por eso **no hace falta activar** si llamas
# directamente al ejecutable: `.venv\Scripts\python.exe -m pip install ...` funciona
# igual (muy útil en scripts y en CI).
#
# ## 10. Especificadores de versión: `==`, `>=`, `~=`
#
# Probamos varios especificadores contra una lista de versiones "candidatas" de
# scikit-learn. Usamos la librería `packaging`, que es la misma que usa pip por dentro
# para decidir qué versión acepta.

# %%
try:
    from packaging.specifiers import SpecifierSet
    from packaging.version import Version
except ImportError:  # pip trae su propia copia
    from pip._vendor.packaging.specifiers import SpecifierSet
    from pip._vendor.packaging.version import Version

candidatas = ["1.2.2", "1.3.0", "1.3.2", "1.4.0", "1.8.0", "2.0.0"]
especificadores = ["==1.3.2", ">=1.3", "~=1.3.0", "~=1.3", ">=1.3,<2", ">=1.3,!=1.4.0"]

matriz = pd.DataFrame(
    {esp: ["✔" if SpecifierSet(esp).contains(v) else "·" for v in candidatas] for esp in especificadores},
    index=candidatas,
)
matriz.index.name = "versión"
matriz

# %% [markdown]
# **Interpretación (fila por fila de la tabla real):**
#
# - `==1.3.2` acepta **una sola** versión: máxima reproducibilidad, cero flexibilidad.
# - `>=1.3` acepta todo desde 1.3.0, **incluida la 2.0.0**: si mañana sale una versión
#   mayor con cambios incompatibles, tu proyecto la instala y se rompe.
# - `~=1.3.0` ("compatible") equivale a `>=1.3.0, <1.4`: acepta parches (1.3.x) pero no
#   1.4.0.
# - `~=1.3` equivale a `>=1.3, <2`: acepta 1.4 y 1.8 pero no 2.0.
# - `>=1.3,<2` es lo mismo escrito explícito. `!=` excluye una versión con un bug
#   conocido.
#
# Regla práctica del curso: **librería** (lo que publicas, tema 08) → rangos abiertos
# como `>=1.3`; **aplicación** (lo que despliegas, tema 09) → `==` exacto, como los
# `requirements.txt` de los Dockerfiles de la Actividad 4.
#
# ## 11. Por qué la carpeta `.venv` NO se sube a Git
#
# Medimos el tamaño del venv recién creado (que ni siquiera tiene pandas).

# %%
archivos = [p for p in venv_dir.rglob("*") if p.is_file()]
mb = sum(p.stat().st_size for p in archivos) / 1024**2
print(f"venv VACÍO: {len(archivos)} archivos, {mb:.1f} MB")

# Las rutas absolutas quedan escritas adentro: no sirve en otra compu
cfg = (venv_dir / "pyvenv.cfg").read_text()
print("Rutas absolutas guardadas en pyvenv.cfg:")
for linea in cfg.splitlines():
    if linea.startswith(("home", "executable")):
        print("   ", linea)

# %% [markdown]
# **Interpretación:** aun vacío, el ambiente ya tenía 1905 archivos y 41.9 MB (casi
# todo es pip y setuptools). Con pandas + scikit-learn crece a cientos de MB. Además guarda
# **rutas absolutas** de esta máquina (`home = ...`) y en Windows trae `.exe` que no
# sirven en Mac. Lo que se versiona es la **receta** (`requirements.txt`,
# `pyproject.toml`, lock file) y cada quien recrea el venv en 1 minuto.
#
# ## 12. Borrar el ambiente
#
# Un venv es **desechable**: si se corrompe, lo borras y lo recreas desde la receta.

# %%
shutil.rmtree(tmp, ignore_errors=True)
print("¿Sigue existiendo?", venv_dir.exists())

# %% [markdown]
# ## Resumen
#
# - Un **ambiente virtual** es una carpeta con `pyvenv.cfg`, un `python` (que reutiliza
#   el intérprete original) y su **propia `site-packages`**.
# - Estás en un venv si `sys.prefix != sys.base_prefix`.
# - **Activar** solo antepone `.venv\Scripts` (o `.venv/bin`) al `PATH` y define
#   `VIRTUAL_ENV`; puedes saltártelo llamando directo a `.venv\Scripts\python.exe`.
# - El venv nuevo no ve los paquetes globales (`include-system-site-packages = false`).
# - `requirements.txt` a mano = intención (pocas líneas); `pip freeze` = foto exacta
#   con transitivas (lo que hace un lock file).
# - `==` fija una versión, `>=` deja la puerta abierta hasta versiones mayores, `~=`
#   acepta solo cambios compatibles.
# - La carpeta `.venv` no se versiona: pesa, tiene rutas absolutas y es desechable.
