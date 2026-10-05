# 06 · Calibración de hiperparámetros con pipelines

🎬 Video: `hiperparametros\hiperparametros-es.mp4` (también en inglés: `-en.mp4`, y hojas de revisión `revision-es.png`).

## 🧱 Conocimiento previo

### 1. El pipeline del tema 05

Ya tenemos un `Pipeline` que recibe las 12 columnas crudas de un partido, las convierte en 86
columnas numéricas (`ColumnTransformer`) y entrena un clasificador. En este tema le agregamos un
paso `SelectKBest` y nos preguntamos: **¿con qué configuración funciona mejor?**

### 2. Sobreajuste en una línea

Un modelo **sobreajusta** cuando memoriza los datos de entrenamiento en lugar de aprender el
patrón: le va excelente en train y mal en datos nuevos. Ejemplo: un bosque sin límite de
profundidad con 115 partidos saca 1.000 en train y ~0.55 en validación. (Tema 02.)

### 3. Validación cruzada (k-fold)

Partir una sola vez en train/validación depende de la suerte del corte. La **validación
cruzada** parte el train en *k* bloques (folds); entrena *k* veces, cada vez dejando un bloque
afuera para validar, y promedia los *k* puntajes.

```
fold 1: [VAL][ tr ][ tr ][ tr ][ tr ]
fold 2: [ tr ][VAL][ tr ][ tr ][ tr ]
...                                    -> promedio de 5 puntajes
fold 5: [ tr ][ tr ][ tr ][ tr ][VAL]
```

**Estratificada** (`StratifiedKFold`) = cada fold conserva la proporción de clases. Con solo 20
empates en train, un fold sin estratificar podría quedarse casi sin empates.

### 4. Precisión, recall y F1 (para entender `f1_macro`)

Para una clase, por ejemplo `Draw`:

- **precision** = de los que predije como empate, ¿cuántos lo eran?
- **recall** = de los empates reales, ¿cuántos detecté?
- **F1** = media armónica de las dos (castiga si una es muy baja).

`f1_macro` = calcula el F1 de **cada clase** y los promedia **sin ponderar** por tamaño.

### 5. Tres conjuntos con tres trabajos distintos

| Conjunto | Para qué | Cuántas veces se usa |
|---|---|---|
| **train** (folds de entrenamiento) | aprender parámetros | muchas |
| **validación** (fold que se deja afuera en CV) | elegir hiperparámetros | muchas |
| **test** | estimar el desempeño final | **una** |

## 🎯 Qué tienes que saber

### 1. Parámetros vs hiperparámetros

| | Parámetro | Hiperparámetro |
|---|---|---|
| ¿Quién lo fija? | el modelo, en `fit` | tú, **antes** de `fit` |
| Ejemplos | `coef_` de la regresión logística, los cortes de un árbol, `mean_` del escalador | `C`, `max_depth`, `n_estimators`, `class_weight`, `k` de `SelectKBest`, `strategy` del imputador |
| ¿Cómo se elige? | optimización sobre train | **búsqueda + validación cruzada** |

**Analogía:** en una receta, la temperatura y el tiempo del horno son hiperparámetros (los
eliges tú); cómo queda el pastel por dentro son los parámetros (salen del horneado). En el
notebook, el mismo dato con `C=0.01` da coeficientes ≈ 0.05 y con `C=100` da ≈ 1.3.

¿Por qué no elegir el hiperparámetro mirando el train? Porque el train siempre "prefiere" la
configuración que más memoriza (árbol infinito, `C` enorme). Se elige con datos que el modelo
no vio: la validación.

### 2. La sintaxis `paso__parametro`

En un `Pipeline` cada hiperparámetro se nombra con **doble guion bajo**:

```
modelo__max_depth                                  paso "modelo"      -> max_depth
seleccion__k                                       paso "seleccion"   -> k
preprocesamiento__numericas__imputar__strategy     ColumnTransformer -> rama -> paso -> strategy
modelo                                             ¡el paso completo! se puede reemplazar por otro modelo
```

