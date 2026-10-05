# %% [markdown]
# # 08 · Construir un paquete de Python y mirarlo por dentro
#
# En la Tarea 4 construimos `act3-pipeline-mlops` con `python -m build` y lo subimos a
# TestPyPI con `twine`. Subir necesita internet y un token, así que aquí hacemos
# **todo lo demás**, sin internet, con un paquete mínimo que vive en
# `ejemplos/paquete-minimo/`:
#
# 1. Ver la estructura `src/` y el `pyproject.toml`.
# 2. **Construir** el sdist (`.tar.gz`) y el wheel (`.whl`).
# 3. **Abrir** el wheel (es un `.zip`) y comprobar que el CSV y el comando viajan adentro.
# 4. **Instalarlo** en un ambiente virtual limpio y ejecutar su comando de consola.
# 5. Ver la diferencia entre **nombre de distribución** y **nombre de import**.
# 6. Practicar **versionado semántico** con la misma librería que usa pip.

# %%
import importlib.util
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import warnings
import zipfile
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
RANDOM_STATE = 42  # convención del repo; aquí no hay azar

PAQUETE = Path("ejemplos/paquete-minimo").resolve()


def correr(cmd, **kw):
    env = {**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, **kw)
    return r.returncode, (r.stdout + r.stderr).strip()


# %% [markdown]
# ## 1. La estructura del proyecto (disposición `src/`)
#
# El código del paquete **no** está en la raíz del proyecto sino dentro de `src/`. Así,
# cuando pruebas, Python no puede importar "por accidente" la carpeta local: está
# obligado a usar la versión **instalada**, que es la que recibirán los demás.

# %%
for p in sorted(PAQUETE.rglob("*")):
    if p.is_file():
        print("   ", p.relative_to(PAQUETE).as_posix())

# %% [markdown]
# **Interpretación:** son 7 archivos. En la raíz, lo que describe el paquete
# (`pyproject.toml`, `README.md`, `LICENSE`); en `src/mini_champions/`, el código y un
# CSV de 8 partidos dentro de `datasets/`. Es la misma forma que la Tarea 4
# (`src/act3_pipeline/` con `datasets/champions_league_matches.csv`).
#
# ## 2. El `pyproject.toml`
#
# Es la ficha técnica del paquete. Fíjate en tres cosas: `[build-system]` (con qué
# herramienta se construye), `name` (con guiones) y `package-data` (para que el CSV
# entre).

# %%
print((PAQUETE / "pyproject.toml").read_text(encoding="utf-8"))

# %% [markdown]
# ## 3. Construir: sdist y wheel
#
# `python -m build` hace dos cosas: crea un ambiente aislado, instala ahí lo que pide
# `[build-system].requires` (aquí, setuptools; en la Tarea 4, hatchling) y llama a dos
# funciones estándar del *backend* (PEP 517): `build_sdist` y `build_wheel`.
#
# Para no depender de internet llamamos **esas mismas funciones** directamente con el
# setuptools que ya está instalado. Trabajamos en una copia temporal para no ensuciar
# el repo con `build/`, `dist/` y `*.egg-info`.

# %%
tmp = Path(tempfile.mkdtemp(prefix="repaso08_"))
proyecto = tmp / "paquete-minimo"
shutil.copytree(PAQUETE, proyecto)
dist = proyecto / "dist"

if importlib.util.find_spec("setuptools") is not None:
    codigo, salida = correr(
        [sys.executable, "-c",
         "from setuptools import build_meta as b; "
         "print('sdist ->', b.build_sdist('dist')); print('wheel ->', b.build_wheel('dist'))"],
        cwd=proyecto,
    )
    print("código:", codigo)
    print("\n".join(l for l in salida.splitlines() if l.startswith(("sdist", "wheel"))) or salida[-1500:])
