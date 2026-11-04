from quality.ml.predict import predict_quality
from quality.ml.data_loader import get_feature_columns

cols = get_feature_columns()
if not cols:
    # Si no hay columnas, crear una fake
    cols = [f"f{i}" for i in range(3)]

data = {c: 0.5 for c in cols}

try:
    print(predict_quality(data))
except Exception as e:
    import traceback
    traceback.print_exc()