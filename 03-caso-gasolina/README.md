# 03 · Caso de estudio: precios de combustible en Guatemala

🎬 Video: `caso-gasolina\caso-gasolina-es.mp4` (también en inglés: `-en.mp4`, y hojas de revisión `revision-es.png`).

En los demás temas el dataset ya existía (un CSV de la Champions). En el proyecto final
(PF-ML, Caso de Estudio 1) **no hay datos**: los precios viven en fotografías de
surtidores. Este tema enseña cómo se plantea un problema de ML desde cero, con la fase de
**Entendimiento del Negocio** de CRISP-DM, y cómo se construye un pipeline de captura
confiable antes de pensar en modelos.

---

## 🧱 Conocimiento previo

### 1. CRISP-DM, fase 1: Business Understanding

CRISP-DM tiene 6 fases (ver tema 00). La primera responde **"¿qué problema resolvemos y
cómo sabremos que lo resolvimos?"** antes de tocar un dato. La guía oficial la divide en
cuatro tareas:

| Tarea | Preguntas | Entregable |
|---|---|---|
| Determinar objetivos de negocio | ¿Qué quiere lograr el usuario? ¿Para qué le sirve? | Objetivos y **criterios de éxito de negocio** |
| Evaluar la situación | ¿Qué datos, personas y recursos hay? ¿Qué riesgos? | Inventario de recursos, supuestos, restricciones, **riesgos** |
| Determinar objetivos de ML | ¿Qué se predice exactamente? ¿Con qué métrica? | Objetivo técnico y **criterios de éxito técnicos** |
| Plan del proyecto | ¿En qué etapas y con qué herramientas? | Plan por etapas |

> **Analogía:** antes de construir una casa, el arquitecto pregunta para cuántas personas es,
> qué presupuesto hay y qué terreno. Empezar a poner ladrillos sin eso es el error más caro.

### 2. Criterios de éxito de negocio vs. técnicos

| | De negocio | Técnicos |
|---|---|---|
| Hablan de | Valor para el usuario | Calidad del modelo y de los datos |
| Ejemplo | "El conductor puede decidir si llena el tanque hoy o espera" | "Macro-F1 mayor que la línea base" |
| Quién los valida | El usuario / el negocio | El equipo de datos |

Un modelo puede cumplir el técnico y fallar el de negocio (por ejemplo, predecir bien pero
con un día de atraso, cuando ya no sirve).

### 3. Business Model Canvas

Un lienzo de 9 bloques (segmentos de clientes, propuesta de valor, canales, relación con
clientes, fuentes de ingreso, recursos clave, actividades clave, socios clave, estructura
de costos) que resume **cómo un proyecto genera valor**. El PDF lo usa para justificar el
proyecto.

### 4. Fotografías, HEIC y metadata EXIF

- **HEIC** es el formato de foto por defecto de los iPhone (más comprimido que JPG).
- Cada foto lleva **metadata EXIF**: fecha y hora exactas (`DateTimeOriginal`), modelo de
  cámara, coordenadas GPS, zona horaria. Es como la "etiqueta" que el celular le pega a cada
  foto.
- **ExifTool** es un programa de línea de comandos que extrae **toda** esa metadata a JSON.

### 5. Visión por computadora básica con OpenCV

**Rectificar** una imagen es corregir la perspectiva: si fotografías una pantalla de lado,
se ve como un trapecio; con una transformación de perspectiva
(`cv2.getPerspectiveTransform` + `cv2.warpPerspective`) se "endereza" a un rectángulo. Es lo
que hace la app de escáner del celular con una hoja.

### 6. Series de tiempo (lo mínimo)

- El **orden importa**: el pasado explica el futuro, nunca al revés.
- **Rezago** (*lag*): el valor de hace k periodos. "El precio local sigue al Brent con una
  semana de rezago".
- **Cambio** vs. **nivel**: el precio (nivel, 41.09) sube con los años; el cambio semanal
  (+0.50) se mueve alrededor de cero. Los modelos generalizan mejor con cambios.

### 7. Brent y WTI

