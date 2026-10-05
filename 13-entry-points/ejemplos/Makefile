# Makefile de la Actividad 9
#
# Cada etapa del pipeline es un entry point (un comando que creó el
# instalador). El Makefile no sabe nada de Python ni de scikit-learn: solo
# llama a esos comandos en orden y decide cuáles hace falta volver a correr,
# comparando la fecha de cada archivo con la de los archivos de los que depende.
#
#   make pipeline                 # datos -> entrenar -> evaluar -> predecir
#   make entrenar N_ITER=20       # cambiar una variable al vuelo
#   make pipeline RUN="uv run"    # el mismo pipeline con otro gestor de paquetes
#
# Requiere GNU make 4.3 o más nuevo (por la regla de objetivos agrupados &:).
# En Windows se instala con conda: está en environment.yml.

# --- Variables (se pueden cambiar desde la línea de comandos) ---------------
PYTHON   ?= python
# Prefijo para correr los comandos dentro de un ambiente sin activarlo:
#   RUN="uv run"   RUN="poetry run"   RUN="conda run -n act9-mlops"
RUN      ?=
FAMILIAS ?= todas
N_ITER   ?= 60
N_JOBS   ?= -1
UMBRAL   ?= 0.50

# --- Archivos que produce cada etapa -----------------------------------------
CSV_CRUDO    := src/act9_pipeline/datasets/champions_league_matches.csv
DIR_DATOS    := datos/procesados
TRAIN        := $(DIR_DATOS)/train.csv
TEST         := $(DIR_DATOS)/test.csv
MODELO       := modelos/modelo.joblib
METRICAS     := reportes/metricas.json
PREDICCIONES := reportes/predicciones.csv

# Si un comando falla, make borra el archivo que estaba generando. Así una
# evaluación que no pasó el umbral no deja un metricas.json "nuevo" que haga
# creer a make que ya no hay nada que hacer.
.DELETE_ON_ERROR:

.PHONY: help install install-dev plugin-knn info modelos datos entrenar evaluar \
        predecir pipeline all test build clean

help:
	@echo Objetivos disponibles:
	@echo   make install       instala el paquete y crea los comandos act9-*
	@echo   make install-dev   igual, con pytest y build
	@echo   make plugin-knn    instala el plugin externo act9-modelo-knn
	@echo   make info          equipo, ambiente y entry points registrados
	@echo   make modelos       familias de modelos descubiertas como plugins
	@echo   make datos         act9-datos: limpia y separa train/test
	@echo   make entrenar      act9-entrenar: calibra y guarda el modelo
	@echo   make evaluar       act9-evaluar: metricas y compuerta de calidad
	@echo   make predecir      act9-predecir: predicciones en CSV
	@echo   make pipeline      las cuatro etapas, solo las que hagan falta
	@echo   make test          pruebas con pytest
	@echo   make build         construye el wheel y el sdist en dist/
	@echo   make clean         borra datos procesados, modelos y reportes

# --- Instalación: aquí es donde se crean los ejecutables de los entry points --
install:
	$(PYTHON) -m pip install -e .

install-dev:
	$(PYTHON) -m pip install -e ".[dev]"

plugin-knn:
	$(PYTHON) -m pip install -e plugins/act9-modelo-knn

info:
	$(RUN) act9 info

modelos:
	$(RUN) act9 modelos

# --- Etapas del pipeline: cada receta llama a un entry point -----------------
# act9-datos escribe los dos archivos a la vez: objetivo agrupado (&:).
$(TRAIN) $(TEST) &: $(CSV_CRUDO)
	$(RUN) act9-datos --salida $(DIR_DATOS)

$(MODELO): $(TRAIN)
	$(RUN) act9-entrenar --entrada $(TRAIN) --salida modelos --familias $(FAMILIAS) --n-iter $(N_ITER) --n-jobs $(N_JOBS)

# act9-evaluar devuelve código 1 si f1_macro < UMBRAL, y make se detiene.
$(METRICAS): $(MODELO) $(TEST)
	$(RUN) act9-evaluar --modelo $(MODELO) --entrada $(TEST) --salida reportes --umbral $(UMBRAL)

$(PREDICCIONES): $(MODELO) $(TEST) $(METRICAS)
	$(RUN) act9-predecir --modelo $(MODELO) --entrada $(TEST) --salida $(PREDICCIONES)

datos: $(TRAIN) $(TEST)
entrenar: $(MODELO)
evaluar: $(METRICAS)
predecir: $(PREDICCIONES)
pipeline: predecir
all: install pipeline

# --- Calidad y empaquetado ----------------------------------------------------
test:
	$(RUN) $(PYTHON) -m pytest -q

build:
	$(PYTHON) -m build

# Con Python y no con rm, para que funcione igual en Linux y en Windows.
clean:
	$(PYTHON) -c "import shutil; [shutil.rmtree(d, ignore_errors=True) for d in ['$(DIR_DATOS)', 'modelos', 'reportes', 'build']]"
