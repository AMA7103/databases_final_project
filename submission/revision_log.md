# Revision Log

## November 19, 2026 — Behavior-event storage

**Change:** As a group, before writing the schema code, we changed the initial plan of storing views, clicks, and page duration in Neo4j. We decided to store raw behavior events in MongoDB and use Neo4j for purchase relationships and summarized viewing relationships.

**Rationale:** MongoDB lets us keep detailed events with different fields for searches, views, clicks, and cart actions. Keeping those raw events out of Neo4j leaves the graph focused on relationships and recommendations. Summarized viewing relationships still let us connect browsing activity to purchases without creating a graph relationship for every view.

**Reflected in:** [schema/mongodb.js](../schema/mongodb.js), [src/load.py](../src/load.py), and [submission/part1_writeup.md](part1_writeup.md).

## November 20, 2026 — Redis expiration policy

**Change:** Increased session and cart expiration from one day to seven days, and inventory cache expiration from 60 seconds to 24 hours.

**Rationale:** Longer expiration times keep sessions and cached carts available between shopping visits. They also let inventory values remain cached longer instead of expiring every minute. Stock freshness relies on invalidation after changes, with MySQL remaining the source of truth.

**Reflected in:** [schema/redis_store.py](../schema/redis_store.py).

## November 22, 2026 — Recently viewed retrieval

**Change:** Expanded the Redis caching plan to include a MongoDB fallback when fewer than five qualifying products are cached.

**Rationale:** Redis entries can expire or contain only part of a user's browsing history. MongoDB retains the underlying view events, so the query can still return the five most recently viewed distinct products within the requested window. Redis remains the first lookup for fast reads when enough cached results are available.

**Reflected in:** [queries/queries.py](../queries/queries.py), in `q2` and `recent_views_from_mongo`.

## November 23, 2026 — Payment attempts in order history

**Change:** Changed Task 8 to select one payment attempt per order, prioritizing successful attempts and then recency, instead of joining every payment attempt to every order item.

**Rationale:** The schema allows multiple payment attempts for an order. Joining all of them to the items could duplicate those items and leave the displayed payment method dependent on row order. Selecting one attempt avoids that duplication, while a left join keeps orders without a payment record visible.

**Reflected in:** [queries/queries.py](../queries/queries.py), in `q8`, and [submission/performance_evaluation.md](performance_evaluation.md).

## November 23, 2026 — Purchase analytics

**Change:** Excluded cancelled orders from co-purchase analysis, allowed another headphones product to qualify as a co-purchase, and separated total order counts from the last non-cancelled purchase date.

**Rationale:** Cancelled orders should not count as purchases, but they still belong in the total number of orders. A different headphones product can legitimately be bought alongside the anchor product, so excluding the entire category missed valid combinations. Counting distinct orders prevents multiple matching items from inflating co-purchase frequency.

**Reflected in:** [queries/queries.py](../queries/queries.py), in `q12` and `q13`, and [submission/performance_evaluation.md](performance_evaluation.md).
