WITH $seed_parameter AS seed
WITH seed, 5000 AS DEG_CAP, 8000 AS NODE_LIMIT
CALL apoc.cypher.runTimeboxed('
  MATCH (s:Script {Address: $seed})-[:Transfers]-(h1:Script)
  WHERE COUNT { (h1)--() } < $DEG_CAP
  WITH collect(DISTINCT s) + collect(DISTINCT h1) AS lvl1
  UNWIND lvl1 AS n1
  MATCH (n1)-[:Transfers]-(h2:Script)
  WHERE COUNT { (h2)--() } < $DEG_CAP
  WITH lvl1, collect(DISTINCT h2) AS hop2_list
  WITH apoc.coll.toSet(lvl1 + hop2_list)[0..$NODE_LIMIT] AS lvl2
  UNWIND lvl2 AS n2
  MATCH (n2)-[:Transfers]-(h3:Script)
  WHERE COUNT { (h3)--() } < $DEG_CAP
  WITH lvl2, collect(DISTINCT h3) AS hop3_list
  WITH apoc.coll.toSet(lvl2 + hop3_list)[0..$NODE_LIMIT] AS neighborhood
  UNWIND neighborhood AS a
  MATCH (a)-[r:Transfers]-(b:Script)
  WHERE b IN neighborhood AND a.Address < b.Address
  RETURN $seed AS seed,
         a.Address AS source_id,
         b.Address AS target_id,
         r.Value AS btc_amount,
         r.Height AS block_height
  LIMIT 20000
', {seed:seed, DEG_CAP:DEG_CAP, NODE_LIMIT:NODE_LIMIT}, 2000)
YIELD value
RETURN value.seed AS seed,
       value.source_id AS source_id,
       value.target_id AS target_id,
       value.btc_amount AS btc_amount,
       value.block_height AS block_height