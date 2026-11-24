# E-Commerce Database Project

## Overview

An e-commerce database backend using four technologies:

- **MySQL:** Users, products, inventory, carts, orders, payments, and returns.
- **MongoDB:** Product-specific attributes and user behavior events.
- **Redis:** Sessions, cart caching, recently viewed products, and inventory caching.
- **Neo4j:** Purchase relationships, co-purchases, and recommendations.

## 1. Technologies

| Database | Docker Image |
|---|---|
| MySQL | `mysql:8.0` |
| MongoDB | `mongo:8.0` |
| Redis | `redis:7.4-alpine` |
| Neo4j | `neo4j:5.26-community` |

**Python:** 3.13. Dependencies are in `requirements.txt`.

## 2. Setup

**Prerequisites:** Python 3.13, Docker Desktop, Git.

Copy the environment template and configure credentials:

```bash
cp .env.example .env
```

Start the databases:

```bash
docker compose up -d
docker compose ps
```

Create a Python environment and install dependencies (macOS/Linux):

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Verify connections:

```bash
python src/db.py
```

Expected output when all services are ready:

```text
MySQL: Connected
MongoDB: Connected
Redis: Connected
Neo4j: Connected
```

## 3. Schema Initialization

Initialize MySQL tables, MongoDB collections, and Neo4j constraints and indexes:

```bash
python src/setup.py
```

Redis requires no schema initialization. The setup script also verifies connections to all four databases.

## 4. Database Synchronization

MySQL uses a transactional outbox to synchronize orders, products, carts, and inventory changes with Redis and Neo4j.

Process pending updates:

```bash
python src/sync.py
```

Continuously synchronize updates:

```bash
python src/sync.py watch
```

Synchronize MongoDB product views into Neo4j:

```bash
python src/sync.py views
```

## 5. Data Generation

Generate synthetic data for all four databases:

```bash
python src/generate.py
```

This creates 10,000 users, 5,000 products, 100,000 orders, and 500,000 behavior events, including Sarah's required history.

Generated files are saved in `data/`. The generator uses a fixed random seed and shared identifiers across databases.

## 6. Data Loading

Load the generated dataset into MySQL, MongoDB, Neo4j, and Redis:

```bash
python src/load.py
```

To clear existing project data and reload:

```bash
python src/load.py --reset
```

Data is inserted in batches using consistent identifiers across databases. Neo4j relationships and Redis caches are derived from the generated data.

## 7. Running Queries

All 13 queries are in `queries/queries.py` as functions `q1(c)` to `q13(c)`. 

To run all of them:

```bash
python queries/run_queries.py
```

To run one query, and add `--show` to print its result:

```bash
python queries/run_queries.py 5
python queries/run_queries.py 5 --show
```

Runtimes and execution plans are in `submission/performance_evaluation.md`.

## 8. Data Validation

Validate dataset sizes, Sarah's history, and consistency across all four databases:

```bash
python src/validate.py
```

The script reports PASS, FAIL, or WARN for each check. A successful validation finishes with zero failures. Expired Redis caches may produce warnings.

## 9. Citations and External Resources

### Redis Python Client

**Source:** Redis. "redis-py guide (Python)."  
https://redis.io/docs/latest/develop/clients/redis-py/

**What we learned:** How to connect to Redis and execute Redis commands through Python using the `redis-py` library, including `set()`, `get()`, `hset()`, and `hgetall()`.

**How we adapted it:** We used these operations in `schema/redis_store.py` to implement user sessions, shopping cart caching, recently viewed products, and inventory caching. As we already knew how to do this in the command line, it was relatively simple mapping this onto what we already knew.

### Redis Pipelines

**Source:** Redis. "Pipelines and transactions."  
https://redis.io/docs/latest/develop/clients/redis-py/transpipe/

**What we learned:** How to batch Redis commands using Python pipelines and execute them together.

**How we adapted it:** We used a transactional pipeline when saving sessions to set session fields and expiration together.

### Neo4j Constraints and Indexes

**Sources:**
- Neo4j. "Create Constraints." https://neo4j.com/docs/cypher-manual/5/constraints/create-constraints/
- Neo4j. "Search-Performance Indexes." https://neo4j.com/docs/cypher-manual/5/indexes/search-performance-indexes/

