import joblib
import pandas as pd
from pathlib import Path
from typing import Tuple

import math

from quality.ml.data_loader import FEATURE_RANGES, get_feature_columns

# Ruta base del módulo ml/
BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "model.pkl"
SCALER_PATH = BASE_DIR / "scaler.pkl"

_model = None
_scaler = None


def _load_artifacts() -> Tuple[object, object]:
    global _model, _scaler
    if _model is None or _scaler is None:
        if not MODEL_PATH.exists() or not SCALER_PATH.exists():
            raise FileNotFoundError("Model or scaler artifacts not found. Run training to create them.")
        _model = joblib.load(MODEL_PATH)
        _scaler = joblib.load(SCALER_PATH)
    return _model, _scaler


def predict_quality(input_data: dict):
    """Predict quality using a dict of features keyed by column name.

    Raises:
        FileNotFoundError: if model artifacts are missing
        ValueError: if input is invalid or missing features
    """
    if not isinstance(input_data, dict):
        raise ValueError("input_data must be a dict mapping feature names to numeric values")

    feature_columns = get_feature_columns()

    missing = [c for c in feature_columns if c not in input_data]
    if missing:
        raise ValueError(f"Faltan variables: {missing}")

    values = {}
    for c in feature_columns:
        try:
            value = float(input_data[c])
        except (TypeError, ValueError):
            raise ValueError(f"Valor no numerico para '{c}'")
        if not math.isfinite(value):
            raise ValueError(f"Valor no valido para '{c}'")
        low, high = FEATURE_RANGES[c]
        if not low <= value <= high:
            raise ValueError(f"'{c}' fuera de rango ({low} a {high}): {value}")
        values[c] = value

    features = pd.DataFrame([[values[c] for c in feature_columns]], columns=feature_columns)

    model, scaler = _load_artifacts()

    features_scaled = scaler.transform(features)

    prediction = model.predict(features_scaled)[0]

    # Algunos modelos no implementan predict_proba; manejar eso
    try:
        confidence = model.predict_proba(features_scaled).max()
    except Exception:
        confidence = 1.0

    return {
        "prediction": int(prediction),
        "confidence": float(round(confidence, 3))
    }
