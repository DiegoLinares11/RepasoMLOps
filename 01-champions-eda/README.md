# 01 · EDA del dataset de la Champions League

🎬 Video: `champions\champions-es.mp4` (también en inglés: `-en.mp4`, y hojas de revisión `revision-es.png`).

El análisis exploratorio (EDA) del Ejercicio 1 / Lab 02 fue la base de **todo** el curso:
cada cosa rara que encontramos en el CSV se convirtió después en una línea de código del
pipeline. Si entiendes este tema, entiendes por qué el pipeline de los temas 05, 06, 09 y
10 tiene la forma que tiene.

---

## 🧱 Conocimiento previo

### 1. Un dataset tabular

Una tabla donde **cada fila es una observación** (aquí, un partido) y **cada columna es una
variable** (equipo local, posesión, tiros...). En pandas se carga con
`pd.read_csv(...)` y queda en un `DataFrame`.

### 2. El `dtype`: cómo pandas "cree" que es cada columna

Al leer un CSV, pandas adivina el tipo de cada columna:

| dtype | Significa | Ejemplo |
|---|---|---|
| `float64` / `int64` | número | `30.0` |
| `object` / `str` | texto | `'PSV'`, `'63%'` |
| `datetime64` | fecha (solo si se lo pides con `parse_dates`) | `2025-09-16` |

Si una columna tiene **un solo carácter no numérico** (como `%` u `of`), pandas la lee
**toda** como texto. Un modelo de scikit-learn no puede usar texto directamente, así que
hay que convertirla.

### 3. ¿Qué es un EDA y por qué va antes de modelar?

**EDA** (*Exploratory Data Analysis*) es mirar los datos con preguntas: ¿cuántas filas hay?
¿qué tipo tiene cada columna? ¿hay nulos? ¿hay valores imposibles? ¿cómo se distribuye la
variable objetivo? ¿qué se relaciona con qué?

> **Analogía:** un médico no receta antes de preguntar síntomas y ver análisis. Modelar sin
> EDA es recetar a ciegas: el modelo "funciona", pero no sabes si aprendió algo real o si
> está haciendo trampa con una columna que no debería ver.

### 4. Tipos de variables

| Tipo | Subtipo | Qué es | Ejemplo general |
|---|---|---|---|
| **Numérica** | continua | puede tomar cualquier valor en un rango | posesión 63.0 % |
| | discreta | conteos | 3 tiros a puerta |
| **Categórica** | nominal | categorías **sin orden** | equipo: PSV, Arsenal |
| | ordinal | categorías **con orden** | talla S < M < L |
| **Fecha/tiempo** | | un instante | 2025-09-16 |
| **Texto** | | texto libre | un comentario |

Y una trampa práctica: **texto que en realidad es número** (`'63%'`, `'3 of 10'`).

### 5. Clasificación multiclase, variable objetivo y baseline

- **Variable objetivo** (*target*, `y`): lo que queremos predecir. Aquí `result`.
- **Clasificación multiclase:** `y` tiene más de dos categorías (Home Win, Away Win, Draw).
- **Baseline:** el modelo más tonto posible, por ejemplo "siempre predigo la clase más
  común". Cualquier modelo serio tiene que ganarle.

### 6. Fuga de información (*data leakage*)

Una variable tiene fuga cuando contiene información que **no estaría disponible en el
momento de predecir**, o que es directa o indirectamente la respuesta.

> **Analogía:** es dar un examen con la hoja de respuestas pegada debajo del escritorio.
> Sacas 100, pero no aprendiste nada y en el examen real (producción) no tendrás la hoja.

Con estas ideas, vamos al CSV.

---

## 🎯 Qué tienes que saber

### 1. El dataset en una tabla

`datos/champions_league_matches.csv`: fase de liga de la UEFA Champions League 2025/26.

