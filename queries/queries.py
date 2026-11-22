import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from db import (
    get_mongo_client,
    get_mysql_connection,
    get_neo4j_driver,
    get_redis_client,
)

# Fixed inputs
SARAH_USER_ID = 1


def connect():
    """Open all four databases. Returns a dict the queries use as `c`:
    c["mysql"] (connection), c["mongo"] (database), c["redis"], c["neo4j"] (driver)."""
    mongo_client = get_mongo_client()
    return {
        "mysql": get_mysql_connection(),
        "mongo": mongo_client[os.getenv("MONGO_DATABASE", "ecommerce")],
        "redis": get_redis_client(),
        "neo4j": get_neo4j_driver(),
    }


def close(c):
    c["mysql"].close()
    c["mongo"].client.close()
    c["redis"].close()
    c["neo4j"].close()


# The 13 queries.
# Each takes the connections `c`, does its own queries,
# combines results however it needs to, and returns the answer.


# 1. Retrieve all products in the "fashion" category along with their attributes, such as size, color, and material.
# MySQL + Mongo
def q1(c):
    # Query MYSQL for products
    cur = c["mysql"].cursor(dictionary=True)
    cur.execute(
        """
        SELECT p.product_id, p.name, p.base_price,
            v.variant_id, v.size, v.color, v.price, v.stock_quantity
        FROM products p
        JOIN categories c ON c.category_id = p.category_id
        JOIN product_variants v ON v.product_id = p.product_id
        WHERE c.slug = %s
        ORDER BY p.product_id, v.variant_id
        """,
        ("fashion",),
    )
    rows = cur.fetchall()
    cur.close()

    # Group variants under their product
    products = {}
    for r in rows:
        p = products.setdefault(r["product_id"], {
            "product_id": r["product_id"],
            "name": r["name"],
            "base_price": r["base_price"],
            "variants": [],
        })
        p["variants"].append({
            "variant_id": r["variant_id"], "size": r["size"],
            "color": r["color"], "price": r["price"],
            "stock_quantity": r["stock_quantity"],
        })

    # Attach Mongo attributes
    docs = c["mongo"]["product_attributes"].find(
        {"product_id": {"$in": list(products)}},
        {"_id": 0, "product_id": 1, "attributes": 1},
    )
    for doc in docs:
        products[doc["product_id"]]["attributes"] = doc["attributes"]

    return list(products.values())


# 2. Retrieve the last five products Sarah viewed within the past six months, ordered from most recent to least recent.
# MySQL + Mongo + Redis
def q2(c):
    # Query Redis first
    cutoff = time.time() - 182 * 24 * 60 * 60
    viewed = c["redis"].zrevrangebyscore(
        f"recent:{SARAH_USER_ID}", "+inf", cutoff, start=0, num=5, withscores=True
    )
    viewed = [(int(pid), datetime.fromtimestamp(score, timezone.utc)) for pid, score in viewed]

    # If Redis (cache) is missing entries then we check Mongo
    if len(viewed) < 5:
        viewed = recent_views_from_mongo(c, cutoff)
    if not viewed:
        return []

    # Query MySQL for products and details
    ids = [pid for pid, _ in viewed]
    cur = c["mysql"].cursor(dictionary=True)
    cur.execute(
        "SELECT product_id, name, base_price FROM products "
        "WHERE product_id IN (%s)" % ", ".join(["%s"] * len(ids)),
        ids,
    )
    details = {row["product_id"]: row for row in cur.fetchall()}
    cur.close()

    # Keep newest-first order
    return [{**details[pid], "viewed_at": viewed_at} for pid, viewed_at in viewed]

# Helper function for Mongo in q2
def recent_views_from_mongo(c, cutoff):
    """Sarah's five most recently viewed distinct products, as (product_id, viewed_at)."""
    rows = c["mongo"]["events"].aggregate([
        {"$match": {
            "user_id": SARAH_USER_ID,
            "event_type": "product_view",
            "occurred_at": {"$gte": datetime.fromtimestamp(cutoff, timezone.utc)},
        }},
        {"$group": {"_id": "$product_id", "viewed_at": {"$max": "$occurred_at"}}},
        {"$sort": {"viewed_at": -1}},
        {"$limit": 5},
    ])
    return [(row["_id"], row["viewed_at"].replace(tzinfo=timezone.utc)) for row in rows]


