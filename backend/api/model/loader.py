import pickle
import pandas as pd
from sklearn.preprocessing import scale
from core.environments import environments as env

with open(env.MODEL_PATH, 'rb') as f:
    loaded = pickle.load(f)

with open(env.SCALER_PATH, "rb") as f:
    scale_loader = pickle.load(f)

# Unwrap if double-wrapped
if hasattr(loaded, 'model') and hasattr(loaded.model, 'predict_proba'):
    lgb_model = loaded.model  # raw LightGBM
elif hasattr(loaded, 'predict_proba'):
    lgb_model = loaded  # already raw
else:
    lgb_model = loaded  # BitGuard, use predict_score directly

