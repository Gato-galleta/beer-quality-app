import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quality.ml.predict import predict_quality
from quality.ml.data_loader import get_feature_columns

cols = get_feature_columns()
if not cols:
    cols = [f"f{i}" for i in range(3)]

print('feature columns:', cols)

data = {c: 0.5 for c in cols}

try:
    print('predict =>', predict_quality(data))
except Exception as e:
    import traceback
    traceback.print_exc()
