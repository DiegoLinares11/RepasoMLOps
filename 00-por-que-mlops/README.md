# 00 · ¿Por qué MLOps?

🎬 Video: `mlops-general\mlops-general-es.mp4` (también en inglés: `-en.mp4`, y hojas de revisión `revision-es.png`).

Este es el tema "mapa": explica **qué problema resuelve MLOps** y cómo cada tema del curso
(01 a 11) arma una pieza del rompecabezas. Si solo tienes tiempo para un tema antes del
examen, que sea este.

---

## 🧱 Conocimiento previo

### 1. ¿Qué es un modelo de machine learning?

En programación tradicional **tú escribes las reglas**:

```python
def llega_tarde(distancia, trafico):
    return trafico + 0.6 * distancia > 9      # regla escrita por una persona
```

En machine learning **le das ejemplos y el algoritmo descubre la regla**: le pasas 3 000
pedidos con su distancia, su tráfico y si llegaron tarde o no, y el algoritmo encuentra
una función que se parece a la de arriba. Esa función aprendida es **el modelo**.

> **Analogía:** programar es darle a alguien una receta paso a paso. Hacer ML es darle
> 3 000 platos ya preparados y pedirle que deduzca la receta.

Consecuencia clave: **el comportamiento del modelo depende de los datos** con que se
entrenó, no solo del código. Si cambian los datos, cambia el modelo (aunque el código sea
idéntico). Esta frase es la semilla de todo MLOps.

### 2. Entrenamiento vs. inferencia

| Fase | Qué pasa | Cuándo | Ejemplo del curso |
|---|---|---|---|
| **Entrenamiento** (*training*) | El algoritmo aprende de datos históricos y produce un modelo (un archivo, p. ej. `modelo.joblib`) | De vez en cuando (horas/días) | El contenedor `entrenador` de la Actividad 4 |
| **Inferencia** (*serving*, *prediction*) | El modelo ya entrenado recibe un dato nuevo y devuelve una predicción | Todo el tiempo, en milisegundos | `POST /predecir` de la API FastAPI |

### 3. ¿Qué es "producción"?

Un modelo está **en producción** cuando personas o sistemas reales dependen de sus
predicciones: una app que te dice "tu pedido llegará tarde", un banco que aprueba o
rechaza créditos, una API que otros equipos consumen. Lo contrario es un modelo que vive
en un notebook en la laptop del científico de datos.

### 4. ¿Qué es DevOps?

Antes de MLOps existió **DevOps** (desarrollo + operaciones), la práctica de entregar
software de forma frecuente y confiable:

- **Control de versiones** (git): cada cambio queda registrado y se puede deshacer.
- **CI (integración continua):** en cada `push` se ejecutan pruebas automáticas.
- **CD (entrega/despliegue continuo):** si las pruebas pasan, el software se empaqueta y
  se despliega solo.
- **Infraestructura reproducible:** contenedores (Docker) para que "funcione igual en
  todas partes".
- **Monitoreo:** saber si el sistema está vivo y respondiendo.

> **Analogía:** DevOps es la línea de ensamblaje de una fábrica de carros. Antes, cada carro
> se armaba a mano y cada uno salía distinto; con la línea, cada carro pasa por las mismas
> estaciones de control de calidad.

### 5. ¿Qué es un pipeline?

Una secuencia de pasos automatizados donde la salida de uno es la entrada del siguiente.
En la Tarea 3 usamos la analogía de IBM: el agua no llega del río directo a tu llave;
pasa por recolección → tuberías → planta de tratamiento → distribución. Un pipeline de ML
hace lo mismo: datos crudos → limpieza → transformación → entrenamiento → evaluación →
modelo.

### 6. Métricas básicas

- **Accuracy:** proporción de aciertos.
- **F1 macro:** promedio del F1 de cada clase, dándole el mismo peso a todas (importa
  cuando hay clases pequeñas, como los empates en la Champions).
- **Baseline:** el modelo más tonto posible (p. ej. "siempre predigo la clase más común").
  Un modelo que no le gana al baseline no sirve.

Con estas piezas ya se entiende el resto.

---

## 🎯 Qué tienes que saber

### 1. El problema: los modelos no llegan a producción (o llegan y se pudren)

