import os
import sys
import time
from pathlib import Path
from datetime import timezone

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from db import (
    get_mysql_connection,
    get_mongo_client,
    get_redis_client,
    get_neo4j_driver
)
from schema.redis_store import (
    save_cart,
    invalidate_cart,
    invalidate_stock
)


def fetch_mysql(conn, query, params=(), many=False):
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchall() if many else cursor.fetchone()
    finally:
        cursor.close()


# Refresh Redis cart from MySQL
def sync_cart(mysql, redis_client, cart_id):
    cart = fetch_mysql(
        mysql,
        "SELECT * FROM carts WHERE cart_id = %s",
        (cart_id,)
    )

    if not cart:
        raise ValueError(f"Cart {cart_id} not found")

    user_id = cart["user_id"]

    if cart["status"] != "active":
        invalidate_cart(redis_client, user_id)
        return

    items = fetch_mysql(
        mysql,
        """
        SELECT ci.variant_id, ci.quantity, pv.price
        FROM cart_items AS ci
        INNER JOIN product_variants AS pv
            ON ci.variant_id = pv.variant_id
        WHERE ci.cart_id = %s
        """,
        (cart_id,),
        many=True
    )

    items = [
        {
            "variant_id": row["variant_id"],
            "quantity": row["quantity"],
            "price": str(row["price"])
        }
        for row in items
    ]

    save_cart(
        redis_client,
        user_id,
        cart_id,
        items,
        cart["last_device"] or "unknown"
    )


# Update product and category relationships in Neo4j
def sync_product(mysql, driver, product_id):
    product = fetch_mysql(
        mysql,
        """
        SELECT p.product_id, p.name,
               c.category_id, c.name AS category_name,
               c.slug AS category_slug
        FROM products AS p
        INNER JOIN categories AS c
            ON p.category_id = c.category_id
        WHERE p.product_id = %s
        """,
        (product_id,)
    )

    if not product:
        raise ValueError(f"Product {product_id} not found")

    driver.execute_query(
        """
        MERGE (p:Product {product_id: $product_id})
        SET p.name = $name
        MERGE (c:Category {category_id: $category_id})
        SET c.name = $category_name,
            c.slug = $category_slug
        MERGE (p)-[:IN_CATEGORY]->(c)
        """,
        parameters_=product,
        database_=os.getenv("NEO4J_DATABASE", "neo4j")
    )


# Update order relationships in Neo4j
def sync_order(mysql, redis_client, driver, order_id):
    order = fetch_mysql(
        mysql,
        """
        SELECT o.order_id, o.user_id, o.cart_id,
               o.placed_at, o.status, u.full_name
        FROM orders AS o
        INNER JOIN users AS u
            ON o.user_id = u.user_id
        WHERE o.order_id = %s
        """,
        (order_id,)
    )

    if not order:
        raise ValueError(f"Order {order_id} not found")

    items = fetch_mysql(
        mysql,
        """
        SELECT oi.order_item_id, oi.variant_id,
               oi.quantity, oi.unit_price,
               p.product_id, p.name AS product_name,
               c.category_id, c.name AS category_name,
               c.slug AS category_slug
        FROM order_items AS oi
        INNER JOIN product_variants AS pv
            ON oi.variant_id = pv.variant_id
        INNER JOIN products AS p
            ON pv.product_id = p.product_id
        INNER JOIN categories AS c
            ON p.category_id = c.category_id
        WHERE oi.order_id = %s
        """,
        (order_id,),
        many=True
    )

    if not items:
        raise ValueError(f"Order {order_id} has no items")

    graph_items = [
        {
            **item,
            "unit_price": str(item["unit_price"])
        }
        for item in items
    ]

    driver.execute_query(
        """
        MERGE (u:User {user_id: $user_id})
        SET u.name = $full_name

        MERGE (o:Order {order_id: $order_id})
        SET o.placed_at = localdatetime($placed_at),
            o.status = $status

        MERGE (u)-[:PLACED]->(o)

        WITH o
        UNWIND $items AS item

        MERGE (p:Product {product_id: item.product_id})
        SET p.name = item.product_name

        MERGE (c:Category {category_id: item.category_id})
        SET c.name = item.category_name,
            c.slug = item.category_slug

        MERGE (p)-[:IN_CATEGORY]->(c)

        MERGE (o)-[r:CONTAINS {
            order_item_id: item.order_item_id
        }]->(p)

        SET r.variant_id = item.variant_id,
            r.quantity = item.quantity,
            r.unit_price = item.unit_price
        """,
        parameters_={
            "user_id": order["user_id"],
            "full_name": order["full_name"],
            "order_id": order_id,
            "placed_at": order["placed_at"].isoformat(),
            "status": order["status"],
            "items": graph_items
        },
        database_=os.getenv("NEO4J_DATABASE", "neo4j")
    )

    invalidate_cart(redis_client, order["user_id"])

    for item in items:
        invalidate_stock(redis_client, item["variant_id"])


