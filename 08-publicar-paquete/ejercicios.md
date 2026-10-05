# 08 · Ejercicios en tu compu: empaquetar y publicar

Trabaja sobre una **copia** de [`ejemplos/paquete-minimo/`](ejemplos/paquete-minimo/)
fuera del repo, dentro de un ambiente virtual (tema 07). Los ejercicios 3 a 5 necesitan
internet y una cuenta en <https://test.pypi.org>.

```powershell
Copy-Item -Recurse RepasoMLOps\08-publicar-paquete\ejemplos\paquete-minimo C:\Users\dlinares\Documents\mi-paquete
cd C:\Users\dlinares\Documents\mi-paquete
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip build twine
```

```bash
cp -r RepasoMLOps/08-publicar-paquete/ejemplos/paquete-minimo ~/mi-paquete && cd ~/mi-paquete
python3 -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip build twine
```

---

## Ejercicio 1 · Construye y abre el wheel

```powershell
python -m build
Get-ChildItem dist
# Un wheel es un zip: cópialo con extensión .zip y ábrelo
Copy-Item dist\mini_champions_uvg-0.1.0-py3-none-any.whl revisar.zip
Expand-Archive revisar.zip -DestinationPath revisar -Force
Get-ChildItem revisar -Recurse | Select-Object FullName
Get-Content revisar\mini_champions_uvg-0.1.0.dist-info\entry_points.txt
```

```bash
python -m build
ls dist
python -m zipfile -l dist/mini_champions_uvg-0.1.0-py3-none-any.whl
unzip -p dist/*.whl '*entry_points.txt'
tar tzf dist/mini_champions_uvg-0.1.0.tar.gz
```

**Preguntas:** ¿Está `src/` dentro del wheel? ¿Y dentro del sdist? ¿Dónde quedó el CSV?
¿Qué dice la línea `Requires-Python` del `METADATA`?

---

## Ejercicio 2 · Rompe el CSV a propósito

1. En `pyproject.toml`, comenta las dos líneas de `[tool.setuptools.package-data]`.
2. Reconstruye e instala **en un venv limpio**:

   ```powershell
   Remove-Item dist -Recurse -Force; python -m build
   py -3.12 -m venv C:\temp\venv-prueba
   C:\temp\venv-prueba\Scripts\python.exe -m pip install (Get-Item dist\*.whl).FullName
   C:\temp\venv-prueba\Scripts\mini-champions.exe
   ```

   ```bash
   rm -rf dist && python -m build
   python3 -m venv /tmp/venv-prueba
   /tmp/venv-prueba/bin/python -m pip install dist/*.whl
   /tmp/venv-prueba/bin/mini-champions
   ```

3. **Preguntas:** ¿Qué error sale? ¿Por qué **no** lo verías si instalaras en modo
   editable (`pip install -e .`), o si el paquete estuviera en la raíz del proyecto y
   ejecutaras desde ahí? (Pista: en los dos casos Python lee la carpeta de tu código,
   donde el CSV sí existe; por eso existe la disposición `src/` y por eso se prueba en
   un venv limpio.) Vuelve a activar `package-data` y repite: ahora debe funcionar.

**Variante:** cambia el backend a hatchling (`requires = ["hatchling >= 1.26"]`,
`build-backend = "hatchling.build"`, borra las secciones `[tool.setuptools...]` y agrega
`[tool.hatch.build.targets.wheel] packages = ["src/mini_champions"]`). ¿Entra el CSV
sin declararlo?

---

## Ejercicio 3 · Publica TU paquete en TestPyPI

1. **Nombre único.** Cambia en `pyproject.toml` `name = "mini-champions-uvg"` por algo
   como `"mini-champions-dlinares"`. Busca en <https://test.pypi.org> que no exista.
   Cambia también `authors`.
2. **Cuenta y token.** Crea la cuenta en TestPyPI (verifica el correo y activa 2FA, es
   obligatorio para subir). En *Account settings → API tokens* crea un token con alcance
   "Entire account" (la primera vez el proyecto todavía no existe). Cópialo: se muestra
   una sola vez.
3. **`.env` y `.gitignore`.** Copia [`ejemplos/.env.example`](ejemplos/.env.example) a
   `.env`, pega el token y asegúrate de que `.env` esté en el `.gitignore` **antes** de
   cualquier `git add`:

   ```powershell
   Copy-Item ..\RepasoMLOps\08-publicar-paquete\ejemplos\.env.example .env
   notepad .env
   Add-Content .gitignore ".env"
   ```

4. **Sube** con el script de la Tarea 4: copia
   [`ejemplos/subir_a_testpypi.ps1`](ejemplos/subir_a_testpypi.ps1) a la carpeta y
   cambia el nombre del proyecto en sus dos últimas líneas.

   ```powershell
   .\subir_a_testpypi.ps1
   ```

   ```bash
   bash subir_a_testpypi.sh
   ```

5. **Comprueba** la página `https://test.pypi.org/project/<tu-nombre>/`: ¿aparece el
   README como descripción? ¿La licencia MIT?

6. **Seguridad:** una vez que el proyecto existe, borra el token de "toda la cuenta" y
   crea uno con alcance **solo de ese proyecto**. Actualiza el `.env`.

---

## Ejercicio 4 · Instala en limpio desde TestPyPI

En un venv **nuevo**, sin la carpeta del proyecto cerca:

```powershell
py -3.12 -m venv C:\temp\venv-limpio
C:\temp\venv-limpio\Scripts\Activate.ps1
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ mini-champions-dlinares
mini-champions
python -c "from importlib.metadata import version; import mini_champions; print(version('mini-champions-dlinares'), mini_champions.__file__)"
```

Ahora prueba con el paquete **real** de la Tarea 4. Primero el intento que falla:

```powershell
pip install --index-url https://test.pypi.org/simple/ act3-pipeline-mlops
```

Y luego el correcto:

```powershell
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ act3-pipeline-mlops
act3-demo --busqueda aleatoria
```

**Preguntas:** ¿Qué mensaje de error da el primer intento? ¿Te salió accuracy=0.690 y
f1_macro=0.631 como en la Tarea 4? Si no, compara tu versión de scikit-learn
(`pip show scikit-learn`) con la 1.8.0 de la Actividad 4: ¿qué te dice eso sobre los
rangos `>=` de una librería?

---

## Ejercicio 5 · Publica la versión 0.1.1

1. Haz un cambio pequeño (por ejemplo, que `mini-champions` imprima también el total de
   empates).
2. Intenta subir **sin** cambiar la versión: ¿qué responde TestPyPI?
3. Sube `version = "0.1.1"` en `pyproject.toml` **y** `__version__ = "0.1.1"` en
   `__init__.py`, reconstruye y sube.
4. En el venv limpio: `pip install --upgrade --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ mini-champions-dlinares`
   y comprueba la versión.

**Reto:** ¿qué cambio harías en el código para que `__version__` se lea de la metadata
instalada (`importlib.metadata.version(...)`) y no tengas que escribir la versión en dos
lugares?

---

## Ejercicio bonus · Instálalo en un Dockerfile

Escribe un Dockerfile de 4 líneas (tema 09) que parta de `python:3.12-slim`, instale tu
paquete desde TestPyPI con `--extra-index-url` y ejecute `mini-champions` como `CMD`.
Es exactamente el cambio que la Tarea 4 proponía para la Actividad 4: reemplazar el
`COPY libreria/*.whl` por un `pip install` normal.
