import __main__
import pickle


class BitGuard:
    pass


__main__.BitGuard = BitGuard


def load_model():
    model_path = "/app/model/bitguard_lightgbm.pkl"  # TODO - add to env
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    return model
