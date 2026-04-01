"""
wallet_stats.py

Computes display statistics for a single seed address from raw Neo4j edge output.
All stats are scoped to the seed address itself (hop 0) except total_wallets
which counts all unique addresses in the neighborhood.

Input:  Pandas DataFrame with columns:
        seed, source_id, target_id, btc_amount, block_height,
        edge_min_hop, edge_max_hop, tx_direction

Output: Plain Python dict (JSON-serializable)
"""

import pandas as pd


def compute_wallet_stats(df: pd.DataFrame) -> dict:
    """
    Compute display statistics for the queried seed address.

    Args:
        df: Pandas DataFrame of raw Neo4j edge rows for a single seed address.

    Returns:
        dict with the following keys:
            btc_sent         - total BTC sent by the seed (hop0, source_to_target)
            btc_received     - total BTC received by the seed (hop0, target_to_source)
            total_txs        - total number of edges returned by the query
            total_wallets    - distinct count of all other addresses in the neighborhood
            first_active_block - earliest block height involving the seed (hop0)
            last_active_block  - latest block height involving the seed (hop0)
    """
    if df.empty:
        return {
            "btc_sent":           0.0,
            "btc_received":       0.0,
            "total_txs":          0,
            "total_wallets":      0,
            "first_active_block": None,
            "last_active_block":  None,
        }

    # ── Hop 0 only — seed's direct transactions ───────────────────────────────
    hop0 = df[df["edge_min_hop"] == 0]

    sent = hop0[hop0["tx_direction"] == "source_to_target"]["btc_amount"].sum()
    received = hop0[hop0["tx_direction"] == "target_to_source"]["btc_amount"].sum()

    hop0_blocks = hop0["block_height"].dropna()
    first_block = int(hop0_blocks.min()) if not hop0_blocks.empty else None
    last_block = int(hop0_blocks.max()) if not hop0_blocks.empty else None

    # ── All wallets in neighborhood (excluding seed) ───────────────────────────
    all_addresses = set(df["source_id"].dropna().tolist() + df["target_id"].dropna().tolist())
    seed = df["seed"].iloc[0] if "seed" in df.columns else None
    if seed:
        all_addresses.discard(seed)

    return {
        "btc_sent":  round(float(sent), 8),
        "btc_received": round(float(received), 8),
        "total_txs_analyzed": int(len(df)),
        "total_wallets_analyzed": int(len(all_addresses)),
        "first_active_block": first_block,
        "last_active_block":  last_block,
    }