Una cifra muy citada (VentureBeat, 2019) dice que **alrededor del 87 % de los proyectos de
ciencia de datos nunca llegan a producción**. Es una estimación de la industria, no un
estudio riguroso, pero describe un patrón real. ¿Por qué pasa?

1. **"Funciona en mi máquina".** El notebook corre en la laptop de una persona, con *sus*
   versiones de pandas y scikit-learn, *su* copia del CSV y celdas ejecutadas en *cierto*
   orden. Nadie más puede reproducirlo.
2. **Nadie sabe con qué datos se entrenó.** Tres meses después, el CSV cambió, la semilla
   no estaba fija y el accuracy "oficial" ya no se puede reproducir.
3. **El paso a producción es un mundo distinto.** El científico de datos entrega un
   notebook; el equipo de software necesita una API, con pruebas, logs, seguridad y
   escalabilidad. Ese "tirar el notebook por encima de la pared" se rompe.
4. **El modelo se degrada en silencio.** Aunque llegue a producción, el mundo cambia (los
   clientes, los precios, el clima) y las predicciones empeoran **sin ningún error
   visible**. El servidor responde 200 OK con predicciones malas.

**MLOps** (*Machine Learning Operations*) es el conjunto de prácticas, herramientas y roles
para **llevar modelos a producción de forma reproducible y mantenerlos funcionando bien**.
Es DevOps adaptado a un mundo donde los datos también son "código".

### 2. La deuda técnica oculta en ML (Sculley et al., 2015)

El artículo *Hidden Technical Debt in Machine Learning Systems* (Google, NeurIPS 2015) tiene
la figura más famosa de MLOps: **el código del modelo es una cajita negra pequeña en medio
de una infraestructura enorme**.

```
┌────────────────────────────────────────────────────────────────────────┐
│  Configuración     Recolección de datos      Verificación de datos     │
│                                                                        │
│  Extracción de     ┌──────────┐     Gestión de recursos de máquina     │
│  características   │ CÓDIGO   │                                        │
│                    │   ML     │     Herramientas de análisis           │
│  Gestión de        └──────────┘                                        │
│  procesos          Infraestructura de serving        Monitoreo         │
└────────────────────────────────────────────────────────────────────────┘
        el modelo (fit/predict) es una fracción mínima del sistema
```

El `model.fit(X, y)` que tanto estudiamos son unas pocas líneas. Alrededor hay que
recolectar y verificar datos, extraer variables, configurar, servir las predicciones,
monitorear, gestionar recursos... Y **ahí** está la mayor parte del trabajo y de los bugs.

Ideas del artículo que conviene conocer:

| Concepto | Qué significa | Ejemplo |
|---|---|---|
| **CACE** (*Changing Anything Changes Everything*) | En ML nada está aislado: cambiar una variable, un hiperparámetro o la forma de limpiar cambia todo el modelo | Cambiar la imputación de `median` a `mean` cambia los coeficientes de todas las variables |
| **Código pegamento** (*glue code*) | Mucho código solo para conectar librerías y formatos | Convertir `'3 of 10'` a dos números antes de llamar a scikit-learn |
| **Junglas de pipelines** | Pasos de preparación agregados sin diseño, uno encima de otro | Notebooks que se llaman entre sí con archivos intermedios a mano |
| **Dependencias de datos inestables** | El modelo depende de datos que otro equipo puede cambiar sin avisar | La fuente del CSV empieza a mandar la posesión como `0.63` en vez de `'63%'` |
| **Ciclos de retroalimentación** | Las predicciones del modelo influyen en los datos futuros con que se reentrena | Un recomendador que solo muestra lo que ya predijo, y luego aprende de esos clics |

**Moraleja:** hacer el modelo es lo fácil. Lo difícil (y lo que pide el mercado laboral) es
el sistema alrededor.

### 3. DevOps vs. MLOps: ¿qué cambia?

En software tradicional, el comportamiento lo define **el código**. En ML lo definen
**tres cosas a la vez**: código + datos + modelo. Cualquiera de las tres puede cambiar y
romper el sistema.

