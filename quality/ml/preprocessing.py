from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from quality.ml.data_loader import get_feature_columns


def preprocess_data(df):
    """
    Selecciona las 13 variables del modelo, normaliza y devuelve X, y y el scaler.
    """
    X = df[get_feature_columns()]
    y = df["quality_label"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return X_scaled, y, scaler


def split_data(X, y):
    """
    Divide los datos en entrenamiento y prueba manteniendo proporcion de clases.
    """
    return train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
