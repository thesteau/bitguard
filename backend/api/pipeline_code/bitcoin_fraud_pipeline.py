import numpy as np
import pandas as pd


FEATURE_COLS = [
    'in_degree', 'out_degree', 'total_degree',
    'total_received_btc', 'total_sent_btc',
    'avg_received_btc', 'avg_sent_btc', 'balance',
    'equal_output_count', 'suspicious_blocks', 'max_equal_outputs', 'fan_in_out_ratio',
    'lifetime_blocks', 'tx_frequency',
    'dust_tx_count', 'dust_ratio', 'round_number_ratio', 'amount_variance',
    'has_dust_attack', 'has_round_laundering',
]


def build_features(bfn: pd.DataFrame) -> pd.DataFrame:

    rows = []

    for address, group in bfn.groupby('seed'):
        group = group.copy()

        # ── Basic features ────────────────────────────────────────────────────
        outgoing = group[group['source_id'] == address]
        incoming = group[group['target_id'] == address]

        out_degree = outgoing['target_id'].nunique()
        total_sent_btc = outgoing['btc_amount'].sum()
        in_degree = incoming['source_id'].nunique()
        total_received_btc = incoming['btc_amount'].sum()

        total_degree = in_degree + out_degree
        avg_received_btc = total_received_btc / in_degree if in_degree > 0 else 0
        avg_sent_btc = total_sent_btc / out_degree if out_degree > 0 else 0
        balance = total_received_btc - total_sent_btc

        # ── Temporal features ─────────────────────────────────────────────────
        lifetime_blocks = int(group['block_height'].max() - group['block_height'].min())
        num_blocks = len(group)
        tx_frequency = num_blocks / lifetime_blocks if lifetime_blocks > 0 else 0

        # ── CoinJoin features ─────────────────────────────────────────────────
        group['amount_fuzzy'] = (group['btc_amount'] * 100).round(0)
        duplicates = group.groupby(['block_height', 'amount_fuzzy']).size().reset_index(name='dup_count')
        suspicious = duplicates[duplicates['dup_count'] >= 5]

        equal_output_count = int(suspicious['dup_count'].sum()) if len(suspicious) > 0 else 0
        suspicious_blocks = int(suspicious['block_height'].nunique()) if len(suspicious) > 0 else 0
        max_equal_outputs = int(suspicious['dup_count'].max()) if len(suspicious) > 0 else 0
        fan_in_out_ratio = out_degree / in_degree if in_degree > 0 else float(out_degree)

        # ── Transaction value features ────────────────────────────────────────
        direct = group[(group['source_id'] == address) | (group['target_id'] == address)].copy()
        total_txs = len(direct)

        dust_tx_count = int((direct['btc_amount'] < 0.0001).sum())
        dust_ratio = dust_tx_count / total_txs if total_txs > 0 else 0
        has_dust_attack = int(dust_tx_count > 10)

        direct['amount_rounded'] = direct['btc_amount'].round(1)
        direct['is_round'] = direct['amount_rounded'].isin([0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]).astype(int)
        round_count = int(direct['is_round'].sum())
        round_number_ratio = round_count / total_txs if total_txs > 0 else 0
        has_round_laundering = int(round_number_ratio > 0.3)

        mean_amt = direct['btc_amount'].mean()
        var_amt = direct['btc_amount'].var()
        amount_variance = (var_amt / (mean_amt + 0.0001)) if not np.isnan(var_amt) else 0

        rows.append({
            'in_degree':             in_degree,
            'out_degree':            out_degree,
            'total_degree':          total_degree,
            'total_received_btc':    total_received_btc,
            'total_sent_btc':        total_sent_btc,
            'avg_received_btc':      avg_received_btc,
            'avg_sent_btc':          avg_sent_btc,
            'balance':               balance,
            'equal_output_count':    equal_output_count,
            'suspicious_blocks':     suspicious_blocks,
            'max_equal_outputs':     max_equal_outputs,
            'fan_in_out_ratio':      fan_in_out_ratio,
            'lifetime_blocks':       lifetime_blocks,
            'tx_frequency':          tx_frequency,
            'dust_tx_count':         dust_tx_count,
            'dust_ratio':            dust_ratio,
            'round_number_ratio':    round_number_ratio,
            'amount_variance':       amount_variance,
            'has_dust_attack':       has_dust_attack,
            'has_round_laundering':  has_round_laundering,
        })

    return pd.DataFrame(rows, columns=FEATURE_COLS)
