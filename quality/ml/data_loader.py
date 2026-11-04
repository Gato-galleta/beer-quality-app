from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "beer_quality.csv"
QUALITY_SCORE_THRESHOLD = 8.0
MAX_TRAINING_ROWS = 250_000
FEATURE_COLUMNS = (
    "fermentation_time",
    "temperature",
    "ph_level",
    "gravity",
    "alcohol_content",
    "bitterness",
    "color",
    "volume_produced",
    "brewhouse_efficiency",
    "loss_during_brewing",
    "loss_during_fermentation",
    "loss_during_bottling_kegging",
)

# Rangos fisicos amplios (minimo, maximo) para rechazar datos imposibles
# (por ejemplo pH -50 o temperatura 900). Son provisorios: ajustalos con
# los valores reales de la cerveceria cuando los tengas.
FEATURE_RANGES = {
    "fermentation_time": (0, 120),
    "temperature": (-5, 60),
    "ph_level": (0, 14),
    "gravity": (0.9, 1.2),
    "alcohol_content": (0, 20),
    "bitterness": (0, 200),
    "color": (0, 100),
    "volume_produced": (0, 1_000_000_000),
    "brewhouse_efficiency": (0, 100),
    "loss_during_brewing": (0, 100),
    "loss_during_fermentation": (0, 100),
    "loss_during_bottling_kegging": (0, 100),
}


def load_data(nrows=None, skiprows=0):
    """
    Carga el dataset de calidad de cerveza y crea la etiqueta objetivo.

    skiprows: cantidad de filas de datos a saltar (sin contar el encabezado).
    """
    import pandas as pd

    skip = range(1, skiprows + 1) if skiprows else None
    df = pd.read_csv(DATA_PATH, nrows=nrows, skiprows=skip)

    # Normalizar nombres de columnas
    df.columns = df.columns.str.strip().str.lower()

    if "quality_score" not in df.columns:
        raise ValueError("La columna 'quality_score' no existe en el dataset")

    # Quality_Score va de 1 a 10; 8 o mas se considera alta calidad.
    df["quality_label"] = df["quality_score"].apply(
        lambda x: 1 if x >= QUALITY_SCORE_THRESHOLD else 0
    )

    return df


def get_feature_columns():
    """Devuelve el esquema estable del modelo sin leer el dataset."""
    return list(FEATURE_COLUMNS)