Precios de referencia internacionales del barril de petróleo (en dólares): **Brent** (Mar
del Norte) y **WTI** (Texas). Guatemala importa sus combustibles, así que su precio local
reacciona a estas referencias, al tipo de cambio, a costos de importación y transporte,
impuestos y márgenes. La **FRED** (Reserva Federal de St. Louis) publica las series de la
**EIA** (agencia de energía de EE. UU.) en CSV gratuito.

---

## 🎯 Qué tienes que saber

### 1. El problema, planteado como lo hizo el equipo

**Pregunta:** *¿Es posible utilizar precios históricos y variables de contexto para predecir
si el precio de un combustible bajará, subirá o se mantendrá durante la siguiente semana?*

**Formalización** (para una estación s, un combustible f y una semana t):

$$\Delta P_{s,f,t+1} = P_{s,f,t+1} - P_{s,f,t}$$

$$y_{s,f,t+1} = \begin{cases} \text{BAJA} & \Delta P < -\varepsilon \\ \text{ESTABLE} & |\Delta P| \le \varepsilon \\ \text{SUBE} & \Delta P > \varepsilon \end{cases}$$

- Es **clasificación multiclase**, no regresión: al usuario le importa la **dirección**, no
  el centavo exacto.
- **ε** es el cambio mínimo que se considera relevante. **No se inventa**: se fija en la fase
  de entendimiento de los datos según la precisión de las lecturas y la distribución real de
  los cambios.

### 2. Cómo se plantea un problema cuando los datos NO existen

Receta que sigue el caso:

1. **Definir la unidad de observación:** una fotografía = (estación, fecha, precios de 4
   combustibles).
2. **Diseñar la captura** antes que el modelo: fotos → metadata → lectura → validación →
   CSV/JSON.
3. **Hacer un piloto pequeño** que pruebe el pipeline de punta a punta (5 fotos), sin
   pretender predecir todavía.
4. **Separar el alcance por etapas** para no prometer lo que los datos no permiten:

   | Etapa | Alcance |
   |---|---|
   | Piloto actual | 5 imágenes de una estación Shell: metadata, precios, validaciones, flags, exportación CSV/JSON |
   | Ampliación de datos | Observaciones de otras fechas y estaciones (no disponibles en esta entrega) |
   | Objetivo final | Modelo que clasifique el cambio de la siguiente semana como BAJA, ESTABLE o SUBE |

5. **Listar fuentes externas** necesarias y su estado:

   | Fuente | Variables | Estado en la entrega |
   |---|---|---|
   | Fotografías propias | fecha, GPS, estación, precios | Piloto disponible |
   | MEM (Ministerio de Energía y Minas) | precios semanales oficiales, estructura del precio | Pendiente |
   | Banco de Guatemala | tipo de cambio GTQ/USD | Pendiente |
   | EIA (vía FRED) | Brent, WTI | Integrado en el código (caché) |
   | Noticias verificadas | eventos externos | Catálogo inicial de 2 eventos |

6. **Definir criterios de éxito y riesgos** (siguientes secciones).

### 3. Objetivos

**General:** desarrollar un sistema **reproducible** que construya una serie histórica de
precios y permita predecir semanalmente la dirección del cambio de cada combustible.

**Específicos:** (1) extraer y conservar fecha, ubicación y metadata de cada imagen;
(2) estructurar los precios de Diesel, Regular, Súper y V-Power; (3) validar lecturas con
reglas, diferencias y flags de revisión; (4) ordenar cronológicamente para formar una serie;
(5) integrar más fechas y estaciones; (6) integrar precios oficiales, tipo de cambio y precios
internacionales; (7) entrenar y evaluar un clasificador temporal de tres categorías.

### 4. Criterios de éxito (del PDF) y de qué tipo son

