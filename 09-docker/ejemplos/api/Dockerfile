# syntax=docker/dockerfile:1
## =============================================================================
## Dockerfile REAL del servicio API (Actividad 4), comentado línea por línea
## Los comentarios con "##" son del repaso; los de un "#" venían en el original.
## Es casi idéntico al del entrenador: mira ese archivo para el detalle de
## FROM, ENV, WORKDIR y la caché de capas. Aquí se comenta lo distinto.
##   docker build -f api/Dockerfile -t act4/api:1.0 .
## =============================================================================

## Misma imagen base y MISMA versión de Python que el entrenador: el modelo se
## serializa en un contenedor y se deserializa en el otro.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

## Primero lo que cambia poco (dependencias)...
## api/requirements.txt fija las MISMAS versiones exactas que el entrenador
## (scikit-learn==1.8.0, pandas==2.3.3, numpy==2.4.1, scipy==1.17.1,
## joblib==1.5.3) y agrega el stack web: fastapi, uvicorn, pydantic, psycopg.
COPY api/requirements.txt ./requirements.txt
COPY libreria/act3_pipeline-0.1.0-py3-none-any.whl /tmp/
# El paquete de la Actividad 3 tambien se instala aqui, aunque la API no
# entrene nada: el modelo guardado con joblib referencia las clases
# PorcentajeATexto y RatioATexto, y Python necesita poder importarlas desde el
# MISMO modulo para reconstruir el pipeline.
## (Un pickle guarda "act3_pipeline.transformers.PorcentajeATexto", no el
## código de la clase. Sin el paquete: ModuleNotFoundError al cargar el modelo.)
RUN pip install --no-cache-dir -r requirements.txt /tmp/act3_pipeline-0.1.0-py3-none-any.whl \
    && rm /tmp/act3_pipeline-0.1.0-py3-none-any.whl

## ...y al final lo que cambia mucho (el código de la API).
COPY api/main.py ./

## Usuario sin privilegios. Aquí no hace falta crear /modelos con chown porque
## la API monta el volumen en SOLO LECTURA (modelos:/modelos:ro): nunca escribe.
RUN useradd --create-home --uid 1000 mlops && chown -R mlops:mlops /app
USER mlops

## EXPOSE: DOCUMENTA que el contenedor escucha en el 8000. No abre nada por sí
## solo: lo que realmente publica el puerto hacia tu compu es
## "ports: - 8000:8000" en el compose (o "docker run -p 8000:8000").
EXPOSE 8000
## uvicorn = servidor web que ejecuta la app de FastAPI.
##   main:app        -> en el módulo main.py, el objeto llamado app
##   --host 0.0.0.0  -> escuchar en TODAS las interfaces. Con el valor por
##                      defecto (127.0.0.1) solo aceptaría conexiones desde
##                      DENTRO del contenedor y localhost:8000 no respondería.
##   --port 8000     -> el puerto interno (el lado derecho de "8000:8000").
##
## CMD vs ENTRYPOINT: CMD es el comando por defecto y se reemplaza fácil
## (docker run act4/api:1.0 python -c "import sklearn" ejecuta eso en vez de
## uvicorn). ENTRYPOINT fija el ejecutable y lo que pongas después se le pasa
## como argumentos. Para un servicio así, CMD basta.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