| Aspecto | DevOps (software clásico) | MLOps (machine learning) |
|---|---|---|
| Qué se versiona | Código | Código **+ datos + modelos + hiperparámetros + ambiente** |
| Qué se prueba | Pruebas unitarias e integración | Lo anterior **+ validación de datos + validación del modelo** (¿le gana al baseline?) |
| Qué se despliega | Un binario o servicio | Un **pipeline de entrenamiento** y un **servicio de predicción** |
| Cómo falla | Error, excepción, caída (ruidoso) | **Degradación silenciosa**: responde normal pero predice peor |
| Por qué se vuelve a desplegar | Cambió el código | Cambió el código **o cambiaron los datos** (reentrenar) |
| Práctica nueva | — | **CT: entrenamiento continuo** (*continuous training*) |
| Equipo | Devs + Ops | Data scientists + data engineers + ML engineers + Ops |

> **Analogía:** el software clásico es una calculadora: 2 + 2 siempre da 4. Un modelo de ML
> es un pronosticador del clima entrenado con los veranos de 1990-2020: si el clima cambia,
> sus pronósticos empeoran aunque nadie le haya tocado un tornillo.

### 4. El ciclo de vida de un modelo

Un modelo no es un proyecto que "se termina": es un **ciclo**.

```
   ┌─────────────┐   ┌──────────┐   ┌──────────────┐   ┌───────────────┐
   │ 1. Problema │──►│ 2. Datos │──►│ 3. Preparar  │──►│ 4. Entrenar y │
   │  de negocio │   │ (captura,│   │ (limpiar,    │   │   calibrar    │
   └─────────────┘   │  EDA)    │   │  transformar)│   └───────┬───────┘
          ▲          └──────────┘   └──────────────┘           │
          │                                                    ▼
   ┌──────┴──────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────┐
   │ 8. Reentre- │◄──│ 7. Monitorear│◄──│ 6. Desplegar │◄──│5. Evaluar│
   │    nar      │   │ (drift,      │   │ (API, batch, │   │ (¿le gana│
   └─────────────┘   │  métricas)   │   │  contenedor) │   │ baseline?)│
                     └──────────────┘   └──────────────┘   └──────────┘
```

Los pasos 1-5 son lo que se enseña en cursos de ML. MLOps se ocupa de que los pasos 2-8
sean **automáticos, reproducibles y vigilados**, y de cerrar el ciclo (8 → 2).

### 5. CRISP-DM y dónde entra MLOps

**CRISP-DM** (*Cross-Industry Standard Process for Data Mining*, 1999-2000) es la metodología
clásica de proyectos de datos. Tiene 6 fases, y en el curso cada entrega se ubicó en una:

| Fase CRISP-DM | Pregunta | Qué agrega MLOps | Dónde lo vimos |
|---|---|---|---|
| 1. **Business Understanding** | ¿Qué problema de negocio resolvemos y cómo sabremos que funcionó? | Criterios de éxito medibles que luego serán **compuertas automáticas** | Caso gasolina (tema 03), CRISP-DM en Act. 1 |
| 2. **Data Understanding** | ¿Qué datos hay y qué problemas tienen? | Validaciones de datos que se ejecutan siempre, no una vez | EDA Champions (tema 01) |
| 3. **Data Preparation** | ¿Cómo dejamos los datos listos para modelar? | Preparación **dentro de un pipeline versionado** (misma limpieza en train, test y producción) | Pipelines (temas 04, 05) |
| 4. **Modeling** | ¿Qué modelo e hiperparámetros? | Experimentos registrados y reproducibles (semillas, MLflow) | Hiperparámetros (tema 06), Databricks/MLflow (11) |
| 5. **Evaluation** | ¿Cumple los criterios de éxito? | Evaluación automática con **compuerta de calidad** que bloquea modelos malos | Compuerta en CI (tema 10), sobreajuste (02) |
| 6. **Deployment** | ¿Cómo lo usa el negocio? | Empaquetado, contenedores, CI/CD, monitoreo y reentrenamiento | Temas 07, 08, 09, 10, 11 |

Diferencia de fondo: CRISP-DM dibuja el despliegue como **la última flecha**. MLOps dice que
el despliegue es **el comienzo** de la vida útil del modelo, y agrega monitoreo y
reentrenamiento como fases permanentes.

### 6. Niveles de madurez de MLOps (Google Cloud)

