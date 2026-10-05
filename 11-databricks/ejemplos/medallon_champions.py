# Databricks notebook source
# =============================================================================
# medallon_champions.py  -  Ejercicio 4 / Actividad 7 (Ejecicio3-MLOPS/databricks/)
# -----------------------------------------------------------------------------
# Notebook REAL (formato "source" de Databricks) con comentarios de repaso
# agregados. El código es idéntico al original.
#
# Cómo leer este formato:
#   "# Databricks notebook source"  -> 1a línea: Databricks lo importa como notebook
#   "# COMMAND ----------"          -> separador de CELDAS
#   "# MAGIC %md"                   -> celda Markdown (texto)
#   "# MAGIC %sql"                  -> celda SQL (comando mágico)
#   (sin MAGIC)                     -> celda Python (el lenguaje por defecto)
#
# Variables que existen solas en un notebook de Databricks (no hay que importarlas):
#   spark    -> la SparkSession conectada al cluster
#   display  -> muestra un DataFrame como tabla interactiva (con gráficas)
#   dbutils  -> utilidades (archivos, secrets, widgets)
#
# Qué construye: workspace.champions.partidos_bronze -> _silver -> _gold
# (Esta celda de comentarios es del repaso; el notebook original empieza en la siguiente.)
# =============================================================================

# COMMAND ----------

# MAGIC %md
# MAGIC # Estructura medallón en Unity Catalog
# MAGIC
# MAGIC Curso **Machine Learning Engineering (MLE/MLOps)** — Universidad del Valle de Guatemala
# MAGIC
# MAGIC Diego Linares · Andy Fuentes · Christian Echeverria · Diederich Solis
# MAGIC
# MAGIC Construye las tres capas del medallón sobre el dataset de la UEFA Champions League.
# MAGIC
# MAGIC **Importante para el linaje:** cada capa lee la **tabla** anterior con `spark.table(...)`,
# MAGIC no un DataFrame que quedó en memoria. Esa es la única forma en que Unity Catalog registra
# MAGIC la dependencia entre tablas y arma el grafo de linaje solo.

# COMMAND ----------

# Unity Catalog nombra todo con TRES niveles:  catálogo.esquema.tabla
#   catálogo "workspace" -> el catálogo por defecto de la edición Free / workspace nuevo
#   esquema  "champions" -> la "carpeta" de este proyecto (en SQL clásico, una base de datos)
CATALOGO = "workspace"
ESQUEMA = "champions"

# spark.sql(...) ejecuta SQL desde Python.
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOGO}.{ESQUEMA}")   # idempotente: no truena si ya existe
spark.sql(f"USE CATALOG {CATALOGO}")                             # contexto por defecto, como "cd"
spark.sql(f"USE SCHEMA {ESQUEMA}")

