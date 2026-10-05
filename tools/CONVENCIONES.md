# Convenciones del repo RepasoMLOps

Cada tema vive en `NN-nombre/` y corresponde a una carpeta de video local en
`C:\Users\dlinares\Documents\videos-ia\estudio\out\<carpeta-video>\`.
Los videos NO van en el repo (pesan demasiado): se suben como archivos del Release `videos`,
renombrados `NN-nombre-es.mp4` y `NN-nombre-en.mp4`:

```
gh release upload videos NN-nombre-es.mp4 NN-nombre-en.mp4 --repo DiegoLinares11/RepasoMLOps --clobber
```

`--clobber` reemplaza un video que ya existía sin cambiar su link.

## Archivos por tema
```
NN-nombre/
├── README.md        # obligatorio
├── repaso.py        # notebook percent, si el tema tiene código ejecutable en Python
├── repaso.ipynb     # generado y EJECUTADO: python tools/build_nb.py NN-nombre/repaso.py
└── ejemplos/        # opcional: archivos de configuración comentados (Dockerfile, workflow .yml, pyproject.toml...)
```
Temas puramente de infraestructura (Docker, CI/CD, Databricks, ambientes) pueden no
tener repaso.py; en su lugar llevan `ejemplos/` con archivos reales comentados línea
por línea, y un `ejercicios.md` con tareas prácticas para hacer en la compu propia.

## README.md (español, tono de apuntes claros, de lo básico a lo avanzado)
Secciones en este orden:
1. `# NN · Título`
2. Una línea con los links del Release: `🎬 Video: [▶️ en español](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/NN-nombre-es.mp4) · [▶️ in English](…/NN-nombre-en.mp4) · [todos los videos](https://github.com/DiegoLinares11/RepasoMLOps/releases/tag/videos)`.
3. `## 🧱 Conocimiento previo` — qué hay que entender ANTES, explicado desde cero (el estudiante pidió explícitamente que se le explique primero lo previo y luego se profundice).
4. `## 🎯 Qué tienes que saber` — los conceptos clave construidos paso a paso, con ejemplos concretos, analogías y el POR QUÉ de cada cosa. Tablas para comparar.
5. `## 📂 Qué hicimos en el curso` — resumen de la entrega original (repo/PDF), con links y números reales.
6. `## 🧪 Práctica` — qué trae repaso.ipynb o ejemplos/, y cómo correrlo.
7. `## ❓ Preguntas tipo examen` — mínimo 10, formato `**P:** ...` / `**R:** ...`.
8. `## 🏋️ Ejercicios` — 3-5 retos concretos.
9. `## 🔗 Referencias` — repos originales y docs oficiales.

## repaso.py
- Formato percent (`# %% [markdown]` con líneas prefijadas `# `, y `# %%` para código).
- Rutas a datos relativas al tema: `../datos/champions_league_matches.csv` (cwd = carpeta del tema).
- `RANDOM_STATE = 42`, `warnings.filterwarnings("ignore")`, sin internet, < 2 min.
- Librerías disponibles: pandas, numpy, scikit-learn, scipy, matplotlib, seaborn, statsmodels.
  NO hay fastapi, mlflow, docker-py ni pyspark-databricks: no las importes en notebooks.
- Cada bloque de código precedido de markdown con QUÉ y POR QUÉ; tras resultados importantes, `**Interpretación:**` basada en los números REALES que salieron.
- Termina con `## Resumen`.
- Debe ejecutar sin errores: `cd /home/user/RepasoMLOps && python3 tools/build_nb.py NN-nombre/repaso.py` imprime `ok ->`. Verifica que el .ipynb no tenga outputs con `"output_type": "error"`.

## Estilo
- Español neutro. Sin inventar números: los del curso vienen de los resúmenes/PDFs; los del notebook, de ejecutarlo.
- No hagas commits; el orquestador los hace.

## Dataset compartido
`datos/champions_league_matches.csv`: 151 filas (7 vacías que separan jornadas), 18 columnas:
date, home_team, away_team, score, venue, referee, home_possession ('63%'), away_possession,
home_shots_on_target ('3 of 10'), away_shots_on_target, home_saves ('4 of 8'), away_saves,
home_shots_on_target_pct, away_shots_on_target_pct, home_saves_pct, away_saves_pct,
result (Home Win / Away Win / Draw), winner. `score` y `winner` revelan el resultado (fuga).
