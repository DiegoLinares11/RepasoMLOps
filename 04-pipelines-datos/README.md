# 04 · Pipelines de datos y comandos de pandas

🎬 Video: [▶️ en español](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/04-pipelines-datos-es.mp4) · [▶️ in English](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/04-pipelines-datos-en.mp4) · [todos los videos](https://github.com/DiegoLinares11/RepasoMLOps/releases/tag/videos)

## 🧱 Conocimiento previo

Antes de hablar de "pipelines" hay que tener claras cinco ideas pequeñas. Si ya las dominas,
salta a la siguiente sección.

### 1. Una tabla en pandas: `DataFrame` y `Series`

- Un **`DataFrame`** es una tabla: filas (registros) y columnas (variables). Piensa en una hoja
  de Excel que vive en memoria.
- Cada columna es una **`Series`**: una lista de valores con un índice (el número de fila).
- `df["result"]` devuelve una `Series`; `df[["home_team", "result"]]` (doble corchete) devuelve
  un `DataFrame` con esas dos columnas.

### 2. El tipo de dato (`dtype`) importa

Cada columna tiene **un** tipo: `int64` (enteros), `float64` (decimales), `str`/`object`
(texto), `datetime64` (fechas), `bool`.

Ejemplo concreto de nuestro CSV: la posesión llega como el texto `'63%'`. Para pandas eso es
igual que `'hola'`: no puedes sacarle promedio. Hay que convertirlo a `63.0` (`float`). Buena
parte del trabajo de un pipeline es justo eso: **dejar cada columna con el tipo correcto**.

### 3. Valores faltantes: `NaN`

`NaN` ("Not a Number") es como pandas marca un dato que no está. Se detecta con `isna()`.
Ojo: no todos los nulos son iguales.

- En nuestro CSV hay **7 filas completamente vacías**: son separadores de jornada, basura.
- Y hay **3 nulos en `home_saves_pct`**: el portero tuvo `0 of 0` atajadas y 0/0 no existe.
  Ese nulo **sí significa algo**.

La decisión (borrar o rellenar) depende de *por qué* falta el dato.

### 4. Expresiones regulares (regex) mínimas

Una regex es un patrón de texto. Solo necesitas cuatro piezas:

| Pieza | Significa | Ejemplo |
|---|---|---|
| `\d` | un dígito | `\d` encaja con `7` |
| `+` | uno o más del anterior | `\d+` encaja con `10` |
| `\s*` | cero o más espacios | `3 of 10` y `3of10` |
| `( )` | **grupo de captura**: "guárdame esto" | `(\d+) of (\d+)` guarda `3` y `10` |

`df["col"].str.extract(r"(\d+) of (\d+)")` devuelve **una columna por cada grupo**.

### 5. Funciones que devuelven algo nuevo (y no modifican la entrada)

Una función "pura" recibe un DataFrame y **devuelve otro**, sin tocar el original. Es la base
para que un pipeline se pueda correr muchas veces sin sorpresas. En pandas casi todos los
métodos (`dropna`, `assign`, `drop`...) ya funcionan así: devuelven una copia.

Y el **encadenamiento de métodos**: `df.dropna().drop_duplicates().reset_index()` se lee de
izquierda a derecha como una receta. `df.pipe(mi_funcion)` permite meter tus propias funciones
en esa cadena (`df.pipe(f)` es lo mismo que `f(df)`).

## 🎯 Qué tienes que saber

### 1. ¿Qué es un pipeline de datos?

Es la **secuencia automatizada de pasos que lleva los datos desde su origen hasta un destino
donde se puedan usar**, dejándolos limpios y con buena calidad en el camino.

**Analogía del agua (IBM, la que usamos en la Tarea 3):** el agua no va directo del río a tu
llave. Se recolecta de varias fuentes (ríos, lagos, pozos), viaja por tuberías hasta una planta
donde se purifica, y solo entonces se distribuye. Con los datos igual: salen de bases de datos,
apps, sensores o APIs, casi nunca sirven como llegan, y hay que filtrarlos, limpiarlos y
ordenarlos antes de que lleguen a un tablero, un data warehouse o un modelo de ML.

Un buen pipeline es:

| Característica | Qué significa | Ejemplo |
|---|---|---|
| **Automatizado** | corre solo, por horario o por evento | todas las noches a las 2 a. m. |
| **Repetible / reproducible** | misma entrada → mismo resultado | el accuracy 0.724 del tema 05 sale igual en Windows y Linux |
| **Escalable** | aguanta más datos sin romperse | de 151 partidos a 10 temporadas |
| **Monitoreable** | avisa si algo falla o la calidad cae | alerta si llegan 0 filas |

### 2. Las etapas, una por una

```
fuente ──► INGESTA ──► VALIDACIÓN ──► LIMPIEZA ──► TRANSFORMACIÓN ──► CARGA ──► consumo
           (extract)                                                 (load)
                 ▲───────────── orquestación y monitoreo ───────────────▲
```

| Etapa | Pregunta que responde | En pandas | En nuestro CSV |
|---|---|---|---|
| **Ingesta / extracción** | ¿de dónde traigo los datos? | `read_csv`, `read_sql`, `read_json` | `pd.read_csv(...)` → 151 × 18 |
| **Validación** | ¿llegó lo que esperaba? | `assert`, `str.match`, `isin` | ¿están las 18 columnas? ¿`result` solo tiene 3 valores? |
| **Limpieza** | ¿qué sobra o está mal? | `dropna`, `drop_duplicates`, `str.strip` | fuera las 7 filas vacías → 144 |
| **Transformación** | ¿qué forma necesita? | `astype`, `str.extract`, `to_datetime`, `groupby`, `merge` | `'63%'` → `63.0`; `'3 of 10'` → 3 y 10 |
| **Carga** | ¿dónde lo dejo? | `to_csv`, `to_parquet`, `to_sql` | `salida/partidos_limpios.csv` |

La Tarea 3 (citando a IBM) agrega componentes que rodean a esas etapas: **almacenamiento**
(warehouse, lake o lakehouse), **consumo** (tableros, apps, modelos), **orquestación y
monitoreo** (Airflow, Prefect, Dagster: orden, horarios, reintentos) y **controles de acceso**
(quién puede ver qué dato).

**¿Por qué validar dos veces?** Antes de transformar se revisa el **formato** (¿la posesión
sigue viniendo como `'63%'`?). Después se revisan **reglas de negocio** (¿la posesión suma
~100? ¿el marcador coincide con `result`?). Un pipeline que sigue corriendo con datos rotos es
peor que uno que se detiene: el error aparece semanas después en un modelo que predice basura.

### 3. ETL vs ELT

La diferencia es **en qué momento se transforma**.

- **ETL** (Extract → Transform → Load): se transforma en un espacio intermedio y se carga ya
  limpio. Es lo que hacemos con pandas: todo en memoria y al final `to_csv`.
- **ELT** (Extract → Load → Transform): se carga el dato crudo en el destino y se transforma
  allá, con la potencia del warehouse en la nube (BigQuery, Snowflake, Redshift).

| Criterio | ETL | ELT |
|---|---|---|
| ¿Dónde se transforma? | en un espacio intermedio, **antes** de cargar | en el destino, **después** de cargar |
| Tipo de datos | sobre todo estructurados | estructurados, semi y no estructurados |
| Velocidad de ingesta | más lenta (transforma primero) | más rápida (carga crudo) |
| Destino típico | data warehouse tradicional | data lake o warehouse en la nube |
| Mejor para | reglas estrictas, cumplimiento (anonimizar antes de guardar) | grandes volúmenes y flexibilidad |

**Analogía:** ETL es lavar y picar las verduras en casa antes de meterlas al refri; ELT es
meterlas tal cual al refri (que es enorme) y picarlas cuando vas a cocinar. Según IBM, con los
warehouses modernos en la nube ELT se volvió el enfoque predominante.

Otras técnicas que menciona la Tarea 3: **replicación** (copiar datos a otros destinos para
mantenerlos sincronizados, sin transformarlos) y **virtualización** (una capa que muestra datos
de varias fuentes como si fueran una sola, sin moverlos).

### 4. Batch vs streaming

| | Batch (por lotes) | Streaming (en flujo) |
|---|---|---|
| Cuándo procesa | en grupos, por horario (cada noche) | continuamente, al llegar cada dato |
| Latencia | horas | segundos o menos |
| Casos | reportes, reentrenar un modelo cada semana | fraude, monitoreo, recomendaciones en vivo |
| Herramientas | pandas, Spark, Airflow | Kafka, Spark Streaming |

Nuestro pipeline es **batch**: procesa el CSV completo de una vez.

### 5. Qué problemas resuelve un pipeline

| Problema sin pipeline | Cómo lo resuelve el pipeline |
|---|---|
| "En mi compu sí salía": cada quien limpia distinto en su notebook | **Reproducibilidad**: el mismo código, en el mismo orden, da el mismo resultado |
| Alguien tiene que correr 15 celdas a mano cada lunes | **Automatización**: un comando o un horario |
| Nadie sabe de dónde salió una cifra del reporte | **Trazabilidad**: cada etapa está escrita; se puede seguir el dato desde la fuente |
| El proveedor cambia un formato y nadie se entera | **Calidad**: las validaciones frenan el pipeline con un mensaje claro |
| Cambia la fuente (CSV → SQL) y hay que reescribir todo | **Modularidad**: solo cambia la función `extraer` |

### 6. Idempotencia: la propiedad que más se pregunta

**Idempotente** = correrlo una vez o diez deja **el mismo estado final**. Como el botón del
ascensor: presionarlo cinco veces no hace que llegue cinco veces.

**Por qué importa:** los pipelines fallan a medias y se reintentan, los orquestadores los
re-ejecutan, alguien los corre "por si acaso". Si cada corrida duplicara filas, nadie podría
confiar en los datos.

| Diseño | ¿Idempotente? | Qué pasa al correr 3 veces |
|---|---|---|
| `to_csv(ruta)` (sobrescribe, modo `"w"`) | Sí | el mismo archivo, byte por byte |
| `to_csv(ruta, mode="a")` (agrega) | No | 144 → 288 → 432 filas (lo medimos en el notebook) |
| `to_sql(..., if_exists="append")` sin llave | No | partidos duplicados en la tabla |
| *upsert* por llave `(date, home_team, away_team)` | Sí | inserta lo nuevo, actualiza lo existente |
| sobrescribir la partición del día | Sí | el día se reescribe completo |

Recetas para lograrla: arrancar **siempre desde la fuente cruda**, no modificar la entrada
(trabajar sobre copias), orden determinista, y guardar sobrescribiendo o con *upsert*.

Un matiz: no hace falta que **cada** función sea idempotente por separado. `limpiar(limpiar(x))`
da lo mismo que `limpiar(x)`, pero `transformar` falla si la aplicas dos veces (la posesión ya es
número). Lo que debe ser idempotente es la **corrida completa** fuente → destino.

### 7. Data pipeline vs ML pipeline, CRISP-DM y el ciclo de vida

Un **ML pipeline** es un pipeline especializado: no solo deja datos listos, sino que los
convierte en un **modelo** entrenado, evaluado y desplegado. Lo normal es que el data pipeline
**le dé de comer** al ML pipeline.

| Aspecto | Data pipeline | ML pipeline |
|---|---|---|
| Objetivo | mover, limpiar y entregar datos | entrenar y desplegar modelos |
| Producto final | datos listos para usar | modelo entrenado en producción |
| Etapas típicas | ingesta, transformación, carga | preparación, features, entrenamiento, evaluación, despliegue, monitoreo |
| Enfoque | ingeniería de datos | ingeniería de ML / MLOps |

Relación con CRISP-DM (las 6 fases: Business Understanding, Data Understanding, Data
Preparation, Modeling, Evaluation, Deployment):

```
Business Understanding
Data Understanding   ◄── inspección y validación del data pipeline (info, isna, asserts)
Data Preparation     ◄── limpieza y transformación del data pipeline (tema 04) + preprocesamiento sklearn (tema 05)
Modeling             ◄── ML pipeline: entrenamiento y calibración (tema 06)
Evaluation
Deployment           ◄── empaquetar y servir (temas 08-10); el monitoreo vuelve a disparar el ciclo
```

En el **ciclo de vida de ML** el pipeline de datos no corre una sola vez: cuando el monitoreo
detecta que el modelo se degrada (drift), se vuelve a correr para reentrenar con datos nuevos.
Por eso tiene que ser automatizado, reproducible e idempotente.

### 8. Los comandos de pandas, por etapa y cuándo usar cada uno

| Etapa | Comando | Cuándo usarlo |
|---|---|---|
| Extracción | `read_csv`, `read_excel`, `read_json`, `read_parquet`, `read_sql`, `json_normalize` | según el formato de la fuente; `json_normalize` para JSON anidado de una API |
| | `read_csv(..., chunksize=10000)`, `usecols=[...]` | archivos que no caben en memoria / solo algunas columnas |
| Inspección | `shape`, `head`, `info`, `dtypes`, `describe` | siempre, justo después de extraer |
| | `isna().sum()`, `isna().mean()*100` | cuántos nulos y en qué columnas |
| Filtrado | `df[df["result"] == "Home Win"]`, `query(...)` | filas por condición (`query` se lee más natural) |
| | `isin([...])`, `str.contains(...)` | lista de valores / texto que contiene algo |
| | `loc[filas, cols]` / `iloc[0:10, 0:5]` | por etiqueta / por posición |
| | `drop(columns=[...])` | quitar columnas que no aportan o que son fuga |
| Limpieza | `dropna(how="all")`, `dropna(subset=[...])`, `dropna(thresh=10)` | filas vacías / falta la etiqueta / pocas columnas llenas |
| | `drop_duplicates()` | registros repetidos |
| | `str.strip()`, `str.lower()`, `replace({...})` | variantes del mismo valor ("Man City" vs "Manchester City") |
| Tipos | `astype(float)`, `pd.to_numeric(errors="coerce")` | texto a número (`coerce` convierte lo inválido en `NaN`) |
| | `str.replace("%", "")` + `astype` | quitar símbolos antes de convertir |
| | `str.extract(r"(\d+) of (\d+)")` | sacar varias partes de un texto |
| | `pd.to_datetime` | texto a fecha |
| Nulos | `fillna(valor)`, `fillna(mediana)`, `mode()[0]`, `ffill`, `interpolate` | rellenar; en un pipeline de ML mejor `SimpleImputer` (aprende en train) |
| Transformación | `assign(nueva=...)`, `pipe(f)` | crear columnas / encadenar funciones propias |
| Agregación | `groupby().agg(nombre=("col", "func"))` | resumir por categoría |
| | `pivot_table`, `crosstab`, `groupby().transform` | tabla dinámica / frecuencias / resultado del tamaño original |
| Unión | `merge(..., how="inner"/"left"/"outer")`, `concat` | juntar tablas por llave (JOIN) / apilar |
| Carga | `to_csv(index=False)`, `to_parquet`, `to_sql(if_exists=...)`, `to_json` | según quién consume el dato |

## 📂 Qué hicimos en el curso

### Ejercicio 2 · Comandos para un pipeline de datos en Python (individual, 31 jul 2026)

Documento con las operaciones de pandas que sostienen un pipeline, todas aplicadas al mismo
`champions_league_matches.csv` (151 filas, 18 columnas, 7 filas vacías), con los resultados
reales que devuelve cada comando. Elegí Python con pandas porque es la herramienta del curso
(Ejercicio 1 y Actividad 1). Seis secciones:

1. **Extracción**: familia `read_*`, `read_sql` con SQLAlchemy, APIs con `requests` +
   `json_normalize`, `chunksize` y `usecols` para archivos grandes.
2. **Filtrado**: máscaras booleanas (71 partidos de `Home Win`), `query`, `isin` (96 partidos
   Draw o Home Win), `str.contains`, `loc`/`iloc`, `drop`, `dropna(how="all")`,
   `drop_duplicates`.
3. **Estandarización**: tipos (`'63%'` → 63.0, `'3 of 10'` → dos columnas con `str.extract`,
   `to_datetime`), limpieza de texto, y escala (`StandardScaler`, `MinMaxScaler`).
4. **Agrupación**: `groupby().agg()`; el resultado clave fue Away Win 48 partidos con 48.5 % de
   posesión media, Draw 25 con 48.3 %, Home Win 71 con 53.6 % (la ventaja de localía).
5. **Nulos**: 129 nulos en el CSV crudo; eliminar (`dropna` con `how`, `subset`, `thresh`) o
   imputar (`fillna`, `ffill`, `interpolate`, `SimpleImputer`, `KNNImputer`). Los nulos de
   `home_saves_pct` vienen de "0 of 0".
6. **Publicar**: `to_csv`, `to_parquet`, `to_sql`, una API con FastAPI, el paquete de la
   Actividad 1 y `joblib.dump` del pipeline entrenado.

Cierra con una tabla que ubica cada sección en Extract / Transform / Load (siguiendo el
artículo de DataCamp), la distinción ETL vs ELT ("con pandas normalmente se trabaja al estilo
ETL") y la recomendación de diseñar el pipeline **solo tan complejo como haga falta**: para 151
filas bastan pandas y scikit-learn; Spark o Airflow se justifican con más volumen o frecuencia.

### Tarea 3 · Pipelines en el mundo de los datos (grupal, 24 jul 2026)

Investigación en equipo (Diego Linares, Andy Fuentes, Christian Echeverria, Diederich Solis)
basada en los artículos y el video de IBM:

- **Definición** con la analogía del sistema de agua de la ciudad, y las características de un
  pipeline: automatizado, repetible y confiable, escalable y monitoreable.
- **Capas**: ingesta (batch o streaming), procesamiento/transformación, almacenamiento
  (warehouse, lake, lakehouse), consumo, orquestación y monitoreo (Airflow, Prefect, Dagster),
  validación y controles de acceso.
- **Procesos**: ETL, ELT (con tabla comparativa), replicación y virtualización de datos.
- **Modos de procesamiento**: por lotes y en flujo (Kafka, Spark Streaming).
- **Data pipeline vs ML pipeline** (tabla comparativa) y las 7 etapas de un ML pipeline:
  ingesta, preprocesamiento, feature engineering, entrenamiento, evaluación, despliegue,
  monitoreo y reentrenamiento.
- **Conclusión**: separar en capas y etapas facilita automatizar, repetir, mantener y escalar.

Ambos documentos están publicados en el portafolio del equipo (sección Talleres).

## 🧪 Práctica

`repaso.ipynb` construye un **mini pipeline de datos en pandas** sobre
`../datos/champions_league_matches.csv`, con una función por etapa:

```
extraer → validar_crudo → limpiar → transformar → validar_limpio → guardar
```

Qué vas a ver (números reales del notebook):

- Inspección: 151 × 18, casi todo como texto, **129 nulos** = 7 filas vacías (126) + 3 casos de
  `0 of 0`.
- Validación con `assert` que **detiene** el pipeline cuando una sola fila trae `'0.63'` en vez
  de `'63%'`.
- Limpieza 151 → **144** partidos; `to_datetime` (del 16-09-2025 al 28-01-2026).
- Transformación con `str.replace`, `str.extract` (también los goles desde `score`) y `.pipe`.
- Reglas de negocio: posesión suma 100 (132 partidos) o 101 (12, por redondeo); hechos ≤
  intentos; el marcador coincide con `result` en los 144.
- `groupby/agg` que reproduce la tabla del Ejercicio 2 (53.6 / 48.5 / 48.3 % de posesión) y
  una tabla por equipo con `merge(how="outer")`: 36 equipos, 288 partidos-equipo, 238 puntos
  de local contra 169 de visita.
- **Idempotencia**: dos corridas dan el mismo DataFrame y el mismo MD5; el anti-ejemplo con
  `mode="a"` crece 144 → 288 → 432 filas.

Para correrlo:

```powershell
cd RepasoMLOps
python tools/build_nb.py 04-pipelines-datos/repaso.py   # regenera y ejecuta el notebook
# o ábrelo directo:
jupyter lab 04-pipelines-datos/repaso.ipynb
```

La salida se escribe en `04-pipelines-datos/salida/` (ignorada por git: es un archivo generado).

## ❓ Preguntas tipo examen

**P:** ¿Qué es un pipeline de datos, en una frase?
**R:** La secuencia automatizada de pasos que lleva los datos desde su origen hasta un destino
utilizable (tablero, warehouse, modelo), limpiándolos y validándolos en el camino.

**P:** Menciona las etapas de un pipeline de datos en orden.
**R:** Ingesta/extracción → validación → limpieza → transformación → carga; alrededor de todas,
orquestación y monitoreo. (IBM agrega almacenamiento, consumo y controles de acceso).

**P:** ¿Cuál es la diferencia entre ETL y ELT y cuándo conviene cada uno?
**R:** En ETL se transforma antes de cargar (en un espacio intermedio); en ELT se carga crudo y se
transforma dentro del destino. ETL conviene con reglas estrictas o cumplimiento (anonimizar antes
de guardar); ELT con grandes volúmenes y warehouses potentes en la nube.

**P:** Con pandas, ¿se trabaja normalmente al estilo ETL o ELT? ¿Por qué?
**R:** ETL: las transformaciones se hacen en memoria con pandas antes de guardar el resultado.

**P:** ¿Batch o streaming para detectar fraude con tarjeta? ¿Y para reentrenar un modelo cada
semana?
**R:** Fraude: streaming (cada transacción debe evaluarse en segundos). Reentrenar semanalmente:
batch.

**P:** ¿Qué significa que un pipeline sea idempotente y por qué importa?
**R:** Que correrlo una o varias veces deja el mismo estado final. Importa porque los pipelines se
reintentan tras fallos o se re-ejecutan; si no es idempotente, se duplican o corrompen datos.

**P:** Da un ejemplo de guardado NO idempotente y cómo arreglarlo.
**R:** `to_csv(ruta, mode="a")` o `to_sql(if_exists="append")` sin llave: cada corrida agrega las
mismas filas (144 → 288 → 432). Se arregla sobrescribiendo (`mode="w"`, `if_exists="replace"`,
reescribir la partición) o con *upsert* por llave.

**P:** ¿Para qué sirven los `assert` en un pipeline? ¿Por qué validar antes y después?
**R:** Detienen el pipeline con un mensaje claro si los datos no cumplen lo esperado. Antes de
transformar se valida formato/esquema (¿sigue llegando '63%'?); después, reglas de negocio
(¿posesión ~100? ¿marcador coherente con el resultado?).

**P:** ¿Qué hace `df["home_shots_on_target"].str.extract(r"(\d+)\s*of\s*(\d+)")`?
**R:** Devuelve un DataFrame con dos columnas (una por grupo de captura): los tiros a puerta y los
tiros totales, todavía como texto; luego se convierten con `astype(int)`.

**P:** ¿Diferencia entre `dropna()`, `dropna(how="all")` y `dropna(subset=["result"])`?
**R:** `dropna()` borra cualquier fila con al menos un nulo (aquí borraría también los 3 partidos
con 0 of 0 atajadas); `how="all"` solo las filas totalmente vacías (las 7 separadoras);
`subset=["result"]` las filas donde falta la etiqueta.

**P:** ¿Por qué en un pipeline de ML es mejor `SimpleImputer` que `fillna(df.median())`?
**R:** Porque `SimpleImputer` aprende la mediana solo con entrenamiento (`fit`) y aplica ese mismo
valor a prueba y a datos nuevos; `fillna` sobre todo el df usa información de prueba (fuga).

**P:** ¿Cuál es la diferencia entre un data pipeline y un ML pipeline?
**R:** El data pipeline entrega datos listos; el ML pipeline usa esos datos para entrenar,
evaluar, desplegar y monitorear un modelo. El primero alimenta al segundo.

**P:** ¿En qué fases de CRISP-DM vive un pipeline de datos?
**R:** Data Understanding (inspección y validación) y Data Preparation (limpieza y
transformación). Su salida alimenta Modeling.

**P:** ¿Qué es `df.pipe(f)` y por qué se usa?
**R:** Es equivalente a `f(df)`, pero permite encadenar funciones propias en el mismo estilo que los
métodos de pandas, de modo que el pipeline se lee de arriba a abajo en el orden en que ocurre.

**P:** Al unir la tabla de partidos como local y como visitante, ¿por qué `how="outer"`?
**R:** Para no perder equipos que aparezcan solo en una de las dos tablas; con `inner` desaparecerían.
Luego `fillna(0)` porque "no jugó de local" significa 0 puntos de local.

## 🏋️ Ejercicios

1. **Validación nueva:** agrega a `validar_limpio` una regla que verifique que
   `home_shots_on_target_pct` ≈ `hechos / intentos * 100` (tolerancia 0.1). ¿Pasa en todos los
   partidos? ¿Qué haces con los de 0 intentos?
2. **Rompe la idempotencia a propósito:** cambia `guardar` para que escriba con
   `mode="a"` y corre `correr_pipeline()` tres veces. Luego arréglalo con un *upsert*: lee el
   archivo existente, haz `concat` con lo nuevo y `drop_duplicates(subset=["date",
   "home_team", "away_team"], keep="last")`.
3. **Pipeline incremental:** separa el CSV en dos archivos por fecha (antes y después del 1 de
   diciembre). Haz que el pipeline procese el primero, luego el segundo, y que el resultado
   final sea idéntico a procesar todo junto.
4. **ELT en miniatura:** carga el CSV crudo a una base SQLite (`sqlite3` + `to_sql`) y escribe la
   transformación de la posesión y los goles **en SQL** (`REPLACE`, `CAST`, `SUBSTR`). Compara
   con la versión pandas.
5. **Tabla por jornada:** con `groupby("jornada")` calcula cuántos partidos y qué proporción de
   victorias locales hubo en cada fecha. ¿En qué jornada el local ganó más?

## 🔗 Referencias

- Portafolio del equipo (Ejercicio 2 y Tarea 3 en la sección Talleres):
  [Andyfer004/Portafolio-MLOPS](https://github.com/Andyfer004/Portafolio-MLOPS)
- IBM. [What is a data pipeline?](https://www.ibm.com/think/topics/data-pipeline) (incluye el
  video *Data Pipelines Explained*)
- IBM. [What is a machine learning pipeline?](https://www.ibm.com/think/topics/machine-learning-pipeline)
- IBM. [What is a data pipeline architecture?](https://www.ibm.com/think/topics/data-pipeline-architecture)
- IBM. [What is ETL?](https://www.ibm.com/think/topics/etl)
- DataCamp. [Introduction to Data Pipelines for Data Professionals](https://www.datacamp.com/tutorial/introduction-to-data-pipelines-for-data-professionals)
- pandas. [User Guide](https://pandas.pydata.org/docs/user_guide/index.html) ·
  [Working with text data](https://pandas.pydata.org/docs/user_guide/text.html) ·
  [Group by](https://pandas.pydata.org/docs/user_guide/groupby.html) ·
  [Merge, join, concatenate](https://pandas.pydata.org/docs/user_guide/merging.html)
- scikit-learn. [Imputation of missing values](https://scikit-learn.org/stable/modules/impute.html)
