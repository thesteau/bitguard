import pickle

from core.environments import environments as env

with open(env.MODEL_PATH, 'rb') as f:
    lgb_model = pickle.load(f)

with open(env.SCALER_PATH, "rb") as f:
    scale_loader = pickle.load(f)
