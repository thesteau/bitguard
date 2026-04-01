"""
shap_explainer.py

Returns top interpretable SHAP-based reasons for a model prediction.
Only features with human-readable explanations are surfaced.
Reasons are filtered to match the direction of the risk score.

IMPORTANT - Cache the explainer at server startup for fast inference:

    from shap_explainer import init_explainer, get_shap_explanations
    explainer = init_explainer(model)  # call once at startup

    # Then at inference time:
    reasons = get_shap_explanations(X, explainer, risk)

Input:  X         - Pandas DataFrame (one row, 138 features from build_features())
        explainer - shap.TreeExplainer (pre-initialized at startup)
        risk      - risk tier string from prob_to_risk()
Output: list of dicts with keys: feature, display_name, shap_value, direction,
                                  feature_value, influence_pct
"""

import numpy as np
import shap

# ── Whitelist of explainable features with simplified display names ───────────
EXPLAINABLE_FEATURES = {
    # Dust
    "dust_ratio_hop0_forward":           "High ratio of dust transactions sent",
    "dust_ratio_hop0_reverse":           "High ratio of dust transactions received",
    "dust_ratio_hop1_forward":           "Neighboring wallets send many dust transactions",
    "dust_ratio_hop1_reverse":           "Neighboring wallets receive many dust transactions",
    "dust_count_hop0_forward":           "Sends many dust transactions",
    "dust_count_hop0_reverse":           "Receives many dust transactions",
    "has_dust_attack":                   "Dust attack detected on this wallet",

    # Coinjoin
    "coinjoin_ratio_hop0_forward":       "High CoinJoin activity in outgoing transactions",
    "coinjoin_ratio_hop0_reverse":       "High CoinJoin activity in incoming transactions",
    "coinjoin_ratio_hop1_forward":       "Neighboring wallets use CoinJoin when sending",
    "coinjoin_ratio_hop1_reverse":       "Neighboring wallets use CoinJoin when receiving",
    "coinjoin_tx_count_hop0_forward":    "Many outgoing CoinJoin transactions",
    "coinjoin_tx_count_hop0_reverse":    "Many incoming CoinJoin transactions",
    "coinjoin_tx_count_hop1_forward":    "Neighboring wallets have many outgoing CoinJoin transactions",
    "coinjoin_tx_count_hop1_reverse":    "Neighboring wallets have many incoming CoinJoin transactions",
    "max_coinjoin_outputs_hop0_forward": "Large CoinJoin batches in outgoing transactions",
    "max_coinjoin_outputs_hop0_reverse": "Large CoinJoin batches in incoming transactions",
    "max_coinjoin_outputs_hop1_forward": "Neighboring wallets have large outgoing CoinJoin batches",
    "max_coinjoin_outputs_hop1_reverse": "Neighboring wallets have large incoming CoinJoin batches",

    # Round number laundering
    "round_ratio_hop0_forward":          "High rate of round-number amounts sent",
    "round_ratio_hop0_reverse":          "High rate of round-number amounts received",
    "round_ratio_hop1_forward":          "Neighboring wallets frequently send round-number amounts",
    "round_ratio_hop1_reverse":          "Neighboring wallets frequently receive round-number amounts",
    "has_round_laundering":              "Suspicious round-number transaction pattern detected",

    # Network structure
    "fan_in_out_ratio":                  "Sends to many more wallets than it receives from",
    "unique_neighbors_hop0_forward":     "Sends to many unique wallets",
    "unique_neighbors_hop0_reverse":     "Receives from many unique wallets",
    "unique_neighbors_hop1_forward":     "Connected to wallets that send to many unique addresses",
    "unique_neighbors_hop1_reverse":     "Connected to wallets that receive from many unique addresses",
    "deep_flow_ratio":                   "Most activity happens far from this wallet in the network",
    "degree_hop0_forward":               "High number of outgoing transactions",
    "degree_hop0_reverse":               "High number of incoming transactions",
    "degree_hop1_forward":               "Neighboring wallets have many outgoing transactions",
    "degree_hop1_reverse":               "Neighboring wallets have many incoming transactions",

    # Volume
    "btc_volume_hop0_forward":           "Large amount of Bitcoin sent",
    "btc_volume_hop0_reverse":           "Large amount of Bitcoin received",
    "btc_volume_hop1_forward":           "Neighboring wallets send large amounts of Bitcoin",
    "btc_volume_hop1_reverse":           "Neighboring wallets receive large amounts of Bitcoin",
    "balance":                           "Unusual Bitcoin balance pattern",
    "total_btc_forward":                 "Large total Bitcoin sent across network",
    "total_btc_reverse":                 "Large total Bitcoin received across network",

    # Asymmetry
    "btc_volume_hop0_asymmetry":         "Uneven Bitcoin send/receive amounts",
    "btc_volume_hop1_asymmetry":         "Neighboring wallets have uneven send/receive amounts",
    "degree_hop0_asymmetry":             "Uneven number of sends vs receives",
    "degree_hop1_asymmetry":             "Neighboring wallets have uneven sends vs receives",
}


