"""
inference_features.py

Converts raw Neo4j edge output (Pandas DataFrame) into model-ready features (Pandas DataFrame).
Interface: Pandas DataFrame in -> Pandas DataFrame out (one row, 138 features).

Input DataFrame columns:
    seed, source_id, target_id, btc_amount, block_height,
    edge_min_hop, edge_max_hop, tx_direction

Output: Pandas DataFrame, one row, 138 columns matching model.pkl feature_cols exactly.
"""

import pandas as pd
import numpy as np
from collections import defaultdict, Counter

# ── CONFIG (must match aggregate_features.py) ─────────────────────────────────
DUST_THRESH   = 0.0001
ROUND_AMOUNTS = {0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0}
COINJOIN_MIN  = 5
ROUND_DPS     = 4
HOPS          = [0, 1, 2]

FEATURE_COLS = [
    'btc_volume_hop0_forward', 'btc_avg_hop0_forward', 'btc_max_hop0_forward',
    'degree_hop0_forward', 'unique_neighbors_hop0_forward', 'dust_count_hop0_forward',
    'dust_ratio_hop0_forward', 'round_count_hop0_forward', 'round_ratio_hop0_forward',
    'amount_variance_hop0_forward', 'coinjoin_tx_count_hop0_forward',
    'max_coinjoin_outputs_hop0_forward', 'coinjoin_ratio_hop0_forward',
    'btc_volume_hop0_reverse', 'btc_avg_hop0_reverse', 'btc_max_hop0_reverse',
    'degree_hop0_reverse', 'unique_neighbors_hop0_reverse', 'dust_count_hop0_reverse',
    'dust_ratio_hop0_reverse', 'round_count_hop0_reverse', 'round_ratio_hop0_reverse',
    'amount_variance_hop0_reverse', 'coinjoin_tx_count_hop0_reverse',
    'max_coinjoin_outputs_hop0_reverse', 'coinjoin_ratio_hop0_reverse',
    'block_range_hop0', 'tx_frequency_hop0',
    'btc_volume_hop1_forward', 'btc_avg_hop1_forward', 'btc_max_hop1_forward',
    'degree_hop1_forward', 'unique_neighbors_hop1_forward', 'dust_count_hop1_forward',
    'dust_ratio_hop1_forward', 'round_count_hop1_forward', 'round_ratio_hop1_forward',
    'amount_variance_hop1_forward', 'coinjoin_tx_count_hop1_forward',
    'max_coinjoin_outputs_hop1_forward', 'coinjoin_ratio_hop1_forward',
    'btc_volume_hop1_reverse', 'btc_avg_hop1_reverse', 'btc_max_hop1_reverse',
    'degree_hop1_reverse', 'unique_neighbors_hop1_reverse', 'dust_count_hop1_reverse',
    'dust_ratio_hop1_reverse', 'round_count_hop1_reverse', 'round_ratio_hop1_reverse',
    'amount_variance_hop1_reverse', 'coinjoin_tx_count_hop1_reverse',
    'max_coinjoin_outputs_hop1_reverse', 'coinjoin_ratio_hop1_reverse',
    'block_range_hop1', 'tx_frequency_hop1',
    'btc_volume_hop2_forward', 'btc_avg_hop2_forward', 'btc_max_hop2_forward',
    'degree_hop2_forward', 'unique_neighbors_hop2_forward', 'dust_count_hop2_forward',
    'dust_ratio_hop2_forward', 'round_count_hop2_forward', 'round_ratio_hop2_forward',
    'amount_variance_hop2_forward', 'coinjoin_tx_count_hop2_forward',
    'max_coinjoin_outputs_hop2_forward', 'coinjoin_ratio_hop2_forward',
    'btc_volume_hop2_reverse', 'btc_avg_hop2_reverse', 'btc_max_hop2_reverse',
    'degree_hop2_reverse', 'unique_neighbors_hop2_reverse', 'dust_count_hop2_reverse',
    'dust_ratio_hop2_reverse', 'round_count_hop2_reverse', 'round_ratio_hop2_reverse',
    'amount_variance_hop2_reverse', 'coinjoin_tx_count_hop2_reverse',
    'max_coinjoin_outputs_hop2_reverse', 'coinjoin_ratio_hop2_reverse',
    'block_range_hop2', 'tx_frequency_hop2',
    'total_btc_forward', 'total_btc_reverse', 'total_degree_forward',
    'total_degree_reverse', 'deep_flow_ratio', 'balance', 'fan_in_out_ratio',
    'has_dust_attack', 'has_round_laundering',
    'btc_volume_hop0_asymmetry', 'degree_hop0_asymmetry',
    'unique_neighbors_hop0_asymmetry', 'dust_count_hop0_asymmetry',
    'round_count_hop0_asymmetry', 'btc_volume_hop1_asymmetry',
    'degree_hop1_asymmetry', 'unique_neighbors_hop1_asymmetry',
    'dust_count_hop1_asymmetry', 'round_count_hop1_asymmetry',
    'btc_volume_hop2_asymmetry', 'degree_hop2_asymmetry',
    'unique_neighbors_hop2_asymmetry', 'dust_count_hop2_asymmetry',
    'round_count_hop2_asymmetry',
    'btc_volume_hop0_forward_log', 'btc_avg_hop0_forward_log',
    'btc_max_hop0_forward_log', 'amount_variance_hop0_forward_log',
    'btc_volume_hop0_reverse_log', 'btc_avg_hop0_reverse_log',
    'btc_max_hop0_reverse_log', 'amount_variance_hop0_reverse_log',
    'btc_volume_hop1_forward_log', 'btc_avg_hop1_forward_log',
    'btc_max_hop1_forward_log', 'amount_variance_hop1_forward_log',
    'btc_volume_hop1_reverse_log', 'btc_avg_hop1_reverse_log',
    'btc_max_hop1_reverse_log', 'amount_variance_hop1_reverse_log',
    'btc_volume_hop2_forward_log', 'btc_avg_hop2_forward_log',
    'btc_max_hop2_forward_log', 'amount_variance_hop2_forward_log',
    'btc_volume_hop2_reverse_log', 'btc_avg_hop2_reverse_log',
    'btc_max_hop2_reverse_log', 'amount_variance_hop2_reverse_log',
    'total_btc_forward_log', 'total_btc_reverse_log', 'balance_log',
    'btc_volume_hop0_asymmetry_log', 'btc_volume_hop1_asymmetry_log',
    'btc_volume_hop2_asymmetry_log',
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
    # ── Build accumulator ─────────────────────────────────────────────────────
    acc = {}
    for hop in HOPS:
        for d in ("forward", "reverse"):
            acc[(hop, d)] = {
                "amounts":       [],
                "blocks":        [],
                "neighbors":     set(),
                "block_amounts": defaultdict(list),
            }

    for _, row in df.iterrows():
        hop       = row["edge_min_hop"]
        direction = "forward" if row["tx_direction"] == "source_to_target" else "reverse"
        amount    = row["btc_amount"] if pd.notna(row["btc_amount"]) else 0.0
        block     = row["block_height"] if pd.notna(row["block_height"]) else 0
        neighbor  = row["target_id"] if direction == "forward" else row["source_id"]

        if pd.isna(hop) or int(hop) not in HOPS or pd.isna(neighbor):
            continue

        b = acc[(int(hop), direction)]
        b["amounts"].append(float(amount))
        b["blocks"].append(int(block))
        b["neighbors"].add(neighbor)
        b["block_amounts"][int(block)].append(round(float(amount), ROUND_DPS))

    # ── Compute base features ─────────────────────────────────────────────────
    r = {}

    for hop in HOPS:
        all_blocks = []
        for d in ("forward", "reverse"):
            k   = f"hop{hop}_{d}"
            bkt = acc[(hop, d)]
            amounts = bkt["amounts"]
            blocks  = bkt["blocks"]
            n       = len(amounts)

            r[f"btc_volume_{k}"]            = 0.0
            r[f"btc_avg_{k}"]              = 0.0
            r[f"btc_max_{k}"]              = 0.0
            r[f"degree_{k}"]               = 0
            r[f"unique_neighbors_{k}"]     = 0
            r[f"dust_count_{k}"]           = 0
            r[f"dust_ratio_{k}"]           = 0.0
            r[f"round_count_{k}"]          = 0
            r[f"round_ratio_{k}"]          = 0.0
            r[f"amount_variance_{k}"]      = 0.0
            r[f"coinjoin_tx_count_{k}"]    = 0
            r[f"max_coinjoin_outputs_{k}"] = 0
            r[f"coinjoin_ratio_{k}"]       = 0.0

            if n == 0:
                continue

            vol  = sum(amounts)
            mean = vol / n
            r[f"btc_volume_{k}"]       = vol
            r[f"btc_avg_{k}"]          = mean
            r[f"btc_max_{k}"]          = max(amounts)
            r[f"degree_{k}"]           = n
            r[f"unique_neighbors_{k}"] = len(bkt["neighbors"])

            dust = sum(1 for a in amounts if a < DUST_THRESH)
            r[f"dust_count_{k}"]  = dust
            r[f"dust_ratio_{k}"]  = dust / n

            rounds = sum(1 for a in amounts if round(a, 1) in ROUND_AMOUNTS)
            r[f"round_count_{k}"] = rounds
            r[f"round_ratio_{k}"] = rounds / n

            r[f"amount_variance_{k}"] = sum((a - mean) ** 2 for a in amounts) / n

            cj_tx = 0; cj_out = 0; cj_max = 0
            for blk_amts in bkt["block_amounts"].values():
                for amt, c in Counter(blk_amts).items():
                    if c >= COINJOIN_MIN:
                        cj_tx  += 1
                        cj_out += c
                        cj_max  = max(cj_max, c)
            r[f"coinjoin_tx_count_{k}"]    = cj_tx
            r[f"max_coinjoin_outputs_{k}"] = cj_max
            r[f"coinjoin_ratio_{k}"]       = cj_out / n

            all_blocks.extend(blocks)

        if all_blocks:
            mn, mx      = min(all_blocks), max(all_blocks)
            block_range = mx - mn
            r[f"block_range_hop{hop}"]  = block_range
            r[f"tx_frequency_hop{hop}"] = len(set(all_blocks)) / max(block_range, 1)
        else:
            r[f"block_range_hop{hop}"]  = 0
            r[f"tx_frequency_hop{hop}"] = 0.0

    # ── Rollups ───────────────────────────────────────────────────────────────
    fwd    = sum(r[f"btc_volume_hop{h}_forward"]  for h in HOPS)
    rev    = sum(r[f"btc_volume_hop{h}_reverse"]  for h in HOPS)
    h2     = r["btc_volume_hop2_forward"] + r["btc_volume_hop2_reverse"]
    td_fwd = sum(r[f"degree_hop{h}_forward"]      for h in HOPS)
    td_rev = sum(r[f"degree_hop{h}_reverse"]      for h in HOPS)
    total_dust  = sum(r[f"dust_count_hop{h}_forward"]  + r[f"dust_count_hop{h}_reverse"]  for h in HOPS)
    total_round = sum(r[f"round_count_hop{h}_forward"] + r[f"round_count_hop{h}_reverse"] for h in HOPS)
    total_edges = td_fwd + td_rev

    r["total_btc_forward"]    = fwd
    r["total_btc_reverse"]    = rev
    r["total_degree_forward"] = td_fwd
    r["total_degree_reverse"] = td_rev
    r["deep_flow_ratio"]      = h2 / (fwd + rev) if (fwd + rev) > 0 else 0.0
    r["balance"]              = rev - fwd
    r["fan_in_out_ratio"]     = td_fwd / max(td_rev, 1)
    r["has_dust_attack"]      = int(total_dust > 10)
    r["has_round_laundering"] = int((total_round / max(total_edges, 1)) > 0.3)

    # ── Asymmetry features ────────────────────────────────────────────────────
    for hop in HOPS:
        for metric in ['btc_volume', 'degree', 'unique_neighbors', 'dust_count', 'round_count']:
            fwd_val = r.get(f'{metric}_hop{hop}_forward', 0.0)
            rev_val = r.get(f'{metric}_hop{hop}_reverse', 0.0)
            r[f'{metric}_hop{hop}_asymmetry'] = (
                (fwd_val - rev_val) / (fwd_val + rev_val + 1e-8)
            )

    # ── Log transforms ────────────────────────────────────────────────────────
    log_targets = [
        'btc_volume_hop0_forward', 'btc_avg_hop0_forward', 'btc_max_hop0_forward', 'amount_variance_hop0_forward',
        'btc_volume_hop0_reverse', 'btc_avg_hop0_reverse', 'btc_max_hop0_reverse', 'amount_variance_hop0_reverse',
        'btc_volume_hop1_forward', 'btc_avg_hop1_forward', 'btc_max_hop1_forward', 'amount_variance_hop1_forward',
        'btc_volume_hop1_reverse', 'btc_avg_hop1_reverse', 'btc_max_hop1_reverse', 'amount_variance_hop1_reverse',
        'btc_volume_hop2_forward', 'btc_avg_hop2_forward', 'btc_max_hop2_forward', 'amount_variance_hop2_forward',
        'btc_volume_hop2_reverse', 'btc_avg_hop2_reverse', 'btc_max_hop2_reverse', 'amount_variance_hop2_reverse',
        'total_btc_forward', 'total_btc_reverse', 'balance',
        'btc_volume_hop0_asymmetry', 'btc_volume_hop1_asymmetry', 'btc_volume_hop2_asymmetry',
    ]
    for col in log_targets:
        r[f'{col}_log'] = float(np.log1p(max(r.get(col, 0.0), 0)))

    # ── Return as Pandas DataFrame with correct column order ──────────────────
    return pd.DataFrame([[r.get(col, 0.0) for col in FEATURE_COLS]], columns=FEATURE_COLS)
