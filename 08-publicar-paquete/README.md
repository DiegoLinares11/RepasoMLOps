# 08 · Empaquetar y publicar una librería en TestPyPI

🎬 Video: [▶️ en español](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/08-publicar-paquete-es.mp4) · [▶️ in English](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/08-publicar-paquete-en.mp4) · [todos los videos](https://github.com/DiegoLinares11/RepasoMLOps/releases/tag/videos)

## 🧱 Conocimiento previo

### 1. Módulo, paquete y librería (repaso del tema 07)

- **Módulo**: un archivo `.py` (`data.py`).
- **Paquete**: una carpeta de módulos con `__init__.py` (`act3_pipeline/`). Se importa
  por el nombre de la carpeta: `import act3_pipeline`.
- **Distribución** (o "librería publicada"): el paquete **empaquetado** en un archivo
  que pip sabe instalar. Tiene su propio nombre, que se usa con pip:
  `pip install act3-pipeline-mlops`.

### 2. Qué significa realmente "instalar" un paquete

`pip install algo` hace tres cosas:

1. **Descarga** un archivo (normalmente un `.whl`) de un **índice** como PyPI.
2. **Copia** su contenido a la carpeta `site-packages` del Python activo.
3. Lee su **metadata** para instalar también sus dependencias y crear sus comandos de
   consola (por ejemplo `act3-demo.exe`).

Después de eso, `import act3_pipeline` funciona desde **cualquier carpeta**, porque
`site-packages` está en `sys.path`. Sin instalar, el import solo funciona si estás
parado justo en la carpeta del código.

### 3. Un índice de paquetes es una "tienda" con dirección web

- **PyPI** (<https://pypi.org>): la tienda oficial, la que usa pip por defecto.
- **TestPyPI** (<https://test.pypi.org>): una tienda **de práctica**, separada, para
  probar publicaciones sin ensuciar la oficial.

Cada uno tiene una dirección "simple" que es la que lee pip:
`https://pypi.org/simple/` y `https://test.pypi.org/simple/`.

### 4. Un `.zip` con otro nombre

Un wheel (`.whl`) es literalmente un archivo zip. Puedes cambiarle la extensión a
`.zip` y abrirlo con el Explorador de Windows. Lo comprobamos en el notebook.

### 5. Variables de entorno

Son pares `NOMBRE=valor` que viven en la sesión de la terminal y que cualquier programa
puede leer. Sirven para pasar configuración y **secretos** sin escribirlos en el código.

```powershell
$env:MI_VARIABLE = "hola"      # PowerShell: solo dura lo que dure esta ventana
echo $env:MI_VARIABLE
```

```bash
export MI_VARIABLE="hola"      # bash
echo $MI_VARIABLE
```

### 6. Token de API

Una "contraseña para programas": un texto largo (en PyPI empieza con `pypi-`) que
permite a una herramienta (twine) actuar **en tu nombre**. Quien lo tenga puede subir
versiones de tu paquete. Por eso se trata como una contraseña: nunca en el código,
nunca en el repo, nunca en una captura.

### 7. Versionado semántico (repaso del tema 07)

`MAYOR.MENOR.PARCHE`: parche para arreglos, menor para funciones nuevas compatibles,
mayor para cambios que rompen código ajeno.

## 🎯 Qué tienes que saber

### 1. Por qué empaquetar

**El problema real del curso.** En la Actividad 4, los dos Dockerfiles instalaban
nuestra librería copiando un archivo a mano dentro del repositorio:

```dockerfile
COPY libreria/act3_pipeline-0.1.0-py3-none-any.whl /tmp/
RUN pip install --no-cache-dir /tmp/act3_pipeline-0.1.0-py3-none-any.whl
```

Con el paquete publicado, eso se vuelve una dependencia normal como cualquier otra:

```dockerfile
RUN pip install act3-pipeline-mlops
```

**Analogía:** tener el código en una carpeta es como tener una receta escrita en tu
cuaderno; empaquetarlo es imprimirla con lista de ingredientes (dependencias), número de
edición (versión) e instrucciones de uso (comandos de consola); publicarla es ponerla en
una biblioteca pública donde cualquiera la pide por su nombre.

### 2. La estructura: disposición `src/`

```
mi-proyecto/
├── pyproject.toml       ← la ficha técnica (lo único obligatorio además del código)
├── README.md            ← descripción que se muestra en el índice
├── LICENSE              ← qué pueden hacer otros con tu código
└── src/
    └── act3_pipeline/   ← el paquete (nombre de IMPORT)
        ├── __init__.py
        ├── ...
        └── datasets/champions_league_matches.csv
```

**¿Por qué `src/`?** Si el paquete estuviera en la raíz, al correr pruebas desde ahí
Python importaría la **carpeta local** y no la versión **instalada**. Podrías olvidar
incluir el CSV en el paquete y no enterarte, porque localmente el archivo está. Con
`src/`, para importar estás obligado a instalar, así que pruebas lo mismo que recibirán
los demás. La estructura completa de la Tarea 4 está en
[`ejemplos/estructura.txt`](ejemplos/estructura.txt).

### 3. `pyproject.toml`, sección por sección

| Sección | Para qué | En la Tarea 4 |
|---|---|---|
| `[build-system]` | **Con qué** se construye: el backend y sus requisitos | `hatchling >= 1.26` |
| `[project]` | **Metadatos**: nombre, versión, autores, descripción, licencia, `requires-python` | `act3-pipeline-mlops`, `0.1.0`, MIT, `>=3.10` |
| `dependencies` | Qué instala pip junto con el paquete (con **rangos**) | `scikit-learn>=1.3`, `pandas>=2.0`, `numpy>=1.24`, `scipy>=1.10` |
| `[project.optional-dependencies]` | Extras opcionales: `pip install "paquete[dev]"` | `notebook`, `dev` |
| `[project.urls]` | Enlaces en la página del índice | repo de GitHub |
| `[project.scripts]` | **Comandos de consola** (entry points) | `act3-demo = "act3_pipeline.cli:main"` |
| `[tool.<backend>]` | Configuración propia del backend | `[tool.hatch.build.targets.wheel] packages = ["src/act3_pipeline"]` |

El archivo real comentado línea por línea: [`ejemplos/pyproject.toml`](ejemplos/pyproject.toml).

### 4. Frontend y backend de construcción

- **Frontend**: la herramienta que tú ejecutas: `python -m build` (o `pip wheel`, `uv build`).
- **Backend**: la librería que realmente arma los archivos: **hatchling** (Tarea 4),
  **setuptools** (Actividades 1 y 3), poetry-core, flit-core.

`python -m build` lee `[build-system]`, crea un ambiente aislado, instala ahí el
backend y le llama dos funciones estándar (PEP 517): `build_sdist` y `build_wheel`. Así
cualquier frontend funciona con cualquier backend.

| | setuptools (Act. 1 y 3) | hatchling (Tarea 4) |
|---|---|---|
| `build-backend` | `setuptools.build_meta` | `hatchling.build` |
| Incluir el CSV | **Hay que declararlo**: `[tool.setuptools.package-data] "act3_pipeline" = ["datasets/*.csv"]` | **Automático**: todo lo que está dentro de la carpeta del paquete |
| Nombre de distribución ≠ carpeta | `packages.find` busca carpetas con `__init__.py` | Hay que decir `packages = ["src/act3_pipeline"]` |
| Licencia | Forma vieja `license = { text = "MIT" }` | Forma nueva (PEP 639) `license = "MIT"` + `license-files` |
| `setup.py` | Tenían un *shim* de 3 líneas por compatibilidad | No hace falta |

Comparación lado a lado: [`ejemplos/pyproject-setuptools.toml`](ejemplos/pyproject-setuptools.toml).

### 5. Datos dentro del paquete (`package-data`) y cómo leerlos

El dataset viaja **dentro** del paquete para que `cargar_datos()` funcione en cualquier
compu sin descargar nada. Dos reglas:

1. **Que entre al wheel.** En setuptools se declara con `package-data`; en hatchling
   entra solo. Se verifica abriendo el wheel (en la Tarea 4 lo hicimos y aparecía
   `act3_pipeline/datasets/champions_league_matches.csv`).
2. **Leerlo sin rutas fijas.** Nunca `pd.read_csv("C:/Users/dlinares/.../datos.csv")`:
   en otra compu esa ruta no existe. Se usa `importlib.resources`, que encuentra el
   archivo dentro del paquete instalado, esté donde esté:

```python
from importlib import resources
with resources.files("act3_pipeline.datasets").joinpath("champions_league_matches.csv").open() as fh:
    df = pd.read_csv(fh)
```

### 6. Comandos de consola (entry points)

```toml
[project.scripts]
act3-demo = "act3_pipeline.cli:main"
```

Se lee: "crea un comando llamado `act3-demo` que importe `act3_pipeline.cli` y llame a
`main()`". Al instalar, pip genera `act3-demo.exe` en `.venv\Scripts\` (en Linux/macOS,
`.venv/bin/act3-demo`) y lo anota en `dist-info/entry_points.txt`. El valor que
devuelve `main()` es el código de salida (0 = todo bien). Si el comando no queda en el
PATH, siempre funciona `python -m act3_pipeline.cli`.

### 7. Dependencias de una librería: rangos, no versiones exactas

| | Librería (lo que publicas) | Aplicación (lo que despliegas) |
|---|---|---|
| Ejemplo del curso | `pyproject.toml` de la Tarea 4 | `requirements.txt` de los Dockerfiles de la Act. 4 |
| Cómo se fija | Rangos: `scikit-learn>=1.3` | Exacto: `scikit-learn==1.8.0` |
| Por qué | Se instala junto a otras librerías; si exige `==1.8.0` choca con quien necesite 1.7 | Debe dar **siempre** lo mismo y poder cargar el modelo serializado |

Como resumió el PDF de la Tarea 4: *las versiones exactas se fijan en la aplicación, no
en la librería*. `dependencies` **no es** un `requirements.txt`.

### 8. sdist vs wheel

| | **sdist** (`.tar.gz`) | **wheel** (`.whl`) |
|---|---|---|
| Qué es | El **código fuente** + `pyproject.toml` | El paquete **ya construido**, listo para copiar |
| Al instalar | pip tiene que **construirlo** (y compilar si hay C) | pip solo **descomprime y copia** |
| Velocidad | Lenta | Rápida |
| Trae `src/`, `pyproject.toml` | Sí | No (ya no hacen falta) |
| En la Tarea 4 | `act3_pipeline_mlops-0.1.0.tar.gz`, 20 KB | `act3_pipeline_mlops-0.1.0-py3-none-any.whl`, 24 KB |

Se suben **los dos**: pip prefiere el wheel y usa el sdist si no hay wheel compatible.

**El nombre del wheel** se lee `distribución-versión-python-abi-plataforma.whl`:

- `act3_pipeline_mlops-0.1.0-py3-none-any.whl` → cualquier Python 3, sin binarios,
  cualquier sistema operativo (Python puro).
- `numpy-2.4.1-cp312-cp312-win_amd64.whl` → solo CPython 3.12 en Windows de 64 bits
  (trae código C compilado).

### 9. Construir, validar, subir

```powershell
python -m pip install build twine        # una vez
python -m build                          # genera dist/*.tar.gz y dist/*.whl
python -m twine check dist/*             # valida README, licencia, clasificadores
python -m twine upload --repository testpypi dist/*    # sube a TestPyPI
```

Los comandos son iguales en bash (cambia `python` por `python3` si hace falta). En la
Tarea 4 los tres pasos se automatizaron en
[`ejemplos/subir_a_testpypi.ps1`](ejemplos/subir_a_testpypi.ps1) (comentado línea por
línea) y aquí está su gemelo en bash: [`ejemplos/subir_a_testpypi.sh`](ejemplos/subir_a_testpypi.sh).

**Una versión subida no se puede reemplazar.** Si subiste `0.1.0` con un error, subes
`0.1.1`. Aunque borres la `0.1.0`, ese número queda usado para siempre. Por eso el
script borra `dist/` antes de construir: si quedara un wheel viejo, `twine upload
dist/*` intentaría subirlo otra vez y fallaría.

### 10. TestPyPI vs PyPI

| | TestPyPI | PyPI |
|---|---|---|
| Para qué | Practicar y probar el proceso | Publicar de verdad |
| Dirección para pip | `https://test.pypi.org/simple/` | `https://pypi.org/simple/` (por defecto) |
| Cuenta y tokens | **Separados** de PyPI | Separados de TestPyPI |
| Tiene scikit-learn, pandas... | **No** (solo lo que la gente sube a practicar) | Sí |
| Se borra | Puede limpiarse de vez en cuando | Permanente |
| `twine upload` | `--repository testpypi` | sin opción (por defecto) |

### 11. El token: nunca en el repo

1. En TestPyPI: *Account settings → API tokens → Add API token*. Puede tener alcance de
   **toda la cuenta** o de **un solo proyecto** (mejor, una vez que el proyecto existe).
   Se muestra **una sola vez**.
2. Se guarda en un archivo `.env` que está en el `.gitignore`:

   ```
   TWINE_USERNAME=__token__
   TWINE_PASSWORD=pypi-TU_TOKEN_AQUI
   ```

   El usuario es literalmente `__token__`: así PyPI sabe que la contraseña es un token.
3. Al repo se sube solo la **plantilla** [`ejemplos/.env.example`](ejemplos/.env.example),
   sin el valor real. El `.gitignore` de la Tarea 4 lo logra con `.env`, `.env.*` y la
   excepción `!.env.example`.
4. El script carga el `.env` como variables de entorno **del proceso** y twine las lee
   solo. Así el token **no aparece en la terminal ni en el historial** de comandos.

Alternativas que conviene conocer: un archivo `%USERPROFILE%\.pypirc` (en Linux
`~/.pypirc`) con el token, fuera del repo; y en CI, **Trusted Publishing** (PyPI confía
en GitHub Actions sin ningún token guardado, tema 10).

Si un token se filtra (lo subiste a GitHub, salió en un video): **revócalo de inmediato**
en la página de tokens y genera otro. Borrarlo del repo no basta: queda en el historial de Git.

### 12. Instalar desde TestPyPI: el error más común

```powershell
pip install --index-url https://test.pypi.org/simple/ act3-pipeline-mlops      # ❌ FALLA
```

Falla porque TestPyPI es un índice **separado** que **no tiene** scikit-learn ni
pandas: pip encuentra nuestro paquete pero no puede resolver sus dependencias. La forma
correcta:

```powershell
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ act3-pipeline-mlops
```

```bash
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            act3-pipeline-mlops
```

(En PowerShell el salto de línea se hace con un acento grave `` ` `` al final, no con `\`.)

- `--index-url`: el índice **principal** (reemplaza a PyPI).
- `--extra-index-url`: un índice **adicional** donde también buscar.

**Ojo de seguridad:** pip trata los dos índices como uno solo y elige la versión **más
alta** entre ambos. Si alguien subiera a PyPI un paquete con tu mismo nombre y versión
mayor, pip instalaría el de esa persona ("confusión de dependencias"). Para practicar
está bien; en una empresa se usa un índice privado que hace de proxy.

### 13. Nombre de distribución ≠ nombre de import

| | Distribución | Import |
|---|---|---|
| Se usa en | `pip install`, `pip show`, `importlib.metadata.version(...)` | `import ...` |
| Tarea 4 | `act3-pipeline-mlops` | `act3_pipeline` |
| scikit-learn | `scikit-learn` | `sklearn` |
| Paquete mínimo del notebook | `mini-champions-uvg` | `mini_champions` |

Además los nombres de distribución se **normalizan**: `Act3_Pipeline.MLOps`,
`act3__pipeline--mlops` y `act3-pipeline-mlops` son el mismo proyecto para PyPI (todo a
minúsculas, `_` `.` `-` → `-`). Por eso los archivos se llaman `act3_pipeline_mlops-...`
con guiones bajos.

### 14. La licencia

Sin licencia, legalmente **nadie** puede usar tu código aunque esté público. La Tarea 4
usa **MIT**: cualquiera puede usar, copiar, modificar y vender el código siempre que
conserve el aviso de copyright, y sin garantía.

| Licencia | Resumen | Típica en |
|---|---|---|
| MIT | Haz lo que quieras, conserva el aviso | Librerías pequeñas, cursos (Tarea 4) |
| BSD-3-Clause | Como MIT + no usar el nombre del autor para promocionar | scikit-learn, numpy, pandas |
| Apache-2.0 | Como MIT + protección de patentes | Proyectos de empresa |
| GPL-3.0 | Si distribuyes algo derivado, también debe ser GPL | Software libre "copyleft" |

### 15. Código, modelo y ambiente: tres cosas distintas

La pregunta de la Tarea 4 era qué conviene más: Docker, pickles o paquetes. La
conclusión del equipo: **no compiten, empaquetan cosas distintas**.

| Herramienta | Qué empaqueta | Dónde la usamos |
|---|---|---|
| Paquete (wheel) | El **código** y sus dependencias declaradas | Actividad 1, y hoy en TestPyPI |
| Pickle / joblib | El **modelo entrenado** (los parámetros aprendidos) | `modelo.joblib` de la Actividad 4 |
| Docker | El **ambiente completo**: sistema operativo, intérprete, librerías y código | Las tres imágenes de la Actividad 4 |

Y se usan **apilados**: el código se publica como paquete → el paquete se instala
dentro de la imagen → el modelo vive **fuera** de la imagen (volumen o registro de
modelos), porque es estado y no código.

**Por qué el pickle es el eslabón peligroso:** un pickle **no guarda el código** de sus
clases, guarda la **ruta para importarlas**. El pipeline tiene dos transformadores
propios (`PorcentajeATexto`, `RatioATexto`); al cargar `modelo.joblib`, Python los busca
en `act3_pipeline`. Si el paquete no está instalado (o es otra versión), el archivo es
inservible. Además `pickle` ejecuta código al deserializar: cargar uno de origen
desconocido es un riesgo de seguridad.

## 📂 Qué hicimos en el curso

### Actividad 6 (empaquetado y publicación)

No hay repositorio propio de la Actividad 6: es la parte de empaquetado y publicación
que cubre este mismo video, y se concreta en la Tarea 4. El empaquetado ya venía de
antes: en las **Actividades 1 y 3** el pipeline se empaquetó con **setuptools**
(`act1-pipeline`, `act3-pipeline`), con `package-data` para el CSV y el comando
`act3-demo`, y se instalaba con `pip install .`. El wheel de la Act. 3
(`act3_pipeline-0.1.0-py3-none-any.whl`) es el que la Actividad 4 copiaba a mano en
`libreria/`.

### Tarea 4: publicación en TestPyPI ([Tarea4-MLOPS](https://github.com/DiegoLinares11/Tarea4-MLOPS), PDF `Tarea4_MLOPS.pdf`)

Diego Linares, Andy Fuentes, Christian Echeverria y Diederich Solis, 1 de septiembre de
2026. Paquete publicado: <https://test.pypi.org/project/act3-pipeline-mlops/>.

**Pasos:**

1. **Qué publicar.** La primera idea fue publicar la Actividad 4, pero es una
   aplicación dockerizada: **PyPI distribuye paquetes de Python; las imágenes van a un
   registro como Docker Hub**. Lo publicable era la librería que vive dentro de esas
   imágenes: `act3_pipeline`.
2. **Estructura** según el tutorial oficial de la PyPA: disposición `src/` y toda la
   configuración en un solo `pyproject.toml`, sin `setup.py` ni `setup.cfg`, con
   **hatchling** como backend.
3. **Tres detalles que costaron:**
   - El nombre de distribución (`act3-pipeline-mlops`) no es el de import
     (`act3_pipeline`), así que hubo que declarar `[tool.hatch.build.targets.wheel]`.
   - El nombre debe ser único en el índice: se le agregó `-mlops`.
   - `dependencies` no es `requirements.txt`: van rangos `>=`.
4. **Construcción** con `python -m build`: wheel de **24 KB** y sdist de **20 KB**. Se
   abrió el wheel para verificar que traía `datasets/champions_league_matches.csv`,
   `entry_points.txt` (el comando `act3-demo`) y `licenses/LICENSE`.
5. **Validación** con `python -m twine check dist/*`: los dos archivos pasaron.
6. **Publicación** con `twine upload --repository testpypi`, con el token en `.env`
   (excluido por `.gitignore`) cargado por `subir_a_testpypi.ps1`.
7. **Verificación instalando en limpio.** El primer intento, solo con `--index-url`
   de TestPyPI, **falló** por las dependencias científicas; con `--extra-index-url`
   de PyPI funcionó. El paquete instalado reportó: distribución 0.1.0, import
   `act3_pipeline` 0.1.0, dataset incluido **115 entrenamiento / 29 prueba**, pipeline
   `['preprocesamiento', 'seleccion', 'modelo']`, y `act3-demo --busqueda aleatoria`
   dio **accuracy=0.690, f1_macro=0.631**.

La metadata real que quedó dentro del wheel (`dist-info/METADATA`, recortada):

```
Metadata-Version: 2.5
Name: act3-pipeline-mlops
Version: 0.1.0
Author-email: Diego Linares <lin221256@uvg.edu.gt>
License-Expression: MIT
Requires-Python: >=3.10
Requires-Dist: numpy>=1.24
Requires-Dist: pandas>=2.0
Requires-Dist: scikit-learn>=1.3
Requires-Dist: scipy>=1.10
Provides-Extra: dev
Requires-Dist: pytest>=7; extra == 'dev'
```

**Reflexión del PDF (resumen):**

- Paquete, pickle y Docker **no compiten**: empaquetan código, modelo y ambiente.
- Se usan en capas: código como paquete → instalado en la imagen → modelo fuera, en un
  volumen o registro de modelos. No hornear el modelo en la imagen fue decisión propia
  en la Actividad 4: reentrenar habría obligado a reconstruir la imagen.
- El pickle es el eslabón peligroso (guarda rutas de import, no código; ejecuta código
  al cargar; está atado a la versión de la librería). Por eso las dos imágenes de la
  Act. 4 instalan el mismo paquete con las mismas versiones exactas.
- Recomendación: código reutilizable → **paquete**; reproducir un experimento o servir
  un modelo → **Docker**; modelo entrenado → **registro de modelos** (como MLflow en
  Databricks, tema 11), no el repo ni la imagen.
- Idea final: *empaquetar el código es fácil y ya está resuelto; lo difícil de un
  proyecto de ML es empaquetar el modelo y los datos, que cambian solos y que ninguna de
  estas tres herramientas versiona bien por sí sola.*

## 🧪 Práctica

**`repaso.ipynb`** (ya ejecutado; generado desde `repaso.py`). Sin internet:

1. Muestra la estructura `src/` y el `pyproject.toml` de
   [`ejemplos/paquete-minimo/`](ejemplos/paquete-minimo/) (`mini-champions-uvg`).
2. Construye el sdist y el wheel llamando a las funciones PEP 517 del backend (lo mismo
   que hace `python -m build`): salen de 3.8 KB y 4.7 KB.
3. Descompone nombres de wheels reales (`py3-none-any` vs `cp312-cp312-win_amd64`).
4. Abre el wheel como zip: el CSV y `entry_points.txt` están adentro, `src/` no.
5. Abre el sdist: ahí sí están `src/` y `pyproject.toml`.
6. Instala el wheel en un venv limpio con `--no-index` y ejecuta el comando
   `mini-champions` (8 partidos: 3 Away Win, 3 Draw, 2 Home Win).
7. Demuestra nombre de distribución vs import con `importlib.metadata`.
8. Normaliza nombres y ordena versiones con `packaging` (como pip).

Si tu ambiente no tiene `setuptools` (Python 3.12+ no lo trae en los venv), el
notebook usa `pip wheel`, que lo descarga: en ese caso necesita internet. Para
regenerarlo:

```powershell
python tools/build_nb.py 08-publicar-paquete/repaso.py
```

**`ejemplos/`**:

| Archivo | Qué es |
|---|---|
| [`pyproject.toml`](ejemplos/pyproject.toml) | El real de la Tarea 4 (hatchling), comentado línea por línea |
| [`pyproject-setuptools.toml`](ejemplos/pyproject-setuptools.toml) | El real de la Actividad 3 (setuptools), para comparar |
| [`subir_a_testpypi.ps1`](ejemplos/subir_a_testpypi.ps1) | El script real de la Tarea 4, comentado |
| [`subir_a_testpypi.sh`](ejemplos/subir_a_testpypi.sh) | El mismo flujo en bash |
| [`.env.example`](ejemplos/.env.example) | Plantilla del archivo del token |
| [`estructura.txt`](ejemplos/estructura.txt) | Árbol del proyecto y contenido del wheel |
| [`paquete-minimo/`](ejemplos/paquete-minimo/) | Paquete completo y funcional para practicar |

**[`ejercicios.md`](ejercicios.md)**: publicar tu propio paquete en TestPyPI paso a paso.

## ❓ Preguntas tipo examen

**P:** ¿Qué diferencia hay entre el nombre de distribución y el nombre de import? Da el ejemplo de la Tarea 4.
**R:** El de distribución se usa con pip y en el índice (`pip install act3-pipeline-mlops`); el de import es el nombre de la carpeta del paquete (`import act3_pipeline`). No tienen que coincidir; cuando no coinciden, en hatchling hay que indicar dónde está el paquete con `[tool.hatch.build.targets.wheel] packages = ["src/act3_pipeline"]`.

**P:** ¿Qué es un wheel y qué es un sdist?
**R:** El wheel (`.whl`) es el paquete ya construido, un zip que pip solo descomprime y copia a `site-packages`. El sdist (`.tar.gz`) es el código fuente con su `pyproject.toml`, que pip tiene que construir antes de instalar. Se publican ambos y pip prefiere el wheel.

**P:** ¿Qué significa `py3-none-any` en el nombre de un wheel?
**R:** Que sirve para cualquier Python 3, no depende de una ABI binaria y corre en cualquier plataforma: es Python puro. Un wheel con código C lleva algo como `cp312-cp312-win_amd64`.

**P:** ¿Para qué sirve `[build-system]` en `pyproject.toml`?
**R:** Declara qué backend construye el paquete (`build-backend`) y qué hay que instalar para usarlo (`requires`). `python -m build` lo lee, instala el backend en un ambiente aislado y le pide el sdist y el wheel.

**P:** ¿Por qué `pip install --index-url https://test.pypi.org/simple/ act3-pipeline-mlops` falla?
**R:** Porque TestPyPI es un índice separado que no tiene scikit-learn, pandas, numpy ni scipy, así que pip no puede resolver las dependencias. Hay que agregar `--extra-index-url https://pypi.org/simple/`.

**P:** ¿Por qué las dependencias de una librería van con `>=` y no con `==`?
**R:** Porque la librería se instala junto a otras que también tienen requisitos; si fijara versiones exactas, chocaría con cualquier proyecto que necesite otra versión. Las versiones exactas se fijan en la aplicación que se despliega (como los `requirements.txt` de la Actividad 4).

**P:** ¿Cómo se maneja el token de TestPyPI de forma segura?
**R:** En un archivo `.env` excluido por `.gitignore` (con `TWINE_USERNAME=__token__` y `TWINE_PASSWORD=pypi-...`), cargado como variables de entorno del proceso para que twine lo lea solo. Nunca en un comando, en el historial ni en el repo; al repo va solo `.env.example`. Si se filtra, se revoca.

**P:** ¿Qué hace `[project.scripts] act3-demo = "act3_pipeline.cli:main"`?
**R:** Al instalar, pip crea un ejecutable `act3-demo` que importa `act3_pipeline.cli` y llama a `main()`; su valor de retorno es el código de salida. Queda registrado en `entry_points.txt`.

**P:** ¿Cómo te aseguras de que el CSV viaje dentro del paquete y cómo lo lees?
**R:** En setuptools con `[tool.setuptools.package-data] "act3_pipeline" = ["datasets/*.csv"]`; en hatchling entra solo si está dentro de la carpeta del paquete. Se verifica abriendo el wheel. Se lee con `importlib.resources.files(...)`, nunca con una ruta absoluta.

**P:** Subiste la versión 0.1.0 con un error. ¿Puedes volver a subir 0.1.0 corregida?
**R:** No. PyPI y TestPyPI no permiten reemplazar una versión, ni siquiera después de borrarla. Hay que subir 0.1.1 (parche).

**P:** ¿Qué hace `twine check` y por qué correrlo antes de subir?
**R:** Valida que la metadata esté bien formada: que el README se pueda mostrar como descripción, la licencia, los clasificadores. Así fallas antes de subir y no a medias.

**P:** ¿Por qué no se puede publicar la Actividad 4 en PyPI?
**R:** Porque es una aplicación dockerizada: PyPI distribuye paquetes de Python y las imágenes de contenedor van a un registro de imágenes como Docker Hub. Lo publicable era la librería `act3_pipeline` que esas imágenes instalan.

**P:** ¿Por qué la disposición `src/`?
**R:** Para que las pruebas usen el paquete instalado y no la carpeta local. Si olvidas incluir un archivo (como el CSV), lo descubres tú y no el usuario.

**P:** ¿Por qué el pickle es "el eslabón peligroso" según la Tarea 4?
**R:** Porque no guarda el código de las clases sino la ruta para importarlas: sin el paquete `act3_pipeline` (con `PorcentajeATexto` y `RatioATexto`) el `modelo.joblib` no se puede cargar. Además ejecuta código al deserializar y está atado a la versión de la librería.

## 🏋️ Ejercicios

Detallados en [`ejercicios.md`](ejercicios.md). Resumen:

1. **Construye y abre** el `paquete-minimo` con `python -m build` y revisa el wheel
   como zip.
2. **Rompe el CSV a propósito**: quita `package-data`, reconstruye, instala y mira el
   error.
3. **Publica tu paquete** en TestPyPI con tu propio nombre único y un token en `.env`.
4. **Instala en limpio** desde TestPyPI (primero sin `--extra-index-url`, para ver el
   error, luego con).
5. **Sube una versión 0.1.1** con un cambio y comprueba que `pip install --upgrade` la toma.

## 🔗 Referencias

- Tutorial oficial *Packaging Python projects*: <https://packaging.python.org/en/latest/tutorials/packaging-projects/>
- *Using TestPyPI*: <https://packaging.python.org/en/latest/guides/using-testpypi/>
- *Writing your pyproject.toml*: <https://packaging.python.org/en/latest/guides/writing-pyproject-toml/>
- Disposición src vs plana: <https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/>
- Formato de nombres de wheels: <https://packaging.python.org/en/latest/specifications/binary-distribution-format/>
- Hatch / hatchling: <https://hatch.pypa.io/latest/config/build/>
- setuptools con pyproject: <https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html>
- twine: <https://twine.readthedocs.io/>
- Versionado semántico: <https://semver.org/lang/es/>
- Elegir licencia: <https://choosealicense.com/>
- `pickle` (advertencia de seguridad): <https://docs.python.org/3/library/pickle.html>
- Repos: [Tarea4-MLOPS](https://github.com/DiegoLinares11/Tarea4-MLOPS), [Actividad3-MLOPS](https://github.com/DiegoLinares11/Actividad3-MLOPS), [Actividad1-MLOPS](https://github.com/DiegoLinares11/Actividad1-MLOPS), [Actividad4-MLOPS](https://github.com/DiegoLinares11/Actividad4-MLOPS)
