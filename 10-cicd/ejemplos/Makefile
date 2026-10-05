# =============================================================================
# Makefile  -  Ejercicio 3 (Ejecicio3-MLOPS/Makefile)
# -----------------------------------------------------------------------------
# Makefile REAL del Ejercicio 3 con comentarios de repaso.
#
# Qué es make: una herramienta vieja (1976) que ejecuta "recetas" con nombre.
#   objetivo: dependencias
#   <TAB>comando
# OJO: la sangría de los comandos DEBE ser un TAB, no espacios
# (si no: "Makefile: *** missing separator").
#
# Por qué lo usamos (idea del tutorial de DataCamp citado en el PDF):
#   - El workflow llama `make limpiar` y en la laptop también corremos
#     `make limpiar`: EXACTAMENTE el mismo comando en los dos lados.
#     Si falla en la nube, se reproduce local sin adivinar qué hizo el runner.
#   - Si mañana cambiamos de GitHub Actions a GitLab CI o Jenkins, los
#     comandos ya viven fuera del YAML.
#
# En Windows: make no viene instalado. Opciones: Git Bash + `choco install make`,
# WSL, o correr los comandos python a mano (son de una línea).
# =============================================================================

# Las mismas etapas se corren igual en la laptop y en GitHub Actions.

# .PHONY = estos objetivos NO son archivos. Sin esto, si existiera un archivo
# llamado "limpiar", make diría "limpiar is up to date" y no haría nada.
.PHONY: instalar extraer limpiar entrenar evaluar pipeline limpiar-todo

# make instalar  -> dependencias declaradas (lo primero que hace cada job del CI)
instalar:
	pip install --upgrade pip
	pip install -r requirements.txt

# Una receta por etapa. Cada script lee de artefactos/ y escribe en artefactos/.
extraer:
	python src/extraer.py

limpiar:
	python src/limpiar.py

entrenar:
	python src/entrenar.py

# Si evaluar.py devuelve código 1, make se detiene y también devuelve error
# (por eso el step `run: make evaluar` sale en rojo en Actions).
evaluar:
	python src/evaluar.py

# Objetivo "agregado": no tiene comandos propios, solo dependencias.
# make las corre en orden: extraer, limpiar, entrenar, evaluar.
# Si una falla, make se detiene ahí (igual que `needs:` en el workflow).
pipeline: extraer limpiar entrenar evaluar

# Borra todos los artefactos para empezar de cero.
limpiar-todo:
	rm -rf artefactos