| Criterio | Tipo | Por qué |
|---|---|---|
| Cada observación conserva fecha, ubicación y referencia a su imagen | Datos / trazabilidad | Auditar cualquier número hasta su foto |
| Registros incompletos o inconsistentes activan una bandera de revisión | Datos / calidad | Ningún error pasa en silencio |
| La serie se divide **cronológicamente** | Técnico | Evitar usar información futura |
| El modelo se compara contra una línea base: **clase mayoritaria** o **repetir la tendencia anterior** | Técnico | Un modelo que no le gana a "lo de siempre" no sirve |
| Debe superar la línea base en **Macro-F1** | Técnico | Pesa igual BAJA, ESTABLE y SUBE |
| Resultados **por combustible**, no solo exactitud global | Técnico / negocio | Diesel puede comportarse distinto que Regular |

Y la propuesta de valor del Canvas da el criterio de negocio: un **historial verificable y
una predicción semanal** que permita ahorro potencial, mejor planificación de compra y menos
incertidumbre para conductores, compradores frecuentes y analistas.

### 5. Riesgos y limitaciones

| Riesgo | Mitigación |
|---|---|
| 5 fotografías de una estación no permiten generalizar ni predecir | Declararlo: el piloto valida el pipeline, no el modelo |
| La data ampliada no está disponible aún | Alcance por etapas |
| Las reglas Regular/Súper/V-Power de Shell no aplican a otras marcas | No generalizar reglas sin verificarlas |
| Reflejos, perspectiva u obstrucciones afectan la lectura | Rectificación con OpenCV + validación cruzada + flags |
| Eventos internacionales provocan cambios repentinos | Catálogo de eventos fechados como contexto |
| Si una clase aparece poco, el modelo se sesga a la mayoritaria | Macro-F1, revisar que la serie tenga ejemplos de las 3 clases |

**Eventos ≠ causalidad:** que una decisión de la OPEP+ coincida con una subida no demuestra
que la causó. El PDF lo deja explícito: el evento se interpreta como **contexto o
asociación** salvo evidencia adicional.

### 6. El pipeline determinista de captura

El README del repo lo define como *"pipeline determinista, sin LLM ni servicios de IA"*.
¿Por qué determinista? Porque es **reproducible y auditable**: la misma foto da siempre el
mismo resultado, y cada paso se puede explicar. Un OCR o un LLM puede leer distinto cada vez
y es difícil saber por qué se equivocó.

```
data/images/*.HEIC
   │
   ├─► ExifTool (-j -n) ───────────► output/metadata/IMG_xxxx.json   (TODA la metadata)
   │      (si no hay ExifTool: Pillow lee el EXIF básico)
   │
   ├─► Pillow + pillow-heif: abrir, orientar (exif_transpose), redimensionar a 1600 px
   │
   ├─► OpenCV: detectar y rectificar las 4 pantallas LCD inferiores
   │      máscara de color "azulado-claro" → cierre morfológico → componentes conectados
   │      → filtrar por posición (60-78 % de la altura) y tamaño → exactamente 4 candidatos
   │      → ordenar de izquierda a derecha: diesel, regular, super, vpower
   │      → minAreaRect → getPerspectiveTransform → warpPerspective a 320×120
   │      ──────────────────────────► output/crops/IMG_xxxx/{diesel,regular,super,vpower}.png
   │
   ├─► data/lecturas_manuales.csv (un humano lee total, galones y 4 precios)
   │
   ├─► Reglas de negocio + flags (validación cruzada de la lectura)
   │
   ├─► external_data.py: Brent/WTI (FRED, caché) + eventos de los 21 días anteriores
   │
   └─► output/gas_prices.csv (ordenado por fecha) + output/records/IMG_xxxx.json (auditable)
```

Si OpenCV no encuentra **exactamente 4** pantallas, no inventa: devuelve vacío y se enciende
`requiere_revision_flag`.

### 7. Validar una lectura calculándola de otra forma

Una lectura manual puede equivocarse. El truco: **calcular el mismo número por otro camino**
y comparar. Cada foto es de una venta de **Q150.00 de Súper**, y la bomba muestra los galones:

| Regla (estación Shell observada) | Fórmula |
|---|---|
| Súper | total / galones |
| Regular | Súper − Q1.00 |
| V-Power | Súper + Q0.50 |

