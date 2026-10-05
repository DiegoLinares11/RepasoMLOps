# 02 · Sobreajuste, sesgo-varianza y validación cruzada

🎬 Video: `overfitting\overfitting-es.mp4` (también en inglés: `-en.mp4`, y hojas de revisión `revision-es.png`).

El sobreajuste es la razón número uno por la que un modelo "espectacular en el notebook"
falla en producción. Este tema explica cómo detectarlo, cómo medir bien un modelo con pocos
datos (¡solo 144 partidos!) y qué perillas lo controlan.

---

## 🧱 Conocimiento previo

### 1. ¿Qué significa que un modelo "aprenda"?

Entrenar es **ajustar los parámetros** del modelo para que se equivoque lo menos posible en
los datos de entrenamiento. Una regresión lineal ajusta pendiente e intercepto; un árbol
decide qué preguntas hacer y en qué orden.

Pero el objetivo **no** es acertar en los datos que ya vio, sino en datos nuevos. A eso se
le llama **generalizar**.

> **Analogía:** un estudiante que se aprende de memoria las respuestas del examen del año
> pasado saca 100 en ese examen, pero reprueba el de este año. Otro que entendió los temas
> saca 85 en ambos. El primero **sobreajustó**: memorizó en vez de aprender.

### 2. Señal y ruido

Los datos tienen **señal** (el patrón real: más tiros a puerta → más probabilidad de ganar)
y **ruido** (azar: un rebote, un autogol, un penal dudoso). Un buen modelo captura la señal
e ignora el ruido. Un modelo sobreajustado aprende también el ruido, que no se repite en
datos nuevos.

### 3. Capacidad de un modelo

La **capacidad** es qué tan complejas pueden ser las funciones que el modelo puede aprender:

| Modelo | Perilla de capacidad | Poca capacidad | Mucha capacidad |
|---|---|---|---|
| Polinomio | grado | recta (grado 1) | grado 15 |
| Árbol de decisión | `max_depth`, `min_samples_leaf` | 1 pregunta | sin límite |
| Regresión logística | `C` (inverso de la regularización) | `C` muy chico | `C` muy grande |
| Boosting | número de árboles | pocos | miles |
| Cualquier modelo | número de variables | pocas | muchas (p. ej. 86 columnas para 115 filas) |

### 4. Métricas y datos "no vistos"

Para saber si un modelo generaliza hay que medirlo en datos que **no usó para aprender**.
Las métricas del curso: **accuracy** (proporción de aciertos) y **f1_macro** (promedio del F1
de cada clase con el mismo peso; ver tema 01).

---

## 🎯 Qué tienes que saber

### 1. Subajuste y sobreajuste

| | Subajuste (*underfitting*) | Buen ajuste | Sobreajuste (*overfitting*) |
|---|---|---|---|
| Qué pasa | El modelo es demasiado simple para el patrón | Captura la señal | Memoriza también el ruido |
| Error de entrenamiento | **Alto** | Bajo | **Muy bajo** (≈ 0) |
| Error de validación/prueba | **Alto** | Bajo | **Alto** |
| Brecha train-validación | Pequeña | Pequeña | **Grande** |
| Analogía | Estudiar solo el índice del libro | Entender los temas | Memorizar el examen pasado |

En el notebook, con 30 puntos de una curva seno: el polinomio de grado 1 tiene MSE de
prueba 0.258 (subajuste), el de grado 4 baja a **0.066** y el de grado 15 sube a 0.156
(sobreajuste), aunque su MSE de **entrenamiento** es el más bajo de los tres (0.024).

**Lección central:** el error de entrenamiento **siempre baja** al aumentar la capacidad.
Por eso **nunca** se elige un modelo mirando el error de entrenamiento.

### 2. El dilema sesgo-varianza

El error esperado de un modelo en datos nuevos se descompone en:

$$\text{Error} = \text{Sesgo}^2 + \text{Varianza} + \text{Ruido irreducible}$$

- **Sesgo:** error por suposiciones demasiado simples (una recta para una curva). Causa
  subajuste.
- **Varianza:** cuánto cambiaría el modelo si lo entrenaras con otra muestra de datos.
  Un árbol profundo cambia muchísimo con unos pocos partidos distintos. Causa sobreajuste.
- **Ruido irreducible:** el azar del fenómeno. Ningún modelo lo elimina (ningún modelo
  predice un autogol).

> **Analogía del tiro al blanco:** sesgo alto = todos los dardos agrupados pero lejos del
> centro. Varianza alta = dardos alrededor del centro pero muy dispersos. Lo ideal: agrupados
> y en el centro.

