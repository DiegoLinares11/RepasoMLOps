"""
tests/test_pipeline.py  -  EJEMPLO DE REPASO para el repo del Ejercicio 3.

Pruebas automáticas que correría el job `pruebas` de ci-pytest-matrix.yml.
Se ejecutan desde la raíz del repo con:   pytest -v

Hay tres tipos de prueba, y en ML necesitas las tres:
  1. Pruebas de CÓDIGO   -> ¿la función hace lo que dice?  (como en software normal)
  2. Pruebas de DATOS    -> ¿los datos llegan con el formato que el código asume?
  3. Pruebas de MODELO   -> ¿el modelo aprende algo? (la compuerta de calidad)
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from entrenar import construir_pipeline, convertir_texto_a_numero  # noqa: E402

DATOS = Path("datos/champions_league_matches.csv")


# ---------------------------------------------------------------- 1. CÓDIGO
def test_convierte_porcentaje_y_razones():
    df = pd.DataFrame({
        "home_possession": ["63%"], "away_possession": ["37%"],
        "home_shots_on_target": ["3 of 10"], "away_shots_on_target": ["8 of 18"],
        "home_saves": ["4 of 8"], "away_saves": ["2 of 3"],
    })
    out = convertir_texto_a_numero(df)
    assert out.loc[0, "home_possession"] == 63.0
    assert out.loc[0, "home_shots_on_target"] == 3.0
    assert out.loc[0, "home_shots_on_target_intentos"] == 10.0


# ---------------------------------------------------------------- 2. DATOS
@pytest.fixture
def crudo():
    return pd.read_csv(DATOS).dropna(how="all")


def test_columnas_esperadas(crudo):
    for col in ["home_team", "away_team", "home_possession", "result"]:
        assert col in crudo.columns


def test_formato_de_tiros(crudo):
    # El código asume '3 of 10'. Si la fuente cambia a '3/10', esto lo detecta
    # ANTES de entrenar (la compuerta de métricas podría no notarlo).
    ok = crudo["home_shots_on_target"].astype(str).str.fullmatch(r"\d+ of \d+")
    assert ok.mean() > 0.95


def test_clases_validas(crudo):
    assert set(crudo["result"].dropna()) <= {"Home Win", "Away Win", "Draw"}


# ---------------------------------------------------------------- 3. MODELO
def test_modelo_le_gana_al_trivial(crudo):
    from sklearn.dummy import DummyClassifier
    from sklearn.metrics import f1_score
    from sklearn.model_selection import train_test_split

    df = convertir_texto_a_numero(crudo.drop(columns=["score", "winner"]))
    y, X = df["result"], df.drop(columns=["result"])
    Xe, Xp, ye, yp = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    f1 = f1_score(yp, construir_pipeline().fit(Xe, ye).predict(Xp), average="macro")
    f1_trivial = f1_score(yp, DummyClassifier().fit(Xe, ye).predict(Xp),
                          average="macro", zero_division=0)
    assert f1 >= 0.40 and f1 > f1_trivial
