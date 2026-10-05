# 11 · Databricks: lakehouse, medallón, Unity Catalog y MLflow

🎬 Video: [▶️ en español](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/11-databricks-es.mp4) · [▶️ in English](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/11-databricks-en.mp4) · [todos los videos](https://github.com/DiegoLinares11/RepasoMLOps/releases/tag/videos)

## 🧱 Conocimiento previo

Databricks junta varias ideas a la vez. Antes de entrarle, conviene tener claras estas seis.

### 1. Tabla, esquema y SQL

Una **tabla** son filas y columnas con un **esquema**: el nombre y el tipo de cada columna (`home_team: string`, `home_possession_pct: double`). **SQL** es el lenguaje para consultarlas:

```sql
SELECT home_team, AVG(home_possession_pct) FROM partidos GROUP BY home_team;
```

En pandas eso es `df.groupby("home_team")["home_possession_pct"].mean()`. Databricks deja usar las dos formas sobre la misma tabla.

### 2. Archivos: CSV vs Parquet

| | CSV | Parquet |
|---|---|---|
| Cómo guarda | Texto, fila por fila | Binario, **columna por columna**, comprimido |
| ¿Guarda los tipos? | No: `63` y `'63'` se ven igual; al releer hay que adivinar | Sí, el esquema va dentro del archivo |
| Leer 2 de 18 columnas | Tiene que leer todo | Lee solo esas 2 columnas |

Por eso en big data casi todo se guarda en Parquet. (Lo verás en el notebook: con CSV tuvimos que guardar el esquema aparte.)

### 3. ¿Por qué hace falta Spark?

pandas trabaja en **una sola computadora** y necesita que los datos quepan en su RAM. Con 151 partidos no hay problema; con 2 mil millones de eventos de tracking de jugadores, sí.

**Apache Spark** reparte el trabajo entre **muchas máquinas** (un **cluster**): un *driver* divide la tarea y varios *workers* procesan cada uno un pedazo.

> Analogía: contar los votos de un país. pandas es una sola persona contando todo. Spark es un coordinador (driver) que reparte las urnas entre cien voluntarios (workers) y luego suma sus conteos.

Detalle importante: Spark es **perezoso** (*lazy*). `filter`, `drop`, `withColumn` solo arman un plan; nada se calcula hasta que pides un resultado (`count`, `display`, `saveAsTable`).

### 4. Transacciones ACID

Garantías de una base de datos seria, que un montón de archivos sueltos **no** tiene:

| Letra | Significa | Ejemplo de lo que evita |
|---|---|---|
| **A**tomicidad | Una escritura se hace completa o no se hace | Que un error a la mitad deje la tabla con la mitad de las filas |
| **C**onsistencia | Se respetan las reglas (esquema, restricciones) | Que alguien meta texto en una columna numérica |
| a**I**slamiento | Lecturas y escrituras simultáneas no se pisan | Que un dashboard lea la tabla a medio reescribir |
| **D**urabilidad | Lo confirmado no se pierde | Que un reinicio borre la última carga |

### 5. La nube y el almacenamiento de objetos

Los datos de un lakehouse viven en almacenamiento de objetos barato (Amazon S3, Azure Data Lake Storage, Google Cloud Storage): básicamente un disco infinito de archivos. El cómputo (el cluster) se **enciende y apaga aparte**: separar almacenamiento de cómputo es lo que hace que sea barato.

### 6. Experimento, run y registro de modelos (por qué existe MLflow)

En la Actividad 3 probaste muchas combinaciones de hiperparámetros. ¿Dónde quedó cuál dio qué? Normalmente en prints y en tu memoria. Y en la Actividad 4 el modelo se guardaba como un único `modelo.joblib` en un volumen: cada reentrenamiento **pisaba** al anterior, sin historial. MLflow resuelve exactamente esos dos problemas.

## 🎯 Qué tienes que saber

### 1. Qué es Databricks

Una **plataforma en la nube construida sobre Apache Spark** (la fundaron los creadores de Spark) que junta en un solo lugar: notebooks colaborativos, clusters administrados, tablas Delta, gobernanza con Unity Catalog, MLflow y programación de tareas (Jobs). Su propuesta se llama **lakehouse**.

### 2. Data warehouse vs data lake vs lakehouse

| | Data warehouse | Data lake | Lakehouse |
|---|---|---|---|
| Qué guarda | Datos **estructurados** y limpios | **Todo**, crudo: CSV, JSON, imágenes, logs | Todo, en archivos abiertos (Parquet) + una capa de tablas |
| Esquema | Se define **antes** de cargar (*schema-on-write*) | Se interpreta **al leer** (*schema-on-read*) | Se impone al escribir en tablas Delta, pero se puede guardar crudo |
| Transacciones ACID | Sí | No (son archivos sueltos) | **Sí** (gracias a Delta Lake) |
| Costo | Alto | Bajo | Bajo (almacenamiento de objetos) |
| Bueno para | BI y reportes SQL | Ciencia de datos, ML, datos no estructurados | Las dos cosas en un mismo lugar |
| Riesgo típico | Caro y rígido | Se vuelve un **"pantano de datos"** (nadie sabe qué hay ni si es confiable) | — |
| Ejemplos | Snowflake, BigQuery, Redshift | S3 / ADLS con archivos | Databricks + Delta Lake |

> Analogía: el **warehouse** es una biblioteca con todo catalogado (orden perfecto, pero solo acepta libros). El **lake** es una bodega donde se tira todo (cabe cualquier cosa, pero no encuentras nada). El **lakehouse** es la bodega barata con el sistema de catálogo de la biblioteca encima.

### 3. Compute: clusters

Para correr cualquier celda necesitas un **cómputo** encendido:

| Tipo | Para qué | Nota |
|---|---|---|
| **All-purpose cluster** | Trabajar interactivamente en notebooks | Se apaga solo tras X minutos sin uso (*auto-termination*) para no gastar |
| **Job cluster** | Correr un Job programado | Se crea para el job y se destruye al terminar: más barato |
| **Serverless** | Notebooks/Jobs/SQL sin administrar máquinas | Lo que usa la edición Free; arranca en segundos |
| **SQL warehouse** | Consultas SQL y dashboards | Optimizado solo para SQL |

Un cluster tiene un **runtime** (versión de Spark + librerías preinstaladas; el *ML Runtime* ya trae scikit-learn y MLflow).

### 4. Notebooks y comandos mágicos

Un notebook de Databricks tiene un lenguaje por defecto (Python) y cada celda puede cambiarlo con un **comando mágico** en la primera línea:

| Mágico | Qué hace | Uso en el curso |
|---|---|---|
| `%md` | Celda de texto Markdown | Títulos y explicación de cada capa |
| `%sql` | Celda SQL | `SELECT ... FROM workspace.champions.partidos_gold` |
| `%python` | Celda Python (si el notebook es de otro lenguaje) | — |
| `%pip install paquete` | Instala una librería en el notebook | — |
| `%run ./otro_notebook` | Ejecuta otro notebook e importa sus variables | — |

En el notebook ya existen `spark` (la sesión de Spark), `display()` (tabla interactiva con gráficas) y `dbutils` (archivos, secrets, widgets). Exportado como `.py`, un notebook se ve con líneas `# COMMAND ----------` entre celdas y `# MAGIC %md` en las celdas mágicas (ver `ejemplos/`).

### 5. Delta Lake

Una tabla Delta es **archivos Parquet + un registro de transacciones** (la carpeta `_delta_log/`, con un JSON por cada cambio). Ese log es lo que le da poderes de base de datos a unos archivos:

| Característica | Qué significa | Comando |
|---|---|---|
| **ACID** | Escrituras completas o nada; lectores no ven tablas a medias | automático |
| **Time travel** | Cada escritura es una versión; puedes leer una versión anterior | `SELECT * FROM t VERSION AS OF 3` / `TIMESTAMP AS OF '...'` |
| **Historial** | Quién cambió qué y cuándo | `DESCRIBE HISTORY t` |
| **Restaurar** | Volver atrás tras un error | `RESTORE TABLE t TO VERSION AS OF 3` |
| **Schema enforcement** | Rechaza escrituras con columnas/tipos que no coinciden | automático (se relaja con `overwriteSchema` / `mergeSchema`) |
| **Upserts** | Insertar o actualizar en una sola operación | `MERGE INTO` |

`saveAsTable(...)` en Databricks crea por defecto una tabla Delta. Por eso en el curso se usó `.option("overwriteSchema", "true")`: permite que una nueva corrida cambie las columnas.

> Analogía del time travel: es el **historial de versiones de Google Docs** aplicado a una tabla.

### 6. Unity Catalog: nombres, gobernanza y linaje

Unity Catalog (UC) es el **catálogo central** de todo lo que hay en Databricks: tablas, vistas, volúmenes (archivos) y modelos.

**Nombres de tres niveles:** `catálogo.esquema.tabla` → `workspace.champions.partidos_silver`.

| Nivel | Analogía | En el curso |
|---|---|---|
| Catálogo | El edificio | `workspace` |
| Esquema | El piso / departamento | `champions` (medallón) y `default` (pipeline) |
| Tabla | El archivero | `partidos_bronze`, `partidos_silver`, `partidos_gold`, `partidos_limpios` |

**Gobernanza:** permisos centralizados con SQL (`GRANT SELECT ON TABLE workspace.champions.partidos_gold TO analistas`), auditoría de quién accedió a qué.

**Linaje:** UC registra **automáticamente** qué tabla se produjo a partir de cuál, y lo muestra como grafo en la pestaña **Lineage**. La regla de oro del Ejercicio 4:

> Cada capa debe **leer la TABLA anterior con `spark.table(...)`**, no reutilizar un DataFrame que quedó en memoria. UC solo ve lo que pasa por el catálogo: si plata se construye desde una variable de Python, para UC esa tabla "salió de la nada" y el linaje queda roto.

¿Para qué sirve el linaje? Si un número de oro sale raro, lo rastreas hasta plata y bronce (*análisis de causa*). Y si vas a cambiar bronce, sabes qué tablas de abajo se verán afectadas (*análisis de impacto*).

### 7. Arquitectura medallón: bronce, plata, oro

| Capa | Qué contiene | Pregunta que responde | En el curso |
|---|---|---|---|
| 🥉 **Bronce** | Los datos **tal como llegaron**, sin limpiar | *¿Qué llegó exactamente?* | 151 filas, con las 7 vacías y `score`/`winner` |
| 🥈 **Plata** | Limpios, sin duplicados, **tipados**, sin fuga | *¿En qué puedo confiar?* | 144 partidos, posesión y tiros como números |
| 🥇 **Oro** | **Agregados** listos para un consumidor (dashboard, modelo, reporte) | *¿Qué necesita quien lo va a usar?* | Resumen por equipo local: victorias, posesión, tasa de victoria |

**¿Por qué no se limpia bronce?** Por **auditoría** y para poder **reprocesar**. Si en plata te equivocas (p. ej. un regex que borra filas buenas), corriges el código y regeneras plata desde bronce. Si hubieras limpiado al ingerir, el dato original ya no existiría. Bronce es el "acta original".

> Analogía de una refinería: bronce es el petróleo crudo tal como sale del pozo (lo guardas aunque no sirva directo), plata es el combustible refinado, oro es la gasolina ya en la bomba, lista para cada tipo de cliente.

### 8. MLflow

MLflow (también creado por Databricks, de código abierto) tiene dos piezas que usamos:

**a) Tracking (seguimiento de experimentos)**

