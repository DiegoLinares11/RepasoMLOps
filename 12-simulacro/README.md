# 12 · Simulacro de MLOps

50 preguntas de opción múltiple mezcladas de los 11 temas, en el estilo de un
examen o una entrevista técnica. Respóndelas de corrido, sin ver nada, y después
abre las respuestas. Cada respuesta dice a qué tema volver.

| Aciertos | Qué hacer |
|---|---|
| 43-50 | Listo. Repasa solo los fallos. |
| 33-42 | Vuelve al README de los temas fallados y corre sus notebooks. |
| < 33 | Empieza otra vez por [00](../00-por-que-mlops/) y mira los videos. |

---

## Bloque A · Fundamentos

1. ¿Qué cambia en un sistema de ML que no cambia en software tradicional?
   a) Solo el código  b) Código, datos y modelo  c) Solo la infraestructura  d) Solo los requisitos
2. Un modelo funcionaba bien y su accuracy cae lentamente porque los clientes cambiaron de comportamiento, aunque la distribución de las variables de entrada sigue igual. Es:
   a) Data drift  b) Concept drift  c) Overfitting  d) Data leakage
3. Cambia la distribución de las variables de entrada, por ejemplo llegan clientes más jóvenes. Es:
   a) Data drift  b) Concept drift  c) Underfitting  d) Sesgo de selección
4. En el nivel 0 de madurez de MLOps de Google:
   a) Todo es manual y el modelo se entrega como artefacto  b) Hay CI/CD de pipelines  c) Hay reentrenamiento automático  d) Hay monitoreo continuo
5. En CRISP-DM, ¿en qué fase se definen los criterios de éxito?
   a) Modelado  b) Evaluación  c) Comprensión del negocio  d) Despliegue
6. En el dataset de Champions, `score` y `winner` deben eliminarse porque:
   a) Tienen nulos  b) Revelan el resultado que se quiere predecir  c) Son texto  d) Están correlacionadas entre sí
7. La posesión venía como `'63%'` y los tiros como `'3 of 10'`. El problema es:
   a) Valores atípicos  b) Números guardados como texto  c) Multicolinealidad  d) Desbalance
8. Un árbol sin límite de profundidad da 100 % en entrenamiento y 55 % en prueba. Es:
   a) Subajuste  b) Sobreajuste  c) Fuga de datos  d) Drift
9. Con solo 144 partidos, ¿por qué conviene validación cruzada en vez de un solo split?
   a) Es más rápida  b) La métrica de un solo split varía mucho según qué filas caigan en prueba  c) Evita la fuga siempre  d) No necesita datos de prueba
10. ¿Por qué usar StratifiedKFold en clasificación?
    a) Para mezclar las filas  b) Para mantener la proporción de clases en cada pliegue  c) Para usar menos datos  d) Para series de tiempo

## Bloque B · Pipelines

11. ¿Qué significa que un pipeline de datos sea idempotente?
    a) Que corre rápido  b) Que correrlo varias veces con la misma entrada da el mismo resultado  c) Que no usa memoria  d) Que corre en paralelo
12. ETL y ELT se diferencian en:
    a) El lenguaje  b) Si la transformación ocurre antes o después de cargar al destino  c) El tamaño de los datos  d) Nada
13. En scikit-learn, un transformer implementa:
    a) fit y predict  b) fit y transform  c) solo predict  d) score
14. ¿Cuál es la ventaja principal de meter el escalado dentro de un Pipeline?
    a) Es más bonito  b) Evita la fuga de datos, porque se ajusta solo con entrenamiento en cada pliegue  c) Acelera el modelo  d) Elimina los nulos
15. ColumnTransformer sirve para:
    a) Aplicar distinto preprocesamiento a distintas columnas  b) Reducir dimensiones  c) Unir datasets  d) Calibrar hiperparámetros
16. Para crear un transformador propio en scikit-learn se hereda de:
    a) Pipeline  b) BaseEstimator y TransformerMixin  c) GridSearchCV  d) DataFrame
17. La diferencia entre parámetro e hiperparámetro es:
    a) Ninguna  b) El parámetro lo aprende el modelo; el hiperparámetro lo fijas tú antes de entrenar  c) El hiperparámetro lo aprende el modelo  d) Los parámetros son solo de redes neuronales
18. En un pipeline con un paso llamado `clf`, ¿cómo se nombra el hiperparámetro C en el grid?
    a) `C`  b) `clf.C`  c) `clf__C`  d) `clf-C`
19. ¿Cuándo prefieres RandomizedSearchCV sobre GridSearchCV?
    a) Espacios pequeños  b) Espacios grandes o con hiperparámetros continuos  c) Nunca  d) Cuando no hay validación cruzada