else:
    # Python 3.12+ ya no trae setuptools en los venv: pip lo descarga en un ambiente aislado
    print("No hay setuptools en este ambiente; uso 'pip wheel' (necesita internet).")
    codigo, salida = correr([sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", str(dist), "."], cwd=proyecto)
    print("código:", codigo, "\n", salida[-800:])

archivos_dist = sorted(dist.glob("*"))
pd.DataFrame({"archivo": [p.name for p in archivos_dist],
              "KB": [round(p.stat().st_size / 1024, 1) for p in archivos_dist]})

# %% [markdown]
# **Interpretación:** salen los dos formatos que espera PyPI, con nombres
# **normalizados** (`mini_champions_uvg`, con guion bajo, aunque en `pyproject.toml`
# escribimos `mini-champions-uvg`). Pesan 4.7 KB (wheel) y 3.8 KB (sdist) porque el
# paquete es mínimo; los de la Tarea 4 pesaban 24 KB y 20 KB.
#
# ## 4. Anatomía del nombre de un wheel
#
# El nombre de un wheel no es decorativo: pip lo lee para saber si el archivo sirve en
# tu compu. Formato: `nombre-versión-python-abi-plataforma.whl`.

# %%
def partes_wheel(nombre):
    base = nombre[:-4].split("-")
    return dict(zip(["distribución", "versión", "python", "abi", "plataforma"], base))


ejemplos_wheel = [
    "act3_pipeline_mlops-0.1.0-py3-none-any.whl",            # Tarea 4 (TestPyPI)
    "act3_pipeline-0.1.0-py3-none-any.whl",                  # Actividad 3 (copiado a mano en la Act. 4)
    "numpy-2.4.1-cp312-cp312-win_amd64.whl",                 # librería con código C compilado
] + [p.name for p in archivos_dist if p.suffix == ".whl"]
pd.DataFrame([partes_wheel(n) for n in ejemplos_wheel], index=ejemplos_wheel).reset_index(drop=True)

# %% [markdown]
# **Interpretación:** nuestros wheels dicen `py3-none-any`: sirven para **cualquier**
# Python 3 (`py3`), no dependen de una ABI binaria (`none`) y corren en **cualquier**
# sistema operativo (`any`), porque son Python puro. Un wheel como el de numpy dice
# `cp312-cp312-win_amd64`: solo sirve en CPython 3.12 sobre Windows de 64 bits, porque
# trae código C ya compilado. Por eso numpy publica decenas de wheels por versión.
#
# ## 5. Un wheel es un `.zip`: abrámoslo
#
# Un wheel es un archivo zip con el código listo para copiar a `site-packages` y una
# carpeta `*.dist-info` con la metadata. Es exactamente la verificación que hicimos en
# la Tarea 4 para confirmar que el dataset viajaba adentro.

# %%
wheel = next(p for p in archivos_dist if p.suffix == ".whl")
with zipfile.ZipFile(wheel) as z:
    contenido = pd.DataFrame([(i.filename, i.file_size) for i in z.infolist()],
                             columns=["archivo dentro del wheel", "bytes"])
    metadata = z.read(next(n for n in z.namelist() if n.endswith("METADATA"))).decode()
    entry_points = z.read(next(n for n in z.namelist() if n.endswith("entry_points.txt"))).decode()
contenido

# %% [markdown]
# **Interpretación:** adentro está el paquete `mini_champions/` **sin** la carpeta
# `src/` (ese prefijo era solo para organizar el proyecto), el CSV en
# `mini_champions/datasets/partidos.csv` gracias a `package-data`, la licencia en
# `dist-info/licenses/` y los archivos de metadata. No hay `pyproject.toml` ni
# `README.md` sueltos: el wheel ya está "construido".
#
# ## 6. La metadata y el comando de consola

# %%
print("=== METADATA (primeras líneas) ===")
print("\n".join(metadata.splitlines()[:14]))
print("\n=== entry_points.txt ===")
print(entry_points)

# %% [markdown]
# **Interpretación:** `METADATA` es lo que TestPyPI muestra en la página del proyecto
# (nombre, versión, licencia, `Requires-Python` y, al final, el README completo como
# descripción). `entry_points.txt` dice que el comando `mini-champions` debe llamar a
# `mini_champions.cli:main`. pip leerá esto al instalar y creará el ejecutable.
#
# ## 7. ¿Y el sdist?
#
# El sdist (*source distribution*) es el **código fuente** comprimido, con el
# `pyproject.toml` incluido para que pip pueda reconstruir el wheel si no hay uno
# compatible.

# %%
sdists = [p for p in archivos_dist if p.name.endswith(".tar.gz")]
if sdists:
    with tarfile.open(sdists[0]) as t:
        nombres = [m.name for m in t.getmembers() if m.isfile()]
    for n in nombres:
        print("   ", n)
else:
    print("(no se generó sdist en este ambiente)")

# %% [markdown]
# **Interpretación:** el sdist sí conserva la carpeta `src/`, el `pyproject.toml`, el
# `README.md` y la licencia: es el proyecto tal cual, listo para construirse. Instalar
# desde sdist obliga a pip a **construir** en tu compu (y si hubiera código C, a
# compilar); instalar desde wheel solo **copia** archivos. Por eso se publican ambos y
# pip prefiere el wheel.
#
# ## 8. Instalar el wheel en un ambiente limpio
#
# Publicar no prueba nada: hay que **instalarlo en limpio** y ver que funcione. Creamos
# un venv temporal e instalamos el wheel local con `--no-index` (prohibido buscar en
# internet) y `--no-deps` (no tiene dependencias).

# %%
venv = tmp / ".venv"
correr([sys.executable, "-m", "venv", str(venv)])
bin_dir = venv / ("Scripts" if os.name == "nt" else "bin")
py_venv = bin_dir / ("python.exe" if os.name == "nt" else "python")

codigo, salida = correr([str(py_venv), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)])
print("código:", codigo)
print(salida.splitlines()[-1])

# %% [markdown]
# ## 9. Ejecutar el comando de consola
#
# pip creó un ejecutable `mini-champions` (en Windows, `mini-champions.exe`) dentro de
# la carpeta de scripts del venv. Es el equivalente de `act3-demo` en la Tarea 4.

# %%
exe = next(p for p in bin_dir.iterdir() if p.name.startswith("mini-champions"))
print("ejecutable creado:", exe.name)
codigo, salida = correr([str(exe)])
print("código de salida:", codigo)
print(salida)

# %% [markdown]
# **Interpretación:** el comando funciona fuera de la carpeta del proyecto, desde el
# paquete instalado, y encuentra el CSV dentro de `site-packages` (por eso usamos
# `importlib.resources` y no una ruta fija). Cuenta 8 partidos: 3 `Away Win`, 3 `Draw`
# y 2 `Home Win`, que son exactamente las filas del CSV empaquetado.
#
# ## 10. Nombre de distribución vs. nombre de import
#
# Con pip usas el nombre de **distribución**; con `import`, el nombre del **paquete**.
# No tienen por qué coincidir: `scikit-learn` se importa como `sklearn`, y en la
# Tarea 4 `act3-pipeline-mlops` se importa como `act3_pipeline`.

# %%
script = r"""
from importlib import metadata
import mini_champions
print("import mini_champions           ->", mini_champions.__file__.split("site-packages")[-1])
print("metadata.version('mini-champions-uvg') ->", metadata.version("mini-champions-uvg"))
print("¿qué distribución trae el import 'mini_champions'? ->", metadata.packages_distributions()["mini_champions"])
eps = metadata.entry_points(group="console_scripts")
print("comandos registrados:", [f"{e.name} = {e.value}" for e in eps])
try:
    import mini_champions_uvg
except ModuleNotFoundError as e:
    print("import mini_champions_uvg       ->", type(e).__name__, "(el nombre de distribución NO se importa)")
"""
codigo, salida = correr([str(py_venv), "-c", script])
print(salida)

# %% [markdown]
# **Interpretación:** `import mini_champions` funciona, `metadata.version` se consulta
# con el nombre de distribución (`mini-champions-uvg`) e `import mini_champions_uvg`
# falla. `packages_distributions()` hace la traducción import → distribución. En la
# lista de comandos registrados aparece `mini-champions` junto a los de pip, que
# también es un paquete instalado con sus propios *entry points*. En la
# Tarea 4 esta diferencia obligó a escribir `[tool.hatch.build.targets.wheel]
# packages = ["src/act3_pipeline"]`, porque hatchling busca por defecto una carpeta con
# el nombre de la distribución.
#
# ## 11. Normalización de nombres
#
# PyPI considera **el mismo proyecto** a `Act3_Pipeline.MLOps`, `act3-pipeline-mlops`
# y `act3__pipeline--mlops`: pasa todo a minúsculas y cambia `_`, `.` y `-` (repetidos)
# por un solo `-`. Por eso el nombre tiene que ser único **después** de normalizar.

# %%
try:
    from packaging.utils import canonicalize_name
    from packaging.version import Version
except ImportError:
    from pip._vendor.packaging.utils import canonicalize_name
    from pip._vendor.packaging.version import Version

for n in ["act3-pipeline-mlops", "Act3_Pipeline.MLOps", "act3__pipeline--mlops", "act3_pipeline"]:
    print(f"{n:<24} -> {canonicalize_name(n)}")

# %% [markdown]
# **Interpretación:** las tres primeras se normalizan a `act3-pipeline-mlops` (el mismo
# proyecto); la cuarta queda `act3-pipeline`, que es otro nombre. En la Tarea 4 le
# agregamos el sufijo `-mlops` justamente para no chocar con un posible `act3-pipeline`
# ajeno.
#
# ## 12. Versionado semántico: ordenar versiones bien
#
# Las versiones **no** se ordenan como texto. Comparamos el orden alfabético con el
# orden real de PEP 440 (el que usa pip para elegir "la más nueva").

# %%
versiones = ["0.9.0", "0.10.0", "0.1.0", "1.0.0rc1", "1.0.0", "1.0.0.post1", "0.2.0a1", "1.0.1"]
pd.DataFrame({
    "orden como texto": sorted(versiones),
    "orden real (PEP 440)": sorted(versiones, key=Version),
})

# %% [markdown]
# **Interpretación:** como texto, `0.10.0` queda **antes** que `0.9.0` (porque el
# carácter "1" < "9"), y `1.0.0` antes que `1.0.0rc1`. Con `Version`, el orden es el
# correcto: `0.1.0` < `0.2.0a1` (alfa de la 0.2.0) < `0.9.0` < `0.10.0` < `1.0.0rc1`
# (release candidate, **antes** de la final) < `1.0.0` < `1.0.0.post1` < `1.0.1`. Además, pip
# **no instala pre-releases** (`a1`, `rc1`) salvo que uses `--pre` o las pidas
# explícitamente.
#
# Y la regla para subir la versión del paquete según el cambio:

# %%
def siguiente(version, cambio):
    v = Version(version)
    mayor, menor, parche = v.major, v.minor, v.micro
    return {"parche": f"{mayor}.{menor}.{parche + 1}",
            "menor": f"{mayor}.{menor + 1}.0",
            "mayor": f"{mayor + 1}.0.0"}[cambio]


casos = [
    ("0.1.0", "parche", "Arreglo un bug en RatioATexto con '0 of 0'"),
    ("0.1.0", "menor", "Agrego una función nueva de evaluación"),
    ("0.1.0", "mayor", "Renombro cargar_datos() a load_data() (rompe código ajeno)"),
]
pd.DataFrame([{"actual": v, "cambio": c, "ejemplo": e, "nueva": siguiente(v, c)} for v, c, e in casos])

# %% [markdown]
# **Interpretación:** parche para arreglos, menor para funciones nuevas compatibles,
# mayor para cambios que rompen. Y una regla de PyPI/TestPyPI que se aprende a golpes:
# **una versión subida no se puede reemplazar**. Si subiste `0.1.0` con un error, la
# siguiente subida tiene que ser `0.1.1` (aunque borres la `0.1.0`, su número queda
# usado para siempre).

# %%
shutil.rmtree(tmp, ignore_errors=True)
print("Carpeta temporal borrada:", not tmp.exists())

# %% [markdown]
# ## Resumen
#
# - **Disposición `src/`**: obliga a probar contra el paquete instalado, no contra la
#   carpeta local.
# - **`pyproject.toml`**: `[build-system]` (con qué se construye), `[project]`
#   (nombre, versión, dependencias con rangos, licencia), `[project.scripts]`
#   (comandos de consola) y la configuración del backend (qué carpetas y datos entran).
# - **Construir** produce un **sdist** (`.tar.gz`, código fuente que hay que
#   construir) y un **wheel** (`.whl`, un zip listo para copiar). pip prefiere el wheel.
# - `py3-none-any` = Python puro, sirve en cualquier sistema; los wheels con código C
#   llevan la versión de Python y la plataforma en el nombre.
# - El **CSV** solo viaja si se declara como datos del paquete (`package-data` en
#   setuptools; en hatchling, todo lo que está dentro de la carpeta del paquete) y se
#   lee con `importlib.resources`.
# - **Nombre de distribución** (`pip install mini-champions-uvg`) ≠ **nombre de
#   import** (`import mini_champions`); los nombres se normalizan antes de comparar.
# - **Versionado semántico** MAYOR.MENOR.PARCHE; las versiones se comparan con
#   `packaging.version`, no como texto; una versión publicada no se puede re-subir.
# - Lo que falta para publicar (necesita internet): `twine check dist/*` y
#   `twine upload --repository testpypi dist/*` con un token en `.env`.