Google describe tres niveles en *MLOps: Continuous delivery and automation pipelines in
machine learning*:

| Nivel | Nombre | Cómo se ve | Problema típico |
|---|---|---|---|
| **0** | Proceso manual | Notebooks y scripts corridos a mano. El científico de datos entrega un archivo de modelo y otro equipo lo despliega. Se reentrena pocas veces al año. Sin CI/CD, sin monitoreo activo | No se puede reproducir; el modelo se degrada y nadie se entera |
| **1** | Automatización del pipeline de ML | El **pipeline completo** (validar datos → preparar → entrenar → evaluar → validar modelo) está automatizado y se dispara solo (por horario, por datos nuevos o por caída de desempeño). Esto es **CT (entrenamiento continuo)**. Se despliega el pipeline, no solo el modelo. Aparecen validación de datos/modelo, *feature store* y metadatos | El pipeline en sí se actualiza a mano: probar una idea nueva sigue siendo lento |
| **2** | Automatización de CI/CD del pipeline | Además, el **código del pipeline** pasa por CI/CD: cada cambio se prueba, se construye y se despliega automáticamente. Hay registro de modelos, orquestador y almacén de metadatos | Más complejidad de infraestructura (se justifica con muchos modelos o cambios frecuentes) |

> **Analogía de cocina:** nivel 0 es un chef que cocina cada plato a mano. Nivel 1 es una
> cocina con recetas estandarizadas que se preparan solas cuando llegan ingredientes frescos.
> Nivel 2 es que, además, cuando el chef mejora una receta, esa receta nueva se prueba y se
> instala sola en todas las sucursales.

¿Dónde quedó el curso? Las Actividades 1 y 3 son nivel 0 **bien hecho** (reproducible,
empaquetado, semillas fijas). El Ejercicio 3 (GitHub Actions con 4 jobs y compuerta de
calidad en cada `push`) es el primer paso hacia los niveles 1-2: el pipeline corre solo y
decide si el modelo es aceptable. Databricks con MLflow (tema 11) agrega registro de
experimentos y modelos.

### 7. Los componentes de un sistema de MLOps

| Componente | Para qué sirve | Herramientas típicas | En el curso |
|---|---|---|---|
| **Versionado de código** | Saber qué código produjo qué modelo | git, GitHub | Todos los repos |
| **Versionado de datos** | Saber con qué datos se entrenó | DVC, Delta Lake (time travel), CSV dentro del paquete | CSV empaquetado en Act. 1/3; Delta en Databricks |
| **Ambiente reproducible** | Mismas versiones de librerías en todas partes | `venv`, `requirements.txt`, `pyproject.toml`, Docker | Temas 07, 08, 09 |
| **Pipeline** | Pasos automáticos y en orden | scikit-learn `Pipeline`, Make, GitHub Actions, Airflow | Temas 04, 05, 10 |
| **Seguimiento de experimentos** | Registrar parámetros, métricas y artefactos de cada corrida | MLflow Tracking | Tema 11 |
| **Registro de modelos** (*model registry*) | Catálogo de modelos con versiones y etapas (staging/producción) | MLflow Model Registry, Unity Catalog | Tema 11 |
| **Serving** | Entregar predicciones | **Online:** API REST (FastAPI). **Batch:** un trabajo que predice miles de filas de una vez | API de la Act. 4 (tema 09) |
| **Monitoreo** | Saber si el sistema y el modelo están sanos | Métricas operativas (latencia, errores) + estadísticas de datos (drift) + métricas de desempeño | Este notebook (simulación) |
| **Compuerta de calidad** | Impedir que un modelo malo llegue a producción | Un script que falla si la métrica baja de un umbral | `evaluar.py` del Ej. 3: `f1_macro ≥ 0.40` y ganarle al baseline |

### 8. Drift: por qué los modelos se degradan

El modelo aprendió con datos del pasado. Cuando el presente es distinto, se equivoca más.
Hay que distinguir **qué** cambió:

