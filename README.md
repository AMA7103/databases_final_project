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

*To be completed.*

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
