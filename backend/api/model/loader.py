import __main__
import pickle
import environments.environments as env


class BitGuard:
    pass


__main__.BitGuard = BitGuard


def load_model():
    model_path = env.MODEL_PATH
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    return model
