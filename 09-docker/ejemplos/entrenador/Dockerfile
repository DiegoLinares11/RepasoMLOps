# syntax=docker/dockerfile:1
## ^ No es un comentario cualquiera: es una "directiva del parser". Le pide a
##   BuildKit (el motor de construcción) usar la última sintaxis estable v1.
##   Tiene que ser la PRIMERA línea del archivo.
#
## =============================================================================
## Dockerfile REAL del servicio ENTRENADOR (Actividad 4), comentado línea por línea
## Los comentarios con "##" son del repaso; los de un "#" venían en el original.
## Se construye desde la RAÍZ del repo (context: . en docker-compose.yml):
##   docker build -f entrenador/Dockerfile -t act4/entrenador:1.0 .
## =============================================================================

# Imagen base oficial y "slim" (Debian minimo). Se fija la version exacta:
# 'python:3.12' cambiaria de contenido con el tiempo y la imagen dejaria de
# ser reproducible.
## FROM: el punto de partida. Todo Dockerfile empieza con una imagen base que
## ya trae un sistema operativo (Debian) con Python 3.12 instalado.
## Variantes: python:3.12 (~1 GB, con compiladores), python:3.12-slim (mínima,
## Debian), python:3.12-alpine (aún más chica, pero sin glibc: numpy/scikit-learn
## pueden tener que compilarse).
FROM python:3.12-slim

# Sin .pyc y con salida sin buffer, para que los logs salgan en vivo en
# `docker compose logs`.
## ENV: variables de entorno que quedan grabadas en la imagen (y en todo
## contenedor que salga de ella). La \ al final continúa la instrucción.
##   PYTHONDONTWRITEBYTECODE=1 -> no crear __pycache__/*.pyc (inútiles aquí).
##   PYTHONUNBUFFERED=1        -> print() sale de inmediato, no al final.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

## WORKDIR: "cd" dentro de la imagen (la crea si no existe). Los COPY, RUN y
## CMD siguientes usan /app como carpeta actual.
WORKDIR /app

# Las dependencias se copian e instalan ANTES que el codigo. Docker cachea
# cada instruccion en una capa: si solo cambia entrenar.py, esta capa (que es
# la lenta) se reutiliza y el build tarda segundos en vez de minutos.
## COPY origen destino: copia desde el CONTEXTO (tu disco) hacia la imagen.
## El origen es relativo al contexto (la raíz del repo), no al Dockerfile.
COPY entrenador/requirements.txt ./requirements.txt
## El paquete de la Actividad 3 (act3_pipeline). La Tarea 4 propuso
## reemplazar estas líneas por un "pip install act3-pipeline-mlops" normal.
COPY libreria/act3_pipeline-0.1.0-py3-none-any.whl /tmp/
## RUN: ejecuta un comando DURANTE LA CONSTRUCCIÓN y guarda el resultado como
## una capa. --no-cache-dir: no guardar la caché de descargas de pip (la
## imagen pesaría más sin ningún beneficio). El "&& rm" va en el MISMO RUN: si
## fuera en otro, el .whl seguiría ocupando espacio en la capa anterior.
RUN pip install --no-cache-dir -r requirements.txt /tmp/act3_pipeline-0.1.0-py3-none-any.whl \
    && rm /tmp/act3_pipeline-0.1.0-py3-none-any.whl

# Ahora si, el codigo (lo que mas cambia va al final).
COPY entrenador/entrenar.py ./

# Usuario sin privilegios: si alguien se mete al contenedor, no es root.
#
# El mkdir + chown de /modelos NO es opcional. Cuando Docker monta un volumen
# con nombre que esta vacio, copia el contenido, el propietario y los permisos
# que tenga esa carpeta EN LA IMAGEN. Si la carpeta no existe en la imagen, el
# volumen nace perteneciendo a root y el usuario mlops no puede escribir:
#   PermissionError: [Errno 13] Permission denied: '/modelos/modelo.joblib'
## useradd crea el usuario mlops con uid 1000; chown le da la propiedad de
## /app y /modelos. Si el volumen ya se creó con el dueño equivocado, hay que
## borrarlo (docker compose down -v) para que nazca de nuevo.
RUN useradd --create-home --uid 1000 mlops \
    && mkdir -p /modelos \
    && chown -R mlops:mlops /app /modelos
## USER: a partir de aquí (y al ejecutar el contenedor) se corre como mlops.
USER mlops

## CMD: el comando que ejecuta el contenedor al arrancar (NO durante el build).
## Forma "exec" (lista JSON): python es el proceso principal (PID 1) y recibe
## las señales de "docker stop". Cuando entrenar.py termina, el contenedor muere
## con su mismo código de salida: 0 = éxito, que es lo que espera
## "condition: service_completed_successfully" en el compose.
## No hay EXPOSE: el entrenador no escucha en ningún puerto.
CMD ["python", "entrenar.py"]