| Tipo | Qué cambia | En símbolos | Ejemplo (entregas a domicilio) | ¿Se detecta sin etiquetas? |
|---|---|---|---|---|
| **Data drift** (*covariate shift*) | La distribución de las entradas | cambia $P(X)$, se mantiene $P(y\mid X)$ | La empresa se expande y llegan pedidos de 13 km en vez de 5 km | **Sí**: comparar histogramas, KS, PSI |
| **Concept drift** | La relación entre entradas y salida | cambia $P(y\mid X)$ | Hay obras en la ciudad: misma distancia y tráfico, pero ahora llega tarde | **No**: hay que esperar las etiquetas reales y medir el desempeño |
| *Label drift* (*prior shift*) | La proporción de clases | cambia $P(y)$ | En diciembre se atrasan muchos más pedidos por volumen | Parcialmente (vigilando la proporción de predicciones) |

Formas del cambio: **súbito** (una pandemia, una ley nueva), **gradual** (inflación,
obras que crecen), **estacional** (diciembre vs. enero) o **recurrente**.

> **Analogía:** aprendiste a manejar en Ciudad de Guatemala. *Data drift* es manejar en una
> carretera de montaña: las reglas son las mismas, pero son situaciones que casi no
> practicaste. *Concept drift* es que cambien las leyes de tránsito: las calles se ven
> igual, pero lo que es correcto cambió.

**Cómo se detecta:**

- **KS (Kolmogórov-Smirnov):** prueba estadística que compara dos distribuciones numéricas.
  p-valor muy pequeño → "no vienen de la misma distribución".
- **PSI (Population Stability Index):** divide la variable en cubetas con los datos de
  referencia y compara los porcentajes. Regla práctica: < 0.1 estable, 0.1-0.25 vigilar,
  > 0.25 cambio importante.
- **Métricas de desempeño** (accuracy, F1) cuando llegan las etiquetas reales: la única
  forma de ver el concept drift.

**Qué se hace:** reentrenar con datos recientes (manual o automático, por calendario o por
alerta), y si el cambio es profundo, rediseñar variables.

### 9. Reproducibilidad

Un resultado es reproducible si otra persona, en otra computadora, obtiene **exactamente**
los mismos números. Ingredientes:

1. **Semillas fijas** (`random_state=42`): la partición train/test y los algoritmos
   aleatorios dan lo mismo siempre.
2. **Datos versionados**: el mismo CSV (en el curso, el CSV viaja *dentro* del paquete).
3. **Versiones de librerías fijadas** (`scikit-learn==1.x.y`).
4. **Código empaquetado** (`pip install .`) en vez de celdas sueltas.
5. **Ambiente aislado**: `venv` o, mejor, un contenedor Docker.

La prueba del curso: el `act1-demo` da **accuracy = 0.724** y el `act3-demo` da
**accuracy = 0.690, f1_macro = 0.631** idénticos en Windows, macOS y dentro de Docker. Y un
bug real de la Actividad 4 muestra por qué fijar versiones importa: un modelo guardado con
`joblib` guarda la *ruta de importación* de sus clases, así que la API necesita el mismo
paquete y las mismas versiones que el entrenador para poder cargarlo.

### 10. Roles

| Rol | Se enfoca en | Entregables típicos | Analogía (restaurante) |
|---|---|---|---|
| **Data engineer** | Que los datos lleguen limpios, a tiempo y a escala | Pipelines de ingesta, data lake/warehouse, capas bronce-plata-oro | Proveedor y bodega: que los ingredientes lleguen frescos |
| **Data scientist** | Entender el problema y encontrar un modelo que funcione | EDA, experimentos, notebooks, elección de modelo y métricas | Chef que inventa la receta |
| **ML engineer** | Llevar el modelo a producción y mantenerlo | Pipelines de entrenamiento, APIs, contenedores, CI/CD, monitoreo | Quien convierte la receta en un proceso de cocina que sale igual 1 000 veces al día |
| **MLOps / platform engineer** | La plataforma que usan todos | Registro de modelos, orquestadores, infraestructura | Quien diseña y mantiene la cocina industrial |

En equipos pequeños una persona hace varios roles (como en el curso: el mismo equipo hizo
EDA, pipeline, Docker y CI/CD).

### 11. Mapa: qué pieza cubre cada tema de este repo

