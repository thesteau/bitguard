#!/usr/bin/env python3

"""
Bitcoin wallet fraud detection pipeline.

What this script does:
1. Loads labeled wallet data and wallet-edge network data from CSV files
2. Engineers wallet-level features from direct transaction behavior
3. Trains a LightGBM classifier on those features
4. Evaluates the model on validation and test sets
5. Saves outputs for reporting and later analysis

Example usage:
    python bitcoin_fraud_pipeline.py \
        --addresses balanced_addresses.csv \
        --network bitcoin_fraud_network.csv \
        --outdir outputs

Optional plotting:
    python bitcoin_fraud_pipeline.py \
        --addresses balanced_addresses.csv \
        --network bitcoin_fraud_network.csv \
        --outdir outputs \
        --make-plots
"""

import argparse
import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split


# ---------------------------------------------------------------------
# Data loading and validation
# ---------------------------------------------------------------------

def load_csv_data(addresses_path: str, network_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load the labeled address table and the network edge table.
    Also drops any unnamed index columns that often appear in exported CSVs.
    """
    ba = pd.read_csv(addresses_path)
    bfn = pd.read_csv(network_path)

    # Drop notebook/export leftovers like "Unnamed: 0"
    ba = ba.loc[:, ~ba.columns.str.startswith("Unnamed")]
    bfn = bfn.loc[:, ~bfn.columns.str.startswith("Unnamed")]

    return ba, bfn


def validate_input_columns(ba: pd.DataFrame, bfn: pd.DataFrame) -> None:
    """
    Make sure the script fails early if the expected schema is not present.
    """
    required_ba_cols = {"address", "bad_actor", "category", "source"}
    required_bfn_cols = {"seed", "source_id", "target_id", "btc_amount", "block_height"}

    missing_ba = required_ba_cols - set(ba.columns)
    missing_bfn = required_bfn_cols - set(bfn.columns)

    if missing_ba:
        raise ValueError(f"balanced_addresses.csv is missing required columns: {sorted(missing_ba)}")

    if missing_bfn:
        raise ValueError(f"bitcoin_fraud_network.csv is missing required columns: {sorted(missing_bfn)}")


def print_dataset_summary(ba: pd.DataFrame, bfn: pd.DataFrame, bfn_labeled: pd.DataFrame) -> None:
    """
    Print a quick summary so we can verify the data looks reasonable.
    """
    print("=" * 70)
    print("DATA SUMMARY")
    print("=" * 70)
    print(f"Total labeled addresses: {len(ba):,}")
    print(f"Total network edges:      {len(bfn):,}")
    print(f"Unique seeds:             {bfn['seed'].nunique():,}")

    seed_summary = (
        bfn_labeled.groupby("seed")
        .agg(
            is_bad=("seed_is_bad", "first"),
            category=("seed_category", "first"),
            edge_count=("source_id", "count"),
        )
        .reset_index()
    )

    print("\nSeeds with data breakdown:")
    print(seed_summary["is_bad"].value_counts(dropna=False).sort_index())

    print("\nBad actor categories:")
    print(seed_summary[seed_summary["is_bad"] == 1]["category"].value_counts())

    good_count = (seed_summary["is_bad"] == 0).sum()
    print(f"\nGood actor count: {good_count:,}")

    bad_avg_edges = seed_summary.loc[seed_summary["is_bad"] == 1, "edge_count"].mean()
    good_avg_edges = seed_summary.loc[seed_summary["is_bad"] == 0, "edge_count"].mean()

    print(f"\nAverage edges per bad seed:  {bad_avg_edges:.0f}")
    print(f"Average edges per good seed: {good_avg_edges:.0f}")


# ---------------------------------------------------------------------
# Label merge
# ---------------------------------------------------------------------

def merge_seed_labels(bfn: pd.DataFrame, ba: pd.DataFrame) -> pd.DataFrame:
    """
    Join label metadata from the address table onto the network table using the seed address.
    """
    bfn_labeled = bfn.merge(
        ba[["address", "bad_actor", "category", "source"]],
        left_on="seed",
        right_on="address",
        how="left",
    )

    bfn_labeled = (
        bfn_labeled.rename(
            columns={
                "bad_actor": "seed_is_bad",
                "category": "seed_category",
                "source": "seed_source",
            }
        )
        .drop(columns=["address"])
    )

    return bfn_labeled


# ---------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------

def calculate_basic_features_vectorized(bfn_labeled: pd.DataFrame, ba: pd.DataFrame) -> pd.DataFrame:
    """
    Build basic wallet features from direct incoming and outgoing edges.

    These features describe:
    - how many unique counterparties a wallet sends to / receives from
    - how much BTC it sends / receives
    - average transaction behavior
    - simple net balance-style signal
    """
    # Rows where the seed wallet is the sender
    seed_as_source = bfn_labeled.loc[
        bfn_labeled["source_id"] == bfn_labeled["seed"],
        ["seed", "target_id", "btc_amount"],
    ].copy()

    # Rows where the seed wallet is the receiver
    seed_as_target = bfn_labeled.loc[
        bfn_labeled["target_id"] == bfn_labeled["seed"],
        ["seed", "source_id", "btc_amount"],
    ].copy()

    # Outgoing behavior
    outgoing = (
        seed_as_source.groupby("seed")
        .agg(
            out_degree=("target_id", "nunique"),
            total_sent_btc=("btc_amount", "sum"),
        )
        .reset_index()
    )

    # Incoming behavior
    incoming = (
        seed_as_target.groupby("seed")
        .agg(
            in_degree=("source_id", "nunique"),
            total_received_btc=("btc_amount", "sum"),
        )
        .reset_index()
    )

    # Start with one row per seed, then merge features in
    all_seeds = pd.DataFrame({"seed": bfn_labeled["seed"].unique()})

    features = all_seeds.merge(outgoing, on="seed", how="left")
    features = features.merge(incoming, on="seed", how="left").fillna(0)
    features = features.rename(columns={"seed": "address"})

    # Simple derived features
    features["total_degree"] = features["in_degree"] + features["out_degree"]
    features["avg_received_btc"] = (
        features["total_received_btc"] / features["in_degree"].replace(0, 1)
    )
    features["avg_sent_btc"] = (
        features["total_sent_btc"] / features["out_degree"].replace(0, 1)
    )
    features["balance"] = features["total_received_btc"] - features["total_sent_btc"]

    # Add labels back onto the feature table
    features = features.merge(
        ba[["address", "bad_actor", "category"]],
        on="address",
        how="left",
    ).rename(columns={"bad_actor": "is_bad_actor"})

    return features


def calculate_coinjoin_features_vectorized(
    bfn_labeled: pd.DataFrame,
    seeds: pd.Series,
    duplicate_threshold: int = 5,
) -> pd.DataFrame:
    """
    Build CoinJoin-style features by looking for repeated equal-ish outputs
    within the same block for the same seed.

    We use a fuzzy amount bucket instead of exact equality because exact floating
    point matches can be too brittle.
    """
    seed_set = set(seeds)
    seed_edges = bfn_labeled[bfn_labeled["seed"].isin(seed_set)].copy()

    # Round to 0.01 BTC buckets after multiplying by 100
    seed_edges["amount_fuzzy"] = (seed_edges["btc_amount"] * 100).round(0)

    duplicates = (
        seed_edges.groupby(["seed", "block_height", "amount_fuzzy"])
        .size()
        .reset_index(name="dup_count")
    )

    suspicious = duplicates[duplicates["dup_count"] >= duplicate_threshold]

    coinjoin_features = (
        suspicious.groupby("seed")
        .agg(
            equal_output_count=("dup_count", "sum"),
            suspicious_blocks=("block_height", "nunique"),
            max_equal_outputs=("dup_count", "max"),
        )
        .reset_index()
        .rename(columns={"seed": "address"})
    )

    # Make sure every seed gets a row, even if it has zero suspicious patterns
    all_seeds_df = pd.DataFrame({"address": list(seed_set)})
    result = all_seeds_df.merge(coinjoin_features, on="address", how="left").fillna(0)

    return result


def add_temporal_features(bfn_labeled: pd.DataFrame, features_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add block-based timing features for each wallet.

    These features try to capture:
    - how long a wallet is active
    - how densely its transactions appear over that lifetime
    """
    temporal = (
        bfn_labeled.groupby("seed")["block_height"]
        .agg(["min", "max", "count"])
        .reset_index()
    )

    temporal.columns = ["address", "first_block", "last_block", "num_blocks"]
    temporal["lifetime_blocks"] = temporal["last_block"] - temporal["first_block"]
    temporal["tx_frequency"] = temporal["num_blocks"] / temporal["lifetime_blocks"].replace(0, 1)

    return features_df.merge(
        temporal[["address", "lifetime_blocks", "tx_frequency"]],
        on="address",
        how="left",
    ).fillna(0)


def calculate_transaction_value_features_fast(
    bfn_labeled: pd.DataFrame,
    seeds: pd.Series,
) -> pd.DataFrame:
    """
    Build value-pattern features from transactions touching each seed.

    These include:
    - dust behavior
    - round-number behavior
    - amount variance
    """
    seed_set = set(seeds)
    seed_edges = bfn_labeled[bfn_labeled["seed"].isin(seed_set)].copy()

    # Keep only edges that directly involve the seed wallet
    seed_edges["is_seed_tx"] = (
        (seed_edges["source_id"] == seed_edges["seed"]) |
        (seed_edges["target_id"] == seed_edges["seed"])
    )
    seed_edges = seed_edges[seed_edges["is_seed_tx"]].copy()

    # Dust detection
    seed_edges["is_dust"] = (seed_edges["btc_amount"] < 0.0001).astype(int)
    dust_stats = (
        seed_edges.groupby("seed")
        .agg(
            dust_tx_count=("is_dust", "sum"),
            total_txs=("btc_amount", "count"),
        )
        .reset_index()
    )
    dust_stats["dust_ratio"] = dust_stats["dust_tx_count"] / dust_stats["total_txs"]
    dust_stats["has_dust_attack"] = (dust_stats["dust_tx_count"] > 10).astype(int)

    # Round-number detection
    seed_edges["amount_rounded"] = seed_edges["btc_amount"].round(1)
    round_values = [0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]
    seed_edges["is_round"] = seed_edges["amount_rounded"].isin(round_values).astype(int)

    round_stats = (
        seed_edges.groupby("seed")["is_round"]
        .agg(["sum", "count"])
        .reset_index()
    )
    round_stats.columns = ["seed", "round_count", "total_txs"]
    round_stats["round_number_ratio"] = round_stats["round_count"] / round_stats["total_txs"]
    round_stats["has_round_laundering"] = (round_stats["round_number_ratio"] > 0.3).astype(int)

    # Variance relative to mean transaction size
    variance_stats = (
        seed_edges.groupby("seed")["btc_amount"]
        .agg(["var", "mean"])
        .reset_index()
    )
    variance_stats["amount_variance"] = variance_stats["var"] / (variance_stats["mean"] + 0.0001)

    # Merge all value-based features together
    result = dust_stats[["seed", "dust_tx_count", "dust_ratio", "has_dust_attack"]]
    result = result.merge(
        round_stats[["seed", "round_number_ratio", "has_round_laundering"]],
        on="seed",
        how="left",
    )
    result = result.merge(
        variance_stats[["seed", "amount_variance"]],
        on="seed",
        how="left",
    )

    result = result.rename(columns={"seed": "address"}).fillna(0)

    # Make sure every seed gets a row
    all_seeds_df = pd.DataFrame({"address": list(seed_set)})
    result = all_seeds_df.merge(result, on="address", how="left").fillna(0)

    return result


def build_feature_table(
    bfn_labeled: pd.DataFrame,
    ba: pd.DataFrame,
    duplicate_threshold: int = 5,
) -> pd.DataFrame:
    """
    Run the full feature engineering pipeline and return one row per wallet.
    """
    print("\nBuilding feature table...")

    # Basic degree and flow features
    features_df = calculate_basic_features_vectorized(bfn_labeled, ba)

    # Temporal features
    features_df = add_temporal_features(bfn_labeled, features_df)

    # CoinJoin-style features
    coinjoin_df = calculate_coinjoin_features_vectorized(
        bfn_labeled,
        features_df["address"],
        duplicate_threshold=duplicate_threshold,
    )

    coinjoin_df["fan_in_out_ratio"] = (
        features_df["out_degree"].values /
        features_df["in_degree"].replace(0, 1).values
    )

    features_df = features_df.merge(
        coinjoin_df[
            [
                "address",
                "equal_output_count",
                "suspicious_blocks",
                "max_equal_outputs",
                "fan_in_out_ratio",
            ]
        ],
        on="address",
        how="left",
    ).fillna(0)

    # Transaction value features
    value_features = calculate_transaction_value_features_fast(
        bfn_labeled,
        features_df["address"],
    )

    features_df = features_df.merge(value_features, on="address", how="left").fillna(0)

    # Final cleanup: one row per address
    before = len(features_df)
    features_df = features_df.drop_duplicates(subset="address", keep="first").copy()
    after = len(features_df)

    print(f"Feature rows before dedup: {before:,}")
    print(f"Feature rows after dedup:  {after:,}")
    print(f"Duplicates removed:        {before - after:,}")

    return features_df


# ---------------------------------------------------------------------
# Modeling
# ---------------------------------------------------------------------

def get_feature_columns() -> list[str]:
    """
    Return the final list of model features.
    """
    return [
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


def prepare_model_data(features_df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """
    Keep only the columns needed for modeling and drop any incomplete rows.
    """
    model_df = features_df[feature_cols + ["is_bad_actor", "address"]].dropna().copy()

    # Make sure the target is numeric integer 0/1
    model_df["is_bad_actor"] = model_df["is_bad_actor"].astype(int)

    return model_df


def split_train_val_test(
    model_df: pd.DataFrame,
    random_state: int = 42,
    test_size: float = 0.2,
    val_size_within_trainval: float = 0.25,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split into 60/20/20:
    - 20% test
    - remaining 80% split into 60% train and 20% validation overall
    """
    train_val_df, test_df = train_test_split(
        model_df,
        test_size=test_size,
        random_state=random_state,
        stratify=model_df["is_bad_actor"],
    )

    train_df, val_df = train_test_split(
        train_val_df,
        test_size=val_size_within_trainval,
        random_state=random_state,
        stratify=train_val_df["is_bad_actor"],
    )

    return train_df, val_df, test_df


def train_lightgbm_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    random_state: int = 42,
) -> lgb.LGBMClassifier:
    """
    Train a LightGBM classifier with early stopping on the validation set.
    """
    model = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=1000,
        learning_rate=0.05,
        num_leaves=31,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=-1,
        verbosity=-1,
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        eval_metric="auc",
        callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)],
    )

    return model


def evaluate_classifier(
    model,
    X: pd.DataFrame,
    y: pd.Series,
    split_name: str,
) -> dict:
    """
    Evaluate the trained model on one split and return structured metrics.
    """
    y_pred = model.predict(X)
    y_prob = model.predict_proba(X)[:, 1]
    cm = confusion_matrix(y, y_pred)
    report = classification_report(
        y,
        y_pred,
        target_names=["Good", "Bad"],
        output_dict=True,
        zero_division=0,
    )

    metrics = {
        "split": split_name,
        "roc_auc": float(roc_auc_score(y, y_prob)),
        "average_precision": float(average_precision_score(y, y_prob)),
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
    }

    return metrics


def print_metrics(metrics: dict) -> None:
    """
    Print a readable version of the most important evaluation results.
    """
    report = metrics["classification_report"]
    cm = np.array(metrics["confusion_matrix"])

    print("\n" + "=" * 70)
    print(f"{metrics['split'].upper()} PERFORMANCE")
    print("=" * 70)
    print(f"ROC-AUC:           {metrics['roc_auc']:.4f}")
    print(f"Average Precision: {metrics['average_precision']:.4f}")
    print(f"Accuracy:          {report['accuracy']:.4f}")

    print("\nBad actor class:")
    print(f"  Precision: {report['Bad']['precision']:.4f}")
    print(f"  Recall:    {report['Bad']['recall']:.4f}")
    print(f"  F1-score:  {report['Bad']['f1-score']:.4f}")

    print("\nConfusion matrix:")
    print(cm)


def build_feature_importance_table(model, feature_cols: list[str]) -> pd.DataFrame:
    """
    Build a ranked feature importance table from the trained LightGBM model.
    """
    importances = model.booster_.feature_importance(importance_type="gain")
    total = importances.sum()

    # Normalize if possible so the table is easier to interpret
    if total > 0:
        importances = importances / total

    fi_df = pd.DataFrame(
        {
            "feature": feature_cols,
            "importance": importances,
        }
    ).sort_values("importance", ascending=False)

    return fi_df


# ---------------------------------------------------------------------
# Output saving
# ---------------------------------------------------------------------

def save_metrics_json(metrics: dict, output_path: Path) -> None:
    """
    Save structured metrics to JSON.
    """
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)


def save_predictions_csv(
    model,
    df_split: pd.DataFrame,
    feature_cols: list[str],
    output_path: Path,
) -> None:
    """
    Save address-level predictions and probabilities for a split.
    """
    X = df_split[feature_cols]
    y_true = df_split["is_bad_actor"].values
    y_pred = model.predict(X)
    y_prob = model.predict_proba(X)[:, 1]

    pred_df = pd.DataFrame(
        {
            "address": df_split["address"].values,
            "true_label": y_true,
            "predicted_label": y_pred,
            "predicted_probability_bad": y_prob,
        }
    )

    pred_df.to_csv(output_path, index=False)


def save_confusion_matrix_csv(metrics: dict, output_path: Path) -> None:
    """
    Save confusion matrix as a small CSV for reporting.
    """
    cm = np.array(metrics["confusion_matrix"])
    cm_df = pd.DataFrame(
        cm,
        index=["actual_good", "actual_bad"],
        columns=["pred_good", "pred_bad"],
    )
    cm_df.to_csv(output_path)


def save_run_artifacts(
    outdir: Path,
    features_df: pd.DataFrame,
    feature_importance_df: pd.DataFrame,
    val_metrics: dict,
    test_metrics: dict,
    model,
    test_df: pd.DataFrame,
    feature_cols: list[str],
) -> None:
    """
    Save all core outputs from the run.
    """
    outdir.mkdir(parents=True, exist_ok=True)

    features_df.to_csv(outdir / "features.csv", index=False)
    feature_importance_df.to_csv(outdir / "feature_importance.csv", index=False)

    save_metrics_json(val_metrics, outdir / "validation_metrics.json")
    save_metrics_json(test_metrics, outdir / "test_metrics.json")

    save_confusion_matrix_csv(test_metrics, outdir / "test_confusion_matrix.csv")
    save_predictions_csv(model, test_df, feature_cols, outdir / "test_predictions.csv")

    # Save a short plain-text summary too
    with (outdir / "run_summary.txt").open("w", encoding="utf-8") as f:
        f.write("LightGBM Bitcoin Fraud Detection Run Summary\n")
        f.write("=" * 50 + "\n")
        f.write(f"Validation ROC-AUC: {val_metrics['roc_auc']:.4f}\n")
        f.write(f"Validation AP:      {val_metrics['average_precision']:.4f}\n")
        f.write(f"Test ROC-AUC:       {test_metrics['roc_auc']:.4f}\n")
        f.write(f"Test AP:            {test_metrics['average_precision']:.4f}\n")
        f.write(f"Test Accuracy:      {test_metrics['classification_report']['accuracy']:.4f}\n")
        f.write("\nTop 10 features:\n")
        for _, row in feature_importance_df.head(10).iterrows():
            f.write(f"  - {row['feature']}: {row['importance']:.6f}\n")


# ---------------------------------------------------------------------
# Optional plotting
# ---------------------------------------------------------------------

def make_optional_plots(
    model,
    feature_importance_df: pd.DataFrame,
    test_metrics: dict,
    outdir: Path,
) -> None:
    """
    Optional plotting helper.

    This is not called unless --make-plots is passed.
    Imports live inside the function so the script can still run in
    environments where plotting libraries are not installed.
    """
    import matplotlib.pyplot as plt
    import seaborn as sns

    outdir.mkdir(parents=True, exist_ok=True)

    # Confusion matrix plot
    cm = np.array(test_metrics["confusion_matrix"])
    plt.figure(figsize=(5, 4))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        cbar=False,
        linewidths=1.5,
        linecolor="white",
        xticklabels=["Good", "Bad"],
        yticklabels=["Good", "Bad"],
    )
    plt.title("Test Set Confusion Matrix")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.tight_layout()
    plt.savefig(outdir / "test_confusion_matrix.png", dpi=200, bbox_inches="tight")
    plt.close()

    # Top feature importance plot
    top_fi = feature_importance_df.head(15).sort_values("importance")
    plt.figure(figsize=(8, 6))
    plt.barh(top_fi["feature"], top_fi["importance"])
    plt.xlabel("Normalized Gain Importance")
    plt.title("Top 15 LightGBM Feature Importances")
    plt.tight_layout()
    plt.savefig(outdir / "feature_importance.png", dpi=200, bbox_inches="tight")
    plt.close()


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Train a LightGBM model for Bitcoin wallet fraud detection."
    )

    parser.add_argument(
        "--addresses",
        type=str,
        required=True,
        help="Path to balanced_addresses.csv",
    )
    parser.add_argument(
        "--network",
        type=str,
        required=True,
        help="Path to bitcoin_fraud_network.csv",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default="outputs",
        help="Directory where outputs will be saved",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducible train/val/test splits",
    )
    parser.add_argument(
        "--coinjoin-threshold",
        type=int,
        default=5,
        help="Minimum duplicate count in the same block to flag suspicious equal-output behavior",
    )
    parser.add_argument(
        "--make-plots",
        action="store_true",
        help="If set, save confusion matrix and feature importance plots",
    )

    return parser.parse_args()


def main() -> None:
    """
    Run the full training pipeline.
    """
    args = parse_args()
    outdir = Path(args.outdir)

    # Load data
    ba, bfn = load_csv_data(args.addresses, args.network)
    validate_input_columns(ba, bfn)

    # Merge labels onto the network table
    bfn_labeled = merge_seed_labels(bfn, ba)

    # Print summary so we can sanity-check the run
    print_dataset_summary(ba, bfn, bfn_labeled)

    # Build wallet-level features
    features_df = build_feature_table(
        bfn_labeled=bfn_labeled,
        ba=ba,
        duplicate_threshold=args.coinjoin_threshold,
    )

    feature_cols = get_feature_columns()
    model_df = prepare_model_data(features_df, feature_cols)

    print("\n" + "=" * 70)
    print("MODEL DATA SUMMARY")
    print("=" * 70)
    print(f"Total samples: {len(model_df):,}")
    print(f"Bad actors:    {model_df['is_bad_actor'].sum():,}")
    print(f"Good actors:   {(model_df['is_bad_actor'] == 0).sum():,}")

    # Split data
    train_df, val_df, test_df = split_train_val_test(
        model_df,
        random_state=args.random_state,
    )

    print(f"\nTrain size: {len(train_df):,} ({len(train_df) / len(model_df):.1%})")
    print(f"Val size:   {len(val_df):,} ({len(val_df) / len(model_df):.1%})")
    print(f"Test size:  {len(test_df):,} ({len(test_df) / len(model_df):.1%})")

    X_train = train_df[feature_cols]
    y_train = train_df["is_bad_actor"]

    X_val = val_df[feature_cols]
    y_val = val_df["is_bad_actor"]

    X_test = test_df[feature_cols]
    y_test = test_df["is_bad_actor"]

    # Train LightGBM
    print("\nTraining LightGBM...")
    model = train_lightgbm_model(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        random_state=args.random_state,
    )

    best_iter = getattr(model, "best_iteration_", None)
    if best_iter is not None:
        print(f"Best iteration from early stopping: {best_iter}")

    # Evaluate
    val_metrics = evaluate_classifier(model, X_val, y_val, split_name="validation")
    test_metrics = evaluate_classifier(model, X_test, y_test, split_name="test")

    print_metrics(val_metrics)
    print_metrics(test_metrics)

    # Feature importance
    feature_importance_df = build_feature_importance_table(model, feature_cols)

    print("\n" + "=" * 70)
    print("TOP 10 LIGHTGBM FEATURES")
    print("=" * 70)
    print(feature_importance_df.head(10).to_string(index=False))

    # Save outputs
    save_run_artifacts(
        outdir=outdir,
        features_df=features_df,
        feature_importance_df=feature_importance_df,
        val_metrics=val_metrics,
        test_metrics=test_metrics,
        model=model,
        test_df=test_df,
        feature_cols=feature_cols,
    )

    # Optional plotting
    if args.make_plots:
        print("\nGenerating optional plots...")
        make_optional_plots(
            model=model,
            feature_importance_df=feature_importance_df,
            test_metrics=test_metrics,
            outdir=outdir,
        )

    print("\nDone.")
    print(f"Outputs saved to: {outdir.resolve()}")


if __name__ == "__main__":
    main()