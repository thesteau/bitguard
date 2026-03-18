import pickle

import pandas as pd


FEATURE_COLUMNS = [
    "in_degree",
    "out_degree",
    "total_degree",
    "total_received_btc",
    "total_sent_btc",
    "avg_received_btc",
    "avg_sent_btc",
    "balance",
    "equal_output_count",
    "suspicious_blocks",
    "max_equal_outputs",
    "fan_in_out_ratio",
    "lifetime_blocks",
    "tx_frequency",
    "dust_tx_count",
    "dust_ratio",
    "round_number_ratio",
    "amount_variance",
    "has_dust_attack",
    "has_round_laundering",
]


class BitGuard:

    feature_columns = FEATURE_COLUMNS

    def __init__(self, model_path):
        self.model = self.load_model_light_gbm_pickle(model_path)

    def load_model_light_gbm_pickle(self, model_path):
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        return model

    def predict_from_features(self, features):
        X = pd.DataFrame(
            [[features[column] for column in self.feature_columns]],
            columns=self.feature_columns,
        )
        return int(self.predict_score(X)[0])

    def predict_score(self, X):
        return ((1 - self.model.predict_proba(X)[:, 1]) * 100).round().astype(int)
