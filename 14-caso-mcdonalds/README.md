# 14 · Caso de estudio 2: el sistema de puntos de MiMcDonald's

🎬 Video: [▶️ en español](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/14-caso-mcdonalds-es.mp4) · [▶️ in English](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/14-caso-mcdonalds-en.mp4) · [todos los videos](https://github.com/DiegoLinares11/RepasoMLOps/releases/tag/videos)

En el Caso de Estudio 2 nos tocó hacer de **consultores**: McDonald's Guatemala tiene un programa
de puntos, **MiMcDonald's**, que nadie documentó, y el cliente no nos dio ni un dato. Este tema
junta casi todo el curso en un solo proyecto: CRISP-DM (tema 03), medallion en Databricks
(tema 11), calidad de datos, validación sin fuga (tema 01) y un modelo que se compara contra
un baseline. La idea que deja es un **orden**: primero documentar el sistema, después medirlo y
hasta el final meterle machine learning.

---

## 🧱 Conocimiento previo

### 1. Cómo funciona un programa de puntos

| Término | Qué significa | En MiMcDonald's |
|---|---|---|
| **Acumulación** | Ganar puntos por comprar | 10 puntos por cada Q1 |
| **Canje** | Cambiar puntos por una recompensa | Recompensas de 3,000 a 7,500 puntos |
| **Tope** | Máximo que se puede ganar en un periodo | 1,000 puntos por día |
| **Vencimiento** | Los puntos dejan de valer después de un tiempo | 365 días |
| **Lote** | Los puntos de una misma compra, que vencen juntos | Cada compra crea un lote |
| **Breakage** | Puntos que vencen sin que nadie los use | Lo que se "rompe" del programa |
| **Pasivo** | Para la empresa, cada punto vivo es una deuda con el cliente | El saldo total de todos |

### 2. CRISP-DM, ahora con las seis fases

En el tema 03 vimos a fondo la primera fase. Este caso recorre las seis, en orden:

| Fase | Pregunta en este caso |
|---|---|
| Entendimiento del negocio | ¿Qué reglas tiene el programa? |
| Entendimiento de los datos | ¿Qué sistemas generan datos y con qué problemas? |
| Preparación de datos | ¿Cómo armamos una réplica confiable? |
| Modelado | ¿Qué recompensa le mostramos a cada cliente? |
| Evaluación | ¿Cómo demostramos que la réplica calcula bien? |
| Despliegue | ¿Qué le recomendamos a McDonald's? |

### 3. Procesamiento por lotes (*batch*)

Hay dos formas de procesar datos: **en línea**, cada evento en cuanto llega, o **por lotes**,
todo lo del día de un solo golpe (por ejemplo, de noche). Los términos del programa dicen que los
puntos se acreditan en un **máximo de 24 horas**: esa es la huella típica de un proceso nocturno
por lotes. Un dato pequeño de la documentación ya te dice cómo está construido el sistema.

### 4. La arquitectura medallion (repaso del tema 11)

Los datos pasan por tres capas, cada una con una responsabilidad:

- **Bronze**: lo que llegó, tal cual, sin corregir nada. Es la evidencia.
- **Silver**: lo limpio, tipado, sin duplicados y unificado. Lo que no se puede arreglar va a
  **cuarentena** con su motivo; nunca se borra en silencio.
- **Gold**: las reglas del negocio aplicadas, listas para reportes y modelos.

### 5. El libro de movimientos (*ledger*)

Tu banco no guarda tu saldo como un número que va sobrescribiendo: guarda **cada movimiento**
(depósitos y retiros), y el saldo es la suma. Así cualquier saldo se puede auditar, y si algo sale
mal se puede reconstruir. A ese libro de movimientos se le llama **ledger**.

### 6. FIFO

*First In, First Out*: lo primero que entra es lo primero que sale. En una bodega se despacha
primero la mercadería más vieja, y en la refri se come primero lo que se va a arruinar. Con
puntos que vencen, un canje debe gastar primero los puntos **más viejos**.

### 7. Suma acumulada por grupo (*window function*)

Una suma acumulada recorre las filas en orden y va sumando: `[600, 300, 400]` se vuelve
`[600, 900, 1300]`. Si se hace **por grupo** (por cliente y por día), se reinicia en cada grupo.
En SQL y Spark esto es una *window function* (`SUM(...) OVER (PARTITION BY ... ORDER BY ...)`);
en pandas, `groupby(...).cumsum()`.

### 8. Baseline, hit@1 y precisión/recall

- Un **baseline** es la solución tonta contra la que se compara el modelo. Aquí: recomendarle a
  todos lo más popular. Si el modelo no le gana al baseline, no sirve.
- **hit@1**: ¿el primer elemento recomendado es el que el usuario eligió? Es la proporción de
  aciertos en el primer lugar, como el banner principal de la app.
- **Precisión y recall** (de clasificación): cuántas alarmas eran ciertas y cuántos casos reales
  se detectaron. En este caso se usan para algo distinto: medir si la limpieza encontró
  exactamente los errores que había.

---

## 🎯 Qué tienes que saber

### 1. El encargo: diagnosticar un sistema sin documentación y sin datos

McDonald's Guatemala, operado por la franquicia **McDonald's Mesoamérica** (126 restaurantes),
lanzó **MiMcDonald's** el 27 de agosto de 2025 para reemplazar a *Puntos McDelivery*. Quienes
diseñaron el sistema ya no están en la empresa y no quedó documentación. El reto fue doble:
**entender el sistema desde afuera** y **demostrar que lo entendimos**.

### 2. Paso 1: documentar las reglas y lo que falta

Las reglas se reconstruyeron de los **Términos y Condiciones** oficiales: **22 reglas**. Las que
mueven los puntos:

| ID | Regla | Valor |
|---|---|---|
| R1–R2 | Acumulación | 10 puntos por cada Q1, redondeando hacia arriba (precios con IVA) |
| R6–R7 | Canales | Acumulan mostrador, AutoMac, kioscos, McCafé y la app. **No** acumulan apps de terceros, Call Center ni WhatsApp |
| R8 | Tope | 1,000 puntos por día |
| R9 | Acreditación | Máximo 24 horas (procesamiento por lotes) |
| R10–R11 | Vencimiento | 365 días por lote, con aviso 30 días antes |
| R15 | Mínimo para canjear en McDelivery | Q50 en desayuno y Q60 en almuerzo y cena |
| R16 | Catálogo | De 3,000 a 7,500 puntos; cambia sin aviso |
| R21 | Migración | Los puntos anteriores "se convierten automáticamente" |

Igual de importante es lo que **no** dice la documentación. Se encontraron **8 vacíos** (H1–H8)
y cada uno se resolvió con un **supuesto explícito** que el cliente debe validar:

| ID | Vacío | Supuesto |
|---|---|---|
| H1 | No se publica la tasa de conversión del programa anterior | ×10 (1 pt/Q → 10 pts/Q) |
| H2 | No es explícito si el IVA suma puntos | Sí, se usa el total pagado |
| H3 | No se dice qué pasa con una orden anulada | No acumula |
| H5 | El tope no define zona horaria ni orden | Día de Guatemala, en orden cronológico |
| H6 | "Dos correos = dos cuentas" y el teléfono es opcional | Se detectan cuentas de la misma persona |

> **Por qué importa:** un supuesto escrito se puede discutir y corregir. Un supuesto escondido
> en el código es un error esperando a pasar.

### 3. Paso 2: inferir la arquitectura actual

Sin acceso a los sistemas, se dedujo cómo fluyen los datos: las compras en el restaurante pasan
por el **POS** y llegan al motor de lealtad **por lotes**; las de la app entran directo. Un
detalle clave: el POS solo conoce el **código QR** del cliente, no quién es. En el diagrama, lo
inferido se dibujó con borde punteado, para no presentarlo como un hecho.

### 4. Paso 3: datos sintéticos con hoja de respuestas

Como no había datos, el notebook `00_generador_datos.py` simula los **6 sistemas origen**, cada
uno con su formato, como en la vida real: el POS manda CSV con hora local, la app manda JSON
anidado con hora UTC y campos en inglés, y el CRM manda un solo arreglo JSON. Son 5,250 cuentas,
30 restaurantes y 13 meses de operación: **56,239 tickets**, con **18 tipos de error** inyectados
a propósito (archivos reenviados, canales mal escritos, precios con coma decimal, QR inexistentes,
eventos duplicados, cuentas duplicadas, saldos negativos, entre otros).

La decisión que más sirvió: el generador lleva **su propia contabilidad** en Python puro y la
guarda como **hoja de respuestas** en un Volume aparte, que el pipeline nunca lee. Al final se
comparan **dos implementaciones independientes** de las mismas reglas.

### 5. Paso 4: la réplica medallion

| Capa | Qué hace |
|---|---|
| Landing | Los archivos tal como los "envían" los sistemas (un Volume) |
| Bronze | Cada fuente como tabla, **sin corregir nada** (todo texto), más el archivo de origen y la fecha de ingesta. 6 tablas |
| Silver | Limpia, tipa, deduplica y **unifica POS y app** en hora de Guatemala; lo irrecuperable va a cuarentena con su motivo |
| Gold | Aplica las **reglas del programa**: ledger de puntos, saldos, vencimientos, KPIs y violaciones. 8 tablas |

La frase que resume la frontera entre capas: **Silver describe qué pasó y Gold decide qué
significa**. Si mañana McDonald's cambia la tasa de puntos, solo se toca Gold.

### 6. El tope diario sin ciclos

Si `S` es la suma acumulada de los puntos calculados del cliente en el día, en orden cronológico,
cada compra recibe:

```
otorgados = min(1000, S) - min(1000, S - puntos)
```

| Compra | Puntos calculados | S (acumulado) | Otorgados |
|---|---|---|---|
| 1 | 600 | 600 | 600 − 0 = **600** |
| 2 | 300 | 900 | 900 − 600 = **300** |
| 3 | 400 | 1,300 | 1,000 − 900 = **100** |

Todo cabe en una sola *window function* de PySpark:

```python
mismo_dia = (Window.partitionBy("customer_id", "fecha_gt")
                   .orderBy("fecha_hora_gt", "transaccion_id")
                   .rowsBetween(Window.unboundedPreceding, Window.currentRow))
compras = (compras
    .withColumn("suma_dia", F.sum("puntos_calculados").over(mismo_dia))
    .withColumn("puntos_otorgados",
        F.least(tope, F.col("suma_dia"))
        - F.least(tope, F.col("suma_dia") - F.col("puntos_calculados"))))
```

### 7. El saldo no se guarda: se calcula

Como cada lote vence por separado, un solo número de "saldo" no dice qué parte vence cuándo. Por
eso Gold arma un **ledger**: cada compra es un abono que crea un lote, cada canje es un cargo que
consume primero el lote **más viejo** (FIFO), y antes de cada movimiento se vencen los lotes que
cumplieron 365 días. El saldo es lo que queda, y se puede rastrear hasta la compra que lo originó.

Esto **no cabe en SQL**: lo que vence de un lote depende de lo que consumieron los canjes
anteriores, y eso depende de lo que venció antes. Se resolvió cliente por cliente con
`applyInPandas`, que Spark reparte en paralelo:

```python
def procesar_lotes(pdf):
    lotes = []                                    # [fecha, puntos_restantes]
    for fila in pdf.sort_values(["fecha_gt", "fecha_hora_gt"]).itertuples():
        vencer(fila.fecha_gt)                     # fecha del lote + 365 <= hoy
        if fila.puntos > 0:
            lotes.append([fila.fecha_gt, fila.puntos])   # abono: nace un lote
        else:
            costo = -fila.puntos                         # canje: lo más viejo primero
            for lote in lotes:
                usar = min(lote[1], costo)
                lote[1] -= usar; costo -= usar

lotes = movimientos.groupBy("customer_id").applyInPandas(procesar_lotes, ...)
```

### 8. La prueba funcional (POC): 39 de 39

`05_evaluacion` compara todo contra la hoja de respuestas:

| Parte | Qué se probó | OK |
|---|---|---|
| A. Reglas | Cada regla sobre **todos** sus casos reales, con el resultado esperado calculado aparte | 12 / 12 |
| B. Calidad de datos | Los registros detectados contra los inyectados, uno por uno | 18 / 18 |
| C. Saldos | Gold contra la hoja de respuestas, cliente por cliente | 8 / 8 |
| D. Recomendador | Recomendaciones contra el gusto real de cada cliente | 1 / 1 |

Dos ideas que vale la pena llevarse:

- **Comparar registros, no conteos.** Si Silver detecta 100 errores y se inyectaron 100, podría
  ser casualidad: dos errores distintos se compensan. Por eso se compararon los registros: **0
  faltantes y 0 falsas alarmas**. Es la lógica de *recall* y *precisión*, aplicada a la limpieza.
- **Dos implementaciones independientes.** Python puro en el generador y Spark en Gold llegan al
  mismo saldo en los **5,150 clientes, con 0 diferencias**. Eso convence mucho más que "el
  código corrió sin errores".

### 9. Los hallazgos

| Hallazgo | Evidencia |
|---|---|
| El tope diario castiga a **McDelivery**, el canal que más gasta | Pierde el **39 %** de sus puntos, contra un **17 %** en caja. El 67 % de sus pedidos pasa de Q100 |
| **Breakage** alto | 8.1 millones de puntos vencidos, el 44 % de lo acumulado por compras. Los puntos migrados vencen todos juntos al año |
| La app no valida el mínimo de canje en McDelivery | 33 canjes por debajo de Q50 / Q60 |
| El catálogo no atiende a todos | El **café**, la única recompensa barata de desayuno, salió del catálogo en junio |
| No hay verificación de identidad | 150 cuentas duplicadas cobrando la bienvenida |
| No se publicó la tasa de conversión del programa anterior | Riesgo reputacional y contable |

¿Por qué el tope castiga a McDelivery? Con 10 puntos por quetzal y un tope de 1,000, **todo lo
que se gaste arriba de Q100 en un día no genera puntos**. Los pedidos a domicilio son los más
grandes, así que los clientes que más gastan son los peor tratados.

### 10. El recomendador de recompensas

La pregunta: **¿qué recompensa le mostramos a cada cliente en la app?** El diseño es de **dos
etapas**, como en los recomendadores reales: primero se toman como candidatas las recompensas
vigentes y luego un modelo de *gradient boosting* las ordena según el gusto del cliente, el costo
contra su saldo, la hora y la popularidad. El modelo queda en **MLflow** y **Unity Catalog** y
escribe `gold_recomendaciones` con un mensaje para la app ("Te faltan 500 puntos para tu
McFlurry").

Tres lecciones de ingeniería:

1. **Primero los baselines.** Con la primera versión de los datos, ningún modelo le ganaba a
   "recomendar lo más popular": a los datos les faltaban gustos. Se generó una segunda versión
   con perfiles de gusto por cliente.
2. **Validación temporal.** Variables hasta el 20 de junio y etiqueta con los canjes del 20 de
   junio al 20 de septiembre: nada del futuro entra a las variables. Es la misma fuga de
   información del tema 01 con `score` y `winner`.
3. **El modelo evaluado es el que se despliega.** scikit-learn activa el *early stopping* del
   gradient boosting solo cuando hay más de 10,000 filas, así que el modelo de producción se
   entrenaba distinto al evaluado. Se fijó explícitamente.

**Resultado:** el modelo acierta la recompensa del banner principal (hit@1) un **39 % más** que
recomendar lo más popular: **0.495 contra 0.356**. Contra el gusto real de cada cliente, que el
modelo nunca vio, también gana (0.62 contra 0.52).

Lo más interesante fue lo que reveló: el segmento **desayuno no lo atiende ni el modelo ni la
lista popular**. No es culpa del algoritmo sino del **catálogo**: las recompensas de desayuno
cuestan 5,000 y 7,500 puntos, y la única barata, el café, salió en junio. Además, la variable que
más pesa es el **costo**: el modelo predice bien lo que la gente canjea, que es lo barato. Si
McDonald's quiere otra cosa (más visitas o un ticket más alto), **qué optimizar es una decisión
de negocio**, no técnica.

### 11. Cómo entraría el modelo a producción

| Aspecto | Propuesta |
|---|---|
| Inferencia | Nocturna, después de Gold, con el saldo del día |
| Reentrenamiento | Mensual o cuando cambie el catálogo; el modelo nuevo solo reemplaza al actual si le gana a él y a los baselines |
| Monitoreo | hit@1 semanal con los canjes reales, clics del banner y diversidad de lo recomendado |
| Validación real | Prueba A/B de 30 días: la mitad ve el catálogo actual y la otra el recomendado |
| LLM | Un LLM (`ai_query()` en Databricks) redacta el mensaje, pero **no** decide qué recompensa ofrecer |

### 12. La lección: documentar, medir y después ML

El orden del caso es el orden de MLOps:

1. **Documentar** el sistema: reglas, vacíos y supuestos.
2. **Medirlo**: una réplica que calcule igual que una contabilidad independiente.
3. Hasta entonces, **machine learning**, comparado contra un baseline.

El modelo fue lo último y no lo más valioso: los hallazgos más fuertes (el tope, el breakage, el
catálogo) salieron de documentar y medir. **Limitación:** los datos son sintéticos; la POC
demuestra que el pipeline aplica bien las reglas, y el siguiente paso sería validarlas con el
cliente y correrlo con sus datos reales.

---

## 📂 Qué hicimos en el curso

Caso de Estudio 2 en equipo (Diego Linares, Andy Fuentes, Christian Echeverria y Diederich
Solis): **[MLOPS-Caso-de-estudio-2](https://github.com/DiegoLinares11/MLOPS-Caso-de-estudio-2)**.
Se trabajó fase por fase de CRISP-DM en **Databricks Free Edition** (Serverless, Unity Catalog,
Volumes, tablas Delta y MLflow), con PySpark, pandas, scikit-learn, diagramas en Mermaid y el repo
conectado al workspace con *Git folders*.

| Notebook | Qué hace |
|---|---|
| `00_generador_datos.py` | Genera las 6 fuentes sintéticas y la hoja de respuestas |
| `01_bronze.py` | Landing → 6 tablas `bronze_*`, todo como texto |
| `02_silver.py` | Bronze → tablas `silver_*` limpias y unificadas, y verifica que se detectaron los errores |
| `03_gold.py` | Silver → ledger de puntos, saldos, KPIs y violaciones, con cuadre contable |
| `04_recomendador.py` | Recomendador de recompensas con MLflow y Unity Catalog |
| `05_evaluacion.py` | POC contra la hoja de respuestas; guarda `eval_resultados_poc` |

El cuadre de la POC, cliente por cliente:

| Métrica | Total | Clientes con diferencia |
|---|---|---|
| Acumulados por compras | 18,581,394 | 0 de 5,150 |
| Bienvenida | 4,336,000 | 0 de 5,150 |
| Migrados del programa anterior | 17,835,600 | 0 de 5,150 |
| Canjeados | 20,729,000 | 0 de 5,150 |
| Vencidos | 8,097,012 | 0 de 5,150 |
| Perdidos por el tope diario | 5,277,554 | 0 de 5,150 |
| **Saldo al 20 de septiembre de 2026** | **11,926,982** | **0 de 5,150** |

Las propuestas de mayor prioridad del reporte: subir el tope o excluir a McDelivery (como mínimo,
avisarle al cliente), validar el mínimo de canje en la app y verificar el teléfono con OTP al
registrarse. En lo técnico: Auto Loader para ingesta incremental, `MERGE` en Gold, movimientos de
reverso para anulaciones tardías, *expectations* de Lakeflow y orquestación con Lakeflow Jobs.

---

## 🧪 Práctica

`repaso.ipynb` arma una réplica en miniatura del caso en pandas, sin Databricks ni internet, en
menos de un minuto:

1. Las reglas como constantes y funciones (`puntos_de(12.75)` da 128).
2. Un generador de datos sintéticos (1,500 clientes, 20,296 tickets) con gustos ocultos, puntos
   migrados y su propia **hoja de respuestas**.
3. **Bronze** con 5 tipos de error inyectados, **Silver** con cuarentena, y la comparación de
   registros: 0 faltantes y 0 falsas alarmas.
4. **Gold** con el tope sin ciclos (`groupby().cumsum()`): McDelivery pierde el 29.7 % de sus
   puntos y los canales del restaurante entre 2 y 6 %.
5. El **ledger FIFO** y la **POC**: 0 diferencias en los 1,500 clientes. La primera versión del
   notebook dio 1 diferencia por un error del generador, y la POC lo encontró.
6. El **breakage**: casi todo vence en agosto de 2026, cuando cumplen un año los puntos migrados.
7. El **recomendador** con validación temporal: "lo más popular" acierta 0.354 y una regresión
   logística 0.718; en el segmento desayuno, lo que canjean de su gusto baja de 82 % a 57 %
   cuando sale el café.

Los números de la simulación no son los del caso; lo que se repite es el **patrón**.

```powershell
.venv\Scripts\Activate.ps1
jupyter lab 14-caso-mcdonalds/repaso.ipynb
# para regenerarlo después de editar repaso.py:
python tools/build_nb.py 14-caso-mcdonalds/repaso.py
```

---

## ❓ Preguntas tipo examen

**P:** ¿Por qué se usaron datos sintéticos y qué condición deben cumplir para servir?
**R:** Porque el cliente no entregó datos. Deben respetar las reglas del programa y traer errores
conocidos, para poder comprobar que el pipeline aplica las reglas y detecta los errores.

**P:** ¿Qué es la "hoja de respuestas" y por qué el pipeline nunca la lee?
**R:** Es la contabilidad que el generador lleva en Python puro mientras simula. Si el pipeline la
leyera, la comparación final sería trampa: deben ser dos implementaciones independientes.

**P:** ¿Qué es un vacío de documentación y qué se hace con él?
**R:** Algo que las reglas no definen (por ejemplo, la zona horaria del tope). Se resuelve con un
supuesto explícito y escrito, que el cliente debe validar.

**P:** ¿Qué pista de la documentación indica que el sistema procesa por lotes?
**R:** Que los puntos se acreditan en un máximo de 24 horas.

**P:** Completa: "Silver describe ___ y Gold decide ___".
**R:** Qué pasó; qué significa. Silver limpia y unifica; Gold aplica las reglas del negocio.

**P:** ¿Qué capa cambia si McDonald's sube la tasa a 20 puntos por quetzal?
**R:** Solo Gold, que es donde viven las reglas. Bronze y Silver quedan igual.

**P:** Un cliente compra 600, 300 y 400 puntos el mismo día. ¿Cuántos recibe en cada compra?
**R:** 600, 300 y 100: las sumas acumuladas son 600, 900 y 1,300, y cada compra recibe
`min(1000, S) − min(1000, S − puntos)`.

**P:** ¿Por qué el saldo no se guarda como un número?
**R:** Porque los puntos vencen por lote: hay que saber qué parte del saldo vence cuándo. El saldo
se calcula sumando el ledger, y así se puede auditar hasta la compra que lo originó.

**P:** ¿Por qué el vencimiento FIFO no cabe en una consulta SQL?
**R:** Porque lo que vence de un lote depende de lo que consumieron los canjes anteriores, y eso
depende de lo que venció antes: cada paso depende del anterior. Se resolvió cliente por cliente
con `applyInPandas`.

**P:** ¿Por qué no basta con comparar conteos para validar la limpieza?
**R:** Porque dos errores pueden compensarse (uno que sobra y otro que falta dan el mismo total).
Se comparan los registros: faltantes y falsas alarmas, como recall y precisión.

**P:** ¿Por qué el tope diario castiga a McDelivery?
**R:** Porque arriba de Q100 en un día ya no se ganan puntos, y en McDelivery el 67 % de los
pedidos pasa de Q100. Pierde el 39 % de sus puntos contra un 17 % en caja.

**P:** ¿Qué es el breakage y por qué fue tan alto?
**R:** Los puntos que vencen sin usarse. Fueron 8.1 millones (44 % de lo acumulado por compras),
en buena parte porque los puntos migrados del programa anterior vencieron todos juntos al año.

**P:** ¿Cómo se evitó la fuga de información en el recomendador?
**R:** Con validación temporal: las variables se calcularon hasta el 20 de junio y la etiqueta con
los canjes del 20 de junio al 20 de septiembre.

**P:** ¿Por qué el segmento desayuno no queda bien atendido aunque el modelo le gane al baseline?
**R:** Porque es un problema del catálogo: el café salió en junio y lo que queda de desayuno cuesta
5,000 o 7,500 puntos. Ningún algoritmo arregla eso; es una decisión de negocio.

**P:** ¿Qué papel tiene el LLM en la propuesta?
**R:** Solo redacta el mensaje de la recompensa con `ai_query()`. La decisión de qué recompensa
ofrecer la toma el modelo, que se puede medir y auditar.

---

## 🏋️ Ejercicios

1. **Cambia una regla.** En `repaso.py`, sube `TOPE_DIARIO` a 1,500 y vuelve a correr. ¿Cuánto baja
   el porcentaje perdido de McDelivery? ¿Tuviste que tocar Bronze o Silver?
2. **Un error nuevo.** Inyecta en Bronze fechas con otro formato (`"11/03/2026 16:42"`) en el 1 %
   de las filas. Haz que Silver las recupere y que la tabla de calidad lo compruebe con 0
   faltantes y 0 falsas alarmas.
3. **Rompe el pipeline a propósito.** Cambia el FIFO de `procesar_lotes` para que consuma el lote
   más **nuevo** primero. ¿Qué métricas de la POC detectan el cambio y en cuántos clientes?
4. **Arregla el catálogo.** Agrega una recompensa de desayuno de 3,000 puntos que no salga del
   catálogo. ¿Qué pasa con la columna "de su gusto (jun-sep)" del segmento desayuno?
5. **Piensa como consultor.** Escribe tres supuestos que harías si el programa no dijera si los
   puntos de una devolución parcial se descuentan, y cómo los validarías con el cliente.

---

## 🔗 Referencias

- Repo del caso: [MLOPS-Caso-de-estudio-2](https://github.com/DiegoLinares11/MLOPS-Caso-de-estudio-2)
  (documentación por fase en `docs/`, diagramas en `diagramas/`, notebooks y reporte final).
- Chapman, P. et al. (2000). *CRISP-DM 1.0: Step-by-step data mining guide*. SPSS.
- Databricks: [What is a medallion architecture?](https://www.databricks.com/glossary/medallion-architecture)
- Apache Spark: [`applyInPandas` (PySpark)](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.GroupedData.applyInPandas.html)
- McDonald's Guatemala: [Términos y Condiciones de la app](https://mcdonaldsdigital.com/GML/public/app/gt/terminos-y-condiciones)
- Temas relacionados de este repo: [01 · fuga de información](../01-champions-eda/),
  [03 · CRISP-DM y caso de estudio 1](../03-caso-gasolina/), [11 · Databricks y medallion](../11-databricks/).