| Tema | Pieza del ciclo de vida | Fase CRISP-DM | Qué problema de MLOps resuelve |
|---|---|---|---|
| [01 · EDA Champions](../01-champions-eda/) | Datos | Data Understanding | Detectar fuga, tipos mal leídos y filas basura **antes** de automatizar nada |
| [02 · Overfitting](../02-overfitting/) | Evaluar | Modeling / Evaluation | No confiar en un modelo que solo brilla en el notebook |
| [03 · Caso gasolina](../03-caso-gasolina/) | Problema de negocio + captura de datos | Business Understanding | Plantear objetivos y criterios de éxito medibles cuando ni siquiera existen los datos |
| [04 · Pipelines de datos](../04-pipelines-datos/) | Preparar | Data Preparation | ETL/ELT, etapas de un pipeline y comandos de pandas para automatizar la limpieza |
| [05 · Pipeline sklearn](../05-pipeline-sklearn/) | Preparar + entrenar | Data Preparation | Amarrar la limpieza al modelo y empaquetarlo: "funciona en mi máquina" → `pip install .` |
| [06 · Hiperparámetros](../06-hiperparametros/) | Entrenar y calibrar | Modeling / Evaluation | Elegir modelo con CV, sin mirar el test, con baseline y CV anidada |
| [07 · Ambientes virtuales](../07-ambientes-virtuales/) | Reproducibilidad | Deployment | Aislar dependencias y fijar versiones |
| [08 · Publicar paquete](../08-publicar-paquete/) | Distribuir | Deployment | Que cualquiera instale el pipeline desde un índice (TestPyPI) |
| [09 · Docker](../09-docker/) | Desplegar / serving | Deployment | Entrenador por lotes + API + base de datos en contenedores reproducibles |
| [10 · CI/CD](../10-cicd/) | Automatizar + compuerta | Evaluation / Deployment | El pipeline corre solo en cada `push` y bloquea modelos malos |
| [11 · Databricks](../11-databricks/) | Escalar, registrar, gobernar | Todas | Arquitectura medallón, Unity Catalog, MLflow (experimentos y registro de modelos) |
| **00 · este tema** | Monitorear y reentrenar | (después de Deployment) | Drift, degradación silenciosa y por qué el ciclo nunca termina |

---

## 📂 Qué hicimos en el curso

El curso **Machine Learning Engineering (MLE/MLOps)** de la UVG siguió un hilo conductor:
**un mismo dataset y un mismo problema** (clasificar 144 partidos de la UEFA Champions
League 2025/26 en `Home Win`, `Away Win` o `Draw`) al que cada entrega le agregó una capa de
ingeniería. Así se ve el recorrido completo de un modelo, desde el EDA hasta los
contenedores y la CI:

| Entrega | Qué agregó | Número clave |
|---|---|---|
| Ejercicio 1 / Lab 02 | EDA: filas vacías, texto que es número, fuga (`score`, `winner`) | 151 filas → 144 partidos |
| Actividad 1 / Lab 01 | Pipeline de scikit-learn empaquetado e instalable | accuracy **0.724** en 29 partidos (baseline 0.483), idéntico en varias computadoras |
| Actividad 3 / Lab 03 | Calibración con `GridSearchCV`, `RandomizedSearchCV`, `HalvingGridSearchCV` | f1_macro en CV de **0.508 → 0.619**; test accuracy 0.690 / f1_macro 0.631; CV anidada 0.541 |
| Tarea 4 | El paquete publicado en TestPyPI (`act3-pipeline-mlops`) | `pip install` desde un índice |
| Actividad 4 / Lab 04 | Tres contenedores: entrenador, API FastAPI, PostgreSQL | Mismos 0.690 / 0.631 dentro de Docker |
| Ejercicio 3 | 4 jobs en GitHub Actions (extraer → limpiar → entrenar → evaluar) | Compuerta: falla si `f1_macro < 0.40` o no le gana al baseline |
| Caso de Estudio 1 (PF-ML) | Business Understanding de un problema nuevo: precios de combustible | 5 fotos piloto, pipeline de captura validado |
| Taller 1 | Portafolio en GitHub Pages desplegado con Actions | Se despliega solo en cada `push` a `main` |

El portafolio del equipo resume la filosofía del curso: *"De modelos experimentales a
sistemas confiables"*.

---

## 🧪 Práctica