| Concepto | Qué es | Ejemplo del curso |
|---|---|---|
| **Experimento** | Carpeta que agrupa corridas de un mismo problema | El experimento del notebook |
| **Run** | Una corrida de entrenamiento, con id único | `champions-logistica` |
| **Parámetros** | Entradas de configuración (no cambian durante el run) | `C=0.541`, `class_weight="balanced"` |
| **Métricas** | Números de desempeño (pueden registrarse por paso/época) | accuracy, f1 |
| **Artefactos** | Archivos producidos: el modelo serializado, gráficas, CSV | el pipeline de sklearn con su entorno |
| **Tags** | Metadatos libres | versión de datos, autor |

Se registra a mano (`mlflow.log_param`, `mlflow.log_metric`, `mlflow.sklearn.log_model`) o **automáticamente** con `mlflow.sklearn.autolog()`, que en cada `.fit()` guarda todos los hiperparámetros, métricas de entrenamiento y el modelo. La pestaña **Experiments** compara runs en una tabla y gráficas.

**b) Model Registry (registro de modelos)**

Toma el modelo de un run y lo **registra con nombre y versión**: `workspace.champions.clasificador_resultado` v1, v2, v3... En Unity Catalog los modelos son un objeto más del catálogo (mismos tres niveles, mismos permisos). Un **alias** como `champion` apunta a la versión en producción; quien consume carga `models:/<nombre>@champion` y no le importa qué run ganó. Cambiar de modelo = mover el alias; volver atrás = moverlo de regreso.

