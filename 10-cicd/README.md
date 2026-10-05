# 10 · CI/CD con GitHub Actions y compuerta de calidad

🎬 Video: `cicd\cicd-es.mp4` (también en inglés: `-en.mp4`, y hojas de revisión `revision-es.png`).

## 🧱 Conocimiento previo

Antes de hablar de CI/CD conviene tener claras cinco piezas. Si ya las dominas, salta a la siguiente sección.

### 1. Git: commit, push, rama y pull request

- **Commit:** una "foto" del proyecto con un mensaje. Vive en tu compu.
- **Push:** subir tus commits a GitHub. Es el momento en que *los demás* (y los robots) se enteran del cambio.
- **Rama (branch):** una línea de trabajo paralela. `main` es la rama "oficial"; tú trabajas en `feature/limpieza` para no romper `main` mientras experimentas.
- **Pull request (PR):** la petición de "mezcla mi rama en `main`". Es donde el equipo revisa el cambio **antes** de aceptarlo.

> Analogía: `main` es el documento final del trabajo en grupo. Cada quien escribe en su copia (rama) y pide permiso (PR) para pegar su parte en el documento final.

### 2. El problema del "en mi máquina sí funciona"

En la Actividad 3 el **mismo código** daba f1 = 0.563 en Windows y 0.611 en macOS, por versiones distintas de scikit-learn. Cada compu tiene su Python, sus librerías y sus archivos sueltos. Un proyecto que solo corre "en la compu de Diego" no es un proyecto reproducible.

### 3. Script y código de salida (exit code)

Todo programa, al terminar, le devuelve al sistema operativo un número:

| Código | Significado | Cómo se produce en Python |
|---|---|---|
| `0` | todo bien | el script termina normal, o `raise SystemExit(0)` |
| `1` (o cualquier ≠ 0) | algo falló | una excepción no capturada, o `raise SystemExit(1)` a propósito |

Esto es **la base de todo CI**: la máquina no lee tus `print`, solo mira ese número para pintar verde o rojo.

### 4. Pruebas automáticas (tests)

Una prueba es una función que verifica algo con `assert`:

```python
def test_convierte_porcentaje():
    assert convertir("63%") == 63.0
```

`pytest` busca archivos `test_*.py`, corre cada función `test_*` y, si algún `assert` falla, sale con código 1. Hacerlo a mano cada vez se olvida; por eso se automatiza.

### 5. YAML

El formato en que se escriben los workflows. Es como un JSON sin llaves, donde **la sangría importa**:

```yaml
llave: valor
lista:
  - elemento1
  - elemento2
diccionario:
  subllave: "3.12"     # entre comillas: si no, 3.10 se lee como el número 3.1
```

## 🎯 Qué tienes que saber

### 1. CI, entrega continua y despliegue continuo

Son tres escalones; cada uno automatiza un poco más.

| Concepto | Qué automatiza | Pregunta que responde | Quién aprieta el último botón |
|---|---|---|---|
| **CI** — Integración continua | Cada push/PR se **construye y prueba** solo en una máquina limpia | ¿Este cambio rompe algo? | — |
| **CD** — Entrega continua (*Delivery*) | Además deja un **artefacto listo** para producción (paquete, imagen, modelo) | ¿Está listo para salir? | **Un humano** decide desplegar |
| **CD** — Despliegue continuo (*Deployment*) | Además lo **publica** solo si todo pasó | — | **Nadie**: se despliega automáticamente |

> Analogía de restaurante: **CI** es el chef que prueba cada plato antes de que salga de la cocina. **Entrega continua** es dejar el plato listo en la barra; el mesero decide cuándo llevarlo. **Despliegue continuo** es una banda transportadora que lo lleva a la mesa en cuanto pasa la prueba.

