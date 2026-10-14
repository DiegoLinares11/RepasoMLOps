"""Generador de datos sintéticos del tutorial de MLflow (demanda de manzanas).

El tutorial "Your First MLflow Model" de la documentación de MLflow genera un
dataset artificial de ventas de manzanas para entrenar su primer modelo. Aquí
están dos versiones:

``generar_datos_tutorial``
    El código del tutorial con **un solo cambio**: la línea que rellena el
    primer valor de ``previous_days_demand``. El original usa
    ``fillna(method="bfill", inplace=True)`` sobre una columna, que pandas 3 ya
    no acepta (se eliminó el argumento ``method``) y que, con *copy-on-write*,
    tampoco modificaría el DataFrame.

``generar_datos_mejorado``
    Nuestra versión, que corrige los problemas que encontramos al analizarlo
    (detalle en ``notebooks/02_datos_sinteticos_mejoras.ipynb``):

    1. El efecto de cosecha del original siempre vale 0: suma dos senos
       desfasados medio periodo, ``sin(x) + sin(x - pi) = 0``. Aquí se usa un
       solo coseno con picos en marzo y septiembre, que es lo que sugiere el
       propio tutorial al poner las promociones en abril y octubre ("un mes
       después del pico de cosecha").
    2. Las fechas salen de ``datetime.now()``, así que el dataset cambia según
       el día (y hasta el microsegundo) en que se ejecuta, aunque tenga semilla.
       Aquí las fechas terminan en una fecha fija.
    3. Usa ``np.random.seed`` (estado global); aquí cada llamada tiene su propio
       generador (``np.random.default_rng``) y la semilla es un argumento.
    4. La inflación salta cada 1 de enero porque se calcula con el año
       calendario; aquí crece de forma continua con los días transcurridos.
    5. La temperatura, la lluvia y los feriados no influyen en la demanda:
       son columnas de ruido. Aquí se les da un efecto (se puede apagar con
       ``efectos_clima=False``).
    6. El primer ``previous_days_demand`` se rellenaba con la demanda del mismo
       día (fuga de información en esa fila); aquí esa fila se descarta.
    7. Arma las fechas, el fin de semana y el mes con ciclos de Python; aquí
       todo es vectorizado.

Los nombres de las columnas se dejan en inglés, igual que en el tutorial,
para poder comparar las dos versiones columna por columna.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def generar_datos_tutorial(base_demand: int = 1000, n_rows: int = 5000) -> pd.DataFrame:
    """Copia del generador del tutorial de MLflow (ver docstring del módulo)."""
    # Set seed for reproducibility
    np.random.seed(9999)

    # Create date range
    dates = [datetime.now() - timedelta(days=i) for i in range(n_rows)]
    dates.reverse()

    # Generate features
    df = pd.DataFrame(
        {
            "date": dates,
            "average_temperature": np.random.uniform(10, 35, n_rows),
            "rainfall": np.random.exponential(5, n_rows),
            "weekend": [(date.weekday() >= 5) * 1 for date in dates],
            "holiday": np.random.choice([0, 1], n_rows, p=[0.97, 0.03]),
            "price_per_kg": np.random.uniform(0.5, 3, n_rows),
            "month": [date.month for date in dates],
        }
    )

    # Introduce inflation over time (years)
    df["inflation_multiplier"] = 1 + (df["date"].dt.year - df["date"].dt.year.min()) * 0.03

    # Incorporate seasonality due to apple harvests
    df["harvest_effect"] = np.sin(2 * np.pi * (df["month"] - 3) / 12) + np.sin(
        2 * np.pi * (df["month"] - 9) / 12
    )

    # Modify the price_per_kg based on harvest effect
    df["price_per_kg"] = df["price_per_kg"] - df["harvest_effect"] * 0.5

    # Adjust promo periods to coincide with periods lagging peak harvest by 1 month
    peak_months = [4, 10]  # months following the peak availability
    df["promo"] = np.where(
        df["month"].isin(peak_months),
        1,
        np.random.choice([0, 1], n_rows, p=[0.85, 0.15]),
    )

    # Generate target variable based on features
    base_price_effect = -df["price_per_kg"] * 50
    seasonality_effect = df["harvest_effect"] * 50
    promo_effect = df["promo"] * 200

    df["demand"] = (
        base_demand
        + base_price_effect
        + seasonality_effect
        + promo_effect
        + df["weekend"] * 300
        + np.random.normal(0, 50, n_rows)
    ) * df["inflation_multiplier"]  # adding random noise

    # Add previous day's demand
    df["previous_days_demand"] = df["demand"].shift(1)
    # ÚNICO CAMBIO: el original era
    #   df["previous_days_demand"].fillna(method="bfill", inplace=True)
    # que en pandas 3 lanza TypeError.
    df["previous_days_demand"] = df["previous_days_demand"].bfill()

    # Drop temporary columns
    df.drop(columns=["inflation_multiplier", "harvest_effect", "month"], inplace=True)

    return df


def efecto_cosecha(mes: np.ndarray | pd.Series) -> np.ndarray:
    """Estacionalidad por cosecha: +1 en marzo y septiembre, -1 en junio y diciembre.

    ``mes`` puede tener decimales (por ejemplo 3.5 es mediados de marzo), así que
    la curva es continua a lo largo del año.
    """
    return np.cos(2 * np.pi * (np.asarray(mes, dtype=float) - 3) / 6)


def generar_datos_mejorado(
    base_demand: float = 1000,
    n_rows: int = 5000,
    semilla: int = 9999,
    fecha_final: str = "2026-09-30",
    inflacion_anual: float = 0.03,
    efectos_clima: bool = True,
) -> pd.DataFrame:
    """Versión corregida del generador (ver los 7 cambios en el docstring del módulo).

    Devuelve ``n_rows - 1`` filas, porque la primera no tiene demanda del día
    anterior y se descarta en lugar de inventarla.
    """
    rng = np.random.default_rng(semilla)
    fechas = pd.date_range(end=pd.Timestamp(fecha_final), periods=n_rows, freq="D")
    mes = fechas.month + (fechas.day - 1) / fechas.days_in_month  # mes con decimales
    anios = np.asarray((fechas - fechas[0]).days) / 365.25

    df = pd.DataFrame(
        {
            "date": fechas,
            "average_temperature": rng.uniform(10, 35, n_rows),
            "rainfall": rng.exponential(5, n_rows),
            "weekend": (fechas.dayofweek >= 5).astype(int),
            "holiday": rng.choice([0, 1], n_rows, p=[0.97, 0.03]),
        }
    )

    cosecha = efecto_cosecha(mes)
    # En cosecha hay más oferta: el precio baja.
    df["price_per_kg"] = rng.uniform(0.5, 3, n_rows) - 0.5 * cosecha
    # Promoción todo abril y octubre (un mes después de cada pico); el resto, al azar.
    df["promo"] = np.where(np.isin(fechas.month, [4, 10]), 1, rng.choice([0, 1], n_rows, p=[0.85, 0.15]))

    demanda = (
        base_demand
        - 50 * df["price_per_kg"]
        + 50 * cosecha
        + 200 * df["promo"]
        + 300 * df["weekend"]
        + rng.normal(0, 50, n_rows)
    )
    if efectos_clima:
        demanda = (
            demanda
            + 150 * df["holiday"]                              # feriado: más compras
            - 4 * df["rainfall"]                               # lluvia: menos visitas
            - 0.8 * (df["average_temperature"] - 22) ** 2      # se compra más con clima templado
        )
    df["demand"] = demanda * (1 + inflacion_anual * anios)    # inflación continua

    df["previous_days_demand"] = df["demand"].shift(1)
    return df.iloc[1:].reset_index(drop=True)