`repaso.ipynb` (generado desde `repaso.py`) **simula data drift y concept drift** con un
modelo de entregas a domicilio (`RandomForestClassifier` sobre `distancia_km` y `trafico`):

```bash
cd RepasoMLOps
python tools/build_nb.py 00-por-que-mlops/repaso.py    # o abre repaso.ipynb en Jupyter
```

Resultados reales del notebook:

| Escenario | Accuracy | Qué pasó |
|---|---|---|
| Enero (prueba, mismos datos que entrenamiento) | **0.912** | El "notebook feliz" |
| Marzo, expansión a zonas lejanas (*data drift*) | **0.835** | Tarde real 86.0 %, predicho 70.7 %: los árboles no extrapolan más allá de 11.8 km |
| Obras en la ciudad (*concept drift*) | **0.816** | Tarde real 60.1 %, predicho 41.8 %: las X se ven igual que en enero |

Monitoreo sin etiquetas: en la expansión, `distancia_km` da **KS = 0.965 y PSI = 7.9**
(alarma). En las obras, ambas variables dan **PSI ≈ 0.003** (nada): el concept drift es
invisible si solo miras las entradas.

Un año simulado con obras que crecen poco a poco: el modelo congelado baja de **0.931**
(febrero) a **0.702** (diciembre) y cruza el umbral de 0.85 en **julio**; reentrenando cada
mes con los datos del mes anterior se mantiene entre **0.919 y 0.931** (promedio 0.925 vs.
0.831).

---

## ❓ Preguntas tipo examen

**P:** ¿Qué problema resuelve MLOps, en una frase?
**R:** Llevar modelos de ML a producción de forma reproducible y automatizada, y mantenerlos funcionando bien en el tiempo (monitoreo y reentrenamiento), porque un modelo depende de datos que cambian.

**P:** ¿Cuál es la idea central de la figura de Sculley et al. (2015)?
**R:** Que el código del modelo es una fracción pequeña de un sistema de ML real; la mayor parte (y la mayor deuda técnica) está en la recolección y verificación de datos, la configuración, la extracción de variables, el serving y el monitoreo.

**P:** ¿Qué significa CACE?
**R:** *Changing Anything Changes Everything*: en ML los componentes están entrelazados; cambiar una variable, la limpieza o un hiperparámetro cambia el comportamiento de todo el modelo, por eso hay que versionar y probar todo junto.

**P:** Menciona tres diferencias entre DevOps y MLOps.
**R:** (1) En MLOps se versionan código, datos y modelos, no solo código. (2) Se prueban también los datos y el desempeño del modelo. (3) Los modelos fallan en silencio (degradación por drift), por eso aparece el entrenamiento continuo (CT) y el monitoreo estadístico.

**P:** Describe los niveles 0, 1 y 2 de madurez de MLOps de Google.
**R:** Nivel 0: todo manual con notebooks/scripts, despliegues raros, sin CI/CD ni monitoreo. Nivel 1: el pipeline de entrenamiento está automatizado y se dispara solo (entrenamiento continuo), con validación de datos y modelos. Nivel 2: además, el código del pipeline pasa por CI/CD automatizado, con registro de modelos y orquestador.

**P:** ¿Qué es *data drift* y cómo se detecta?
**R:** Cambio en la distribución de las variables de entrada, P(X), manteniendo la relación con la salida. Se detecta sin etiquetas comparando la distribución actual con la de entrenamiento: KS, PSI, histogramas.

**P:** ¿Qué es *concept drift* y por qué es más peligroso?
**R:** Cambio en la relación entre entradas y salida, P(y|X). Es más peligroso porque las entradas pueden verse idénticas (PSI ≈ 0), así que solo se detecta midiendo el desempeño cuando llegan las etiquetas reales, que suelen llegar tarde.

**P:** En la simulación, ¿por qué el bosque aleatorio falló con pedidos de 13 km si la regla del mundo no cambió?
**R:** Porque los árboles no extrapolan: para distancias mayores que la máxima vista en entrenamiento (11.8 km) predicen lo mismo que en ese borde, así que subestiman los atrasos de zonas lejanas.

**P:** ¿Qué valores de PSI indican un cambio importante?
**R:** Por regla práctica, PSI < 0.1 es estable, entre 0.1 y 0.25 hay que vigilar, y mayor que 0.25 es un cambio importante.

