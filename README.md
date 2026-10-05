# 🛠️ Repaso de MLOps

Repo de estudio del curso **Machine Learning Engineering (MLE/MLOps)** de la UVG,
construido a partir de mis entregas del curso. Cada tema corresponde a uno de mis
videos de repaso, va de lo básico a lo avanzado y trae práctica ejecutable.

Hilo conductor: casi todo el curso usa el mismo dataset, **151 partidos de la UEFA
Champions League**, y el mismo problema, predecir si gana el local, gana la visita
o empatan. Cada tema le agrega una pieza nueva a ese mismo proyecto.

## 🗺️ Ruta de estudio

| # | Tema | 🎬 Carpeta del video | Entrega del curso |
|---|---|---|---|
| [00](00-por-que-mlops/) | **¿Por qué MLOps?** Ciclo de vida, madurez, drift | `mlops-general` ⭐ | Visión general |
| [01](01-champions-eda/) | Análisis exploratorio del dataset y fuga de información | `champions` | Ejercicio 1 |
| [02](02-overfitting/) | Sobreajuste, sesgo-varianza y validación cruzada | `overfitting` | Primeros videos |
| [03](03-caso-gasolina/) | Caso de estudio: precios de combustible en Guatemala | `caso-gasolina` | Caso de Estudio 1 |
| [04](04-pipelines-datos/) | Pipelines de datos y comandos de pandas | `pipelines-datos` | Ejercicio 2 + Tarea 3 |
| [05](05-pipeline-sklearn/) | Pipeline de scikit-learn empaquetado | `pipeline-sklearn` | Actividad 1 |
| [06](06-hiperparametros/) | Calibración de hiperparámetros | `hiperparametros` | Actividad 3 |
| [07](07-ambientes-virtuales/) | Ambientes virtuales y dependencias | `ambientes-virtuales` | Taller 2 |
| [08](08-publicar-paquete/) | Empaquetar y publicar en TestPyPI | `publicar-paquete` | Actividad 6 + Tarea 4 |
| [09](09-docker/) | Docker, Compose y microservicios | `docker` | Actividad 4 |
| [10](10-cicd/) | CI/CD con GitHub Actions y compuerta de calidad | `cicd` | Taller 1 + Actividad 5 + Ejercicio 3 |
| [11](11-databricks/) | Databricks, medallón, Unity Catalog y MLflow | `databricks` | Ejercicio 4 + Actividad 7 |
| [12](12-simulacro/) | **Simulacro**: 50 preguntas con respuestas | — | Todos |

## 🎬 Dónde están los videos

Los videos viven en mi compu, no en el repo, porque pesan demasiado para GitHub:

```
C:\Users\dlinares\Documents\videos-ia\estudio\out\<carpeta>\
    <carpeta>-es.mp4        video en español
    <carpeta>-en.mp4        video en inglés
    revision-es.png         hoja de revisión en español
    revision-en.png         hoja de revisión en inglés
```

Por ejemplo, el general en español es
`C:\Users\dlinares\Documents\videos-ia\estudio\out\mlops-general\mlops-general-es.mp4`.

Los videos de `champions` y `overfitting` son los dos primeros, todavía con el
Chepe viejo.

El `.gitignore` excluye `*.mp4`, así que aunque copies videos dentro del repo no se
suben por accidente.

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
- [Portafolio-MLOPS](https://github.com/Andyfer004/Portafolio-MLOPS): portafolio del equipo, Taller 1, Ejercicio 2 y Tarea 3.
- [PF-ML](https://github.com/Andyfer004/PF-ML): proyecto final de precios de combustible.
