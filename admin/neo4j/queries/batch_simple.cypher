// =============================================================================
// STEP 0 — One-time setup (run once)
// =============================================================================

// Put BitcoinHeistData.csv in your Neo4j import folder first, then:
LOAD CSV WITH HEADERS FROM 'file:///BitcoinHeistData.csv' AS row
WITH DISTINCT row.address AS addr
WHERE addr IS NOT NULL AND addr <> ''
MERGE (:HeistSeed {address: addr});

// Verify
MATCH (h:HeistSeed) RETURN count(h) AS total_seeds;


// =============================================================================
// STEP 1 — Run the batch (re-run to resume after crash)
// =============================================================================

CALL apoc.periodic.iterate(

  // Iterator: only seeds not yet processed
  'MATCH (h:HeistSeed) WHERE h.done IS NULL RETURN h.address AS seed',

  // Operation: run query, export results, mark done
  '
    WITH seed, 5000 AS DEG_CAP, 8000 AS NODE_LIMIT, 300 AS HOP2_THRESHOLD

    CALL {
      WITH seed, DEG_CAP
      MATCH (s:Script {Address: seed})-[:Transfers]-(h1:Script)
      WHERE COUNT { (h1)-[:Transfers]-() } < DEG_CAP
      WITH collect(DISTINCT s) + collect(DISTINCT h1) AS lvl1, DEG_CAP
      UNWIND lvl1 AS n1
      MATCH (n1:Script)-[:Transfers]-(h2:Script)
      WHERE COUNT { (h2)-[:Transfers]-() } < DEG_CAP
      RETURN count(DISTINCT h2) AS hop2_count
    }

    CALL {
      WITH seed, DEG_CAP, NODE_LIMIT, HOP2_THRESHOLD, hop2_count
      WITH seed, DEG_CAP, NODE_LIMIT, HOP2_THRESHOLD, hop2_count
      WHERE hop2_count > HOP2_THRESHOLD
      CALL apoc.cypher.runTimeboxed("
        MATCH (s:Script {Address: $seed})-[:Transfers]-(h1:Script)
        WHERE COUNT { (h1)-[:Transfers]-() } < $DEG_CAP
        WITH s, collect(DISTINCT h1) AS hop1_nodes
        UNWIND ([s] + hop1_nodes) AS n1
        MATCH (n1:Script)-[:Transfers]-(h2:Script)
        WHERE COUNT { (h2)-[:Transfers]-() } < $DEG_CAP
        WITH s, hop1_nodes, collect(DISTINCT h2) AS hop2_raw
        WITH s, hop1_nodes, [n IN hop2_raw WHERE NOT n IN hop1_nodes AND n <> s] AS hop2_nodes
        WITH s, hop1_nodes, hop2_nodes,
             apoc.coll.toSet([s] + hop1_nodes + hop2_nodes)[0..$NODE_LIMIT] AS neighborhood
        WITH s, neighborhood,
             [{addr: s.Address, hop: 0}] +
             [n IN hop1_nodes WHERE n IN neighborhood | {addr: n.Address, hop: 1}] +
             [n IN hop2_nodes WHERE n IN neighborhood | {addr: n.Address, hop: 2}] AS hop_lookup
        UNWIND neighborhood AS a
        MATCH (a)-[r:Transfers]-(b:Script)
        WHERE b IN neighborhood AND a.Address < b.Address
        RETURN $seed AS inner_seed, a.Address AS source_id, b.Address AS target_id,
               r.Value AS btc_amount, r.Height AS block_height,
               head([x IN hop_lookup WHERE x.addr = a.Address | x.hop]) AS source_hop,
               head([x IN hop_lookup WHERE x.addr = b.Address | x.hop]) AS target_hop,
               CASE WHEN startNode(r) = a AND endNode(r) = b THEN 'source_to_target'
                    WHEN startNode(r) = b AND endNode(r) = a THEN 'target_to_source'
                    ELSE 'unknown' END AS tx_direction
        LIMIT 20000
      ", {seed: seed, DEG_CAP: DEG_CAP, NODE_LIMIT: NODE_LIMIT}, 2000)
      YIELD value
      RETURN value.inner_seed AS result_seed, value.source_id AS source_id,
             value.target_id AS target_id, value.btc_amount AS btc_amount,
             value.block_height AS block_height, value.source_hop AS source_hop,
             value.target_hop AS target_hop, value.tx_direction AS tx_direction

      UNION

      WITH seed, DEG_CAP, NODE_LIMIT, HOP2_THRESHOLD, hop2_count
      WITH seed, DEG_CAP, NODE_LIMIT, HOP2_THRESHOLD, hop2_count
      WHERE hop2_count <= HOP2_THRESHOLD
      CALL apoc.cypher.runTimeboxed("
        MATCH (s:Script {Address: $seed})-[:Transfers]-(h1:Script)
        WHERE COUNT { (h1)-[:Transfers]-() } < $DEG_CAP
        WITH s, collect(DISTINCT h1) AS hop1_nodes
        UNWIND ([s] + hop1_nodes) AS n1
        MATCH (n1:Script)-[:Transfers]-(h2:Script)
        WHERE COUNT { (h2)-[:Transfers]-() } < $DEG_CAP
        WITH s, hop1_nodes, collect(DISTINCT h2) AS hop2_raw
        WITH s, hop1_nodes, [n IN hop2_raw WHERE NOT n IN hop1_nodes AND n <> s] AS hop2_nodes
        WITH s, hop1_nodes, hop2_nodes,
             apoc.coll.toSet([s] + hop1_nodes + hop2_nodes)[0..$NODE_LIMIT] AS lvl2
        UNWIND lvl2 AS n2
        MATCH (n2:Script)-[:Transfers]-(h3:Script)
        WHERE COUNT { (h3)-[:Transfers]-() } < $DEG_CAP
        WITH s, hop1_nodes, hop2_nodes, lvl2, collect(DISTINCT h3) AS hop3_raw
        WITH s, hop1_nodes, hop2_nodes, lvl2,
             [n IN hop3_raw WHERE NOT n IN hop1_nodes AND NOT n IN hop2_nodes AND n <> s] AS hop3_nodes
        WITH s, hop1_nodes, hop2_nodes, hop3_nodes,
             apoc.coll.toSet(lvl2 + hop3_nodes)[0..$NODE_LIMIT] AS neighborhood
        WITH s, neighborhood,
             [{addr: s.Address, hop: 0}] +
             [n IN hop1_nodes WHERE n IN neighborhood | {addr: n.Address, hop: 1}] +
             [n IN hop2_nodes WHERE n IN neighborhood | {addr: n.Address, hop: 2}] +
             [n IN hop3_nodes WHERE n IN neighborhood | {addr: n.Address, hop: 3}] AS hop_lookup
        UNWIND neighborhood AS a
        MATCH (a)-[r:Transfers]-(b:Script)
        WHERE b IN neighborhood AND a.Address < b.Address
        RETURN $seed AS inner_seed, a.Address AS source_id, b.Address AS target_id,
               r.Value AS btc_amount, r.Height AS block_height,
               head([x IN hop_lookup WHERE x.addr = a.Address | x.hop]) AS source_hop,
               head([x IN hop_lookup WHERE x.addr = b.Address | x.hop]) AS target_hop,
               CASE WHEN startNode(r) = a AND endNode(r) = b THEN 'source_to_target'
                    WHEN startNode(r) = b AND endNode(r) = a THEN 'target_to_source'
                    ELSE 'unknown' END AS tx_direction
        LIMIT 20000
      ", {seed: seed, DEG_CAP: DEG_CAP, NODE_LIMIT: NODE_LIMIT}, 2000)
      YIELD value
      RETURN value.inner_seed AS result_seed, value.source_id AS source_id,
             value.target_id AS target_id, value.btc_amount AS btc_amount,
             value.block_height AS block_height, value.source_hop AS source_hop,
             value.target_hop AS target_hop, value.tx_direction AS tx_direction
    }

    // Collect all rows for this seed, write to CSV, mark done
    WITH seed, collect({
      seed:         result_seed,
      source_id:    source_id,
      target_id:    target_id,
      btc_amount:   btc_amount,
      block_height: block_height,
      source_hop:   source_hop,
      target_hop:   target_hop,
      tx_direction: tx_direction
    }) AS rows

    CALL apoc.export.csv.data([], rows,
      "neighborhood_results.csv",
      {delim: ",", quotes: true, appendToFile: true}
    )
    YIELD done

    // Mark this seed complete so re-runs skip it
    MATCH (h:HeistSeed {address: seed})
    SET h.done = true
  ',

  {batchSize: 1, parallel: false}
)
YIELD batches, total, committedOperations, failedOperations
RETURN batches, total, committedOperations, failedOperations;


// =============================================================================
// STEP 2 — Check progress anytime
// =============================================================================

MATCH (h:HeistSeed)
RETURN
  count(h)                                    AS total,
  count(h.done)                               AS done,
  count(h) - count(h.done)                    AS remaining,
  round(100.0 * count(h.done) / count(h), 1) AS pct_complete;
