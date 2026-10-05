# 07 · Ejercicios en tu compu: ambientes virtuales

Hazlos en una carpeta de prueba fuera del repo, por ejemplo
`C:\Users\dlinares\Documents\pruebas-venv`. Cada ejercicio trae los comandos en
**PowerShell** y, cuando cambian, en **bash**. Necesitas internet para instalar paquetes.

Antes de empezar, si nunca activaste un venv en PowerShell:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
py --list          # qué versiones de Python tienes instaladas
```

---

## Ejercicio 1 · Dos proyectos, dos versiones de scikit-learn

**Objetivo:** comprobar que dos versiones de la misma librería conviven en la misma compu.

```powershell
mkdir proyA, proyB
cd proyA
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install "scikit-learn==1.5.2"
cd ..\proyB
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install "scikit-learn==1.8.0"
cd ..
proyA\.venv\Scripts\python.exe -c "import sklearn; print('A', sklearn.__version__, sklearn.__file__)"
proyB\.venv\Scripts\python.exe -c "import sklearn; print('B', sklearn.__version__, sklearn.__file__)"
```

```bash
mkdir proyA proyB
python3 -m venv proyA/.venv && proyA/.venv/bin/python -m pip install "scikit-learn==1.5.2"
python3 -m venv proyB/.venv && proyB/.venv/bin/python -m pip install "scikit-learn==1.8.0"
proyA/.venv/bin/python -c "import sklearn; print('A', sklearn.__version__, sklearn.__file__)"
proyB/.venv/bin/python -c "import sklearn; print('B', sklearn.__version__, sklearn.__file__)"
```

**Preguntas:** ¿Desde qué carpeta se importa sklearn en cada caso? ¿Qué pasa si ejecutas
lo mismo con el Python global (`py -c "import sklearn"`)? Si `scikit-learn==1.5.2` no
tiene wheel para tu versión de Python, elige otra versión vieja con
`pip index versions scikit-learn`.

---

## Ejercicio 2 · Detective del PATH

**Objetivo:** ver con tus ojos que activar solo cambia el PATH.

```powershell
cd proyA
Get-Command python | Select-Object Source        # antes de activar
($env:PATH -split ';')[0..2]                      # primeras 3 carpetas del PATH
.venv\Scripts\Activate.ps1
Get-Command python | Select-Object Source        # después
($env:PATH -split ';')[0..2]
$env:VIRTUAL_ENV
python -c "import sys; print(sys.prefix, sys.base_prefix)"
deactivate
($env:PATH -split ';')[0..2]                      # volvió a la normalidad
```

```bash
cd proyA
which python3; echo "$PATH" | tr ':' '\n' | head -3
source .venv/bin/activate
which python;  echo "$PATH" | tr ':' '\n' | head -3; echo "$VIRTUAL_ENV"
python -c "import sys; print(sys.prefix, sys.base_prefix)"
deactivate
```

**Reto extra:** abre `.venv\Scripts\Activate.ps1` en el bloc de notas y busca la línea
`$Env:PATH = ...`. Luego abre una **segunda** ventana de PowerShell: ¿está activado ahí?
¿Por qué no?

---

## Ejercicio 3 · De intención a foto

**Objetivo:** contar cuántas dependencias transitivas trae un `requirements.txt` pequeño.

1. Crea `requirements.txt` con solo tres líneas:

   ```
   pandas>=2.0
   scikit-learn>=1.3
   joblib
   ```

2. Instala y congela:

   ```powershell
   py -3.12 -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   .venv\Scripts\python.exe -m pip freeze | Out-File -Encoding utf8 requirements-lock.txt
   (Get-Content requirements-lock.txt).Count
   ```

   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   .venv/bin/python -m pip freeze > requirements-lock.txt
   wc -l requirements-lock.txt
   ```

3. **Preguntas:** ¿Cuántas líneas tiene el lock? ¿Cuáles nunca las pediste? Usa
   `python -m pip show pandas` y mira la línea `Requires:` para saber quién trajo a quién.

---

## Ejercicio 4 · Reproduce en limpio

**Objetivo:** demostrar que el lock recrea exactamente el mismo ambiente.

```powershell
Remove-Item .venv -Recurse -Force
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe -m pip freeze | Out-File -Encoding utf8 lock2.txt
Compare-Object (Get-Content requirements-lock.txt) (Get-Content lock2.txt)   # vacío = idénticos
```

```bash
rm -rf .venv && python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip freeze > lock2.txt
diff requirements-lock.txt lock2.txt && echo "idénticos"
```

**Reto:** usa el script [`ejemplos/setup_entorno.ps1`](ejemplos/setup_entorno.ps1)
(cópialo a la carpeta) con `.\setup_entorno.ps1 -Recrear` y comprueba que hace lo mismo.

---

## Ejercicio 5 · Lo mismo con uv

**Objetivo:** ver cómo una herramienta moderna separa intención (`pyproject.toml`) y foto (`uv.lock`).

```powershell
# Instalar uv (una vez)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv init repaso-uv
cd repaso-uv
uv add pandas scikit-learn joblib
Get-Content pyproject.toml          # rangos
Get-Content .python-version         # versión exacta de Python
Select-String -Path uv.lock -Pattern '^name = ' | Measure-Object   # cuántos paquetes fijados
Remove-Item .venv -Recurse -Force
uv sync                             # recrea .venv idéntico desde uv.lock
uv run python -c "import sklearn; print(sklearn.__version__)"
```

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv init repaso-uv && cd repaso-uv
uv add pandas scikit-learn joblib
cat pyproject.toml .python-version
grep -c '^name = ' uv.lock
rm -rf .venv && uv sync
uv run python -c "import sklearn; print(sklearn.__version__)"
```

**Preguntas:** ¿Qué archivos subirías a Git? ¿Cuánto tardó `uv sync` comparado con
`pip install -r` del ejercicio 4? ¿Qué pasa con `uv python install 3.13` y
`uv venv --python 3.13`, algo que venv solo no puede hacer?

---

## Ejercicio bonus · Jupyter con tu venv

```powershell
.venv\Scripts\python.exe -m pip install ipykernel
.venv\Scripts\python.exe -m ipykernel install --user --name repaso-venv --display-name "Python (repaso-venv)"
jupyter kernelspec list
```

Abre Jupyter, elige el kernel "Python (repaso-venv)" y ejecuta
`import sys; sys.prefix`: debe apuntar a tu `.venv`.
