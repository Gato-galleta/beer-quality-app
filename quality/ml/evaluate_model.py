from pathlib import Path

import joblib
from sklearn.metrics import accuracy_score, classification_report

from quality.ml.data_loader import MAX_TRAINING_ROWS, get_feature_columns, load_data

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.pkl"
SCALER_PATH = BASE_DIR / "scaler.pkl"
EVAL_ROWS = 50_000


def evaluate_model():
    # Se evalua con filas que NO se usaron para entrenar (despues de las
    # primeras MAX_TRAINING_ROWS) y sin cargar el CSV completo.
    df = load_data(nrows=EVAL_ROWS, skiprows=MAX_TRAINING_ROWS)
    if df.empty:
        raise ValueError(
            f"El dataset no tiene filas despues de las {MAX_TRAINING_ROWS} de entrenamiento"
        )
    columns = get_feature_columns()

    X = df[columns]
    y = df["quality_label"]

    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)

    y_pred = model.predict(scaler.transform(X))

    print(f"Filas evaluadas: {len(df)}")
    print("Accuracy:", accuracy_score(y, y_pred))
    print("\nClassification report:\n")
    print(classification_report(y, y_pred))


if __name__ == "__main__":
    evaluate_model()