def init_explainer(model) -> shap.TreeExplainer:
    """
    Initialize the SHAP TreeExplainer. Call once at server startup and reuse.

    Args:
        model: loaded LightGBM model from model.pkl

    Returns:
        shap.TreeExplainer instance
    """
    return shap.TreeExplainer(model)


def get_shap_explanations(X, explainer: shap.TreeExplainer, risk: str, top_n: int = 2) -> list:
    """
    Compute SHAP values and return top N interpretable reasons matching risk direction.

    Args:
        X:         Pandas DataFrame, one row, 138 features from build_features()
        explainer: pre-initialized shap.TreeExplainer from init_explainer()
        risk:      risk tier string ("very_low", "low", "medium", "high", "very_high")
        top_n:     number of top reasons to return (default 2)

    Returns:
        list of dicts, each with:
            feature:       raw feature name
            display_name:  simplified human-readable description
            shap_value:    raw SHAP value (positive = increases risk, negative = decreases risk)
            direction:     "increases_risk" or "decreases_risk"
            feature_value: the actual value of the feature for this address
            influence_pct: percentage of total explained influence for this feature
    """
    shap_values = explainer(X)

    # Handle both shap output shapes
    vals = shap_values.values
    if vals.ndim == 3:
        vals = vals[0, :, 1]  # class 1 (bad actor) SHAP values
    else:
        vals = vals[0]

    feature_names = list(X.columns)

    # ── Filter to explainable features only ───────────────────────────────────
    explainable_indices = [
        i for i, name in enumerate(feature_names)
        if name in EXPLAINABLE_FEATURES
    ]

    # Sort by absolute SHAP value descending
    explainable_indices.sort(key=lambda i: abs(vals[i]), reverse=True)

    # ── Build full list of explainable reasons ────────────────────────────────
    all_reasons = []
    for i in explainable_indices:
        name      = feature_names[i]
        shap_val  = float(vals[i])
        direction = "increases_risk" if shap_val > 0 else "decreases_risk"
        all_reasons.append({
            "feature":       name,
            "display_name":  EXPLAINABLE_FEATURES[name],
            "shap_value":    round(shap_val, 4),
            "direction":     direction,
            "feature_value": round(float(X.iloc[0][name]), 6),
        })

    # ── Filter by direction matching risk tier ────────────────────────────────
    if risk in ("very_low", "low"):
        filtered = [r for r in all_reasons if r["direction"] == "decreases_risk"]
    elif risk in ("high", "very_high"):
        filtered = [r for r in all_reasons if r["direction"] == "increases_risk"]
    else:
        # medium - show highest absolute value regardless of direction
        filtered = all_reasons

    top = filtered[:top_n]

    # ── Compute influence_pct relative to all explainable SHAP values ─────────
    total_abs = sum(abs(r["shap_value"]) for r in all_reasons)
    if total_abs > 0:
        for r in top:
            r["influence_pct"] = int(round(abs(r["shap_value"]) / total_abs * 100, 0))
    else:
        for r in top:
            r["influence_pct"] = 0

    return top