# Process a MySQL outbox event
def handle_event(mysql, redis_client, driver, event):
    event_type = event["event_type"]
    entity_id = event["entity_id"]

    if event_type == "cart_updated":
        sync_cart(mysql, redis_client, entity_id)

    elif event_type == "stock_changed":
        invalidate_stock(redis_client, entity_id)

    elif event_type == "product_updated":
        sync_product(mysql, driver, entity_id)

    elif event_type in ("order_placed", "order_updated"):
        sync_order(mysql, redis_client, driver, entity_id)

    else:
        raise ValueError(f"Unknown event type: {event_type}")


# Process pending events with retries
def process_outbox(batch_size=100):
    mysql = get_mysql_connection()
    redis_client = get_redis_client()
    driver = get_neo4j_driver()

    processed = 0

    try:
        events = fetch_mysql(
            mysql,
            """
            SELECT event_id, event_type, entity_id
            FROM outbox_events
            WHERE processed_at IS NULL
            ORDER BY event_id
            LIMIT %s
            """,
            (batch_size,),
            many=True
        )

        for event in events:
            try:
                handle_event(mysql, redis_client, driver, event)

                cursor = mysql.cursor()
                try:
                    cursor.execute(
                        """
                        UPDATE outbox_events
                        SET processed_at = UTC_TIMESTAMP(6),
                            attempts = attempts + 1,
                            last_error = NULL
                        WHERE event_id = %s
                        """,
                        (event["event_id"],)
                    )
                    mysql.commit()
                finally:
                    cursor.close()

                processed += 1

            except Exception as error:
                mysql.rollback()

                cursor = mysql.cursor()
                try:
                    cursor.execute(
                        """
                        UPDATE outbox_events
                        SET attempts = attempts + 1,
                            last_error = %s
                        WHERE event_id = %s
                        """,
                        (str(error), event["event_id"])
                    )
                    mysql.commit()
                finally:
                    cursor.close()

                print(f"Event {event['event_id']} failed: {error}")

    finally:
        mysql.close()
        redis_client.close()
        driver.close()

    return processed


# Aggregate MongoDB product views into Neo4j
def sync_views(batch_size=500):
    mongo_client = get_mongo_client()
    driver = get_neo4j_driver()
    count = 0

    try:
        database = mongo_client[
            os.getenv("MONGO_DATABASE", "ecommerce")
        ]

        pipeline = [
            {
                "$match": {
                    "event_type": "product_view",
                    "product_id": {"$exists": True}
                }
            },
            {
                "$group": {
                    "_id": {
                        "user_id": "$user_id",
                        "product_id": "$product_id"
                    },
                    "view_count": {"$sum": 1},
                    "last_viewed_at": {"$max": "$occurred_at"}
                }
            }
        ]

        def write_batch(rows):
            driver.execute_query(
                """
                UNWIND $rows AS row
                MERGE (u:User {user_id: row.user_id})
                MERGE (p:Product {product_id: row.product_id})
                MERGE (u)-[r:VIEWED]->(p)
                SET r.view_count = row.view_count,
                    r.last_viewed_at = datetime(row.last_viewed_at)
                """,
                rows=rows,
                database_=os.getenv("NEO4J_DATABASE", "neo4j")
            )

        batch = []

        for event in database.events.aggregate(
            pipeline, allowDiskUse=True
        ):
            timestamp = event["last_viewed_at"]

            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            batch.append({
                "user_id": event["_id"]["user_id"],
                "product_id": event["_id"]["product_id"],
                "view_count": event["view_count"],
                "last_viewed_at": timestamp.isoformat()
            })

            if len(batch) >= batch_size:
                write_batch(batch)
                count += len(batch)
                batch = []

        if batch:
            write_batch(batch)
            count += len(batch)

    finally:
        mongo_client.close()
        driver.close()

    return count


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "views":
        count = sync_views()
        print(f"Synchronized {count} user-product view relationships")

    elif len(sys.argv) > 1 and sys.argv[1] == "watch":
        try:
            while True:
                count = process_outbox()
                if count:
                    print(f"Processed {count} outbox events")
                time.sleep(1)
        except KeyboardInterrupt:
            print("Synchronization stopped")

    else:
        count = process_outbox()
        print(f"Processed {count} outbox events")
