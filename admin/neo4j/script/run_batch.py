"""
run_batch.py

Edit the variables under CONFIG, then:
    pip install neo4j pandas tqdm
    python run_batch.py
"""

import csv
import os
import time
import pandas as pd
from neo4j import GraphDatabase
from tqdm import tqdm

# ── CONFIG ────────────────────────────────────────────────────────────────────
URI        = "neo4j://localhost:7687"
USER       = "neo4j"
PASSWORD   = "your_password"
CSV_IN     = "combined.csv"
CSV_OUT    = "neighborhood_results.csv"

DEG_CAP    = 1000   # skip any node with more connections than this
NODE_LIMIT = 5000   # max neighborhood size
# ─────────────────────────────────────────────────────────────────────────────

QUERY = """
WITH $seed AS seed, $DEG_CAP AS DEG_CAP, $NODE_LIMIT AS NODE_LIMIT

// --- Bail early if the seed itself is a supernode ---
MATCH (s:Script {Address: seed})
WHERE COUNT { (s)-[:Transfers]-() } < DEG_CAP

// --- Hop 1: only non-supernodes ---
MATCH (s)-[:Transfers]-(h1:Script)
WHERE COUNT { (h1)-[:Transfers]-() } < DEG_CAP
WITH s, collect(DISTINCT h1)[..NODE_LIMIT] AS hop1_nodes, DEG_CAP, NODE_LIMIT

// --- Hop 2: expand each hop-1 node, filter supernodes immediately ---
UNWIND hop1_nodes AS n1
MATCH (n1)-[:Transfers]-(h2:Script)
WHERE COUNT { (h2)-[:Transfers]-() } < DEG_CAP
  AND h2 <> s
  AND NOT h2 IN hop1_nodes
WITH s, hop1_nodes, collect(DISTINCT h2)[..NODE_LIMIT] AS hop2_nodes, NODE_LIMIT

// --- Build final neighborhood (seed + hop1 + hop2, capped) ---
WITH s, hop1_nodes, hop2_nodes,
     apoc.coll.toSet([s] + hop1_nodes + hop2_nodes)[..NODE_LIMIT] AS neighborhood

// --- Hop lookup for edge annotation ---
WITH s, neighborhood,
     [{addr: s.Address, hop: 0}] +
     [n IN hop1_nodes WHERE n IN neighborhood | {addr: n.Address, hop: 1}] +
     [n IN hop2_nodes WHERE n IN neighborhood | {addr: n.Address, hop: 2}] AS hop_lookup

// --- Collect all edges within the neighborhood ---
UNWIND neighborhood AS a
MATCH (a)-[r:Transfers]-(b:Script)
WHERE b IN neighborhood
  AND a.Address < b.Address

WITH
  s.Address AS seed,
  a.Address AS source_id,
  b.Address AS target_id,
  r.Value   AS btc_amount,
  r.Height  AS block_height,
  head([x IN hop_lookup WHERE x.addr = a.Address | x.hop]) AS source_hop,
  head([x IN hop_lookup WHERE x.addr = b.Address | x.hop]) AS target_hop,
  CASE
    WHEN startNode(r) = a AND endNode(r) = b THEN 'source_to_target'
    WHEN startNode(r) = b AND endNode(r) = a THEN 'target_to_source'
    ELSE 'unknown'
  END AS tx_direction

RETURN
  seed, source_id, target_id, btc_amount, block_height,
  source_hop, target_hop,
  CASE WHEN source_hop <= target_hop THEN source_hop ELSE target_hop END AS edge_min_hop,
  CASE WHEN source_hop >= target_hop THEN source_hop ELSE target_hop END AS edge_max_hop,
  tx_direction
LIMIT 20000
"""

FIELDNAMES = [
    "seed", "bad_actor", "source_id", "target_id", "btc_amount",
    "block_height", "source_hop", "target_hop",
    "edge_min_hop", "edge_max_hop", "tx_direction"
]

def load_seeds(path):
    df = pd.read_csv(path)
    return df[["address", "bad_actor"]].drop_duplicates("address").values.tolist()

def load_done(path):
    if not os.path.exists(path):
        return set()
    df = pd.read_csv(path, usecols=["seed"])
    return set(df["seed"].unique())

def make_driver():
    return GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def main():
    seeds = load_seeds(CSV_IN)
    print(f"Total seeds:  {len(seeds):,}")

    done = load_done(CSV_OUT)
    remaining = [(addr, label) for addr, label in seeds if addr not in done]
    print(f"Already done: {len(done):,}")
    print(f"Remaining:    {len(remaining):,}\n")

    write_header = not os.path.exists(CSV_OUT)
    out = open(CSV_OUT, "a", newline="")
    writer = csv.DictWriter(out, fieldnames=FIELDNAMES)
    if write_header:
        writer.writeheader()

    driver = make_driver()
    times = []

    try:
        with driver.session() as session:
            for i, (address, bad_actor) in enumerate(tqdm(remaining, unit="seed"), 1):
                t0 = time.perf_counter()
                try:
                    rows = session.run(QUERY, seed=address, DEG_CAP=DEG_CAP, NODE_LIMIT=NODE_LIMIT).data()
                    elapsed = time.perf_counter() - t0
                    times.append(elapsed)

                    if rows:
                        for row in rows:
                            row["bad_actor"] = bad_actor
                            writer.writerow(row)
                    else:
                        # No neighbors — write blank row so we don't retry
                        writer.writerow({
                            "seed": address, "bad_actor": bad_actor,
                            "source_id": None, "target_id": None,
                            "btc_amount": None, "block_height": None,
                            "source_hop": None, "target_hop": None,
                            "edge_min_hop": None, "edge_max_hop": None,
                            "tx_direction": None
                        })

                    out.flush()

                    # Rolling stats every 10 seeds
                    if i % 10 == 0:
                        avg     = sum(times) / len(times)
                        eta_hrs = (avg * (len(remaining) - i)) / 3600
                        tqdm.write(
                            f"  [{i:>6}/{len(remaining)}]  "
                            f"last={elapsed:.2f}s  avg={avg:.2f}s  "
                            f"max={max(times):.2f}s  "
                            f"rows={len(rows)}  "
                            f"ETA={eta_hrs:.1f}h"
                        )

                except KeyboardInterrupt:
                    raise  # let it bubble up cleanly

                except Exception as e:
                    elapsed = time.perf_counter() - t0
                    tqdm.write(f"\n  ERROR {address} ({elapsed:.2f}s): {e}")
                    # Not flushed — seed will retry on next run

    except KeyboardInterrupt:
        print("\nInterrupted — progress saved, re-run to resume.")

    finally:
        out.close()
        try:
            driver.close()
        except Exception:
            pass

    if times:
        print(f"\nFinished {len(times):,} seeds")
        print(f"  avg:   {sum(times)/len(times):.2f}s")
        print(f"  max:   {max(times):.2f}s")
        print(f"  total: {sum(times)/3600:.1f}h")
    print(f"\nResults: {CSV_OUT}")

if __name__ == "__main__":
    main()
