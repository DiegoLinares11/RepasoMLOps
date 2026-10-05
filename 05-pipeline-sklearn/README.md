# 05 · Pipeline de scikit-learn empaquetado

🎬 Video: [▶️ en español](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/05-pipeline-sklearn-es.mp4) · [▶️ in English](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/05-pipeline-sklearn-en.mp4) · [todos los videos](https://github.com/DiegoLinares11/RepasoMLOps/releases/tag/videos)

## 🧱 Conocimiento previo

### 1. El problema que estamos resolviendo

Con el CSV de la Champions (tema 01) queremos **clasificar** cada partido en `Home Win`,
`Away Win` o `Draw` a partir de las estadísticas del juego. Es **clasificación multiclase**
(tres clases). Las clases están desbalanceadas: 71 / 48 / 25.

### 2. `X` e `y`

- `X` = las variables de entrada (features): posesión, tiros, atajadas, equipos. Una fila por
  partido.
- `y` = lo que queremos predecir (target): `result`.

Un modelo aprende la relación `X → y` con unos partidos y la aplica a otros.

### 3. Train y test: por qué se separa

Si evalúas al modelo con los mismos partidos con los que estudió, mides **memoria**, no
aprendizaje. Por eso se aparta un conjunto de **prueba** (test) que el modelo nunca ve al
entrenar. Analogía: los ejercicios resueltos de clase (train) vs el examen con problemas
nuevos (test).

**Estratificar** (`stratify=y`) = que train y test tengan la misma proporción de clases. Con
solo 25 empates, un corte al azar podría dejar el test casi sin empates.

### 4. Los modelos solo entienden números

Un `RandomForestClassifier` no sabe qué es `'63%'`, ni `'3 of 10'`, ni `'Arsenal'`, ni un
`NaN`. Antes de entrenar, todo tiene que ser una matriz de números sin huecos. A ese trabajo se
le llama **preprocesamiento**:

| Problema | Herramienta |
|---|---|
| hay nulos | **imputar** (rellenar) con `SimpleImputer` |
| números en escalas distintas (posesión 0–100, tiros 0–20) | **escalar** con `StandardScaler` |
| texto categórico ("Arsenal") | **codificar** con `OneHotEncoder` |
| números disfrazados de texto ('63%') | transformador **personalizado** |

### 5. Clases y herencia en Python (lo mínimo)

Para crear un transformador propio vamos a escribir una **clase** que **hereda** de otras:

```python
class TextoANumero(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None): ...
    def transform(self, X): ...
```

Heredar = "mi clase recibe gratis los métodos de esas otras". `self` es el propio objeto, y
`self.algo_ = ...` guarda información dentro de él para usarla después.

## 🎯 Qué tienes que saber

### 1. El contrato de scikit-learn: transformer vs estimator

| Tipo | Métodos | Qué hace | Ejemplos |
|---|---|---|---|
| **Transformer** | `fit(X)` + `transform(X)` (y `fit_transform`) | aprende algo de los datos y los **cambia** | `SimpleImputer`, `StandardScaler`, `OneHotEncoder`, `SelectKBest` |
| **Estimator / predictor** | `fit(X, y)` + `predict(X)` | aprende y **predice** | `RandomForestClassifier`, `LogisticRegression` |

**Analogía:** `fit` es estudiar, `transform`/`predict` es responder el examen. Lo aprendido en
`fit` queda en atributos que **terminan en `_`**: `StandardScaler().fit(train)` guarda `mean_`
y `scale_`. Ejemplo del notebook: con train `[40, 50, 60]` aprende media 50 y desviación 8.165;
al transformar un 70 de prueba da (70 − 50) / 8.165 = 2.449. **Nunca** recalcula la media con
los datos de prueba.

### 2. `Pipeline`: la línea de ensamblaje

Un `Pipeline` encadena pasos con nombre: varios transformers y un estimator al final.

```python
Pipeline([("preprocesamiento", ColumnTransformer(...)),
          ("modelo", RandomForestClassifier(n_estimators=300, random_state=42))])
```

- `pipe.fit(X_train, y_train)`: cada paso hace `fit_transform` y le pasa el resultado al
  siguiente; el último hace `fit`.
- `pipe.predict(X_test)`: cada paso hace solo `transform` (con lo aprendido en train) y el
  último `predict`.

Se comporta como **un solo modelo**: se entrena, se evalúa, se guarda (`joblib.dump`) y se
calibra (tema 06) como una sola pieza.

### 3. Por qué el `Pipeline` evita la fuga de datos

**Fuga de información (data leakage):** información del test (o del fold de validación) se
cuela en el entrenamiento → métricas infladas que no se repiten en producción. Como estudiar
con el examen resuelto.

Hay dos fugas distintas en este proyecto:

| Fuga | Ejemplo | Solución |
|---|---|---|
| **de columnas** | `score` y `winner` revelan el resultado | eliminarlas en el filtrado |
| **de preprocesamiento** | escalar/imputar/seleccionar con los 144 partidos antes de partir | meter todo lo que "aprende" dentro del `Pipeline` |

```python
# MAL: el escalador ve los 144 partidos, incluido el test
X_esc = StandardScaler().fit_transform(X)
cross_val_score(modelo, X_esc, y)

# BIEN: en cada fold el escalador se ajusta solo con el train de ese fold
cross_val_score(Pipeline([("escalar", StandardScaler()), ("modelo", modelo)]), X, y)
```

Lo que mide el notebook:

| Experimento | Fuera del pipeline | Dentro del pipeline |
|---|---|---|
| Escalar + KNN (accuracy CV) | 0.695 | 0.716 |
| `SelectKBest(k=20)` sobre **2 000 columnas de ruido puro** (accuracy CV) | **0.750** | **0.438** (baseline 0.493) |

Lectura: con `StandardScaler` la fuga es sutil y ni siquiera infla de forma predecible (aquí
salió más bajo); por eso pasa desapercibida. Con un paso que aprende mucho de los datos, como
seleccionar variables, la fuga convierte **ruido puro** en un modelo "de 75 %". Dentro del
pipeline la verdad aparece: el ruido no predice nada.

### 4. `ColumnTransformer`: un tratamiento por tipo de variable

**Analogía:** una cocina con estaciones. Las verduras van a una tabla, la carne a otra, y al
final todo se sirve en el mismo plato (una sola matriz).

| Rama | Columnas | Pasos | Salida |
|---|---|---|---|
| `numericas` | 4 `*_pct` (ya float) | `SimpleImputer(median)` → `StandardScaler` | 4 |
| `porcentajes` | `home_possession`, `away_possession` (`'63%'`) | convertir → imputar → escalar | 2 |
| `razones` | tiros a puerta y atajadas (`'3 of 10'`) | convertir a hechos + intentos → imputar → escalar | 8 |
| `categoricas` | `home_team`, `away_team` | `SimpleImputer(most_frequent)` → `OneHotEncoder` | 72 |

Total: **12 columnas crudas → 86 numéricas**. `remainder="drop"` descarta cualquier columna
que no se declaró (filtro de seguridad: si se colara `score`, no llegaría al modelo).

### 5. Las piezas de preprocesamiento, una por una

- **`SimpleImputer`**: rellena nulos. `strategy="median"` para números (la mediana no se mueve
  con extremos), `"most_frequent"` para categorías. Aprende el valor en train y lo reutiliza.
  En nuestro CSV, los 3 nulos de `home_saves_pct` vienen de porteros con `0 of 0` atajadas.
- **`StandardScaler`**: `z = (x − media) / desviación`. Deja media 0 y desviación 1. Imprescindible
  para modelos basados en distancias o coeficientes (KNN, SVC, regresión logística); al bosque
  aleatorio le da igual, pero no estorba.
- **`OneHotEncoder`**: "Arsenal" → una columna `home_team_Arsenal` con 1 y las demás 0.
  `handle_unknown="ignore"`: un equipo nunca visto produce ceros en lugar de un error (en el
  notebook se predice un "Municipal vs Comunicaciones" sin problema).

### 6. Transformadores personalizados

Cuando no existe un transformer para tu caso (`'3 of 10'`), lo escribes:

```python
class TextoANumero(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        self.tipos_ = {...}          # aprende: ¿cada columna es porcentaje o razón?
        return self                  # fit SIEMPRE devuelve self (para poder encadenar)

    def transform(self, X):
        ...                          # '63%' -> 63.0 ; '3 of 10' -> 3.0, 10.0
        return matriz_numerica

    def get_feature_names_out(self, input_features=None):
        return ["home_possession_pct", "home_saves_hechos", "home_saves_intentos", ...]
```

| Hereda de | Te da gratis | Regla que impone |
|---|---|---|
| `BaseEstimator` | `get_params` / `set_params` (los usan `GridSearchCV` y `clone`) | el `__init__` solo guarda argumentos, sin lógica |
| `TransformerMixin` | `fit_transform` y `set_output` | definir `fit` y `transform` |

¿Por qué no limpiar con pandas antes? Porque entonces la limpieza vive **fuera** del modelo: el
día que llegue un partido nuevo, alguien tendría que acordarse de repetirla igual. Dentro del
pipeline viaja con el modelo (y con el `.joblib`). En la Actividad 1 se escribieron dos clases
(`PorcentajeATexto` y `RatioATexto`); en el notebook usamos una sola, `TextoANumero`, que
detecta el tipo en `fit`.

### 7. Mirar adentro: `get_feature_names_out` y `set_output`

- `pipe.named_steps["preprocesamiento"].get_feature_names_out()` devuelve los 86 nombres, con el
  prefijo de la rama: `razones__home_saves_hechos`, `categoricas__home_team_Arsenal`... Para que
  funcione, **cada** transformer (incluido el personalizado) tiene que saber nombrar sus salidas.
- `preprocesamiento.set_output(transform="pandas")` hace que la salida sea un `DataFrame` con
  esos nombres en lugar de un array anónimo. Requiere `OneHotEncoder(sparse_output=False)`.
- `set_config(display="diagram")` dibuja el pipeline como diagrama interactivo en Jupyter.

### 8. Por qué empaquetar

Un notebook que "corre en mi compu" no es reproducible: depende de qué versiones tengas, de
dónde está el CSV, de en qué orden corriste las celdas. Empaquetar lo convierte en algo que
**cualquier integrante corre con un comando**:

```bash
pip install .
act1-demo
```

| Pieza | Qué es | Por qué |
|---|---|---|
| **`src/` layout** | el código vive en `src/act1_pipeline/` | obliga a instalar para importar: pruebas lo mismo que recibe el compañero |
| **`pyproject.toml`** | metadatos, dependencias, configuración del build | estándar moderno (PEP 621); pip lo lee directo |
| **`setup.py`** | *shim* que solo llama `setup()` | compatibilidad con herramientas viejas |
| **`package-data`** | `"act1_pipeline" = ["datasets/*.csv"]` | el CSV viaja dentro del wheel; se lee con `importlib.resources` |
| **entry point** | `[project.scripts] act1-demo = "act1_pipeline.cli:main"` | pip crea el ejecutable `act1-demo` que llama a `main()` |
| **`random_state=42`** | semillas fijas | mismo resultado en cualquier máquina |
| **wheel** | `python -m build` → `dist/act1_pipeline-0.1.0-py3-none-any.whl` | se comparte por Drive/USB y se instala con `pip install archivo.whl` |

El archivo [`ejemplos/pyproject.toml`](ejemplos/pyproject.toml) trae el original comentado línea
por línea. (El tema 08 profundiza en empaquetar y publicar.)

## 📂 Qué hicimos en el curso

**Actividad 1 · Pipeline de scikit-learn** (equipo: Diego Linares, Andy Fuentes, Christian
Echeverria, Diederich Solis). Repo:
[DiegoLinares11/Actividad1-MLOPS](https://github.com/DiegoLinares11/Actividad1-MLOPS).

Continuación del Ejercicio 1: se implementó el modelo propuesto ahí, enmarcado en las dos
primeras etapas de CRISP-DM.

- **Business Understanding:** clasificar cada partido como Home Win / Away Win / Draw a partir de
  posesión, tiros y atajadas. Criterio de éxito: superar a la clase mayoritaria (~49 %) y que el
  pipeline sea reproducible en cualquier computadora.
- **Data Understanding:** cada hallazgo del Ejercicio 1 se volvió una pieza del pipeline:

| Hallazgo | Cómo lo atiende el pipeline |
|---|---|
| 7 filas vacías que separan jornadas | se eliminan en el filtrado (quedan 144 partidos) |
| posesión como `'63%'` | transformador `PorcentajeATexto` |
| tiros/atajadas como `'3 of 10'` | transformador `RatioATexto` (hechos e intentos) |
| nulos en `home_saves_pct` (0 of 0) | imputación por mediana |
| equipos categóricos | One-Hot Encoding |
| `score` y `winner` revelan el resultado | se descartan (fuga) |

- **Etapas:** extracción (`data.extraer_datos`, CSV empaquetado) → filtrado (`filtrar_datos`)
  → manejo de los cuatro tipos de variables (`construir_pipeline`) → separación estratificada
  (`separar_datos`, `test_size=0.2`, `seed=42`).
- **Diagrama** con `set_config(display="diagram")` en `notebooks/pipeline_demo.ipynb`.

Resultados (salida de `act1-demo`):

```
[1] Extracción      -> 151 filas, 18 columnas
[2] Filtrado        -> 144 filas, 13 columnas
[4] Separación      -> train=115  test=29
RESULTADO - Accuracy en prueba = 0.724
```

| Clase | precision | recall | f1 | soporte |
|---|---|---|---|---|
| Away Win | 0.615 | 0.800 | 0.696 | 10 |
| Draw | 0.500 | 0.200 | 0.286 | 5 |
| Home Win | 0.857 | 0.857 | 0.857 | 14 |

Accuracy **0.724** (21 de 29) contra un baseline de **0.483**. Evidencia de reproducibilidad: el
mismo paquete dio 0.724 en `Dlinares` (Windows 11, Python 3.14.2) y en `WH-Chris` (Linux
cachyos, Python 3.14.4).

Limitaciones que anotamos: test de solo 29 partidos (mucho margen de error), los empates casi no
se detectan (1 de 5), y las variables solo existen cuando el partido ya terminó, así que el
modelo **explica** el resultado más de lo que lo **predice** de antemano.

## 🧪 Práctica

`repaso.ipynb` reconstruye ese pipeline paso a paso sobre `../datos/champions_league_matches.csv`.
Números reales del notebook:

1. Transformer vs estimator con un ejemplo de juguete (`mean_` = 50, `scale_` = 8.165).
2. Extracción y filtrado 151 → 144 × 13; separación estratificada 115 / 29 con proporciones
   0.493 / 0.333 / 0.174 conservadas.
3. Transformador personalizado `TextoANumero` (aprende en `fit` si cada columna es porcentaje o
   razón).
4. `ColumnTransformer` de 4 ramas + `RandomForestClassifier(300, random_state=42)`:
   **accuracy 0.724**, mismo reporte por clase que la Actividad 1; baseline 0.483.
5. Diagrama en texto (función recursiva) y diagrama HTML; `get_feature_names_out` (12 → 86:
   4 + 2 + 8 + 72); `set_output(transform="pandas")` (DataFrame 115 × 86 sin nulos).
6. Fuga: escalar fuera vs dentro con KNN (0.695 vs 0.716) y selección de variables sobre ruido
   (0.750 fuera vs 0.438 dentro).
7. Predicción de un partido nuevo con texto crudo y equipos desconocidos (`Home Win`, p = 0.897),
   guardado/carga con `joblib`, y una `main()` que imprime lo mismo que `act1-demo`.

```powershell
python tools/build_nb.py 05-pipeline-sklearn/repaso.py
```

## ❓ Preguntas tipo examen

**P:** ¿Cuál es la diferencia entre un transformer y un estimator en scikit-learn?
**R:** El transformer tiene `fit` + `transform` (aprende y modifica los datos: imputar, escalar,
codificar); el estimator/predictor tiene `fit` + `predict` (aprende y predice una etiqueta).

**P:** ¿Qué significa que un atributo termine en guion bajo, como `mean_`?
**R:** Que se aprendió durante `fit`. Antes de `fit` no existe; `check_is_fitted` lo usa para saber
si el objeto ya fue entrenado.

**P:** ¿Qué hace `pipe.fit(X, y)` internamente? ¿Y `pipe.predict(X)`?
**R:** `fit`: `fit_transform` en cada transformer, pasando la salida al siguiente, y `fit` en el
estimator final. `predict`: solo `transform` en cada paso (con lo aprendido) y `predict` al final.

**P:** ¿Por qué el `Pipeline` evita la fuga de datos?
**R:** Porque todo lo que aprende de los datos (medias, medianas, categorías, columnas
seleccionadas) se aprende solo con train en `fit`, y en validación cruzada se reajusta dentro de
cada fold; el test o el fold de validación nunca influyen en el preprocesamiento.

**P:** Diferencia entre la fuga por `score`/`winner` y la fuga por escalar antes de partir.
**R:** La primera es fuga de **columnas**: variables que contienen la respuesta (se eliminan). La
segunda es fuga de **preprocesamiento**: estadísticas calculadas con datos de prueba (se evita
metiendo el preprocesamiento en el pipeline).

**P:** ¿Para qué sirve `ColumnTransformer`?
**R:** Para aplicar un sub-pipeline distinto a cada grupo de columnas (numéricas, porcentajes,
razones, categóricas) y concatenar las salidas en una sola matriz.

**P:** ¿Qué hace `handle_unknown="ignore"` en `OneHotEncoder` y por qué es necesario?
**R:** Si en predicción aparece una categoría que no se vio en train (un equipo nuevo), produce
una fila de ceros en lugar de lanzar un error. Sin él, el pipeline revienta en producción.

**P:** ¿De qué clases hereda un transformador personalizado y qué aporta cada una?
**R:** `BaseEstimator` (da `get_params`/`set_params`, necesarios para `GridSearchCV` y `clone`;
exige un `__init__` sin lógica) y `TransformerMixin` (da `fit_transform` y `set_output`).

**P:** ¿Por qué `fit` debe devolver `self`?
**R:** Para poder encadenar (`TextoANumero().fit(X).transform(X)`) y porque `Pipeline` y
`fit_transform` lo esperan.

**P:** ¿Para qué sirve `get_feature_names_out` y qué pasa si tu transformer no lo implementa?
**R:** Devuelve los nombres de las columnas de salida (aquí 86, con prefijo de rama). Si un paso
no lo implementa, `get_feature_names_out` del `ColumnTransformer` falla y `set_output("pandas")`
no puede nombrar las columnas.

**P:** ¿Por qué se usa `stratify=y` en `train_test_split`?
**R:** Para que train y test conserven la proporción de clases (49/33/17 %). Con solo 25 empates,
un corte al azar podría dejar el test casi sin empates y la métrica dependería de la suerte.

**P:** 12 columnas entran al pipeline y salen 86. ¿De dónde salen?
**R:** 4 numéricas + 2 de posesión + 8 de razones (4 columnas × hechos/intentos) + 72 del One-Hot
(36 equipos como local + 36 como visitante).

**P:** ¿Qué ganas al empaquetar el pipeline? ¿Qué hace la línea `act1-demo =
"act1_pipeline.cli:main"`?
**R:** Que cualquiera lo instale con `pip install .` y lo corra con un comando, con las
dependencias y el CSV incluidos, obteniendo el mismo resultado (0.724). Esa línea de
`[project.scripts]` le dice a pip que cree un ejecutable `act1-demo` que llama a la función
`main()` del módulo `act1_pipeline.cli`.

**P:** ¿Qué es el `src/` layout y por qué se recomienda?
**R:** Poner el paquete dentro de `src/`. Así no se puede importar "por accidente" desde la carpeta
del repo: hay que instalarlo, y se prueba exactamente lo que recibirá otro usuario.

**P:** ¿Es bueno un accuracy de 0.724 aquí?
**R:** Supera al baseline de 0.483 (siempre "gana el local"), así que cumple el criterio. Pero con
29 partidos de test el margen de error es grande, y el recall de empates es 0.200.

## 🏋️ Ejercicios

1. **Otro modelo, mismo pipeline:** usa `construir_pipeline(LogisticRegression(max_iter=2000,
   class_weight="balanced"))`. ¿Sube el recall de `Draw`? ¿Qué pasa con el accuracy?
2. **Fuga en la imputación:** rellena los nulos de `home_saves_pct` con la mediana de los 144
   partidos antes de partir y compara con hacerlo dentro del pipeline. ¿Cambia la mediana?
   ¿Cambia la métrica? Explica por qué casi no se nota aquí.
3. **Transformador nuevo:** escribe `DiferenciaPosesion(BaseEstimator, TransformerMixin)` que
   reciba las dos columnas de posesión y devuelva una sola: local − visitante. Con su
   `get_feature_names_out`. Mételo en el pipeline en lugar de la rama `porcentajes`.
4. **Empaqueta tu versión:** crea una carpeta con `src/mi_pipeline/` (con `TextoANumero`,
   `construir_pipeline` y una `main()`), copia `ejemplos/pyproject.toml` ajustando el nombre y
   el entry point, haz `pip install .` en un entorno virtual nuevo y corre tu comando.
5. **Sin equipos:** quita la rama `categoricas` y compara accuracy. ¿Las 72 columnas de equipos
   ayudaban o estorbaban?

## 🔗 Referencias

- Repo original: [DiegoLinares11/Actividad1-MLOPS](https://github.com/DiegoLinares11/Actividad1-MLOPS)
- scikit-learn. [Pipelines and composite estimators](https://scikit-learn.org/stable/modules/compose.html)
- scikit-learn. [Common pitfalls: data leakage](https://scikit-learn.org/stable/common_pitfalls.html)
- scikit-learn. [Preprocessing data](https://scikit-learn.org/stable/modules/preprocessing.html) ·
  [Imputation](https://scikit-learn.org/stable/modules/impute.html)
- scikit-learn. [Developing scikit-learn estimators](https://scikit-learn.org/stable/developers/develop.html)
- scikit-learn. [set_output API](https://scikit-learn.org/stable/auto_examples/miscellaneous/plot_set_output.html)
- Python Packaging User Guide. [Writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) ·
  [src layout vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