| Dato | Valor |
|---|---|
| Filas crudas | 151 (7 vacías) → **144 partidos** |
| Columnas | 18 |
| Columnas numéricas al leer | solo 4 (`*_pct`); las otras 14 son texto |
| Equipos | 36, cada uno en **8 partidos** (4 de local, 4 de visita) |
| Objetivo | `result`: Home Win 71 · Away Win 48 · Draw 25 |

### 2. Hallazgo 1: filas vacías que separan jornadas

```python
df.isna().all(axis=1).sum()      # 7
```

Las 7 filas vacías aparecen **cada 19 filas** (índices 18, 37, 56, ..., 132): son
**separadores visuales** entre bloques de 18 partidos, como cuando se copia una tabla de una
página web que agrupa por jornada. 144 = 8 bloques × 18 partidos.

**¿Por qué importa?** Si no se quitan:
- `value_counts()` y las proporciones de clase salen mal.
- Un `SimpleImputer` las rellenaría con medianas, creando **7 partidos fantasma**.

**Decisión:** `df.dropna(how="all")` es el primer paso del filtrado en todos los repos.

### 3. Hallazgo 2: los cuatro tipos de variables del dataset

| Tipo | Columnas | Ejemplo | Tratamiento en el pipeline |
|---|---|---|---|
| Numérica ya limpia | `home/away_shots_on_target_pct`, `home/away_saves_pct` | `30.0` | imputar (mediana) → estandarizar |
| Texto que es número: **porcentaje** | `home_possession`, `away_possession` | `'63%'` | quitar `%` → `63.0` → imputar → estandarizar |
| Texto que es número: **razón** | `home/away_shots_on_target`, `home/away_saves` | `'3 of 10'` | separar en **hechos = 3** e **intentos = 10** → imputar → estandarizar |
| Categórica nominal | `home_team`, `away_team` | `'PSV'` | imputar (moda) → One-Hot |

Columnas que **no** entran:

| Columna | Por qué se descarta |
|---|---|
| `score`, `winner` | **Fuga**: revelan el resultado |
| `date` | Fecha: se podría convertir en "jornada", pero no se usó |
| `venue` (38 valores), `referee` (42 valores) | Alta cardinalidad para 144 filas: casi una categoría por partido |

### 4. Hallazgo 3: convertir el texto que es número (y **validar** la conversión)

**Posesión** `'63%'` → `63.0`:

```python
df["home_possession"].str.rstrip("%").astype(float)
```

Validación de sentido común: local + visita debería dar 100. Da **100 en 132 partidos y
101 en 12**. Es redondeo de la fuente (50.6 % y 50.4 % publicados como 51 % y 50 %), no un
error.

**Tiros y atajadas** `'3 of 10'` → dos columnas:

```python
partes = df["home_saves"].str.extract(r"(\d+)\s*of\s*(\d+)").astype(float)
hechos, intentos = partes[0], partes[1]
```

¿Por qué dos columnas y no una división? Porque `'1 of 1'` y `'10 of 10'` dan el mismo 100 %,
pero no significan lo mismo: un portero que atajó 10 tiros tuvo un partido muy distinto al
que atajó 1. La Actividad 1 empaquetó estas conversiones en dos transformadores propios,
`PorcentajeATexto` y `RatioATexto`, para que se apliquen **dentro del pipeline** igual a
train, test y a cada dato nuevo que llegue a la API.

Validación cruzada entre columnas: `hechos / intentos × 100` reproduce exactamente
`home_shots_on_target_pct` (diferencia máxima 0.0). Conclusión doble: la conversión está
bien, y las columnas `*_pct` son **redundantes**.

### 5. Hallazgo 4: los nulos que quedan tienen explicación

Tras quitar las filas vacías quedan **3 nulos en `home_saves_pct`**, y los tres son
partidos con `home_saves = '0 of 0'`: el visitante no tiró ni una vez a puerta, así que el
porcentaje es 0/0, **indefinido**. No es un dato perdido, es una división entre cero.