Subir la capacidad baja el sesgo y sube la varianza. El punto óptimo está en medio: la "U"
del error de prueba.

### 3. Train / validación / test: tres conjuntos, tres usos

| Conjunto | Para qué | Analogía | Cuántas veces se usa |
|---|---|---|---|
| **Entrenamiento** | El modelo **aprende** (ajusta parámetros) | Las tareas y el libro | Siempre |
| **Validación** | **Elegir** modelo e hiperparámetros | Los exámenes de práctica | Muchas veces |
| **Prueba** (*test*) | **Confirmar** el desempeño final, honesto | El examen final | **Una sola vez**, al final |

¿Por qué no basta con dos? Si eliges el hiperparámetro mirando el test, el test pasa a ser
parte del entrenamiento (lo "optimizaste") y ya no mide generalización. La Actividad 3 lo
dice como regla: *"el finalista se elige por el puntaje de validación cruzada, nunca mirando
el conjunto de prueba"*.

**Fuga entre conjuntos:** si calculas la media para imputar o el escalado con **todos** los
datos antes de separar, el test "contamina" el entrenamiento. Solución: meter la
preparación **dentro** de un `Pipeline` de scikit-learn, que hace `fit` solo con el train de
cada fold (tema 05).

### 4. Validación cruzada (CV)

Con 115 partidos de entrenamiento, separar otro 20 % para validación deja muy poco. La
**validación cruzada k-fold** reutiliza los datos:

```
Datos de entrenamiento (115 partidos) divididos en 5 folds:
  Iteración 1: [VAL][ tr ][ tr ][ tr ][ tr ]  → puntaje 1
  Iteración 2: [ tr ][VAL][ tr ][ tr ][ tr ]  → puntaje 2
  Iteración 3: [ tr ][ tr ][VAL][ tr ][ tr ]  → puntaje 3
  Iteración 4: [ tr ][ tr ][ tr ][VAL][ tr ]  → puntaje 4
  Iteración 5: [ tr ][ tr ][ tr ][ tr ][VAL]  → puntaje 5
  Resultado: media ± desviación estándar de los 5 puntajes
```

Cada partido se usa para validar **exactamente una vez**.

| Esquema | Qué hace | Cuándo usarlo |
|---|---|---|
| `KFold` | Corta en k bloques sin mirar la clase (con o sin barajar) | Regresión, o clases balanceadas |
| `StratifiedKFold` | Cada fold mantiene la proporción de clases | **Clasificación con clases desbalanceadas** (el curso) |
| `RepeatedStratifiedKFold` | Repite el anterior con distintas semillas | Pocos datos: suaviza el ruido |
| `TimeSeriesSplit` | Siempre entrena con el pasado y valida con el bloque siguiente | **Series de tiempo** (tema 03) |
| `GroupKFold` | Un mismo grupo (p. ej. un paciente) nunca está en train y validación a la vez | Datos con grupos |
| **CV anidada** | Un CV externo para medir y uno interno para calibrar | Estimación honesta después de buscar hiperparámetros |

Con 25 empates en 144 partidos, `KFold` sin barajar deja entre **3 y 7** empates por fold;
`StratifiedKFold` deja **5 en cada uno**.

**CV anidada (Actividad 3):** el `best_score_` de una búsqueda es optimista, porque
elegiste el mejor de muchos intentos sobre los mismos folds (como reportar tu mejor
lanzamiento de 96). La CV anidada recalibra dentro de cada fold externo. Resultado del
curso: `best_score_` de `GridSearchCV` **0.563** vs. CV anidada **0.541 ± 0.053**. Esa
diferencia es el optimismo de la búsqueda.

### 5. Curvas de validación y de aprendizaje

**Curva de validación** (`validation_curve`): mueve **un hiperparámetro** y grafica train vs.
validación.

```
puntaje
 1.0 ┤            ●───●───●───●   ← entrenamiento: sube hasta memorizar
     │        ●
     │    ●            brecha = sobreajuste
     │ ●  ■───■───■───■───■───■   ← validación: se aplana o baja
     └──────────────────────────► capacidad (max_depth, C, grado...)
       subajuste │ óptimo │ sobreajuste
```

**Curva de aprendizaje** (`learning_curve`): mueve **la cantidad de datos** de entrenamiento.

| Lo que ves | Diagnóstico | Qué hacer |
|---|---|---|
| Brecha grande y validación aún subiendo | Varianza: faltan datos | Conseguir más filas, regularizar |
| Las dos curvas juntas y bajas | Sesgo: el modelo o las variables no alcanzan | Más capacidad o **variables nuevas** |
| Validación plana desde cierto tamaño | Límite de información | Variables nuevas, no más filas |

