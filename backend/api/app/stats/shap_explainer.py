"""
shap_explainer.py

Returns top interpretable SHAP-based reasons for a model prediction.

Rules:
- Skip any feature where feature_value == 0.0
- No dynamic values injected into explanation text
- Simple static explanations, direction-aware
- Only CoinJoin, dust, round-number, and fan-in/out signals

USAGE:
    from shap_explainer import init_explainer, get_shap_explanations
    explainer = init_explainer(model)  # once at server startup
    reasons = get_shap_explanations(X, explainer, risk)
"""

import shap


FEATURE_DEFS = {

    # ── Binary flags ───────────────────────────────────────────────────────────
    "has_dust_attack": {
        "display_name": {
            "increases_risk": "Dust attack detected",
            "decreases_risk": "No dust attack detected"
        },
        "explanation": {
            "increases_risk": "This wallet shows signs of a dust attack — a technique where tiny Bitcoin amounts are sent to link addresses and de-anonymize the owner. This is a known blockchain surveillance tactic associated with illicit activity.",
            "decreases_risk": "No dust attack pattern was detected on this wallet, consistent with normal wallet behavior."
        }
    },
    "has_round_laundering": {
        "display_name": {
            "increases_risk": "Round-number transaction pattern detected",
            "decreases_risk": "No round-number laundering pattern detected"
        },
        "explanation": {
            "increases_risk": "This wallet shows a statistically unusual concentration of round-number BTC amounts (e.g. 0.1, 0.5, 1.0 BTC). Structured round-number payments are a known technique used to avoid automated detection thresholds.",
            "decreases_risk": "No unusual round-number transaction pattern was detected, consistent with organic transaction behavior."
        }
    },

    # ── CoinJoin ───────────────────────────────────────────────────────────────
    "coinjoin_ratio_hop0_forward": {
        "display_name": {
            "increases_risk": "CoinJoin activity detected in outgoing transactions",
            "decreases_risk": "Low CoinJoin activity in outgoing transactions"
        },
        "explanation": {
            "increases_risk": "A significant portion of this wallet's outgoing transactions use CoinJoin — a technique that mixes funds with other users to obscure where money is going. While used for legitimate privacy, high CoinJoin usage is also a common money laundering technique.",
            "decreases_risk": "A low proportion of outgoing transactions use CoinJoin mixing, consistent with a wallet that does not rely on transaction obfuscation."
        }
    },
    "coinjoin_ratio_hop0_reverse": {
        "display_name": {
            "increases_risk": "CoinJoin activity detected in incoming transactions",
            "decreases_risk": "Low CoinJoin activity in incoming transactions"
        },
        "explanation": {
            "increases_risk": "A significant portion of funds arriving at this wallet came through CoinJoin mixing, meaning the origin of those funds has been deliberately obscured before reaching this wallet.",
            "decreases_risk": "A low proportion of incoming funds arrived via CoinJoin mixing, suggesting funds came through normal, traceable channels."
        }
    },
    "coinjoin_ratio_hop1_forward": {
        "display_name": {
            "increases_risk": "Neighboring wallets use CoinJoin when sending",
            "decreases_risk": "Neighboring wallets use minimal CoinJoin when sending"
        },
        "explanation": {
            "increases_risk": "Wallets directly connected to this one use CoinJoin heavily for outgoing transactions, placing this wallet adjacent to significant transaction obfuscation activity.",
            "decreases_risk": "Connected wallets use CoinJoin minimally for outgoing transactions, indicating the surrounding network does not rely on mixing."
        }
    },
    "coinjoin_ratio_hop1_reverse": {
        "display_name": {
            "increases_risk": "Neighboring wallets receive CoinJoin-mixed funds",
            "decreases_risk": "Neighboring wallets receive minimal CoinJoin-mixed funds"
        },
        "explanation": {
            "increases_risk": "Wallets connected to this one receive a significant portion of their funds via CoinJoin, suggesting the surrounding network relies on transaction mixing.",
            "decreases_risk": "A low portion of funds received by neighboring wallets came through CoinJoin, indicating a low-mixing network environment."
        }
    },

    # ── Dust ───────────────────────────────────────────────────────────────────
    "dust_ratio_hop0_forward": {
        "display_name": {
            "increases_risk": "Dust transaction activity detected in outgoing transactions",
            "decreases_risk": "Low dust activity in outgoing transactions"
        },
        "explanation": {
            "increases_risk": "A significant portion of this wallet's outgoing transactions are dust — tiny Bitcoin amounts under 0.0001 BTC often used to track or probe other wallets. Sending dust at scale is associated with blockchain surveillance tactics.",
            "decreases_risk": "A low proportion of outgoing transactions are dust amounts, not indicative of suspicious behavior."
        }
    },
    "dust_ratio_hop0_reverse": {
        "display_name": {
            "increases_risk": "Dust transaction activity detected in incoming transactions",
            "decreases_risk": "Low dust activity in incoming transactions"
        },
        "explanation": {
            "increases_risk": "A significant portion of this wallet's incoming transactions are dust amounts, which can indicate this wallet has been targeted by a dust attack to trace its activity.",
            "decreases_risk": "A low proportion of incoming transactions are dust amounts, not indicative of a dust attack."
        }
    },
    "dust_ratio_hop1_forward": {
        "display_name": {
            "increases_risk": "Neighboring wallets send dust transactions",
            "decreases_risk": "Neighboring wallets send minimal dust transactions"
        },
        "explanation": {
            "increases_risk": "Wallets connected to this one send a high proportion of their transactions as dust, placing this wallet within a network exhibiting dust-sending behavior.",
            "decreases_risk": "Connected wallets send a low proportion of dust transactions, not exhibiting dust attack patterns."
        }
    },

    # ── Round number transactions ──────────────────────────────────────────────
    "round_ratio_hop0_forward": {
        "display_name": {
            "increases_risk": "Round-number amounts detected in outgoing transactions",
            "decreases_risk": "Low round-number activity in outgoing transactions"
        },
        "explanation": {
            "increases_risk": "A significant portion of outgoing transactions use round BTC amounts (e.g. 0.1, 0.5, 1.0 BTC). Structured round-number payments are sometimes used to avoid automated detection systems.",
            "decreases_risk": "A low proportion of outgoing transactions use round amounts, not a statistically unusual pattern."
        }
    },
    "round_ratio_hop0_reverse": {
        "display_name": {
            "increases_risk": "Round-number amounts detected in incoming transactions",
            "decreases_risk": "Low round-number activity in incoming transactions"
        },
        "explanation": {
            "increases_risk": "A significant portion of incoming transactions use round BTC amounts, consistent with structured or automated payment patterns.",
            "decreases_risk": "A low proportion of incoming transactions use round amounts, within normal range."
        }
    },

    # ── Fan-in/out ratio ───────────────────────────────────────────────────────
    "fan_in_out_ratio": {
        "display_name": {
            "increases_risk": "Unbalanced send-to-receive address ratio",
            "decreases_risk": "Balanced send-to-receive address ratio"
        },
        "explanation": {
            "increases_risk": "This wallet sends to significantly more unique addresses than it receives from — a hub-and-spoke pattern commonly seen in wallets used to distribute illicit funds to many recipients.",
            "decreases_risk": "This wallet shows a balanced send-to-receive address ratio, consistent with normal wallet usage."
        }
    },
}


