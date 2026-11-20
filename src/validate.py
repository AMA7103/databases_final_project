import json
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from db import (
    get_mysql_connection,
    get_mongo_client,
    get_redis_client,
    get_neo4j_driver,
)


MYSQL_TABLES = [
    "users", "addresses", "categories", "products",
    "product_variants", "carts", "cart_items",
    "shipping_options", "orders", "order_items",
    "payments", "returns", "outbox_events"
]


def sql_value(conn, query, params=()):
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        return cursor.fetchone()[0]
    finally:
        cursor.close()


def sql_ids(conn, table, column):
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT {column} FROM {table}")
        return {int(row[0]) for row in cursor}
    finally:
        cursor.close()


def graph_ids(driver, label, field, database):
    with driver.session(database=database) as session:
        records = session.run(
            f"MATCH (n:{label}) RETURN n.{field} AS id"
        )
        return {int(record["id"]) for record in records}


def graph_count(driver, query, database):
    with driver.session(database=database) as session:
        return session.run(query).single()["total"]


def validate():
    failures = []

    def check(label, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        message = f"{status}  {label}"

        if detail:
            message += f" ({detail})"

        print(message, flush=True)

        if not passed:
            failures.append(label)

    def warning(message):
        print(f"WARN  {message}", flush=True)

    mysql = get_mysql_connection()
    mongo = get_mongo_client()
    redis_client = get_redis_client()
    driver = get_neo4j_driver()

    try:
        database = mongo[os.getenv("MONGO_DATABASE", "ecommerce")]
        graph_db = os.getenv("NEO4J_DATABASE", "neo4j")

        now = datetime.now(timezone.utc)
        cutoff_year = (now - timedelta(days=366)).replace(tzinfo=None)
        cutoff_six_months = now - timedelta(days=183)
        cutoff_month = now - timedelta(days=30)

        # MySQL validation
        print("\nMySQL")

        counts = {}

        for table in MYSQL_TABLES:
            counts[table] = sql_value(
                mysql, f"SELECT COUNT(*) FROM `{table}`"
            )

        minimums = {
            "users": 10000,
            "products": 5000,
            "orders": 100000
        }

        check("All 13 MySQL tables exist", len(counts) == 13)

        for table, minimum in minimums.items():
            check(
                f"At least {minimum:,} {table}",
                counts[table] >= minimum,
                f"found {counts[table]:,}"
            )

        check("Required product categories", sql_value(mysql, """
            SELECT COUNT(DISTINCT slug)
            FROM categories
            WHERE slug IN ('fashion', 'headphones', 'home-decor')
        """) == 3)

        check("Low-stock variants exist", sql_value(mysql, """
            SELECT COUNT(*)
            FROM product_variants
            WHERE stock_quantity < 5
        """) > 0)

        check("Fashion sizes and colors exist", sql_value(mysql, """
            SELECT COUNT(*)
            FROM product_variants AS v
            INNER JOIN products AS p
                ON p.product_id = v.product_id
            INNER JOIN categories AS c
                ON c.category_id = p.category_id
            WHERE c.slug = 'fashion'
              AND v.size IS NOT NULL
              AND v.color IS NOT NULL
        """) > 0)

        check("Recent unconverted carts exist", sql_value(mysql, """
            SELECT COUNT(*)
            FROM carts AS c
            WHERE c.created_at >= %s
              AND c.status <> 'converted'
              AND NOT EXISTS (
                  SELECT 1
                  FROM orders AS o
                  WHERE o.cart_id = c.cart_id
              )
        """, (cutoff_month.replace(tzinfo=None),)) > 0)

        check("Order totals are consistent", sql_value(mysql, """
            SELECT COUNT(*)
            FROM orders
            WHERE total_amount <>
                subtotal + tax_amount + shipping_amount
        """) == 0)

        check("Orders span the past year", sql_value(mysql, """
            SELECT COUNT(*)
            FROM orders
            WHERE placed_at >= %s
        """, (cutoff_year,)) >= minimums["orders"])

        user_ids = sql_ids(mysql, "users", "user_id")
        product_ids = sql_ids(mysql, "products", "product_id")
        order_ids = sql_ids(mysql, "orders", "order_id")
        cart_ids = sql_ids(mysql, "carts", "cart_id")
        category_ids = sql_ids(mysql, "categories", "category_id")

        # Sarah's history
        print("\nSarah")

        sarah_id = sql_value(mysql, """
            SELECT MIN(user_id)
            FROM users
            WHERE full_name = 'Sarah'
        """)

        check("Sarah exists", sarah_id is not None)

        if sarah_id is not None:
            check("At least 5 orders in the past year", sql_value(mysql, """
                SELECT COUNT(*)
                FROM orders
                WHERE user_id = %s AND placed_at >= %s
            """, (sarah_id, cutoff_year)) >= 5)

            check("Headphones purchase exists", sql_value(mysql, """
                SELECT COUNT(DISTINCT o.order_id)
                FROM orders AS o
                INNER JOIN order_items AS oi
                    ON oi.order_id = o.order_id
                INNER JOIN product_variants AS v
                    ON v.variant_id = oi.variant_id
                INNER JOIN products AS p
                    ON p.product_id = v.product_id
                INNER JOIN categories AS c
                    ON c.category_id = p.category_id
                WHERE o.user_id = %s
                  AND c.slug = 'headphones'
            """, (sarah_id,)) > 0)

            check("At least one return", sql_value(mysql, """
                SELECT COUNT(*)
                FROM `returns` AS r
                INNER JOIN order_items AS oi
                    ON oi.order_item_id = r.order_item_id
                INNER JOIN orders AS o
                    ON o.order_id = oi.order_id
                WHERE o.user_id = %s
            """, (sarah_id,)) > 0)

            check("Carts on multiple devices", sql_value(mysql, """
                SELECT COUNT(DISTINCT last_device)
                FROM carts
                WHERE user_id = %s
            """, (sarah_id,)) >= 2)

            check("Persistent active cart exists", sql_value(mysql, """
                SELECT COUNT(*)
                FROM carts
                WHERE user_id = %s AND status = 'active'
            """, (sarah_id,)) > 0)

        # MongoDB validation
        print("\nMongoDB")

        doc_count = database.product_attributes.count_documents({})
        event_count = database.events.count_documents({})

        check(
            "Product attribute documents",
            doc_count == counts["products"],
            f"found {doc_count:,}"
        )

        check(
            "At least 500,000 behavior events",
            event_count >= 500000,
            f"found {event_count:,}"
        )

        document_ids = set()
        invalid_documents = 0

        for doc in database.product_attributes.find(
            {}, {"product_id": 1, "attributes": 1}
        ):
            pid = doc.get("product_id")
            document_ids.add(pid)

            if (
                pid not in product_ids
                or not isinstance(doc.get("attributes"), dict)
            ):
                invalid_documents += 1

        check(
            "MongoDB product IDs match MySQL",
            document_ids == product_ids and invalid_documents == 0
        )

        invalid_events = 0
        invalid_timestamps = 0
        event_types = set()
        views_with_duration = 0

        for event in database.events.find({}, {
            "user_id": 1,
            "product_id": 1,
            "cart_id": 1,
            "occurred_at": 1,
            "event_type": 1,
            "search_term": 1,
            "duration_ms": 1
        }).batch_size(5000):

            uid = event.get("user_id")
            pid = event.get("product_id")
            cid = event.get("cart_id")
            kind = event.get("event_type")

            event_types.add(kind)

            if (
                uid not in user_ids
                or (pid is not None and pid not in product_ids)
                or (cid is not None and cid not in cart_ids)
                or (kind == "search" and not event.get("search_term"))
            ):
                invalid_events += 1

            if kind == "product_view" and event.get("duration_ms", 0) > 0:
                views_with_duration += 1

            timestamp = event.get("occurred_at")

            if not isinstance(timestamp, datetime):
                invalid_timestamps += 1
            else:
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)

                if (
                    timestamp < now - timedelta(days=366)
                    or timestamp > now + timedelta(minutes=5)
                ):
                    invalid_timestamps += 1

        check(
            "Behavior event IDs are consistent",
            invalid_events == 0,
            f"invalid {invalid_events:,}"
        )

        check(
            "Event timestamps within the past year",
            invalid_timestamps == 0
        )

        check(
            "All behavior event types present",
            {
                "product_view", "product_click", "search",
                "cart_add", "cart_remove", "cart_update"
            }.issubset(event_types)
        )

        check("Product page durations recorded", views_with_duration > 0)

        if sarah_id is not None:
            check(
                "Sarah has recent product views",
                database.events.count_documents({
                    "user_id": sarah_id,
                    "event_type": "product_view",
                    "occurred_at": {"$gte": cutoff_six_months}
                }) >= 5
            )

            searches = list(database.events.find({
                "user_id": sarah_id,
                "event_type": "search",
                "occurred_at": {"$gte": cutoff_month}
            }, {
                "occurred_at": 1,
                "search_term": 1
            }))

            check("Sarah has recent searches", len(searches) > 0)

            periods = set()
            chicago = ZoneInfo("America/Chicago")

            for event in searches:
                timestamp = event["occurred_at"]

                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)

                hour = timestamp.astimezone(chicago).hour
                periods.add(
                    ("night", "morning", "afternoon", "evening")[hour // 6]
                )

            check(
                "Sarah's searches cover all four time periods",
                len(periods) == 4
            )

        # Neo4j validation
        print("\nNeo4j")

        graph_entities = [
            ("User", "user_id", user_ids),
            ("Product", "product_id", product_ids),
            ("Order", "order_id", order_ids),
            ("Category", "category_id", category_ids)
        ]

        for label, field, expected in graph_entities:
            actual = graph_ids(driver, label, field, graph_db)

            check(
                f"{label} identifiers match MySQL",
                actual == expected,
                f"found {len(actual):,}"
            )

        check("User-order relationships", graph_count(
            driver,
            """
            MATCH (:User)-[r:PLACED]->(:Order)
            RETURN COUNT(r) AS total
            """,
            graph_db
        ) == counts["orders"])

        check("Order-product relationships", graph_count(
            driver,
            """
            MATCH (:Order)-[r:CONTAINS]->(:Product)
            RETURN COUNT(r) AS total
            """,
            graph_db
        ) == counts["order_items"])

        check("Product-category relationships", graph_count(
            driver,
            """
            MATCH (p:Product)-[:IN_CATEGORY]->(:Category)
            RETURN COUNT(DISTINCT p) AS total
            """,
            graph_db
        ) == counts["products"])

        check("Product view relationships", graph_count(
            driver,
            """
            MATCH (:User)-[r:VIEWED]->(:Product)
            RETURN COUNT(r) AS total
            """,
            graph_db
        ) > 0)

        check("Headphones co-purchase data", graph_count(
            driver,
            """
            MATCH (o:Order)-[:CONTAINS]->(h:Product)
                  -[:IN_CATEGORY]->(c:Category)
            WHERE c.slug = 'headphones'
            MATCH (o)-[:CONTAINS]->(other:Product)
            WHERE other.product_id <> h.product_id
            RETURN COUNT(DISTINCT other) AS total
            """,
            graph_db
        ) >= 3)

        # Redis validation
        print("\nRedis")

        check("Redis connection", redis_client.ping())

        if sarah_id is not None:
            for device in ("tablet", "laptop"):
                key = f"session:session-{sarah_id}-{device}"
                session = redis_client.hgetall(key)

                if session:
                    check(
                        f"Sarah's {device} session",
                        int(session.get("user_id", -1)) == sarah_id
                        and session.get("device") == device
                    )
                else:
                    warning(f"{device} session expired or missing")

            cart_data = redis_client.get(f"cart:{sarah_id}")

            if cart_data:
                cart = json.loads(cart_data)

                check(
                    "Sarah's active cart cache",
                    bool(cart.get("items"))
                    and cart.get("last_device") == "laptop"
                )
            else:
                warning("Cart cache expired; MySQL retains the cart")

            recent = redis_client.zrevrange(
                f"recent:{sarah_id}", 0, 4
            )

            if recent:
                check("Recently viewed cache", len(recent) >= 3)
            else:
                warning("Recent-view cache expired")

        cached_stock = redis_client.get("stock:1")

        if cached_stock is not None:
            actual_stock = sql_value(mysql, """
                SELECT stock_quantity
                FROM product_variants
                WHERE variant_id = 1
            """)

            check(
                "Inventory cache matches MySQL",
                int(cached_stock) == actual_stock
            )
        else:
            warning("Inventory cache expired (60-second TTL)")

        # Summary
        print(f"\nValidation complete: {len(failures)} failures")

        for failure in failures:
            print(f"FAIL  {failure}")

        return 1 if failures else 0

    finally:
        mysql.close()
        mongo.close()
        redis_client.close()
        driver.close()


if __name__ == "__main__":
    try:
        sys.exit(validate())
    except Exception as error:
        print(f"Validation stopped: {error}", file=sys.stderr)
        sys.exit(1)