Si |estimado − leído| ≤ **Q0.02** (`MATCH_TOLERANCE`), el flag del combustible vale 1. ¿Por
qué 2 centavos y no 0? Porque los galones se muestran con 3 decimales y el redondeo produce
diferencias de 1 centavo (IMG_8304: 150 / 3.651 = 41.08 frente a 41.09 leído).

| Flag | Significado |
|---|---|
| `regular/super/vpower_match_flag` | 1 si ese precio coincide dentro de la tolerancia |
| `todos_match_flag` / `estado_flag` | 1 / `ENCENDIDO` si los tres coinciden |
| `requiere_revision_flag` | 1 si falta algún dato, no se detectaron 4 pantallas o algún precio no coincide |

### 8. ¿Por qué Diesel no se estima?

Porque **no sigue una diferencia fija**. En el piloto, Regular − Súper = −1.00 y V-Power −
Súper = +0.50 en las cinco fotos, pero Diesel − Súper va de **−0.80 a +1.70**. Diesel es otro
producto (otro proceso de refinación, otra demanda: carga, agricultura, generación), con su
propia dinámica. Estimarlo con una regla inventada fabricaría datos falsos, así que se
**almacena** tal como se lee, sin estimación ni flag de comparación.

### 9. Contexto externo sin fuga temporal

Regla de oro del caso: **nunca se usan eventos o precios posteriores a la fecha de la
imagen**.

- **Brent/WTI:** a cada foto se le asigna la **última observación disponible en o antes** de
  su fecha (`_latest_market_value`). Una foto de domingo toma el Brent del viernes, no el del
  lunes. También se calcula `variacion_brent_7d_pct` contra el último valor de 7 días antes.
- **Eventos:** se cuentan los que empezaron en o antes de la fecha de la foto y seguían
  activos dentro de los **21 días anteriores** (`EVENT_LOOKBACK_DAYS = 21`). Cada evento
  tiene id, fechas, tipo, descripción, impacto esperado (BAJA/SUBE/INCIERTO), importancia
  (1-3) y fuente con URL.
- **Sin red:** se reutiliza la caché `data/external/series_mercado.csv` y la columna
  `datos_externos_estado` dice si faltó algo (`CACHE`, `DESCARGADO`, `CACHE_TRAS_ERROR`,
  `NO_DISPONIBLE`, `...;FALTA_MERCADO`).

Una prueba unitaria (`test_contexto_solo_usa_datos_anteriores`) lo verifica con un "evento
futuro" que **no** debe aparecer.

> **Analogía:** es como apostar en una carrera de caballos. Solo vale la información que
> tenías **antes** de la carrera; usar el periódico del día siguiente es trampa.

### 10. Del historial al modelo: split temporal y líneas base

Cuando exista historia suficiente (varios meses, con ejemplos de las tres clases):

- **Split temporal:** entrenar con las semanas antiguas y probar con las recientes. Nunca
  barajar: barajando, el modelo "ve" semanas de 2025 al entrenar y "valida" en 2024.
- **Validación cruzada temporal:** `TimeSeriesSplit` (siempre entrena con el pasado y valida
  con el bloque siguiente).