**Decisión:** imputar con la mediana dentro del pipeline. La Actividad 3 incluso calibró
`median` vs. `mean` y comprobó que la decisión no movía el resultado: saber que algo **no**
importa también es un hallazgo.

### 6. Hallazgo 5: la variable objetivo está desbalanceada

| Clase | Partidos | Proporción |
|---|---|---|
| Home Win | 71 | 49.3 % |
| Away Win | 48 | 33.3 % |
| Draw | 25 | 17.4 % |

Consecuencias:

1. **Baseline:** "siempre gana el local" ya acierta 49.3 %. En el test de 29 partidos de la
   Actividad 1 eso fue 0.483 (14 de 29).
2. **Accuracy engaña:** un modelo que nunca predice empate puede tener buen accuracy.
   Por eso desde la Actividad 3 se optimiza **`f1_macro`**: el promedio del F1 de las tres
   clases, cada una con el mismo peso.
3. **Estratificar:** `train_test_split(..., stratify=y)` y `StratifiedKFold` para que los
   pocos empates queden repartidos en train y test.

> **F1 en una línea:** el F1 de una clase combina *precision* (de los que predije como
> empate, ¿cuántos lo eran?) y *recall* (de los empates reales, ¿cuántos encontré?) con una
> media armónica: F1 = 2·P·R / (P + R).

### 7. Hallazgo 6: fuga de información, en tres niveles

**Nivel 1 — Fuga directa: `score` y `winner`.** Con `score` (`'1–3'`) o con `winner`
(`'Union SG'` o `'Draw'`) se reconstruye `result` al **100 %**. Un árbol entrenado con la
diferencia de goles saca accuracy **1.000** en validación cruzada. Inútil: para saber el
marcador, el partido ya terminó. Detalle práctico: el marcador usa un guion largo `–`, no
`-`, así que `split("-")` falla.

**Nivel 2 — Fuga indirecta: tiros y atajadas esconden los goles.** Un tiro a puerta termina
en gol o en atajada, así que:

```
goles del local ≈ tiros a puerta del local − atajadas del portero visitante
```

En los datos, las atajadas *intentadas* del portero local son **exactamente** los tiros a
puerta acertados del visitante (100 % de coincidencia), y la resta reproduce el marcador
exacto en 70.8 % (local) y 81.9 % (visita) de los partidos. Con esa sola resta, sin mirar
`score`, se recupera el resultado en el **84.7 %** de los partidos. Esto explica la
limitación que escribimos en las Actividades 1 y 3: *"las variables se conocen cuando el
partido ya terminó, así que el modelo **explica** el resultado más de lo que lo
**predice**"*.

**Nivel 3 — Fuga temporal** (se ve en el tema 03): usar información de fechas posteriores a
la predicción. Aquí no aplica porque cada partido es independiente, pero si quisiéramos
predecir **antes** del partido con el historial de cada equipo, solo valdrían partidos
anteriores.

| Tipo de fuga | Ejemplo en este dataset | Cómo se detecta | Qué se hizo |
|---|---|---|---|
| Directa | `score`, `winner` | Reconstruyen la `y` al 100 % | Se eliminan siempre (`LEAKAGE_COLUMNS`) |
| Indirecta | tiros − atajadas ≈ goles | Una combinación simple de variables predice demasiado bien | Se documentó como limitación |
| Temporal | (historial con partidos futuros) | Revisar que cada variable use solo datos anteriores | — |

**Regla para el examen:** pregúntate de cada columna *"¿la tendría disponible en el momento
exacto en que necesito la predicción?"*. Si la respuesta es no, fuera.

### 8. Hallazgo 7: qué se relaciona con el resultado

Correlación con `gana_local` (1 si Home Win):

| Variable | Correlación |
|---|---|
| tiros a puerta acertados del visitante | −0.439 |
| tiros a puerta acertados del local | +0.427 |
| % atajadas del portero local | +0.370 |
| % tiros a puerta del local | +0.350 |
| posesión del local | +0.219 |

