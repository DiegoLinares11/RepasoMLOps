"""Servicio API.

Microservicio que sirve el modelo entrenado. No entrena nada: **lee** el modelo
que el servicio `entrenador` dejo en el volumen compartido y expone endpoints
HTTP para predecir. Cada prediccion se guarda en Postgres, que a su vez
persiste en otro volumen.

Endpoints:
    GET  /salud          estado del servicio, del modelo y de la base
    GET  /modelo         metadatos del modelo entrenado
    POST /predecir       predice el resultado de un partido y lo guarda
    GET  /predicciones   historial guardado en Postgres
"""
## =============================================================================
## api/main.py REAL de la Actividad 4, comentado línea por línea.
## Los comentarios con "##" son del repaso; los de un "#" venían en el original.
## El código es idéntico al del repo: https://github.com/DiegoLinares11/Actividad4-MLOPS
##
## Necesita fastapi, uvicorn, pydantic y psycopg (no están en el requirements
## del repaso: este archivo es para LEER). Dentro del contenedor lo ejecuta:
##   uvicorn main:app --host 0.0.0.0 --port 8000
## y FastAPI genera sola la documentación interactiva en http://localhost:8000/docs
## =============================================================================

## Permite escribir anotaciones modernas (dict | None) en versiones viejas de Python.
from __future__ import annotations

import json
import os
import socket                      ## para saber el nombre del contenedor (hostname)
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import joblib                      ## carga el modelo serializado por el entrenador
import pandas as pd                ## el pipeline espera un DataFrame con columnas crudas
import psycopg                     ## cliente de Postgres (versión 3)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

## --- Configuración por VARIABLES DE ENTORNO ----------------------------------
## Los valores vienen de "environment:" en docker-compose.yml. El segundo
## argumento de os.getenv es el valor por defecto si la variable no existe.
## Así la misma imagen sirve en tu laptop, en pruebas y en producción.
DIR_MODELOS = Path(os.getenv("DIR_MODELOS", "/modelos"))   ## donde se monta el volumen (ro)
RUTA_MODELO = DIR_MODELOS / "modelo.joblib"
RUTA_METADATOS = DIR_MODELOS / "metadatos.json"
## postgresql://mlops:clave@db:5432/predicciones  -> "db" es el nombre del servicio
URL_BD = os.getenv("URL_BD", "")

## Estado global del proceso: el modelo se carga UNA vez y se reutiliza en cada
## petición (cargarlo en cada /predecir sería lentísimo).
estado: dict[str, Any] = {"modelo": None, "metadatos": None}


def cargar_modelo() -> bool:
    """Carga el modelo del volumen. Se reintenta si todavia no existe."""
    ## Si ya está en memoria, no hacer nada.
    if estado["modelo"] is not None:
        return True
    ## Si el entrenador todavía no dejó el archivo, avisar (False) sin romper.
    if not RUTA_MODELO.exists():
        return False
    ## joblib.load reconstruye el Pipeline. Para eso IMPORTA act3_pipeline
    ## (PorcentajeATexto, RatioATexto): por eso el Dockerfile de la API instala
    ## el mismo paquete y las mismas versiones exactas que el entrenador.
    estado["modelo"] = joblib.load(RUTA_MODELO)
    if RUTA_METADATOS.exists():
        estado["metadatos"] = json.loads(RUTA_METADATOS.read_text(encoding="utf-8"))
    ## flush=True: que el mensaje salga ya en "docker compose logs api".
    print(f"[api] modelo cargado desde {RUTA_MODELO}", flush=True)
    return True


def guardar_prediccion(entrada: dict, prediccion: str, probabilidades: dict | None) -> bool:
    """Inserta la prediccion en Postgres. Si la base no esta, no rompe la API."""
    if not URL_BD:
        return False
    try:
        ## "with" abre la conexión y el cursor y los cierra al salir; si todo
        ## salió bien, psycopg hace COMMIT automáticamente.
        with psycopg.connect(URL_BD, connect_timeout=5) as con, con.cursor() as cur:
            cur.execute(
                ## %s son PARÁMETROS: psycopg los escapa. Nunca armar el SQL con
                ## f-strings (inyección SQL).
                """INSERT INTO predicciones (entrada, prediccion, probabilidades, modelo)
                   VALUES (%s, %s, %s, %s)""",
                (
                    json.dumps(entrada, ensure_ascii=False),
                    prediccion,
                    json.dumps(probabilidades, ensure_ascii=False) if probabilidades else None,
                    (estado["metadatos"] or {}).get("modelo", "desconocido"),
                ),
            )
        return True
    except Exception as exc:  # la API sigue viva aunque la base falle
        ## Fallo AISLADO: si Postgres se cae, se sigue prediciendo; solo se
        ## deja de guardar el historial ("guardado_en_bd": false).
        print(f"[api] no se pudo guardar en la base: {exc}", flush=True)
        return False


## lifespan: código que corre al ARRANCAR el servidor (antes del yield) y al
## APAGARLO (después). Aquí se intenta cargar el modelo una vez al inicio.
@asynccontextmanager
async def lifespan(app: FastAPI):
    cargar_modelo()
    yield


## La aplicación. title/description/version aparecen en /docs.
app = FastAPI(
    title="API de prediccion — Champions League",
    description="Actividad 4 (MLE/MLOps, UVG). Sirve el pipeline calibrado en la Actividad 3.",
    version="1.0.0",
    lifespan=lifespan,
)


