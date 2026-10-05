# 13 · Entry points: el pipeline como comandos y plugins

🎬 Video: [▶️ en español](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/13-entry-points-es.mp4) · [▶️ in English](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/13-entry-points-en.mp4) · [todos los videos](https://github.com/DiegoLinares11/RepasoMLOps/releases/tag/videos)

## 🧱 Conocimiento previo

### 1. Qué pasa cuando escribes `jupyter` o `pip` en la terminal

La terminal busca un **ejecutable** con ese nombre en las carpetas de la variable `PATH`. En un
ambiente virtual, esos ejecutables viven en `.venv\Scripts\` (Windows) o `.venv/bin/` (Linux y
macOS), y **activar** el ambiente es justamente poner esa carpeta al principio del `PATH`.

Por eso, si el ambiente no está activado, el comando "no existe" aunque el paquete esté instalado:
el ejecutable está ahí, pero la terminal no lo busca en esa carpeta.

### 2. Lo que deja `pip install` (repaso de los temas 07 y 08)

Además de copiar el código a `site-packages`, pip deja una carpeta de **metadata** por paquete:
`<nombre>-<versión>.dist-info/`. Ahí están el nombre, la versión, las dependencias y, si las hay,
las entradas de `entry_points.txt`. Python puede leer esa metadata de cualquier paquete instalado
con el módulo estándar `importlib.metadata`.

### 3. El código de salida de un proceso

Todo programa termina con un número: **0 si salió bien**, cualquier otro si algo falló. No se ve en
pantalla, pero lo leen las herramientas que encadenan comandos:

| Dónde | Cómo se ve el código de la última orden |
|---|---|
| PowerShell | `$LASTEXITCODE` |
| Bash | `echo $?` |
| Python | `sys.exit(1)` lo pone; `subprocess.run(...).returncode` lo lee |

`make`, GitHub Actions y Airflow se detienen cuando un paso devuelve algo distinto de 0.

## 🎯 Qué tienes que saber

### 1. Qué es un entry point

Un **entry point** es una línea de metadata que dice "este nombre apunta a este objeto de Python".
Tiene tres partes (especificación de PyPA):

| Parte | Ejemplo | Para qué sirve |
|---|---|---|
| **Grupo** | `console_scripts`, `act9_pipeline.modelos` | Qué tipo de cosa ofrece |
| **Nombre** | `act9-entrenar`, `knn` | Cómo se llama dentro del grupo |
| **Referencia** | `act9_pipeline.cli.entrenar:main` | Dónde está: `modulo:objeto` |

Analogía: un **timbre**. Desde afuera aprietas un botón con un nombre ("act9-entrenar") y suena
adentro, sin saber en qué cuarto está la cocina. Si mañana mueves la cocina, solo recableas el
timbre: el botón sigue igual.

### 2. Dos usos: comandos y plugins

**a) Comandos (`console_scripts`).** En el `pyproject.toml` van en `[project.scripts]`. Al instalar,
el instalador crea **un ejecutable por línea**:

```toml
[project.scripts]
act9-entrenar = "act9_pipeline.cli.entrenar:main"   # crea .venv\Scripts\act9-entrenar.exe
```

El ejecutable no contiene tu código: es un lanzador que **importa la función, la llama sin
argumentos y usa lo que devuelve como código de salida** (ver `ejemplos/lanzador_generado.py`).

**b) Plugins (un grupo propio).** En `[project.entry-points."<grupo>"]`. No crea ejecutables; solo
deja el registro en la metadata para que **otro programa lo descubra**:

```toml
[project.entry-points."act9_pipeline.modelos"]
svc = "act9_pipeline.modelos:svc"
```

```python
from importlib.metadata import entry_points

for ep in entry_points(group="act9_pipeline.modelos"):
    spec = ep.load()()      # load() importa el objeto; () llama a la función
```

`entry_points()` revisa los `entry_points.txt` de **todos** los paquetes instalados. Por eso otro
paquete, escrito por otra persona, puede registrarse en el mismo grupo y aparecer solo. Así
funcionan los plugins de pytest (`pytest11`), los comandos de Flask (`flask.commands`) y los
backends de MLflow (`mlflow.tracking_store`).

| | `[project.scripts]` | `[project.entry-points."grupo"]` |
|---|---|---|
| Grupo | `console_scripts` (especial) | Uno inventado por ti, idealmente con el nombre de tu paquete al inicio |
| Crea ejecutables | Sí, uno por línea | No |
| Quién lo usa | La terminal, `make`, Docker, cron | Tu propio código, con `importlib.metadata` |
| Ejemplo del curso | `act9-entrenar` | Familias de modelos: `svc`, `knn`... |

### 3. Un buen descubridor de plugins

La función `descubrir_modelos()` de la Actividad 9 (`ejemplos/plugins.py`) muestra lo que hay que
cuidar:

- **Un contrato claro**: cada plugin es una función sin argumentos que devuelve
  `{"estimador": ..., "espacio": ..., "descripcion": ...}`.
- **Validar** que el plugin cumpla el contrato antes de usarlo.
- **Ordenar por nombre**, para que el resultado no dependa del orden del sistema de archivos.
- **Aislar fallas**: si un plugin truena se omite con un aviso, y el resto del pipeline sigue.

### 4. El código de salida como contrato

Como el ejecutable hace `sys.exit(main())`, **lo que devuelve tu función es lo que ve el mundo**.
En la Actividad 9, `act9-evaluar --umbral 0.50` devolvía `1` si el `f1_macro` no llegaba al mínimo.
Eso es una **compuerta de calidad** que funciona en cualquier orquestador sin leer la salida.

### 5. Entry points con cualquier gestor de paquetes

Son parte del estándar de empaquetado, así que el mismo `pyproject.toml` sirve con todos:

| Gestor | Cómo se ejecuta el comando |
|---|---|
| pip (venv) | Activar el ambiente y `act9-entrenar` |
| conda | `conda activate act9-mlops` o `conda run -n act9-mlops act9-entrenar` |
| uv | `uv run act9-entrenar`, o `uvx --from . act9 info` en un ambiente temporal |
| Poetry 2 | `poetry run act9-entrenar` |
| pipx | `pipx install .` (un ambiente aislado por herramienta) |

### 6. Entry points y Makefile: el qué y el cuándo

- El **entry point** define **qué** se ejecuta: la interfaz de cada etapa, dentro del paquete.
- El **Makefile** define **cuándo y en qué orden**: las dependencias entre etapas, fuera del
  paquete. Además repite solo las etapas cuyas entradas cambiaron (compara fechas de archivos).
- **CI** (GitHub Actions) solo llama al Makefile, así que corre igual que en tu laptop.

Las recetas quedan cortas porque llaman comandos, no rutas internas:

```make
$(MODELO): $(TRAIN)
	act9-entrenar --entrada $(TRAIN) --salida modelos --n-iter $(N_ITER)
```

### 7. Las trampas

- **Sin el ambiente activado el comando no existe.** Alternativas: `python -m act9_pipeline` o
  `uv run` / `poetry run` / `conda run`.
- **Instalar un plugin puede cambiar los resultados.** Si la búsqueda reparte sus combinaciones entre
  las familias descubiertas, una familia nueva cambia qué combinaciones se prueban. En producción,
  fija las familias explícitamente.
- **Nombres de grupo genéricos chocan.** Un grupo llamado `modelos` lo puede usar cualquier otro
  paquete; `act9_pipeline.modelos` no.
- **Cambiar un entry point exige reinstalar.** El ejecutable y `entry_points.txt` se escriben al
  instalar; editar el `pyproject.toml` no basta.

## 📂 Qué hicimos en el curso

**Actividad 9** ([repo Actividad-9-MLOPS](https://github.com/DiegoLinares11/Actividad-9-MLOPS)):
investigar los entry points y adaptar el pipeline de la Actividad 3, que ahora es `act9_pipeline`.

| Comando | Etapa de CRISP-DM | Qué hace |
|---|---|---|
| `act9-datos` | Data Preparation | Limpia (151 → 144 partidos) y separa train/test estratificado |
| `act9-entrenar` | Modeling | `RandomizedSearchCV` sobre las familias descubiertas como plugins |
| `act9-evaluar` | Evaluation | Métricas y baseline; **código 1** si `f1_macro < --umbral` |
| `act9-predecir` | Deployment | Predicciones para partidos nuevos |
| `act9 <etapa>`, `act9-demo` | — | Subcomandos, `act9 info`, `act9 modelos` y una demo de evidencia |

- Las 4 familias propias (`random_forest`, `regresion_logistica`, `svc`, `hist_gradient_boosting`)
  se registran en el grupo `act9_pipeline.modelos`. El paquete aparte `plugins/act9-modelo-knn`
  agregó una quinta sin tocar el pipeline.
- Un **Makefile** encadena las etapas y GitHub Actions solo llama al Makefile, con un job para pip y
  otro para uv. En Windows, `make` vino con el ambiente de conda `act9-mlops` (GNU Make 4.4.1).
- Con `make pipeline UMBRAL=0.90`, `act9-evaluar` devolvió 1, make se detuvo, borró
  `metricas.json` (`.DELETE_ON_ERROR`) y no corrió la predicción.

Resultados (todas las semillas fijas):

| Configuración | Mejor `f1_macro` en CV | Ganador | Test: accuracy / `f1_macro` |
|---|---|---|---|
| Familias en el orden de la Actividad 3 | 0.619 | LogisticRegression | 0.690 / 0.631 (idéntico a la Actividad 3) |
| Todas, en orden alfabético (por defecto) | 0.652 | SVC | 0.655 / 0.604 |
| Con el plugin `knn` instalado (5 familias) | 0.622 | SVC | 0.655 / 0.604 |
| Solo `knn` | 0.559 | KNeighborsClassifier | 0.621 / 0.534 |
| Baseline (clase mayoritaria) | — | — | 0.483 / 0.217 |

El mismo `pyproject.toml` dio lo mismo con pip, conda, uv y Poetry. Y quedaron dos lecciones:
instalar un plugin cambió el resultado, y ganar en CV (0.652 contra 0.619) no garantizó ganar en
test (0.604 contra 0.631), porque con 29 partidos la diferencia fue de un solo acierto.

## 🧪 Práctica

**`repaso.ipynb`** (ya ejecutado; corre en segundos y sin internet):

1. Lee el `pyproject.toml` real de la Actividad 9 con `tomllib` y separa comandos y plugins.
2. Lista los `console_scripts` de tu ambiente (44 en el que se ejecutó).
3. **Simula `pip install`**: crea a mano la carpeta `.dist-info` con su `entry_points.txt`.
4. Descubre las familias del grupo `repaso.modelos` y luego "instala" un plugin KNN: pasan de 2 a 3
   sin tocar el código.
5. Entrena cada familia descubierta con el dataset de la Champions (6 variables numéricas,
   `f1_macro` en CV de 5 partes): regresión logística 0.645, random forest 0.603, KNN 0.520.
6. Imita el lanzador: carga el entry point `mini-entrenar`, lo llama y devuelve código 0.
7. Simula la compuerta: `f1_macro` 0.645 da código 0 (make sigue) y 0.420 da código 1 (make se
   detiene).

**`ejemplos/`**, con los archivos reales de la entrega:

| Archivo | Qué ver |
|---|---|
| `pyproject.toml` | `[project.scripts]` y el grupo `act9_pipeline.modelos`, comentados |
| `plugin-knn/pyproject.toml` y `act9_modelo_knn.py` | Un paquete sin comandos que solo se registra en el grupo |
| `plugins.py` | `descubrir_modelos()`: ordenar, validar el contrato y aislar fallas |
| `lanzador_generado.py` | Lo que hay dentro del `.exe` que crea pip |
| `Makefile` | Cada receta llama a un entry point; `.DELETE_ON_ERROR` y la variable `RUN` |

## ❓ Preguntas tipo examen

**P:** ¿Cuáles son las tres partes de un entry point?
**R:** Grupo (qué tipo de cosa ofrece), nombre (cómo se llama dentro del grupo) y referencia
(`modulo:objeto`, dónde está).

**P:** ¿Qué diferencia hay entre `[project.scripts]` y `[project.entry-points."grupo"]`?
**R:** `[project.scripts]` es el grupo especial `console_scripts`: el instalador crea un ejecutable
por línea. Un grupo propio no crea ejecutables; solo deja el registro para que un programa lo
descubra con `importlib.metadata`.

**P:** ¿Dónde quedan escritos los entry points de un paquete instalado?
**R:** En `<paquete>-<versión>.dist-info/entry_points.txt`, dentro de `site-packages`.

**P:** ¿Qué hace el ejecutable que crea pip para un comando?
**R:** Importa la función de la referencia, la llama sin argumentos y usa lo que devuelve como
código de salida (`sys.exit(main())`). No contiene el código del paquete.

**P:** Instalaste el paquete y `act9-entrenar` dice "no se reconoce como comando". ¿Por qué?
**R:** Casi siempre porque el ambiente no está activado: la carpeta `Scripts` (o `bin`) del ambiente
no está en el `PATH`. Se arregla activándolo o con `python -m act9_pipeline`, `uv run`,
`poetry run` o `conda run`.

**P:** ¿Cómo descubre `act9-entrenar` un modelo que trae otro paquete?
**R:** Con `importlib.metadata.entry_points(group="act9_pipeline.modelos")`, que lee los
`entry_points.txt` de todos los paquetes instalados; luego `ep.load()` importa la función y la llama.

**P:** ¿Por qué ordenar los plugins por nombre al descubrirlos?
**R:** Para que el resultado no dependa del orden en que el sistema de archivos devuelve los
paquetes. En una búsqueda de hiperparámetros, el orden cambia qué combinaciones se prueban.

**P:** ¿Por qué el nombre del grupo debería empezar con el nombre de tu paquete?
**R:** Para no chocar con otros paquetes. Un grupo `modelos` lo podría usar cualquiera;
`act9_pipeline.modelos` es solo de este proyecto.

**P:** ¿Para qué sirve que `act9-evaluar` devuelva 1 cuando el modelo no pasa el umbral?
**R:** Es una compuerta de calidad: make, GitHub Actions o un orquestador ven el código distinto de
0 y detienen el pipeline sin tener que leer la salida.

**P:** ¿Qué relación hay entre un entry point y un Makefile?
**R:** El entry point define qué se ejecuta y el Makefile, cuándo y en qué orden. El Makefile llama a
los comandos, se detiene con sus códigos de salida y solo repite las etapas cuyas entradas cambiaron.

**P:** ¿Se pueden usar entry points con conda, uv o Poetry?
**R:** Sí. Son parte del estándar de empaquetado. En la Actividad 9 el mismo `pyproject.toml`
funcionó con pip, conda, uv y Poetry y dio los mismos resultados.

**P:** En la Actividad 9, ¿por qué instalar el plugin `knn` cambió el mejor `f1_macro` de 0.652 a 0.622?
**R:** `RandomizedSearchCV` reparte sus 60 combinaciones entre las familias descubiertas. Con una
familia más cambian las combinaciones que se prueban. Por eso en producción se fijan las familias.

**P:** Cambiaste el nombre de un comando en el `pyproject.toml` y el nombre viejo sigue funcionando. ¿Qué pasó?
**R:** No reinstalaste. Los ejecutables y `entry_points.txt` se escriben al instalar, así que hay que
correr de nuevo `pip install -e .`.

## 🏋️ Ejercicios

1. En `repaso.py`, agrega una cuarta familia (por ejemplo `SVC`) como **otro** plugin falso y
   verifica que `descubrir()` la encuentre sin cambiar la función.
2. Haz un plugin "roto" que devuelva una lista en vez de un diccionario. Agrega a `descubrir()` una
   validación del contrato y comprueba que se omite con un aviso sin detener a los demás.
3. Crea un paquete real mínimo con un comando `hola-mlops = "hola:main"` donde `main()` devuelva 3.
   Instálalo con `pip install -e .`, córrelo y revisa `$LASTEXITCODE` (PowerShell) o `echo $?`.
4. Agrega a `ejemplos/Makefile` un objetivo `reporte` que dependa de `metricas.json` y piensa qué
   pasa con él cuando `act9-evaluar` devuelve 1.
5. Busca en tu ambiente qué grupos de entry points existen además de `console_scripts`
   (`entry_points().groups`) y averigua de qué librería es cada uno.

## 🔗 Referencias

- Repo de la entrega: [Actividad-9-MLOPS](https://github.com/DiegoLinares11/Actividad-9-MLOPS).
- PyPA, [Entry points specification](https://packaging.python.org/en/latest/specifications/entry-points/).
- PyPA, [Creating and packaging command-line tools](https://packaging.python.org/en/latest/guides/creating-command-line-tools/).
- Python, [`importlib.metadata`](https://docs.python.org/3/library/importlib.metadata.html), sección *Entry points*.
- Setuptools, [Entry Points](https://setuptools.pypa.io/en/latest/userguide/entry_point.html).
- Temas relacionados del repo: [07 ambientes](../07-ambientes-virtuales/), [08 paquetes](../08-publicar-paquete/), [10 CI/CD](../10-cicd/).
