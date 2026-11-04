from pathlib import Path
import joblib

from quality.ml.data_loader import MAX_TRAINING_ROWS, get_feature_columns, load_data


def train_model():
    # Importar sklearn localmente para evitar dependencia en import time
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report

    print("Cargando datos...")
    df = load_data(nrows=MAX_TRAINING_ROWS)

    columns = get_feature_columns()
    faltan = [c for c in columns if c not in df.columns]
    if faltan:
        raise ValueError(f"Faltan columnas en el dataset: {faltan}")

    # Mismas 13 variables y mismo orden que usa predict.py
    X = df[columns]
    y = df["quality_label"]

    print("Dividiendo dataset...")
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    print("Escalando características...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print("Entrenando modelo RandomForest...")
    model = RandomForestClassifier(
        n_estimators=50,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train_scaled, y_train)

    print("Evaluando modelo...")
    y_pred = model.predict(X_test_scaled)
    print(classification_report(y_test, y_pred))

    models_dir = Path(__file__).resolve().parent
    model_path = models_dir / "model.pkl"
    scaler_path = models_dir / "scaler.pkl"

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    print(f"Modelo guardado en: {model_path}")
    print(f"Scaler guardado en: {scaler_path}")


if __name__ == "__main__":
    train_model()
