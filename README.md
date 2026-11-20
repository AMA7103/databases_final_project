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

## 4. Data Generation

*To be completed.*

## 5. Data Loading

*To be completed.*

## 6. Running Queries

*To be completed.*

## 7. Data Validation

*To be completed.*

## 8. Performance Evaluation

*To be completed.*

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
- MongoDB. "Create an Index." https://www.mongodb.com/docs/v8.0/core/indexes/create-index/

**What we learned:** How to write and execute JavaScript scripts using `mongosh`, define document validation rules with `$jsonSchema`, update existing collection validators using `collMod`, and create indexes using `createIndex()`.

**How we adapted it:** We used these techniques in `schema/mongodb.js` to initialize the `product_attributes` and `events` collections. We defined required fields and data types while allowing flexible category-specific product attributes. We also created unique and compound indexes to support product lookups, browsing history, search history, and product view counts.

