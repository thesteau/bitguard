"""
inference_features.py

Converts raw Neo4j edge output (Pandas DataFrame) into model-ready features (Pandas DataFrame).
Interface: Pandas DataFrame in -> Pandas DataFrame out (one row, 138 features).

Input DataFrame columns:
    seed, source_id, target_id, btc_amount, block_height,
    edge_min_hop, edge_max_hop, tx_direction

Output: Pandas DataFrame, one row, 138 columns matching model.pkl feature_cols exactly.
"""

from collections import Counter, defaultdict

import numpy as np
import pandas as pd

# Config must stay aligned with the training-side aggregate feature generation.
DUST_THRESH = 0.0001
ROUND_AMOUNTS = {0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0}
COINJOIN_MIN = 5
ROUND_DPS = 4
HOPS = [0, 1, 2]

FEATURE_COLS = [
    "btc_volume_hop0_forward",
    "btc_avg_hop0_forward",
    "btc_max_hop0_forward",
    "degree_hop0_forward",
    "unique_neighbors_hop0_forward",
    "dust_count_hop0_forward",
    "dust_ratio_hop0_forward",
    "round_count_hop0_forward",
    "round_ratio_hop0_forward",
    "amount_variance_hop0_forward",
    "coinjoin_tx_count_hop0_forward",
    "max_coinjoin_outputs_hop0_forward",
    "coinjoin_ratio_hop0_forward",
    "btc_volume_hop0_reverse",
    "btc_avg_hop0_reverse",
    "btc_max_hop0_reverse",
    "degree_hop0_reverse",
    "unique_neighbors_hop0_reverse",
    "dust_count_hop0_reverse",
    "dust_ratio_hop0_reverse",
    "round_count_hop0_reverse",
    "round_ratio_hop0_reverse",
    "amount_variance_hop0_reverse",
    "coinjoin_tx_count_hop0_reverse",
    "max_coinjoin_outputs_hop0_reverse",
    "coinjoin_ratio_hop0_reverse",
    "block_range_hop0",
    "tx_frequency_hop0",
    "btc_volume_hop1_forward",
    "btc_avg_hop1_forward",
    "btc_max_hop1_forward",
    "degree_hop1_forward",
    "unique_neighbors_hop1_forward",
    "dust_count_hop1_forward",
    "dust_ratio_hop1_forward",
    "round_count_hop1_forward",
    "round_ratio_hop1_forward",
    "amount_variance_hop1_forward",
    "coinjoin_tx_count_hop1_forward",
    "max_coinjoin_outputs_hop1_forward",
    "coinjoin_ratio_hop1_forward",
    "btc_volume_hop1_reverse",
    "btc_avg_hop1_reverse",
    "btc_max_hop1_reverse",
    "degree_hop1_reverse",
    "unique_neighbors_hop1_reverse",
    "dust_count_hop1_reverse",
    "dust_ratio_hop1_reverse",
    "round_count_hop1_reverse",
    "round_ratio_hop1_reverse",
    "amount_variance_hop1_reverse",
    "coinjoin_tx_count_hop1_reverse",
    "max_coinjoin_outputs_hop1_reverse",
    "coinjoin_ratio_hop1_reverse",
    "block_range_hop1",
    "tx_frequency_hop1",
    "btc_volume_hop2_forward",
    "btc_avg_hop2_forward",
    "btc_max_hop2_forward",
    "degree_hop2_forward",
    "unique_neighbors_hop2_forward",
    "dust_count_hop2_forward",
    "dust_ratio_hop2_forward",
    "round_count_hop2_forward",
    "round_ratio_hop2_forward",
    "amount_variance_hop2_forward",
    "coinjoin_tx_count_hop2_forward",
    "max_coinjoin_outputs_hop2_forward",
    "coinjoin_ratio_hop2_forward",
    "btc_volume_hop2_reverse",
    "btc_avg_hop2_reverse",
    "btc_max_hop2_reverse",
    "degree_hop2_reverse",
    "unique_neighbors_hop2_reverse",
    "dust_count_hop2_reverse",
    "dust_ratio_hop2_reverse",
    "round_count_hop2_reverse",
    "round_ratio_hop2_reverse",
    "amount_variance_hop2_reverse",
    "coinjoin_tx_count_hop2_reverse",
    "max_coinjoin_outputs_hop2_reverse",
    "coinjoin_ratio_hop2_reverse",
    "block_range_hop2",
    "tx_frequency_hop2",
    "total_btc_forward",
    "total_btc_reverse",
    "total_degree_forward",
    "total_degree_reverse",
    "deep_flow_ratio",
    "balance",
    "fan_in_out_ratio",
    "has_dust_attack",
    "has_round_laundering",
    "btc_volume_hop0_asymmetry",
    "degree_hop0_asymmetry",
    "unique_neighbors_hop0_asymmetry",
    "dust_count_hop0_asymmetry",
    "round_count_hop0_asymmetry",
    "btc_volume_hop1_asymmetry",
    "degree_hop1_asymmetry",
    "unique_neighbors_hop1_asymmetry",
    "dust_count_hop1_asymmetry",
    "round_count_hop1_asymmetry",
    "btc_volume_hop2_asymmetry",
    "degree_hop2_asymmetry",
    "unique_neighbors_hop2_asymmetry",
    "dust_count_hop2_asymmetry",
    "round_count_hop2_asymmetry",
    "btc_volume_hop0_forward_log",
    "btc_avg_hop0_forward_log",
    "btc_max_hop0_forward_log",
    "amount_variance_hop0_forward_log",
    "btc_volume_hop0_reverse_log",
    "btc_avg_hop0_reverse_log",
    "btc_max_hop0_reverse_log",
    "amount_variance_hop0_reverse_log",
    "btc_volume_hop1_forward_log",
    "btc_avg_hop1_forward_log",
    "btc_max_hop1_forward_log",
    "amount_variance_hop1_forward_log",
    "btc_volume_hop1_reverse_log",
    "btc_avg_hop1_reverse_log",
    "btc_max_hop1_reverse_log",
    "amount_variance_hop1_reverse_log",
    "btc_volume_hop2_forward_log",
    "btc_avg_hop2_forward_log",
    "btc_max_hop2_forward_log",
    "amount_variance_hop2_forward_log",
    "btc_volume_hop2_reverse_log",
    "btc_avg_hop2_reverse_log",
    "btc_max_hop2_reverse_log",
    "amount_variance_hop2_reverse_log",
    "total_btc_forward_log",
    "total_btc_reverse_log",
    "balance_log",
    "btc_volume_hop0_asymmetry_log",
    "btc_volume_hop1_asymmetry_log",
    "btc_volume_hop2_asymmetry_log",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert raw Neo4j edge DataFrame to model-ready feature DataFrame.

    Args:
        df: Pandas DataFrame with columns:
            seed, source_id, target_id, btc_amount, block_height,
            edge_min_hop, edge_max_hop, tx_direction

    Returns:
        Pandas DataFrame with one row and 138 feature columns matching model.pkl
    """
    acc = {}
    for hop in HOPS:
        for direction in ("forward", "reverse"):
            acc[(hop, direction)] = {
                "amounts": [],
                "blocks": [],
                "neighbors": set(),
                "block_amounts": defaultdict(list),
            }

    for _, row in df.iterrows():
        hop = row["edge_min_hop"]
        direction = "forward" if row["tx_direction"] == "source_to_target" else "reverse"
        amount = row["btc_amount"] if pd.notna(row["btc_amount"]) else 0.0
        block = row["block_height"] if pd.notna(row["block_height"]) else 0
        neighbor = row["target_id"] if direction == "forward" else row["source_id"]

        if pd.isna(hop) or int(hop) not in HOPS or pd.isna(neighbor):
            continue

        bucket = acc[(int(hop), direction)]
        bucket["amounts"].append(float(amount))
        bucket["blocks"].append(int(block))
        bucket["neighbors"].add(neighbor)
        bucket["block_amounts"][int(block)].append(round(float(amount), ROUND_DPS))

    r = {}

    for hop in HOPS:
        all_blocks = []
        for direction in ("forward", "reverse"):
            key = f"hop{hop}_{direction}"
            bucket = acc[(hop, direction)]
            amounts = bucket["amounts"]
            blocks = bucket["blocks"]
            count = len(amounts)

            r[f"btc_volume_{key}"] = 0.0
            r[f"btc_avg_{key}"] = 0.0
            r[f"btc_max_{key}"] = 0.0
            r[f"degree_{key}"] = 0
            r[f"unique_neighbors_{key}"] = 0
            r[f"dust_count_{key}"] = 0
            r[f"dust_ratio_{key}"] = 0.0
            r[f"round_count_{key}"] = 0
            r[f"round_ratio_{key}"] = 0.0
            r[f"amount_variance_{key}"] = 0.0
            r[f"coinjoin_tx_count_{key}"] = 0
            r[f"max_coinjoin_outputs_{key}"] = 0
            r[f"coinjoin_ratio_{key}"] = 0.0

            if count == 0:
                continue

            volume = sum(amounts)
            mean = volume / count
            r[f"btc_volume_{key}"] = volume
            r[f"btc_avg_{key}"] = mean
            r[f"btc_max_{key}"] = max(amounts)
            r[f"degree_{key}"] = count
            r[f"unique_neighbors_{key}"] = len(bucket["neighbors"])

            dust = sum(1 for value in amounts if value < DUST_THRESH)
            r[f"dust_count_{key}"] = dust
            r[f"dust_ratio_{key}"] = dust / count

            rounds = sum(1 for value in amounts if round(value, 1) in ROUND_AMOUNTS)
            r[f"round_count_{key}"] = rounds
            r[f"round_ratio_{key}"] = rounds / count

            r[f"amount_variance_{key}"] = sum((value - mean) ** 2 for value in amounts) / count

            coinjoin_transactions = 0
            coinjoin_outputs = 0
            max_coinjoin_outputs = 0
            for block_amounts in bucket["block_amounts"].values():
                for _, occurrences in Counter(block_amounts).items():
                    if occurrences >= COINJOIN_MIN:
                        coinjoin_transactions += 1
                        coinjoin_outputs += occurrences
                        max_coinjoin_outputs = max(max_coinjoin_outputs, occurrences)
            r[f"coinjoin_tx_count_{key}"] = coinjoin_transactions
            r[f"max_coinjoin_outputs_{key}"] = max_coinjoin_outputs
            r[f"coinjoin_ratio_{key}"] = coinjoin_outputs / count

            all_blocks.extend(blocks)

        if all_blocks:
            min_block, max_block = min(all_blocks), max(all_blocks)
            block_range = max_block - min_block
            r[f"block_range_hop{hop}"] = block_range
            r[f"tx_frequency_hop{hop}"] = len(set(all_blocks)) / max(block_range, 1)
        else:
            r[f"block_range_hop{hop}"] = 0
            r[f"tx_frequency_hop{hop}"] = 0.0

    total_forward_volume = sum(r[f"btc_volume_hop{hop}_forward"] for hop in HOPS)
    total_reverse_volume = sum(r[f"btc_volume_hop{hop}_reverse"] for hop in HOPS)
    hop2_total_volume = r["btc_volume_hop2_forward"] + r["btc_volume_hop2_reverse"]
    total_forward_degree = sum(r[f"degree_hop{hop}_forward"] for hop in HOPS)
    total_reverse_degree = sum(r[f"degree_hop{hop}_reverse"] for hop in HOPS)
    total_dust = sum(r[f"dust_count_hop{hop}_forward"] + r[f"dust_count_hop{hop}_reverse"] for hop in HOPS)
    total_round = sum(r[f"round_count_hop{hop}_forward"] + r[f"round_count_hop{hop}_reverse"] for hop in HOPS)
    total_edges = total_forward_degree + total_reverse_degree

    r["total_btc_forward"] = total_forward_volume
    r["total_btc_reverse"] = total_reverse_volume
    r["total_degree_forward"] = total_forward_degree
    r["total_degree_reverse"] = total_reverse_degree
    r["deep_flow_ratio"] = hop2_total_volume / \
        (total_forward_volume + total_reverse_volume) if (total_forward_volume + total_reverse_volume) > 0 else 0.0
    r["balance"] = total_reverse_volume - total_forward_volume
    r["fan_in_out_ratio"] = total_forward_degree / max(total_reverse_degree, 1)
    r["has_dust_attack"] = int(total_dust > 10)
    r["has_round_laundering"] = int((total_round / max(total_edges, 1)) > 0.3)

    for hop in HOPS:
        for metric in ["btc_volume", "degree", "unique_neighbors", "dust_count", "round_count"]:
            forward_value = r.get(f"{metric}_hop{hop}_forward", 0.0)
            reverse_value = r.get(f"{metric}_hop{hop}_reverse", 0.0)
            r[f"{metric}_hop{hop}_asymmetry"] = (forward_value - reverse_value) / (forward_value + reverse_value + 1e-8)

    log_targets = [
        "btc_volume_hop0_forward",
        "btc_avg_hop0_forward",
        "btc_max_hop0_forward",
        "amount_variance_hop0_forward",
        "btc_volume_hop0_reverse",
        "btc_avg_hop0_reverse",
        "btc_max_hop0_reverse",
        "amount_variance_hop0_reverse",
        "btc_volume_hop1_forward",
        "btc_avg_hop1_forward",
        "btc_max_hop1_forward",
        "amount_variance_hop1_forward",
        "btc_volume_hop1_reverse",
        "btc_avg_hop1_reverse",
        "btc_max_hop1_reverse",
        "amount_variance_hop1_reverse",
        "btc_volume_hop2_forward",
        "btc_avg_hop2_forward",
        "btc_max_hop2_forward",
        "amount_variance_hop2_forward",
        "btc_volume_hop2_reverse",
        "btc_avg_hop2_reverse",
        "btc_max_hop2_reverse",
        "amount_variance_hop2_reverse",
        "total_btc_forward",
        "total_btc_reverse",
        "balance",
        "btc_volume_hop0_asymmetry",
        "btc_volume_hop1_asymmetry",
        "btc_volume_hop2_asymmetry",
    ]
    for col in log_targets:
        r[f"{col}_log"] = float(np.log1p(max(r.get(col, 0.0), 0)))

    return pd.DataFrame([[r.get(col, 0.0) for col in FEATURE_COLS]], columns=FEATURE_COLS)
