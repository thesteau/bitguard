WITH  $seed_parameter AS seed

// --- Bail early if the seed itself is a supernode ---
MATCH (s:Script {Address: seed})
WHERE COUNT { (s)-[:Transfers]-() } < 1000

// --- Hop 1: only non-supernodes ---
MATCH (s)-[:Transfers]-(h1:Script)
WHERE COUNT { (h1)-[:Transfers]-() } < 1000
WITH s, collect(DISTINCT h1)[..5000] AS hop1_nodes

// --- Hop 2: expand each hop-1 node, filter supernodes immediately ---
UNWIND hop1_nodes AS n1
MATCH (n1)-[:Transfers]-(h2:Script)
WHERE COUNT { (h2)-[:Transfers]-() } < 1000
  AND h2 <> s
  AND NOT h2 IN hop1_nodes
WITH s, hop1_nodes, collect(DISTINCT h2)[..5000] AS hop2_nodes

// --- Build final neighborhood (seed + hop1 + hop2, capped) ---
WITH s, hop1_nodes, hop2_nodes,
     apoc.coll.toSet([s] + hop1_nodes + hop2_nodes)[..5000] AS neighborhood

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
  CASE WHEN source_hop <= target_hop THEN source_hop ELSE target_hop END AS edge_min_hop,
  CASE WHEN source_hop >= target_hop THEN source_hop ELSE target_hop END AS edge_max_hop,
  tx_direction
LIMIT 20000