20. HalvingGridSearchCV:
    a) Prueba todas las combinaciones con todos los datos  b) Descarta candidatos en rondas, dándole más datos a los que sobreviven  c) Divide el dataset a la mitad  d) Solo sirve para árboles
21. ¿Por qué se usa f1_macro y no accuracy en el proyecto de Champions?
    a) Es más fácil  b) Las clases están desbalanceadas, los empates son pocos  c) Accuracy no existe en multiclase  d) Por velocidad
22. ¿Cuántas veces debe usarse el conjunto de prueba al calibrar?
    a) En cada combinación  b) Una sola vez, al final  c) Nunca  d) Dos veces

## Bloque C · Entorno y empaquetado

23. ¿Qué hace realmente activar un ambiente virtual?
    a) Instala Python de nuevo  b) Antepone la carpeta del ambiente al PATH  c) Descarga paquetes  d) Reinicia la terminal
24. ¿Por qué no se sube la carpeta `.venv` al repositorio?
    a) Es ilegal  b) Es pesada, depende del sistema operativo y se recrea desde requirements  c) GitHub la bloquea  d) Contiene contraseñas
25. `pandas~=2.1.0` acepta:
    a) Solo 2.1.0  b) 2.1.x pero no 2.2  c) Cualquier versión  d) 2.x
26. En Windows, el error al ejecutar `Activate.ps1` se resuelve con:
    a) Reinstalar Python  b) Set-ExecutionPolicy  c) pip upgrade  d) Reiniciar
27. ¿Qué archivo es el estándar moderno para describir un paquete de Python?
    a) setup.cfg  b) pyproject.toml  c) requirements.txt  d) Makefile
28. Un wheel (`.whl`) es:
    a) El código fuente sin compilar  b) Un paquete ya construido, listo para instalar  c) Un ambiente virtual  d) Un contenedor
29. ¿Para qué sirve TestPyPI?
    a) Producción  b) Practicar la publicación sin contaminar el PyPI real  c) Correr pruebas unitarias  d) Alojar videos
30. Al instalar desde TestPyPI se agrega `--extra-index-url https://pypi.org/simple/` porque:
    a) Es obligatorio  b) TestPyPI no tiene las dependencias como scikit-learn y pandas  c) Es más rápido  d) Por seguridad
31. El paquete se instala como `act3-pipeline-mlops` pero se importa como `act3_pipeline`. ¿Por qué?
    a) Error  b) El nombre de distribución y el de import son cosas distintas  c) Windows  d) Por la versión
32. El token de API de PyPI debe guardarse:
    a) En el README  b) En el código  c) En un `.env` o en secrets, nunca en el repo  d) En el pyproject.toml
33. En versionado semántico 2.4.1, un cambio que rompe compatibilidad sube a:
    a) 2.4.2  b) 2.5.0  c) 3.0.0  d) 2.4.1-b

## Bloque D · Docker

34. La diferencia principal entre un contenedor y una máquina virtual es:
    a) El contenedor comparte el kernel del sistema anfitrión  b) Son iguales  c) La VM es más liviana  d) El contenedor no tiene sistema de archivos
35. Imagen y contenedor se relacionan como:
    a) Iguales  b) Receta y plato, o clase y objeto  c) Disco y memoria  d) Código y prueba
36. ¿Por qué se copia `requirements.txt` antes que el resto del código en el Dockerfile?
    a) Por orden alfabético  b) Para aprovechar la caché de capas y no reinstalar dependencias en cada cambio de código  c) Es obligatorio  d) Para que pese menos
37. Un volumen con nombre sirve para:
    a) Persistir datos aunque el contenedor se borre  b) Compartir la red  c) Acelerar el build  d) Exponer puertos
38. En la Actividad 4, el servicio entrenador:
    a) Está siempre encendido  b) Corre por lotes, guarda el modelo en un volumen y termina  c) Expone el puerto 8000  d) Es la base de datos
39. Dentro de docker compose, la API se conecta a Postgres usando:
    a) localhost  b) El nombre del servicio, por ejemplo `db`  c) La IP pública  d) No puede
40. `docker compose down -v`:
    a) Solo detiene  b) Detiene, borra contenedores y también los volúmenes  c) Actualiza las imágenes  d) Muestra logs

## Bloque E · CI/CD y Databricks

41. Integración continua significa:
    a) Desplegar a producción en cada cambio  b) Integrar y probar automáticamente cada cambio de código  c) Escribir documentación  d) Hacer reuniones diarias
42. En GitHub Actions, `needs:` sirve para:
    a) Instalar dependencias  b) Declarar que un job depende de otro y debe esperarlo  c) Definir secretos  d) Elegir el sistema operativo
