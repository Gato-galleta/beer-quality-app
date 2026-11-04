import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np

from quality.ml.data_loader import get_feature_columns
from quality.ml.predict import predict_quality

# Colocar artefactos dummy
base = Path(__file__).resolve().parents[1] / 'quality' / 'ml'
models_dir = base / 'models'
models_dir.mkdir(parents=True, exist_ok=True)

class DummyScaler:
    def fit(self, X): return self
    def transform(self, X): return X
    def fit_transform(self, X): return X

class DummyModel:
    def fit(self, X, y): pass
    def predict(self, X): return [0 for _ in range(len(X))]
    def predict_proba(self, X): import numpy as _np; return _np.array([[0.5,0.5] for _ in range(len(X))])

joblib.dump(DummyModel(), models_dir / 'model.pkl')
joblib.dump(DummyScaler(), models_dir / 'scaler.pkl')

cols = get_feature_columns()
if not cols:
    cols = [f'f{i}' for i in range(3)]

data = {c: 0.5 for c in cols}

try:
    print('predict result:', predict_quality(data))
except Exception as e:
    import traceback; traceback.print_exc()