Lectura: **tener el balón no es ganar**. Lo que separa los resultados es la eficacia
(tiros a puerta) y los porteros. La mediana del % de atajadas del portero local es 83.3 %
cuando gana el local y 53.6 % cuando gana la visita. Los **empates quedan en medio**,
traslapados con las otras dos clases: por eso todos los modelos del curso fallan más en
`Draw` (F1 0.286 en la Actividad 1, 0.364 en la Actividad 3).

### 9. Hallazgo 8: los equipos traen poca información

36 equipos × 8 partidos cada uno. El One-Hot de `home_team` y `away_team` crea **72
columnas** con apenas 4 "unos" cada una. Sumadas a las 14 numéricas, salen las **86
columnas** del preprocesamiento de las Actividades 1 y 3. Con 115 filas de entrenamiento,
eso invita al sobreajuste (tema 02); por eso en la Actividad 3 `SelectKBest` con k = 30
rindió mejor que usar las 86, y la importancia por permutación dejó a los equipos en casi
cero.

### 10. Cómo el EDA definió el preprocesamiento de todo el curso

```
CSV crudo (151 × 18)
  │  dropna(how="all")                       ← Hallazgo 1 (filas vacías)
  │  drop(score, winner)                     ← Hallazgo 6 (fuga)
  │  drop(date, venue, referee)              ← Hallazgo 2 (no aportan / alta cardinalidad)
  ▼
144 × 13  ──► ColumnTransformer
               ├── numéricas   : SimpleImputer(median) → StandardScaler   ← Hallazgo 5 (0 of 0)
               ├── porcentajes : PorcentajeATexto → imputar → escalar     ← Hallazgo 3
               ├── razones     : RatioATexto → imputar → escalar          ← Hallazgo 3
               └── categóricas : imputar(moda) → OneHotEncoder            ← Hallazgo 8
           ──► (SelectKBest en la Act. 3)                                 ← Hallazgo 8
           ──► modelo, evaluado con f1_macro y stratify=y                 ← Hallazgo 6 (desbalance)
```

Y en producción: la API de la Actividad 4 recibe la posesión como `"43%"` y los tiros como
`"15 of 28"`, **tal como vienen en el CSV**, porque la conversión es parte del pipeline.

---

## 📂 Qué hicimos en el curso

- **Ejercicio 1 / Lab 02 (EDA):** exploración de los 151 partidos: se detectaron las filas
  vacías que separan jornadas, las columnas numéricas guardadas como texto y las que revelan
  el resultado. Según el portafolio del equipo, *"esos hallazgos definieron el
  preprocesamiento de todo lo que vino después"*. Se propuso el modelo: clasificación
  multiclase de `result`.