En la Actividad 3, la curva de aprendizaje subió hasta ~66 partidos (f1_macro 0.638) y se
aplanó: *"el techo no lo pone la cantidad de datos ni la calibración, sino la información
que traen las variables"*.

### 6. Muestras pequeñas: la métrica también tiene error

Con 29 partidos de prueba, **cada acierto vale 1/29 = 3.4 puntos** de accuracy. Medir un
accuracy es como lanzar una moneda cargada n veces: la desviación estándar es
aproximadamente

$$\sigma \approx \sqrt{\frac{p(1-p)}{n_{test}}}$$

Con p ≈ 0.75 y n = 29, σ ≈ 0.08: un modelo con accuracy real de 0.75 puede salir 0.67 u 0.83
por pura suerte de la partición. Para reducir σ a la mitad se necesitan **4 veces** más
datos de prueba.

En el notebook, la misma regresión logística con 100 semillas distintas de
`train_test_split` dio accuracy de **0.655 a 0.897**. La media de CV 5-fold varió solo de
0.743 a 0.792.

**Qué hacer con pocos datos:** usar CV (repetida si se puede), reportar **media ±
desviación**, preferir modelos simples cuando las diferencias caen dentro del ruido y
desconfiar de mejoras de 1-2 puntos.

### 7. Remedios contra el sobreajuste

| Remedio | Cómo actúa | En scikit-learn |
|---|---|---|
| Limitar la complejidad del árbol | Menos preguntas, hojas con más datos | `max_depth`, `min_samples_leaf`, `min_samples_split` |
| **Regularización L2** (Ridge) | Penaliza coeficientes grandes: los encoge | `LogisticRegression(C=...)` (C chico = más freno), `Ridge(alpha=...)` |
| **Regularización L1** (Lasso) | Penaliza y lleva coeficientes a **cero**: selecciona variables | `penalty="l1"`, `Lasso` |
| Selección de variables | Menos columnas de ruido | `SelectKBest(k=...)` |
| Ensambles | Promediar muchos modelos baja la varianza | `RandomForestClassifier` (más árboles no sobreajustan más) |
| **Early stopping** | Detener el entrenamiento iterativo cuando la validación deja de mejorar | `GradientBoostingClassifier(n_iter_no_change=..., validation_fraction=...)` |
| Más datos | Más señal frente al ruido | — |
| Balanceo de clases | Que la clase pequeña cuente | `class_weight="balanced"` |

> **Analogía de la regularización:** es un "impuesto a la complejidad". El modelo puede
> usar coeficientes grandes, pero le cuestan; solo los usa si de verdad mejoran mucho el
> ajuste.

> **Analogía del early stopping:** estudiar para un examen haciendo ejercicios de práctica.
> Al principio cada hora mejora tu nota en los simulacros; llega un punto en que solo estás
> memorizando las respuestas de esos simulacros. Ahí paras.

### 8. ¿Qué tiene que ver con MLOps?

- Un modelo sobreajustado **se ve bien en el notebook y falla en producción**. Es la versión
  "de modelado" del "funciona en mi máquina".
- Por eso los pipelines de MLOps incluyen una **compuerta de calidad** que evalúa en datos
  reservados y compara contra un baseline (Ejercicio 3: `f1_macro ≥ 0.40` y ganarle al
  modelo trivial).
- La brecha train-validación es una métrica que vale la pena **registrar** en cada
  experimento (MLflow, tema 11).
- En producción, la caída de desempeño puede ser sobreajuste (nunca generalizó) o **drift**
  (el mundo cambió, tema 00). Distinguirlos requiere haber medido bien desde el principio.

---

## 📂 Qué hicimos en el curso

El sobreajuste apareció en cada entrega con el dataset de la Champions (115 partidos de
entrenamiento / 29 de prueba, estratificado, semilla 42):