`pipe.get_params().keys()` lista todas las llaves válidas (106 en nuestro pipeline) y
`pipe.set_params(seleccion__k=15)` las cambia. Esto es lo que hace que la búsqueda calibre
**juntos** el preprocesamiento y el modelo, y que reajuste **todo** el preprocesamiento dentro de
cada fold (sin fuga).

### 3. Por qué `f1_macro` y no `accuracy`

Las clases están desbalanceadas (Home Win 71, Away Win 48, Draw 25). Un modelo que **siempre**
dice "gana el local":

| Métrica | Modelo tonto (CV en train) |
|---|---|
| accuracy | 0.496 |
| f1_macro | 0.221 |

El accuracy lo hace parecer decente; `f1_macro` lo delata, porque el F1 de `Draw` y de
`Away Win` es 0. Optimizar `f1_macro` obliga al modelo a tomarse en serio los empates. En la
Actividad 3 concluimos que **la métrica es una decisión de negocio, no un detalle técnico**: con
`accuracy` la búsqueda se queda con un modelo que casi nunca predice empate.

### 4. Los tres objetos de búsqueda

| | `GridSearchCV` | `RandomizedSearchCV` | `HalvingGridSearchCV` |
|---|---|---|---|
| Qué prueba | **todas** las combinaciones de la rejilla | `n_iter` combinaciones **muestreadas** | todas al inicio, eliminando por rondas |
| Espacio | listas de valores | listas **o distribuciones** (`scipy.stats`) | listas |
| Costo | crece multiplicando (2×3×2×2×2×2 = 96) | lo fijas tú con `n_iter` | menos ajustes "completos" |
| Ventaja | exhaustivo, reproducible | cubre espacios enormes; compara **familias de modelos** | descarta temprano lo malo |
| Riesgo | caro; encerrado en el vecindario que definiste | puede no muestrear justo el óptimo | rondas iniciales con pocos datos = ruidosas |
| Import | `sklearn.model_selection` | `sklearn.model_selection` | **experimental**: primero `from sklearn.experimental import enable_halving_search_cv` |

**`GridSearchCV`** — exhaustivo:

```python
rejilla = {"seleccion__k": [15, 30, "all"], "modelo__max_depth": [None, 6],
           "modelo__min_samples_leaf": [1, 3], "modelo__class_weight": [None, "balanced"]}
GridSearchCV(pipe, rejilla, scoring="f1_macro", cv=StratifiedKFold(5, shuffle=True, random_state=42),
             n_jobs=-1, refit=True, return_train_score=True)
```

**`RandomizedSearchCV`** — distribuciones y familias:

```python
from scipy.stats import loguniform, randint, uniform
espacio = [
    {"modelo": [LogisticRegression(max_iter=5000)], "modelo__C": loguniform(1e-3, 1e2),
     "modelo__class_weight": [None, "balanced"], "seleccion__k": [10, 20, 40, "all"]},
    {"modelo": [RandomForestClassifier()], "modelo__n_estimators": randint(100, 600), ...},
    ...
]
RandomizedSearchCV(pipe, espacio, n_iter=60, random_state=42, ...)
```

| Distribución | Da | Úsala cuando |
|---|---|---|
| `loguniform(a, b)` | decimales uniformes en escala **logarítmica** | el valor bueno puede estar en 0.001 o en 50 (`C`, `gamma`, `alpha`) |
| `randint(a, b)` | enteros en `[a, b)` | `n_estimators`, `min_samples_leaf` |
| `uniform(loc, scale)` | decimales en `[loc, loc + scale]` | `learning_rate` entre 0.02 y 0.30 |

Una **lista de diccionarios** = varios espacios: la búsqueda elige uno al azar y muestrea dentro.
Como `modelo` es un paso más, se puede sustituir entero → comparar cuatro familias en **una sola
búsqueda** con la misma CV.

**`HalvingGridSearchCV`** — *successive halving*, como un torneo con eliminatorias: en la ronda
1 juegan **todos** los candidatos con pocos datos (`resource="n_samples"`); solo el mejor
`1/factor` (con `factor=3`, un tercio) pasa a la siguiente ronda con más datos. El mínimo de
datos por ronda es `2 × n_splits × n_clases` = 2 × 5 × 3 = **30** partidos. En la Actividad 3:
96 → 32 candidatos con 30 → 90 partidos.

