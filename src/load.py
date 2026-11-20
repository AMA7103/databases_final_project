import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db import (
    get_mysql_connection,
    get_mongo_client,
    get_redis_client,
    get_neo4j_driver
)
from schema.redis_store import (
    CART_TTL, RECENT_TTL, RECENT_LIMIT,
    SESSION_TTL, STOCK_TTL
)
from sync import sync_views


MYSQL_ORDER = [
    "users",
    "addresses",
    "categories",
    "products",
    "product_variants",
    "carts",
    "cart_items",
    "shipping_options",
    "orders",
    "order_items",
    "payments",
    "returns"
]


def read_csv(data_dir, table):
    path = data_dir / "mysql" / f"{table}.csv"

    with path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            yield {
                key: value if value != "" else None
                for key, value in row.items()
            }


def batches(rows, size=1000):
    batch = []

    for row in rows:
        batch.append(row)

        if len(batch) == size:
            yield batch
            batch = []

    if batch:
        yield batch


# Load relational data in foreign-key order
def load_mysql(data_dir):
    conn = get_mysql_connection()

    try:
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM users")

            if cursor.fetchone()[0]:
                raise RuntimeError(
                    "MySQL already contains users. "
                    "Use --reset to reload the dataset."
                )

            for table in MYSQL_ORDER:
                path = data_dir / "mysql" / f"{table}.csv"

                with path.open(newline="", encoding="utf-8") as file:
                    columns = csv.DictReader(file).fieldnames

                column_names = ", ".join(
                    f"`{col}`" for col in columns
                )
                placeholders = ", ".join(
                    ["%s"] * len(columns)
                )

                query = (
                    f"INSERT INTO `{table}` ({column_names}) "
                    f"VALUES ({placeholders})"
                )

                count = 0

                for rows in batches(read_csv(data_dir, table), 2000):
                    values = [
                        tuple(row[col] for col in columns)
                        for row in rows
                    ]

                    cursor.executemany(query, values)
                    conn.commit()
                    count += len(rows)

                print(f"MySQL {table}: {count:,} rows", flush=True)

        finally:
            cursor.close()

    finally:
        conn.close()


# Load MongoDB documents with BSON dates
def load_mongodb(data_dir):
    client = get_mongo_client()

    try:
        database = client[os.getenv("MONGO_DATABASE", "ecommerce")]

        for name in ("product_attributes", "events"):
            path = data_dir / "mongodb" / f"{name}.jsonl"

            def documents():
                with path.open(encoding="utf-8") as file:
                    for line in file:
                        doc = json.loads(line)

                        if name == "events":
                            doc["occurred_at"] = datetime.fromisoformat(
                                doc["occurred_at"]
                            )

                        yield doc

            count = 0

            for docs in batches(documents(), 2000):
                database[name].insert_many(docs, ordered=False)
                count += len(docs)

            print(f"MongoDB {name}: {count:,} documents", flush=True)

    finally:
        client.close()


def graph_batches(driver, query, rows, size=500):
    total = 0
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    for batch in batches(rows, size):
        driver.execute_query(query, rows=batch, database_=database)
        total += len(batch)

    return total


# Construct graph from the shared MySQL identifiers
def load_neo4j(data_dir):
    driver = get_neo4j_driver()

    try:
        categories = (
            {
                "category_id": int(row["category_id"]),
                "name": row["name"],
                "slug": row["slug"]
            }
            for row in read_csv(data_dir, "categories")
        )

        graph_batches(driver, """
            UNWIND $rows AS row
            MERGE (c:Category {category_id: row.category_id})
            SET c.name = row.name, c.slug = row.slug
        """, categories)

        users = (
            {
                "user_id": int(row["user_id"]),
                "name": row["full_name"]
            }
            for row in read_csv(data_dir, "users")
        )

        graph_batches(driver, """
            UNWIND $rows AS row
            MERGE (u:User {user_id: row.user_id})
            SET u.name = row.name
        """, users)

        products = (
            {
                "product_id": int(row["product_id"]),
                "category_id": int(row["category_id"]),
                "name": row["name"]
            }
            for row in read_csv(data_dir, "products")
        )

        graph_batches(driver, """
            UNWIND $rows AS row
            MERGE (p:Product {product_id: row.product_id})
            SET p.name = row.name

            WITH p, row
            MATCH (c:Category {category_id: row.category_id})
            MERGE (p)-[:IN_CATEGORY]->(c)
        """, products)

        orders = (
            {
                "order_id": int(row["order_id"]),
                "user_id": int(row["user_id"]),
                "placed_at": row["placed_at"].replace(" ", "T"),
                "status": row["status"]
            }
            for row in read_csv(data_dir, "orders")
        )

        count = graph_batches(driver, """
            UNWIND $rows AS row
            MATCH (u:User {user_id: row.user_id})

            MERGE (o:Order {order_id: row.order_id})
            SET o.placed_at = localdatetime(row.placed_at),
                o.status = row.status

            MERGE (u)-[:PLACED]->(o)
        """, orders)

        print(f"Neo4j orders: {count:,}", flush=True)

        variant_product = {
            int(row["variant_id"]): int(row["product_id"])
            for row in read_csv(data_dir, "product_variants")
        }

        items = (
            {
                "order_item_id": int(row["order_item_id"]),
                "order_id": int(row["order_id"]),
                "product_id": variant_product[int(row["variant_id"])],
                "variant_id": int(row["variant_id"]),
                "quantity": int(row["quantity"]),
                "unit_price": row["unit_price"]
            }
            for row in read_csv(data_dir, "order_items")
        )

        count = graph_batches(driver, """
            UNWIND $rows AS row
            MATCH (o:Order {order_id: row.order_id})
            MATCH (p:Product {product_id: row.product_id})

            MERGE (o)-[r:CONTAINS {
                order_item_id: row.order_item_id
            }]->(p)

            SET r.variant_id = row.variant_id,
                r.quantity = row.quantity,
                r.unit_price = row.unit_price
        """, items)

        print(f"Neo4j order items: {count:,}", flush=True)

    finally:
        driver.close()

    count = sync_views()
    print(f"Neo4j VIEWED relationships: {count:,}", flush=True)