En el curso vimos dos de estos:
- **Taller 1 (GitHub Pages):** despliegue continuo puro. Cada push a `main` termina en el sitio publicado.
- **Ejercicio 3:** CI + entrega continua. Cada push entrena y evalúa el modelo y deja `modelo.joblib` como artefacto, pero no lo despliega. El PDF lo defiende así: *"para algo que le afecte a alguien, preferiríamos que la última puerta la abra un humano"*.

### 2. Por qué en ML la CI/CD es distinta

En software, el comportamiento depende del **código**. En ML depende de **tres cosas que cambian por separado** (Sculley et al., 2015):

| Qué cambia | Ejemplo con la Champions | Cómo se valida en CI |
|---|---|---|
| **Código** | Alguien edita `limpiar.py` | Pruebas unitarias (pytest), lint |
| **Datos** | La fuente manda `'3/10'` en vez de `'3 of 10'` | Pruebas de datos: esquema, formato, nulos, clases válidas |
| **Modelo** | Se reentrena y sale peor | **Compuerta de calidad**: métrica mínima y comparación con un baseline |

Consecuencias (las que el equipo escribió en la reflexión del Ejercicio 3):
1. **Las pruebas de modelo no son binarias.** Un modelo da un número; alguien tiene que decidir el umbral (0.40). Es una decisión de criterio, no técnica.
2. **El pipeline puede fallar sin que nadie toque el código.** Basta con que lleguen datos distintos.
3. **Un modelo puede ser malo sin que nada truene.** El código corre, el modelo se entrena... y predice basura. Por eso la compuerta es obligatoria.

### 3. GitHub Actions: anatomía de un workflow

Un workflow es un archivo `.yml` en `.github/workflows/`. Su jerarquía:

```
Workflow (pipeline.yml)
 └── on:  eventos que lo disparan
 └── jobs:
      ├── job "extraer"  ── runs-on: ubuntu-latest   (una VM nueva)
      │     └── steps: checkout → setup-python → make instalar → make extraer → upload
      └── job "limpiar"  ── needs: extraer           (otra VM nueva)
            └── steps: ...
```

| Pieza | Qué es | Ejemplo |
|---|---|---|
| **Evento** (`on:`) | Qué dispara el workflow | `push`, `pull_request`, `workflow_dispatch`, `schedule` |
| **Job** | Unidad de trabajo; corre en **su propia máquina** | `extraer`, `limpiar` |
| **Runner** | La máquina virtual que ejecuta el job | `runs-on: ubuntu-latest` (también `windows-latest`, `macos-latest`, o un runner propio) |
| **Step** | Un paso dentro del job; los steps de un mismo job **sí** comparten disco | `- run: make extraer` |
| **`uses:`** | Usar una **acción** ya hecha por otros (código reutilizable versionado) | `uses: actions/checkout@v4` |
| **`run:`** | Ejecutar un **comando de shell** tuyo | `run: pytest -v` |
| **`with:`** | Parámetros de una acción | `with: { python-version: "3.12" }` |
| **`needs:`** | Dependencia entre jobs: "no empieces hasta que X termine **bien**" | `needs: entrenar` |
| **`if:`** | Condición para correr un step/job | `if: always()` |

#### Los eventos más usados

| Evento | Cuándo corre | Para qué sirve |
|---|---|---|
| `push: branches: [main]` | Cada push a `main` | Validar/desplegar lo que ya es oficial |
| `pull_request` | Cada PR abierto o actualizado | Validar **antes** de mezclar: la esencia de la CI |
| `workflow_dispatch` | Botón "Run workflow" | Correrlo a mano (re-desplegar, depurar) |
| `schedule: - cron: "0 6 * * 1"` | Según un horario (UTC) | Reentrenar cada semana, detectar que una dependencia nueva rompió algo |

#### `uses` vs `run`

> `uses:` es **comprar un mueble armado** (una acción que alguien ya programó: clonar el repo, instalar Python, subir artefactos). `run:` es **armarlo tú** con tus propias herramientas (tus comandos).

#### Jobs en paralelo vs encadenados