43. ¿Por qué el Ejercicio 3 usa upload-artifact y download-artifact entre jobs?
    a) Por estética  b) Cada job corre en una máquina limpia y no comparte archivos con los demás  c) Para ahorrar dinero  d) Es opcional
44. La compuerta de calidad del Ejercicio 3 hace fallar el pipeline si:
    a) El código tiene comentarios  b) El modelo baja de cierto f1_macro o no le gana al modelo trivial  c) Tarda mucho  d) Hay muchos commits
45. ¿Cómo hace un script de Python para que GitHub Actions marque un paso como fallido?
    a) Imprimir "error"  b) Terminar con código de salida distinto de cero  c) Escribir un archivo  d) Dormir
46. `matrix` en un workflow sirve para:
    a) Multiplicar matrices  b) Correr el mismo job con varias combinaciones, como varias versiones de Python  c) Guardar secretos  d) Programar horarios
47. En la arquitectura medallón, la capa bronce contiene:
    a) Datos agregados para reportes  b) Los datos tal como llegan, sin limpiar, para poder auditar  c) Solo el modelo  d) Datos de prueba
48. ¿Por qué cada capa del medallón debe leer la tabla anterior con `spark.table` y no un DataFrame en memoria?
    a) Es más rápido  b) Así Unity Catalog registra el linaje entre tablas  c) Por seguridad  d) Spark no permite memoria
49. MLflow sirve principalmente para:
    a) Visualizar dashboards  b) Registrar experimentos (parámetros, métricas, artefactos) y versionar modelos  c) Programar jobs  d) Limpiar datos
50. Delta Lake permite "time travel", que significa:
    a) Predecir el futuro  b) Consultar o restaurar versiones anteriores de una tabla  c) Cambiar zonas horarias  d) Acelerar consultas

---

## Respuestas

<details>
<summary>Ábrelas solo después de responder las 50</summary>

| # | R | Tema | # | R | Tema |
|---|---|---|---|---|---|
| 1 | b | [00](../00-por-que-mlops/) | 26 | b | [07](../07-ambientes-virtuales/) |
| 2 | b | [00](../00-por-que-mlops/) | 27 | b | [08](../08-publicar-paquete/) |
| 3 | a | [00](../00-por-que-mlops/) | 28 | b | [08](../08-publicar-paquete/) |
| 4 | a | [00](../00-por-que-mlops/) | 29 | b | [08](../08-publicar-paquete/) |
| 5 | c | [00](../00-por-que-mlops/) | 30 | b | [08](../08-publicar-paquete/) |
| 6 | b | [01](../01-champions-eda/) | 31 | b | [08](../08-publicar-paquete/) |
| 7 | b | [01](../01-champions-eda/) | 32 | c | [08](../08-publicar-paquete/) |
| 8 | b | [02](../02-overfitting/) | 33 | c | [08](../08-publicar-paquete/) |
| 9 | b | [02](../02-overfitting/) | 34 | a | [09](../09-docker/) |
| 10 | b | [02](../02-overfitting/) | 35 | b | [09](../09-docker/) |
| 11 | b | [04](../04-pipelines-datos/) | 36 | b | [09](../09-docker/) |
| 12 | b | [04](../04-pipelines-datos/) | 37 | a | [09](../09-docker/) |
| 13 | b | [05](../05-pipeline-sklearn/) | 38 | b | [09](../09-docker/) |
| 14 | b | [05](../05-pipeline-sklearn/) | 39 | b | [09](../09-docker/) |
| 15 | a | [05](../05-pipeline-sklearn/) | 40 | b | [09](../09-docker/) |
| 16 | b | [05](../05-pipeline-sklearn/) | 41 | b | [10](../10-cicd/) |
| 17 | b | [06](../06-hiperparametros/) | 42 | b | [10](../10-cicd/) |
| 18 | c | [06](../06-hiperparametros/) | 43 | b | [10](../10-cicd/) |
| 19 | b | [06](../06-hiperparametros/) | 44 | b | [10](../10-cicd/) |
| 20 | b | [06](../06-hiperparametros/) | 45 | b | [10](../10-cicd/) |
| 21 | b | [06](../06-hiperparametros/) | 46 | b | [10](../10-cicd/) |
| 22 | b | [06](../06-hiperparametros/) | 47 | b | [11](../11-databricks/) |
| 23 | b | [07](../07-ambientes-virtuales/) | 48 | b | [11](../11-databricks/) |
| 24 | b | [07](../07-ambientes-virtuales/) | 49 | b | [11](../11-databricks/) |
| 25 | b | [07](../07-ambientes-virtuales/) | 50 | b | [11](../11-databricks/) |

Ojo con la 2 y la 3, que son la pareja más preguntada: **data drift** es que
cambian las entradas, **concept drift** es que cambia la relación entre entradas
y resultado.

</details>