Ojo: halving ahorra cuando entrenar cuesta proporcional a los datos. Con 115 filas el costo es
casi fijo, así que **no ahorró tiempo** (60.3 s contra 55.7 s de la rejilla en la Actividad 3;
lo mismo en el notebook). Y su `best_score_` se mide con los datos de la última ronda (90, no
115), así que no es directamente comparable.

### 5. `SelectKBest` dentro del pipeline

`SelectKBest(f_classif, k=...)` se queda con las *k* columnas más relacionadas con `result`
(test F de ANOVA). ¿Por qué aquí? 72 de las 86 columnas son el One-Hot de los equipos (cada
equipo aparece ~6–8 veces): casi ruido. Con 115 filas, 86 columnas invitan al sobreajuste.

Dos claves:

- `k` es un hiperparámetro del **preprocesamiento**, y aun así se calibra en la **misma**
  búsqueda que el modelo, porque interactúan (cuántas variables conviene depende del modelo).
- Tiene que ir **dentro** del pipeline. Seleccionar con los 144 partidos antes de validar es
  fuga: en el tema 05 eso convirtió 2 000 columnas de ruido puro en un modelo de 0.750.

### 6. Lo que deja la búsqueda: `refit`, `best_estimator_`, `cv_results_`

| Atributo | Qué es |
|---|---|
| `best_params_` | el diccionario de hiperparámetros ganador |
| `best_score_` | el puntaje medio de CV de ese ganador (**optimista**, ver abajo) |
| `best_estimator_` | con `refit=True`: el pipeline ganador **reentrenado con todo el train**, listo para `predict` |
| `cv_results_` | diccionario con una fila por combinación: `mean_test_score`, `std_test_score`, `rank_test_score`, `mean_train_score` (si `return_train_score=True`), `params`, tiempos |

Leer `cv_results_` como DataFrame ordenado por `rank_test_score` responde tres preguntas:

1. **¿Quién ganó y por cuánto?** Si la diferencia entre el 1.º y el 5.º es menor que
   `std_test_score`, es empate técnico.
2. **¿Hay sobreajuste?** `mean_train_score − mean_test_score` grande = memoriza (en el notebook,
   con `min_samples_leaf=1` el train llega a 0.994–1.000 y la brecha a 0.43–0.45).
3. **¿Qué perilla importa?** Agrupar `mean_test_score` por cada valor: en la Actividad 3,
   `class_weight="balanced"` (0.524 vs 0.515) y recortar `k` (30 → 0.525, `all` → 0.509)
   ayudaban; `n_estimators` e imputación **no importaban**. Saber qué no importa permite fijarlo
   en el valor barato **con evidencia**.

Qué **no** se calibra: `handle_unknown="ignore"` (requisito, no perilla), la métrica y el
esquema de CV (calibrarlos sería elegir la vara con la que uno mismo se mide) y
`random_state=42` (reproducibilidad).

### 7. Sobreajuste a la validación y por qué el test se usa una sola vez

`best_score_` es el **máximo** de muchos intentos sobre las **mismas** particiones. El máximo de
muchos números ruidosos sale alto por suerte. Experimento del notebook con 100 "modelos" que
adivinan al azar:

| | f1_macro |
|---|---|
| promedio de los 100 adivinos en CV | 0.317 |
| `best_score_` del adivino "ganador" | 0.447 |
| ese mismo adivino en test | **0.109** |

Consecuencias prácticas:

1. Se elige el ganador por CV, **nunca** mirando el test.
2. El test se evalúa **una sola vez**, al final. Si comparas tres finalistas en test y te quedas
   con el mejor, el test se volvió validación y su número ya no es honesto.
3. `best_score_` no se reporta como desempeño. Para estimar el **procedimiento completo**
   (buscar + entrenar) se usa **validación cruzada anidada**: la búsqueda se repite dentro de
   cada fold externo. En la Actividad 3: CV anidada **0.541** contra `best_score_` **0.563**.