Por defecto **todos los jobs corren en paralelo**. Con `needs:` los encadenas, y además ganas algo importante: si un job falla, los que dependen de él quedan **skipped** (ni se intentan). Así no gastas minutos entrenando con datos que no se limpiaron.

### 4. Artefactos: cada job es una máquina limpia

Este es el concepto que más confunde. Cada job arranca en una VM **recién creada y vacía**: no tiene tu código, ni Python con tus librerías, ni los archivos del job anterior. Por eso cada job del Ejercicio 3 repite `checkout` + `setup-python` + `make instalar`, y los archivos viajan así:

```
job extraer:   ... make extraer → upload-artifact (name: datos-crudos, path: artefactos/crudo.csv)
                                         │
                                  [almacén de GitHub]
                                         │
job limpiar:   download-artifact (name: datos-crudos) → make limpiar → upload-artifact (datos-limpios)
```

> Analogía: cada job es un turno distinto en una fábrica, con trabajadores distintos que no se conocen. Para pasarse el trabajo, el turno saliente deja la pieza en un **casillero con nombre** (`upload-artifact`) y el entrante la recoge de ese casillero (`download-artifact`).

Los artefactos también quedan **descargables** desde la página de la ejecución (así se verificaba el Ejercicio 3: bajar `metricas.json` o `modelo.joblib`).

### 5. Secrets, matrix y caché

| Herramienta | Problema que resuelve | Cómo se escribe |
|---|---|---|
| **Secrets** | Contraseñas/tokens que no pueden ir en el repo | Se guardan en *Settings → Secrets and variables → Actions*; se usan como `${{ secrets.TESTPYPI_TOKEN }}`. En los logs aparecen como `***`. |
| **Matrix** | Probar en varias versiones/sistemas sin copiar el job | `strategy: matrix: python-version: ["3.10", "3.11", "3.12"]` → 3 jobs en paralelo |
| **Caché de pip** | Reinstalar todo en cada corrida es lento | `setup-python` con `cache: pip`; la llave es el hash de `requirements.txt` (si no cambió, reusa) |

La matrix habría atrapado el problema de la Actividad 3 (Windows vs macOS) desde el primer día: `os: [ubuntu-latest, windows-latest, macos-latest]`.

### 6. Pruebas automáticas, lint y construcción de artefactos (Actividad 5)

No hay repo propio de la Actividad 5; en este repaso la tratamos como la parte de **pruebas dentro del pipeline**. Un pipeline de CI típico tiene tres capas, de la más barata a la más cara:

1. **Lint** (`ruff check`, `flake8`): revisa el código **sin ejecutarlo** (imports sin usar, variables indefinidas). Falla en segundos.
2. **Pruebas** (`pytest`): de código (¿la función convierte `'63%'` a 63.0?), de datos (¿los tiros siguen llegando como `'N of M'`?) y de modelo (¿le gana al trivial?).
3. **Construcción del artefacto**: solo si todo pasó, se genera lo que se entrega (el `.joblib`, un paquete `.whl`, una imagen Docker) y se sube con `upload-artifact`.

Ver `ejemplos/ci-pytest-matrix.yml` y `ejemplos/test_pipeline.py`.

### 7. La compuerta de calidad (quality gate)

Es lo que convierte un "script programado" en un pipeline de ML: el último job no solo **mide**, **decide**.

```python
if f1 < MINIMO_F1:          # 0.40
    return 1                # → raise SystemExit(1) → step rojo → workflow rojo
if f1 <= f1_tonto:          # DummyClassifier(strategy="most_frequent")
    return 1
return 0
```

- **¿Por qué un baseline trivial?** Un modelo que siempre dice "Home Win" ya saca accuracy 0.483 sin aprender nada. Si tu modelo no le gana a eso, no sirve, por bonita que se vea su accuracy. El equipo lo llamó *"el más honesto de los dos criterios"*.
- **¿Por qué `f1_macro`?** Promedia el F1 de las tres clases por igual, así que castiga ignorar `Draw` (25 de 144 partidos). El trivial saca f1_macro = 0.217.
- **Efecto práctico:** nadie del equipo puede subir por accidente un modelo peor sin que el PR quede en rojo.

