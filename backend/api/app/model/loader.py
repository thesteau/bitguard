import pickle

from app.environments import environments as env

with open(env.MODEL_PATH, "rb") as f:
    lgb_model = pickle.load(f)["model"]