- **Actividad 1** ([repo](https://github.com/DiegoLinares11/Actividad1-MLOPS)) tomó la tabla
  de hallazgos y la convirtió en código (`data.py` con `LEAKAGE_COLUMNS = ["score",
  "winner"]` y `DROP_COLUMNS = ["date", "venue", "referee"]`; `transformers.py` con
  `PorcentajeATexto` y `RatioATexto`):

  | Hallazgo del Ejercicio 1 | Cómo lo atiende el pipeline |
  |---|---|
  | 7 filas totalmente vacías | Se eliminan en el filtrado (quedan 144 partidos) |
  | Posesión como `'63%'` | `PorcentajeATexto` |
  | Tiros/atajadas como `'3 of 10'` | `RatioATexto` (hechos e intentos) |
  | Nulos en `home_saves_pct` (`0 of 0`) | Imputación por mediana |
  | Equipos = categóricas | One-Hot Encoding |

  Resultado: 12 columnas crudas → 86 numéricas → `RandomForestClassifier`, **accuracy 0.724**
  en 29 partidos de prueba (baseline 0.483). Empates: F1 0.286 (detectó 1 de 5).
- **Ejercicio 3** reutilizó el mismo filtrado en `src/limpiar.py` ("quita filas vacías y
  columnas con fuga de información") como un job de GitHub Actions.

---

## 🧪 Práctica

`repaso.ipynb` hace el EDA completo sobre `../datos/champions_league_matches.csv`:

```bash
cd RepasoMLOps
python tools/build_nb.py 01-champions-eda/repaso.py
```

Qué trae y qué sale:

| Sección | Resultado real |
|---|---|
| Filas vacías | 7, en los índices 18, 37, …, 132 (cada 19) → 8 bloques de 18 partidos |
| Posesión | de 24 % a 77 %, media 51 %; suma 100 en 132 partidos y 101 en 12 |
| `hechos/intentos` vs `*_pct` | coinciden exactamente (diferencia máxima 0.0) |
| Nulos | 3 en `home_saves_pct`, todos `'0 of 0'` |
| Clases | 71 / 48 / 25 → baseline 0.493 |
| Fuga directa | `score` y `winner` reconstruyen `result` al 100 % |
| Fuga indirecta | resta tiros − atajadas: 84.7 % de resultados correctos |
| Árbol (`max_depth=4`, CV 5-fold) | diferencia de goles **1.000** · goles sueltos 0.924 · tiros−atajadas **0.847** · 14 estadísticas 0.652 |
| Correlaciones | heatmap + ranking contra `gana_local` |
| Boxplots | posesión separa poco; % de atajadas separa mucho |
| Equipos | 36, exactamente 8 partidos cada uno |

---

## ❓ Preguntas tipo examen

**P:** ¿Cuántas filas tiene el CSV y cuántos partidos reales hay? ¿Por qué la diferencia?
**R:** 151 filas y 144 partidos. Hay 7 filas totalmente vacías, una cada 19 filas, que separan bloques de 18 partidos (jornadas); se quitan con `dropna(how="all")`.

**P:** ¿Por qué `home_possession` aparece como texto y cómo se convierte?
**R:** Porque trae el símbolo `%` (`'63%'`) y pandas lee toda la columna como texto. Se quita el `%` y se convierte a float: `str.rstrip("%").astype(float)`.

**P:** ¿Por qué `'3 of 10'` se convierte en dos columnas y no en un porcentaje?
**R:** Porque el porcentaje pierde información: `'1 of 1'` y `'10 of 10'` dan 100 % pero describen partidos muy distintos. Se guardan hechos e intentos (y además el porcentaje ya existe en las columnas `*_pct`).

**P:** ¿Por qué hay 3 nulos en `home_saves_pct` y qué se hizo?
**R:** Son partidos con `'0 of 0'` atajadas: el porcentaje es 0/0, indefinido. Se imputan con la mediana dentro del pipeline.

**P:** ¿Cuáles son los cuatro tipos de variables del dataset que maneja el pipeline?
**R:** Numéricas ya limpias (`*_pct`), porcentajes en texto (posesión), razones en texto (tiros y atajadas) y categóricas nominales (equipos).

**P:** ¿Qué es fuga de información y qué columnas la tienen aquí?
**R:** Una variable con información no disponible al momento de predecir o que revela la respuesta. `score` y `winner` revelan el resultado y se eliminan.

**P:** ¿Por qué tiros a puerta y atajadas se consideran una fuga indirecta?
**R:** Porque goles ≈ tiros a puerta − atajadas del rival; con esa resta se recupera el 84.7 % de los resultados. Además solo se conocen cuando el partido terminó, así que el modelo explica el resultado pero no lo predice de antemano.

**P:** ¿Cuál es el baseline y por qué importa?
**R:** Predecir siempre "Home Win": 49.3 % en los 144 partidos (0.483 en los 29 de prueba). Un modelo que no lo supere no aporta nada; el Ejercicio 3 lo usa como compuerta de calidad.

**P:** ¿Por qué usar `f1_macro` y no accuracy?
**R:** Porque las clases están desbalanceadas (25 empates de 144). El accuracy premia acertar la clase mayoritaria; `f1_macro` promedia el F1 de las tres clases con el mismo peso y obliga a tomarse en serio los empates.

**P:** ¿Por qué se usa `stratify=y` en el split?
**R:** Para que la proporción de las tres clases sea la misma en train y test; sin estratificar, los pocos empates podrían quedar casi todos de un lado.

**P:** ¿De dónde salen las 86 columnas del preprocesamiento?
**R:** 14 numéricas (4 `*_pct` + 2 posesiones + 4 razones × 2) + 72 del One-Hot de 36 equipos locales y 36 visitantes.

**P:** ¿Por qué se descartan `venue` y `referee`?
**R:** Tienen 38 y 42 valores distintos en 144 partidos: casi una categoría por fila, sin patrones que aprender, y solo añaden columnas que invitan al sobreajuste.

**P:** ¿Qué variable se relaciona más con que gane el local y cuál menos de las principales?
**R:** Los tiros a puerta acertados (+0.427 los del local, −0.439 los del visitante) y el % de atajadas (+0.370). La posesión apenas +0.219: tener el balón no es ganar.

**P:** ¿Por qué el EDA es importante para MLOps y no solo para el análisis?
**R:** Porque cada hallazgo se convierte en código versionado del pipeline (filtrado, transformadores, imputación, métrica), que se aplica igual en entrenamiento, prueba y producción.

---

## 🏋️ Ejercicios

1. **Jornada como variable.** Usa los bloques de 18 partidos para crear una columna
   `jornada` (1 a 8). ¿Cambia la proporción de victorias locales por jornada?
2. **Ventaja de localía.** Calcula la proporción de victorias locales y visitantes, y la media
   de goles de local vs. visita a partir de `score`. ¿Existe ventaja de localía en esta
   Champions?
3. **Variables sin fuga.** Diseña 3 variables que **sí** se conocerían antes del partido
   usando solo jornadas anteriores (por ejemplo, puntos acumulados de cada equipo). ¿Cuántos
   partidos pierdes en la primera jornada?
4. **Fuga indirecta, parte 2.** Entrena una regresión logística solo con
   `home_shots_on_target_hechos`, `away_shots_on_target_hechos`, `home_saves_hechos`,
   `away_saves_hechos`. Compara su accuracy en CV con el 0.652 del árbol con las 14
   variables. ¿Qué te dice?
5. **Validación automática.** Escribe una función `validar(df)` que lance un error si: hay
   filas vacías, la posesión no suma 100 ± 1, o `hechos > intentos`. Es el tipo de
   validación de datos que un pipeline de MLOps ejecuta en cada corrida.

---

## 🔗 Referencias

- [Actividad1-MLOPS](https://github.com/DiegoLinares11/Actividad1-MLOPS): `src/act1_pipeline/data.py` (hallazgos documentados en el docstring) y `transformers.py`.
- [Actividad3-MLOPS](https://github.com/DiegoLinares11/Actividad3-MLOPS): baseline, `f1_macro`, importancias.
- [Ejecicio3-MLOPS](https://github.com/DiegoLinares11/Ejecicio3-MLOPS): `src/limpiar.py`.
- [Portafolio-MLOPS](https://github.com/Andyfer004/Portafolio-MLOPS): página de laboratorios (Lab 02).
- pandas, *Working with text data*: <https://pandas.pydata.org/docs/user_guide/text.html>
- scikit-learn, *Common pitfalls: data leakage*: <https://scikit-learn.org/stable/common_pitfalls.html#data-leakage>
- Kaufman, S. et al. (2012). *Leakage in Data Mining: Formulation, Detection, and Avoidance*. ACM TKDD.