# 3. Check the current stock level of every product variant (for example, each size and color of a dress),
# and return only the variants that are low in stock, meaning fewer than five units.
# MySQL
def q3(c):
    # Query MySQL
    cur = c["mysql"].cursor(dictionary=True)
    cur.execute(
        """
        SELECT v.variant_id, v.sku, v.size, v.color, v.stock_quantity,
            p.product_id, p.name
        FROM product_variants v
        JOIN products p ON p.product_id = v.product_id
        WHERE v.stock_quantity < %s
        ORDER BY v.stock_quantity, v.variant_id
        """,
        (5,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


# 4. Retrieve all products in the "fashion" category that are available in blue or in size large.
# MySQL
# Note 1: assumes "blue" means JUST blue, not blue-variants like "aqua-blue"
# Note 2: assumes "available" means inventory (stock_quantity) > 0
def q4(c):
    # Query MySQL
    cur = c["mysql"].cursor(dictionary=True)
    cur.execute(
        """
        SELECT p.product_id, p.name, p.base_price,
            v.variant_id, v.size, v.color, v.price, v.stock_quantity
        FROM products p
        JOIN categories c ON c.category_id = p.category_id
        JOIN product_variants v ON v.product_id = p.product_id
        WHERE c.slug = %s
        AND (v.color = %s OR v.size = %s)
        AND v.stock_quantity > 0
        AND v.is_active = 1
        AND p.is_active = 1
        ORDER BY p.product_id, v.variant_id
        """,
        ("fashion", "blue", "Large"),
    )
    rows = cur.fetchall()
    cur.close()

    # Group matching variants under their product
    products = {}
    for r in rows:
        p = products.setdefault(r["product_id"], {
            "product_id": r["product_id"],
            "name": r["name"],
            "base_price": r["base_price"],
            "variants": [],
        })
        p["variants"].append({
            "variant_id": r["variant_id"], "size": r["size"],
            "color": r["color"], "price": r["price"],
            "stock_quantity": r["stock_quantity"],
        })
    return list(products.values())


# 5. Display the number of times each product page has been viewed, ordered from most viewed to least viewed.
# MySQL + Mongo
def q5(c):
    # Query Mongo for page count and product_id pairs
    counts = {
        row["_id"]: row["views"]
        for row in c["mongo"]["events"].aggregate([
            {"$match": {"event_type": "product_view"}},
            {"$group": {"_id": "$product_id", "views": {"$sum": 1}}},
        ])
    }

    # Query MySQL for products by product_id
    cur = c["mysql"].cursor(dictionary=True)
    cur.execute("SELECT product_id, name FROM products")
    products = cur.fetchall()
    cur.close()

    # Products with no views still show up, with 0
    result = [
        {"product_id": p["product_id"], "name": p["name"],
         "views": counts.get(p["product_id"], 0)}
        for p in products
    ]
    result.sort(key=lambda r: (-r["views"], r["product_id"]))
    return result


# 6. Retrieve all the search terms Sarah used in the past 30 days, and categorize them by frequency and by time of day.
# Use these time-of-day periods: night (00:00–05:59), morning (06:00–11:59), afternoon (12:00–17:59), and evening (18:00–23:59).
# Mongo
# Note 1: time-of-day periods are by UTC since event times are stored in UTC
def q6(c):
    # Query Mongo
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    searches = c["mongo"]["events"].find(
        {"user_id": SARAH_USER_ID, "event_type": "search", "occurred_at": {"$gte": cutoff}},
        {"_id": 0, "search_term": 1, "occurred_at": 1},
    )

    terms = {}
    for s in searches:
        hour = s["occurred_at"].hour
        if hour < 6:
            period = "night"
        elif hour < 12:
            period = "morning"
        elif hour < 18:
            period = "afternoon"
        else:
            period = "evening"

        t = terms.setdefault(s["search_term"], {
            "search_term": s["search_term"], "total": 0,
            "night": 0, "morning": 0, "afternoon": 0, "evening": 0,
        })
        t["total"] += 1
        t[period] += 1

    # Most frequent first
    return sorted(terms.values(), key=lambda t: (-t["total"], t["search_term"]))


# 7. Retrieve information about all active carts:
# the device last used (for example, laptop or tablet), the number of items in the cart,
# and the cart's total amount.
# MySQL
def q7(c):
    # Query MySQL
    cur = c["mysql"].cursor(dictionary=True)
    cur.execute(
        """
        SELECT c.cart_id, c.user_id, c.last_device,
            CAST(COALESCE(SUM(i.quantity), 0) AS UNSIGNED) AS item_count,
            COALESCE(SUM(i.quantity * v.price), 0) AS total_amount
        FROM carts c
        LEFT JOIN cart_items i ON i.cart_id = c.cart_id
        LEFT JOIN product_variants v ON v.variant_id = i.variant_id
        WHERE c.status = 'active'
        GROUP BY c.cart_id, c.user_id, c.last_device
        ORDER BY c.cart_id
        """
    )
    rows = cur.fetchall()
    cur.close()
    return rows


# 8. Retrieve all orders placed by Sarah, showing the order ID, item details,
# payment method, shipping option chosen, and status of each order.
# MySQL 
def q8(c):
    cur = c["mysql"].cursor(dictionary=True)
    cur.execute(
        """
        SELECT o.order_id, o.placed_at, o.status, o.total_amount,
            s.name AS shipping_option, pay.method_type AS payment_method,
            i.product_name_snapshot AS product_name, v.size, v.color,
            i.quantity, i.unit_price
        FROM orders o
        JOIN shipping_options s ON s.shipping_option_id = o.shipping_option_id
        JOIN payments pay ON pay.order_id = o.order_id
        JOIN order_items i ON i.order_id = o.order_id
        JOIN product_variants v ON v.variant_id = i.variant_id
        WHERE o.user_id = %s
        ORDER BY o.placed_at, o.order_id, i.order_item_id
        """,
        (SARAH_USER_ID,),
    )
    rows = cur.fetchall()
    cur.close()

    # Group items under their order
    orders = {}
    for r in rows:
        o = orders.setdefault(r["order_id"], {
            "order_id": r["order_id"], "placed_at": r["placed_at"],
            "status": r["status"], "total_amount": r["total_amount"],
            "shipping_option": r["shipping_option"],
            "payment_method": r["payment_method"],
            "items": [],
        })
        o["items"].append({
            "product_name": r["product_name"], "size": r["size"], "color": r["color"],
            "quantity": r["quantity"], "unit_price": r["unit_price"],
        })
    return list(orders.values())


# 9. List all items Sarah has returned,
# with the refund or exchange status,the refund amount, and any restocking fee.
# MySQL
def q9(c):
    cur = c["mysql"].cursor(dictionary=True)
    cur.execute(
        """
        SELECT r.return_id, o.order_id, i.product_name_snapshot AS product_name,
            r.quantity, r.resolution, r.status, r.refund_status, r.exchange_status,
            r.refund_amount, r.restocking_fee, r.requested_at
        FROM `returns` r
        JOIN order_items i ON i.order_item_id = r.order_item_id
        JOIN orders o ON o.order_id = i.order_id
        WHERE o.user_id = %s
        ORDER BY r.requested_at
        """,
        (SARAH_USER_ID,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows

# 10. Calculate the average number of days between Sarah's purchases.
# MySQL
# Note 1: Excludes cancelled orders
def q10(c):
    cur = c["mysql"].cursor()
    cur.execute(
        "SELECT placed_at FROM orders "
        "WHERE user_id = %s AND status <> 'cancelled' ORDER BY placed_at",
        (SARAH_USER_ID,),
    )
    dates = [row[0] for row in cur.fetchall()]
    cur.close()

    if len(dates) < 2:
        return [{"orders": len(dates), "avg_days_between_purchases": None}]

    gaps = [(b - a).total_seconds() / 86400 for a, b in zip(dates, dates[1:])]
    return [{
        "orders": len(dates),
        "avg_days_between_purchases": round(sum(gaps) / len(gaps), 2),
    }]


# 11. Calculate the percentage of carts created in the past 30 days that never converted to an order.
# MySQL
# Note 1: Assumes currently-open carts count as "never converted to an order."
def q11(c):
    cur = c["mysql"].cursor(dictionary=True)
    cur.execute(
        """
        SELECT COUNT(*) AS carts_created,
            CAST(COALESCE(SUM(o.order_id IS NULL), 0) AS UNSIGNED) AS never_converted
        FROM carts c
        LEFT JOIN orders o ON o.cart_id = c.cart_id
        WHERE c.created_at >= NOW() - INTERVAL 30 DAY
        """
    )
    row = cur.fetchone()
    cur.close()

    created, missed = row["carts_created"], row["never_converted"]
    return [{
        "carts_created": created,
        "never_converted": missed,
        "percent_never_converted": round(100 * missed / created, 2) if created else None,
    }]

# 12. Find the 3 products most frequently purchased in the same order as products in the "headphones" category.
# Neo4j
# Note 1: Excludes items with "headphones" category
# Note 2: Ties are broken by product_id
def q12(c):
    with c["neo4j"].session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:
        result = session.run(
            """
            MATCH (:Category {name: 'Headphones'})<-[:IN_CATEGORY]-(:Product)<-[:CONTAINS]-(o:Order)
            WITH DISTINCT o
            MATCH (o)-[:CONTAINS]->(other:Product)
            WHERE NOT (other)-[:IN_CATEGORY]->(:Category {name: 'Headphones'})
            RETURN other.product_id AS product_id, other.name AS name,
                count(DISTINCT o) AS orders_together
            ORDER BY orders_together DESC, product_id
            LIMIT 3
            """
        )
        return [record.data() for record in result]


# 13. For each user, compute the number of days since their last purchase and their total number of orders.
# MySQL
# Note 1: Excludes cancelled orders
def q13(c):
    cur = c["mysql"].cursor(dictionary=True)
    cur.execute(
        """
        SELECT u.user_id, u.full_name,
            COUNT(o.order_id) AS total_orders,
            DATEDIFF(NOW(), MAX(o.placed_at)) AS days_since_last_purchase
        FROM users u
        LEFT JOIN orders o ON o.user_id = u.user_id AND o.status <> 'cancelled'
        GROUP BY u.user_id, u.full_name
        ORDER BY u.user_id
        """
    )
    rows = cur.fetchall()
    cur.close()
    return rows


QUERIES = {n: globals()[f"q{n}"] for n in range(1, 14)}