**P:** ¿Qué fase agrega MLOps que CRISP-DM no tiene explícita?
**R:** El monitoreo y el reentrenamiento continuos después del despliegue. En CRISP-DM el despliegue es la última fase; en MLOps es el inicio de la vida útil del modelo.

**P:** ¿Qué cinco ingredientes hacen reproducible un resultado?
**R:** Semillas fijas, datos versionados, versiones de librerías fijadas, código empaquetado y un ambiente aislado (venv o Docker).

**P:** ¿Qué hace un ML engineer que no hace típicamente un data scientist?
**R:** Convierte el modelo en un sistema de producción: pipelines automáticos, APIs, contenedores, CI/CD, monitoreo y reentrenamiento.

**P:** ¿Qué es una compuerta de calidad y qué umbral usó el Ejercicio 3?
**R:** Un paso automático que hace fallar el pipeline si el modelo no cumple un mínimo. En el Ejercicio 3, `evaluar.py` falla si `f1_macro < 0.40` o si el modelo no le gana al clasificador que siempre predice la clase mayoritaria.

**P:** ¿Diferencia entre serving online y batch?
**R:** Online responde predicciones una por una, en tiempo real, típicamente vía API REST (como la FastAPI de la Act. 4). Batch predice muchas filas de una vez en un trabajo programado (por ejemplo, cada noche).

---

## 🏋️ Ejercicios

1. **Drift en el dataset real.** Separa los 144 partidos de la Champions en las primeras 4
   jornadas (72 partidos) y las últimas 4. Calcula el PSI y la prueba KS de
   `home_possession` y `home_saves_pct` entre ambas mitades. ¿Hay drift? ¿Esperarías
   alguno?
2. **Label drift.** Modifica `generar_mes` del notebook para que en diciembre cambie solo la
   proporción de pedidos tarde (por ejemplo, el tráfico pasa a `uniform(4, 10)`). ¿Qué tipo
   de drift es? ¿Lo detecta el PSI? ¿Cuánto cae el accuracy?
3. **Política de reentrenamiento.** En la simulación anual, en vez de reentrenar cada mes,
   reentrena **solo cuando** el accuracy del mes anterior baja de 0.85. ¿Cuántas veces
   reentrenas? ¿Cuánto accuracy pierdes contra reentrenar siempre?
4. **Ubica tu proyecto.** Para el proyecto de precios de combustible (tema 03), escribe qué
   tendría que existir para que fuera nivel 0, nivel 1 y nivel 2 de Google.
5. **Arregla la extrapolación.** Repite el escenario de expansión con `LogisticRegression` en
   vez de `RandomForestClassifier`. ¿Cae igual el accuracy? Explica por qué con la regla
   verdadera (que es lineal).

---

## 🔗 Referencias

- Sculley, D. et al. (2015). *Hidden Technical Debt in Machine Learning Systems*. NeurIPS. <https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems>
- Google Cloud. *MLOps: Continuous delivery and automation pipelines in machine learning*. <https://cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning>
- VentureBeat (2019). *Why do 87% of data science projects never make it into production?* <https://venturebeat.com/ai/why-do-87-of-data-science-projects-never-make-it-into-production/>
- Chapman, P. et al. (2000). *CRISP-DM 1.0: Step-by-step data mining guide*.
- Documentación de `scipy.stats.ks_2samp`: <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ks_2samp.html>
- MLflow: <https://mlflow.org/docs/latest/index.html>
- Repos del curso: [Actividad1-MLOPS](https://github.com/DiegoLinares11/Actividad1-MLOPS) · [Actividad3-MLOPS](https://github.com/DiegoLinares11/Actividad3-MLOPS) · [Actividad4-MLOPS](https://github.com/DiegoLinares11/Actividad4-MLOPS) · [Ejecicio3-MLOPS](https://github.com/DiegoLinares11/Ejecicio3-MLOPS) · [Tarea4-MLOPS](https://github.com/DiegoLinares11/Tarea4-MLOPS) · [Portafolio-MLOPS](https://github.com/Andyfer004/Portafolio-MLOPS) · [PF-ML](https://github.com/Andyfer004/PF-ML)