### 8. El Makefile: mismos comandos en local y en CI

`make` ejecuta recetas con nombre. El workflow llama `make limpiar` y tú en la laptop también: **el mismo comando**, así que si algo falla en la nube lo reproduces local sin adivinar. Y si cambian de GitHub Actions a GitLab, los comandos ya viven fuera del YAML. (Ojo: la sangría de las recetas debe ser **TAB**.)

### 9. GitHub Pages con Actions (Taller 1)

GitHub Pages hospeda gratis sitios **estáticos** (HTML/CSS/JS). Con *Settings → Pages → Source = GitHub Actions*, el workflow `pages.yml` hace: `checkout` → `configure-pages` → `upload-pages-artifact` (empaqueta el sitio) → `deploy-pages` (lo publica). Detalles que suelen preguntar:
- `permissions: pages: write, id-token: write` — mínimo privilegio; el `id-token` (OIDC) permite autenticarse sin contraseñas.
- `concurrency: group: pages, cancel-in-progress: true` — si haces dos pushes seguidos, solo se publica el último.
- `environment: github-pages` con `url: ${{ steps.deployment.outputs.page_url }}` — muestra la URL publicada en la ejecución.

## 📂 Qué hicimos en el curso

### Taller 1 · Portafolio con GitHub Pages
Repo: [Andyfer004/Portafolio-MLOPS](https://github.com/Andyfer004/Portafolio-MLOPS). Sitio estático del equipo (Inicio, Proyectos, Laboratorios, Casos de estudio, Talleres) que *"se despliega solo con cada push a main"*. Un solo job `deploy` en `.github/workflows/pages.yml` con eventos `push` a `main` y `workflow_dispatch`. Ver `ejemplos/pages.yml` comentado.

### Actividad 5 · Pruebas automáticas en el pipeline
No hay repo separado; en este repaso se cubre como pruebas con pytest, lint y construcción de artefactos dentro del pipeline (secciones 5 y 6, y `ejemplos/ci-pytest-matrix.yml`).

### Ejercicio 3 · Pipeline automatizado con GitHub Actions
Repo: [DiegoLinares11/Ejecicio3-MLOPS](https://github.com/DiegoLinares11/Ejecicio3-MLOPS) (PDF del 21 de agosto de 2026; Diego Linares, Andy Fuentes, Christian Echeverria, Diederich Solis).

**Qué construyeron.** Las etapas que corrían a mano en ejercicios anteriores, partidas en cuatro scripts que corren como jobs separados en cada push:

| Job | Script | Qué hace | Artefacto |
|---|---|---|---|
| `extraer` | `src/extraer.py` | Lee `datos/champions_league_matches.csv` (151 filas × 18 columnas) | `crudo.csv` |
| `limpiar` | `src/limpiar.py` | Quita 7 filas vacías y las columnas `score`, `winner` (fuga) + `date`, `venue`, `referee` → 144 filas | `limpio.csv` |
| `entrenar` | `src/entrenar.py` | Convierte texto a número, `ColumnTransformer` + `LogisticRegression(C=0.541, class_weight="balanced")`, split 80/20 estratificado (115/29) | `modelo.joblib` + `prueba.csv` |
| `evaluar` | `src/evaluar.py` | Mide en prueba, compara con el trivial y aplica la compuerta | `metricas.json` |

- **Encadenamiento:** `needs:` + `upload-artifact`/`download-artifact`; si una etapa falla, las siguientes ni se intentan. Eventos: `push` a `main`, `pull_request`, `workflow_dispatch`. Python 3.12 con `cache: pip`.
- **Makefile** (idea del tutorial de DataCamp): `make instalar`, `make extraer`… `make pipeline`.
- **Compuerta:** `evaluar.py` sale con código 1 si `f1_macro < 0.40` o si no supera al `DummyClassifier(strategy="most_frequent")`. Escribe además una tabla en `GITHUB_STEP_SUMMARY` y el artefacto `metricas` se sube con `if: always()`.

**Resultado de la corrida:**

| Métrica | Modelo | Modelo trivial |
|---|---|---|
| accuracy | 0.621 | 0.483 |
| f1_macro | 0.542 | 0.217 |

El PDF aclara que es una versión **reducida a propósito**: no repite la selección de variables ni la búsqueda de hiperparámetros de la Actividad 3 (usa directamente los valores ganadores), por eso da 0.542 y no el 0.631 de la Actividad 4.

**Reflexión sobre CI/CD en ML (resumen del PDF):**
- *Lo que se traslada tal cual:* verificar cada cambio en una máquina limpia. Les habría ahorrado el problema de 0.563 (Windows) vs 0.611 (macOS) de la Actividad 3: la CI es *"una segunda opinión que no depende de lo que cada quien tenga instalado"*.
- *Lo que cambia:* el sistema depende de código, datos y modelo. (1) Las pruebas no son binarias: elegir el umbral les costó más que programarlo. (2) Los datos también deberían validarse: si la posesión dejara de llegar como `'63%'` o los tiros como `'3 of 10'`, el pipeline produciría un modelo malo **en silencio** — *"la falla más peligrosa y la que todavía no cubrimos"*. (3) El pipeline puede fallar sin que nadie toque el código.
- *Su opinión:* el mayor valor no es la velocidad (entrenar tarda segundos) sino la **disciplina**: dependencias declaradas, rutas relativas, datos accesibles, sin pasos escondidos en la cabeza de alguien. Al partir el trabajo en cuatro scripts descubrieron suposiciones que solo funcionaban porque siempre corrían todo en el mismo directorio. Y cuidado con automatizar de más: un modelo no debería llegar a producción sin que una persona vea sus resultados.

## 🧪 Práctica

### `repaso.ipynb` (generado desde `repaso.py`)
Simula GitHub Actions en local sobre `../datos/champions_league_matches.csv`:
1. Demuestra los códigos de salida con `subprocess` (`print` → 0, `SystemExit(1)` → 1, `1/0` → 1).
2. Corre las 4 etapas, cada una en una **carpeta temporal vacía** ("máquina limpia"), pasándose archivos por un almacén que imita `upload/download-artifact`, con `needs` (si un job falla, los siguientes quedan `skipped`) y simulación de `GITHUB_STEP_SUMMARY`. Resultado real: **accuracy 0.621 / f1_macro 0.542** vs **0.483 / 0.217** del trivial.
3. Simula modelos malos y la compuerta los bloquea capturando `SystemExit` (el notebook no se rompe): etiquetas revueltas (f1 0.320) y `C=1e-6` (predice siempre Home Win, f1 0.217 = trivial).
4. Cambia el formato de la fuente a `'3/10'`: 8 columnas quedan 100 % nulas y el modelo **pasa la compuerta** con f1 0.550. Un mini-pytest de pruebas de datos sí lo detecta (2 pruebas fallan, exit code 1).

```bash
cd RepasoMLOps
python tools/build_nb.py 10-cicd/repaso.py     # regenera y ejecuta el notebook
```

### `ejemplos/`
| Archivo | Qué es |
|---|---|
| `pipeline.yml` | Workflow real del Ejercicio 3, comentado línea por línea |
| `pages.yml` | Workflow real del Taller 1 (GitHub Pages), comentado |
| `Makefile` | Makefile real del Ejercicio 3, comentado |
| `ci-pytest-matrix.yml` | Ejemplo de repaso: lint → pytest en Python 3.10/3.11/3.12 (matrix) → construir artefacto; incluye `schedule` y un ejemplo de `secrets` |
| `test_pipeline.py` | Pruebas de código, datos y modelo para el repo del Ejercicio 3 (las que corre el workflow anterior) |

Para probar de verdad: haz fork de `Ejecicio3-MLOPS`, copia `ci-pytest-matrix.yml` a `.github/workflows/ci.yml` y `test_pipeline.py` a `tests/`, y haz push.

## ❓ Preguntas tipo examen

**P:** ¿Cuál es la diferencia entre entrega continua y despliegue continuo?
**R:** En los dos, cada cambio que pasa las pruebas queda listo para producción. En la **entrega** continua un humano decide cuándo desplegar; en el **despliegue** continuo se publica automáticamente sin intervención. El Taller 1 (Pages) es despliegue continuo; el Ejercicio 3 es entrega continua (deja el modelo como artefacto, no lo despliega).

**P:** ¿Por qué la CI/CD en ML es distinta de la de software tradicional?
**R:** Porque el sistema depende de tres cosas que cambian por separado: código, datos y modelo. Además de pruebas de código hay que validar datos (esquema, formato) y modelo (métrica mínima, comparación con un baseline). El pipeline puede fallar sin cambios en el código, solo porque llegaron datos distintos.

**P:** ¿Cómo sabe GitHub Actions que un step falló?
**R:** Por el código de salida del proceso: 0 es éxito, cualquier otro valor es falla. Por eso `evaluar.py` termina con `raise SystemExit(main())` y `main()` devuelve 1 cuando la compuerta rechaza el modelo.

**P:** ¿Qué hace `needs:` y qué pasa si el job del que depende falla?
**R:** Hace que el job espere a que otro termine **con éxito**. Si ese job falla, el dependiente queda *skipped* y no se ejecuta. Sin `needs:`, los jobs corren en paralelo.

**P:** ¿Por qué el Ejercicio 3 usa `upload-artifact` y `download-artifact` entre jobs?
**R:** Porque cada job corre en una máquina virtual nueva y limpia; no comparten disco. La única forma de pasar `crudo.csv`, `limpio.csv` o `modelo.joblib` al siguiente job es subirlo como artefacto con nombre y descargarlo en el siguiente.

**P:** ¿Diferencia entre `uses:` y `run:`?
**R:** `uses:` ejecuta una acción reutilizable ya publicada (p. ej. `actions/checkout@v4`, `actions/setup-python@v5`), configurable con `with:`. `run:` ejecuta un comando de shell propio (p. ej. `make evaluar`, `pytest -v`).

**P:** ¿Cuáles son los dos criterios de la compuerta de calidad del Ejercicio 3 y por qué el segundo?
**R:** Falla si `f1_macro < 0.40` o si no supera al `DummyClassifier(strategy="most_frequent")`. El segundo asegura que el modelo aprende algo: el trivial saca accuracy 0.483 sin aprender nada, pero su f1_macro es solo 0.217.

**P:** ¿Por qué se sube `metricas.json` con `if: always()`?
**R:** Porque si la compuerta falla, el step `make evaluar` queda en rojo y los steps siguientes normalmente no correrían. Con `if: always()` las métricas se suben igual, que es justo cuando más interesa verlas.

**P:** ¿Para qué sirve el Makefile si ya existe el YAML?
**R:** Para que local y CI usen exactamente los mismos comandos (`make limpiar`). Si algo falla en la nube se reproduce igual en la laptop, y los comandos no quedan amarrados a una herramienta de CI específica.

**P:** ¿Qué es una matrix y qué problema del curso habría detectado?
**R:** Una estrategia que clona un job por cada combinación de valores (p. ej. Python 3.10/3.11/3.12 o Ubuntu/Windows/macOS) y los corre en paralelo. Habría detectado que el mismo código daba 0.563 en Windows y 0.611 en macOS (Actividad 3).

**P:** ¿Cómo se maneja un token de PyPI en un workflow?
**R:** Como **secret** del repo (*Settings → Secrets and variables → Actions*), referenciado con `${{ secrets.NOMBRE }}`. Nunca se escribe en el YAML ni en el código; en los logs aparece como `***`.

**P:** ¿Qué hace `cache: pip` en `setup-python`?
**R:** Guarda los paquetes descargados entre corridas usando como llave el hash de `requirements.txt`. Si las dependencias no cambiaron, las reutiliza y la instalación es más rápida.

**P:** En el Taller 1, ¿qué hacen `permissions` y `concurrency` en `pages.yml`?
**R:** `permissions` da al token solo lo necesario (`contents: read`, `pages: write`, `id-token: write` para autenticarse con OIDC). `concurrency` con `cancel-in-progress: true` cancela una publicación en curso si llega un push nuevo, para que solo se publique el último.

**P:** ¿Qué falla reconoció el equipo que su pipeline todavía no cubría?
**R:** La validación de datos: si la fuente cambiara de formato (posesión sin `'%'`, tiros sin `'N of M'`), el pipeline correría y produciría un modelo malo en silencio. En el notebook de repaso, con `'3/10'` el modelo pasa la compuerta (f1 0.550) aunque perdió 8 columnas; solo una prueba de datos lo detecta.

## 🏋️ Ejercicios

1. **Rompe la compuerta a propósito.** En un fork de `Ejecicio3-MLOPS`, cambia `MINIMO_F1` a `0.60` y haz push. Verifica en *Actions* que `evaluar` queda rojo, que `metricas.json` igual se puede descargar (por el `if: always()`) y que la tabla aparece en el Step Summary.
2. **Agrega un job de pruebas.** Copia `ejemplos/test_pipeline.py` a `tests/` y crea un job `pruebas` que corra `pytest -v`. Haz que `extraer` tenga `needs: pruebas`. Luego modifica el CSV para que una fila diga `'3/10'` en vez de `'3 of 10'`… ¿cuántas filas tienes que cambiar para que falle `test_formato_de_tiros`?
3. **Matrix de sistemas.** Modifica `ci-pytest-matrix.yml` para correr en `ubuntu-latest` y `windows-latest`. ¿Funciona `make` en Windows? (Pista: no viene instalado; reemplaza `make pipeline` por los cuatro `python src/...`.)
4. **Programa un reentrenamiento.** Agrega `schedule: - cron: "0 6 * * 1"` al `pipeline.yml`. Explica con tus palabras qué ganas y qué riesgo corres si además lo desplegaras automáticamente.
5. **En el notebook:** agrega un tercer criterio a `etapa_evaluar` — que el F1 de la clase `Draw` sea al menos 0.15 — y mira qué casos pasan y cuáles no.

## 🔗 Referencias

- Repo del Ejercicio 3: <https://github.com/DiegoLinares11/Ejecicio3-MLOPS> (incluye `Ejercicio_3.pdf`)
- Portafolio / Taller 1: <https://github.com/Andyfer004/Portafolio-MLOPS>
- GitHub Docs — Quickstart for GitHub Actions: <https://docs.github.com/en/actions/writing-workflows/quickstart>
- GitHub Docs — Storing and sharing data from a workflow (artefactos): <https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts>
- GitHub Docs — Using secrets in GitHub Actions: <https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions>
- GitHub Docs — Running variations of jobs in a workflow (matrix): <https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/running-variations-of-jobs-in-a-workflow>
- GitHub Pages con Actions: <https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages>
- Abid, A. — Makefile and GitHub Actions tutorial (DataCamp): <https://www.datacamp.com/tutorial/makefile-github-actions-tutorial>
- Sato, Wider y Windheuser (2019) — Continuous Delivery for Machine Learning: <https://martinfowler.com/articles/cd4ml.html>
- Sculley et al. (2015) — Hidden Technical Debt in Machine Learning Systems, NeurIPS 28.