**What we learned:** How to create uniqueness constraints and indexes in Neo4j using Cypher, including `CREATE CONSTRAINT`, `CREATE INDEX`, and `IF NOT EXISTS`. We also learned that uniqueness constraints automatically create supporting indexes.

**How we adapted it:** We applied uniqueness constraints to `user_id`, `order_id`, `product_id`, and `category_id` in `schema/neo4j.cypher` to maintain consistent identifiers across databases. We added an index on category names to support efficient lookups. We avoided redundant indexes because uniqueness constraints already provide them. This was all done in the cypher file in the schema directory.

### MongoDB JavaScript Scripting, Schema Validation, and Indexes

**Sources:**
- MongoDB. "Write Scripts." https://www.mongodb.com/docs/mongodb-shell/write-scripts/
- MongoDB. "Specify JSON Schema Validation." https://www.mongodb.com/docs/manual/core/schema-validation/specify-json-schema/
- MongoDB. "Modify Schema Validation." https://www.mongodb.com/docs/manual/core/schema-validation/update-schema-validation/

**What we learned:** How to write and execute JavaScript scripts using `mongosh`, define document validation rules with `$jsonSchema`, and update existing collection validators using `collMod`.

**How we adapted it:** We used these techniques in `schema/mongodb.js` to initialize the `product_attributes` and `events` collections. We defined required fields and data types while allowing flexible category-specific product attributes. We also created unique and compound indexes to support product lookups, browsing history, search history, and product view counts.

### Python Timing and Median

**Sources:**
- Python Software Foundation. "time — Time access and conversions." https://docs.python.org/3/library/time.html#time.perf_counter

**What we learned:** How to use `time.perf_counter()` to measure short durations up to fractions of seconds.

**How we adapted it:** In `queries/run_queries.py`, we read `perf_counter()` before and after each query call, run each query 3 times, and report the median of the 3 runtimes.

### Redis ZREVRANGEBYSCORE

**Source:** Redis. "ZREVRANGEBYSCORE." https://redis.io/docs/latest/commands/zrevrangebyscore/

**What we learned:** How to return the members of a sorted set whose scores fall between a maximum and a minimum using `ZREVRANGEBYSCORE`, ordered from highest to lowest score. The page lists the command as deprecated as of Redis 6.2.0, but it still works on the Redis 7.4 we use.

**How we adapted it:** In query 2 in `queries/queries.py` we call `zrevrangebyscore` on a user's `recent:<user_id>` sorted set. The scores are timestamps so the minimum score is the six-month cutoff.


### Neo4j PROFILE

**Source:** Neo4j. "Understanding query plans." https://neo4j.com/docs/cypher-manual/5/planning-and-tuning/execution-plans/

**What we learned:** How to show a query plan with `EXPLAIN` and `PROFILE`. `EXPLAIN` provides an estimate without running and `PROFILE` runs the query and shows real measurements for each operator, including rows produced and database hits. The plan is read from the bottom up.

**How we adapted it:** We ran `PROFILE` on the Neo4j query (Query 12) in `cypher-shell` and recorded the output in `submission/performance_evaluation.md`.

### MongoDB explain

**Sources:**
- MongoDB. "cursor.explain()." https://www.mongodb.com/docs/manual/reference/method/cursor.explain/
- MongoDB. "explain (database command)." https://www.mongodb.com/docs/manual/reference/command/explain/
- MongoDB. "Explain Results." https://www.mongodb.com/docs/manual/reference/explain-results/

**What we learned:** How to use `explain` to get the query plan. It has three verbosity modes: `queryPlanner`, `executionStats` and `allPlansExecution`. `executionStats` runs the winning plan and returns its statistics, including `nReturned`, `totalKeysExamined` and `totalDocsExamined`, so we can compare documents examined against documents returned.

**How we adapted it:** We ran the `explain` command with `executionStats` verbosity on the MongoDB calls in Queries 1, 2, 5 and 6 and recorded the output in `submission/performance_evaluation.md`.

## 10. Contributions

- Everyone contributed to database design and schema decisions.
- Anuj Agarwal wrote the initial schema code and the data generation and loading scripts.
- Neal Jere completed the Part 1 write-up, ERD, and supporting diagrams and explanations.
- Jaden Lee wrote the queries and completed the performance evaluation.