| Actividad 4 (Docker) | Databricks + MLflow |
|---|---|
| Un único `modelo.joblib` en un volumen | Cada entrenamiento es un run con params, métricas y artefacto |
| Reentrenar pisa el anterior | Versiones 1, 2, 3... del modelo registrado |
| "¿Con qué hiperparámetros se entrenó este?" → nadie sabe | Queda en el run |
| La API cargaba "el archivo que hubiera" | Se carga `@champion`, explícito y reversible |

### 9. Jobs: programar el pipeline

Un **Job** (en la interfaz, *Jobs & Pipelines*) ejecuta notebooks o scripts sin que nadie los abra. Tiene **tareas** con **dependencias** (un grafo, como `needs:`), un **disparador** (horario cron, llegada de archivos nuevos, o manual), reintentos y alertas por correo.

| GitHub Actions (Ejercicio 3) | Databricks Jobs |
|---|---|
| Workflow `.yml` | Job |
| Job (`extraer`, `limpiar`…) | Tarea (un notebook por capa) |
| `needs: limpiar` | *Depends on* |
| `on: schedule: cron` | *Schedule* / *File arrival trigger* |
| `runs-on: ubuntu-latest` | Job cluster o serverless |
| Artefactos entre jobs | Las tablas de UC: cada tarea lee la tabla que escribió la anterior |
| `raise SystemExit(1)` falla el job | Una excepción (`assert`) falla la tarea y detiene las dependientes |