- **Actividad 1** ([repo](https://github.com/DiegoLinares11/Actividad1-MLOPS)): bosque aleatorio
  con accuracy 0.724 en prueba, con la advertencia: *"el conjunto de prueba tiene solo 29
  partidos, así que la métrica tiene bastante margen de error"*.
- **Actividad 3** ([repo](https://github.com/DiegoLinares11/Actividad3-MLOPS)):
  - En `GridSearchCV`, `mean_train_score` **≈ 0.96-1.00** contra `mean_test_score` **≈ 0.56**:
    *"el bosque memoriza el entrenamiento casi perfecto"*. Esa brecha es lo que intentan cerrar
    `max_depth`, `min_samples_leaf` y `k`.
  - `max_depth` se calibró como *"**la** perilla de sobreajuste: sin límite, con 115 filas el
    árbol memoriza (`mean_train_score` ≈ 1.0)"*; limitarla casi no movió el promedio
    (0.522 vs. 0.516) pero redujo la brecha.
  - Curva de validación con `max_depth` ∈ {2, 3, 4, 6, 8, 12, None}: *"la curva de
    entrenamiento se dispara hacia 1.0 mientras la de validación se queda plana"*.
  - Curva de aprendizaje: partidos [27, 40, 53, 66, 79, 92] → f1_macro [0.554, 0.553, 0.617,
    0.638, 0.638, 0.619].
  - CV anidada **0.541 ± 0.053** (folds: 0.583, 0.608, 0.46, 0.505, 0.549) vs. `best_score_`
    0.563.
  - Ganó una **regresión logística regularizada** (`C=0.541`, `class_weight="balanced"`,
    `SelectKBest(k=40)`): *"con 115 filas y 86 columnas, una regresión logística regularizada
    resultó más adecuada que un bosque"*.
  - Limitación: *"29 partidos de prueba: cada acierto vale 3.4 puntos de accuracy"*.

---

## 🧪 Práctica

`repaso.ipynb` usa el dataset de la Champions limpio igual que en el tema 01 (14 variables
numéricas) y datos sintéticos:

```bash
cd RepasoMLOps
python tools/build_nb.py 02-overfitting/repaso.py
```

Resultados reales:

| Experimento | Resultado |
|---|---|
| Polinomios (MSE train / test) | grado 1: 0.198 / 0.258 · grado 4: 0.037 / **0.066** · grado 15: 0.024 / 0.156 |
| Árbol, `max_depth` 1 → 15 (115/29) | train de 0.661 a **1.000** (desde depth 9, 31 hojas); test nunca mejora: 0.552 → 0.483-0.517 (baseline 0.483) |
| `validation_curve` (StratifiedKFold 5, f1_macro) | train 0.486 → 1.000; validación plana 0.42-0.51, mejor en `max_depth=3` (0.509) |
| Empates por fold | KFold sin barajar [5, 7, 6, 4, 3] · StratifiedKFold [5, 5, 5, 5, 5] |
| Una partición vs. CV (regresión logística) | 100 semillas: 0.765 ± 0.049, rango **0.655-0.897** · CV 5-fold ×20: 0.768 ± 0.015 |
| `learning_curve` | validación 0.590 (23 partidos) → 0.629 (92); train 0.896 → 0.735 |
| Tamaño de muestra (σ del accuracy) | n=144: 0.089 (teoría 0.079) · n=500: 0.044 · n=2000: 0.018 · n=10000: 0.008 |
| Regularización `C` con 86 columnas | train = **1.000** desde C=0.1, validación máx. ≈ 0.55: sobreajuste por exceso de columnas |
| Regularización `C` con 14 numéricas | validación sube hasta ≈ 0.70 con C=1000 (explota la fuga indirecta del tema 01) |
| Early stopping (sintético) | 500 árboles: 0.887 · early stopping en **47 árboles**: 0.893 |

---

## ❓ Preguntas tipo examen

**P:** Define sobreajuste y subajuste en términos de error de entrenamiento y de validación.
**R:** Sobreajuste: error de entrenamiento muy bajo y de validación alto (brecha grande). Subajuste: ambos errores altos y parecidos.

**P:** ¿Por qué no se puede elegir un modelo con el error de entrenamiento?
**R:** Porque siempre baja al aumentar la capacidad; el modelo más complejo siempre "gana" en entrenamiento aunque generalice peor (grado 15: MSE train 0.024, test 0.156).

**P:** Explica la descomposición sesgo-varianza.
**R:** Error esperado = sesgo² + varianza + ruido irreducible. El sesgo viene de supuestos demasiado simples (subajuste); la varianza, de la sensibilidad a la muestra de entrenamiento (sobreajuste); el ruido no se puede eliminar.

**P:** ¿Para qué sirve cada conjunto: train, validación y test?
**R:** Train para ajustar parámetros, validación para elegir modelo e hiperparámetros, test para confirmar una sola vez el desempeño final de forma honesta.

**P:** ¿Qué pasa si eliges hiperparámetros mirando el test?
**R:** El test deja de ser independiente: lo optimizaste, así que su métrica sale optimista y ya no mide generalización.

**P:** ¿Diferencia entre KFold y StratifiedKFold? ¿Cuál usó el curso y por qué?
**R:** KFold corta sin mirar la clase; StratifiedKFold mantiene la proporción de clases en cada fold. El curso usó StratifiedKFold porque solo hay 25 empates en 144 partidos.

**P:** ¿Qué es la CV anidada y qué mostró en la Actividad 3?
**R:** Un CV externo que mide y uno interno que calibra hiperparámetros dentro de cada fold externo. Dio 0.541 frente al `best_score_` de 0.563: la diferencia es el optimismo de la búsqueda.

**P:** ¿Cómo se lee una curva de validación?
**R:** Si train sube hacia 1.0 y validación se aplana o baja, la brecha es sobreajuste; si ambas son bajas, subajuste; el mejor valor está en el máximo de validación (prefiriendo el más simple si varios empatan dentro del ruido).

**P:** La curva de aprendizaje se aplana desde ~66 partidos. ¿Qué conviene hacer?
**R:** Agregar variables nuevas con más información (historial de equipos, rachas), no más filas del mismo tipo.

**P:** ¿Cuánto vale un acierto con 29 partidos de prueba y qué implica?
**R:** 1/29 ≈ 3.4 puntos de accuracy. La métrica tiene un error de medición grande (σ ≈ √(p(1−p)/n) ≈ 0.08), así que diferencias de pocos puntos no son confiables.

**P:** ¿Qué hace el parámetro `C` de la regresión logística?
**R:** Es el inverso de la fuerza de regularización: C pequeño = mucha penalización a los coeficientes (modelo más simple); C grande = poca penalización (modelo más flexible).

**P:** ¿Diferencia entre regularización L1 y L2?
**R:** L2 encoge los coeficientes hacia cero sin anularlos; L1 puede llevarlos exactamente a cero, por lo que además selecciona variables.

**P:** ¿Qué es early stopping?
**R:** Detener un entrenamiento iterativo (boosting, redes) cuando el desempeño en un conjunto de validación interno deja de mejorar durante varias iteraciones; evita seguir ajustando ruido y ahorra cómputo.

**P:** ¿Por qué agregar el One-Hot de los equipos produjo sobreajuste?
**R:** Crea 72 columnas casi vacías (cada equipo aparece en 8 partidos) para ~115 filas: el modelo puede separar perfectamente el entrenamiento usando "quién jugó" (train = 1.000) sin que eso se repita en validación (≈ 0.55).

**P:** ¿Cómo se relaciona el sobreajuste con MLOps?
**R:** Un modelo sobreajustado se ve bien en el notebook y falla en producción; por eso el pipeline evalúa en datos reservados, compara con un baseline y aplica una compuerta de calidad antes de desplegar.

---

## 🏋️ Ejercicios

1. **Curva de validación de `min_samples_leaf`.** Repite la sección 4 con
   `min_samples_leaf` ∈ {1, 2, 3, 5, 8, 12, 20} y `max_depth=None`. ¿Qué valor cierra la
   brecha sin hundir la validación?
2. **Bosque vs. árbol.** Repite la sección 3 con `RandomForestClassifier(n_estimators=300)`.
   ¿Sigue llegando el train a 1.000? ¿Mejora el test? Relaciónalo con "promediar baja la
   varianza".
3. **L1 como selector.** Entrena `LogisticRegression(penalty="l1", solver="liblinear")` con las
   86 columnas y distintos `C`. Cuenta cuántos coeficientes quedan distintos de cero. ¿Cuáles
   sobreviven: equipos o estadísticas?
4. **CV anidada casera.** Implementa una CV anidada (5 folds externos, `GridSearchCV` interno
   sobre `max_depth`) para el árbol de la sección 3 y compara con el mejor puntaje de la
   `validation_curve`.
5. **¿Cuántos partidos necesitaría?** Con la fórmula σ ≈ √(p(1−p)/n), calcula cuántos
   partidos de prueba se necesitarían para que σ sea 0.02 con p = 0.7.

---

## 🔗 Referencias

- scikit-learn, *Cross-validation: evaluating estimator performance*: <https://scikit-learn.org/stable/modules/cross_validation.html>
- scikit-learn, *Validation curves: plotting scores to evaluate models*: <https://scikit-learn.org/stable/modules/learning_curve.html>
- scikit-learn, *Nested versus non-nested cross-validation*: <https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html>
- scikit-learn, *Early stopping in Gradient Boosting*: <https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_early_stopping.html>
- Hastie, Tibshirani y Friedman. *The Elements of Statistical Learning*, cap. 7 (Model Assessment and Selection).
- [Actividad3-MLOPS](https://github.com/DiegoLinares11/Actividad3-MLOPS): `evaluation.py` (curvas, CV anidada) y el notebook `calibracion_hiperparametros.ipynb`.
- [Actividad1-MLOPS](https://github.com/DiegoLinares11/Actividad1-MLOPS).
