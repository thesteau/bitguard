import os, json, datetime
from pathlib import Path
import requests
import pyarrow as pa
import pyarrow.parquet as pq

RPC_URL = os.environ["BTC_RPC_URL"]
WORKDIR = Path(os.environ.get("WORKDIR", "/work"))
BLOCKS_PER_FLUSH = int(os.environ.get("BLOCKS_PER_FLUSH", "500"))
START_HEIGHT = int(os.environ.get("START_HEIGHT", "0"))

OUT_BLOCKS = WORKDIR / "parquet" / "blocks"
OUT_TX = WORKDIR / "parquet" / "transactions"
OUT_BLOCKS.mkdir(parents=True, exist_ok=True)
OUT_TX.mkdir(parents=True, exist_ok=True)

CKPT = WORKDIR / "checkpoint.json"

def rpc(method, params=None):
    if params is None:
        params = []
    payload = {"jsonrpc": "1.0", "id": "x", "method": method, "params": params}
    r = requests.post(RPC_URL, json=payload, timeout=300)
    r.raise_for_status()
    j = r.json()
    if j.get("error"):
        raise RuntimeError(j["error"])
    return j["result"]

def load_next_height():
    if CKPT.exists():
        return int(json.loads(CKPT.read_text()).get("next_height", START_HEIGHT))
    return START_HEIGHT

def save_next_height(h):
    CKPT.write_text(json.dumps({"next_height": h}, indent=2))

def year_month_from_epoch(epoch_seconds: int):
    dt = datetime.datetime.utcfromtimestamp(epoch_seconds)
    return dt.year, dt.month

def block_row(block):
    return {
        "hash": block.get("hash"),
        "height": block.get("height"),
        "time": block.get("time"),
        "mediantime": block.get("mediantime"),
        "version": block.get("version"),
        "versionHex": block.get("versionHex"),
        "merkleroot": block.get("merkleroot"),
        "bits": block.get("bits"),
        "nonce": block.get("nonce"),
        "difficulty": block.get("difficulty"),
        "chainwork": block.get("chainwork"),
        "nTx": block.get("nTx"),
        "size": block.get("size"),
        "strippedsize": block.get("strippedsize"),
        "weight": block.get("weight"),
        "previousblockhash": block.get("previousblockhash"),
        "nextblockhash": block.get("nextblockhash"),
    }

def tx_row(tx, block_meta):
    return {
        "txid": tx.get("txid"),
        "hash": tx.get("hash"),
        "version": tx.get("version"),
        "size": tx.get("size"),
        "vsize": tx.get("vsize"),
        "weight": tx.get("weight"),
        "locktime": tx.get("locktime"),
        "block_hash": block_meta.get("hash"),
        "block_height": block_meta.get("height"),
        "block_time": block_meta.get("time"),
        "vin_json": json.dumps(tx.get("vin", []), separators=(",", ":")),
        "vout_json": json.dumps(tx.get("vout", []), separators=(",", ":")),
    }

tip = rpc("getblockchaininfo")["blocks"]
h = load_next_height()

print(f"Chain tip: {tip}")
print(f"Starting/resuming at height: {h}")
print(f"Partitioning by year/month under: {WORKDIR / 'parquet'}")
print(f"Flush every ~{BLOCKS_PER_FLUSH} blocks\n")

while h <= tip:
    end = min(h + BLOCKS_PER_FLUSH - 1, tip)

    blocks_rows = []
    tx_rows = []

    for height in range(h, end + 1):
        bh = rpc("getblockhash", [height])
        block = rpc("getblock", [bh, 2])

        yr, mo = year_month_from_epoch(block["time"])

        b = block_row(block)
        b["year"] = yr
        b["month"] = mo
        blocks_rows.append(b)

        for tx in block.get("tx", []):
            t = tx_row(tx, block)
            t["year"] = yr
            t["month"] = mo
            tx_rows.append(t)

    pq.write_to_dataset(
        pa.Table.from_pylist(blocks_rows),
        root_path=str(OUT_BLOCKS),
        partition_cols=["year", "month"],
        existing_data_behavior="overwrite_or_ignore",
    )

    pq.write_to_dataset(
        pa.Table.from_pylist(tx_rows),
        root_path=str(OUT_TX),
        partition_cols=["year", "month"],
        existing_data_behavior="overwrite_or_ignore",
    )

    save_next_height(end + 1)
    print(f"Wrote heights {h}..{end} (next={end+1})")
    h = end + 1

print("\nDone.")
