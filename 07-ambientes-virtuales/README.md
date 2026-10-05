# 07 · Ambientes virtuales y dependencias

🎬 Video: [▶️ en español](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/07-ambientes-virtuales-es.mp4) · [▶️ in English](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/07-ambientes-virtuales-en.mp4) · [todos los videos](https://github.com/DiegoLinares11/RepasoMLOps/releases/tag/videos)

## 🧱 Conocimiento previo

Antes de hablar de ambientes virtuales hay que tener claras cinco piezas. Si alguna
te suena borrosa, este es el momento.

### 1. El intérprete de Python es un programa más

Cuando escribes `python entrenar.py`, la terminal ejecuta un **programa** llamado
`python` (en Windows, `python.exe`) que lee tu archivo y lo ejecuta línea por línea.
Ese programa vive en una carpeta concreta de tu disco, por ejemplo
`C:\Users\dlinares\AppData\Local\Programs\Python\Python312\python.exe`.

Puedes tener **varios** Pythons instalados a la vez (3.11, 3.12, el de Anaconda...).
Cada uno es una carpeta distinta, y cada uno tiene **sus propias librerías**.

### 2. Paquete, librería, módulo

| Palabra | Qué es | Ejemplo |
|---|---|---|
| **Módulo** | Un archivo `.py` que puedes importar | `data.py` → `import data` |
| **Paquete** | Una carpeta con módulos (y un `__init__.py`) | `act3_pipeline/` |
| **Librería / distribución** | Un paquete empaquetado para instalarse con pip | `scikit-learn`, `act3-pipeline-mlops` |

En la vida diaria "paquete" y "librería" se usan como sinónimos.

### 3. pip y PyPI: la tienda y el repartidor

- **PyPI** (<https://pypi.org>) es la "tienda" pública donde están publicadas cientos de
  miles de librerías.
- **pip** es el "repartidor": descarga la librería de PyPI y la deja en una carpeta
  llamada **`site-packages`**, dentro del Python que lo ejecutó.

Esto último es la clave de todo el tema: **`pip install pandas` instala pandas en el
Python al que pertenece ese pip**, no "en la compu". Por eso conviene escribir siempre
`python -m pip install ...`: así sabes que pip y python son del mismo lugar.

### 4. Cuando haces `import pandas`, Python busca en una lista de carpetas

Esa lista se llama `sys.path`. Python la recorre en orden y usa la **primera** carpeta
`pandas/` que encuentra. Si ninguna la tiene: `ModuleNotFoundError`.

### 5. El PATH: dónde busca la terminal los programas

Cuando escribes `python` en PowerShell, Windows no sabe mágicamente dónde está. Recorre
la variable de entorno **`PATH`**, una lista de carpetas separadas por `;` (en
Linux/macOS por `:`), y ejecuta el **primer** `python.exe` que encuentra.

```powershell
# PowerShell: ver el PATH, una carpeta por línea, y qué python se ejecutaría
$env:PATH -split ';'
Get-Command python          # o: where.exe python
```

```bash
# bash
echo $PATH | tr ':' '\n'
which python3
```

### 6. Las versiones tienen significado (versionado semántico)

Una versión como `1.8.0` se lee **MAYOR.MENOR.PARCHE**:

- **PARCHE** (1.8.0 → 1.8.1): arregla bugs, no cambia nada de lo que usas.
- **MENOR** (1.8 → 1.9): agrega cosas nuevas, lo viejo sigue funcionando.
- **MAYOR** (1.x → 2.0): puede **romper** código que funcionaba.

Con estas seis piezas ya se entiende el problema.

## 🎯 Qué tienes que saber

### 1. El problema: un solo Python para todos los proyectos

Imagina que en tu compu tienes **un solo** Python con **una sola** `site-packages`:

- El proyecto A (un curso del año pasado) necesita `scikit-learn==1.3`.
- El proyecto B (la Actividad 4) necesita `scikit-learn==1.8.0`.

Solo puede haber **una** versión instalada a la vez. Si actualizas para B, rompes A.
Eso es un **conflicto de versiones**.

Y hay dos problemas más:

- **"En mi máquina funciona"**: tu compañero instala "la última versión" de todo un mes
  después y obtiene otras versiones, otros resultados u otros errores.
- **Reproducibilidad**: en ML, la versión de la librería cambia los números. Lo vivimos
  en el curso: en la Actividad 3, con el mismo código y `random_state=42`,
  `GridSearchCV` dio `f1_macro` **0.563 en Windows** y **0.611 en macOS** porque cada
  compu tenía una versión distinta de scikit-learn. Fijar la semilla no alcanza: hay
  que fijar las versiones.

**Analogía:** un Python global es como una cocina compartida con **una sola** alacena.
Si un cocinero cambia el azúcar por edulcorante para su receta, le arruina el pastel a
todos. Un ambiente virtual le da a **cada receta su propia alacena**.

### 2. Qué es por dentro un ambiente virtual

Un ambiente virtual (venv) es **solo una carpeta**. No es una máquina virtual ni un
contenedor. Contiene:

```
.venv/
├── pyvenv.cfg            ← "DNI": dice de qué Python salió y que está aislado
├── Scripts/              ← (Windows)  python.exe, pip.exe, Activate.ps1, activate.bat
│   (bin/ en Linux/macOS)    python, pip, activate, Activate.ps1
└── Lib/site-packages/    ← (Windows)  AQUÍ se instalan sus librerías
    (lib/python3.12/site-packages/ en Linux/macOS)
```

Cómo funciona, paso a paso:

1. `python -m venv .venv` crea la carpeta y escribe `pyvenv.cfg` con
   `home = <carpeta del Python original>` e `include-system-site-packages = false`.
2. El `python` de `.venv\Scripts` **no es una copia completa** de Python: reutiliza el
   intérprete original. Lo que cambia es que, al arrancar, ve el `pyvenv.cfg` y usa
   **la `site-packages` del venv** en vez de la global.
3. Por eso dentro de un venv `sys.prefix` (la carpeta del ambiente) es distinto de
   `sys.base_prefix` (el Python original). Esa es la forma de saber si estás dentro.

En el notebook de este tema se ve con números reales: un venv **recién creado** tenía
1905 archivos y 41.9 MB, `import pandas` funcionaba afuera y daba `ModuleNotFoundError`
adentro.

### 3. Activar = cambiar el PATH (y nada más)

"Activar" el ambiente **no** instala ni carga nada. El script de activación:

1. Pone `.venv\Scripts` **al principio** del `PATH`, así el primer `python` que
   encuentra la terminal es el del venv.
2. Define la variable `VIRTUAL_ENV` con la ruta del ambiente.
3. Cambia el prompt para que veas `(.venv)` al inicio.

`deactivate` deshace esos tres cambios. Y como solo afecta al `PATH` de **esa**
terminal, si abres otra ventana tienes que volver a activar.

**Consecuencia práctica:** no hace falta activar si llamas directamente al ejecutable
del ambiente. En scripts y en CI es lo más seguro:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe entrenar.py
```

### 4. Los comandos del día a día

| Qué quieres | PowerShell (Windows) | bash (Linux / macOS) |
|---|---|---|
| Crear el ambiente | `py -3.12 -m venv .venv` (o `python -m venv .venv`) | `python3 -m venv .venv` |
| Activarlo | `.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |
| Comprobar cuál python uso | `Get-Command python` | `which python` |
| Comprobar que estoy dentro | `python -c "import sys; print(sys.prefix)"` | igual |
| Instalar dependencias | `python -m pip install -r requirements.txt` | igual |
| Congelar versiones exactas | `python -m pip freeze \| Out-File -Encoding utf8 requirements-lock.txt` | `python -m pip freeze > requirements-lock.txt` |
| Ver qué hay instalado | `python -m pip list` | igual |
| Salir | `deactivate` | `deactivate` |
| Borrarlo | `Remove-Item .venv -Recurse -Force` | `rm -rf .venv` |

En Git Bash sobre Windows se activa con `source .venv/Scripts/activate`.

### 5. Problemas típicos en Windows (y cómo se arreglan)

| Síntoma | Causa | Solución |
|---|---|---|
| `Activate.ps1 no se puede cargar porque la ejecución de scripts está deshabilitada en este sistema` | La política de ejecución de PowerShell bloquea scripts `.ps1` | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` (una vez, sin administrador). Solo para la ventana actual: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| Escribes `python` y se abre la **Microsoft Store** | Alias falso de Windows | Configuración → Aplicaciones → Configuración avanzada → **Alias de ejecución de aplicaciones**: desactivar `python.exe` y `python3.exe`. O usar `py` |
| `python` ejecuta una versión que no quieres | Varias versiones en el PATH | Usar el **py launcher**: `py --list` muestra las instaladas, `py -3.12 -m venv .venv` elige una |
| Instalaste algo pero `import` dice `ModuleNotFoundError` | Instalaste con un pip y ejecutas con otro Python | Usar siempre `python -m pip`; en VS Code, `Ctrl+Shift+P` → *Python: Select Interpreter* → elegir `.venv` |
| Jupyter no ve las librerías del venv | El kernel de Jupyter es otro Python | Dentro del venv: `python -m pip install ipykernel` y `python -m ipykernel install --user --name repaso` |
| `pip freeze > archivo.txt` da un archivo que pip no lee | PowerShell 5 guarda con `>` en UTF-16 | `pip freeze \| Out-File -Encoding utf8 requirements-lock.txt` |

**El py launcher** (`py.exe`) se instala junto con el Python oficial de python.org y es
la forma recomendada de elegir versión en Windows. No existe en Linux/macOS: allá se
usa `python3.12` directamente.

### 6. Fijar versiones: `==`, `>=`, `~=`

| Especificador | Significa | Acepta (de la tabla del notebook) | Cuándo usarlo |
|---|---|---|---|
| `scikit-learn` | Cualquier versión (la última de hoy) | todas | Herramientas secundarias, prototipos |
| `>=1.3` | 1.3 o más nueva | 1.3.0, 1.3.2, 1.4.0, 1.8.0, **2.0.0** | Dependencias de una **librería** que publicas |
| `~=1.3.0` | Compatible: `>=1.3.0, <1.4` | 1.3.0, 1.3.2 | Aceptar solo parches |
| `~=1.3` | Compatible: `>=1.3, <2` | 1.3.0 … 1.8.0, **no** 2.0.0 | Aceptar mejoras sin cambios mayores |
| `>=1.3,<2` | Lo mismo, explícito | igual que `~=1.3` | Más legible |
| `==1.8.0` | Exactamente esa | solo 1.8.0 | **Aplicaciones** que se despliegan (Docker) |
| `!=1.4.0` | Todas menos esa | | Saltarse una versión con un bug |

**La regla del curso (la volverás a ver en los temas 08 y 09):**

- Una **librería** (algo que otros instalan junto con sus propias cosas) declara
  **rangos** (`>=`), para no imponer versiones y dejar que pip resuelva con lo demás.
  Así lo hace el `pyproject.toml` de la Tarea 4.
- Una **aplicación** (algo que tú despliegas y debe dar siempre lo mismo) fija
  **versiones exactas** (`==`). Así lo hacen los `requirements.txt` de los Dockerfiles
  de la Actividad 4: `scikit-learn==1.8.0`, `pandas==2.3.3`, `numpy==2.4.1`...

### 7. `requirements.txt` vs `pip freeze` vs lock file

| | `requirements.txt` escrito a mano | `pip freeze` | Lock file (`uv.lock`, `poetry.lock`) |
|---|---|---|---|
| Quién lo escribe | Tú | pip, a partir de lo instalado | La herramienta (uv, poetry) |
| Qué contiene | Dependencias **directas** | **Todo**, con transitivas | Todo, con transitivas **y hashes** |
| Versiones | Rangos o nada | Siempre `==` | Exactas |
| Expresa | **Intención** | **Foto** del ambiente actual | Foto **reproducible y verificable** |
| Ejemplo real | 11 líneas en el `requirements.txt` de este repo | 114 líneas en el ambiente donde se ejecutó el notebook | |

**Dependencia transitiva**: la que no pediste pero llega porque otra la necesita
(pandas trae `python-dateutil`, que trae `six`). Si no la fijas, puede cambiar sola.

**Analogía:** `requirements.txt` es la lista del súper ("leche, pan"); `pip freeze` es
el **ticket** ("Leche Dos Pinos 1 L lote 2210, pan Bimbo 680 g"). El lock file es el
ticket con código de barras para comprobar que nadie cambió el producto.

Un problema de `pip freeze`: mezcla lo que pediste con lo que llegó solo, y si un día
quitas pandas no sabes cuáles transitivas puedes borrar. Por eso las herramientas
modernas separan los dos archivos: `pyproject.toml` (intención) + lock (foto).

### 8. `pyproject.toml` y `.python-version`

- **`pyproject.toml`**: el archivo estándar moderno de un proyecto de Python. Declara
  nombre, versión, `requires-python` y `dependencies` (con rangos). Sirve para
  proyectos y para librerías que se publican (tema 08). Ver
  [`ejemplos/pyproject.toml`](ejemplos/pyproject.toml).
- **`.python-version`**: un archivo de una línea (por ejemplo `3.12`) que le dice a
  **pyenv** y a **uv** qué versión de Python usar en esa carpeta. Se versiona en Git.
  `requires-python = ">=3.10"` dice "con qué versiones funciona"; `.python-version` dice
  "cuál uso yo para desarrollar".

### 9. Las herramientas: venv, virtualenv, conda, uv, poetry

| Herramienta | Qué es | Instala Python | Librerías no-Python (CUDA, GDAL) | Lock file | Cuándo |
|---|---|---|---|---|---|
| **venv** | Módulo **incluido** en Python 3.3+ | No | No | No (usa `pip freeze`) | Siempre disponible; lo que usamos en el curso |
| **virtualenv** | El "abuelo" de venv, paquete aparte | No | No | No | Python viejo o crear ambientes más rápido |
| **conda** | Gestor de ambientes **y** paquetes (Anaconda/Miniconda) | **Sí** | **Sí** | Con `conda-lock` | Ciencia de datos con dependencias compiladas, GPU |
| **uv** | Gestor ultrarrápido escrito en Rust (de Astral) | **Sí** | No | **Sí** (`uv.lock`) | Proyectos nuevos: reemplaza pip + venv + pyenv |
| **poetry** | Gestor de dependencias y empaquetado | No | No | **Sí** (`poetry.lock`) | Librerías que se publican, equipos |
| **pipenv** | `Pipfile` + `Pipfile.lock` | No | No | Sí | Proyectos que ya lo usan |

Equivalencias rápidas:

| Acción | venv + pip | conda | uv |
|---|---|---|---|
| Crear | `python -m venv .venv` | `conda create -n mlops python=3.12` | `uv venv` (o `uv init`) |
| Activar | `.venv\Scripts\Activate.ps1` | `conda activate mlops` | `.venv\Scripts\Activate.ps1` (o no activar y usar `uv run`) |
| Instalar | `pip install pandas` | `conda install pandas` | `uv add pandas` |
| Recrear desde receta | `pip install -r requirements.txt` | `conda env create -f environment.yml` | `uv sync` |

Dato útil: los ambientes de **conda** no viven en la carpeta del proyecto, sino en
`<carpeta de conda>\envs\<nombre>`. Los de venv/uv viven en `.venv` dentro del proyecto.

### 10. Por qué la carpeta `.venv` NO se sube a Git

1. **Pesa**: vacío ya eran 41.9 MB en el notebook; con pandas y scikit-learn, cientos de MB.
2. **No es portable**: `pyvenv.cfg` guarda **rutas absolutas** de tu máquina, y en
   Windows contiene `.exe` que no sirven en macOS ni en Linux.
3. **Es desechable**: se recrea en un minuto desde la receta.

Lo que se versiona es la **receta**: `requirements.txt` / `pyproject.toml` + lock +
`.python-version`. La carpeta va en el `.gitignore` (este repo ya ignora `.venv/` y `venv/`).

### 11. Del ambiente virtual a Docker

Un venv aísla **las librerías de Python**, pero no el sistema operativo, ni la versión
de Python instalada, ni las librerías del sistema (por ejemplo, la libpq que necesita
Postgres). Para fijar **todo el entorno** se usa Docker (tema 09). La escalera es:

```
requirements.txt con rangos  →  pip freeze / lock  →  venv  →  imagen de Docker
   "más o menos esto"          "exactamente esto"    "aislado"   "aislado + sistema operativo"
```

## 📂 Qué hicimos en el curso

**Taller 2 (ambientes virtuales).** No hay repositorio del taller: este tema se armó
desde la teoría estándar, y se conecta con cómo se usaron los ambientes en las demás
entregas:

- **Actividad 1 y Actividad 3** ([Actividad1-MLOPS](https://github.com/DiegoLinares11/Actividad1-MLOPS),
  [Actividad3-MLOPS](https://github.com/DiegoLinares11/Actividad3-MLOPS)): los
  `requirements.txt` usan **rangos** (`scikit-learn>=1.3`, `pandas>=2.0`,
  `numpy>=1.24`, `scipy>=1.10` en la Act. 3) más `jupyter` y `notebook` sin versión. Sus
  `.gitignore` ya excluyen `.venv/`, `venv/` y `env/`.
- **El problema que apareció**: en la Actividad 3, el mismo código con
  `random_state=42` dio en `GridSearchCV` un `f1_macro` de **0.563 en Windows** y
  **0.611 en macOS**, porque cada máquina tenía instalada una versión distinta de
  scikit-learn. Los rangos `>=` dejaron que cada quien instalara algo distinto.
- **La solución (Actividad 4)**: los `requirements.txt` del entrenador y de la API
  fijan versiones **exactas** e **idénticas** (`scikit-learn==1.8.0`, `pandas==2.3.3`,
  `numpy==2.4.1`, `scipy==1.17.1`, `joblib==1.5.3`), y Docker fija además Python 3.12.
  El modelo dio lo mismo en Windows, macOS y el contenedor: CV `f1_macro` 0.619,
  accuracy 0.690 y `f1_macro` en test 0.631.

## 🧪 Práctica

**`repaso.ipynb`** (ya ejecutado; generado desde `repaso.py`). Sin internet y sin instalar nada:

1. Muestra `sys.executable`, `sys.prefix` y `sys.base_prefix` del notebook.
2. Recorre `sys.path` y encuentra la `site-packages` de donde sale pandas.
3. Crea un venv temporal con `python -m venv`, lista su contenido y lee su `pyvenv.cfg`.
4. Compara `sys.prefix` dentro y fuera del venv.
5. Demuestra el aislamiento: `import pandas` funciona afuera y falla adentro.
6. `pip freeze` / `pip list` en el venv vacío.
7. Compara el `requirements.txt` del repo (11 líneas) con `pip freeze` (114 líneas).
8. Simula la activación (anteponer la carpeta al PATH) y muestra las líneas de
   `Activate.ps1` que lo hacen.
9. Tabla de qué versiones acepta cada especificador (`==`, `>=`, `~=`, `!=`).
10. Mide el tamaño del venv vacío y lo borra.

```powershell
cd RepasoMLOps
python tools/build_nb.py 07-ambientes-virtuales/repaso.py   # regenera y ejecuta
```

**`ejemplos/`** (archivos reales comentados línea por línea):

| Archivo | Qué es |
|---|---|
| [`requirements.txt`](ejemplos/requirements.txt) | Todas las formas de escribir una dependencia: `>=`, `~=`, `==`, `!=`, extras, marcadores por sistema operativo, `-r`, `-e .` |
| [`requirements-lock.txt`](ejemplos/requirements-lock.txt) | Cómo se ve un `pip freeze` y por qué aparecen transitivas |
| [`environment.yml`](ejemplos/environment.yml) | Receta de conda, con Python incluido y sección `pip:` |
| [`pyproject.toml`](ejemplos/pyproject.toml) | Proyecto moderno con uv (dependencias + grupo `dev`) |
| [`setup_entorno.ps1`](ejemplos/setup_entorno.ps1) | Script de PowerShell que crea/recrea `.venv` e instala todo |
| [`setup_entorno.sh`](ejemplos/setup_entorno.sh) | El mismo script en bash |
| [`gitignore-python.txt`](ejemplos/gitignore-python.txt) | Plantilla de `.gitignore` para proyectos de ML |

**[`ejercicios.md`](ejercicios.md)**: tareas para hacer en tu compu.

## ❓ Preguntas tipo examen

**P:** ¿Qué problema resuelve un ambiente virtual?
**R:** Los conflictos de versiones entre proyectos (cada uno tiene su propia `site-packages`), el "en mi máquina funciona" y la falta de reproducibilidad, porque permite instalar exactamente las versiones que el proyecto declara sin tocar el Python global.

**P:** ¿Qué es físicamente un venv?
**R:** Una carpeta con un `pyvenv.cfg`, una carpeta de ejecutables (`Scripts\` en Windows, `bin/` en Linux/macOS) con un `python` que reutiliza el intérprete original, y su propia `site-packages` donde pip instala.

**P:** ¿Qué hace exactamente "activar" un ambiente?
**R:** Antepone la carpeta de ejecutables del venv al `PATH`, define `VIRTUAL_ENV` y cambia el prompt. No instala ni carga nada; por eso se puede omitir llamando directo a `.venv\Scripts\python.exe`.

**P:** ¿Cómo sabes desde Python si estás dentro de un venv?
**R:** Si `sys.prefix != sys.base_prefix`. `sys.prefix` es la carpeta del ambiente y `sys.base_prefix` la del Python original.

**P:** ¿Por qué conviene `python -m pip install` en vez de `pip install`?
**R:** Porque garantiza que pip pertenezca al mismo Python que vas a usar. `pip` a secas puede ser el de otra instalación que esté antes en el PATH, y terminas instalando en el lugar equivocado.

**P:** ¿Diferencia entre `scikit-learn>=1.3`, `~=1.3` y `==1.8.0`?
**R:** `>=1.3` acepta cualquier versión desde 1.3, incluida la 2.0; `~=1.3` acepta `>=1.3, <2` (cambios compatibles); `==1.8.0` acepta solo esa versión.

**P:** ¿Cuándo usar rangos y cuándo versiones exactas?
**R:** Rangos en una librería que otros instalan (para no imponer versiones y dejar que pip resuelva), versiones exactas en una aplicación que se despliega y debe dar siempre lo mismo. En el curso: `pyproject.toml` de la Tarea 4 con `>=`, `requirements.txt` de la Actividad 4 con `==`.

**P:** ¿Qué diferencia hay entre un `requirements.txt` escrito a mano y `pip freeze`?
**R:** El primero lista las dependencias directas que pediste, normalmente con rangos (intención). `pip freeze` lista todo lo instalado, incluidas las transitivas, siempre con `==` (foto exacta del ambiente).

**P:** ¿Qué agrega un lock file como `uv.lock` frente a `pip freeze`?
**R:** Separa lo que pediste (en `pyproject.toml`) de la resolución completa, incluye las transitivas con versión exacta y los hashes de cada archivo para verificar que no fueron alterados, y la herramienta lo mantiene sola.

**P:** ¿Por qué no se sube `.venv` al repositorio?
**R:** Pesa mucho (vacío ya ocupaba 41.9 MB en el notebook), guarda rutas absolutas de tu máquina y ejecutables de tu sistema operativo, y se recrea en minutos desde la receta.

**P:** Activas el venv en PowerShell y sale "la ejecución de scripts está deshabilitada". ¿Qué haces?
**R:** `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` una vez (o `-Scope Process -ExecutionPolicy Bypass` solo para esa ventana), o no activar y usar `.venv\Scripts\python.exe` directamente.

**P:** ¿Qué puede hacer conda que venv no?
**R:** Instalar otra versión de Python dentro del ambiente e instalar librerías que no son de Python (CUDA, MKL, GDAL) ya compiladas.

**P:** ¿Para qué sirve `.python-version` y en qué se diferencia de `requires-python`?
**R:** `.python-version` le dice a pyenv/uv qué versión exacta usar en esa carpeta para desarrollar; `requires-python` en `pyproject.toml` declara el rango de versiones con las que el proyecto funciona.

**P:** Si un venv aísla las librerías, ¿por qué hizo falta Docker en la Actividad 4?
**R:** Porque un venv no fija la versión de Python instalada, ni el sistema operativo, ni las librerías del sistema. Docker empaqueta todo el entorno, por eso el resultado fue idéntico en Windows, macOS y el contenedor.

## 🏋️ Ejercicios

Los detallados, paso a paso y con comandos de PowerShell y bash, están en
[`ejercicios.md`](ejercicios.md). Resumen:

1. **Dos proyectos, dos versiones**: crea dos venvs con versiones distintas de
   scikit-learn y comprueba que conviven.
2. **Detective del PATH**: activa, desactiva y mira cómo cambian `$env:PATH`,
   `Get-Command python` y `sys.prefix`.
3. **De intención a foto**: escribe un `requirements.txt` de 3 líneas, instálalo, haz
   `pip freeze` y cuenta las transitivas.
4. **Reproduce en limpio**: borra `.venv`, recréalo desde el lock y verifica que las
   versiones salgan idénticas.
5. **Lo mismo con uv**: rehaz el ejercicio 4 con `uv init`, `uv add` y `uv sync`.

## 🔗 Referencias

- Documentación oficial de `venv`: <https://docs.python.org/3/library/venv.html>
- Guía de la PyPA, instalar paquetes en un ambiente virtual: <https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/>
- Especificadores de versión (PEP 440): <https://packaging.python.org/en/latest/specifications/version-specifiers/>
- Formato de `requirements.txt`: <https://pip.pypa.io/en/stable/reference/requirements-file-format/>
- Python en Windows y el py launcher: <https://docs.python.org/3/using/windows.html>
- Políticas de ejecución de PowerShell: <https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_execution_policies>
- uv: <https://docs.astral.sh/uv/> · conda: <https://docs.conda.io/> · poetry: <https://python-poetry.org/docs/>
- Repos del curso: [Actividad1-MLOPS](https://github.com/DiegoLinares11/Actividad1-MLOPS), [Actividad3-MLOPS](https://github.com/DiegoLinares11/Actividad3-MLOPS), [Actividad4-MLOPS](https://github.com/DiegoLinares11/Actividad4-MLOPS)