# Load temporary and cached data into Redis
def load_redis(data_dir):
    client = get_redis_client()
    conn = get_mysql_connection()

    try:
        # Sessions
        path = data_dir / "redis" / "sessions.jsonl"

        with client.pipeline(transaction=False) as pipe:
            with path.open(encoding="utf-8") as file:
                for line in file:
                    row = json.loads(line)
                    key = f"session:{row['session_id']}"

                    pipe.hset(key, mapping={
                        "user_id": row["user_id"],
                        "device": row["device"]
                    })
                    pipe.expire(key, SESSION_TTL)

            pipe.execute()

        # Active cart cache
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT c.cart_id, c.user_id, c.last_device,
                       ci.variant_id, ci.quantity, pv.price
                FROM carts AS c
                LEFT JOIN cart_items AS ci
                    ON c.cart_id = ci.cart_id
                LEFT JOIN product_variants AS pv
                    ON ci.variant_id = pv.variant_id
                WHERE c.status = 'active'
                ORDER BY c.cart_id
            """)

            carts = {}

            for row in cursor:
                cart = carts.setdefault(row["user_id"], {
                    "cart_id": row["cart_id"],
                    "last_device": row["last_device"] or "unknown",
                    "items": []
                })

                if row["variant_id"] is not None:
                    cart["items"].append({
                        "variant_id": row["variant_id"],
                        "quantity": row["quantity"],
                        "price": str(row["price"])
                    })

        finally:
            cursor.close()

        with client.pipeline(transaction=False) as pipe:
            for user_id, cart in carts.items():
                cart["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

                pipe.set(
                    f"cart:{user_id}",
                    json.dumps(cart),
                    ex=CART_TTL
                )

            pipe.execute()

        # Inventory cache
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT variant_id, stock_quantity
                FROM product_variants
            """)

            with client.pipeline(transaction=False) as pipe:
                for variant_id, stock in cursor:
                    pipe.set(
                        f"stock:{variant_id}",
                        stock,
                        ex=STOCK_TTL
                    )

                pipe.execute()

        finally:
            cursor.close()

        # Recently viewed products
        recent = defaultdict(dict)
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        path = data_dir / "mongodb" / "events.jsonl"

        with path.open(encoding="utf-8") as file:
            for line in file:
                event = json.loads(line)

                if event["event_type"] != "product_view":
                    continue

                viewed_at = datetime.fromisoformat(
                    event["occurred_at"]
                )

                if viewed_at < cutoff:
                    continue

                user_id = event["user_id"]
                product_id = str(event["product_id"])
                score = viewed_at.timestamp()

                recent[user_id][product_id] = max(
                    score,
                    recent[user_id].get(product_id, 0)
                )

        with client.pipeline(transaction=False) as pipe:
            for user_id, views in recent.items():
                latest = dict(
                    sorted(
                        views.items(),
                        key=lambda item: item[1],
                        reverse=True
                    )[:RECENT_LIMIT]
                )

                key = f"recent:{user_id}"
                pipe.zadd(key, latest)
                pipe.expire(key, RECENT_TTL)

            pipe.execute()

        print(
            f"Redis: sessions, {len(carts):,} active carts, "
            "inventory, and recent views loaded",
            flush=True
        )

    finally:
        conn.close()
        client.close()


# Clear existing project data before reloading
def reset_databases():
    mysql = get_mysql_connection()

    try:
        cursor = mysql.cursor()

        try:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

            for table in MYSQL_ORDER + ["outbox_events"]:
                cursor.execute(f"TRUNCATE TABLE `{table}`")

            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            mysql.commit()

        finally:
            cursor.close()

    finally:
        mysql.close()

    mongo = get_mongo_client()

    try:
        database = mongo[os.getenv("MONGO_DATABASE", "ecommerce")]

        for name in ("events", "product_attributes"):
            database[name].delete_many({})

    finally:
        mongo.close()

    driver = get_neo4j_driver()

    try:
        while True:
            result = driver.execute_query(
                "MATCH (n) WITH n LIMIT 5000 DETACH DELETE n",
                database_=os.getenv("NEO4J_DATABASE", "neo4j")
            )

            if result.summary.counters.nodes_deleted == 0:
                break

    finally:
        driver.close()

    client = get_redis_client()

    try:
        for pattern in (
            "session:*", "cart:*", "recent:*", "stock:*"
        ):
            for keys in batches(
                client.scan_iter(match=pattern, count=1000),
                1000
            ):
                client.delete(*keys)

    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    data_dir = Path(args.data).resolve()

    if not data_dir.is_dir():
        parser.error(f"Data directory not found: {data_dir}")

    if args.reset:
        print("Clearing existing project data...", flush=True)
        reset_databases()

    load_mysql(data_dir)
    load_mongodb(data_dir)
    load_neo4j(data_dir)
    load_redis(data_dir)

    print("All four databases loaded successfully.")


if __name__ == "__main__":
    main()
