# 15 · MLflow: seguimiento de experimentos y registro de modelos

🎬 Video: [▶️ en español](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/15-mlflow-es.mp4) · [▶️ in English](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/15-mlflow-en.mp4) · [todos los videos](https://github.com/DiegoLinares11/RepasoMLOps/releases/tag/videos)

## 🧱 Conocimiento previo

### 1. Qué es un experimento en Machine Learning

Entrenar un modelo casi nunca es una sola corrida. Se prueban familias de modelos, hiperparámetros,
variables y formas de validar (temas 02 y 06). Cada prueba es un **experimento**, y al final hay que
poder contestar: ¿cuál fue el mejor, con qué parámetros y con qué datos?

Sin una herramienta, la respuesta vive en la memoria o en las salidas de un notebook, que se
sobrescriben cada vez que lo vuelves a correr. Es como hacer pruebas de laboratorio sin bitácora.

### 2. Parámetros, métricas y validación (repaso de los temas 02 y 06)

| Concepto | Qué es | Ejemplo del curso |
|---|---|---|
| Hiperparámetro | Lo que decides antes de entrenar | `max_depth=6` en un bosque |
| Métrica | El número con que mides el resultado | F1 macro, RMSE, R² |
| Validación cruzada | Promedio de la métrica en varias particiones del entrenamiento | `best_cv_score` |
| Conjunto de prueba | Datos que el modelo nunca vio | `f1_score_X_test` |

Una métrica calculada sobre los datos de **entrenamiento** siempre se ve mejor de lo que es (tema 02:
sobreajuste).

### 3. Guardar un modelo en un archivo

Un modelo entrenado es un objeto de Python; para usarlo después hay que **serializarlo** (temas 05 y
09). `pickle` y `joblib` guardan cualquier objeto, pero al cargarlos pueden **ejecutar código**: un
archivo malicioso puede hacer lo que quiera en tu máquina. `skops` es un formato pensado para
scikit-learn que solo reconstruye los tipos que tú declaras como confiables.

### 4. Cliente y servidor (repaso del tema 09)

MLflow funciona como una API del tema 09: un **servidor** guarda la información en una base de datos
(SQLite, PostgreSQL...) y en una carpeta de archivos, y tu código es el **cliente** que le manda cada
dato. La interfaz web es otro cliente del mismo servidor.

## 🎯 Qué tienes que saber

### 1. Las piezas de MLflow

| Pieza | Qué hace | Analogía |
|---|---|---|
| **Tracking** | Guarda cada entrenamiento (*run*) con sus parámetros, métricas, archivos y modelo | La bitácora del laboratorio |
| **Models** | Un formato estándar para guardar el modelo con sus dependencias y su firma | La caja con instructivo |
| **Model Registry** | Versiones de un modelo con nombre y alias (`@campeon`) | El estante de "lo que está a la venta" |
| **Projects** | Un archivo `MLproject` con *entry points*, parámetros y ambiente | La receta para repetir el experimento |

### 2. Experimentos, runs y lo que guardan

- Un **experimento** agrupa los runs de un mismo problema (`Champions_Resultado`).
- Un **run** es una corrida y guarda:
  - **parámetros**, que MLflow guarda como **texto**;
  - **métricas**, que guarda como **números** y pueden tener historial por paso;
  - **tags**, etiquetas para buscar y filtrar;
  - **artefactos**, archivos como gráficas, CSV o el modelo;
  - **datasets**, con `mlflow.data`.
- Un run puede tener **runs hijos**: por ejemplo, uno por familia de modelo o por combinación de una
  búsqueda.

```python
import mlflow

mlflow.set_tracking_uri("http://127.0.0.1:8080")   # o "sqlite:///mlflow.db" sin servidor
mlflow.set_experiment("Champions_Resultado")
with mlflow.start_run(run_name="svc"):
    mlflow.log_params({"C": 0.18, "kernel": "linear"})
    mlflow.log_metrics({"test_f1_macro": 0.601})
    mlflow.log_figure(figura, "evaluacion/matriz_confusion.png")
```

### 3. Tres formas de hablar con MLflow

| API | Cómo se ve | Para qué |
|---|---|---|
| *Fluent* | `mlflow.start_run()`, `mlflow.log_metrics()` | Lo normal en notebooks y scripts: hay un run activo |
| `MlflowClient` | `client.search_experiments()`, `client.set_registered_model_alias()` | Operaciones puntuales sobre cualquier run o modelo |
| **Autolog** | `mlflow.sklearn.autolog()` | Registro automático de cada `fit` sin escribir `log_*` |

### 4. Autolog con una búsqueda de hiperparámetros: dónde queda cada cosa

Con `RandomizedSearchCV` o `GridSearchCV`, el autolog crea:

| Run | Parámetros | Métricas |
|---|---|---|
| **Padre** | Los de la búsqueda (`cv`, `n_iter`, `estimator`...) y los mejores (`best_*`): 17 en el Taller 3 | `training_*` (sobre **entrenamiento**), `best_cv_score` |
| **Hijos** (5 por defecto, `max_tuning_runs`) | Todo el pipeline con `get_params(deep=True)`: 106 en el Taller 3 | Las de la validación cruzada de esa combinación |

Tres detalles que confunden:

1. Las `training_*` del padre se ven casi perfectas (F1 0.974 en el taller) porque son de
   entrenamiento. La de prueba (0.536) solo aparece si calculas una métrica dentro del run.
2. El autolog **reemplaza** las funciones de `sklearn.metrics` al activarse. Si antes hiciste
   `from sklearn.metrics import f1_score`, ese nombre apunta a la función original y la métrica no
   se registra. Llama a `metrics.f1_score` o importa después de `autolog()`.
3. Guarda el modelo con **cloudpickle**, mientras que `log_model` usa skops.

### 5. El modelo: formato, firma y código

`mlflow.sklearn.log_model(modelo, name="modelo", ...)` guarda el modelo con:

- La **firma** (`signature`): las columnas de entrada con su tipo y la salida. Se infiere con
  `infer_signature(X, pred)` o con un `input_example`.
- Las **dependencias** (`requirements.txt` y `conda.yaml` generados).
- Con `code_paths`, **tu propio código** (por ejemplo, transformadores personalizados), para cargarlo
  en una máquina que no tenga instalado tu paquete.
- El **formato**: desde MLflow 3, fuera de Databricks, es **skops**. Hay que listar en
  `skops_trusted_types` los tipos que skops no conoce (`sklearn.tree._tree.Tree`, `numpy.dtype`, tus
  clases...). Si falta uno, `log_model` se niega a guardar.

### 6. Model Registry: versiones y alias

```python
version = mlflow.register_model(model_uri, "champions-resultado").version   # v1, v2, v3...
MlflowClient().set_registered_model_alias("champions-resultado", "campeon", version)
modelo = mlflow.sklearn.load_model("models:/champions-resultado@campeon")
```

Producción siempre carga `models:/champions-resultado@campeon`. Para cambiar de modelo, o regresar al
anterior (*rollback*), solo se mueve el alias: el código que carga no cambia.

### 7. MLflow Projects

Un archivo `MLproject` en la raíz del repo declara *entry points* (como los del tema 13) con
parámetros tipados y el ambiente en que corren:

```yaml
name: taller3-champions
conda_env: environment.yml
entry_points:
  main:
    parameters:
      familia: {type: string, default: todas}
    command: "taller3-entrenar --familia {familia}"
```

`mlflow run . -P familia=svc --env-manager local` corre ese comando dentro de un run, y MLflow le
pone origen `PROJECT`. Sin `--env-manager local` crea un ambiente nuevo a partir de `conda_env`.

### 8. La lección del tutorial: validar en el tiempo

El tutorial de MLflow valida dividiendo los días **al azar**. En una serie de tiempo eso deja que el
modelo vea días posteriores a los que valida y hace ver bien a un modelo que no sabe extrapolar la
tendencia. Lo honesto es entrenar con el pasado y validar con el **futuro**. Con MLflow, comparar las
dos formas fue cuestión de registrar las 16 combinaciones y mirarlas lado a lado.

## 📂 Qué hicimos en el curso

**Taller 3** ([repo MLFlow](https://github.com/DiegoLinares11/MLFlow), MLflow 3.17.1):

1. **Tres páginas de la documentación:**
   - *Projects*, que se conecta con los entry points del tema 13 y los ambientes del tema 07.
   - *Model Registry*.
   - *Dataset Tracking*, que complementa a DVC.
2. **Tutorial *Your First MLflow Model* en Jupyter.** Para que corriera con las versiones actuales
   hubo que hacer tres cambios: `fillna(method=)` ya no existe en pandas 3, en MLflow 3 el nombre va
   en `name=` y hay que declarar `skops_trusted_types`. El primer run dio RMSE 60.1 y R² 0.885.
3. **Análisis del generador sintético:**
   - La cosecha siempre vale 0: `sin(x) + sin(x − π) = 0`.
   - Con la misma semilla, generarlo un día después cambia la demanda del **30 %** de las filas.
   - Temperatura, lluvia y feriados no influyen en la demanda.
   - La inflación sube por escalones cada año.
   - La primera fila copia su propia demanda.
   - La versión corregida es 5.3 veces más rápida.
4. **Mejoras al modelo** (16 runs). RMSE con validación **en el tiempo**:

   | Modelo | Datos del tutorial | Datos corregidos |
   |---|---:|---:|
   | Bosque del tutorial | 199.6 | 205.9 |
   | Bosque + fecha | 102.1 | 132.3 |
   | Boosting + fecha | 96.4 | 96.7 |
   | **Lineal (Ridge) + fecha** | **77.3** | **79.1** |
   | Piso de ruido | 67.9 | 68.5 |

   Al azar, el bosque del tutorial tenía R² 0.754; en el tiempo, 0.294.
5. **MLflow con el pipeline de la Champions** (el de la Actividad 9):
   - **Autolog:** el run padre tuvo 17 parámetros y cada hijo 106; el F1 fue 0.974 en entrenamiento
     y 0.536 en prueba.
   - **Registro manual de las cuatro familias:** la **SVC** ganó con F1 macro 0.638 en validación
     cruzada y 0.601 en prueba (accuracy 0.655), contra 0.217 de la referencia "siempre gana el local".
   - Quedó registrada como `champions-resultado` v1 con el alias `@campeon`.
   - El mismo entrenamiento corrió con `mlflow run`.

## 🧪 Práctica

**`repaso.ipynb`** (ya ejecutado, sin MLflow ni internet, corre en un minuto):

1. Un **mini MLflow** de unas 40 líneas (`start_run`, `log_params`, `log_metrics`, `set_tags`,
   `search_runs`) para ver qué guarda un run. Con dos runs del tutorial: RMSE 60.2 con `max_depth=6`
   y 62.1 con 12.
2. El **generador del tutorial** (`ejemplos/manzanas.py`, el archivo real del taller):
   - La cosecha vale cero en todo el año.
   - Generarlo "mañana" cambia 296 de 1,000 filas.
   - La versión corregida da siempre los mismos datos.
3. **Al azar contra en el tiempo**: los 16 runs registrados en el mini MLflow, con los mismos números
   del taller.
4. **Lo que guarda el autolog** con una búsqueda sobre la Champions:
   - El padre tiene 16 parámetros y cada hijo 107.
   - El F1 es 0.978 en entrenamiento, 0.594 en validación cruzada y 0.591 en prueba.
5. Un **Model Registry en miniatura**: el alias `@campeon` pasa de la versión 1 (bosque, F1 0.591)
   a la 2 (logística, 0.497) sin cambiar el código que carga.

**`ejemplos/`**, con MLflow de verdad:

| Archivo | Qué ver |
|---|---|
| `mlflow_minimo.py` | **Corre en tu compu** (`pip install mlflow`): run manual con dataset, autolog sobre una búsqueda y Model Registry con alias, en una base SQLite local |
| `seguimiento.py` | El registro manual real del taller: parámetros, métricas, `mlflow.data`, matriz de confusión, `code_paths` y `skops_trusted_types` |
| `manzanas.py` | El generador del tutorial (con su único cambio para pandas 3) y la versión corregida |
| `MLproject` | Los entry points `main` y `registrar` para `mlflow run` |

Para ver la interfaz después de correr `mlflow_minimo.py`:

```bash
cd 15-mlflow/ejemplos
pip install mlflow
python mlflow_minimo.py
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

## ❓ Preguntas tipo examen

**P:** ¿Qué problema resuelve el Tracking de MLflow?
**R:** Guarda cada entrenamiento con sus parámetros, métricas, archivos y modelo, para comparar y
reproducir experimentos sin depender de la memoria ni de salidas de notebooks que se sobrescriben.

**P:** ¿Qué diferencia hay entre un experimento y un run?
**R:** El experimento agrupa los runs de un mismo problema; el run es una corrida concreta con sus
parámetros, métricas, tags y artefactos.

**P:** ¿Por qué MLflow guarda los parámetros como texto y las métricas como números?
**R:** Los parámetros pueden ser de cualquier tipo (`None`, `"balanced"`, un objeto) y solo se
comparan o filtran; las métricas se grafican, se ordenan y pueden tener historial por paso.

**P:** Con `mlflow.sklearn.autolog()` y un `RandomizedSearchCV`, ¿dónde quedan los parámetros del
pipeline?
**R:** En los runs hijos (las mejores `max_tuning_runs` combinaciones). El run padre solo tiene los de
la búsqueda y los mejores valores (`best_*`): 17 contra 106 en el Taller 3.

**P:** El run del autolog dice `training_f1_score = 0.974`. ¿El modelo es casi perfecto?
**R:** No. Es una métrica sobre los datos de entrenamiento. La que importa es `best_cv_score` o una
métrica de prueba; en el taller, 0.576 y 0.536.

**P:** Activaste el autolog, calculaste el F1 de prueba y no aparece en el run. ¿Qué pasó?
**R:** Probablemente importaste `f1_score` antes de activar el autolog. Este reemplaza las funciones
de `sklearn.metrics` al activarse, y tu nombre seguía apuntando a la original.

**P:** ¿Por qué `log_model` falla con *"untrusted types ... sklearn.tree._tree.Tree"* en MLflow 3?
**R:** Desde MLflow 3 los modelos de scikit-learn se guardan con skops, que solo reconstruye tipos
declarados como confiables. Hay que listarlos en `skops_trusted_types`.

**P:** ¿Para qué sirve `code_paths` en `log_model`?
**R:** Para guardar tu propio código junto al modelo (por ejemplo, transformadores personalizados),
de modo que se pueda cargar en una máquina que no tenga instalado tu paquete.

**P:** ¿Qué ventaja tiene cargar `models:/champions-resultado@campeon` en lugar de un archivo?
**R:** Producción no cambia su código cuando cambia el modelo: basta con mover el alias a otra
versión, y regresar a la anterior es igual de fácil.

**P:** ¿Qué tiene un archivo `MLproject` y para qué sirve?
**R:** El nombre del proyecto, los entry points con sus parámetros y comandos, y el ambiente
(venv, conda o Docker). Permite reproducir el entrenamiento con `mlflow run`.

**P:** ¿Qué agrega `mlflow.data` a un run?
**R:** Los datasets usados, con su nombre, una huella digital (*digest*) del contenido, el esquema y
el origen. Si dos runs tienen huellas distintas, no se entrenaron con los mismos datos.

**P:** ¿Por qué el generador del tutorial no es reproducible aunque fija la semilla?
**R:** Porque las fechas salen de `datetime.now()`: corrido otro día, cada fila cae en otro día de la
semana y cambia la demanda (30 % de las filas de un día al siguiente).

**P:** ¿Por qué el bosque del tutorial pasa de R² 0.754 a 0.294?
**R:** Porque se validó al azar y luego en el tiempo. Al azar el modelo ve días posteriores a los que
valida; en el tiempo tiene que predecir un periodo con más inflación de la que vio, y los árboles no
extrapolan la tendencia.

## 🏋️ Ejercicios

1. Corre `ejemplos/mlflow_minimo.py`, abre `mlflow ui` y encuentra en la interfaz:
   - los 5 runs hijos del autolog;
   - la métrica `f1_score_X_test`;
   - el alias `@campeon`.
2. En el mismo script, mueve `from sklearn import metrics` a un `from sklearn.metrics import f1_score`
   **antes** de `autolog()` y comprueba que la métrica de prueba deja de aparecer.
3. Registra una segunda versión con otro modelo (por ejemplo `LogisticRegression`), mueve el alias a
   la mejor de las dos y verifica que `load_model("models:/champions-repaso@campeon")` entrega la nueva
   sin cambiar esa línea.
4. Al mini MLflow del notebook agrégale `log_metric(nombre, valor, paso)` con historial por paso y
   úsalo para registrar el F1 de cada partición de una validación cruzada.
5. Escribe un `MLproject` para `mlflow_minimo.py` con un parámetro `n_iter` y córrelo con
   `mlflow run . -P n_iter=5 --env-manager local`.

## 🔗 Referencias

- Repo de la entrega: [MLFlow (Taller 3)](https://github.com/DiegoLinares11/MLFlow).
- MLflow, [ML Experiment Tracking](https://mlflow.org/docs/latest/ml/tracking/).
- MLflow, [Scikit-learn Integration](https://mlflow.org/docs/latest/ml/traditional-ml/sklearn/) y su
  [guía completa, sección *Pipeline Integration*](https://mlflow.org/docs/3.3.0/ml/traditional-ml/sklearn/guide).
- MLflow, [Model Registry](https://mlflow.org/docs/latest/ml/model-registry/).
- MLflow, [Projects](https://mlflow.org/docs/latest/ml/projects/).
- MLflow, [Dataset Tracking](https://mlflow.org/docs/latest/ml/dataset/).
- MLflow, [Your First MLflow Model](https://mlflow.org/docs/3.1.3/ml/getting-started/logging-first-model/) (tutorial, versión 3.1.3).
- scikit-learn, [Model persistence](https://scikit-learn.org/stable/model_persistence.html) (pickle contra skops).
- Temas relacionados del repo: [02 overfitting](../02-overfitting/), [06 hiperparámetros](../06-hiperparametros/), [11 Databricks](../11-databricks/), [13 entry points](../13-entry-points/).