print(f"[setup] trabajando en {CATALOGO}.{ESQUEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Capa BRONCE — los datos tal como llegan
# MAGIC
# MAGIC Sin limpiar nada: 151 filas, incluidas las 7 vacías que separan jornadas y las columnas que
# MAGIC revelan el resultado. Bronce existe para poder auditar: si mañana dudamos de un dato, aquí
# MAGIC está el original.

# COMMAND ----------

import pandas as pd

# Se lee el CSV directo de GitHub (raw): así no hay que subir archivos al workspace.
URL = ("https://raw.githubusercontent.com/DiegoLinares11/Ejecicio3-MLOPS/"
       "main/datos/champions_league_matches.csv")

crudo = pd.read_csv(URL)
# Única "transformación" en bronce: nombres de columna sin espacios, porque Delta no
# acepta ciertos caracteres en los nombres. El CONTENIDO no se toca.
crudo.columns = [c.strip().replace(" ", "_") for c in crudo.columns]

(spark.createDataFrame(crudo)                      # pandas -> DataFrame de Spark
      .write.mode("overwrite")                     # reemplaza la tabla si ya existía (nueva versión Delta)
      .option("overwriteSchema", "true")           # permite que cambien las columnas/tipos
      .saveAsTable(f"{CATALOGO}.{ESQUEMA}.partidos_bronze"))   # tabla Delta administrada en UC

print(f"[bronce] {crudo.shape[0]} filas x {crudo.shape[1]} columnas")
display(spark.table(f"{CATALOGO}.{ESQUEMA}.partidos_bronze").limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Capa PLATA — limpia y con tipos correctos
# MAGIC
# MAGIC Se lee **la tabla bronce** y se aplica lo que descubrimos en el Ejercicio 1: quitar las
# MAGIC filas vacías, descartar `score` y `winner` porque revelan el resultado, y convertir a
# MAGIC número la posesión (`'63%'`) y los tiros (`'3 of 10'`).

# COMMAND ----------

from pyspark.sql import functions as F   # funciones de columna de Spark (col, when, avg, regexp...)

# CLAVE DEL LINAJE: se lee la TABLA registrada, no la variable `crudo` de la celda anterior.
bronce = spark.table(f"{CATALOGO}.{ESQUEMA}.partidos_bronze")   # <-- lee la TABLA: esto crea linaje

plata = (
    bronce
    .filter(F.col("result").isNotNull())              # quita las 7 filas vacías (no tienen result)
    .drop("score", "winner", "venue", "referee")      # fuga (score, winner) + irrelevantes
    # '63%' -> 63.0 : quitar el % y convertir a double
    .withColumn("home_possession_pct",
                F.regexp_replace("home_possession", "%", "").cast("double"))
    .withColumn("away_possession_pct",
                F.regexp_replace("away_possession", "%", "").cast("double"))
    # '3 of 10' -> 3 (grupo antes de "of") y 10 (grupo después de "of")
    .withColumn("home_shots_on_target_n",
                F.regexp_extract("home_shots_on_target", r"(\d+)\s*of", 1).cast("int"))
    .withColumn("home_shots_total",
                F.regexp_extract("home_shots_on_target", r"of\s*(\d+)", 1).cast("int"))
    .withColumn("away_shots_on_target_n",
                F.regexp_extract("away_shots_on_target", r"(\d+)\s*of", 1).cast("int"))
    .withColumn("away_shots_total",
                F.regexp_extract("away_shots_on_target", r"of\s*(\d+)", 1).cast("int"))
    # ya convertidas, las columnas de texto originales sobran
    .drop("home_possession", "away_possession",
          "home_shots_on_target", "away_shots_on_target")
)
# Nota: Spark es PEREZOSO (lazy). Hasta aquí no se calculó nada; solo se armó el plan.
# El trabajo real ocurre al escribir (saveAsTable) o al pedir un resultado (count, display).
# Nota 2: date, home_saves y away_saves se quedan como venían (texto); solo se tipan
# posesión y tiros.

plata.write.mode("overwrite").option("overwriteSchema", "true") \
     .saveAsTable(f"{CATALOGO}.{ESQUEMA}.partidos_silver")

print(f"[plata] {bronce.count()} -> {plata.count()} partidos")   # 151 -> 144
display(spark.table(f"{CATALOGO}.{ESQUEMA}.partidos_silver").limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Capa ORO — lista para consumir
# MAGIC
# MAGIC Se lee **la tabla plata** y se arma lo que de verdad usa quien consume: un resumen por
# MAGIC equipo local, con su rendimiento agregado.

# COMMAND ----------

silver = spark.table(f"{CATALOGO}.{ESQUEMA}.partidos_silver")   # <-- lee la TABLA: mas linaje

oro = (
    silver.groupBy("home_team")                        # una fila por equipo LOCAL
    .agg(
        F.count("*").alias("partidos_de_local"),
        # contar victorias: 1 si result == "Home Win", 0 si no, y sumar
        F.sum(F.when(F.col("result") == "Home Win", 1).otherwise(0)).alias("victorias"),
        F.sum(F.when(F.col("result") == "Draw", 1).otherwise(0)).alias("empates"),
        F.round(F.avg("home_possession_pct"), 1).alias("posesion_promedio"),
        F.round(F.avg("home_shots_on_target_n"), 1).alias("tiros_a_puerta_promedio"),
    )
    .withColumn("tasa_de_victoria",
                F.round(F.col("victorias") / F.col("partidos_de_local"), 3))
    .orderBy(F.col("tasa_de_victoria").desc())
)

oro.write.mode("overwrite").option("overwriteSchema", "true") \
   .saveAsTable(f"{CATALOGO}.{ESQUEMA}.partidos_gold")

print(f"[oro] resumen de {oro.count()} equipos")
display(spark.table(f"{CATALOGO}.{ESQUEMA}.partidos_gold").limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## El linaje ya quedó registrado
# MAGIC
# MAGIC No hay que hacer nada más: Unity Catalog capturó las dependencias solo, porque cada capa
# MAGIC leyó la tabla anterior.
# MAGIC
# MAGIC ```
# MAGIC partidos_bronze  --->  partidos_silver  --->  partidos_gold
# MAGIC ```
# MAGIC
# MAGIC **Para verlo y tomar el comprobante:**
# MAGIC
# MAGIC 1. En la barra lateral, abrir **Catalog**
# MAGIC 2. Navegar a `workspace` > `champions` > `partidos_silver`
# MAGIC 3. Entrar a la pestaña **Lineage**
# MAGIC 4. Ver el grafo: arriba de dónde viene y abajo qué alimenta
# MAGIC
# MAGIC El linaje puede tardar un par de minutos en aparecer después de correr el notebook.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Celda SQL: el comando mágico %sql cambia el lenguaje SOLO de esta celda.
# MAGIC -- Las tres capas ya son consultables con SQL
# MAGIC SELECT home_team AS equipo,
# MAGIC        partidos_de_local,
# MAGIC        victorias,
# MAGIC        tasa_de_victoria,
# MAGIC        posesion_promedio
# MAGIC FROM workspace.champions.partidos_gold
# MAGIC WHERE partidos_de_local >= 3
# MAGIC ORDER BY tasa_de_victoria DESC
# MAGIC LIMIT 10

# COMMAND ----------

# MAGIC %md
# MAGIC ## Resumen de lo construido
# MAGIC
# MAGIC | Capa | Tabla | Qué contiene |
# MAGIC |---|---|---|
# MAGIC | Bronce | `partidos_bronze` | Los datos crudos, sin tocar, para poder auditar |
# MAGIC | Plata | `partidos_silver` | Limpio, sin fuga de información y con tipos correctos |
# MAGIC | Oro | `partidos_gold` | Resumen por equipo, listo para consumir |
# MAGIC
# MAGIC Cada capa responde a una pregunta distinta: bronce a *"¿qué llegó exactamente?"*, plata a
# MAGIC *"¿en qué puedo confiar?"* y oro a *"¿qué necesita quien lo va a usar?"*.

# COMMAND ----------

# Lista las tablas del esquema: deben aparecer partidos_bronze, partidos_silver, partidos_gold.
display(spark.sql(f"SHOW TABLES IN {CATALOGO}.{ESQUEMA}"))

# Para practicar Delta (no estaba en el original), en una celda %sql:
#   DESCRIBE HISTORY workspace.champions.partidos_silver;          -- versiones de la tabla
#   SELECT * FROM workspace.champions.partidos_silver VERSION AS OF 0;   -- time travel
