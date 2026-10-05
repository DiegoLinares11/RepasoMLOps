# 🛠️ Repaso de MLOps

Repo de estudio del curso **Machine Learning Engineering (MLE/MLOps)** de la UVG,
construido a partir de mis entregas del curso. Cada tema corresponde a uno de mis
videos de repaso, va de lo básico a lo avanzado y trae práctica ejecutable.

Hilo conductor: casi todo el curso usa el mismo dataset, **151 partidos de la UEFA
Champions League**, y el mismo problema, predecir si gana el local, gana la visita
o empatan. Cada tema le agrega una pieza nueva a ese mismo proyecto.

## 🗺️ Ruta de estudio

| # | Tema | 🎬 Video | Entrega del curso |
|---|---|---|---|
| [00](00-por-que-mlops/) | **¿Por qué MLOps?** Ciclo de vida, madurez, drift | [ES](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/00-por-que-mlops-es.mp4) · [EN](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/00-por-que-mlops-en.mp4) ⭐ | Visión general |
| [01](01-champions-eda/) | Análisis exploratorio del dataset y fuga de información | [ES](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/01-champions-eda-es.mp4) · [EN](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/01-champions-eda-en.mp4) | Ejercicio 1 |
| [02](02-overfitting/) | Sobreajuste, sesgo-varianza y validación cruzada | [ES](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/02-overfitting-es.mp4) · [EN](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/02-overfitting-en.mp4) | Primeros videos |
| [03](03-caso-gasolina/) | Caso de estudio: precios de combustible en Guatemala | [ES](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/03-caso-gasolina-es.mp4) · [EN](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/03-caso-gasolina-en.mp4) | Caso de Estudio 1 |
| [04](04-pipelines-datos/) | Pipelines de datos y comandos de pandas | [ES](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/04-pipelines-datos-es.mp4) · [EN](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/04-pipelines-datos-en.mp4) | Ejercicio 2 + Tarea 3 |
| [05](05-pipeline-sklearn/) | Pipeline de scikit-learn empaquetado | [ES](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/05-pipeline-sklearn-es.mp4) · [EN](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/05-pipeline-sklearn-en.mp4) | Actividad 1 |
| [06](06-hiperparametros/) | Calibración de hiperparámetros | [ES](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/06-hiperparametros-es.mp4) · [EN](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/06-hiperparametros-en.mp4) | Actividad 3 |
| [07](07-ambientes-virtuales/) | Ambientes virtuales y dependencias | [ES](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/07-ambientes-virtuales-es.mp4) · [EN](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/07-ambientes-virtuales-en.mp4) | Taller 2 |
| [08](08-publicar-paquete/) | Empaquetar y publicar en TestPyPI | [ES](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/08-publicar-paquete-es.mp4) · [EN](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/08-publicar-paquete-en.mp4) | Actividad 6 + Tarea 4 |
| [09](09-docker/) | Docker, Compose y microservicios | [ES](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/09-docker-es.mp4) · [EN](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/09-docker-en.mp4) | Actividad 4 |
| [10](10-cicd/) | CI/CD con GitHub Actions y compuerta de calidad | [ES](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/10-cicd-es.mp4) · [EN](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/10-cicd-en.mp4) | Taller 1 + Actividad 5 + Ejercicio 3 |
| [11](11-databricks/) | Databricks, medallón, Unity Catalog y MLflow | [ES](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/11-databricks-es.mp4) · [EN](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/11-databricks-en.mp4) | Ejercicio 4 + Actividad 7 |
| [12](12-simulacro/) | **Simulacro**: 50 preguntas con respuestas | — | Todos |
| [13](13-entry-points/) | Entry points: el pipeline como comandos y plugins | [ES](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/13-entry-points-es.mp4) · [EN](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/13-entry-points-en.mp4) | Actividad 9 |

## 🎬 Dónde están los videos

Todos los videos están en el Release **[Videos de repaso](https://github.com/DiegoLinares11/RepasoMLOps/releases/tag/videos)** del repo, en español y
en inglés. Los links de la tabla de arriba y del inicio de cada tema abren el video directo.

Se subieron como archivos del Release y no al repo porque pesan unos 20 MB cada uno: así el
`git clone` sigue siendo liviano. El `.gitignore` excluye `*.mp4` para que no se suban por
accidente.

## 📁 Qué hay en cada tema

```
NN-tema/
├── README.md      ← conocimiento previo, conceptos paso a paso, qué hicimos
│                    en el curso, preguntas tipo examen y ejercicios
├── repaso.ipynb   ← código ejecutado con resultados, en los temas de Python
└── ejemplos/      ← Dockerfile, workflows, pyproject.toml reales y comentados,
                     en los temas de infraestructura
```

Sugerencia: mira el video, lee el README del tema, corre el notebook o los
ejemplos, y contesta las preguntas sin ver la respuesta.

## ▶️ Cómo correr los notebooks

```powershell
git clone https://github.com/DiegoLinares11/RepasoMLOps.git
cd RepasoMLOps
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
jupyter lab
```

Para modificar un notebook, edita su `repaso.py` y regenéralo:

```powershell
python tools/build_nb.py 05-pipeline-sklearn/repaso.py
```

## 🔗 Repos originales del curso

- [Actividad1-MLOPS](https://github.com/DiegoLinares11/Actividad1-MLOPS): pipeline de scikit-learn empaquetado.
- [Actividad3-MLOPS](https://github.com/DiegoLinares11/Actividad3-MLOPS): calibración de hiperparámetros.
- [Actividad4-MLOPS](https://github.com/DiegoLinares11/Actividad4-MLOPS): Docker y microservicios.
- [Ejecicio3-MLOPS](https://github.com/DiegoLinares11/Ejecicio3-MLOPS): CI/CD con GitHub Actions y notebooks de Databricks.
- [Tarea4-MLOPS](https://github.com/DiegoLinares11/Tarea4-MLOPS): paquete publicado en TestPyPI.
- [Actividad-9-MLOPS](https://github.com/DiegoLinares11/Actividad-9-MLOPS): entry points, plugins y Makefile.
- [Portafolio-MLOPS](https://github.com/Andyfer004/Portafolio-MLOPS): portafolio del equipo, Taller 1, Ejercicio 2 y Tarea 3.
- [PF-ML](https://github.com/Andyfer004/PF-ML): proyecto final de precios de combustible.