- **Líneas base:** la clase mayoritaria y la **persistencia** ("esta semana subió → la
  siguiente sube"). La persistencia suele ser difícil de vencer en precios con inercia.
- **Métrica:** Macro-F1, reportada por combustible.
- **Fuga temporal típica:** promedios móviles centrados, rellenar nulos hacia atrás
  (`bfill`), normalizar con la media de toda la serie, o usar la variación del Brent de la
  semana que se quiere predecir.

---

## 📂 Qué hicimos en el curso

**Caso de Estudio 1 · Fase de Entendimiento del Negocio** (PDF del 7 de agosto de 2026, Andy
Fuentes, Diego Linares, Diederich Solis y Christian Echeverria) y el repo
[PF-ML](https://github.com/Andyfer004/PF-ML).

**El PDF** (`reportes/PF1_MLOPS.pdf`) cubre: contexto y justificación (el MEM monitorea
semanalmente los precios y muestra cambios distintos para Superior, Regular y Diesel;
Guatemala depende de hidrocarburos importados), el planteamiento con ΔP y ε, objetivos,
alcance por etapas, Business Model Canvas resumido, datos necesarios, eventos externos como
contexto (6 columnas propuestas: `evento_global`, `tipo_evento`, `fecha_evento`,
`fuente_evento`, `impacto_esperado`, `rezago_dias`), criterios de éxito, limitaciones y
riesgos. Conclusión: *"La entrega actual debe demostrar que las imágenes pueden convertirse en
datos trazables y ordenados. La predicción no se considera resuelta todavía."*

**El repo:**

| Archivo | Qué hace |
|---|---|
| `src/gas_pipeline.py` | ExifTool, OpenCV, lecturas manuales, reglas, flags, exportación (`ImageRecord` con 39 columnas) |
| `src/external_data.py` | Descarga Brent (`DCOILBRENTEU`) y WTI (`DCOILWTICO`) de FRED, caché, eventos de 21 días, contexto sin futuro |
| `data/lecturas_manuales.csv` | Lectura humana de total, galones y 4 precios por foto |
| `data/eventos_globales.csv` | 2 eventos: ajuste de producción de 188 mil barriles diarios anunciado por la OPEP+ (5 jul 2026, importancia 3) y tormenta tropical Bertha en el Golfo de México (19-23 jul 2026, impacto incierto) |
| `data/external/series_mercado.csv` | Caché de Brent/WTI diarios del 9 jun al 30 jul de 2026 |
| `tests/test_gas_pipeline.py` | 5 pruebas: estimados, tolerancia de redondeo, fuera de tolerancia, faltantes, contexto sin futuro |
| `notebooks/01_eda_gas_prices.ipynb` | EDA de la fase de entendimiento de datos |
| `output/gas_prices.csv` | Resultado del piloto |

**Resultados del piloto** (`output/gas_prices.csv` y el EDA):

| Dato | Valor |
|---|---|
| Fotos | 5 (HEIC, misma cámara, mismas coordenadas: una sola estación Shell) |
| Fechas | 9, 15, 22, 26 y 30 de julio de 2026 |
| Pantallas detectadas | 4 de 4 en todas las fotos |
| Flags | 5/5 `ENCENDIDO`, 0 revisiones pendientes; mayor diferencia por redondeo Q0.01 |
| Regular | Q37.09 → Q41.09 (**+Q4.00**); Súper y V-Power también +Q4.00 |
| Diesel | Q39.39 → Q43.79 (**+Q4.40**) |
| Brent en la fecha de la foto | 74.46 → 83.08 → 94.12 → 100.31 → 91.91 USD |
| Variación del Brent a 7 días | +8.65 %, +8.6 %, +13.29 %, +18.0 %, −12.73 % |

Hallazgo del EDA: *"cinco fotografías de una sola estación permiten validar el pipeline y
describir cambios, pero no permiten inferencia estadística ni pronósticos"*.

En el portafolio del equipo el caso aparece como: **Reto:** "No hay historial: los precios
viven en fotografías". **Solución:** "Pipeline de captura y preparación sobre una muestra
inicial". **Resultado:** "Alcance, objetivos y criterios de éxito definidos".

---

## 🧪 Práctica

`repaso.ipynb` tiene dos partes:

```bash
cd RepasoMLOps
python tools/build_nb.py 03-caso-gasolina/repaso.py
```

**Parte A, piloto real** (los valores de las 5 fotos copiados del repo, sin necesitar las
imágenes): reproduce `calcular_estimados()` y `comparar()` (5/5 `ENCENDIDO`, IMG_8304 con
−0.01), muestra que Diesel − Súper va de −0.80 a +1.70, une el Brent con `merge_asof` hacia
atrás (la foto del domingo 26 toma el viernes 24: 100.31) y reproduce las variaciones a 7
días del repo. Al etiquetar Regular con ε = 0.15 salen **4 cambios: 3 SUBE, 1 ESTABLE, 0
BAJA**: imposible entrenar.

**Parte B, simulación** (serie semanal **sintética** de 208 semanas donde el precio sigue al
Brent con una semana de rezago):

| Paso | Resultado real |
|---|---|
| Elegir ε | ε = 0.02 → 3.9 % ESTABLE; ε = 0.50 → 74.4 % ESTABLE; **ε = 0.15** → 39.6 / 23.2 / 37.2 % |
| Split temporal | train 153 semanas (2022-2024), test 52 semanas (2025) |
| Baseline clase mayoritaria | Macro-F1 **0.149** |
| Baseline persistencia | Macro-F1 **0.449** |
| Regresión logística (variables honestas) | Macro-F1 **0.694** (accuracy 0.750; F1 de ESTABLE 0.400) |
| Misma, con media móvil centrada (fuga) | Macro-F1 **0.959**: mejora falsa |
| KFold barajado vs. TimeSeriesSplit, honestas | 0.697 vs. 0.688 |
| Ídem, con niveles (precio, Brent) | 0.681 vs. **0.588**: barajar infla ~9 puntos |

---

## ❓ Preguntas tipo examen

**P:** ¿Cuál es la pregunta de negocio del proyecto final?
**R:** Si es posible usar precios históricos y variables de contexto para predecir si el precio de un combustible bajará, subirá o se mantendrá durante la siguiente semana.

**P:** ¿Por qué se planteó como clasificación y no como regresión?
**R:** Porque al usuario le importa la dirección del cambio (llenar hoy o esperar), no el centavo exacto; además tres clases con un umbral ε absorben el ruido de lectura.

**P:** ¿Qué es ε y cómo se debe elegir?
**R:** El cambio mínimo que se considera relevante. Se elige en el entendimiento de los datos según la precisión de las lecturas (mayor que la tolerancia de Q0.02) y la distribución real de los cambios, cuidando que las tres clases queden representadas.

**P:** ¿Por qué el Caso 1 no entrena ningún modelo?
**R:** Porque solo hay 5 fotos de una estación (4 cambios, ninguna BAJA): sirven para validar el pipeline de captura, no para generalizar ni predecir. El PDF separa el piloto de preparación de datos del objetivo predictivo.

**P:** Da un criterio de éxito de datos y uno técnico del PDF.
**R:** De datos: cada observación conserva fecha, ubicación y referencia a su imagen, y los registros inconsistentes activan una bandera. Técnico: el modelo debe superar en Macro-F1 a la línea base (clase mayoritaria o repetir la tendencia anterior), con división cronológica.

**P:** ¿Qué hace ExifTool en el pipeline y qué pasa si no está instalado?
**R:** Extrae toda la metadata de cada HEIC a JSON (fecha, cámara, GPS, zona horaria). Si no está, el pipeline usa Pillow para leer el EXIF básico y datos del archivo.

**P:** ¿Qué hace OpenCV en el pipeline?
**R:** Localiza las cuatro pantallas LCD inferiores por color, posición y tamaño, y las rectifica con una transformación de perspectiva a recortes de 320×120 (diesel, regular, super, vpower). Si no encuentra exactamente 4, se marca para revisión.

**P:** ¿Por qué un pipeline "determinista, sin LLM"?
**R:** Para que sea reproducible y auditable: la misma foto siempre produce el mismo resultado y cada paso se puede explicar y probar.

**P:** ¿Cómo se valida una lectura manual?
**R:** Calculando Súper = total/galones, Regular = Súper − 1 y V-Power = Súper + 0.50, y comparando con lo leído con tolerancia de Q0.02; cada coincidencia enciende su flag y cualquier fallo enciende `requiere_revision_flag`.

**P:** ¿Por qué Diesel se almacena pero no se estima?
**R:** Porque su precio no guarda una diferencia fija con Súper (en el piloto va de −0.80 a +1.70); estimarlo con una regla inventada generaría datos falsos.

**P:** ¿Cómo evita el pipeline la fuga temporal con el Brent y los eventos?
**R:** A cada foto le asigna la última cotización disponible en o antes de su fecha (una foto de domingo usa el viernes) y solo cuenta eventos iniciados antes de la foto dentro de una ventana de 21 días.

**P:** ¿Por qué un evento global no demuestra la causa de un cambio de precio?
**R:** Porque una coincidencia temporal no es causalidad; el evento se registra como contexto o asociación salvo que haya evidencia adicional.

**P:** ¿Qué es la línea base de persistencia y por qué es importante aquí?
**R:** Predecir que la semana siguiente repetirá la dirección de esta semana. En precios con inercia es difícil de vencer; si un modelo no le gana, no aporta.

**P:** ¿Por qué no se debe barajar al validar una serie de tiempo?
**R:** Porque el modelo vería el futuro al entrenar y validaría en el pasado; con variables de nivel el puntaje sale inflado (en la simulación 0.681 barajado vs. 0.588 temporal). Se usa un corte temporal o `TimeSeriesSplit`.

**P:** ¿Por qué un promedio móvil centrado es fuga?
**R:** Porque `rolling(3, center=True)` usa la semana t+1, la que se quiere predecir; en la simulación subió el Macro-F1 de 0.694 a 0.959 de forma falsa.

---

## 🏋️ Ejercicios

1. **Definir "la semana t".** Las fotos del piloto están separadas 6, 7, 4 y 4 días. Propón
   una regla para convertirlas en una serie semanal (¿último precio de cada semana ISO?
   ¿promedio?) e impleméntala con `resample("W-MON")`. ¿Qué haces con semanas sin foto?
2. **Persistencia más fuerte.** En la Parte B, crea una línea base "si el Brent subió esta
   semana, SUBE; si bajó, BAJA; si cambió menos de 1 USD, ESTABLE". ¿Le gana la regresión
   logística?
3. **Sensibilidad a ε.** Repite el modelo de la Parte B con ε ∈ {0.05, 0.10, 0.15, 0.25,
   0.30}. Grafica Macro-F1 del modelo y de la persistencia contra ε. ¿Qué ε elegirías y por
   qué?
4. **Nueva regla de validación.** Escribe una función que encienda un flag si el precio de
   un combustible cambia más de Q2.00 entre dos fotos consecutivas (posible error de
   lectura). ¿Se habría encendido en el piloto?
5. **Canvas propio.** Llena un Business Model Canvas para una versión del proyecto que
   venda alertas a flotas de transporte que usan Diesel. ¿Qué cambia en los criterios de
   éxito si Diesel es el combustible principal?

---

## 🔗 Referencias

- [PF-ML](https://github.com/Andyfer004/PF-ML): `README.md`, `src/gas_pipeline.py`, `src/external_data.py`, `notebooks/01_eda_gas_prices.ipynb`, `reportes/PF1_MLOPS.pdf`.
- [Portafolio-MLOPS](https://github.com/Andyfer004/Portafolio-MLOPS): página de casos de estudio.
- Ministerio de Energía y Minas, *Precios de combustibles nacionales*: <https://mem.gob.gt/que-hacemos/hidrocarburos/comercializacion-downstream/precios-combustible-nacionales/>
- Ministerio de Energía y Minas, *¿Cómo se determinan los precios de los combustibles en Guatemala?*: <https://mem.gob.gt/como-se-determinan-los-precios-de-los-combustibles-en-guatemala/>
- Banco de Guatemala, *Tipo de cambio de referencia*: <https://banguat.gob.gt/tipo_cambio/>
- U.S. EIA, *Spot Prices for Crude Oil and Petroleum Products*: <https://www.eia.gov/dnav/pet/pet_pri_spt_s1_m.htm>
- FRED, series `DCOILBRENTEU` y `DCOILWTICO`: <https://fred.stlouisfed.org/series/DCOILBRENTEU>
- ExifTool: <https://exiftool.org/>
- OpenCV, *Geometric Transformations of Images*: <https://docs.opencv.org/4.x/da/d6e/tutorial_py_geometric_transformations.html>
- Chapman, P. et al. (2000). *CRISP-DM 1.0: Step-by-step data mining guide* (fase Business Understanding).
- pandas `merge_asof`: <https://pandas.pydata.org/docs/reference/api/pandas.merge_asof.html>
- scikit-learn `TimeSeriesSplit`: <https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html>
