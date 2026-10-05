# =============================================================================
# pipeline_en_una_celda.py  -  Ejercicio 4 / Actividad 7
# (Ejecicio3-MLOPS/databricks/pipeline_en_una_celda.py)
# -----------------------------------------------------------------------------
# Script REAL con comentarios de repaso; el código es idéntico al original.
#
# Qué es: las 4 etapas del Ejercicio 3 comprimidas en UNA sola celda, para pegar
# en un notebook de Databricks (o correr en cualquier lado) sin preparar nada.
# Diferencias con pipeline_champions_databricks.py:
#   - NO guarda tabla en Unity Catalog (solo pandas, no usa `spark`).
#   - MLflow es OPCIONAL: el import está dentro de un try/except, así el mismo
#     archivo corre en Databricks (registra el run) y en una laptop sin mlflow
#     (entrena igual y avisa "sin registro").
#   - La compuerta NO hace fallar la celda: solo imprime OK / FALLA.
# Necesita internet (lee el CSV desde GitHub raw).
# =============================================================================
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED, OBJETIVO = 42, "result"
URL = ("https://raw.githubusercontent.com/DiegoLinares11/Ejecicio3-MLOPS/"
       "main/datos/champions_league_matches.csv")

# --- 1. EXTRACCION ---
crudo = pd.read_csv(URL)
print(f"[extraer] {crudo.shape[0]} filas x {crudo.shape[1]} columnas")   # 151 x 18

# --- 2. LIMPIEZA ---
# filas vacías + sin etiqueta fuera; fuga (score, winner) e irrelevantes fuera
limpio = crudo.dropna(how="all").dropna(subset=[OBJETIVO])
quitar = [c for c in ["score", "winner", "date", "venue", "referee"] if c in limpio.columns]
limpio = limpio.drop(columns=quitar).reset_index(drop=True)
print(f"[limpiar] {len(crudo)} -> {len(limpio)} filas | descartadas: {quitar}")   # 151 -> 144

# --- 3. ENTRENAMIENTO ---
PORCENTAJES = ["home_possession", "away_possession"]
RAZONES = ["home_shots_on_target", "away_shots_on_target", "home_saves", "away_saves"]
NUMERICAS = ["home_shots_on_target_pct", "away_shots_on_target_pct",
             "home_saves_pct", "away_saves_pct"]
CATEGORICAS = ["home_team", "away_team"]

datos = limpio.copy()
for col in PORCENTAJES:                      # '63%' -> 63.0
    datos[col] = pd.to_numeric(
        datos[col].astype(str).str.replace("%", "", regex=False).str.strip(), errors="coerce")
for col in RAZONES:                          # '3 of 10' -> 3.0 y 10.0
    partes = datos[col].astype(str).str.extract(r"(\d+)\s*of\s*(\d+)")
    datos[col] = pd.to_numeric(partes[0], errors="coerce")
    datos[col + "_intentos"] = pd.to_numeric(partes[1], errors="coerce")

y = datos[OBJETIVO]
X = datos.drop(columns=[OBJETIVO])
X_ent, X_pru, y_ent, y_pru = train_test_split(
    X, y, test_size=0.2, random_state=SEED, stratify=y)          # 115 / 29

numericas = NUMERICAS + PORCENTAJES + RAZONES + [c + "_intentos" for c in RAZONES]
pipe = Pipeline([
    ("preprocesamiento", ColumnTransformer([
        ("num", Pipeline([("imputar", SimpleImputer(strategy="median")),
                          ("escalar", StandardScaler())]), numericas),
        ("cat", Pipeline([("imputar", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAS),
    ], remainder="drop")),
    ("modelo", LogisticRegression(C=0.541, class_weight="balanced",
                                  max_iter=5000, random_state=SEED)),
])

# Patrón "degradación elegante": si mlflow existe (Databricks), registra el run;
# si no (ImportError u otro fallo), entrena igual sin registro.
try:                                          # MLflow: solo existe en Databricks
    import mlflow
    mlflow.sklearn.autolog()
    with mlflow.start_run(run_name="champions-logistica"):
        pipe.fit(X_ent, y_ent)
    print("[mlflow] entrenamiento registrado en Experiments")
except Exception as exc:
    pipe.fit(X_ent, y_ent)
    print(f"[mlflow] sin registro ({type(exc).__name__}), el modelo se entreno igual")

print(f"[entrenar] entrenamiento={len(X_ent)}  prueba={len(X_pru)}")

# --- 4. EVALUACION ---
pred = pipe.predict(X_pru)
acc, f1 = accuracy_score(y_pru, pred), f1_score(y_pru, pred, average="macro")
tonto = DummyClassifier(strategy="most_frequent").fit(X_ent, y_ent)   # baseline trivial
pt = tonto.predict(X_pru)
acc_t = accuracy_score(y_pru, pt)
f1_t = f1_score(y_pru, pt, average="macro", zero_division=0)

print(f"\n[evaluar] accuracy = {acc:.3f}   (modelo trivial: {acc_t:.3f})")   # 0.621 vs 0.483
print(f"[evaluar] f1_macro = {f1:.3f}   (modelo trivial: {f1_t:.3f})\n")    # 0.542 vs 0.217
print(classification_report(y_pru, pred, digits=3, zero_division=0))
# Solo compara contra el trivial (no revisa el mínimo 0.40) y no detiene nada:
print("OK: le gana al modelo trivial" if f1 > f1_t else "FALLA: no le gana al modelo trivial")