Se complementan: lo típico es que GitHub Actions pruebe el **código** y despliegue los notebooks, y que Databricks Jobs corra el pipeline de **datos** cada día.

## 📂 Qué hicimos en el curso

> **Nota sobre las entregas:** no hay repos separados del **Ejercicio 4** ni de la **Actividad 7**. El material de Databricks vive en la carpeta [`databricks/`](https://github.com/DiegoLinares11/Ejecicio3-MLOPS/tree/main/databricks) del repo del Ejercicio 3 y en este repaso **asumimos que corresponde a esas dos entregas**. El commit del notebook del medallón lo identifica como del Ejercicio 4 (*"agregar el notebook del medallon en Unity Catalog (Ejercicio 4)"*); los notebooks del pipeline con MLflow los asociamos a la Actividad 7. Autores: Diego Linares, Andy Fuentes, Christian Echeverria, Diederich Solis.

### `pipeline_champions_databricks.py` — el Ejercicio 3 llevado a Databricks
El mismo pipeline de cuatro etapas, ahora como notebook:
1. **Extracción:** `pd.read_csv` directo del CSV raw de GitHub (151 filas × 18 columnas), sin subir archivos.
2. **Limpieza:** `dropna(how="all")` + `dropna(subset=["result"])`, quita `score`, `winner` (fuga) y `date`, `venue`, `referee` → 144 filas. Muestra la distribución de clases con `display`.
3. **Tabla en Unity Catalog:** `spark.createDataFrame(limpio).write.mode("overwrite").saveAsTable("workspace.default.partidos_limpios")`, dentro de un `try/except` para que el notebook siga aunque no se pueda guardar. Luego una celda `%sql` cuenta partidos por resultado.
4. **Entrenamiento con MLflow:** el mismo `convertir_texto_a_numero` y el mismo `Pipeline` (14 numéricas imputadas + escaladas, 2 categóricas con One-Hot, `LogisticRegression(C=0.541, class_weight="balanced")`), split 80/20 estratificado con semilla 42. `mlflow.sklearn.autolog()` + `mlflow.start_run(run_name="champions-logistica")` registra parámetros, métricas y modelo, e imprime el `run_id`.
5. **Evaluación y compuerta:** compara con `DummyClassifier(strategy="most_frequent")` y usa dos `assert` (f1_macro ≥ 0.40 y > trivial), que hacen fallar la celda si el modelo no pasa.
6. **Tabla final** "Qué ganamos al traerlo aquí": CSV en `artefactos/` → tabla en UC; `.joblib` en un volumen → run de MLflow versionado; comparar corridas → pestaña Experiments; GitHub Actions → Jobs & Pipelines. *"Lo que no cambia es la lógica."*

Como el código y el split son los del Ejercicio 3, las métricas esperadas son las mismas: **accuracy 0.621 y f1_macro 0.542** frente a 0.483 / 0.217 del trivial (lo verificamos corriendo `pipeline_en_una_celda.py` en local).

### `pipeline_en_una_celda.py` — versión de una sola celda
Las cuatro etapas en un solo bloque para pegar en cualquier notebook. MLflow es opcional: el `import mlflow` está en un `try/except`, así que en Databricks registra el run y fuera de él entrena igual e imprime *"sin registro"*. Al final solo imprime si le gana al trivial (no detiene la ejecución ni revisa el 0.40).

### `medallon_champions.py` — arquitectura medallón en Unity Catalog (Ejercicio 4)
- **Setup:** `CREATE SCHEMA IF NOT EXISTS workspace.champions`, `USE CATALOG`, `USE SCHEMA`.
- **Bronce (`partidos_bronze`):** el CSV de GitHub sin limpiar (solo normaliza nombres de columnas quitando espacios): 151 filas con las 7 vacías y las columnas de fuga, *"para poder auditar"*.
- **Plata (`partidos_silver`):** lee **la tabla bronce** con `spark.table(...)` y, con funciones de PySpark: filtra `result` no nulo, quita `score`, `winner`, `venue`, `referee`, convierte la posesión con `regexp_replace("%","").cast("double")` y los tiros con `regexp_extract` (`home_shots_on_target_n`, `home_shots_total`, y lo mismo para visita). `date` y las atajadas se quedan como texto. 151 → 144 partidos.
- **Oro (`partidos_gold`):** lee **la tabla plata** y agrupa por `home_team`: `partidos_de_local`, `victorias`, `empates`, `posesion_promedio`, `tiros_a_puerta_promedio` y `tasa_de_victoria`, ordenado por tasa. Son 36 equipos.
- **Linaje:** explica cómo verlo (*Catalog → workspace → champions → partidos_silver → pestaña Lineage*): `partidos_bronze → partidos_silver → partidos_gold`, registrado solo porque cada capa leyó la tabla anterior.
- **Consulta `%sql`** sobre oro (equipos con ≥ 3 partidos de local, top 10 por tasa de victoria) y `SHOW TABLES` al final.

## 🧪 Práctica

### `repaso.ipynb` (generado desde `repaso.py`)
Como en local no hay Databricks, Spark ni MLflow, el notebook **imita las ideas con pandas** en una carpeta temporal:

1. **Un "Unity Catalog" de juguete:** `guardar_tabla()` escribe cada tabla como versiones `v0`, `v1`… (como Delta) y `leer_tabla()` **siempre lee de disco**. El linaje se registra solo: cada escritura anota qué tablas se leyeron antes.
2. **Bronce:** el CSV tal cual (151 × 18, 7 filas vacías, `score`/`winner`), con una huella (hash) idéntica a la de la fuente.
3. **Plata:** lee bronce de disco, limpia y tipa → 144 partidos; al releer quedan 10 columnas enteras, 4 decimales, 1 fecha y 3 de texto.
4. **Oro:** `partidos_gold` (como en el curso) y `equipos_gold` (36 equipos con 8 partidos cada uno; Arsenal 8 de 8 victorias). La consulta `%sql` original corre sobre SQLite.
5. **Linaje** impreso (`partidos_silver <- partidos_bronze`, etc.) y el **anti-ejemplo**: una tabla hecha desde una variable en memoria queda sin linaje.
6. **Time travel:** una escritura con bug borra los 25 empates (119 filas) y se recupera la versión 0.
7. **"MLflow" casero:** 5 runs guardados en JSON con id, parámetros, métricas, artefacto `.joblib`, versión de datos y timestamp. `champions-logistica` reproduce **f1_macro 0.542**; `C=0.05` saca 0.565 en prueba (con la advertencia de que elegir con 29 partidos de prueba no es confiable); trivial 0.217.
8. **Model Registry casero:** registra el mejor run como v1 con alias `champion`, **rechaza** al trivial con la compuerta del Ejercicio 3, y carga `@champion` para predecir.

```bash
cd RepasoMLOps
python tools/build_nb.py 11-databricks/repaso.py
```

### `ejemplos/`
Los tres notebooks reales, con comentarios de repaso (el código no cambia):

| Archivo | Qué es |
|---|---|
| `medallon_champions.py` | Medallón bronce/plata/oro en Unity Catalog con PySpark, linaje y `%sql` |
| `pipeline_champions_databricks.py` | Pipeline del Ejercicio 3 con tabla en UC, `mlflow.sklearn.autolog()` y compuerta con `assert`; al final, cómo se registraría en el Model Registry |
| `pipeline_en_una_celda.py` | Las 4 etapas en una celda, con MLflow opcional |

Para usarlos: en Databricks (la edición Free sirve), *Workspace → Import → File* y sube el `.py`; Databricks lo reconoce como notebook por la primera línea `# Databricks notebook source`.

## ❓ Preguntas tipo examen

**P:** ¿Qué es un lakehouse y qué problema resuelve frente a un data lake?
**R:** Es almacenamiento barato de data lake (archivos abiertos como Parquet en la nube) con las garantías de un warehouse (transacciones ACID, esquema, gobernanza) gracias a una capa de tablas como Delta Lake. Resuelve que un data lake sin control se vuelve un "pantano": sin esquema, sin transacciones y sin saber qué datos son confiables.

**P:** ¿Qué agrega Delta Lake sobre unos archivos Parquet?
**R:** Un registro de transacciones (`_delta_log`) que da ACID, historial de versiones (time travel con `VERSION AS OF`), `RESTORE`, `DESCRIBE HISTORY`, validación de esquema y `MERGE` para upserts.

**P:** ¿Cómo se nombra una tabla en Unity Catalog? Da el ejemplo del curso.
**R:** Con tres niveles, `catálogo.esquema.tabla`: `workspace.champions.partidos_silver` (o `workspace.default.partidos_limpios` en el pipeline).

**P:** ¿Por qué cada capa del medallón debe leer la tabla anterior con `spark.table(...)` y no reutilizar el DataFrame en memoria?
**R:** Porque Unity Catalog solo registra linaje para lo que pasa por el catálogo. Si plata se construye desde una variable de Python, UC no sabe que viene de bronce y el grafo de linaje queda roto: no se puede rastrear un dato ni saber qué se afecta si cambia una tabla.

**P:** ¿Qué va en bronce, plata y oro?
**R:** Bronce: los datos crudos tal como llegaron (151 filas con vacías y fuga). Plata: limpios, tipados y sin fuga (144 partidos con posesión y tiros numéricos). Oro: agregados listos para consumir (resumen por equipo local con victorias, posesión y tasa de victoria).

**P:** ¿Por qué no se limpia la capa bronce?
**R:** Para auditar y poder reprocesar. Si una regla de limpieza resulta equivocada, se corrige y se regenera plata desde bronce; si se hubiera limpiado al ingerir, el dato original se habría perdido.

**P:** ¿Qué es un run de MLflow y qué guarda?
**R:** Una corrida de entrenamiento con id único dentro de un experimento. Guarda parámetros (p. ej. `C=0.541`), métricas (accuracy, f1), artefactos (el modelo serializado, gráficas), tags y tiempos.

**P:** ¿Qué hace `mlflow.sklearn.autolog()`?
**R:** Hace que cada `.fit()` de scikit-learn dentro de un run registre solo los hiperparámetros, métricas de entrenamiento y el modelo con su entorno, sin escribir `log_param`/`log_metric` a mano. Ojo: las métricas de prueba que calculas después hay que registrarlas tú (`mlflow.log_metric`).

**P:** ¿Qué diferencia hay entre el tracking de MLflow y el Model Registry?
**R:** El tracking guarda **todas** las corridas para compararlas. El Model Registry guarda solo los modelos elegidos, con nombre, **versiones** y **alias** (p. ej. `champion`) para usarlos en producción y poder volver atrás.

**P:** ¿Qué problema de la Actividad 4 resuelve el registro de modelos?
**R:** En la Actividad 4 el modelo era un único `modelo.joblib` en un volumen de Docker: cada reentrenamiento pisaba al anterior, sin versiones ni registro de con qué parámetros se entrenó. MLflow da runs con parámetros y métricas, y versiones del modelo registrado.

**P:** ¿Qué es un comando mágico en un notebook de Databricks? Da tres.
**R:** Una instrucción en la primera línea de una celda que cambia su lenguaje o comportamiento: `%md` (Markdown), `%sql` (SQL), `%python`, `%pip install`, `%run ./otro_notebook`.

**P:** ¿Cuál es la diferencia entre un all-purpose cluster y un job cluster?
**R:** El all-purpose es para trabajo interactivo en notebooks y se apaga por inactividad; el job cluster se crea para ejecutar un Job y se destruye al terminar, lo que lo hace más barato para tareas programadas.

**P:** ¿Cómo se implementa la compuerta de calidad en el notebook de Databricks y qué pasa si falla dentro de un Job?
**R:** Con dos `assert` (f1_macro ≥ 0.40 y f1_macro > trivial). Si falla, se lanza un `AssertionError`, la tarea del Job queda fallida y las tareas que dependen de ella no corren, igual que `needs:` en GitHub Actions.

**P:** ¿Por qué Spark es "perezoso" y qué implica?
**R:** Porque las transformaciones (`filter`, `withColumn`, `drop`) solo construyen un plan; se ejecutan al pedir una acción (`count`, `display`, `saveAsTable`). Así Spark puede optimizar el plan completo antes de mover datos entre máquinas.

## 🏋️ Ejercicios

1. **Rompe el linaje a propósito.** En Databricks (edición Free), corre `medallon_champions.py` y mira la pestaña *Lineage* de `partidos_gold`. Luego cambia la celda de oro para usar la variable `plata` en vez de `spark.table(...)`, guárdala como `partidos_gold_v2` y compara los dos grafos.
2. **Time travel real.** Después del ejercicio 1, ejecuta en `%sql`: `DELETE FROM workspace.champions.partidos_silver WHERE result = 'Draw'`, luego `DESCRIBE HISTORY`, `SELECT COUNT(*) ... VERSION AS OF <anterior>` y `RESTORE TABLE`. ¿Cuántas filas tiene cada versión? (En el notebook local: 144 → 119 → 144.)
3. **Registra métricas de prueba.** Modifica `pipeline_champions_databricks.py` para que, dentro del run, registre `test_f1_macro` y `test_accuracy` con `mlflow.log_metric`. Entrena con `C=0.05` y `C=0.541` y compáralos en la pestaña *Experiments*.
4. **Una tabla oro nueva.** En el notebook local, crea `visitantes_gold` (resumen por `away_team`: victorias de visita, posesión promedio) leyendo plata desde disco, y verifica que el linaje la muestre colgando de `partidos_silver`.
5. **Programa el medallón.** Diseña (en papel o en la UI) un Job con tres tareas — bronce, plata, oro — con dependencias entre ellas y horario diario. ¿Qué tendrías que cambiar en el notebook para partirlo en tres?

## 🔗 Referencias

- Repo con los notebooks de Databricks: <https://github.com/DiegoLinares11/Ejecicio3-MLOPS/tree/main/databricks>
- Databricks — What is a data lakehouse?: <https://docs.databricks.com/en/lakehouse/index.html>
- Databricks — Medallion architecture: <https://docs.databricks.com/en/lakehouse/medallion.html>
- Databricks — What is Unity Catalog?: <https://docs.databricks.com/en/data-governance/unity-catalog/index.html>
- Databricks — Data lineage in Unity Catalog: <https://docs.databricks.com/en/data-governance/unity-catalog/data-lineage.html>
- Delta Lake — Time travel / table history: <https://docs.delta.io/latest/delta-batch.html#query-an-older-snapshot-of-a-table-time-travel>
- MLflow — Tracking: <https://mlflow.org/docs/latest/tracking.html>
- MLflow — Model Registry: <https://mlflow.org/docs/latest/model-registry.html>
- Databricks — Jobs (Lakeflow Jobs): <https://docs.databricks.com/en/jobs/index.html>
- Databricks Free Edition: <https://www.databricks.com/learn/free-edition>