## 📂 Qué hicimos en el curso

**Actividad 3 · Calibración de hiperparámetros con pipelines de scikit-learn**. Repo:
[DiegoLinares11/Actividad3-MLOPS](https://github.com/DiegoLinares11/Actividad3-MLOPS)
(paquete `act3_pipeline`, comando `act3-demo`, pruebas con `pytest`). Mismo dataset y mismo
pipeline de preparación de la Actividad 1; lo nuevo son las etapas **Modeling** y **Evaluation**
de CRISP-DM (y Deployment como paquete instalable).

Pipeline: `ColumnTransformer` (4 ramas) → `SelectKBest` → clasificador. CV:
`StratifiedKFold(5, shuffle=True, random_state=42)`, métrica `f1_macro`. Datos: 144 partidos →
115 train / 29 test.

| Objeto | Combinaciones | Tiempo (`act3-demo`) | Mejor `f1_macro` en CV |
|---|---|---|---|
| Sin calibrar (valores por defecto) | 1 | — | 0.508 (± 0.037) |
| `GridSearchCV` (Random Forest, 2×3×2×2×2×2) | 96 | 55.7 s | 0.563 |
| **`RandomizedSearchCV`** (4 familias) | **60** | **17.0 s** | **0.619** |
| `HalvingGridSearchCV` (misma rejilla) | 128 | 60.3 s | 0.594 |

(En la corrida del notebook los tiempos fueron 57.5 s, 14.8 s y 64.2 s: los segundos cambian
entre corridas; los puntajes no.)

La búsqueda aleatoria **ganó en menos de un tercio del tiempo** porque pudo salir del vecindario
del Random Forest:

| Familia | Intentos | Mejor `f1_macro` CV |
|---|---|---|
| LogisticRegression | 15 | **0.619** |
| SVC | 18 | 0.612 |
| HistGradientBoosting | 11 | 0.561 |
| RandomForest | 16 | 0.556 |

Modelo final: `LogisticRegression(C=0.541, class_weight="balanced", max_iter=5000)` con
`SelectKBest(k=40)` e imputación por mediana, elegido por CV.

| Medición | accuracy | `f1_macro` |
|---|---|---|
| Baseline (clase mayoritaria), test | 0.483 | 0.217 |
| Pipeline sin calibrar, CV | — | 0.508 |
| `GridSearchCV` `best_score_`, CV | — | 0.563 |
| `RandomizedSearchCV` `best_score_`, CV | — | 0.619 |
| **CV anidada (estimación honesta)** | — | **0.541** |
| **Modelo final, test reservado** | **0.690** | **0.631** |

Por clase en test: Away Win f1 0.833 (recall 1.000), Draw 0.364, Home Win 0.696. Otras
conclusiones: la curva de aprendizaje se aplana desde ~66 partidos (el techo lo ponen las
variables, no la cantidad de datos); la importancia por permutación deja a `home_team` y
`away_team` en ~0 (el modelo decide por tiros a puerta y atajadas); y la CV acertó el orden: el
ganador en CV también fue el mejor en test (0.631 contra 0.605 y 0.562).

## 🧪 Práctica

`repaso.ipynb` calibra el pipeline de la Champions con los tres objetos, con tiempos reales y en
menos de un minuto (rejillas más chicas que las originales). Números de la corrida guardada:

| Objeto | Combinaciones | Ajustes | Tiempo aprox. | Mejor `f1_macro` CV |
|---|---|---|---|---|
| Sin calibrar | 1 | 5 | — | 0.508 |
| `GridSearchCV` (RF, 3×2×2×2) | 24 | 120 | ~12 s | 0.562 |
| `RandomizedSearchCV` (4 familias, `n_iter=40`) | 40 | 200 | ~11 s | **0.687** (SVC lineal) |
| `HalvingGridSearchCV` (misma rejilla) | 32 (24 + 8) | 160 | ~15 s | 0.615 (medido con 90 partidos) |

- El pipeline sin calibrar reproduce el **0.508 ± 0.037** de la actividad, fold por fold.
- `cv_results_` ordenado con la brecha train − validación (0.35 a 0.45) y el efecto promedio de
  cada hiperparámetro (`class_weight="balanced"` 0.549 vs 0.516).
- Por familia: SVC 0.687 (pero media 0.379), LogisticRegression 0.601, HistGradientBoosting
  0.594, RandomForest 0.579. Igual que en la actividad, gana un modelo lineal regularizado.
- Modelo final en test (una sola vez): **accuracy 0.690, `f1_macro` 0.631** (los mismos números
  del modelo final original), contra 0.483 / 0.217 del baseline.
- Sobreajuste a la validación: 100 adivinos al azar (0.317 promedio, 0.447 el "mejor", 0.109 en
  test) y una CV anidada rápida (0.605 vs `best_score_` 0.608).

```powershell
python tools/build_nb.py 06-hiperparametros/repaso.py   # ~1 minuto con 4 núcleos
```

## ❓ Preguntas tipo examen

**P:** ¿Cuál es la diferencia entre un parámetro y un hiperparámetro? Da un ejemplo de cada uno.
**R:** El parámetro se aprende en `fit` (los coeficientes `coef_` de una regresión logística); el
hiperparámetro se fija antes de entrenar (`C`, `max_depth`, `k`) y se elige con validación.

**P:** En un pipeline con pasos `preprocesamiento`, `seleccion` y `modelo`, ¿cómo se escribe la
llave para calibrar la estrategia del imputador de la rama `numericas`?
**R:** `preprocesamiento__numericas__imputar__strategy` (paso → rama del ColumnTransformer → paso
del sub-pipeline → hiperparámetro, separados por doble guion bajo).

**P:** ¿Por qué optimizar `f1_macro` y no `accuracy` en este problema?
**R:** Las clases están desbalanceadas (71/48/25). Un modelo que siempre predice "Home Win" saca
~0.50 de accuracy pero 0.22 de `f1_macro`. `f1_macro` promedia el F1 de cada clase sin ponderar,
así que no se puede ganar ignorando los empates.

**P:** ¿Por qué `StratifiedKFold` y no `KFold`?
**R:** Para que cada fold conserve la proporción de clases; con 20 empates en train, un `KFold`
podría dejar folds casi sin empates y el F1 de esa clase sería inestable.

**P:** ¿Cuántos modelos entrena un `GridSearchCV` con una rejilla 2×3×2×2×2×2 y 5 folds (más el
refit)?
**R:** 96 combinaciones × 5 folds = 480 ajustes, más 1 de `refit` con todo el train = 481.

**P:** ¿Qué ventajas tiene `RandomizedSearchCV` sobre `GridSearchCV`?
**R:** El costo lo fijas con `n_iter`, puede muestrear distribuciones continuas (`loguniform` para
`C`) y cubrir espacios enormes, y con una lista de diccionarios puede comparar familias de
modelos distintas en una sola búsqueda. En la Actividad 3 ganó (0.619 vs 0.563) en menos de un
tercio del tiempo.

**P:** ¿Por qué `loguniform(1e-3, 1e2)` para `C` y no `uniform`?
**R:** Porque `C` importa en órdenes de magnitud. Con `uniform(0.001, 100)` casi todas las muestras
caerían entre 1 y 100 y casi nunca se probaría 0.01; `loguniform` reparte parejo entre 0.001–0.01,
0.01–0.1, etc.

**P:** ¿Cómo funciona `HalvingGridSearchCV` y qué hay que importar para usarlo?
**R:** Evalúa todos los candidatos con pocos datos, conserva el mejor `1/factor` y les da más datos
en la siguiente ronda, hasta quedarse con el mejor. Es experimental: hay que hacer
`from sklearn.experimental import enable_halving_search_cv` antes de importar
`HalvingGridSearchCV` desde `sklearn.model_selection`.

**P:** ¿Por qué `HalvingGridSearchCV` no ahorró tiempo en la Actividad 3?
**R:** Porque ahorra cuando entrenar cuesta proporcional a los datos; con 115 filas entrenar con 30
o con 90 cuesta casi lo mismo, y además evaluó 128 veces (96 + 32) en vez de 96.

**P:** ¿Qué hace `refit=True` y dónde queda el resultado?
**R:** Al terminar la búsqueda reentrena el pipeline con los mejores hiperparámetros usando **todo**
el train, y lo deja en `best_estimator_`, listo para `predict`.

**P:** ¿Qué columnas de `cv_results_` revisas para detectar sobreajuste y para saber si el ganador
es claramente mejor?
**R:** Sobreajuste: `mean_train_score` vs `mean_test_score` (brecha grande). Ganador claro: la
diferencia de `mean_test_score` con los siguientes comparada con `std_test_score`.

**P:** ¿Por qué `SelectKBest` va dentro del pipeline y no antes?
**R:** Porque elegir columnas mirando todos los datos filtra información de validación/test
(fuga). Dentro del pipeline se reajusta en cada fold, y además su `k` se calibra junto al modelo.

**P:** ¿Por qué `best_score_` es optimista y qué número se reporta en su lugar?
**R:** Porque es el máximo de muchos intentos sobre las mismas particiones (se "sobreajusta a la
validación"). Se reporta el desempeño en el test reservado, evaluado una sola vez, y como
estimación del procedimiento la CV anidada (0.541 contra 0.563 en la Actividad 3).

**P:** ¿Por qué el test se usa una sola vez?
**R:** Si se usa para elegir entre modelos o ajustar algo, se convierte en otro conjunto de
validación y deja de ser una estimación independiente de cómo se comportará el modelo con datos
nuevos.

**P:** En la Actividad 3 la búsqueda aleatoria eligió una regresión logística en vez de un bosque.
¿Qué lección deja?
**R:** Con datasets chicos (115 filas, 86 columnas) el modelo más simple y regularizado suele ser el
correcto, y esa conclusión solo aparece si se deja competir a varias familias en la misma
búsqueda.

## 🏋️ Ejercicios

1. **Cambia la métrica:** corre la `RandomizedSearchCV` del notebook con `scoring="accuracy"`.
   ¿Qué familia gana? ¿Cuál es el recall de `Draw` del ganador en test comparado con el de
   `f1_macro`?
2. **Rejilla vs aleatoria con el mismo presupuesto:** con el espacio de Random Forest, compara un
   `GridSearchCV` de 24 combinaciones contra un `RandomizedSearchCV` con `n_iter=24` y
   distribuciones (`randint` para `n_estimators` y `min_samples_leaf`). ¿Cuál encuentra mejor
   `best_score_`?
3. **Calibra el imputador:** agrega `preprocesamiento__numericas__imputar__strategy: ["median",
   "mean"]` a la rejilla. Usa el análisis de efecto por valor para demostrar si importa o no.
4. **Halving con más recursos:** prueba `HalvingGridSearchCV` con `factor=2` y con
   `min_resources=60`. ¿Cuántas rondas hace? ¿Elige lo mismo que la rejilla completa?
5. **CV anidada del ganador:** envuelve la `RandomizedSearchCV` (con `n_iter=15`) en
   `cross_val_score` y compara la estimación anidada con su `best_score_`. ¿Cuánto optimismo
   había?

## 🔗 Referencias

- Repo original: [DiegoLinares11/Actividad3-MLOPS](https://github.com/DiegoLinares11/Actividad3-MLOPS)
- Base de la Actividad 3: [DiegoLinares11/Actividad1-MLOPS](https://github.com/DiegoLinares11/Actividad1-MLOPS)
- scikit-learn. [Tuning the hyper-parameters of an estimator](https://scikit-learn.org/stable/modules/grid_search.html)
  (incluye *successive halving*)
- scikit-learn. [Cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html)
- scikit-learn. [Nested versus non-nested cross-validation](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html)
- scikit-learn. [Metrics: precision, recall and F-measures](https://scikit-learn.org/stable/modules/model_evaluation.html#precision-recall-f-measure-metrics)
- SciPy. [scipy.stats.loguniform](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.loguniform.html)
- Bergstra & Bengio (2012). [Random Search for Hyper-Parameter Optimization](https://www.jmlr.org/papers/v13/bergstra12a.html)