## Esquema de ENTRADA con pydantic: FastAPI valida el JSON recibido contra esta
## clase. Si falta un campo o el tipo no cuadra, responde 422 automáticamente,
## sin que el modelo llegue a ver datos rotos. Los "examples" llenan /docs.
class Partido(BaseModel):
    """Las mismas columnas crudas que espera el pipeline de la Actividad 3.

    Ojo con el formato: la posesion va como texto ('63%') y los tiros/atajadas
    como texto ('3 of 10'), porque asi vienen en el CSV original y el pipeline
    los convierte adentro.
    """

    home_team: str = Field(examples=["Real Madrid"])
    away_team: str = Field(examples=["Marseille"])
    home_possession: str = Field(examples=["43%"])
    away_possession: str = Field(examples=["57%"])
    home_shots_on_target: str = Field(examples=["15 of 28"])
    away_shots_on_target: str = Field(examples=["5 of 15"])
    home_saves: str = Field(examples=["4 of 5"])
    away_saves: str = Field(examples=["13 of 15"])
    ## float | None = None -> campo opcional (en el CSV hay nulos en home_saves_pct).
    home_shots_on_target_pct: float | None = Field(default=None, examples=[53.6])
    away_shots_on_target_pct: float | None = Field(default=None, examples=[33.3])
    home_saves_pct: float | None = Field(default=None, examples=[80.0])
    away_saves_pct: float | None = Field(default=None, examples=[86.7])


## GET /salud: lo usa el healthcheck del compose (urllib.request.urlopen).
## Responde 200 aunque la base esté caída: informa, no tumba el servicio.
@app.get("/salud")
def salud() -> dict:
    bd_ok = False
    if URL_BD:
        try:
            with psycopg.connect(URL_BD, connect_timeout=3) as con, con.cursor() as cur:
                cur.execute("SELECT 1")
                bd_ok = True
        except Exception:
            bd_ok = False
    return {
        "estado": "ok",
        ## El hostname de un contenedor es su ID corto (p. ej. "72e91038c58f").
        ## Con "docker compose up --scale api=3" verías que cambia entre peticiones.
        "contenedor": socket.gethostname(),
        "modelo_cargado": cargar_modelo(),
        "base_de_datos": bd_ok,
    }


## GET /modelo: devuelve metadatos.json (métricas, hiperparámetros, versiones,
## qué contenedor lo entrenó y cuándo).
@app.get("/modelo")
def modelo() -> dict:
    if not cargar_modelo():
        ## 503 Service Unavailable: "todavía no puedo atenderte".
        raise HTTPException(503, "El modelo todavia no existe. ¿Ya corrio el entrenador?")
    return estado["metadatos"] or {"aviso": "el modelo existe pero sin metadatos"}


## POST /predecir: recibe un Partido en JSON, devuelve la predicción.
## El parámetro tipado "partido: Partido" es lo que activa la validación.
@app.post("/predecir")
def predecir(partido: Partido) -> dict:
    if not cargar_modelo():
        raise HTTPException(503, "El modelo todavia no existe. ¿Ya corrio el entrenador?")

    ## pydantic -> dict -> DataFrame de UNA fila con las columnas crudas.
    entrada = partido.model_dump()
    X = pd.DataFrame([entrada])
    pipe = estado["modelo"]
    ## El pipeline completo hace todo: '43%' -> 43.0, '15 of 28' -> números,
    ## one-hot de equipos, selección de variables y el modelo.
    prediccion = str(pipe.predict(X)[0])

    probabilidades = None
    if hasattr(pipe, "predict_proba"):
        probas = pipe.predict_proba(X)[0]
        ## classes_ da el orden de las columnas de predict_proba.
        probabilidades = {str(c): round(float(p), 4) for c, p in zip(pipe.classes_, probas)}

    guardado = guardar_prediccion(entrada, prediccion, probabilidades)
    return {
        "prediccion": prediccion,
        "probabilidades": probabilidades,
        "guardado_en_bd": guardado,
        "atendido_por": socket.gethostname(),
    }


## GET /predicciones?limite=10: historial desde Postgres. "limite" es un
## parámetro de consulta (query string) con valor por defecto 10.
@app.get("/predicciones")
def predicciones(limite: int = 10) -> dict:
    if not URL_BD:
        raise HTTPException(503, "Este servicio no tiene base de datos configurada")
    try:
        with psycopg.connect(URL_BD, connect_timeout=5) as con, con.cursor() as cur:
            cur.execute(
                """SELECT id, creado_en, prediccion, modelo, entrada
                   FROM predicciones ORDER BY id DESC LIMIT %s""",
                (limite,),
            )
            filas = cur.fetchall()
            cur.execute("SELECT count(*) FROM predicciones")
            total = cur.fetchone()[0]
    except Exception as exc:
        raise HTTPException(503, f"No se pudo consultar la base: {exc}")

    ## "total_historico" es la prueba de persistencia: tras "docker compose down"
    ## y "up" sigue igual; tras "down -v" vuelve a 0.
    return {
        "total_historico": total,
        "predicciones": [
            {
                "id": f[0],
                "creado_en": f[1].isoformat(),
                "prediccion": f[2],
                "modelo": f[3],
                ## entrada es JSONB: psycopg ya la devuelve como dict de Python.
                "partido": f"{f[4].get('home_team')} vs {f[4].get('away_team')}",
            }
            for f in filas
        ],
    }