def init_explainer(model) -> shap.TreeExplainer:
    """Initialize once at server startup and reuse."""
    return shap.TreeExplainer(model)


def get_shap_explanations(X, explainer: shap.TreeExplainer, risk: str, top_n: int = 2) -> list:
    """
    Compute SHAP values and return top N interpretable reasons.

    Args:
        X:         Pandas DataFrame, one row, 138 features from build_features()
        explainer: pre-initialized shap.TreeExplainer from init_explainer()
        risk:      "very_low", "low", "medium", "high", "very_high", "mixed_signal"
        top_n:     max reasons to return (default 2)
    """
    shap_values = explainer(X)

    vals = shap_values.values
    if vals.ndim == 3:
        vals = vals[0, :, 1]
    else:
        vals = vals[0]

    feature_names = list(X.columns)

    explainable_indices = [
        i for i, name in enumerate(feature_names)
        if name in FEATURE_DEFS
    ]

    total_abs = sum(abs(vals[i]) for i in explainable_indices)
    explainable_indices.sort(key=lambda i: abs(vals[i]), reverse=True)

    all_reasons = []
    for i in explainable_indices:
        name      = feature_names[i]
        shap_val  = float(vals[i])
        feat_val  = float(X.iloc[0][name])
        direction = "increases_risk" if shap_val > 0 else "decreases_risk"
        pct       = round(abs(shap_val) / total_abs * 100) if total_abs > 0 else 0

        # Skip any feature where the value is zero — nothing happened, nothing to show
        if feat_val == 0.0:
            continue

        defn        = FEATURE_DEFS[name]
        display_raw = defn["display_name"]
        display     = display_raw[direction] if isinstance(display_raw, dict) else display_raw

        all_reasons.append({
            "feature":          name,
            "display_name":     display,
            "shap_explanation": defn["explanation"][direction],
            "shap_value":       round(shap_val, 4),
            "direction":        direction,
            "feature_value":    round(feat_val, 6),
            "influence_pct":    pct,
        })

    # Remove zero-influence entries
    all_reasons = [r for r in all_reasons if r["influence_pct"] > 0]

    # Filter by direction matching risk tier
    if risk in ("very_low", "low"):
        filtered = [r for r in all_reasons if r["direction"] == "decreases_risk"]
    elif risk in ("high", "very_high"):
        filtered = [r for r in all_reasons if r["direction"] == "increases_risk"]
    else:
        filtered = all_reasons

    return filtered[:top_n]
